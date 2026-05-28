# Real Project Integration

This prototype is intentionally replayable without Unity or UE5. To connect it
to a real game repository, replace the synthetic data source and gate runner in
small, testable steps.

## 1. Create an Architecture Card

Add a project entry to `config/architecture_cards.json`:

- `invariants`: gameplay or runtime properties that must never regress.
- `perf_budget`: numeric budgets used by the perf gate.
- `allowed_components`: high-level areas the repair may touch.
- `file_allowlist`: paths the repair is allowed to modify.
- `gates`: ordered validation stages, for example build, unit, integration,
  perf, and invariants.

Start with strict allowlists. Widen them only when D0 evidence requires a
higher repair tier.

## 2. Emit Symptom Cards

For each failing CI job, create a case with:

- failing test names and messages;
- stack traces or engine logs;
- profiler metrics;
- invariant violations;
- static features, if available;
- visual graph features for Blueprint or visual scripting failures;
- primary files and caller/callee neighbors.

The current format is shown in `data/synthetic_cases.json`.

## 3. Configure Real Gates

Use `CommandGateRunner` for a real repository:

```powershell
python orchestrator.py --patch-provider openai --llm-model gpt-5.5 --gate-runner command --gate-commands config/gate_commands.example.json --gate-cwd C:\path\to\game-repo
```

Replace `config/gate_commands.example.json` with project commands. Examples:

```json
{
  "build": "python ci/build.py",
  "unit": "python ci/unit.py",
  "integration": "python ci/playmode.py",
  "perf": "python ci/perf.py",
  "invariants": "python ci/invariants.py"
}
```

Each command receives:

- `SANERBUG_GATE`
- `SANERBUG_PATCH_ID`
- `SANERBUG_CANDIDATE_JSON`

The command can read the candidate JSON, apply the unified diff in an isolated
workspace, run the gate, and return a nonzero exit code on failure.

## 4. Recommended Isolation

Do not apply LLM patches directly to the developer checkout. Use one of these:

- a temporary copy of the game repository;
- a disposable worktree;
- a CI job workspace;
- a container or VM image with the engine installed.

The synthetic `ReplayProjectGateRunner` demonstrates this pattern by copying
`synthetic_project` per candidate before applying the diff.

## 5. Unity Notes

Useful gate split:

- build: compile scripts and assets;
- unit: edit-mode tests;
- integration: play-mode tests or deterministic scene replay;
- perf: profiler capture with budgets;
- invariants: domain checks over logs or telemetry.

Keep editor paths, package caches, and generated library folders outside the
candidate diff allowlist.

## 6. UE5 Notes

Useful gate split:

- build: module compile and asset load;
- unit: automation tests;
- integration: deterministic map replay;
- perf: game-thread and render-thread budgets;
- invariants: Blueprint event and gameplay property checks.

For Blueprint repairs, export graph summaries or text representations into the
Symptom Card. The current demo uses JSON to make this replayable in Python.

## 7. First Real Trial

Start with a T0 or T1 bug:

```powershell
$env:OPENAI_API_KEY = "..."
python orchestrator.py --case YOUR_CASE_ID --patch-provider openai --llm-model gpt-5.5 --gate-runner command --gate-commands config/your_gate_commands.json --gate-cwd C:\path\to\isolated\repo --verbose
```

Then inspect:

- accepted patch id;
- modified files;
- gate history;
- final Symptom Card;
- prompt snapshot.

Only after a small source-only case works should you try T2 performance repairs
or T3 visual-scripting repairs.
