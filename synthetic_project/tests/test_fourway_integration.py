import unittest
from pathlib import Path

from src.ue5.AI.VehicleController import grant_next_events, load_blueprint


class FourWayIntegrationGate(unittest.TestCase):
    def test_four_way_stop_makes_progress(self):
        blueprint = load_blueprint(Path("Content/Blueprints/BP_IntersectionController.json"))
        self.assertGreater(grant_next_events(blueprint, queue_size=50), 0)


if __name__ == "__main__":
    unittest.main()
