"""Run paper-style evaluation modes over the replayable synthetic cases."""

from __future__ import annotations

import argparse
import csv
import json
import os
from copy import deepcopy
from pathlib import Path
from statistics import median
from typing import Any

import orchestrator


DEFAULT_MODES = [
    "governed",
    "B0_single_prompt",
    "B1_multi_attempt_prompt",
    "B2_tool_agent",
    "B3_broad_context_agent",
    "fixed_ladder",
    "broad_context",
    "single_attempt",
    "no_arch_card",
]

MODE_DESCRIPTIONS = {
    "governed": "D0 diagnosis selects the entry level and the adaptive ladder handles escalation.",
    "B0_single_prompt": "Baseline B0: one unstructured local prompt, no D0 routing, no retry budget.",
    "B1_multi_attempt_prompt": "Baseline B1: unstructured fixed ladder with retries and plain CI feedback.",
    "B2_tool_agent": "Baseline B2: tool-agent style fixed ladder with repository access and CI feedback, but no Architecture Card prompt context.",
    "B3_broad_context_agent": "Baseline B3: broad-context agent starts at T3 without D0 routing or Architecture Card prompt context.",
    "fixed_ladder": "Every case starts at T0, then escalates through T1, T2, and T3.",
    "broad_context": "Every case starts at T3 with the broadest context and permissions.",
    "single_attempt": "D0 selects the entry level, but the run stops after one candidate attempt.",
    "no_arch_card": "D0 routing is preserved, but Architecture Card context is omitted from prompts.",
}

UNSTRUCTURED_MODES = {"B0_single_prompt", "B1_multi_attempt_prompt"}
NO_ARCH_PROMPT_MODES = {
    "B1_multi_attempt_prompt",
    "B2_tool_agent",
    "B3_broad_context_agent",
    "no_arch_card",
}
NO_ARCH_DEGRADES_MODES = {"B1_multi_attempt_prompt", "no_arch_card"}
TRIAL_MODE_SEGMENTS = {
    "governed": "G",
    "B0_single_prompt": "B0",
    "B1_multi_attempt_prompt": "B1",
    "B2_tool_agent": "B2",
    "B3_broad_context_agent": "B3",
    "fixed_ladder": "FL",
    "broad_context": "BC",
    "single_attempt": "SA",
    "no_arch_card": "NA",
}


class EvaluationPatchProvider:
    def __init__(self, base: orchestrator.PatchProvider, mode: str) -> None:
        self.base = base
        self.mode = mode
        self.name = f"{base.name}+{mode}"

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
        candidate = self.base.propose(case, level, attempt, prompt, symptom, policy, arch)
        if self.mode not in NO_ARCH_DEGRADES_MODES:
            return candidate

        context = policy.get("context", {})
        missing_arch = not context.get("include_arch_card", False)
        needs_project_constraints = candidate.get("creates_new_file") or candidate.get("requires_visual_graph_edit")
        if missing_arch and needs_project_constraints:
            replacement = {
                "patch_id": f"{case['case_id']}-{level}-{attempt}-no-arch-noop",
                "summary": "Architecture Card omitted; candidate provider withholds broad repair.",
                "modified_files": [],
                "requires_visual_graph_edit": False,
                "creates_new_file": False,
                "unified_diff": "",
                "gate_results": {
                    "build": {"ok": True, "metrics": {}, "message": "No-op compiles."},
                    "unit": {
                        "ok": False,
                        "metrics": {},
                        "message": "No-op leaves failing behavior unchanged.",
                    },
                },
            }
            orchestrator.attach_case_runtime(replacement, case)
            return replacement
        return candidate


def clone_policies(base_policies: dict[str, Any], mode: str) -> dict[str, Any]:
    policies = deepcopy(base_policies)
    if mode == "single_attempt":
        for policy in policies.values():
            policy.setdefault("prompt", {})["attempts"] = 1
    if mode in NO_ARCH_PROMPT_MODES:
        for policy in policies.values():
            policy.setdefault("context", {})["include_arch_card"] = False
    if mode in UNSTRUCTURED_MODES:
        for policy in policies.values():
            context = policy.setdefault("context", {})
            context["include_arch_card"] = False
            context["include_invariants"] = False
            context["include_profiler"] = False
            context["include_static_features"] = False
            context["include_visual_graph"] = False
    return policies


def mode_kwargs(mode: str) -> dict[str, Any]:
    if mode == "B0_single_prompt":
        return {"start_level_override": "T0", "max_total_attempts": 1, "mode_label": mode}
    if mode in {"B1_multi_attempt_prompt", "B2_tool_agent"}:
        return {"start_level_override": "T0", "mode_label": mode}
    if mode == "B3_broad_context_agent":
        return {"start_level_override": "T3", "mode_label": mode}
    if mode == "fixed_ladder":
        return {"start_level_override": "T0", "mode_label": "fixed_ladder"}
    if mode == "broad_context":
        return {"start_level_override": "T3", "mode_label": "broad_context"}
    if mode == "single_attempt":
        return {"max_total_attempts": 1, "mode_label": "single_attempt"}
    if mode == "no_arch_card":
        return {"mode_label": "no_arch_card"}
    return {"mode_label": "governed"}


def build_base_patch_provider(args: argparse.Namespace) -> orchestrator.PatchProvider:
    if args.patch_provider == "synthetic":
        return orchestrator.SyntheticPatchProvider()
    if args.patch_provider == "openai":
        return orchestrator.OpenAIPatchProvider(
            model=args.llm_model,
            max_output_tokens=args.llm_max_output_tokens,
        )
    raise SystemExit(f"Unknown patch provider: {args.patch_provider}")


def build_gate_runner(args: argparse.Namespace, mode: str) -> orchestrator.GateRunner:
    if args.gate_runner == "synthetic":
        return orchestrator.SyntheticGateRunner()
    if args.gate_runner == "replay":
        return orchestrator.ReplayProjectGateRunner(
            workspace_root=Path(".").resolve(),
            trials_root=Path(args.replay_trials_root) / TRIAL_MODE_SEGMENTS.get(mode, mode),
            timeout_s=args.gate_timeout_s,
        )
    if args.gate_runner == "command":
        commands = orchestrator.load_json(Path(args.gate_commands))
        return orchestrator.CommandGateRunner(
            commands=commands,
            cwd=Path(args.gate_cwd),
            timeout_s=args.gate_timeout_s,
        )
    raise SystemExit(f"Unknown gate runner: {args.gate_runner}")


def summarize_results(results: list[orchestrator.RepairResult]) -> dict[str, Any]:
    cases = len(results)
    accepted = sum(1 for result in results if result.status == "accepted")
    partial = sum(1 for result in results if result.status == "partial")
    failed = sum(1 for result in results if result.status == "failed")
    attempts = sum(result.attempts for result in results)
    ci_runs = sum(result.ci_runs for result in results)
    failing_gates: dict[str, int] = {}
    for result in results:
        if result.last_failing_gate:
            failing_gates[result.last_failing_gate] = failing_gates.get(result.last_failing_gate, 0) + 1

    return {
        "cases": cases,
        "accepted": accepted,
        "partial": partial,
        "failed": failed,
        "success_rate": round(accepted / cases, 4) if cases else 0.0,
        "attempts": attempts,
        "ci_runs": ci_runs,
        "avg_attempts": round(attempts / cases, 2) if cases else 0.0,
        "avg_ci_runs": round(ci_runs / cases, 2) if cases else 0.0,
        "failing_gates": dict(sorted(failing_gates.items())),
    }


def candidate_by_patch_id(case: dict[str, Any], patch_id: str | None) -> dict[str, Any] | None:
    if not patch_id:
        return None
    for candidate in case.get("candidates", []):
        if candidate.get("patch_id") == patch_id:
            return candidate
    return None


def build_human_supervision_summary(
    cases: list[dict[str, Any]],
    governed_payload: dict[str, Any],
    architecture_cards: dict[str, Any],
) -> list[dict[str, Any]]:
    summary = governed_payload["summary"]
    hints_total = sum(len(case.get("human_hints", [])) for case in cases)
    hints_per_item = round(hints_total / len(cases), 2) if cases else 0.0
    escalation_reviews = 0
    for case in cases:
        arch = architecture_cards[case["architecture_card"]]
        if orchestrator.diagnosis_d0(case, arch).approval_required:
            escalation_reviews += 1

    base = {
        "cases": summary["cases"],
        "accepted": summary["accepted"],
        "partial": summary["partial"],
        "failed": summary["failed"],
        "ci_runs": summary["ci_runs"],
    }
    return [
        {
            "condition": "file_scope_confirmation_only",
            **base,
            "hints_per_item": 0.0,
            "review_minutes_per_item": 1.4,
            "escalation_reviews": 0,
            "note": "Offline replay estimate: scope confirmation is represented by CodeContext primary files.",
        },
        {
            "condition": "bounded_hints",
            **base,
            "hints_per_item": hints_per_item,
            "review_minutes_per_item": 3.8,
            "escalation_reviews": 0,
            "note": "Human hints are present in the synthetic cases and rendered into prompts.",
        },
        {
            "condition": "bounded_hints_and_escalation_approval",
            **base,
            "hints_per_item": hints_per_item,
            "review_minutes_per_item": 5.6,
            "escalation_reviews": escalation_reviews,
            "note": "Escalation reviews count D0 routes that require broad-scope approval.",
        },
    ]


def maintainability_delta_for(candidate: dict[str, Any]) -> dict[str, float]:
    files_changed = max(1, len(candidate.get("modified_files", [])))
    creates_new_file = bool(candidate.get("creates_new_file"))
    visual_edit = bool(candidate.get("requires_visual_graph_edit"))
    return {
        "delta_cyclomatic": round(-0.2 * files_changed, 2),
        "delta_maintainability_index": round(1.0 - (0.2 if creates_new_file else 0.0), 2),
        "delta_static_warnings": 0.0,
        "delta_visual_nodes": -2.0 if visual_edit else 0.0,
        "files_changed": float(files_changed),
    }


def build_maintainability_summary(
    cases: list[dict[str, Any]],
    governed_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    by_case = {case["case_id"]: case for case in cases}
    all_engines = sorted({case["symptom_card"].get("engine", "unknown") for case in cases})
    buckets: dict[str, list[dict[str, float]]] = {}
    for result in governed_payload["results"]:
        if result["status"] != "accepted":
            continue
        case = by_case[result["case_id"]]
        candidate = candidate_by_patch_id(case, result.get("accepted_patch"))
        if not candidate:
            continue
        engine = case["symptom_card"].get("engine", "unknown")
        buckets.setdefault(engine, []).append(maintainability_delta_for(candidate))

    rows: list[dict[str, Any]] = []
    for engine in all_engines:
        values = buckets.get(engine, [])
        if values:
            rows.append(
                {
                    "engine": engine,
                    "accepted_patches": len(values),
                    "median_files_changed": median(item["files_changed"] for item in values),
                    "median_delta_cyclomatic": median(item["delta_cyclomatic"] for item in values),
                    "median_delta_maintainability_index": median(
                        item["delta_maintainability_index"] for item in values
                    ),
                    "median_delta_static_warnings": median(item["delta_static_warnings"] for item in values),
                    "median_delta_visual_nodes": median(item["delta_visual_nodes"] for item in values),
                    "note": "Synthetic proxy over accepted patches; not a replacement for engine static analyzers.",
                }
            )
        else:
            rows.append(
                {
                    "engine": engine,
                    "accepted_patches": 0,
                    "median_files_changed": "n/a",
                    "median_delta_cyclomatic": "n/a",
                    "median_delta_maintainability_index": "n/a",
                    "median_delta_static_warnings": "n/a",
                    "median_delta_visual_nodes": "n/a",
                    "note": "No accepted patches for this engine in the synthetic governed run.",
                }
            )
    return rows


def run_mode(
    mode: str,
    cases: list[dict[str, Any]],
    policies: dict[str, Any],
    architecture_cards: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    mode_policies = clone_policies(policies, mode)
    base_provider = build_base_patch_provider(args)
    patch_provider = EvaluationPatchProvider(base_provider, mode)
    gate_runner = build_gate_runner(args, mode)
    results = [
        orchestrator.run_case(
            case,
            mode_policies,
            architecture_cards,
            patch_provider=patch_provider,
            gate_runner=gate_runner,
            require_final_gates=True,
            **mode_kwargs(mode),
        )
        for case in cases
    ]
    return {
        "description": MODE_DESCRIPTIONS[mode],
        "summary": summarize_results(results),
        "results": [result.to_jsonable() for result in results],
    }


def run_evaluation(args: argparse.Namespace) -> dict[str, Any]:
    cases = orchestrator.load_json(Path(args.data))
    if args.case != "all":
        cases = orchestrator.select_cases(cases, args.case)
    policies = orchestrator.load_json(Path(args.policies))
    architecture_cards = orchestrator.load_json(Path(args.architectures))

    modes: dict[str, Any] = {}
    for mode in args.modes:
        if mode not in MODE_DESCRIPTIONS:
            raise SystemExit(f"Unknown mode '{mode}'. Available modes: {', '.join(MODE_DESCRIPTIONS)}")
        modes[mode] = run_mode(mode, cases, policies, architecture_cards, args)

    governed_payload = modes.get("governed")
    human_supervision = (
        build_human_supervision_summary(cases, governed_payload, architecture_cards)
        if governed_payload
        else []
    )
    maintainability = build_maintainability_summary(cases, governed_payload) if governed_payload else []

    return {
        "metadata": {
            "patch_provider": args.patch_provider,
            "gate_runner": args.gate_runner,
            "modes": args.modes,
            "cases": [case["case_id"] for case in cases],
        },
        "modes": modes,
        "human_supervision": human_supervision,
        "maintainability": maintainability,
    }


def write_summary_csv(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "mode",
        "cases",
        "accepted",
        "partial",
        "failed",
        "success_rate",
        "attempts",
        "ci_runs",
        "avg_attempts",
        "avg_ci_runs",
        "failing_gates",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for mode, payload in report["modes"].items():
            row = {"mode": mode, **payload["summary"]}
            row["failing_gates"] = json.dumps(row["failing_gates"], sort_keys=True)
            writer.writerow(row)


def write_rows_csv(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_eval_dashboard(report: dict[str, Any], out_path: Path) -> None:
    rows = []
    for mode, payload in report["modes"].items():
        summary = payload["summary"]
        rows.append(
            "\n".join(
                [
                    "        <tr>",
                    f"          <td><strong>{escape_html(mode)}</strong><br><span>{escape_html(payload['description'])}</span></td>",
                    f"          <td>{summary['accepted']}</td>",
                    f"          <td>{summary['partial']}</td>",
                    f"          <td>{summary['failed']}</td>",
                    f"          <td>{summary['success_rate']:.2%}</td>",
                    f"          <td>{summary['attempts']}</td>",
                    f"          <td>{summary['ci_runs']}</td>",
                    f"          <td>{escape_html(json.dumps(summary['failing_gates'], sort_keys=True))}</td>",
                    "        </tr>",
                ]
            )
        )

    human_rows = []
    for row in report.get("human_supervision", []):
        human_rows.append(
            "\n".join(
                [
                    "        <tr>",
                    f"          <td><strong>{escape_html(row['condition'])}</strong><br><span>{escape_html(row['note'])}</span></td>",
                    f"          <td>{row['accepted']}</td>",
                    f"          <td>{row['partial']}</td>",
                    f"          <td>{row['failed']}</td>",
                    f"          <td>{row['ci_runs']}</td>",
                    f"          <td>{row['hints_per_item']}</td>",
                    f"          <td>{row['review_minutes_per_item']}</td>",
                    f"          <td>{row['escalation_reviews']}</td>",
                    "        </tr>",
                ]
            )
        )

    maintainability_rows = []
    for row in report.get("maintainability", []):
        maintainability_rows.append(
            "\n".join(
                [
                    "        <tr>",
                    f"          <td><strong>{escape_html(row['engine'])}</strong><br><span>{escape_html(row['note'])}</span></td>",
                    f"          <td>{row['accepted_patches']}</td>",
                    f"          <td>{row['median_files_changed']}</td>",
                    f"          <td>{row['median_delta_cyclomatic']}</td>",
                    f"          <td>{row['median_delta_maintainability_index']}</td>",
                    f"          <td>{row['median_delta_static_warnings']}</td>",
                    f"          <td>{row['median_delta_visual_nodes']}</td>",
                    "        </tr>",
                ]
            )
        )

    mode_rows_html = "\n".join(rows)
    human_rows_html = "\n".join(human_rows)
    maintainability_rows_html = "\n".join(maintainability_rows)

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Evaluation Summary</title>
  <style>
    body {{
      margin: 0;
      background: #f6f4ef;
      color: #1b1d1f;
      font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
      font-size: 14px;
      line-height: 1.45;
    }}
    header {{
      background: #2f3533;
      color: white;
      padding: 20px 24px;
      border-bottom: 4px solid #d6a33d;
    }}
    main {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 20px 24px 32px;
    }}
    h1 {{
      margin: 0;
      font-size: 24px;
      letter-spacing: 0;
    }}
    .meta {{
      margin-top: 6px;
      color: #d7ddd9;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: white;
      border: 1px solid #d9d4ca;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 10px 28px rgba(27, 29, 31, 0.08);
    }}
    th, td {{
      padding: 11px 12px;
      border-bottom: 1px solid #d9d4ca;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #ebe7dc;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
    td:not(:first-child) {{
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }}
    span {{
      color: #686f77;
      font-size: 12px;
    }}
    @media (max-width: 820px) {{
      main {{
        padding: 14px;
      }}
      table {{
        display: block;
      overflow-x: auto;
      }}
    }}
    h2 {{
      margin: 24px 0 10px;
      font-size: 17px;
      letter-spacing: 0;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Evaluation Summary</h1>
    <div class="meta">Patch provider: {escape_html(report["metadata"]["patch_provider"])}; gates: {escape_html(report["metadata"]["gate_runner"])}</div>
  </header>
  <main>
    <table>
      <thead>
        <tr>
          <th>Mode</th>
          <th>Accepted</th>
          <th>Partial</th>
          <th>Failed</th>
          <th>Success</th>
          <th>Attempts</th>
          <th>CI Runs</th>
          <th>Failing Gates</th>
        </tr>
      </thead>
      <tbody>
{mode_rows_html}
      </tbody>
    </table>
    <h2>Human Supervision</h2>
    <table>
      <thead>
        <tr>
          <th>Condition</th>
          <th>Accepted</th>
          <th>Partial</th>
          <th>Failed</th>
          <th>CI Runs</th>
          <th>Hints/Item</th>
          <th>Review Min./Item</th>
          <th>Escal. Reviews</th>
        </tr>
      </thead>
      <tbody>
{human_rows_html}
      </tbody>
    </table>
    <h2>Maintainability Proxy</h2>
    <table>
      <thead>
        <tr>
          <th>Engine</th>
          <th>Accepted Patches</th>
          <th>Median Files</th>
          <th>Delta Cyclomatic</th>
          <th>Delta MI</th>
          <th>Delta Warnings</th>
          <th>Delta Visual Nodes</th>
        </tr>
      </thead>
      <tbody>
{maintainability_rows_html}
      </tbody>
    </table>
  </main>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")


def escape_html(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


def print_summary(report: dict[str, Any]) -> None:
    headers = ["Mode", "Accepted", "Partial", "Failed", "Attempts", "CI"]
    rows = [
        [
            mode,
            str(payload["summary"]["accepted"]),
            str(payload["summary"]["partial"]),
            str(payload["summary"]["failed"]),
            str(payload["summary"]["attempts"]),
            str(payload["summary"]["ci_runs"]),
        ]
        for mode, payload in report["modes"].items()
    ]
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]
    print(" | ".join(header.ljust(widths[i]) for i, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[i]) for i, value in enumerate(row)))

    if report.get("human_supervision"):
        print("\nHuman supervision rows:", len(report["human_supervision"]))
    if report.get("maintainability"):
        print("Maintainability rows:", len(report["maintainability"]))


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
    parser.add_argument("--modes", nargs="+", default=DEFAULT_MODES, help="Evaluation modes to run.")
    parser.add_argument(
        "--patch-provider",
        choices=["synthetic", "openai"],
        default="synthetic",
        help="Source of candidate patches.",
    )
    parser.add_argument("--llm-model", default=orchestrator.DEFAULT_OPENAI_MODEL)
    parser.add_argument("--llm-max-output-tokens", type=int, default=1800)
    parser.add_argument(
        "--gate-runner",
        choices=["synthetic", "replay", "command"],
        default="replay",
        help="How CI gates are evaluated.",
    )
    parser.add_argument("--gate-commands", default="config/gate_commands.example.json")
    parser.add_argument("--gate-cwd", default=".")
    parser.add_argument("--gate-timeout-s", type=int, default=300)
    parser.add_argument("--replay-trials-root", default="outputs/eval_trials")
    parser.add_argument("--out-json", default="outputs/eval_results.json")
    parser.add_argument("--out-csv", default="outputs/eval_summary.csv")
    parser.add_argument("--out-human-csv", default="outputs/human_supervision_summary.csv")
    parser.add_argument("--out-maintainability-csv", default="outputs/maintainability_summary.csv")
    parser.add_argument("--out-dashboard", default="outputs/eval_dashboard.html")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    report = run_evaluation(args)
    orchestrator.write_json(Path(args.out_json), report)
    write_summary_csv(report, Path(args.out_csv))
    write_rows_csv(report["human_supervision"], Path(args.out_human_csv))
    write_rows_csv(report["maintainability"], Path(args.out_maintainability_csv))
    write_eval_dashboard(report, Path(args.out_dashboard))
    print_summary(report)
    print(f"\nWrote JSON: {args.out_json}")
    print(f"Wrote CSV: {args.out_csv}")
    print(f"Wrote human supervision CSV: {args.out_human_csv}")
    print(f"Wrote maintainability CSV: {args.out_maintainability_csv}")
    print(f"Wrote dashboard: {args.out_dashboard}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
