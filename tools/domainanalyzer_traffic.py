
"""
Keep game-specific interpretation in domain packs (or human hints)

A domain pack reads the generic facts (VGFE + static code facts + dynamic counters) and—optionally—produces domain_hints. It’s few in number (Traffic, Navigation, Netcode, etc.), not per bug.

If you don’t enable a domain pack, you can supply the same fields via human hints in the UI. Human hints always override/augment the auto ones.
"""


# Example: Right-of-Way pack (consumes generic features)

def right_of_way_pack(features, tests_failed):
    dh = {}
    # use *generic* signals to infer likely patterns
    if any("FourWayStop" in t["name"] or "RightOfWay" in t["name"] for t in tests_failed):
        calls = features.get("call_histogram", {})
        props = set(features.get("prop_access_histogram", {}).keys())

        dh["ordering_key_candidates"] = sorted([p for p in props if "Distance" in p or "Entry" in p or "Heading" in p])
        dh["has_priority_queue"] = any(k.endswith("GrantNext") or k.endswith("RequestRightOfWay") for k, c in calls.items())
    return dh
