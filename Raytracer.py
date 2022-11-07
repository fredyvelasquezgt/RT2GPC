from gl import Raytracer, V3
from obj import *
from figures import *

# Dimensiones
width = 1024
height = 512

# Materiales

gold = Material(diffuse=(1, 0.8, 0), spec=32, matType=REFLECTIVE)
mirror = Material(spec=128, matType=REFLECTIVE)

water = Material(spec=64, ior=1.33, matType=TRANSPARENT)
glass = Material(spec=64, ior=1.5, matType=TRANSPARENT)

stone = Material(diffuse=(0.4, 0.4, 0.4), spec=64, matType=OPAQUE)
brick = Material(diffuse=(0.204, 0.63, 0.63), spec=32, ior=1, matType=OPAQUE)

# Inicializacion
rtx = Raytracer(width, height)
rtx.envmap = EnvMap("fondoFinal.bmp")

# Luces
rtx.ambLight = AmbientLight(strength=0.1)
rtx.dirLight = DirectionalLight(direction=V3(1, -1, -2), intensity=0.5)
rtx.pointLights.append(PointLight(position=V3(0, 2, 0), intensity=0.5))

# Objetos
rtx.scene.append(Sphere(V3(-6, 2, -8), 1.5, mirror))
rtx.scene.append(Sphere(V3(-2, 2, -8), 1.5, water))
rtx.scene.append(Sphere(V3(2, -2, -8), 1.5, glass))
rtx.scene.append(Sphere(V3(6, -2, -8), 1.5, gold))
rtx.scene.append(Sphere(V3(-6, -2, -8), 1.5, stone))
rtx.scene.append(Sphere(V3(6, 2, -8), 1.5, brick))
# Terminar
rtx.glRender()
rtx.glFinish("final.bmp")
