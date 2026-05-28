# Artifact Guide: Governed LLM Repair Prototype

This guide describes the offline artifact for `v0.1-paper-demo`.

Repository: `https://github.com/unibuc-cs/game-ci-llm-repair`  
Artifact tag: `v0.1-paper-demo`  
Artifact commit: `c8895b4 Add accepted UE5 replay case`

## What This Artifact Demonstrates

The prototype implements a minimal runnable version of the paper workflow:

- D0 diagnosis routes bugs into T0, T1, T2, or T3.
- Policy-scoped prompts expose only the evidence allowed at the active repair level.
- Candidate patches are checked by replayable CI gates.
- Synthetic Unity and UE5 cases cover local, cross-file, performance/invariant, and visual-scripting repairs.
- B0-B3 paper baselines and ablations are evaluated under the same replay gates.
- Human-supervision and maintainability proxy summaries are generated offline.

## Setup

Use Python 3.11 or newer. No Unity editor, UE5 editor, OpenAI key, or external package install is required for the offline path.

```powershell
git clone https://github.com/unibuc-cs/game-ci-llm-repair.git
cd game-ci-llm-repair
git checkout v0.1-paper-demo
```

## Required Commands

Run the replay demo:

```powershell
python run_demo.py
```

Expected summary:

```text
D-SpeedLimitClamp    T0  accepted
A-CrosswalkDesync    T1  accepted
B-BrakeOscillation   T2  accepted
C-FourWayDeadlock    T3  partial
E-FairWaitBlueprint  T3  accepted
```

Run the paper-style evaluation:

```powershell
python evaluate.py
```

Expected governed result:

```text
governed  5 cases, 4 accepted, 1 partial, 0 failed, 6 CI runs
```

Run the artifact verifier:

```powershell
python tools\verify_artifact.py
```

Expected final line:

```text
Submission readiness passed.
```

## Evidence Files

- `outputs/dashboard.html`: interactive static dashboard for the replay demo.
- `outputs/demo_report.json`: full D0 routes, prompts, gate histories, and final Symptom Cards.
- `outputs/eval_dashboard.html`: static comparison dashboard for governed mode, B0-B3 baselines, and ablations.
- `outputs/eval_summary.csv`: paper-style comparison summary.
- `outputs/human_supervision_summary.csv`: offline supervision-condition summary.
- `outputs/maintainability_summary.csv`: maintainability proxy rows for Unity and UE5 accepted patches.
- `docs/paper_traceability.md`: maps paper criteria to concrete files and generated evidence.
- `schemas/`: JSON Schema files for Policy, Symptom Card, Architecture Card, and CodeContext.

## Key Expected Claims

- D0 covers all repair levels: T0, T1, T2, and T3.
- Governed mode repairs 4 of 5 synthetic cases and leaves 1 case partial because a fairness invariant still fails.
- UE5 is represented by both a partial visual-scripting repair and an accepted visual-scripting repair.
- `outputs/maintainability_summary.csv` includes `UE5` with `accepted_patches=1`.
- `fixed_ladder` reaches the same accepted count as governed mode but uses more CI runs.
- B0, B1, B3, broad-context, and no-architecture-card modes degrade relative to governed mode.

## Live GPT-5.5 Path

The offline artifact uses deterministic synthetic patches. The GPT-5.5 provider path is wired but requires credentials:

```powershell
$env:OPENAI_API_KEY = "..."
python tools\gpt55_smoke.py
```

The expected offline submission does not require this command.

## Known Boundaries

- The replay project is a Python fixture that emulates Unity and UE5 CI gates.
- Blueprint edits are represented as JSON diffs so the artifact can run without UE5.
- The maintainability summary is a deterministic proxy, not a replacement for engine-native static analyzers.
- The synthetic corpus is designed for protocol demonstration, not statistical claims.

## CI

The artifact commit passed GitHub Actions:

`https://github.com/unibuc-cs/game-ci-llm-repair/actions/runs/26569110826`
