from ursina import *
from projector_shader import *
from ursina.curve import *
from layered_glow import layeredGlow

# const
DIRECTION_ANY = 1

class NullBlock:
    def __init__(self, x, y):

        # position
        self.x = x
        self.y = y

        # entity
        self.entity = Entity(
            position = ((x - 6) * 10 + 5, 0, (-y + 5) * 10 + 5),
        )

        # move attributes
        self.movable = True

class WallBlock:
    def __init__(self, x, y, default = False):

        # position
        self.x = x
        self.y = y

        # default
        self.default = default

        # level
        self.level = 0

        # entity
        self.entity = Entity(
            model = "cube",
            scale = 9.9,
            position = ((x - 6) * 10 + 5, 0, (-y + 5) * 10 + 5),
            texture = "models/wall/wall.png",
            shader = projector_shader,
            collider = "box",
            name = "block",
            owner = self,
        )

        # move attributes
        self.movable = False

    def getJsonData(self):
        return [self.x, self.y]

class CrateBlock:
    def __init__(self, x, y, level):

        # position
        self.x = x
        self.y = y

        # level
        self.level = 0

        # entity
        self.entity = Entity(
            model = "cube",
            scale = 9.9,
            position = ((x - 6) * 10 + 5, level * 10, (-y + 5) * 10 + 5),
            texture = "models/crate/crate.jpg",
            shader = projector_shader,
            collider = "box",
            name = "block",
            owner = self,
        )

        # move attributes
        self.movable = True
        self.direction = DIRECTION_ANY

    def getJsonData(self):
        return [self.x, self.y, self.level]

class DirectionBlock:
    def __init__(self, x, y, level, direction):

        # position
        self.x = x
        self.y = y

        # level
        self.level = level
        
        # direction
        self.direction = direction

        # entity
        self.entity = Entity(
            model = "models/direction_block/direction_block",
            scale = 5,
            position = ((x - 6) * 10 + 5, level * 10, (-y + 5) * 10 + 5),
            rotation = (0, {
                (0, -1): 270,
                (0, 1): 90,
                (-1, 0): 180,
                (1, 0): 0,
            }[tuple(direction)], 0),
            texture = "models/direction_block/direction_block.jpg",
            shader = projector_shader,
            collider = "box",
            name = "block",
            owner = self,
        )

        # move attributes
        self.movable = True
        self.direction = tuple(direction)

    def getJsonData(self):
        return [self.x, self.y, self.level, self.direction]

class PortalBlock:
    def __init__(self, x, y, color, _for = None):

        # position
        self.x = x
        self.y = y

        # for
        self._for = _for

        # level
        self.level = 0

        # entity
        self.entity = Entity(
            model = "models/portal/portal",
            scale = 4,
            position = ((x - 6) * 10 + 5, 0, (-y + 5) * 10 + 5),
            color = color,
            collider = "box",
            owner = self,
            on_destroy = self.setDestroyed,
            name = "block",
        )
        layeredGlow(self.entity, combine = True, scale_expo = 1.03)

        # don't animate when removed
        self.removed = False

        # begin animation
        self.startAnimate()

    def setDestroyed(self):
        self.removed = True

    def startAnimate(self, up = True):
        if self.removed:
            return
        self.entity.animate("y", int(up) * 5, duration = 1.3, curve = linear)
        invoke(self.startAnimate, up = (not up), delay = 1.3)

class CustomBlock:
    def __init__(self, entity_type, x, y, level, texture, **kwargs):

        # position
        self.x = x
        self.y = y

        # entity
        self.entity = entity_type(
            model = "cube",
            scale = 9.9,
            position = ((x - 6) * 10 + 5, level * 10, (-y + 5) * 10 + 5),
            texture = texture,
            shader = projector_shader,
            parent = scene,
            collider = "box",
            owner = self,
            **kwargs,
        )

        # kwargs
        for attr, val in kwargs.items():
            setattr(self, attr, val)

        # move attributes
        self.movable = True
        self.direction = DIRECTION_ANY