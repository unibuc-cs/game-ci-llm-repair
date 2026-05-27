class TrafficLightController:
    def __init__(self) -> None:
        self.car_phase = "Red"
        self._listeners = []

    def subscribe(self, callback) -> None:
        self._listeners.append(callback)

    def set_phase(self, phase: str) -> None:
        self.car_phase = phase
        for callback in list(self._listeners):
            callback(phase)
