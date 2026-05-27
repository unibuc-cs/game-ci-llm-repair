"Domain pack can then narrow candidates based on test wording (e.g., “RightOfWay”, “deadlock”)."


def extract_property_flow_to_call(graph_features, call_symbol):
    """Return property names that frequently feed into a given call symbol."""
    # In a full impl you’d walk dataflow; here we correlate props with call presence
    props = graph_features.get("prop_access_histogram", {})
    calls = graph_features.get("call_histogram", {})
    if calls.get(call_symbol, 0) == 0:
        return []
    # naive: top properties in same graph become 'candidates'
    return sorted([p for p, cnt in props.items() if cnt > 0])


