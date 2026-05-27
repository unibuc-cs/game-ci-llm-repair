# tools/vgfe_bp.py (run inside UE editor)

"""
Make the graph section generic

Rename that analyzer to Visual Graph Feature Extractor (VGFE). It never says “Sort by Distance…”. It only emits neutral features:
    node_histogram — counts by node class

    call_histogram — counts by called function symbol

    degree_stats — min/median/max in/out degree

    path_length_stats — approximate longest path

    prop_access_histogram — property/field getters/setters (names only)

    dataflow_edges (optional, compact) — edges between “value sources” and call inputs

UE Editor Python (generic; no right-of-way knowledge)
"""
from collections import Counter
from statistics import median
from unreal import EditorAssetLibrary as EAL, BlueprintEditorLibrary as BEL

def export_bp_features(bp_path: str) -> dict:
    bp = EAL.load_asset(bp_path)
    graphs = BEL.get_all_graphs(bp)

    node_hist = Counter()
    call_hist = Counter()
    prop_hist = Counter()
    indeg = Counter()
    outdeg = Counter()

    for g in graphs:
        nodes = BEL.get_graph_nodes(g)
        for n in nodes:
            cls = n.get_class().get_name()
            node_hist[cls] += 1
            # degree (approx)
            outs = BEL.get_all_output_pins(n)
            ins  = BEL.get_all_input_pins(n)
            outdeg[cls] += len([p for p in outs if BEL.is_pin_linked(p)])
            indeg[cls]  += len([p for p in ins  if BEL.is_pin_linked(p)])
            # calls
            if cls == "K2Node_CallFunction":
                fn = BEL.get_function_name(n)  # engine symbol name
                call_hist[fn] += 1
            # property access (very generic)
            if cls in ["K2Node_VariableGet","K2Node_VariableSet"]:
                prop = BEL.get_variable_name(n)
                prop_hist[prop] += 1

    degree_stats = {
        "in_min": min(indeg.values() or [0]),
        "in_med": int(median(indeg.values() or [0])),
        "in_max": max(indeg.values() or [0]),
        "out_min": min(outdeg.values() or [0]),
        "out_med": int(median(outdeg.values() or [0])),
        "out_max": max(outdeg.values() or [0]),
    }
    # path_length_stats omitted here; you can approximate with a DAG over exec pins.

    return {
        "node_histogram": dict(node_hist),
        "call_histogram": dict(call_hist),
        "prop_access_histogram": dict(prop_hist),
        "degree_stats": degree_stats
    }
