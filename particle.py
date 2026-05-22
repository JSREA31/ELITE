import numpy as np

class Particle:
    def __init__(self, position, velocity, color, size, lifetime):
        self.position = np.array(position, dtype=float)
        self.velocity = np.array(velocity, dtype=float)
        self.color = color  # (r, g, b)
        self.size = size
        self.lifetime = lifetime
        self.age = 0

    def update(self):
        self.position += self.velocity
        self.age += 1

    def is_alive(self):
        return self.age < self.lifetime