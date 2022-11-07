import struct
from collections import namedtuple
from obj import _color

from numpy import sin, cos, tan

from myLibrary import *

OPAQUE = 0
REFLECTIVE = 1
TRANSPARENT = 2

MAX_RECURSION_DEPTH = 3

STEPS = 1

V2 = namedtuple('Point2', ['x', 'y'])
V3 = namedtuple('Point3', ['x', 'y', 'z'])
V4 = namedtuple('Point4', ['x', 'y', 'z', 'w'])


def char(c):
    # 1 byte
    return struct.pack('=c', c.encode('ascii'))


def word(w):
    # 2 bytes
    return struct.pack('=h', w)


def dword(d):
    # 4 bytes
    return struct.pack('=l', d)


def baryCoords(A, B, C, P):
    # u es para A, v es para B, w es para C
    try:
        # PCB/ABC
        u = (((B.y - C.y) * (P.x - C.x) + (C.x - B.x) * (P.y - C.y)) /
             ((B.y - C.y) * (A.x - C.x) + (C.x - B.x) * (A.y - C.y)))

        # PCA/ABC
        v = (((C.y - A.y) * (P.x - C.x) + (A.x - C.x) * (P.y - C.y)) /
             ((B.y - C.y) * (A.x - C.x) + (C.x - B.x) * (A.y - C.y)))

        w = 1 - u - v
    except:
        return -1, -1, -1

    return u, v, w


def reflectVector(normal, dirVector):
    # R = 2 * ( N . L) * N - L
    reflect = 2 * dotProduct(normal, dirVector)
    reflect = ml(normal, reflect)
    reflect = subtract(reflect, dirVector)
    reflect = normalize(reflect)
    return reflect


def refractVector(normal, dirVector, ior):
    # Snell's Law
    cosi = max(-1, min(1, dotProduct(dirVector, normal)))
    etai = 1
    etat = ior

    if cosi < 0:
        cosi = -cosi
    else:
        etai, etat = etat, etai

        normal = matriz_negada(normal)

    eta = etai/etat
    k = 1 - eta * eta * (1 - (cosi * cosi))

    if k < 0:  # Total Internal Reflection
        return None

    R = add(ml(dirVector, eta), ml(normal, (eta * cosi - k**0.5)))
    return normalize(R)


def fresnel(normal, dirVector, ior):
    cosi = max(-1, min(1, dotProduct(dirVector, normal)))
    etai = 1
    etat = ior

    if cosi > 0:
        etai, etat = etat, etai

    sint = etai / etat * (max(0, 1 - cosi * cosi) ** 0.5)

    if sint >= 1:  # Total internal reflection
        return 1

    cost = max(0, 1 - sint * sint) ** 0.5
    cosi = abs(cosi)
    Rs = ((etat * cosi) - (etai * cost)) / ((etat * cosi) + (etai * cost))
    Rp = ((etai * cosi) - (etat * cost)) / ((etai * cosi) + (etat * cost))

    return (Rs * Rs + Rp * Rp) / 2


class Raytracer(object):
    def __init__(self, width, height):
        # Constructor
        self.curr_color = (1, 1, 1)
        self.clear_color = (0, 0, 0)
        self.glCreateWindow(width, height)

        self.camPosition = V3(0, 0, 0)
        self.fov = 60

        self.background = None

        self.scene = []

        self.pointLights = []
        self.ambLight = None
        self.dirLight = None

        self.envmap = None

    def glFinish(self, filename):
        # Crea un archivo BMP y lo llena con la información dentro de self.pixels
        with open(filename, "wb") as file:
            # Header
            file.write(bytes('B'.encode('ascii')))
            file.write(bytes('M'.encode('ascii')))
            file.write(dword(14 + 40 + (self.width * self.height * 3)))
            file.write(dword(0))
            file.write(dword(14 + 40))

            # InfoHeader
            file.write(dword(40))
            file.write(dword(self.width))
            file.write(dword(self.height))
            file.write(word(1))
            file.write(word(24))
            file.write(dword(0))
            file.write(dword(self.width * self.height * 3))
            file.write(dword(0))
            file.write(dword(0))
            file.write(dword(0))
            file.write(dword(0))

            # Color Table
            for y in range(self.height):
                for x in range(self.width):
                    file.write(_color(self.pixels[x][y][0],
                                      self.pixels[x][y][1],
                                      self.pixels[x][y][2]))

    def glCreateWindow(self, width, height):
        self.width = width
        self.height = height
        self.glClear()
        self.glViewport(0, 0, width, height)

    def glViewport(self, x, y, width, height):
        self.vpX = int(x)
        self.vpY = int(y)
        self.vpWidth = int(width)
        self.vpHeight = int(height)

    def glClearColor(self, r, g, b):
        self.clear_color = (r, g, b)

    def glClear(self):
        # Crea una lista 2D de pixeles y a cada valor le asigna 3 bytes de color
        self.pixels = [[self.clear_color for y in range(self.height)]
                       for x in range(self.width)]

    def glClearBackground(self):
        if self.background:
            for x in range(self.vpX, self.vpX + self.vpWidth):
                for y in range(self.vpY, self.vpY + self.vpHeight):

                    tx = (x - self.vpX) / self.vpWidth
                    ty = (y - self.vpY) / self.vpHeight

                    self.glPoint(x, y, self.background.getColor(tx, ty))

    def glViewportClear(self, color=None):
        for x in range(self.vpX, self.vpX + self.vpWidth):
            for y in range(self.vpY, self.vpY + self.vpHeight):
                self.glPoint(x, y, color)

    def glColor(self, r, g, b):
        self.curr_color = (r, g, b)

    def glPoint(self, x, y, color=None):
        if x < self.vpX or x >= self.vpX + self.vpWidth or y < self.vpY or y >= self.vpY + self.vpHeight:
            return

        if (0 <= x < self.width) and (0 <= y < self.height):
            self.pixels[int(x)][int(y)] = color or self.curr_color

    def glRender(self):

        for y in range(0, self.height, STEPS):
            for x in range(0, self.width, STEPS):
                # pasar de coordenadas de ventana a coordenadas NDC (-1 a 1)
                Px = 2 * ((x + 0.5) / self.width) - 1
                Py = 2 * ((y + 0.5) / self.height) - 1

                # Angulo de vision, asumiendo que el near plane esta a 1 unidad de la camara
                t = tan((self.fov * pi() / 180) / 2)
                r = t * self.width / self.height

                Px *= r
                Py *= t

                # La camara siempre esta viendo hacia -Z
                direction = V3(Px, Py, -1)
                direction = normalize(direction)

                self.glPoint(x, y, self.cast_ray(self.camPosition, direction))

    def scene_intersect(self, orig, dir, origObj=None):
        depth = float('inf')
        intersect = None

        for obj in self.scene:
            if obj is not origObj:
                hit = obj.ray_intersect(orig, dir)
                if hit != None:
                    if hit.distance < depth:
                        depth = hit.distance
                        intersect = hit

        return intersect

    def cast_ray(self, orig, dir, origObj=None, recursion=0):
        intersect = self.scene_intersect(orig, dir, origObj)

        if intersect == None or recursion >= MAX_RECURSION_DEPTH:
            if self.envmap:
                return self.envmap.getColor(dir)
            return self.clear_color

        material = intersect.sceneObject.material

        # Colors
        finalColor = ([0, 0, 0])
        objectColor = ([material.diffuse[0],
                        material.diffuse[1],
                        material.diffuse[2]])

        ambientColor = ([0, 0, 0])
        dirLightColor = ([0, 0, 0])
        pLightColor = ([0, 0, 0])
        finalSpecColor = ([0, 0, 0])
        reflectColor = ([0, 0, 0])
        refractColor = ([0, 0, 0])

        # Direccion de vista
        view_dir = subtract(self.camPosition, intersect.point)
        view_dir = normalize(view_dir)

        if self.ambLight:
            ambientColor = [(self.ambLight.getColor())]

        if self.dirLight:
            diffuseColor = ([0, 0, 0])
            specColor = ([0, 0, 0])
            shadow_intensity = 0

            # Iluminacion difusa
            light_dir = (self.dirLight.direction) * -1

            # print(type(self.dirLight.intensity))

            intensity = max(0, dotProduct(intersect.normal, light_dir)
                            ) * self.dirLight.intensity

            diffuseColor = ([intensity * self.dirLight.color[0],
                             intensity * self.dirLight.color[1],
                             intensity * self.dirLight.color[2]])

            # Iluminacion especular
            reflect = reflectVector(intersect.normal, light_dir)
            spec_intensity = self.dirLight.intensity * \
                max(0, dotProduct(view_dir, reflect)) ** material.spec
            specColor = ([spec_intensity * self.dirLight.color[0],
                          spec_intensity * self.dirLight.color[1],
                          spec_intensity * self.dirLight.color[2]])

            # Shadow
            shadInter = self.scene_intersect(
                intersect.point, light_dir, intersect.sceneObject)
            if shadInter:
                shadow_intensity = 1

            dirLightColor = (1 - shadow_intensity) * diffuseColor
            finalSpecColor = add(
                finalSpecColor, (1 - shadow_intensity) * specColor)

        for pointLight in self.pointLights:
            diffuseColor = ([0, 0, 0])
            specColor = ([0, 0, 0])
            shadow_intensity = 0

            # Iluminacion difusa
            light_dir = subtract(pointLight.position, intersect.point)
            light_dir = normalize(light_dir)
            intensity = max(0, dotProduct(intersect.normal, light_dir)
                            ) * pointLight.intensity
            diffuseColor = ([intensity * pointLight.color[0],
                             intensity * pointLight.color[1],
                             intensity * pointLight.color[2]])

            # Iluminacion especular
            reflect = reflectVector(intersect.normal, light_dir)
            spec_intensity = pointLight.intensity * \
                max(0, dotProduct(view_dir, reflect)) ** material.spec
            specColor = ([spec_intensity * pointLight.color[0],
                          spec_intensity * pointLight.color[1],
                          spec_intensity * pointLight.color[2]])

            # Shadows
            shadInter = self.scene_intersect(
                intersect.point, light_dir, intersect.sceneObject)
            lightDistance = getVectorMagnitude(subtract(
                pointLight.position, intersect.point))
            if shadInter and shadInter.distance < lightDistance:
                shadow_intensity = 1

            pLightColor = add(
                pLightColor, (1 - shadow_intensity) * diffuseColor)
            finalSpecColor = add(
                finalSpecColor, (1 - shadow_intensity) * specColor)

        if material.matType == OPAQUE:
            finalColor = pLightColor + ambientColor + dirLightColor + finalSpecColor

        elif material.matType == REFLECTIVE:
            reflect = reflectVector(intersect.normal, matriz_negada(dir))
            reflectColor = self.cast_ray(
                intersect.point, reflect, intersect.sceneObject, recursion + 1)
            reflectColor = ([reflectColor[0],
                            reflectColor[1],
                            reflectColor[2]])

            finalColor = reflectColor + finalSpecColor

        elif material.matType == TRANSPARENT:
            outside = dotProduct(dir, intersect.normal) < 0
            bias = 0.001 * intersect.normal
            kr = fresnel(intersect.normal, dir, material.ior)

            reflect = reflectVector(intersect.normal, matriz_negada(dir))
            reflectOrig = add(intersect.point, bias) if outside else subtract(
                intersect.point, bias)
            reflectColor = self.cast_ray(
                reflectOrig, reflect, None, recursion + 1)

            reflectColor = list(reflectColor)

            if kr < 1:
                refract = refractVector(intersect.normal, dir, material.ior)
                refractOrig = subtract(
                    intersect.point, bias) if outside else add(intersect.point, bias)
                refractColor = self.cast_ray(
                    refractOrig, refract, None, recursion + 1)
                refractColor = list(refractColor)

            finalColor = add(add(ml(reflectColor, kr), ml(
                refractColor, (1 - kr))), finalSpecColor)

        # Le aplicamos el color del objeto

        # Nos aseguramos que no suba el valor de color de 1
        r = min(1, finalColor[0])
        g = min(1, finalColor[1])
        b = min(1, finalColor[2])

        return (r, g, b)
