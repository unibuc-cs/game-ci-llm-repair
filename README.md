# Governed LLM Bug Repair Demo

This repository contains a minimal runnable prototype for the paper workflow:
D0 diagnosis, adaptive entry into the T0-T3 repair ladder, Symptom Cards,
Architecture Cards, policy-scoped prompts, and CI-gated validation.

The demo is offline. Instead of calling an LLM or a real Unity/UE5 build, it
uses deterministic synthetic candidate patches so the orchestration protocol
can be inspected and tested anywhere Python runs.

## Demo Scope

- `data/synthetic_cases.json` contains three synthetic defect cases:
  - `A-CrosswalkDesync`: cross-file Unity gameplay repair routed to T1.
  - `B-BrakeOscillation`: Unity performance/invariant repair routed to T2.
  - `C-FourWayDeadlock`: UE5 visual-scripting repair routed to T3 and reported
    as a partial repair after a late invariant failure.
- `synthetic_project/` is a replayable failing project fixture. Replay mode
  copies it per attempt, applies the candidate unified diff, and runs real
  unittest-based gates against the patched copy.
- `config/architecture_cards.json` stores project-level constraints and CI
  gate order.
- `config/policies.json` stores the T0-T3 evidence, permission, gate, and
  attempt-budget settings.
- `orchestrator.py` runs D0, assembles policy-bound prompts, simulates patch
  proposals, evaluates CI gates, updates Symptom Cards after failures, and
  writes a JSON report.
- `dashboard.py` generates a self-contained HTML dashboard from the JSON
  report.
- `run_demo.py` runs the orchestrator and regenerates the dashboard in one
  command.

## Run

```powershell
python orchestrator.py --case all --verbose
```

The command writes:

```text
outputs/demo_report.json
```

Run the full demo command:

```powershell
python run_demo.py
```

By default, `run_demo.py` uses replay mode: each candidate patch is applied to
a copied synthetic project under `outputs/replay_trials/`, and the configured
unittest gates are executed against that patched trial.

Run tests with:

```powershell
python -m unittest discover -s tests
```

## Dashboard

Generate a self-contained HTML dashboard from the latest report:

```powershell
python dashboard.py --report outputs/demo_report.json --out outputs/dashboard.html
```

Open `outputs/dashboard.html` directly in a browser. It shows the D0 route,
case status, CI gate history, runtime evidence, prompt snapshots, and final
Symptom Card for each synthetic defect.

## Providers and Gates

The orchestrator now has replaceable patch providers and gate runners.

Offline synthetic mode:

```powershell
python run_demo.py --patch-provider synthetic --gate-runner synthetic
```

Replay mode with real synthetic gates:

```powershell
python run_demo.py --patch-provider synthetic --gate-runner replay
```

OpenAI patch proposal mode uses `gpt-5.5` by default:

```powershell
$env:OPENAI_API_KEY = "..."
python orchestrator.py --case A-CrosswalkDesync --patch-provider openai --llm-model gpt-5.5
```

The OpenAI provider returns a structured candidate patch with a unified diff,
modified files, visual-graph edit flag, and test plan. For real validation,
pair it with command-backed gates:

```powershell
python orchestrator.py --patch-provider openai --llm-model gpt-5.5 --gate-runner command --gate-commands config/gate_commands.example.json
```

`config/gate_commands.example.json` is only a placeholder map. Replace those
commands with project-specific build, unit, integration, performance, and
invariant checks before using command gates on a real repository. Each command
receives `SANERBUG_GATE`, `SANERBUG_PATCH_ID`, and `SANERBUG_CANDIDATE_JSON`
environment variables so it can inspect or apply the proposed patch.

## Minimal Implementation Plan

1. Keep the artifact model explicit: Symptom Card, Architecture Card, Policy,
   and CodeContext are loaded from JSON.
2. Use deterministic D0 routing rules:
   - visual graph or Blueprint evidence -> T3
   - performance budget or invariant evidence -> T2
   - caller/callee neighbor evidence -> T1
   - otherwise -> T0
3. Execute only the active ladder suffix selected by D0.
4. Render prompts from the fields allowed by the active policy.
5. Enforce edit permissions before build-gate success.
6. Stop at the first failing CI gate and append the evidence to the Symptom
   Card.
7. Accept a patch only when all active gates pass; otherwise report the best
   partial attempt.

This is intentionally small, but it gives a demoable path for replacing the
deterministic patch simulator with a real LLM call and real engine CI runners.
