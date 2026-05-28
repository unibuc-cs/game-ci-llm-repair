# GPT-5.5 Smoke Test

The repository has a live LLM path through `OpenAIPatchProvider`. The default
model is `gpt-5.5`; the offline demo still uses deterministic synthetic patches
so CI remains credential-free.

## Preconditions

- `OPENAI_API_KEY` is set in the shell.
- The `openai` Python package is installed.
- The repository commands pass in synthetic replay mode.

Check the environment:

```powershell
python -c "import os, importlib.util; print('key=', bool(os.getenv('OPENAI_API_KEY'))); print('openai=', bool(importlib.util.find_spec('openai')))"
```

## Run

Use the smallest T0 case first:

```powershell
$env:OPENAI_API_KEY = "..."
python tools/gpt55_smoke.py
```

Equivalent direct command:

```powershell
python orchestrator.py --case D-SpeedLimitClamp --patch-provider openai --llm-model gpt-5.5 --gate-runner replay --verbose --out outputs/gpt55_smoke_report.json
```

The smoke runner writes:

```text
outputs/gpt55_smoke_report.json
outputs/gpt55_smoke_dashboard.html
```

## Pass Criteria

The smoke test is useful if all of these are true:

- GPT-5.5 returns JSON matching the candidate patch schema.
- The candidate includes a minimal unified diff.
- The replay runner applies the diff to a copied `synthetic_project`.
- Build and unit gates run against the patched copy.
- The report records either an accepted patch or a meaningful failing gate.

For the current T0 case, the ideal result is:

```text
D-SpeedLimitClamp | T0 | accepted | 1 attempt | 1 CI run
```

## If It Fails

- Schema failure: inspect the raw exception and tighten the provider
  instructions or output schema.
- Patch apply failure: inspect the `unified_diff`; the model likely emitted a
  path or hunk mismatch.
- Gate failure: keep the report. A failed live patch is still useful evidence
  that the validation loop catches bad candidates.
- Missing credentials: the runner exits with status `2` and does not create a
  smoke report.

## What to Commit After a Live Run

After a successful credentialed run, commit either:

- `outputs/gpt55_smoke_report.json` and `outputs/gpt55_smoke_dashboard.html`,
  if you want the exact live evidence in the repository; or
- a short note under `docs/` summarizing the date, command, model, case, status,
  attempts, CI runs, and failing gate if any.
