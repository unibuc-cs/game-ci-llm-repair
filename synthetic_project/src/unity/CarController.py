from src.unity.VehicleSensors import VehicleSensors


def simulate_brake_frame(vehicle_count: int) -> dict[str, float]:
    vehicles = list(range(vehicle_count))
    sensors = VehicleSensors()
    sensors.scan(vehicles)

    raycasts = sensors.raycast_count
    fixed_update_ms = 4.6 + raycasts / 1800.0
    physics_step_ms_p95 = 4.8 + raycasts / 1300.0
    return {
        "FixedUpdate_ms_avg": round(fixed_update_ms, 2),
        "Physics_Step_ms_p95": round(physics_step_ms_p95, 2),
        "RaycastCount_per_frame_avg": raycasts,
        "NoBackwardTeleport": 0,
    }
