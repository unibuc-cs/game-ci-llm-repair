import json
import unittest
from pathlib import Path

from src.ue5.AI.VehicleController import game_thread_metrics, load_blueprint


class FourWayPerfGate(unittest.TestCase):
    def test_game_thread_budget(self):
        blueprint = load_blueprint(Path("Content/Blueprints/BP_IntersectionController.json"))
        metrics = game_thread_metrics(blueprint)
        print("SANERBUG_METRICS " + json.dumps(metrics))
        self.assertLessEqual(metrics["GameThread_ms_avg"], 8.0)
        self.assertLessEqual(metrics["GameThread_ms_p95"], 12.0)


if __name__ == "__main__":
    unittest.main()
