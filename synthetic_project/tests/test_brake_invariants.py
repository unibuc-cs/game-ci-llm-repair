import json
import unittest

from src.unity.CarController import simulate_brake_frame


class BrakeInvariantGate(unittest.TestCase):
    def test_no_backward_teleport(self):
        metrics = simulate_brake_frame(300)
        violations = {"NoBackwardTeleport": metrics["NoBackwardTeleport"]}
        print("SANERBUG_METRICS " + json.dumps({"violations": violations}))
        self.assertEqual(violations["NoBackwardTeleport"], 0)


if __name__ == "__main__":
    unittest.main()
