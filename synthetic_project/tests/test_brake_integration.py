import json
import unittest

from src.unity.CarController import simulate_brake_frame


class BrakeIntegrationGate(unittest.TestCase):
    def test_no_backward_teleport_in_simulated_frame(self):
        metrics = simulate_brake_frame(300)
        print("SANERBUG_METRICS " + json.dumps({"violations": {"NoBackwardTeleport": metrics["NoBackwardTeleport"]}}))
        self.assertEqual(metrics["NoBackwardTeleport"], 0)


if __name__ == "__main__":
    unittest.main()
