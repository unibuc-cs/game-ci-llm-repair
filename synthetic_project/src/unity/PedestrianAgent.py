class PedestrianAgent:
    def __init__(self) -> None:
        self.steps = 0

    def step(self, can_walk: bool) -> str:
        self.steps += 1
        return "walk" if can_walk else "wait"
