"""Verify that the demo artifact satisfies the current submission checklist."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Check:
    label: str
    verify: Callable[[], None]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_eval_rows(path: Path) -> dict[str, dict[str, str]]:
    return load_csv_rows(path, "mode")


def load_csv_rows(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return {row[key]: row for row in csv.DictReader(fh)}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def path_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def build_checks(args: argparse.Namespace) -> list[Check]:
    demo_report_path = ROOT / args.demo_report
    eval_summary_path = ROOT / args.eval_summary
    eval_report_path = ROOT / args.eval_report
    required_paths = [
        ROOT / "outputs/dashboard.html",
        ROOT / "outputs/eval_dashboard.html",
        ROOT / "outputs/human_supervision_summary.csv",
        ROOT / "outputs/maintainability_summary.csv",
        demo_report_path,
        eval_summary_path,
        eval_report_path,
        ROOT / "schemas/policy.schema.json",
        ROOT / "schemas/architecture_card.schema.json",
        ROOT / "schemas/symptom_card.schema.json",
        ROOT / "schemas/code_context.schema.json",
        ROOT / "schemas/README.md",
        ROOT / "docs/paper_traceability.md",
        ROOT / "docs/gpt55_smoke_test.md",
        ROOT / "docs/real_project_integration.md",
        ROOT / "SUBMISSION_CHECKLIST.md",
        ROOT / "DEMO.md",
        ROOT / ".github/workflows/ci.yml",
        ROOT / "tools/gpt55_smoke.py",
        ROOT / "tools/verify_artifact.py",
    ]

    def check_required_paths() -> None:
        missing = [str(path.relative_to(ROOT)) for path in required_paths if not path.exists()]
        require(not missing, f"missing required files: {missing}")
        empty = [str(path.relative_to(ROOT)) for path in required_paths if path_size(path) == 0]
        require(not empty, f"empty required files: {empty}")

    def check_demo_summary() -> None:
        report = load_json(demo_report_path)
        summary = report["summary"]
        require(summary["cases"] == 4, f"expected 4 demo cases, got {summary['cases']}")
        require(summary["accepted"] == 3, f"expected 3 accepted demo cases, got {summary['accepted']}")
        require(summary["partial"] == 1, f"expected 1 partial demo case, got {summary['partial']}")
        require(summary["failed"] == 0, f"expected 0 failed demo cases, got {summary['failed']}")
        require(summary["gate_runner"] == "replay", f"expected replay gate runner, got {summary['gate_runner']}")
        require(summary["patch_provider"] == "synthetic", f"expected synthetic provider, got {summary['patch_provider']}")

    def check_routes() -> None:
        report = load_json(demo_report_path)
        routes = {
            result["case_id"]: result["diagnosis"]["start_level"]
            for result in report["results"]
        }
        expected = {
            "D-SpeedLimitClamp": "T0",
            "A-CrosswalkDesync": "T1",
            "B-BrakeOscillation": "T2",
            "C-FourWayDeadlock": "T3",
        }
        require(routes == expected, f"unexpected D0 routes: {routes}")

    def check_case_outcomes() -> None:
        report = load_json(demo_report_path)
        outcomes = {result["case_id"]: result for result in report["results"]}
        require(outcomes["D-SpeedLimitClamp"]["status"] == "accepted", "T0 case was not accepted")
        require(outcomes["A-CrosswalkDesync"]["status"] == "accepted", "T1 case was not accepted")
        require(outcomes["B-BrakeOscillation"]["status"] == "accepted", "T2 case was not accepted")
        require(outcomes["B-BrakeOscillation"]["attempts"] == 2, "T2 case should demonstrate retry")
        require(outcomes["C-FourWayDeadlock"]["status"] == "partial", "T3 case should remain partial")
        require(
            outcomes["C-FourWayDeadlock"]["last_failing_gate"] == "invariants",
            "T3 case should fail at invariants",
        )

    def check_eval_summary() -> None:
        rows = load_eval_rows(eval_summary_path)
        required_modes = {
            "governed",
            "B0_single_prompt",
            "B1_multi_attempt_prompt",
            "B2_tool_agent",
            "B3_broad_context_agent",
            "fixed_ladder",
            "broad_context",
            "single_attempt",
            "no_arch_card",
        }
        missing_modes = sorted(required_modes - set(rows))
        require(not missing_modes, f"missing eval modes: {missing_modes}")

        governed = rows["governed"]
        fixed = rows["fixed_ladder"]
        require(governed["cases"] == "4", f"expected 4 governed cases, got {governed['cases']}")
        require(governed["accepted"] == "3", f"expected governed accepted=3, got {governed['accepted']}")
        require(governed["partial"] == "1", f"expected governed partial=1, got {governed['partial']}")
        require(governed["failed"] == "0", f"expected governed failed=0, got {governed['failed']}")
        require(int(fixed["ci_runs"]) > int(governed["ci_runs"]), "fixed ladder should use more CI runs")
        require(int(fixed["attempts"]) > int(governed["attempts"]), "fixed ladder should use more attempts")

    def check_ablation_degradation() -> None:
        rows = load_eval_rows(eval_summary_path)
        governed_accepted = int(rows["governed"]["accepted"])
        for mode in ["B0_single_prompt", "B1_multi_attempt_prompt", "B3_broad_context_agent", "broad_context", "no_arch_card"]:
            accepted = int(rows[mode]["accepted"])
            failed = int(rows[mode]["failed"])
            require(accepted < governed_accepted, f"{mode} should accept fewer cases than governed")
            require(failed > 0, f"{mode} should have at least one failed case")
        require(
            int(rows["B2_tool_agent"]["ci_runs"]) > int(rows["governed"]["ci_runs"]),
            "B2 tool-agent baseline should use more CI runs than governed",
        )

    def check_human_supervision_summary() -> None:
        rows = load_csv_rows(ROOT / "outputs/human_supervision_summary.csv", "condition")
        expected = {
            "file_scope_confirmation_only",
            "bounded_hints",
            "bounded_hints_and_escalation_approval",
        }
        require(set(rows) == expected, f"unexpected supervision rows: {sorted(rows)}")
        require(
            int(rows["bounded_hints_and_escalation_approval"]["escalation_reviews"]) > 0,
            "escalation approval row should record broad-scope reviews",
        )

    def check_maintainability_summary() -> None:
        rows = load_csv_rows(ROOT / "outputs/maintainability_summary.csv", "engine")
        require("Unity" in rows, f"maintainability summary missing Unity row: {sorted(rows)}")
        require("UE5" in rows, f"maintainability summary missing UE5 row: {sorted(rows)}")
        require(
            int(rows["Unity"]["accepted_patches"]) >= 3,
            "Unity maintainability summary should cover accepted synthetic patches",
        )

    def check_eval_report_metadata() -> None:
        report = load_json(eval_report_path)
        metadata = report["metadata"]
        require(metadata["patch_provider"] == "synthetic", "evaluation should use synthetic provider")
        require(metadata["gate_runner"] == "replay", "evaluation should use replay gate runner")
        require(len(metadata["cases"]) == 4, f"expected 4 evaluated cases, got {metadata['cases']}")

    def check_ci_uses_verifier() -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        require("python tools/verify_artifact.py" in workflow, "CI workflow does not run verify_artifact.py")

    return [
        Check("required reports, dashboards, docs, and scripts exist", check_required_paths),
        Check("demo summary matches expected replay outcome", check_demo_summary),
        Check("D0 routes cover T0, T1, T2, and T3", check_routes),
        Check("case outcomes demonstrate accepted, retry, and partial repair", check_case_outcomes),
        Check("evaluation summary matches governed baseline expectations", check_eval_summary),
        Check("B0-B3 baselines and ablations differ from governed mode", check_ablation_degradation),
        Check("human-supervision summary exists and records escalation reviews", check_human_supervision_summary),
        Check("maintainability summary exists for accepted patches", check_maintainability_summary),
        Check("evaluation report metadata matches offline replay setup", check_eval_report_metadata),
        Check("GitHub Actions workflow runs artifact verifier", check_ci_uses_verifier),
    ]


def run_checks(checks: list[Check]) -> int:
    failures = 0
    for check in checks:
        try:
            check.verify()
        except Exception as exc:
            failures += 1
            print(f"[FAIL] {check.label}: {exc}")
        else:
            print(f"[OK] {check.label}")
    if failures:
        print(f"\nSubmission readiness failed: {failures} check(s) failed.")
        return 1
    print("\nSubmission readiness passed.")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-report", default="outputs/demo_report.json")
    parser.add_argument("--eval-report", default="outputs/eval_results.json")
    parser.add_argument("--eval-summary", default="outputs/eval_summary.csv")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    return run_checks(build_checks(args))


if __name__ == "__main__":
    raise SystemExit(main())
