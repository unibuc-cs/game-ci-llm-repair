import unittest

from src.unity.CrosswalkController import CrosswalkController
from src.unity.PedestrianAgent import PedestrianAgent
from src.unity.TrafficLightController import TrafficLightController


class CrosswalkIntegrationGate(unittest.TestCase):
    def test_pedestrian_waits_on_car_green_after_timescale_change(self):
        traffic = TrafficLightController()
        crosswalk = CrosswalkController(traffic)
        agent = PedestrianAgent()

        traffic.set_phase("Pedestrian")
        self.assertEqual(agent.step(crosswalk.can_walk()), "walk")

        traffic.set_phase("CarGreen")
        self.assertEqual(agent.step(crosswalk.can_walk()), "wait")


if __name__ == "__main__":
    unittest.main()
