"""Run the repair demo and regenerate the static dashboard."""

from __future__ import annotations

import argparse
from pathlib import Path

import dashboard
import orchestrator


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default="all", help="Synthetic case id or 'all'.")
    parser.add_argument("--report", default="outputs/demo_report.json", help="JSON report path.")
    parser.add_argument("--dashboard", default="outputs/dashboard.html", help="HTML dashboard path.")
    parser.add_argument(
        "--patch-provider",
        choices=["synthetic", "openai"],
        default="synthetic",
        help="Source of candidate patches.",
    )
    parser.add_argument(
        "--llm-model",
        default=orchestrator.DEFAULT_OPENAI_MODEL,
        help="OpenAI model for --patch-provider openai.",
    )
    parser.add_argument(
        "--gate-runner",
        choices=["synthetic", "command"],
        default="synthetic",
        help="How CI gates are evaluated.",
    )
    parser.add_argument(
        "--gate-commands",
        default="config/gate_commands.example.json",
        help="JSON map from gate name to command for --gate-runner command.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    orchestrator_args = [
        "--case",
        args.case,
        "--out",
        args.report,
        "--patch-provider",
        args.patch_provider,
        "--llm-model",
        args.llm_model,
        "--gate-runner",
        args.gate_runner,
        "--gate-commands",
        args.gate_commands,
        "--verbose",
    ]
    orchestrator.main(orchestrator_args)
    dashboard.write_dashboard(Path(args.report), Path(args.dashboard))
    print(f"Wrote dashboard: {args.dashboard}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
