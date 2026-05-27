import unittest

from src.unity.CrosswalkController import CrosswalkController
from src.unity.TrafficLightController import TrafficLightController


class CrosswalkUnitGate(unittest.TestCase):
    def test_car_green_revokes_walk_permission(self):
        traffic = TrafficLightController()
        crosswalk = CrosswalkController(traffic)

        traffic.set_phase("Pedestrian")
        self.assertTrue(crosswalk.can_walk())

        traffic.set_phase("CarGreen")
        self.assertFalse(crosswalk.can_walk())


if __name__ == "__main__":
    unittest.main()
