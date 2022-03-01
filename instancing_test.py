from ursina import *
from panda3d.core import OmniBoundingVolume, LQuaterniond, LVecBase3d
import numpy as np

instancing_shader=Shader(language=Shader.GLSL, vertex='''#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 texcoords;
uniform vec2 texture_scale;
uniform vec2 texture_offset;
uniform vec3 position_offsets[256];
uniform vec4 rotation_offsets[256];
uniform vec3 scale_multipliers[256];
void main() {
    vec3 v = p3d_Vertex.xyz * scale_multipliers[gl_InstanceID];
    vec4 q = rotation_offsets[gl_InstanceID];
    v = v + 2.0 * cross(q.xyz, cross(q.xyz, v) + q.w * v);
    gl_Position = p3d_ModelViewProjectionMatrix * (vec4(v + position_offsets[gl_InstanceID], 1.));
    texcoords = (p3d_MultiTexCoord0 * texture_scale) + texture_offset;
}
''',

fragment='''
#version 140
uniform sampler2D p3d_Texture0;
uniform vec4 p3d_ColorScale;
in vec2 texcoords;
out vec4 fragColor;
void main() {
    vec4 color = texture(p3d_Texture0, texcoords) * p3d_ColorScale;
    fragColor = color.rgba;
}
''',
default_input={
    'texture_scale' : Vec2(1,1),
    'texture_offset' : Vec2(0.0, 0.0),
    'position_offsets' : [Vec3(i,0,0) for i in range(256)],
    'rotation_offsets' : [Vec4(0) for i in range(256)],
    'scale_multipliers' : [Vec3(1) for i in range(256)],
}
)

class snow_entity:
    __slots__ = ['position', 'rotation', 'scale', 'q', 'fallscale']
    def __init__(self, position, rotation, scale):
        self.position = position
        self.rotation = rotation
        self.scale = scale
        self.q = LQuaterniond()
        self.q.setHpr(LVecBase3d(self.rotation.x,self.rotation.y,self.rotation.z))
        self.fallscale = random.uniform(0.8,1.2)
    @property
    def quaternion(self):
        return self.q

points = np.array([Vec3(random.uniform(-10,10),random.uniform(-0.5,0),random.uniform(-10,10)) for i in range(20)])

class SnowCloud(Entity):
    def __init__(self, *args, **kwargs):
        # Entity.__init__(self, *args, model=deepcopy(Mesh(vertices=points, mode='point', thickness=4, render_points_in_3d=True)), **kwargs)
        Entity.__init__(self, *args, model="models/portal/portal", **kwargs)
        self.instances = []
        self.model.uvs = [(v[0],v[1]) for v in self.model.vertices]
        self.model.generate()
        self.shader = instancing_shader
        self.setInstanceCount(256)
        for z in range(16):
            for x in range(16):
                self.instances.append(snow_entity(Vec3(x-8+random.uniform(0,1), random.uniform(-20,20), z-8+random.uniform(0,1)), Vec3(0,0,0), (1,1,1)))
        self.node().setBounds(OmniBoundingVolume())
        self.node().setFinal(True)
        self.frame = 0
        print(len(self.instances))

    def update(self):
        self.offset = self.frame % 2
        for i in range(128):
            e = self.instances[i*2 + self.offset]
            e.position.y -= 4*(time.dt) * e.fallscale
            e.position.x+random.uniform(-0.5,0.5)
            e.position.z+random.uniform(-0.5,0.5)
            if e.position.y < -20: e.position.y = 20
        # self.model.vertices = [e.position for e in self.instances]
        # self.model.generate()
        self.set_shader_input('position_offsets', [e.position for e in self.instances])
        self.set_shader_input('rotation_offsets', [e.quaternion for e in self.instances])
        self.set_shader_input('scale_multipliers',[e.scale for e in self.instances])
        self.frame += 1

if __name__ == '__main__':
    from ursina.prefabs.first_person_controller import FirstPersonController
    app = Ursina(vsync=False)
    SnowCloud()
    # camera = EditorCamera()
    # camera = FirstPersonController(y=2)
    EditorCamera()
    ground = Entity(model='plane', texture='grass', scale=16)
    ground.collider = ground.model
    app.run()