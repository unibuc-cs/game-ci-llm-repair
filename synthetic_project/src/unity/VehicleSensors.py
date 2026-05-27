RAYCASTS_PER_VEHICLE = 61


class VehicleSensors:
    def __init__(self) -> None:
        self.raycast_count = 0

    def scan(self, vehicles: list[int]) -> dict[int, float]:
        self.raycast_count += len(vehicles) * RAYCASTS_PER_VEHICLE
        return {vehicle_id: 0.0 for vehicle_id in vehicles}
