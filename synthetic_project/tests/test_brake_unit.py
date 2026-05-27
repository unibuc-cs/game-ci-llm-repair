import unittest

from src.unity.VehicleSensors import VehicleSensors


class BrakeUnitGate(unittest.TestCase):
    def test_sensor_scan_reports_each_vehicle(self):
        sensors = VehicleSensors()
        readings = sensors.scan([1, 2, 3])
        self.assertEqual(sorted(readings), [1, 2, 3])
        self.assertGreater(sensors.raycast_count, 0)


if __name__ == "__main__":
    unittest.main()
