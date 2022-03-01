from ursina import *
from ursina import curve
from copy import copy

def layeredGlow(entity, combine = False, scale_expo = 1.01):
    scale = Vec3(scale_expo)
    alpha = 0.3
    glow_color = entity.color
    for i in range(13):
        Entity(
            parent = entity,
            model = copy(entity.model),
            color = glow_color,
            alpha = alpha,
            scale = scale,
            add_to_scene_entities = False,
        )

        scale *= scale_expo
        alpha *= 0.85

    if combine:
        entity.combine()

if __name__ == "__main__":
    app = Ursina()

    Sky(color = color.black)

    test = Entity(
        model = "cube",
        color = color.blue, # color.white, # color.yellow,
    )

    def animateCube():
        invoke(test.animate, name = "z", value = 10, duration = 3, curve = curve.linear)
        invoke(test.animate, name = "z", value = 0, duration = 3, delay = 3, curve = curve.linear)
        invoke(animateCube, delay = 6)
    # animateCube()

    layeredGlow(test, True, 1.03)

    EditorCamera()
    app.run()