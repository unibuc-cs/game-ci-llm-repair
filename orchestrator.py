"""
Separate static vs dynamic phases in the orchestrator

You’re right: static analyzers shouldn’t wait for test runs. Split and cache them.

    Static runs once per SHA and feeds many trials.

    Dynamic runs each time you test a patch (different seeds/scenes/policies).

    Domain packs can use both static & dynamic facts; if none enabled, rely on human hints.
"""

# Phase 0: STATIC (fast, cached per commit)
static_index = {
  static_features: run_static_code_analyzers(repo_snapshot),
  visual_graph:    export_visual_graphs(assets_paths)   # VGFE, optional
}

# Phase 1: DYNAMIC (on demand per trial)
artifacts = run_tests_and_capture(engine, trial_policy)   # failures, exceptions, perf, invariants

# Phase 2: FUSE → HINTS
auto_hints = fuse(static_index, artifacts)                 # just bundle generic facts
domain_hints = run_enabled_domain_packs(static_index, artifacts)  # optional
merged = merge_hints(auto_hints, domain_hints, human_hints)

# Phase 3: PROMPT & APPLY
prompt = assemble_prompt(code_ctx, merged, arch_card, trial_policy)
patch  = LLM.propose_patch(prompt)
apply_and_gate(patch, trial_policy)
