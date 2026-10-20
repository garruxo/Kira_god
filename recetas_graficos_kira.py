# -*- coding: utf-8 -*-
"""
recetas_graficos_kira.py - Recetas de GRÁFICOS y JUEGOS para que Kira programe mejoras (cada una es un módulo
completo y PROBADO: tests/test_saber.py las instala y las juega). Las usa saber_mejoras_kira.
"""

RECETAS = [
{
"id": "particulas",
"titulo": "Sistema de partículas (fuegos artificiales)",
"temas": "particulas particula fuegos artificiales explosion chispas efecto humo lluvia nieve gravedad vida desvanecer",
"idea": "Cada partícula tiene posición, velocidad y VIDA. En cada fotograma: gravedad, mover, restar vida y bajar su "
        "transparencia (alfa). Cuando muere se REUTILIZA (piscina de objetos) para no superar el máximo de piezas.",
"codigo": r'''
import math
import random

def registrar():
    def crear(motor):
        class Fuegos(motor.Juego):
            titulo = "Fuegos artificiales"
            instrucciones = "Toca la pantalla para lanzar una explosión."
            fondo = (0.03, 0.03, 0.08)

            def preparar(self):
                self.libres = []           # piscina: partículas muertas listas para reutilizar
                self.vivas = []
                for _ in range(300):
                    p = self.circulo(-50, -50, 3, (1, 1, 1, 0))
                    self.libres.append(p)

            def explotar(self, x, y):
                r, g, b = random.random(), random.random(), random.random()
                for _ in range(60):
                    if not self.libres:
                        break
                    p = self.libres.pop()
                    a = random.uniform(0, 2 * math.pi)
                    v = random.uniform(40, 220)
                    p.x, p.y, p.vx, p.vy = x, y, math.cos(a) * v, math.sin(a) * v
                    p.datos["vida"] = p.datos["max"] = random.uniform(0.8, 1.6)
                    p.datos["rgb"] = (0.5 + r / 2, 0.5 + g / 2, 0.5 + b / 2)
                    self.vivas.append(p)

            def al_tocar(self, x, y):
                self.explotar(x, y)

            def actualizar(self, dt):
                if random.random() < dt * 0.8:                       # explosiones solas de vez en cuando
                    self.explotar(random.uniform(60, 300), random.uniform(320, 560))
                siguen = []
                for p in self.vivas:
                    p.vy -= 120 * dt                                 # gravedad
                    p.vx *= 0.99
                    p.datos["vida"] -= dt
                    if p.datos["vida"] <= 0:
                        p.x, p.y, p.vx, p.vy = -50, -50, 0, 0
                        p.color = (1, 1, 1, 0)
                        self.libres.append(p)
                    else:
                        a = p.datos["vida"] / p.datos["max"]
                        p.color = p.datos["rgb"] + (a,)
                        siguen.append(p)
                self.vivas = siguen
        return Fuegos
    return {"juego fuegos": crear}
''',
},
{
"id": "arbol_fractal",
"titulo": "Árbol fractal (recursión) animado",
"temas": "fractal arbol recursion recursivo ramas viento naturaleza procedural lineas geometria",
"idea": "Una rama se dibuja y se divide en dos más cortas giradas ±ángulo; la recursión para a cierta profundidad. "
        "Las líneas se crean UNA vez y en cada fotograma solo se recolocan (mover_linea) con un ángulo que oscila.",
"codigo": r'''
import math

def registrar():
    def crear(motor):
        class Arbol(motor.Juego):
            titulo = "Árbol fractal"
            instrucciones = "Mueve el dedo de lado a lado para abrir o cerrar las ramas."
            fondo = (0.95, 0.97, 1.0)

            def preparar(self):
                self.prof = 8
                self.lineas = [self.linea(0, 0, 0, 0, (0.3, 0.2, 0.1), 2) for _ in range(2 ** self.prof)]
                self.apertura = 25.0

            def ramas(self, x, y, ang, largo, nivel, i):
                if nivel == 0:
                    return i
                x2 = x + math.cos(math.radians(ang)) * largo
                y2 = y + math.sin(math.radians(ang)) * largo
                l = self.lineas[i]
                self.mover_linea(l, x, y, x2, y2)
                l.grosor = max(1, nivel * 0.9)
                verde = 1 - nivel / self.prof
                l.color = (0.35 * (1 - verde), 0.25 + 0.55 * verde, 0.1, 1)
                i += 1
                giro = self.apertura + 6 * math.sin(self.tiempo * 1.5 + nivel)
                i = self.ramas(x2, y2, ang - giro, largo * 0.72, nivel - 1, i)
                return self.ramas(x2, y2, ang + giro, largo * 0.72, nivel - 1, i)

            def actualizar(self, dt):
                if self.dedo:
                    self.apertura = 10 + 40 * self.dedo[0] / self.ancho
                self.ramas(180, 40, 90, 140, self.prof, 0)
        return Arbol
    return {"juego arbol fractal": crear}
''',
},
{
"id": "cubo_3d",
"titulo": "Cubo 3D: rotación con matrices y proyección en perspectiva",
"temas": "3d tres dimensiones cubo rotar rotacion matriz proyeccion perspectiva vertices aristas camara alambre",
"idea": "Los vértices (x, y, z) se giran con las fórmulas de rotación en Y y en X y se proyectan: "
        "px = cx + x * f / (z + d). Las aristas son pares de vértices; cada una es una línea que se recoloca.",
"codigo": r'''
import math

VERTICES = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
ARISTAS = [(a, b) for a in range(8) for b in range(a + 1, 8)
           if sum(1 for i in range(3) if VERTICES[a][i] != VERTICES[b][i]) == 1]

def girar_y(p, a):
    x, y, z = p
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))

def girar_x(p, a):
    x, y, z = p
    return (x, y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a))

def proyectar(p, cx=180, cy=320, f=260, d=4):
    x, y, z = p
    k = f / (z + d)
    return (cx + x * k, cy + y * k)

def registrar():
    def crear(motor):
        class Cubo(motor.Juego):
            titulo = "Cubo 3D"
            instrucciones = "Desliza el dedo para girar el cubo."
            fondo = (0.05, 0.06, 0.1)

            def preparar(self):
                self.ay, self.ax = 0.5, 0.4
                self.lineas = [self.linea(0, 0, 0, 0, "cian", 3) for _ in ARISTAS]

            def al_deslizar(self, dx, dy):
                self.ay += dx * 0.01
                self.ax += dy * 0.01

            def actualizar(self, dt):
                if not self.dedo:
                    self.ay += dt * 0.8
                    self.ax += dt * 0.3
                pts = [proyectar(girar_x(girar_y(v, self.ay), self.ax)) for v in VERTICES]
                for l, (a, b) in zip(self.lineas, ARISTAS):
                    self.mover_linea(l, pts[a][0], pts[a][1], pts[b][0], pts[b][1])
        return Cubo
    return {"juego cubo 3d": crear}
''',
},
{
"id": "raycaster",
"titulo": "Raycasting: laberinto en 3D falso (como los primeros juegos de disparos)",
"temas": "raycasting raycaster 3d laberinto paredes primera persona rayos dda mapa wolfenstein doom pseudo3d",
"idea": "Para cada columna de la pantalla se lanza un rayo desde el jugador por la cuadrícula del mapa (DDA). La "
        "distancia a la pared (corregida por el coseno para evitar el ojo de pez) da la altura de la columna.",
"codigo": r'''
import math

MAPA = ["1111111111",
        "1000000001",
        "1011101101",
        "1010000101",
        "1010110101",
        "1000100001",
        "1110101111",
        "1000000001",
        "1111111111"]

def pared(x, y):
    i, j = int(y), int(x)
    if i < 0 or j < 0 or i >= len(MAPA) or j >= len(MAPA[0]):
        return True
    return MAPA[i][j] == "1"

def rayo(px, py, ang):
    dx, dy = math.cos(ang), math.sin(ang)
    mx, my = int(px), int(py)
    paso_x = 1 if dx > 0 else -1
    paso_y = 1 if dy > 0 else -1
    delta_x = abs(1 / dx) if dx else 1e9
    delta_y = abs(1 / dy) if dy else 1e9
    lado_x = ((mx + 1 - px) if dx > 0 else (px - mx)) * delta_x
    lado_y = ((my + 1 - py) if dy > 0 else (py - my)) * delta_y
    for _ in range(64):
        if lado_x < lado_y:
            lado_x += delta_x
            mx += paso_x
            vertical = True
        else:
            lado_y += delta_y
            my += paso_y
            vertical = False
        if pared(mx + 0.5, my + 0.5):
            dist = (lado_x - delta_x) if vertical else (lado_y - delta_y)
            return max(0.05, dist), vertical
    return 20.0, False

def registrar():
    def crear(motor):
        class Laberinto(motor.Juego):
            titulo = "Laberinto 3D"
            instrucciones = "Toca la mitad izquierda o derecha para girar; arriba para avanzar."
            fondo = (0.55, 0.75, 0.95)
            COLUMNAS = 60

            def preparar(self):
                self.rect(0, 0, self.ancho, self.alto / 2, (0.35, 0.32, 0.3))         # suelo
                w = self.ancho / self.COLUMNAS
                self.cols = [self.rect(i * w, 0, w + 1, 0, "gris") for i in range(self.COLUMNAS)]
                self.px, self.py, self.ang = 1.5, 1.5, 0.3

            def actualizar(self, dt):
                if self.dedo:
                    x, y = self.dedo
                    if y > self.alto * 0.66:
                        nx = self.px + math.cos(self.ang) * 2 * dt
                        ny = self.py + math.sin(self.ang) * 2 * dt
                        if not pared(nx, self.py):
                            self.px = nx
                        if not pared(self.px, ny):
                            self.py = ny
                    else:
                        self.ang += (-2 if x < self.ancho / 2 else 2) * dt
                campo = math.radians(66)
                for i, c in enumerate(self.cols):
                    a = self.ang - campo / 2 + campo * i / (self.COLUMNAS - 1)
                    d, vertical = rayo(self.px, self.py, a)
                    d *= math.cos(a - self.ang)                      # sin ojo de pez
                    h = min(self.alto, self.alto * 0.9 / d)
                    c.y, c.h = (self.alto - h) / 2, h
                    luz = max(0.15, min(1.0, 1.4 / d)) * (1.0 if vertical else 0.75)
                    c.color = (0.85 * luz, 0.55 * luz, 0.35 * luz, 1)
        return Laberinto
    return {"juego laberinto 3d": crear}
''',
},
{
"id": "mandelbrot",
"titulo": "Conjunto de Mandelbrot (fractal) dibujado poco a poco",
"temas": "mandelbrot fractal julia numeros complejos iteracion colores pixeles zoom progresivo matematicas",
"idea": "Cada punto c del plano complejo se itera z = z² + c; si |z| supera 2 se escapa, y el número de pasos da el "
        "color. Para no congelar la pantalla, se calcula UNA fila por fotograma (trabajo repartido en el tiempo).",
"codigo": r'''
import math

def color_de(n, tope):
    if n >= tope:
        return (0.02, 0.02, 0.05)
    t = n / tope
    return (0.5 + 0.5 * math.sin(6.3 * t), 0.5 + 0.5 * math.sin(6.3 * t + 2.1), 0.5 + 0.5 * math.sin(6.3 * t + 4.2))

def escapa(cx, cy, tope):
    x = y = 0.0
    for n in range(tope):
        x, y = x * x - y * y + cx, 2 * x * y + cy
        if x * x + y * y > 4:
            return n
    return tope

def registrar():
    def crear(motor):
        class Mandel(motor.Juego):
            titulo = "Mandelbrot"
            instrucciones = "Toca un punto para acercarte allí."
            COLS, FILAS = 32, 48

            def preparar(self):
                self.centro, self.escala = (-0.6, 0.0), 3.0
                w, h = self.ancho / self.COLS, self.alto / self.FILAS
                self.celdas = [[self.rect(i * w, j * h, w + 0.5, h + 0.5, "negro") for i in range(self.COLS)]
                               for j in range(self.FILAS)]
                self.fila = 0

            def al_tocar(self, x, y):
                cx, cy = self.a_plano(x, y)
                self.centro, self.escala, self.fila = (cx, cy), self.escala / 2.5, 0

            def a_plano(self, x, y):
                return (self.centro[0] + (x / self.ancho - 0.5) * self.escala,
                        self.centro[1] + (y / self.alto - 0.5) * self.escala * self.alto / self.ancho)

            def actualizar(self, dt):
                if self.fila >= self.FILAS:
                    return
                tope = 40 + int(20 * math.log2(3.0 / self.escala + 1))
                j = self.fila
                for i, c in enumerate(self.celdas[j]):
                    cx, cy = self.a_plano((i + 0.5) * self.ancho / self.COLS, (j + 0.5) * self.alto / self.FILAS)
                    c.color = color_de(escapa(cx, cy, tope), tope) + (1,)
                self.fila += 1
        return Mandel
    return {"juego mandelbrot": crear}
''',
},
{
"id": "bezier",
"titulo": "Curvas de Bézier con puntos que se arrastran",
"temas": "bezier curva curvas spline interpolar control arrastrar dibujo vectorial trazado suave de casteljau",
"idea": "Una Bézier cúbica mezcla 4 puntos de control: B(t) = (1-t)³P0 + 3(1-t)²tP1 + 3(1-t)t²P2 + t³P3. "
        "Se dibuja con muchos segmentos cortos; tocando cerca de un punto se arrastra.",
"codigo": r'''
def bezier(p, t):
    u = 1 - t
    return (u ** 3 * p[0][0] + 3 * u * u * t * p[1][0] + 3 * u * t * t * p[2][0] + t ** 3 * p[3][0],
            u ** 3 * p[0][1] + 3 * u * u * t * p[1][1] + 3 * u * t * t * p[2][1] + t ** 3 * p[3][1])

def registrar():
    def crear(motor):
        class Curva(motor.Juego):
            titulo = "Curva de Bézier"
            instrucciones = "Arrastra los puntos rojos."
            TRAMOS = 40

            def preparar(self):
                self.ctrl = [[40, 120], [80, 520], [280, 520], [320, 120]]
                self.guias = [self.linea(0, 0, 0, 0, "gris", 1) for _ in range(3)]
                self.tramos = [self.linea(0, 0, 0, 0, "azul", 4) for _ in range(self.TRAMOS)]
                self.bolas = [self.circulo(x, y, 12, "rojo") for x, y in self.ctrl]
                self.cogido = None

            def al_tocar(self, x, y):
                d = [((x - c[0]) ** 2 + (y - c[1]) ** 2, i) for i, c in enumerate(self.ctrl)]
                dist, i = min(d)
                self.cogido = i if dist < 50 ** 2 else None

            def al_soltar(self, x, y):
                self.cogido = None

            def actualizar(self, dt):
                if self.dedo and self.cogido is not None:
                    self.ctrl[self.cogido] = [self.dedo[0], self.dedo[1]]
                for b, c in zip(self.bolas, self.ctrl):
                    b.x, b.y = c
                for g, a, b in zip(self.guias, self.ctrl, self.ctrl[1:]):
                    self.mover_linea(g, a[0], a[1], b[0], b[1])
                prev = bezier(self.ctrl, 0)
                for k, l in enumerate(self.tramos, 1):
                    p = bezier(self.ctrl, k / self.TRAMOS)
                    self.mover_linea(l, prev[0], prev[1], p[0], p[1])
                    prev = p
        return Curva
    return {"juego curva bezier": crear}
''',
},
{
"id": "vida_conway",
"titulo": "Juego de la vida de Conway (autómata celular)",
"temas": "automata celular vida conway celulas cuadricula simulacion reglas vecinos generaciones patrones",
"idea": "Cada celda viva con 2 o 3 vecinas sigue viva; una muerta con exactamente 3 nace. Se calcula la generación "
        "nueva en otra cuadrícula (doble búfer) y solo cada décima de segundo para no gastar en cada fotograma.",
"codigo": r'''
import random

def siguiente(viva, cols, filas):
    nueva = [[False] * cols for _ in range(filas)]
    for j in range(filas):
        for i in range(cols):
            n = 0
            for dj in (-1, 0, 1):
                for di in (-1, 0, 1):
                    if (di or dj) and viva[(j + dj) % filas][(i + di) % cols]:
                        n += 1
            nueva[j][i] = n == 3 or (viva[j][i] and n == 2)
    return nueva

def registrar():
    def crear(motor):
        class Vida(motor.Juego):
            titulo = "Juego de la vida"
            instrucciones = "Toca para dar vida a las células."
            COLS, FILAS = 30, 48

            def preparar(self):
                w, h = self.ancho / self.COLS, self.alto / self.FILAS
                self.viva = [[random.random() < 0.25 for _ in range(self.COLS)] for _ in range(self.FILAS)]
                self.celdas = [[self.rect(i * w + 1, j * h + 1, w - 2, h - 2, "blanco") for i in range(self.COLS)]
                               for j in range(self.FILAS)]
                self.reloj = 0.0
                self.pintar()

            def pintar(self):
                for j in range(self.FILAS):
                    for i in range(self.COLS):
                        self.celdas[j][i].color = (0.15, 0.55, 0.35, 1) if self.viva[j][i] else (0.92, 0.94, 0.96, 1)

            def al_tocar(self, x, y):
                i, j = int(x / self.ancho * self.COLS), int(y / self.alto * self.FILAS)
                for dj in (-1, 0, 1):
                    for di in (-1, 0, 1):
                        self.viva[(j + dj) % self.FILAS][(i + di) % self.COLS] = random.random() < 0.6
                self.pintar()

            def actualizar(self, dt):
                self.reloj += dt
                if self.reloj >= 0.12:
                    self.reloj = 0.0
                    self.viva = siguiente(self.viva, self.COLS, self.FILAS)
                    self.pintar()
        return Vida
    return {"juego vida": crear}
''',
},
{
"id": "boids",
"titulo": "Bandada (boids): separación, alineación y cohesión",
"temas": "boids bandada pajaros peces enjambre comportamiento emergente vectores ia agentes steering separacion",
"idea": "Cada pájaro mira a sus vecinos cercanos: se aleja de los muy próximos (separación), copia su dirección "
        "(alineación) y va hacia su centro (cohesión). La suma limitada de esas tres fuerzas crea la bandada.",
"codigo": r'''
import math
import random

def registrar():
    def crear(motor):
        class Bandada(motor.Juego):
            titulo = "Bandada"
            instrucciones = "Pon el dedo: los pájaros huyen de él."
            fondo = (0.85, 0.92, 1.0)
            N = 30

            def preparar(self):
                self.aves = []
                for _ in range(self.N):
                    t = self.poligono([(0, 8), (-5, -5), (5, -5)], (0.15, 0.2, 0.35))
                    t.x, t.y = random.uniform(40, 320), random.uniform(80, 560)
                    a = random.uniform(0, 6.28)
                    t.datos["v"] = [math.cos(a) * 60, math.sin(a) * 60]
                    self.aves.append(t)

            def actualizar(self, dt):
                for a in self.aves:
                    sep = [0.0, 0.0]; ali = [0.0, 0.0]; coh = [0.0, 0.0]; n = 0
                    for b in self.aves:
                        if a is b:
                            continue
                        dx, dy = b.x - a.x, b.y - a.y
                        d2 = dx * dx + dy * dy
                        if d2 < 60 ** 2:
                            n += 1
                            ali[0] += b.datos["v"][0]; ali[1] += b.datos["v"][1]
                            coh[0] += dx; coh[1] += dy
                            if d2 < 18 ** 2:
                                sep[0] -= dx; sep[1] -= dy
                    v = a.datos["v"]
                    if n:
                        v[0] += (ali[0] / n - v[0]) * 0.05 + coh[0] / n * 0.01 + sep[0] * 0.08
                        v[1] += (ali[1] / n - v[1]) * 0.05 + coh[1] / n * 0.01 + sep[1] * 0.08
                    if self.dedo:
                        dx, dy = a.x - self.dedo[0], a.y - self.dedo[1]
                        d = math.hypot(dx, dy) or 1
                        if d < 100:
                            v[0] += dx / d * 20; v[1] += dy / d * 20
                    if a.x < 20: v[0] += 8
                    if a.x > self.ancho - 20: v[0] -= 8
                    if a.y < 20: v[1] += 8
                    if a.y > self.alto - 20: v[1] -= 8
                    rapidez = math.hypot(v[0], v[1]) or 1
                    tope = max(40, min(120, rapidez))
                    v[0], v[1] = v[0] / rapidez * tope, v[1] / rapidez * tope
                    a.x += v[0] * dt; a.y += v[1] * dt
                    ang = math.atan2(v[1], v[0]) - math.pi / 2
                    c, s = math.cos(ang), math.sin(ang)
                    a.puntos = [(px * c - py * s, px * s + py * c) for px, py in ((0, 8), (-5, -5), (5, -5))]
        return Bandada
    return {"juego bandada": crear}
''',
},
{
"id": "verlet_cuerda",
"titulo": "Física de Verlet: una cuerda que cuelga y se balancea",
"temas": "fisica verlet cuerda tela cadena restricciones muelle simulacion pendulo integracion dinamica",
"idea": "Verlet guarda la posición actual y la anterior: nueva = actual + (actual - anterior) + gravedad·dt². "
        "Después se corrigen varias veces las distancias entre puntos unidos (restricciones) para que no se estiren.",
"codigo": r'''
import math

def registrar():
    def crear(motor):
        class Cuerda(motor.Juego):
            titulo = "Cuerda"
            instrucciones = "Arrastra el extremo de la cuerda."
            N, TRAMO = 20, 18

            def preparar(self):
                self.pos = [[180.0, 600.0 - i * self.TRAMO] for i in range(self.N)]
                self.ant = [p[:] for p in self.pos]
                self.segs = [self.linea(0, 0, 0, 0, "marron", 4) for _ in range(self.N - 1)]
                self.bola = self.circulo(0, 0, 12, "rojo")

            def actualizar(self, dt):
                g = -900 * dt * dt
                for i in range(1, self.N):                      # el punto 0 está clavado
                    x, y = self.pos[i]
                    ax, ay = self.ant[i]
                    self.ant[i] = [x, y]
                    self.pos[i] = [x + (x - ax) * 0.995, y + (y - ay) * 0.995 + g]
                if self.dedo:
                    self.pos[-1] = [self.dedo[0], self.dedo[1]]
                for _ in range(8):                              # restricciones de distancia
                    for i in range(self.N - 1):
                        a, b = self.pos[i], self.pos[i + 1]
                        dx, dy = b[0] - a[0], b[1] - a[1]
                        d = math.hypot(dx, dy) or 1e-6
                        dif = (d - self.TRAMO) / d
                        if i == 0:
                            b[0] -= dx * dif; b[1] -= dy * dif
                        else:
                            a[0] += dx * dif / 2; a[1] += dy * dif / 2
                            b[0] -= dx * dif / 2; b[1] -= dy * dif / 2
                for l, a, b in zip(self.segs, self.pos, self.pos[1:]):
                    self.mover_linea(l, a[0], a[1], b[0], b[1])
                self.bola.x, self.bola.y = self.pos[-1]
        return Cuerda
    return {"juego cuerda": crear}
''',
},
{
"id": "terreno_ruido",
"titulo": "Terreno procedural con ruido suave (montañas que se desplazan)",
"temas": "procedural terreno ruido perlin value noise montañas paisaje generacion aleatoria octavas scroll infinito",
"idea": "Ruido «de valor»: números al azar fijos en puntos enteros e interpolación suave (smoothstep) entre ellos. "
        "Sumando varias OCTAVAS (frecuencia ×2, amplitud ×½) sale un relieve natural. Se dibuja como polígonos.",
"codigo": r'''
import math
import random

class Ruido:
    def __init__(self, semilla=7):
        r = random.Random(semilla)
        self.v = [r.random() for _ in range(256)]

    def suave(self, x):
        i = math.floor(x)
        f = x - i
        f = f * f * (3 - 2 * f)                                  # smoothstep
        a, b = self.v[i % 256], self.v[(i + 1) % 256]
        return a + (b - a) * f

    def octavas(self, x, n=4):
        total, amp, frec, suma = 0.0, 1.0, 1.0, 0.0
        for _ in range(n):
            total += self.suave(x * frec) * amp
            suma += amp
            amp *= 0.5
            frec *= 2
        return total / suma

def registrar():
    def crear(motor):
        class Paisaje(motor.Juego):
            titulo = "Paisaje infinito"
            instrucciones = "Mantén el dedo para ir más deprisa."
            fondo = (0.7, 0.85, 1.0)
            TROZOS = 24

            def preparar(self):
                self.capas = []
                for k, (col, alt, esc) in enumerate((((0.55, 0.6, 0.75), 380, 0.004), ((0.3, 0.5, 0.35), 260, 0.008),
                                                       ((0.2, 0.35, 0.2), 150, 0.015))):
                    trozos = [self.poligono([(0, 0), (1, 0), (1, 1), (0, 1)], col) for _ in range(self.TROZOS)]
                    self.capas.append((Ruido(semilla=k + 3), trozos, alt, esc, 20 * (k + 1)))
                self.x = 0.0

            def actualizar(self, dt):
                self.x += dt * (200 if self.dedo else 60)
                w = self.ancho / self.TROZOS
                for ruido, trozos, alt, esc, vel in self.capas:
                    base = self.x * vel / 60
                    for i, t in enumerate(trozos):
                        x0, x1 = i * w, (i + 1) * w + 0.5
                        y0 = alt * (0.4 + ruido.octavas((base + x0) * esc))
                        y1 = alt * (0.4 + ruido.octavas((base + x1) * esc))
                        self.poner_puntos(t, [(x0, 0), (x1, 0), (x1, y1), (x0, y0)])
        return Paisaje
    return {"juego paisaje": crear}
''',
},
{
"id": "laberinto_dfs",
"titulo": "Generar laberintos (búsqueda en profundidad con vuelta atrás) y jugarlos",
"temas": "laberinto generar generacion dfs backtracking vuelta atras pila cuadricula procedural salida juego",
"idea": "Empieza en una celda, elige al azar un vecino SIN visitar, tira la pared entre ambas y sigue; si no hay "
        "vecinos, vuelve atrás con una pila. Así todas las celdas quedan unidas por un único camino.",
"codigo": r'''
import random

def generar(cols, filas, azar):
    paredes = {(i, j): {"N", "S", "E", "O"} for i in range(cols) for j in range(filas)}
    vistos, pila = {(0, 0)}, [(0, 0)]
    dirs = {"N": (0, 1, "S"), "S": (0, -1, "N"), "E": (1, 0, "O"), "O": (-1, 0, "E")}
    while pila:
        i, j = pila[-1]
        opciones = [(d, i + dx, j + dy, op) for d, (dx, dy, op) in dirs.items()
                    if (i + dx, j + dy) in paredes and (i + dx, j + dy) not in vistos]
        if not opciones:
            pila.pop()
            continue
        d, ni, nj, op = azar.choice(opciones)
        paredes[(i, j)].discard(d)
        paredes[(ni, nj)].discard(op)
        vistos.add((ni, nj))
        pila.append((ni, nj))
    return paredes

def registrar():
    def crear(motor):
        class Laberinto(motor.Juego):
            titulo = "Laberinto"
            instrucciones = "Lleva la bola verde hasta la casilla amarilla con el dedo."
            C, F, T = 9, 15, 36

            def preparar(self):
                self.ox, self.oy = (self.ancho - self.C * self.T) / 2, 40
                self.paredes = generar(self.C, self.F, self.azar_gen)
                self.muros = []
                for (i, j), ps in self.paredes.items():
                    x, y = self.ox + i * self.T, self.oy + j * self.T
                    if "S" in ps: self.muros.append(self.rect(x, y, self.T, 3, "negro"))
                    if "O" in ps: self.muros.append(self.rect(x, y, 3, self.T, "negro"))
                    if i == self.C - 1: self.muros.append(self.rect(x + self.T, y, 3, self.T, "negro"))
                    if j == self.F - 1: self.muros.append(self.rect(x, y + self.T, self.T, 3, "negro"))
                self.meta = self.rect(self.ox + (self.C - 1) * self.T + 6, self.oy + (self.F - 1) * self.T + 6,
                                      self.T - 12, self.T - 12, "amarillo")
                self.celda = (0, 0)
                self.bola = self.circulo(0, 0, 10, "verde")
                self.colocar()

            def colocar(self):
                i, j = self.celda
                self.bola.x, self.bola.y = self.ox + (i + 0.5) * self.T, self.oy + (j + 0.5) * self.T

            def actualizar(self, dt):
                if not self.dedo:
                    return
                dx, dy = self.dedo[0] - self.bola.x, self.dedo[1] - self.bola.y
                if max(abs(dx), abs(dy)) < self.T * 0.6:
                    return
                d = ("E" if dx > 0 else "O") if abs(dx) > abs(dy) else ("N" if dy > 0 else "S")
                i, j = self.celda
                if d not in self.paredes[(i, j)]:
                    di, dj = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "O": (-1, 0)}[d]
                    self.celda = (i + di, j + dj)
                    self.colocar()
                    if self.celda == (self.C - 1, self.F - 1):
                        self.puntos += 1
                        self.ganar("¡Salida encontrada!")
        return Laberinto
    return {"juego laberinto": crear}
''',
},
{
"id": "colores",
"titulo": "Colores: hex ↔ RGB ↔ HSV y paletas armónicas",
"temas": "color colores paleta hex rgb hsv hsl tono saturacion complementario triada analogos degradado diseño",
"idea": "colorsys convierte entre RGB y HSV. Girar el TONO (h) da armonías: complementario +180°, tríada ±120°, "
        "análogos ±30°. Un degradado interpola cada canal: c = a + (b - a)·t.",
"codigo": r'''
import colorsys
import re

def a_rgb(hexa):
    h = hexa.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise ValueError("Dime un color como #ff8800")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

def a_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02x}" for c in rgb)

def girar(rgb, grados):
    h, s, v = colorsys.rgb_to_hsv(*rgb)
    return colorsys.hsv_to_rgb((h + grados / 360) % 1, s, v)

def registrar():
    def paleta(texto):
        partes = texto.split()
        if not partes:
            raise ValueError("Uso: paleta #ff8800")
        base = a_rgb(partes[0])
        h, s, v = colorsys.rgb_to_hsv(*base)
        lineas = [f"Color {a_hex(base)} -> RGB {tuple(round(c * 255) for c in base)}, "
                  f"HSV ({round(h * 360)}°, {round(s * 100)}%, {round(v * 100)}%)",
                  "Complementario: " + a_hex(girar(base, 180)),
                  "Tríada: " + ", ".join(a_hex(girar(base, g)) for g in (120, 240)),
                  "Análogos: " + ", ".join(a_hex(girar(base, g)) for g in (-30, 30))]
        if len(partes) > 1:
            fin = a_rgb(partes[1])
            pasos = [a_hex(tuple(a + (b - a) * t / 4 for a, b in zip(base, fin))) for t in range(5)]
            lineas.append("Degradado: " + " → ".join(pasos))
        return "\n".join(lineas)
    return {"paleta": paleta}
''',
"prueba": [("paleta", "#ff0000 #0000ff", "#00ffff")],
},
{
"id": "ascii_arte",
"titulo": "Arte ASCII: dibujar con letras (Mandelbrot y figuras)",
"temas": "ascii arte texto dibujo letras caracteres consola render rasterizar figura circulo fractal",
"idea": "Rasterizar es decidir, para cada celda de una rejilla, qué tono le toca y elegir un carácter más o menos "
        "«lleno» según su intensidad (de ' .:-=+*#%@').",
"codigo": r'''
import math

RAMPA = " .:-=+*#%@"

def mandelbrot(ancho=48, alto=20):
    filas = []
    for j in range(alto):
        fila = ""
        for i in range(ancho):
            cx, cy = -2.2 + 3.0 * i / ancho, -1.2 + 2.4 * j / alto
            x = y = 0.0
            n = 0
            while n < 30 and x * x + y * y <= 4:
                x, y = x * x - y * y + cx, 2 * x * y + cy
                n += 1
            fila += RAMPA[min(len(RAMPA) - 1, n * len(RAMPA) // 31)]
        filas.append(fila.rstrip())
    return "\n".join(filas)

def circulo(r=8):
    filas = []
    for j in range(-r, r + 1):
        fila = ""
        for i in range(-2 * r, 2 * r + 1):
            d = math.hypot(i / 2, j)
            fila += RAMPA[max(0, min(9, int((r - d) * 3)))] if d <= r else " "
        filas.append(fila.rstrip())
    return "\n".join(filas)

def registrar():
    def dibuja(texto):
        t = texto.lower().replace("í", "i").replace("é", "e").replace("á", "a")
        if "mandel" in t or "fractal" in t:
            return mandelbrot()
        if "circ" in t or "bola" in t or "esfera" in t:
            return circulo()
        raise ValueError("Puedo dibujar: «dibuja en ascii fractal» o «dibuja en ascii círculo».")
    return {"dibuja en ascii": dibuja}
''',
"prueba": [("dibuja en ascii", "fractal", "@"), ("dibuja en ascii", "círculo", "#")],
},
{
"id": "suavizado",
"titulo": "Animación suave: interpolación (easing) y muelles",
"temas": "animacion easing interpolacion lerp suavizado tween muelle spring transicion ease in out rebote",
"idea": "lerp(a, b, t) = a + (b - a)·t. Las funciones de easing deforman t (ease-in-out: 3t² - 2t³; rebote; "
        "elástico). Un muelle amortiguado (v += (objetivo - x)·k - v·d) persigue el dedo de forma natural.",
"codigo": r'''
import math

def ease_in_out(t):
    return t * t * (3 - 2 * t)

def rebote(t):
    if t < 1 / 2.75:
        return 7.5625 * t * t
    if t < 2 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    if t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    t -= 2.625 / 2.75
    return 7.5625 * t * t + 0.984375

def elastico(t):
    if t in (0, 1):
        return t
    return 2 ** (-10 * t) * math.sin((t - 0.075) * 2 * math.pi / 0.3) + 1

def registrar():
    def crear(motor):
        class Suave(motor.Juego):
            titulo = "Animación suave"
            instrucciones = "Mueve el dedo: la bola azul te sigue como un muelle."

            def preparar(self):
                self.bolas = [(self.circulo(40, 520 - k * 110, 14, c), f)
                              for k, (c, f) in enumerate((("rojo", lambda t: t), ("verde", ease_in_out),
                                                          ("naranja", rebote), ("morado", elastico)))]
                self.muelle = self.circulo(180, 80, 18, "azul")
                self.v = [0.0, 0.0]

            def actualizar(self, dt):
                t = (self.tiempo % 2.0) / 2.0
                for b, f in self.bolas:
                    b.x = 40 + (self.ancho - 80) * f(t)
                objetivo = self.dedo or (180, 80)
                for k, eje in ((0, "x"), (1, "y")):
                    pos = getattr(self.muelle, eje)
                    self.v[k] += ((objetivo[k] - pos) * 60 - self.v[k] * 8) * dt
                    setattr(self.muelle, eje, pos + self.v[k] * dt)
        return Suave
    return {"juego animacion suave": crear}
''',
},
{
"id": "colisiones_sat",
"titulo": "Colisiones precisas entre polígonos (teorema del eje separador, SAT)",
"temas": "colision colisiones sat eje separador poligonos convexos fisica choque deteccion normales proyeccion",
"idea": "Dos polígonos convexos NO chocan si existe un eje (la normal de algún lado) en el que sus proyecciones no se "
        "solapan. Se prueban las normales de ambos; si en todas se solapan, chocan.",
"codigo": r'''
import math

def ejes(pts):
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        nx, ny = -(y2 - y1), x2 - x1
        d = math.hypot(nx, ny) or 1
        yield nx / d, ny / d

def proyeccion(pts, eje):
    vals = [x * eje[0] + y * eje[1] for x, y in pts]
    return min(vals), max(vals)

def chocan_sat(a, b):
    for eje in list(ejes(a)) + list(ejes(b)):
        a1, a2 = proyeccion(a, eje)
        b1, b2 = proyeccion(b, eje)
        if a2 < b1 or b2 < a1:
            return False
    return True

def puntos_de(p):
    return [(p.x + dx, p.y + dy) for dx, dy in p.puntos]

def registrar():
    def crear(motor):
        class Choques(motor.Juego):
            titulo = "Choques precisos"
            instrucciones = "Mueve el triángulo: se pone rojo al tocar un obstáculo."

            def preparar(self):
                self.obst = [self.poligono([(60, 300), (160, 340), (120, 420)], "gris"),
                             self.poligono([(220, 150), (320, 170), (300, 260), (210, 240)], "gris"),
                             self.poligono([(200, 450), (300, 430), (330, 530), (240, 560), (190, 520)], "gris")]
                self.yo = self.poligono([(160, 80), (200, 80), (180, 130)], "verde")

            def actualizar(self, dt):
                self.girar(self.yo, 60 * dt)
                for o in self.obst:
                    self.girar(o, -15 * dt)
                if self.dedo:
                    self.yo.x, self.yo.y = self.dedo
                toca = any(chocan_sat(puntos_de(self.yo), puntos_de(o)) for o in self.obst)
                self.yo.color = (0.9, 0.2, 0.25, 1) if toca else (0.2, 0.75, 0.4, 1)
        return Choques
    return {"juego choques": crear}
''',
},
{
"id": "transformaciones",
"titulo": "Matrices de transformación 2D (girar, escalar, mover) compuestas",
"temas": "matriz matrices transformacion afin rotacion escala traslacion homogeneas componer algebra lineal 2d graficos",
"idea": "Con coordenadas homogéneas (x, y, 1) mover, girar y escalar son matrices 3×3; multiplicarlas COMPONE las "
        "transformaciones (el orden importa: primero la de la derecha).",
"codigo": r'''
import math

def mult(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

def mover(dx, dy):
    return [[1, 0, dx], [0, 1, dy], [0, 0, 1]]

def girar(grados):
    a = math.radians(grados)
    return [[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]]

def escalar(sx, sy=None):
    return [[sx, 0, 0], [0, sx if sy is None else sy, 0], [0, 0, 1]]

def aplicar(m, p):
    x, y = p
    return (m[0][0] * x + m[0][1] * y + m[0][2], m[1][0] * x + m[1][1] * y + m[1][2])

def registrar():
    def transforma(texto):
        # ej.: "1 0 girar 90 mover 2 3 escalar 2" -> transforma el punto (1, 0) en ese orden
        t = texto.replace(",", " ").split()
        if len(t) < 2:
            raise ValueError("Uso: transforma X Y girar G mover DX DY escalar S")
        p = (float(t[0]), float(t[1]))
        m = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        i = 2
        pasos = []
        while i < len(t):
            op = t[i].lower()
            if op == "girar":
                m = mult(girar(float(t[i + 1])), m); pasos.append(f"girar {t[i + 1]}°"); i += 2
            elif op == "mover":
                m = mult(mover(float(t[i + 1]), float(t[i + 2])), m); pasos.append(f"mover ({t[i + 1]}, {t[i + 2]})"); i += 3
            elif op == "escalar":
                m = mult(escalar(float(t[i + 1])), m); pasos.append(f"escalar ×{t[i + 1]}"); i += 2
            else:
                raise ValueError(f"No conozco «{op}»: usa girar, mover o escalar.")
        x, y = aplicar(m, p)
        return f"({p[0]:g}, {p[1]:g}) tras {', '.join(pasos) or 'nada'} -> ({x:.3f}, {y:.3f})"
    return {"transforma": transforma}
''',
"prueba": [("transforma", "1 0 girar 90 mover 2 3", "(2.000, 4.000)")],
},
{
"id": "filtros_imagen",
"titulo": "Filtros de imagen en una rejilla: desenfoque, bordes (Sobel) y umbral",
"temas": "imagen filtro filtros convolucion desenfoque blur bordes sobel nitidez kernel pixel procesado vision umbral",
"idea": "Una imagen es una rejilla de números. Un filtro es una CONVOLUCIÓN: cada píxel nuevo es la suma de sus "
        "vecinos multiplicados por un núcleo 3×3 (desenfoque: todo 1/9; Sobel: detecta cambios = bordes).",
"codigo": r'''
import math

SOBEL_X = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
SOBEL_Y = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]
BLUR = [[1 / 9] * 3 for _ in range(3)]

def convolucion(img, k):
    h, w = len(img), len(img[0])
    sal = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            s = 0.0
            for j in range(3):
                for i in range(3):
                    yy, xx = min(h - 1, max(0, y + j - 1)), min(w - 1, max(0, x + i - 1))
                    s += img[yy][xx] * k[j][i]
            sal[y][x] = s
    return sal

def bordes(img):
    gx, gy = convolucion(img, SOBEL_X), convolucion(img, SOBEL_Y)
    return [[math.hypot(a, b) for a, b in zip(fa, fb)] for fa, fb in zip(gx, gy)]

def a_texto(img):
    tope = max(max(f) for f in img) or 1
    return "\n".join("".join(" .:-=+*#%@"[min(9, int(v / tope * 9.99))] for v in f).rstrip() for f in img)

def registrar():
    def filtro(texto):
        # imagen de prueba: un cuadrado claro sobre fondo oscuro
        img = [[1.0 if 4 <= x < 16 and 3 <= y < 9 else 0.0 for x in range(20)] for y in range(12)]
        t = texto.lower()
        if "borde" in t or "sobel" in t:
            return "Bordes (Sobel):\n" + a_texto(bordes(img))
        if "desenfo" in t or "blur" in t:
            return "Desenfoque:\n" + a_texto(convolucion(convolucion(img, BLUR), BLUR))
        return "Original:\n" + a_texto(img) + "\n(prueba «filtro bordes» o «filtro desenfoque»)"
    return {"filtro": filtro}
''',
"prueba": [("filtro", "bordes", "Sobel"), ("filtro", "desenfoque", "Desenfoque")],
},
]
