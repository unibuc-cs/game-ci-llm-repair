"""Prototype for the governed LLM bug-repair workflow.

The default mode is deterministic and offline, so the demo can run without
engine installations or LLM credentials. The same orchestration can also use an
OpenAI patch provider configured for gpt-5.5 and command-backed gate runners.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import uuid
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


LEVEL_ORDER = ["T0", "T1", "T2", "T3"]
DEFAULT_OPENAI_MODEL = "gpt-5.5"
METRICS_PREFIX = "SANERBUG_METRICS "


@dataclass(frozen=True)
class Diagnosis:
    mode: str
    start_level: str
    approval_required: bool
    reasons: list[str]


@dataclass
class GateOutcome:
    gate: str
    ok: bool
    metrics: dict[str, Any]
    message: str


@dataclass
class RepairResult:
    case_id: str
    description: str
    diagnosis: Diagnosis
    status: str
    attempts: int
    ci_runs: int
    accepted_patch: str | None
    best_patch: str | None
    last_failing_gate: str | None
    gate_history: list[dict[str, Any]]
    prompts: list[dict[str, str]]
    final_symptom_card: dict[str, Any]

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "description": self.description,
            "diagnosis": {
                "mode": self.diagnosis.mode,
                "start_level": self.diagnosis.start_level,
                "approval_required": self.diagnosis.approval_required,
                "reasons": self.diagnosis.reasons,
            },
            "status": self.status,
            "attempts": self.attempts,
            "ci_runs": self.ci_runs,
            "accepted_patch": self.accepted_patch,
            "best_patch": self.best_patch,
            "last_failing_gate": self.last_failing_gate,
            "gate_history": self.gate_history,
            "prompts": self.prompts,
            "final_symptom_card": self.final_symptom_card,
        }


class PatchProvider(Protocol):
    name: str

    def propose(
        self,
        case: dict[str, Any],
        level: str,
        attempt: int,
        prompt: str,
        symptom: dict[str, Any],
        policy: dict[str, Any],
        arch: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a candidate patch dictionary."""


class GateRunner(Protocol):
    name: str

    def run(
        self,
        gate: str,
        candidate: dict[str, Any],
        policy: dict[str, Any],
        arch: dict[str, Any],
    ) -> GateOutcome:
        """Run one CI gate for a candidate patch."""


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


def normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def matches_allowlist(path: str, patterns: list[str]) -> bool:
    normalized = normalize_path(path)
    allowed = False
    for raw_pattern in patterns:
        is_negative = raw_pattern.startswith("!")
        pattern = raw_pattern[1:] if is_negative else raw_pattern
        if fnmatch.fnmatch(normalized, pattern):
            allowed = not is_negative
    return allowed


def flatten_files(code_context: dict[str, Any], hops: int) -> list[str]:
    files: list[str] = []
    for item in code_context.get("primary_files", []):
        path = item.get("path")
        if path:
            files.append(path)

    if hops > 0:
        for neighbors in code_context.get("neighbors", {}).values():
            for item in neighbors:
                path = item.get("path")
                if path:
                    files.append(path)

    seen: set[str] = set()
    unique: list[str] = []
    for path in files:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def has_visual_signal(symptom: dict[str, Any]) -> bool:
    visual_graph = symptom.get("visual_graph") or {}
    if visual_graph:
        return True
    text = json.dumps(symptom.get("tests_failed", []), sort_keys=True).lower()
    return any(token in text for token in ["blueprint", "bp_", "visual", "event binding"])


def has_perf_budget_signal(symptom: dict[str, Any], arch: dict[str, Any]) -> bool:
    perf = symptom.get("perf") or {}
    for key, budget in (arch.get("perf_budget") or {}).items():
        value = perf.get(key)
        if isinstance(value, (int, float)) and isinstance(budget, (int, float)):
            if value > budget:
                return True

    text = json.dumps(symptom.get("tests_failed", []), sort_keys=True).lower()
    return any(token in text for token in ["perf", "budget", "frametime", "fixedupdate"])


def has_invariant_signal(symptom: dict[str, Any]) -> bool:
    for item in symptom.get("invariants") or []:
        if item.get("violations", 0) > 0:
            return True
    return False


def has_cross_file_signal(symptom: dict[str, Any], code_context: dict[str, Any]) -> bool:
    if code_context.get("neighbors"):
        return True
    text = json.dumps(symptom.get("tests_failed", []), sort_keys=True)
    return "->" in text or "=>" in text


def diagnosis_d0(case: dict[str, Any], arch: dict[str, Any]) -> Diagnosis:
    symptom = case["symptom_card"]
    context = case["code_context"]
    reasons: list[str] = []

    if has_visual_signal(symptom):
        reasons.append("visual-graph or Blueprint/event-binding evidence is present")
        start_level = "T3"
        mode = "visual_scripting"
    elif has_perf_budget_signal(symptom, arch) or has_invariant_signal(symptom):
        reasons.append("runtime budget or invariant evidence must be visible")
        start_level = "T2"
        mode = "performance_or_invariant"
    elif has_cross_file_signal(symptom, context):
        reasons.append("fault evidence reaches direct caller/callee neighbors")
        start_level = "T1"
        mode = "cross_file_source"
    else:
        reasons.append("fault evidence is local to the primary file set")
        start_level = "T0"
        mode = "local_source"

    approval_required = False
    if start_level in {"T2", "T3"}:
        approval_required = bool(arch.get("approval_required_for_broad_scope", True))
        if approval_required:
            reasons.append("broad repair level requires bounded human approval")

    return Diagnosis(
        mode=mode,
        start_level=start_level,
        approval_required=approval_required,
        reasons=reasons,
    )


def policies_from(policies: dict[str, Any], start_level: str) -> list[tuple[str, dict[str, Any]]]:
    start_index = LEVEL_ORDER.index(start_level)
    return [(level, policies[level]) for level in LEVEL_ORDER[start_index:]]


def final_gate_names(case: dict[str, Any], arch: dict[str, Any]) -> list[str]:
    gate_commands = (case.get("replay") or {}).get("gate_commands") or {}
    if gate_commands:
        ordered = [gate for gate in arch.get("gates", []) if gate in gate_commands]
        extras = [gate for gate in gate_commands if gate not in ordered]
        return ordered + extras
    return list(arch.get("gates", []))


def assemble_prompt(
    policy: dict[str, Any],
    symptom: dict[str, Any],
    arch: dict[str, Any],
    code_context: dict[str, Any],
) -> str:
    context_policy = policy.get("context", {})
    hops = int(context_policy.get("cg_hops", 0))
    visible_paths = flatten_files(code_context, hops)

    evidence: dict[str, Any] = {
        "tests_failed": symptom.get("tests_failed", []),
        "exceptions": symptom.get("exceptions", []),
        "paths": visible_paths,
        "last_failing_gate": symptom.get("last_failing_gate"),
    }
    if context_policy.get("include_profiler"):
        evidence["perf"] = symptom.get("perf", {})
    if context_policy.get("include_invariants"):
        evidence["invariants"] = symptom.get("invariants", [])
    if context_policy.get("include_static_features"):
        evidence["static_features"] = symptom.get("static_features", {})
    if context_policy.get("include_visual_graph"):
        evidence["visual_graph"] = symptom.get("visual_graph", {})
    if symptom.get("domain_hints"):
        evidence["domain_hints"] = symptom["domain_hints"]
    if symptom.get("human_hints"):
        evidence["human_hints"] = symptom["human_hints"]

    policy_block: dict[str, Any] = {
        "level": policy["level"],
        "allowed_actions": policy.get("allowed_actions", {}),
        "gates": policy.get("gates", []),
        "attempts": policy.get("prompt", {}).get("attempts", 1),
    }
    if context_policy.get("include_arch_card"):
        policy_block["architecture_card"] = {
            "invariants": arch.get("invariants", []),
            "perf_budget": arch.get("perf_budget", {}),
            "allowed_components": arch.get("allowed_components", []),
            "file_allowlist": arch.get("file_allowlist", []),
        }

    return "\n".join(
        [
            "Role: Senior engineer",
            "Task: Propose minimal patch",
            f"Bug: {symptom.get('bug_id')}",
            f"Engine: {symptom.get('engine')}",
            "",
            "Evidence:",
            json.dumps(evidence, indent=2, sort_keys=True),
            "",
            "Policy:",
            json.dumps(policy_block, indent=2, sort_keys=True),
            "",
            "Deliver: unified diff; 3-line rationale; test plan",
        ]
    )


def candidate_for(case: dict[str, Any], level: str, attempt: int) -> dict[str, Any]:
    for candidate in case.get("candidates", []):
        if candidate["level"] == level and int(candidate["attempt"]) == attempt:
            return deepcopy(candidate)

    return {
        "patch_id": f"{case['case_id']}-{level}-{attempt}-noop",
        "summary": "No candidate was configured for this synthetic slot.",
        "modified_files": [],
        "requires_visual_graph_edit": False,
        "gate_results": {
            "build": {"ok": True, "metrics": {}, "message": "No-op compiles."},
            "unit": {"ok": False, "metrics": {}, "message": "No-op leaves failing behavior unchanged."},
        },
    }


class SyntheticPatchProvider:
    name = "synthetic"

    def propose(
        self,
        case: dict[str, Any],
        level: str,
        attempt: int,
        prompt: str,
        symptom: dict[str, Any],
        policy: dict[str, Any],
        arch: dict[str, Any],
    ) -> dict[str, Any]:
        del prompt, symptom, policy, arch
        candidate = candidate_for(case, level, attempt)
        attach_case_runtime(candidate, case)
        return candidate


def openai_candidate_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "summary",
            "modified_files",
            "requires_visual_graph_edit",
            "creates_new_file",
            "unified_diff",
            "test_plan",
        ],
        "properties": {
            "summary": {"type": "string"},
            "modified_files": {"type": "array", "items": {"type": "string"}},
            "requires_visual_graph_edit": {"type": "boolean"},
            "creates_new_file": {"type": "boolean"},
            "unified_diff": {"type": "string"},
            "test_plan": {"type": "array", "items": {"type": "string"}},
        },
    }


class OpenAIPatchProvider:
    def __init__(self, model: str = DEFAULT_OPENAI_MODEL, max_output_tokens: int = 1800) -> None:
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.name = f"openai:{model}"

    def propose(
        self,
        case: dict[str, Any],
        level: str,
        attempt: int,
        prompt: str,
        symptom: dict[str, Any],
        policy: dict[str, Any],
        arch: dict[str, Any],
    ) -> dict[str, Any]:
        del symptom, arch
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Set it before using --patch-provider openai."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The 'openai' package is required for --patch-provider openai. "
                "Install it with: pip install openai"
            ) from exc

        client = OpenAI()
        temperature = float(policy.get("prompt", {}).get("temperature", 0.0))
        response = client.responses.create(
            model=self.model,
            instructions=(
                "You are a senior game-engine repair engineer. Return only JSON "
                "matching the supplied schema. The unified_diff must be minimal, "
                "respect the active policy, and avoid unrelated edits."
            ),
            input=prompt,
            temperature=temperature,
            max_output_tokens=self.max_output_tokens,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "candidate_patch",
                    "schema": openai_candidate_schema(),
                    "strict": True,
                }
            },
        )
        raw = getattr(response, "output_text", None)
        if not raw:
            raise RuntimeError("OpenAI response did not include output_text.")

        payload = json.loads(raw)
        return {
            "patch_id": f"{case['case_id']}-{level}-{attempt}-openai-{self.model}",
            "summary": payload["summary"],
            "modified_files": payload["modified_files"],
            "requires_visual_graph_edit": payload["requires_visual_graph_edit"],
            "creates_new_file": payload["creates_new_file"],
            "unified_diff": payload["unified_diff"],
            "test_plan": payload["test_plan"],
            "provider": self.name,
            "case_id": case["case_id"],
            "replay": deepcopy(case.get("replay", {})),
            "gate_results": {},
        }


def attach_case_runtime(candidate: dict[str, Any], case: dict[str, Any]) -> None:
    candidate.setdefault("case_id", case["case_id"])
    if case.get("replay"):
        candidate.setdefault("replay", deepcopy(case["replay"]))


def validate_candidate_permissions(
    candidate: dict[str, Any],
    policy: dict[str, Any],
    arch: dict[str, Any],
) -> tuple[bool, str]:
    allowed_patterns = (
        policy.get("allowed_actions", {}).get("file_allowlist")
        or arch.get("file_allowlist", [])
    )
    for path in candidate.get("modified_files", []):
        if not matches_allowlist(path, allowed_patterns):
            return False, f"{path} is outside the active file allowlist"

    if candidate.get("creates_new_file") and not policy.get("allowed_actions", {}).get("new_files", False):
        return False, "candidate creates a new file at a level where new files are disabled"

    if candidate.get("requires_visual_graph_edit") and not policy.get("allowed_actions", {}).get(
        "visual_graph_edits", False
    ):
        return False, "candidate edits a visual graph before T3 permissions are active"

    return True, "candidate respects active edit permissions"


def enforce_gate_policy(
    gate: str,
    ok: bool,
    metrics: dict[str, Any],
    message: str,
    arch: dict[str, Any],
) -> tuple[bool, str]:
    if gate == "perf":
        for metric, budget in (arch.get("perf_budget") or {}).items():
            value = metrics.get(metric)
            if isinstance(value, (int, float)) and isinstance(budget, (int, float)) and value > budget:
                ok = False
                message = f"{metric}={value} exceeds budget {budget}"

    if gate == "invariants":
        violations = metrics.get("violations", {})
        if isinstance(violations, dict):
            failing = {name: count for name, count in violations.items() if count}
            if failing:
                ok = False
                message = f"invariant violations remain: {failing}"

    return ok, message


class SyntheticGateRunner:
    name = "synthetic"

    def run(
        self,
        gate: str,
        candidate: dict[str, Any],
        policy: dict[str, Any],
        arch: dict[str, Any],
    ) -> GateOutcome:
        if gate == "build":
            allowed, message = validate_candidate_permissions(candidate, policy, arch)
            if not allowed:
                return GateOutcome(gate=gate, ok=False, metrics={}, message=message)

        gate_results = candidate.get("gate_results", {})
        if gate not in gate_results:
            return GateOutcome(
                gate=gate,
                ok=False,
                metrics={},
                message=f"synthetic gate result missing for '{gate}'",
            )

        result = deepcopy(gate_results[gate])
        ok = bool(result.get("ok", True))
        metrics = result.get("metrics") or {}
        message = result.get("message", "gate passed" if ok else "gate failed")
        ok, message = enforce_gate_policy(gate, ok, metrics, message, arch)
        return GateOutcome(gate=gate, ok=ok, metrics=metrics, message=message)


class CommandGateRunner:
    def __init__(self, commands: dict[str, str], cwd: Path, timeout_s: int = 300) -> None:
        self.commands = commands
        self.cwd = cwd
        self.timeout_s = timeout_s
        self.name = "command"

    def run(
        self,
        gate: str,
        candidate: dict[str, Any],
        policy: dict[str, Any],
        arch: dict[str, Any],
    ) -> GateOutcome:
        if gate == "build":
            allowed, message = validate_candidate_permissions(candidate, policy, arch)
            if not allowed:
                return GateOutcome(gate=gate, ok=False, metrics={}, message=message)

        command = self.commands.get(gate)
        if not command:
            return GateOutcome(
                gate=gate,
                ok=False,
                metrics={},
                message=f"no command configured for gate '{gate}'",
            )

        candidate_path = self._write_candidate(candidate, gate)
        env = dict(os.environ)
        env.update(
            {
                "SANERBUG_GATE": gate,
                "SANERBUG_PATCH_ID": candidate.get("patch_id", ""),
                "SANERBUG_CANDIDATE_JSON": str(candidate_path),
            }
        )
        try:
            completed = subprocess.run(
                command,
                cwd=str(self.cwd),
                env=env,
                shell=True,
                text=True,
                capture_output=True,
                timeout=self.timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            return GateOutcome(
                gate=gate,
                ok=False,
                metrics={"timeout_s": self.timeout_s},
                message=f"gate command timed out: {exc}",
            )
        finally:
            try:
                candidate_path.unlink(missing_ok=True)
            except OSError:
                pass

        ok = completed.returncode == 0
        metrics = {
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-1200:],
            "stderr_tail": completed.stderr[-1200:],
        }
        message = "command gate passed" if ok else "command gate failed"
        ok, message = enforce_gate_policy(gate, ok, metrics, message, arch)
        return GateOutcome(gate=gate, ok=ok, metrics=metrics, message=message)

    def _write_candidate(self, candidate: dict[str, Any], gate: str) -> Path:
        safe_gate = "".join(ch for ch in gate if ch.isalnum() or ch in {"-", "_"})
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            suffix=f"-{safe_gate}-candidate.json",
            delete=False,
        ) as fh:
            json.dump(candidate, fh, indent=2, sort_keys=True)
            fh.write("\n")
            return Path(fh.name)


def safe_path_segment(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "trial"


def parse_metrics(stdout: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith(METRICS_PREFIX):
            continue
        payload = line[len(METRICS_PREFIX) :]
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            metrics.update(parsed)
    return metrics


class ReplayProjectGateRunner:
    def __init__(
        self,
        workspace_root: Path,
        trials_root: Path = Path("outputs/replay_trials"),
        timeout_s: int = 120,
        keep_trials: bool = True,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.trials_root = trials_root
        self.timeout_s = timeout_s
        self.keep_trials = keep_trials
        self.name = "replay"
        self._prepared: dict[str, Path] = {}

    def run(
        self,
        gate: str,
        candidate: dict[str, Any],
        policy: dict[str, Any],
        arch: dict[str, Any],
    ) -> GateOutcome:
        if gate == "build":
            allowed, message = validate_candidate_permissions(candidate, policy, arch)
            if not allowed:
                return GateOutcome(gate=gate, ok=False, metrics={}, message=message)

        try:
            trial_dir = self._prepare_trial(candidate)
        except RuntimeError as exc:
            return GateOutcome(gate=gate, ok=False, metrics={}, message=str(exc))

        replay = candidate.get("replay") or {}
        command = (replay.get("gate_commands") or {}).get(gate)
        trial_report_path = self._display_path(trial_dir)
        if not command:
            return GateOutcome(
                gate=gate,
                ok=False,
                metrics={"trial_dir": trial_report_path},
                message=f"no replay command configured for gate '{gate}'",
            )

        env = dict(os.environ)
        env.update(
            {
                "PYTHONDONTWRITEBYTECODE": "1",
                "SANERBUG_GATE": gate,
                "SANERBUG_PATCH_ID": candidate.get("patch_id", ""),
                "SANERBUG_CASE_ID": candidate.get("case_id", ""),
                "SANERBUG_TRIAL_DIR": str(trial_dir),
            }
        )
        try:
            completed = subprocess.run(
                command,
                cwd=str(trial_dir),
                env=env,
                shell=True,
                text=True,
                capture_output=True,
                timeout=self.timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            return GateOutcome(
                gate=gate,
                ok=False,
                metrics={"trial_dir": trial_report_path, "timeout_s": self.timeout_s},
                message=f"replay gate timed out: {exc}",
            )

        metrics = parse_metrics(completed.stdout)
        metrics.update(
            {
                "returncode": completed.returncode,
                "trial_dir": trial_report_path,
                "stdout_tail": self._clean_output(completed.stdout),
                "stderr_tail": self._clean_output(completed.stderr),
            }
        )
        ok = completed.returncode == 0
        message = "replay gate passed" if ok else self._failure_message(completed)
        ok, message = enforce_gate_policy(gate, ok, metrics, message, arch)
        return GateOutcome(gate=gate, ok=ok, metrics=metrics, message=message)

    def _prepare_trial(self, candidate: dict[str, Any]) -> Path:
        patch_id = candidate.get("patch_id")
        if not patch_id:
            raise RuntimeError("candidate is missing patch_id")
        if patch_id in self._prepared:
            return self._prepared[patch_id]

        replay = candidate.get("replay") or {}
        project_path = replay.get("project_path")
        if not project_path:
            raise RuntimeError("candidate is missing replay.project_path")

        source = (self.workspace_root / project_path).resolve()
        if not source.exists():
            raise RuntimeError(f"replay project does not exist: {source}")

        case_id = safe_path_segment(candidate.get("case_id", "case"))
        patch_segment = safe_path_segment(patch_id)
        trials_base = (self.workspace_root / self.trials_root).resolve()
        trial_dir = (trials_base / case_id / patch_segment).resolve()
        if not str(trial_dir).startswith(str(trials_base)):
            raise RuntimeError(f"refusing trial path outside replay root: {trial_dir}")

        if trial_dir.exists():
            try:
                self._remove_tree(trial_dir)
            except OSError:
                trial_dir = (trials_base / case_id / f"{patch_segment}-{uuid.uuid4().hex[:8]}").resolve()
                if not str(trial_dir).startswith(str(trials_base)):
                    raise RuntimeError(f"refusing trial path outside replay root: {trial_dir}")
        trial_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, trial_dir)
        init = subprocess.run(
            ["git", "init", "--quiet"],
            cwd=str(trial_dir),
            text=True,
            capture_output=True,
        )
        if init.returncode != 0:
            raise RuntimeError("failed to initialize replay trial git root: " + init.stderr.strip())

        diff_text = candidate.get("unified_diff", "").strip()
        if diff_text:
            diff_path = trial_dir / "candidate.patch"
            diff_path.write_text(diff_text + "\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    "git",
                    "apply",
                    "--ignore-space-change",
                    "--ignore-whitespace",
                    "--whitespace=nowarn",
                    str(diff_path),
                ],
                cwd=str(trial_dir),
                text=True,
                capture_output=True,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    "failed to apply candidate patch: "
                    + (completed.stderr or completed.stdout).strip()
                )
            diff_path.unlink(missing_ok=True)

        candidate["trial_dir"] = self._display_path(trial_dir)
        self._prepared[patch_id] = trial_dir
        return trial_dir

    def _failure_message(self, completed: subprocess.CompletedProcess[str]) -> str:
        text = self._clean_output(completed.stderr or completed.stdout or "replay gate failed").strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines[-1] if lines else "replay gate failed"

    def _display_path(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.workspace_root).as_posix()
        except ValueError:
            return str(path)

    def _clean_output(self, text: str) -> str:
        cleaned = text.replace(str(self.workspace_root), ".")
        workspace_posix = self.workspace_root.as_posix()
        if workspace_posix != str(self.workspace_root):
            cleaned = cleaned.replace(workspace_posix, ".")
        return cleaned[-1200:]

    def _remove_tree(self, path: Path) -> None:
        def clear_readonly(function, failed_path, excinfo) -> None:
            del excinfo
            os.chmod(failed_path, stat.S_IWRITE)
            function(failed_path)

        shutil.rmtree(path, onexc=clear_readonly)


def run_gate(
    gate: str,
    candidate: dict[str, Any],
    policy: dict[str, Any],
    arch: dict[str, Any],
) -> GateOutcome:
    return SyntheticGateRunner().run(gate, candidate, policy, arch)


def update_symptom_card(
    symptom: dict[str, Any],
    level: str,
    candidate: dict[str, Any],
    gate_outcomes: list[GateOutcome],
    failing_gate: str,
) -> None:
    symptom["last_failing_gate"] = failing_gate
    history_entry = {
        "level": level,
        "patch_id": candidate["patch_id"],
        "failing_gate": failing_gate,
        "gates": [
            {
                "gate": outcome.gate,
                "ok": outcome.ok,
                "metrics": outcome.metrics,
                "message": outcome.message,
            }
            for outcome in gate_outcomes
        ],
    }
    symptom.setdefault("gate_history", []).append(history_entry)

    for outcome in gate_outcomes:
        if outcome.gate == "perf" and outcome.metrics:
            symptom.setdefault("perf", {}).update(outcome.metrics)
        if outcome.gate == "invariants" and outcome.metrics.get("violations"):
            updated = []
            current = {item["name"]: dict(item) for item in symptom.get("invariants", [])}
            for name, count in outcome.metrics["violations"].items():
                current[name] = {"name": name, "violations": count}
            for name in sorted(current):
                updated.append(current[name])
            symptom["invariants"] = updated


def run_case(
    case: dict[str, Any],
    policies: dict[str, Any],
    architecture_cards: dict[str, Any],
    patch_provider: PatchProvider | None = None,
    gate_runner: GateRunner | None = None,
    start_level_override: str | None = None,
    max_total_attempts: int | None = None,
    require_final_gates: bool = False,
    mode_label: str | None = None,
) -> RepairResult:
    patch_provider = patch_provider or SyntheticPatchProvider()
    gate_runner = gate_runner or SyntheticGateRunner()
    arch = deepcopy(architecture_cards[case["architecture_card"]])
    symptom = deepcopy(case["symptom_card"])
    symptom["human_hints"] = deepcopy(case.get("human_hints", []))
    symptom.setdefault("gate_history", [])
    diagnosis = diagnosis_d0(case, arch)
    if start_level_override:
        diagnosis = Diagnosis(
            mode=mode_label or f"{diagnosis.mode}_override",
            start_level=start_level_override,
            approval_required=diagnosis.approval_required,
            reasons=diagnosis.reasons
            + [f"evaluation override starts repair at {start_level_override}"],
        )

    attempts_total = 0
    ci_runs = 0
    seen: set[str] = set()
    prompts: list[dict[str, str]] = []
    best_patch: str | None = None
    best_passed_count = -1
    last_failing_gate: str | None = None

    for level, policy in policies_from(policies, diagnosis.start_level):
        attempts = int(policy.get("prompt", {}).get("attempts", 1))
        for attempt in range(1, attempts + 1):
            if max_total_attempts is not None and attempts_total >= max_total_attempts:
                return stopped_result(
                    case=case,
                    diagnosis=diagnosis,
                    attempts_total=attempts_total,
                    ci_runs=ci_runs,
                    best_patch=best_patch,
                    best_passed_count=best_passed_count,
                    last_failing_gate=last_failing_gate,
                    prompts=prompts,
                    symptom=symptom,
                )
            attempts_total += 1
            prompt = assemble_prompt(policy, symptom, arch, case["code_context"])
            prompts.append({"level": level, "attempt": str(attempt), "text": prompt})

            candidate = patch_provider.propose(
                case=case,
                level=level,
                attempt=attempt,
                prompt=prompt,
                symptom=symptom,
                policy=policy,
                arch=arch,
            )
            patch_id = candidate["patch_id"]
            if patch_id in seen:
                continue
            seen.add(patch_id)

            ci_runs += 1
            outcomes: list[GateOutcome] = []
            passed_count = 0
            failing_gate: str | None = None

            for gate in policy.get("gates", []):
                outcome = gate_runner.run(gate, candidate, policy, arch)
                outcomes.append(outcome)
                if not outcome.ok:
                    failing_gate = gate
                    break
                passed_count += 1

            if failing_gate is None and require_final_gates:
                already_run = {outcome.gate for outcome in outcomes}
                for gate in final_gate_names(case, arch):
                    if gate in already_run:
                        continue
                    outcome = gate_runner.run(gate, candidate, policy, arch)
                    outcomes.append(outcome)
                    if not outcome.ok:
                        failing_gate = gate
                        break
                    passed_count += 1

            if passed_count > best_passed_count:
                best_passed_count = passed_count
                best_patch = patch_id

            if failing_gate is None:
                return RepairResult(
                    case_id=case["case_id"],
                    description=case["description"],
                    diagnosis=diagnosis,
                    status="accepted",
                    attempts=attempts_total,
                    ci_runs=ci_runs,
                    accepted_patch=patch_id,
                    best_patch=patch_id,
                    last_failing_gate=None,
                    gate_history=symptom["gate_history"]
                    + [
                        {
                            "level": level,
                            "patch_id": patch_id,
                            "failing_gate": None,
                            "gates": [
                                {
                                    "gate": outcome.gate,
                                    "ok": outcome.ok,
                                    "metrics": outcome.metrics,
                                    "message": outcome.message,
                                }
                                for outcome in outcomes
                            ],
                        }
                    ],
                    prompts=prompts,
                    final_symptom_card=symptom,
                )

            last_failing_gate = failing_gate
            update_symptom_card(symptom, level, candidate, outcomes, failing_gate)

    status = "partial" if best_passed_count >= 3 else "failed"
    return RepairResult(
        case_id=case["case_id"],
        description=case["description"],
        diagnosis=diagnosis,
        status=status,
        attempts=attempts_total,
        ci_runs=ci_runs,
        accepted_patch=None,
        best_patch=best_patch,
        last_failing_gate=last_failing_gate,
        gate_history=symptom.get("gate_history", []),
        prompts=prompts,
        final_symptom_card=symptom,
    )


def stopped_result(
    case: dict[str, Any],
    diagnosis: Diagnosis,
    attempts_total: int,
    ci_runs: int,
    best_patch: str | None,
    best_passed_count: int,
    last_failing_gate: str | None,
    prompts: list[dict[str, str]],
    symptom: dict[str, Any],
) -> RepairResult:
    status = "partial" if best_passed_count >= 3 else "failed"
    return RepairResult(
        case_id=case["case_id"],
        description=case["description"],
        diagnosis=diagnosis,
        status=status,
        attempts=attempts_total,
        ci_runs=ci_runs,
        accepted_patch=None,
        best_patch=best_patch,
        last_failing_gate=last_failing_gate,
        gate_history=symptom.get("gate_history", []),
        prompts=prompts,
        final_symptom_card=symptom,
    )


def select_cases(cases: list[dict[str, Any]], case_id: str) -> list[dict[str, Any]]:
    if case_id == "all":
        return cases
    selected = [case for case in cases if case["case_id"] == case_id]
    if not selected:
        available = ", ".join(case["case_id"] for case in cases)
        raise SystemExit(f"Unknown case '{case_id}'. Available cases: {available}")
    return selected


def print_summary(results: list[RepairResult], verbose: bool) -> None:
    headers = ["Case", "D0", "Status", "Attempts", "CI", "Last gate"]
    rows = []
    for result in results:
        rows.append(
            [
                result.case_id,
                result.diagnosis.start_level,
                result.status,
                str(result.attempts),
                str(result.ci_runs),
                result.last_failing_gate or "-",
            ]
        )

    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    print(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))

    if verbose:
        print()
        for result in results:
            print(f"{result.case_id}: {result.description}")
            print(f"  mode: {result.diagnosis.mode}")
            print(f"  reasons: {'; '.join(result.diagnosis.reasons)}")
            if result.accepted_patch:
                print(f"  accepted patch: {result.accepted_patch}")
            elif result.best_patch:
                print(f"  best partial patch: {result.best_patch}")
            print()


def build_patch_provider(args: argparse.Namespace) -> PatchProvider:
    if args.patch_provider == "synthetic":
        return SyntheticPatchProvider()
    if args.patch_provider == "openai":
        return OpenAIPatchProvider(
            model=args.llm_model,
            max_output_tokens=args.llm_max_output_tokens,
        )
    raise SystemExit(f"Unknown patch provider: {args.patch_provider}")


def build_gate_runner(args: argparse.Namespace) -> GateRunner:
    if args.gate_runner == "synthetic":
        return SyntheticGateRunner()
    if args.gate_runner == "replay":
        return ReplayProjectGateRunner(
            workspace_root=Path(".").resolve(),
            trials_root=Path(args.replay_trials_root),
            timeout_s=args.gate_timeout_s,
        )
    if args.gate_runner == "command":
        commands = load_json(Path(args.gate_commands))
        return CommandGateRunner(
            commands=commands,
            cwd=Path(args.gate_cwd),
            timeout_s=args.gate_timeout_s,
        )
    raise SystemExit(f"Unknown gate runner: {args.gate_runner}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default="all", help="Synthetic case id or 'all'.")
    parser.add_argument("--data", default="data/synthetic_cases.json", help="Path to synthetic cases JSON.")
    parser.add_argument("--policies", default="config/policies.json", help="Path to repair policy JSON.")
    parser.add_argument(
        "--architectures",
        default="config/architecture_cards.json",
        help="Path to architecture-card JSON.",
    )
    parser.add_argument("--out", default="outputs/demo_report.json", help="Path for the JSON run report.")
    parser.add_argument(
        "--patch-provider",
        choices=["synthetic", "openai"],
        default="synthetic",
        help="Source of candidate patches.",
    )
    parser.add_argument(
        "--llm-model",
        default=DEFAULT_OPENAI_MODEL,
        help="OpenAI model for --patch-provider openai.",
    )
    parser.add_argument(
        "--llm-max-output-tokens",
        type=int,
        default=1800,
        help="Maximum output tokens for --patch-provider openai.",
    )
    parser.add_argument(
        "--gate-runner",
        choices=["synthetic", "replay", "command"],
        default="synthetic",
        help="How CI gates are evaluated.",
    )
    parser.add_argument(
        "--gate-commands",
        default="config/gate_commands.example.json",
        help="JSON map from gate name to command for --gate-runner command.",
    )
    parser.add_argument(
        "--gate-cwd",
        default=".",
        help="Working directory for --gate-runner command.",
    )
    parser.add_argument(
        "--gate-timeout-s",
        type=int,
        default=300,
        help="Timeout in seconds for each command gate.",
    )
    parser.add_argument(
        "--replay-trials-root",
        default="outputs/replay_trials",
        help="Directory for copied replay trial projects.",
    )
    parser.add_argument("--verbose", action="store_true", help="Print route reasons and patch ids.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    cases = load_json(Path(args.data))
    policies = load_json(Path(args.policies))
    architecture_cards = load_json(Path(args.architectures))
    patch_provider = build_patch_provider(args)
    gate_runner = build_gate_runner(args)

    results = [
        run_case(
            case,
            policies,
            architecture_cards,
            patch_provider=patch_provider,
            gate_runner=gate_runner,
        )
        for case in select_cases(cases, args.case)
    ]
    report = {
        "summary": {
            "cases": len(results),
            "accepted": sum(1 for result in results if result.status == "accepted"),
            "partial": sum(1 for result in results if result.status == "partial"),
            "failed": sum(1 for result in results if result.status == "failed"),
            "ci_runs": sum(result.ci_runs for result in results),
            "patch_provider": patch_provider.name,
            "gate_runner": gate_runner.name,
        },
        "results": [result.to_jsonable() for result in results],
    }
    write_json(Path(args.out), report)
    print_summary(results, args.verbose)
    print(f"\nWrote report: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
