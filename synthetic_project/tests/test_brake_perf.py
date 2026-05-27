import json
import unittest

from src.unity.CarController import simulate_brake_frame


class BrakePerfGate(unittest.TestCase):
    def test_fixed_update_and_physics_budget(self):
        metrics = simulate_brake_frame(300)
        print("SANERBUG_METRICS " + json.dumps(metrics))
        self.assertLessEqual(metrics["FixedUpdate_ms_avg"], 12.0)
        self.assertLessEqual(metrics["Physics_Step_ms_p95"], 12.0)


if __name__ == "__main__":
    unittest.main()
