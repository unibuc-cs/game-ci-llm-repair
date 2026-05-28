import unittest

from src.unity.SpeedLimiter import SpeedLimiter


class SpeedLimiterUnitGate(unittest.TestCase):
    def test_clamps_speed_above_limit(self):
        limiter = SpeedLimiter(max_speed=50.0)

        self.assertEqual(limiter.clamp(72.5), 50.0)

    def test_leaves_speed_below_limit_unchanged(self):
        limiter = SpeedLimiter(max_speed=50.0)

        self.assertEqual(limiter.clamp(42.0), 42.0)


if __name__ == "__main__":
    unittest.main()
