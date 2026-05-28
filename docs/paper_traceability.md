# Paper Traceability Matrix

This matrix maps the prototype to the implementation criteria claimed by the
paper workflow. The current artifact is a runnable demo over synthetic data,
not a full Unity or UE5 plugin.

| Paper criterion | Prototype artifact | Evidence to inspect |
| --- | --- | --- |
| Symptom Card representation | Each case in `data/synthetic_cases.json` has `symptom_card` with failed tests, perf, invariants, static features, visual-graph evidence, and domain hints. | `outputs/demo_report.json` includes the final Symptom Card after gate feedback. |
| Architecture Card representation | `config/architecture_cards.json` defines invariants, performance budgets, allowed components, file allowlists, and gate order. | T2 and T3 prompts include architecture constraints when policy allows them. |
| D0 diagnosis | `orchestrator.diagnosis_d0` routes from evidence signals to `T0`, `T1`, `T2`, or `T3`. | `python run_demo.py` prints all four routes: D/T0, A/T1, B/T2, and C/E at T3. |
| T0 local repair | `D-SpeedLimitClamp` has local evidence only, no neighbors, no invariant, and no visual signal. | Accepted at T0 after build and unit gates. |
| T1 cross-file repair | `A-CrosswalkDesync` includes caller/callee neighbor evidence. | Accepted at T1 after build, unit, and integration gates. |
| T2 performance or invariant repair | `B-BrakeOscillation` includes profiler evidence and an invariant violation. | First T2 attempt fails perf; second T2 attempt is accepted after all gates. |
| T3 visual-scripting repair | `C-FourWayDeadlock` and `E-FairWaitBlueprint` include Blueprint visual-graph evidence. | C remains partial on the fairness invariant; E is accepted after the fairness invariant passes. |
| Policy-scoped prompt assembly | `config/policies.json` controls context visibility, edit permissions, gates, and attempt budgets. `orchestrator.assemble_prompt` renders only policy-visible evidence. | Prompt snapshots are stored in `outputs/demo_report.json` and shown in `outputs/dashboard.html`. |
| Permission governance | `validate_candidate_permissions` enforces file allowlists, new-file permissions, and visual-graph edit permissions before build success. | `tests/test_orchestrator.py` rejects a visual edit before T3. |
| Adaptive escalation | `orchestrator.run_case` starts at D0-selected level, stops at failing gates, updates the Symptom Card, and tries the next allowed attempt or level. | `B-BrakeOscillation` demonstrates failed perf feedback followed by a better T2 candidate. |
| CI-gated validation | `ReplayProjectGateRunner` copies `synthetic_project`, applies the candidate unified diff, and runs real unittest gates against the patched copy. | `python run_demo.py` uses replay mode by default. |
| Ablation evaluation | `evaluate.py` compares governed routing with `fixed_ladder`, `broad_context`, `single_attempt`, and `no_arch_card`. | `outputs/eval_summary.csv` shows governed success with fewer CI runs than fixed ladder and degraded outcomes for ablations. |
| B0-B3 baseline protocols | `evaluate.py` includes `B0_single_prompt`, `B1_multi_attempt_prompt`, `B2_tool_agent`, and `B3_broad_context_agent` modes. | `outputs/eval_summary.csv` reports each named baseline under the same replay gates. |
| Human supervision accounting | `evaluate.py` emits deterministic offline rows for file-scope confirmation, bounded hints, and escalation approval. | `outputs/human_supervision_summary.csv` records hints/item, review minutes/item, and escalation reviews. |
| Maintainability deltas | `evaluate.py` emits a synthetic maintainability proxy over accepted patches. | `outputs/maintainability_summary.csv` records accepted-patch proxy rows for both Unity and UE5. |
| Release schemas | `schemas/` contains JSON Schema documentation for Policy, Symptom Card, Architecture Card, and CodeContext. | `python -m json.tool schemas/*.schema.json` validates the schema files syntactically. |
| Dashboard evidence | `dashboard.py` and `evaluate.py` emit static HTML artifacts for inspection. | Open `outputs/dashboard.html` and `outputs/eval_dashboard.html`. |
| GPT-5.5 provider path | `OpenAIPatchProvider` defaults to `gpt-5.5` and returns structured candidate patches with unified diffs. | Run `python tools/gpt55_smoke.py` after setting `OPENAI_API_KEY`. |
| Synthetic data policy | Synthetic cases make the demo deterministic and runnable without engine installations or credentials. | All commands run offline with the default synthetic provider. |

## Current Expected Results

`python run_demo.py` should print:

```text
D-SpeedLimitClamp   T0  accepted
A-CrosswalkDesync   T1  accepted
B-BrakeOscillation  T2  accepted
C-FourWayDeadlock   T3  partial
E-FairWaitBlueprint T3  accepted
```

`python evaluate.py` should summarize:

```text
governed                4 accepted, 1 partial, 6 CI runs
B0_single_prompt        1 accepted, 1 partial, 3 failed
B1_multi_attempt_prompt 2 accepted, 1 partial, 2 failed
B2_tool_agent           4 accepted, 1 partial, 17 CI runs
B3_broad_context_agent  1 accepted, 2 partial, 2 failed
fixed_ladder            4 accepted, 1 partial, 17 CI runs
broad_context           1 accepted, 2 partial, 2 failed
single_attempt          3 accepted, 2 partial, 0 failed
no_arch_card            2 accepted, 1 partial, 2 failed
```

## Known Boundaries

- The replay project is a Python fixture that emulates game CI gates; it is not
  a Unity or UE5 editor invocation.
- The default patch provider is deterministic synthetic data. GPT-5.5 support
  is wired but requires `OPENAI_API_KEY` and the `openai` package. See
  `docs/gpt55_smoke_test.md`.
- Visual Blueprint edits are represented as JSON diffs so the behavior can be
  replayed in a standard Python environment.
