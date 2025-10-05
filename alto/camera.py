from typing import Optional


class Camera:
    def __init__(self, speed: float) -> None:
        self.x = 0.0
        self.y = 0.0
        self.speed = speed

    def update(
        self,
        dt: float,
        target_x: Optional[float] = None,
        lerp: Optional[float] = None,
        target_y: Optional[float] = None,
        lerp_y: Optional[float] = None,
    ) -> None:
        if target_x is None or lerp is None:
            self.x += self.speed * dt
        else:
            self.x += (target_x - self.x) * min(1.0, lerp * dt)
        if target_y is not None and lerp_y is not None:
            self.y += (target_y - self.y) * min(1.0, lerp_y * dt)


