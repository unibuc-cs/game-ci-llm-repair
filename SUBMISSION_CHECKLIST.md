# Offline Submission Checklist

This checklist summarizes the current offline submission state. It is intended
for a reviewer or collaborator who wants to verify what is implemented without
OpenAI credentials or game-engine installations.

## Status

| Item | Status | Evidence |
| --- | --- | --- |
| Runnable offline demo | Done | `python run_demo.py` |
| Replayable synthetic CI gates | Done | `synthetic_project/`, `ReplayProjectGateRunner` |
| T0 local repair case | Done | `D-SpeedLimitClamp` accepted at T0 |
| T1 cross-file repair case | Done | `A-CrosswalkDesync` accepted at T1 |
| T2 performance/invariant repair case | Done | `B-BrakeOscillation` accepted after one failed perf attempt |
| T3 visual-scripting repair case | Done | `C-FourWayDeadlock` reaches partial with invariant failure |
| Policy-scoped prompts | Done | Prompt snapshots in `outputs/demo_report.json` |
| Architecture Card constraints | Done | `config/architecture_cards.json` |
| Symptom Card updates after gates | Done | `gate_history` and final cards in `outputs/demo_report.json` |
| Ablation evaluation | Done | `python evaluate.py`, `outputs/eval_summary.csv` |
| Static dashboards | Done | `outputs/dashboard.html`, `outputs/eval_dashboard.html` |
| Paper traceability matrix | Done | `docs/paper_traceability.md` |
| Demo script | Done | `DEMO.md` |
| Real-project integration notes | Done | `docs/real_project_integration.md` |
| GitHub Actions CI | Done | `.github/workflows/ci.yml` |
| Submission verifier | Done | `python tools/verify_artifact.py` |
| GPT-5.5 live smoke path | Wired, not executed here | `tools/gpt55_smoke.py`, blocked by missing `OPENAI_API_KEY` |

## Expected Offline Results

Run:

```powershell
python run_demo.py
```

Expected route/status summary:

```text
D-SpeedLimitClamp   T0  accepted
A-CrosswalkDesync   T1  accepted
B-BrakeOscillation  T2  accepted
C-FourWayDeadlock   T3  partial
```

Run:

```powershell
python evaluate.py
```

Expected evaluation summary:

```text
governed       3 accepted, 1 partial, 5 CI runs
fixed_ladder   3 accepted, 1 partial, 12 CI runs
broad_context  0 accepted, 2 partial, 2 failed
single_attempt 2 accepted, 1 partial, 1 failed
no_arch_card   2 accepted, 1 partial, 1 failed
```

Run:

```powershell
python tools/verify_artifact.py
```

Expected final line:

```text
Submission readiness passed.
```

## What Is Still Credential-Blocked

The only major evidence not produced in this environment is a live GPT-5.5
repair result. The implementation path exists and has a preflight check, but it
requires `OPENAI_API_KEY`.

Command to run when credentials are available:

```powershell
$env:OPENAI_API_KEY = "..."
python tools/gpt55_smoke.py
```

If it succeeds, commit either the generated smoke report/dashboard or a short
result note under `docs/`.

## Reviewer Path

Use this order for a clean offline review:

1. Read `docs/paper_traceability.md`.
2. Run `python run_demo.py`.
3. Open `outputs/dashboard.html`.
4. Run `python evaluate.py`.
5. Open `outputs/eval_dashboard.html`.
6. Run `python tools/verify_artifact.py`.
7. Inspect `DEMO.md` for the presentation flow.
