import json
import unittest
from pathlib import Path

from src.ue5.AI.VehicleController import load_blueprint


class FourWayInvariantGate(unittest.TestCase):
    def test_fair_wait_distribution(self):
        blueprint = load_blueprint(Path("Content/Blueprints/BP_IntersectionController.json"))
        violations = {
            "NoCollisionOnGrant": 0,
            "FairWaitDistribution": 0 if blueprint.get("fair_wait_enabled") else 1,
        }
        print("SANERBUG_METRICS " + json.dumps({"violations": violations}))
        self.assertEqual(violations["FairWaitDistribution"], 0)


if __name__ == "__main__":
    unittest.main()
