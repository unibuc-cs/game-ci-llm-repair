"""Run one live GPT-5.5 repair smoke test against the replay fixture."""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import dashboard  # noqa: E402
import orchestrator  # noqa: E402


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        default="D-SpeedLimitClamp",
        help="Synthetic case id for the smoke test.",
    )
    parser.add_argument(
        "--model",
        default=orchestrator.DEFAULT_OPENAI_MODEL,
        help="OpenAI model used for candidate generation.",
    )
    parser.add_argument(
        "--out",
        default="outputs/gpt55_smoke_report.json",
        help="JSON report path.",
    )
    parser.add_argument(
        "--dashboard",
        default="outputs/gpt55_smoke_dashboard.html",
        help="HTML dashboard path.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=1800,
        help="Maximum output tokens for the candidate patch response.",
    )
    return parser


def preflight() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set; live GPT-5.5 smoke test was not run.", file=sys.stderr)
        return 2
    if importlib.util.find_spec("openai") is None:
        print("The 'openai' package is not installed; run: pip install openai", file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    preflight_status = preflight()
    if preflight_status:
        return preflight_status

    orchestrator.main(
        [
            "--case",
            args.case,
            "--patch-provider",
            "openai",
            "--llm-model",
            args.model,
            "--llm-max-output-tokens",
            str(args.max_output_tokens),
            "--gate-runner",
            "replay",
            "--out",
            args.out,
            "--verbose",
        ]
    )
    dashboard.write_dashboard(Path(args.out), Path(args.dashboard))
    print(f"Wrote dashboard: {args.dashboard}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
