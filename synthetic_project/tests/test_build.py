import json
import unittest
from pathlib import Path

from src.ue5.AI.VehicleController import load_blueprint
from src.unity.CarController import simulate_brake_frame
from src.unity.CrosswalkController import CrosswalkController
from src.unity.SpeedLimiter import SpeedLimiter
from src.unity.TrafficLightController import TrafficLightController


class BuildGate(unittest.TestCase):
    def test_imports_and_blueprint_load(self):
        traffic = TrafficLightController()
        CrosswalkController(traffic)
        SpeedLimiter(max_speed=50.0)
        simulate_brake_frame(1)
        blueprint = load_blueprint(Path("Content/Blueprints/BP_IntersectionController.json"))
        self.assertEqual(blueprint["name"], "BP_IntersectionController")
        json.dumps(blueprint)


if __name__ == "__main__":
    unittest.main()
