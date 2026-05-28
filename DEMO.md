# Demo Script

This is a short script for presenting the prototype in about three minutes.

## 1. State the Goal

The prototype demonstrates the governed LLM repair workflow from the paper:
D0 diagnosis, adaptive T0-T3 routing, policy-scoped prompts, CI-gated patch
validation, replayable synthetic cases, and ablation evaluation.

## 2. Run the Main Demo

```powershell
python run_demo.py
```

Expected result:

```text
Case               | D0 | Status   | Attempts | CI | Last gate
D-SpeedLimitClamp  | T0 | accepted | 1        | 1  | -
A-CrosswalkDesync  | T1 | accepted | 1        | 1  | -
B-BrakeOscillation | T2 | accepted | 2        | 2  | -
C-FourWayDeadlock  | T3 | partial  | 1        | 1  | invariants
```

Point out:

- D0 covers every level from T0 through T3.
- B shows adaptive retry after a performance failure.
- C is intentionally partial because the fairness invariant still fails.
- The default run applies unified diffs to copied replay projects and runs real
  unittest gates.

Open:

```text
outputs/dashboard.html
```

Use the dashboard to show the route, gate history, prompt snapshot, and final
Symptom Card for each case.

## 3. Run the Evaluation

```powershell
python evaluate.py
```

Expected result:

```text
Mode           | Accepted | Partial | Failed | Attempts | CI
governed       | 3        | 1       | 0      | 5        | 5
B0_single_prompt        | 1        | 1       | 2
B1_multi_attempt_prompt | 2        | 1       | 1
B2_tool_agent           | 3        | 1       | 0
B3_broad_context_agent  | 0        | 2       | 2
fixed_ladder   | 3        | 1       | 0      | 12       | 12
broad_context  | 0        | 2       | 2      | 4        | 4
single_attempt | 2        | 1       | 1      | 4        | 4
no_arch_card   | 2        | 1       | 1      | 6        | 6
```

Open:

```text
outputs/eval_dashboard.html
```

Use this table as the paper-facing argument:

- governed matches fixed ladder acceptance while using fewer CI runs;
- B0-B3 are present as named paper baselines;
- broad context performs worse on these synthetic cases;
- removing retries or Architecture Card context degrades outcomes.

## 4. Show Traceability

Open:

```text
docs/paper_traceability.md
```

This maps each paper criterion to the repo file and generated evidence.

## 5. Optional GPT-5.5 Smoke Test

After setting credentials:

```powershell
$env:OPENAI_API_KEY = "..."
python tools/gpt55_smoke.py
```

This exercises the real LLM candidate-generation path on the smallest T0 case.
