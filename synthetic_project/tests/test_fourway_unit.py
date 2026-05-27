import unittest
from pathlib import Path

from src.ue5.AI.VehicleController import load_blueprint


class FourWayUnitGate(unittest.TestCase):
    def test_blueprint_uses_stable_tie_break(self):
        blueprint = load_blueprint(Path("Content/Blueprints/BP_IntersectionController.json"))
        self.assertEqual(blueprint["sort_key"], "DistanceToStopLine")
        self.assertNotEqual(blueprint["tie_break"], "random")


if __name__ == "__main__":
    unittest.main()
