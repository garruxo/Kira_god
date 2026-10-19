# -*- coding: utf-8 -*-
"""
motor_juegos_kira.py - Motor de JUEGOS 2D de Kira (lógica PURA: no dibuja, no usa Kivy; solo math y random).

Para programar un juego:
    from motor_juegos_kira import Juego

    class MiJuego(Juego):
        titulo = "Mi juego"
        def preparar(self):                 # al empezar (y al reiniciar)
            self.nave = self.rect(170, 40, 40, 20, "azul")
        def actualizar(self, dt):           # 60 veces por segundo; dt = segundos desde el anterior
            if self.dedo:                   # (x, y) donde está tocando el dedo, o None
                self.nave.x = self.dedo[0] - self.nave.w / 2
        def al_tocar(self, x, y):           # un toque
            pass

Coordenadas: el juego mide self.ancho x self.alto (360 x 640 por defecto), con (0, 0) ABAJO a la izquierda.
La pantalla de juegos lo escala para que quepa en cualquier móvil.
Piezas: rect(), circulo(), texto(); cada una tiene x, y, w, h (o r), vx, vy, color y viva.
Física: con vx/vy se mueven solas; self.gravedad tira hacia abajo de las que tengan cae=True.
Ayudas: chocan(a, b), rebotar_en_bordes(e), dentro(e), azar(a, b), fin("mensaje"), ganar("mensaje").
"""
import math
import random

COLORES = {
    "blanco": (1, 1, 1), "negro": (0.08, 0.08, 0.1), "gris": (0.55, 0.58, 0.62), "rojo": (0.92, 0.26, 0.3),
    "verde": (0.2, 0.78, 0.45), "azul": (0.2, 0.5, 0.95), "cian": (0.0, 0.78, 1.0), "amarillo": (1.0, 0.82, 0.2),
    "naranja": (1.0, 0.55, 0.15), "rosa": (1.0, 0.35, 0.72), "morado": (0.6, 0.35, 0.95), "marron": (0.55, 0.35, 0.2),
}
MAX_PIEZAS = 2000


def color(c):
    """'rojo' | (r, g, b) | (r, g, b, a) -> (r, g, b, a) con valores de 0 a 1."""
    if isinstance(c, str):
        r, g, b = COLORES.get(c.lower(), COLORES["blanco"])
        return (r, g, b, 1.0)
    t = tuple(float(v) for v in c)
    if len(t) == 3:
        t = t + (1.0,)
    if len(t) != 4:
        raise ValueError("color: usa un nombre o (r, g, b) entre 0 y 1")
    return tuple(max(0.0, min(1.0, v)) for v in t)


class Pieza:
    def __init__(self, forma, x, y, w=0.0, h=0.0, col="blanco", texto="", tam=24):
        self.forma = forma                  # 'rect' | 'circulo' | 'texto'
        self.x, self.y, self.w, self.h = float(x), float(y), float(w), float(h)
        self.vx = self.vy = 0.0
        self.color = color(col)
        self.texto, self.tam = str(texto), int(tam)
        self.viva = True
        self.cae = False                    # ¿le afecta la gravedad?
        self.datos = {}                     # para lo que quieras guardar en ella

    # para círculos: (x, y) es el CENTRO y r el radio
    @property
    def r(self):
        return self.w / 2.0

    @r.setter
    def r(self, v):
        self.w = self.h = 2.0 * float(v)

    def caja(self):
        """(izquierda, abajo, derecha, arriba)"""
        if self.forma == "circulo":
            return (self.x - self.r, self.y - self.r, self.x + self.r, self.y + self.r)
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    @property
    def centro(self):
        if self.forma == "circulo":
            return (self.x, self.y)
        return (self.x + self.w / 2.0, self.y + self.h / 2.0)


def chocan(a, b):
    """¿Se tocan dos piezas? (círculo-círculo exacto; el resto, por cajas)."""
    if not (a.viva and b.viva):
        return False
    if a.forma == b.forma == "circulo":
        return math.hypot(a.x - b.x, a.y - b.y) <= a.r + b.r
    if "circulo" in (a.forma, b.forma):
        c, r = (a, b) if a.forma == "circulo" else (b, a)
        x1, y1, x2, y2 = r.caja()
        px, py = max(x1, min(c.x, x2)), max(y1, min(c.y, y2))
        return math.hypot(c.x - px, c.y - py) <= c.r
    a1, b1, a2, b2 = a.caja()
    c1, d1, c2, d2 = b.caja()
    return a1 < c2 and c1 < a2 and b1 < d2 and d1 < b2


class Juego:
    titulo = "Juego"
    instrucciones = ""
    ancho, alto = 360, 640
    fondo = (0.97, 0.98, 1.0)

    def __init__(self, semilla=None):
        self.azar_gen = random.Random(semilla)
        self.reiniciar()

    # ---------- lo que programas tú ----------
    def preparar(self):
        pass

    def actualizar(self, dt):
        pass

    def al_tocar(self, x, y):
        pass

    def al_soltar(self, x, y):
        pass

    def al_deslizar(self, dx, dy):
        """Deslizar el dedo: dx, dy en unidades del juego (útil para la serpiente)."""
        pass

    # ---------- motor ----------
    def reiniciar(self):
        self.piezas = []
        self.puntos = 0
        self.vidas = 3
        self.estado = "jugando"             # 'jugando' | 'fin' | 'ganado' | 'pausa'
        self.mensaje = ""
        self.tiempo = 0.0
        self.gravedad = 0.0
        self.dedo = None
        self.preparar()

    def paso(self, dt):
        """Un fotograma. La pantalla lo llama ~60 veces por segundo."""
        dt = max(0.0, min(float(dt), 0.05))
        if self.estado != "jugando":
            return
        self.tiempo += dt
        self.actualizar(dt)
        for p in self.piezas:
            if p.cae:
                p.vy -= self.gravedad * dt
            if p.vx or p.vy:
                if p.forma == "circulo":
                    p.x += p.vx * dt
                    p.y += p.vy * dt
                else:
                    p.x += p.vx * dt
                    p.y += p.vy * dt
        self.piezas = [p for p in self.piezas if p.viva]

    def tocar(self, x, y):
        if self.estado in ("fin", "ganado"):
            self.reiniciar()
            return
        self.dedo = (x, y)
        if self.estado == "jugando":
            self.al_tocar(x, y)

    def mover_dedo(self, x, y, dx=0.0, dy=0.0):
        self.dedo = (x, y)
        if self.estado == "jugando" and (dx or dy):
            self.al_deslizar(dx, dy)

    def soltar(self, x, y):
        self.dedo = None
        if self.estado == "jugando":
            self.al_soltar(x, y)

    def pausar(self):
        if self.estado == "jugando":
            self.estado = "pausa"
        elif self.estado == "pausa":
            self.estado = "jugando"

    # ---------- piezas ----------
    def _nueva(self, p):
        if len(self.piezas) >= MAX_PIEZAS:
            raise RuntimeError(f"demasiadas piezas (máximo {MAX_PIEZAS}): borra las que ya no uses (p.viva = False)")
        self.piezas.append(p)
        return p

    def rect(self, x, y, w, h, col="blanco"):
        return self._nueva(Pieza("rect", x, y, w, h, col))

    def circulo(self, x, y, r, col="blanco"):
        return self._nueva(Pieza("circulo", x, y, 2 * r, 2 * r, col))

    def texto(self, x, y, texto, tam=24, col="negro"):
        return self._nueva(Pieza("texto", x, y, 0, 0, col, texto=texto, tam=tam))

    def borrar(self, p):
        p.viva = False

    def con_etiqueta(self, nombre):
        return [p for p in self.piezas if p.viva and p.datos.get("tipo") == nombre]

    # ---------- ayudas ----------
    chocan = staticmethod(chocan)

    def dentro(self, p):
        x1, y1, x2, y2 = p.caja()
        return x2 > 0 and x1 < self.ancho and y2 > 0 and y1 < self.alto

    def rebotar_en_bordes(self, p, suelo=True):
        """Rebota en las paredes y el techo (y en el suelo si suelo=True). Devuelve qué borde tocó o ''."""
        x1, y1, x2, y2 = p.caja()
        borde = ""
        if x1 < 0 and p.vx < 0:
            p.vx, borde = -p.vx, "izquierda"
        if x2 > self.ancho and p.vx > 0:
            p.vx, borde = -p.vx, "derecha"
        if y2 > self.alto and p.vy > 0:
            p.vy, borde = -p.vy, "arriba"
        if y1 < 0 and p.vy < 0:
            if suelo:
                p.vy = -p.vy
            borde = "abajo"
        return borde

    def limitar(self, p):
        """Que no se salga de la pantalla."""
        x1, y1, x2, y2 = p.caja()
        if x1 < 0:
            p.x -= x1
        if x2 > self.ancho:
            p.x -= x2 - self.ancho
        if y1 < 0:
            p.y -= y1
        if y2 > self.alto:
            p.y -= y2 - self.alto

    def azar(self, a, b):
        return self.azar_gen.uniform(a, b)

    def azar_entero(self, a, b):
        return self.azar_gen.randint(a, b)

    def fin(self, mensaje="Fin de la partida"):
        self.estado, self.mensaje = "fin", str(mensaje)

    def ganar(self, mensaje="¡Has ganado!"):
        self.estado, self.mensaje = "ganado", str(mensaje)

    # ---------- lo que dibuja la pantalla ----------
    def dibujo(self):
        """[(forma, x, y, w, h, (r,g,b,a), texto, tam)] en coordenadas del juego."""
        return [(p.forma, p.x, p.y, p.w, p.h, p.color, p.texto, p.tam) for p in self.piezas if p.viva]

    def marcador(self):
        base = f"Puntos: {self.puntos}   Vidas: {self.vidas}"
        if self.estado == "pausa":
            return base + "   (pausa)"
        if self.estado in ("fin", "ganado"):
            return f"{self.mensaje}  —  {self.puntos} puntos. Toca para jugar otra vez."
        return base


def buscar_juego(globales):
    """La clase de juego que define un programa (la última subclase de Juego), o None."""
    candidatas = [v for v in globales.values() if isinstance(v, type) and issubclass(v, Juego) and v is not Juego]
    return candidatas[-1] if candidatas else None
