from ursina import *
from ursina.curve import *

class Cloud:
    def __init__(self, position, scale = 15, alive_time = 1.5):
        
        # entity
        self.entity = Entity(
            model = "quad",
            billboard = True,
            texture = "images/cloud.png",
            position = position,
            scale = scale,
            alpha = 1,
            add_to_scene_entities = False,
        )

        # animations
        self.entity.animate("alpha", 0, duration = alive_time, curve = linear)
        self.entity.animate("rotation_z", 1000, duration = alive_time, curve = linear)
        destroy(self.entity, delay = alive_time)