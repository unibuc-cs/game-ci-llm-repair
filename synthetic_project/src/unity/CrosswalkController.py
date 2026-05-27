from src.unity.TrafficLightController import TrafficLightController


class CrosswalkController:
    def __init__(self, traffic_light: TrafficLightController) -> None:
        self.traffic_light = traffic_light
        self._walk_allowed = False
        self.traffic_light.subscribe(self.on_phase_change)

    def on_phase_change(self, phase: str) -> None:
        if phase == "Pedestrian":
            self._walk_allowed = True

    def can_walk(self) -> bool:
        return self._walk_allowed
