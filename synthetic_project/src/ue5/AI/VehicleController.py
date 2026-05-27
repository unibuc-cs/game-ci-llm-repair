import json
from pathlib import Path


def load_blueprint(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def grant_next_events(blueprint: dict, queue_size: int) -> int:
    if blueprint.get("grant_strategy") == "none":
        return 0
    if blueprint.get("tie_break") == "random":
        return 0
    return max(0, queue_size - 1)


def game_thread_metrics(blueprint: dict) -> dict[str, float]:
    node_count = float(blueprint.get("node_count", 31))
    return {
        "GameThread_ms_avg": round(4.2 + node_count / 26.0, 2),
        "GameThread_ms_p95": round(6.2 + node_count / 18.0, 2),
    }
