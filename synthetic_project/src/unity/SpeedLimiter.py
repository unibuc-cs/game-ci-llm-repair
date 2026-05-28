class SpeedLimiter:
    def __init__(self, max_speed: float) -> None:
        self.max_speed = max_speed

    def clamp(self, speed: float) -> float:
        if speed < self.max_speed:
            return speed
        return speed
