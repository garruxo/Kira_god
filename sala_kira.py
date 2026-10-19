# -*- coding: utf-8 -*-
"""
sala_kira.py - Sala inmersiva de Kira (pseudo-3D en Kivy, móvil y PC)

Qué es:  una entrada con tres puertas dibujadas en perspectiva y una "lluvia de código" para la
         Sala Hacker. Es ESTÉTICA: no es realidad virtual ni 3D real, y no añade herramientas de
         hacking. Dentro de la sala sigue estando tu panel real (orden -> laboratorio -> aplicar).

Dos capas:
  - Lógica PURA (sin Kivy): geometria_sala(), puerta_en(), LluviaModelo. Se pueden probar sin pantalla.
  - Widgets Kivy: crear_widgets() devuelve (LluviaCodigo, SalaEntrada).

Puertas:  izquierda = ARCHIVADOR (módulos) | centro = SALA HACKER (orden) | derecha = ESCRITORIO (ajustes)
Ahorro de batería: la lluvia solo se anima mientras su pantalla está visible (iniciar/detener).
"""
import math
import os
import random

PUERTAS_ORDEN = ("archivador", "taller", "escritorio")
NOMBRES_PUERTA = {"archivador": "ARCHIVADOR", "taller": "SALA HACKER", "escritorio": "ESCRITORIO"}
COLORES_PUERTA = {"archivador": (0.25, 0.55, 1.0), "taller": (0.1, 1.0, 0.5), "escritorio": (0.75, 0.45, 1.0)}


# =====================================================================================
#  LÓGICA PURA (sin Kivy)
# =====================================================================================
def geometria_sala(w, h):
    """Calcula la sala en perspectiva para una pantalla de w x h (origen abajo a la izquierda, como Kivy)."""
    w, h = max(float(w), 1.0), max(float(h), 1.0)
    iw, ih = 0.62 * w, 0.38 * h                     # pared del fondo
    x0, y0 = (w - iw) / 2, 0.38 * h
    x1, y1 = x0 + iw, y0 + ih

    polis = {"suelo": [0, 0, w, 0, x1, y0, x0, y0], "techo": [0, h, w, h, x1, y1, x0, y1],
             "izquierda": [0, 0, x0, y0, x0, y1, 0, h], "derecha": [w, 0, x1, y0, x1, y1, w, h]}

    lineas = []
    for k in range(7):                                # líneas que convergen en el fondo
        xb, xt = w * k / 6, x0 + iw * k / 6
        lineas += [((xb, 0), (xt, y0)), ((xb, h), (xt, y1))]
    for k in range(5):
        lineas += [((0, h * k / 4), (x0, y0 + ih * k / 4)), ((w, h * k / 4), (x1, y0 + ih * k / 4))]
    for u in (0.2, 0.4, 0.6, 0.8):                    # líneas de profundidad, más juntas al fondo
        s = 1 - (1 - u) ** 2
        xl, xr = x0 * s, w - (w - x1) * s
        ys, yt = y0 * s, h - (h - y1) * s
        lineas += [((xl, ys), (xr, ys)), ((xl, yt), (xr, yt)), ((xl, ys), (xl, yt)), ((xr, ys), (xr, yt))]

    puertas, etiquetas, anchos = {}, {}, {}
    for nombre, fx, fw, fh in (("archivador", 0.17, 0.22, 0.74), ("taller", 0.50, 0.30, 0.88),
                               ("escritorio", 0.83, 0.22, 0.74)):
        cx, dw, dh = x0 + iw * fx, iw * fw, ih * fh
        puertas[nombre] = (cx - dw / 2, y0, dw, dh)
        etiquetas[nombre] = (cx, y0 + dh)
        anchos[nombre] = dw * (1.3 if nombre == "taller" else 1.2)  # el texto se encoge para caber
    return {"ancho": w, "alto": h, "fondo": (x0, y0, iw, ih), "polis": polis, "lineas": lineas,
            "puertas": puertas, "etiquetas": etiquetas, "etiquetas_ancho": anchos}


def puerta_en(geo, x, y, margen=6.0):
    """Nombre de la puerta bajo el punto (x, y), con un margen extra para dedos gordos; None si no hay."""
    for nombre in PUERTAS_ORDEN:
        rx, ry, rw, rh = geo["puertas"][nombre]
        if rx - margen <= x <= rx + rw + margen and ry - margen <= y <= ry + rh + margen:
            return nombre
    return None


class LluviaModelo:
    """Lluvia de código estilo Matrix: cada columna es una cabeza que baja dejando una estela."""
    CARACTERES = "01ABCDEFGHJKLMNPRSTUVWXYZ23456789<>/{}[]#$%&*+=-"

    def __init__(self, columnas, filas, semilla=None):
        self.columnas, self.filas = max(1, int(columnas)), max(1, int(filas))
        self.rng = random.Random(semilla)
        self.cols = [self._nueva(inicial=True) for _ in range(self.columnas)]

    def _nueva(self, inicial=False):
        r = self.rng
        return {"cabeza": r.uniform(-self.filas, self.filas) if inicial else -r.uniform(0, self.filas * 0.6),
                "vel": r.uniform(4, 14), "largo": r.randint(5, max(6, min(18, self.filas))),
                "chars": [r.choice(self.CARACTERES) for _ in range(self.filas)]}

    def paso(self, dt):
        dt = max(0.0, min(float(dt), 1.0))
        for i, c in enumerate(self.cols):
            c["cabeza"] += c["vel"] * dt
            if c["cabeza"] - c["largo"] > self.filas:
                self.cols[i] = self._nueva()
            elif self.rng.random() < 0.15:
                c["chars"][self.rng.randrange(self.filas)] = self.rng.choice(self.CARACTERES)

    def celdas(self):
        """Lista de (columna, fila, caracter, opacidad, es_cabeza) visibles ahora mismo."""
        salida = []
        for ci, c in enumerate(self.cols):
            cab = math.floor(c["cabeza"])
            for k in range(c["largo"]):
                f = cab - k
                if 0 <= f < self.filas:
                    alfa = 1.0 if k == 0 else max(0.06, (1 - k / c["largo"]) * 0.8)
                    salida.append((ci, f, c["chars"][f], alfa, k == 0))
        return salida


# =====================================================================================
#  WIDGETS KIVY
# =====================================================================================
def crear_widgets():
    from kivy import kivy_data_dir
    from kivy.animation import Animation
    from kivy.clock import Clock
    from kivy.core.text import Label as CoreLabel
    from kivy.graphics import Color, Line, Quad, Rectangle
    from kivy.metrics import dp, sp
    from kivy.properties import NumericProperty
    from kivy.uix.widget import Widget

    ruta_fuente = os.path.join(kivy_data_dir, "fonts", "RobotoMono-Regular.ttf")
    fuente = ruta_fuente if os.path.exists(ruta_fuente) else None
    cache = {}

    def textura(texto, tam):
        """Textura blanca del texto (se tiñe al dibujar). Se crea al primer uso, ya con el contexto gráfico listo."""
        clave = (texto, tam)
        if clave not in cache:
            kw = {"text": texto, "font_size": tam}
            if fuente:
                kw["font_name"] = fuente
            nucleo = CoreLabel(**kw)
            nucleo.refresh()
            cache[clave] = nucleo.texture
        return cache[clave]

    def ajustada(texto, tam, ancho_max):
        """Textura del texto, encogida si no cabe en ancho_max (nunca por debajo de 8 sp)."""
        tex = textura(texto, tam)
        if tex.width <= ancho_max:
            return tex
        return textura(texto, max(sp(8), int(tam * ancho_max / tex.width)))

    class LluviaCodigo(Widget):
        opacidad = NumericProperty(0.45)

        def __init__(self, **kw):
            super().__init__(**kw)
            self.modelo, self._evento, self._celda = None, None, None
            self.bind(size=self._reiniciar, pos=self._reiniciar)

        def _reiniciar(self, *_):
            if self.width < 10 or self.height < 10:
                return
            muestra = textura("W", sp(14))
            self._celda = (max(muestra.width, 1), max(muestra.height, 1))
            self.modelo = LluviaModelo(int(self.width // self._celda[0]), int(self.height // self._celda[1]))
            self._dibujar()

        def iniciar(self):
            if self.modelo is None:
                self._reiniciar()  # no depender de que Kivy ya haya avisado del tamaño
            if self._evento is None:
                self._evento = Clock.schedule_interval(self._paso, 1 / 15.0)

        def detener(self):
            if self._evento is not None:
                self._evento.cancel()
                self._evento = None

        def _paso(self, dt):
            if self.modelo is not None:
                self.modelo.paso(dt)
                self._dibujar()

        def _dibujar(self):
            self.canvas.clear()
            with self.canvas:
                Color(0.01, 0.03, 0.02, 1)
                Rectangle(pos=self.pos, size=self.size)
                if self.modelo is None or self._evento is None:
                    return  # parada: solo el fondo (no gasta batería)
                cw, ch = self._celda
                for col, fila, car, alfa, cabeza in self.modelo.celdas():
                    tex = textura(car, sp(14))
                    if cabeza:
                        Color(0.8, 1.0, 0.85, min(1.0, alfa * self.opacidad * 2))
                    else:
                        Color(0.1, 0.9, 0.4, alfa * self.opacidad)
                    Rectangle(texture=tex, pos=(self.x + col * cw, self.top - (fila + 1) * ch), size=tex.size)

    class SalaEntrada(Widget):
        abre = NumericProperty(0)

        def __init__(self, al_entrar=None, **kw):
            super().__init__(**kw)
            self.al_entrar, self.geo, self.puerta_activa, self._animando = al_entrar, None, None, False
            self.animar = True  # False = entrar sin animación (ahorra batería)
            self.bind(size=self._redibujar, pos=self._redibujar, abre=self._redibujar)

        def _redibujar(self, *_):
            if self.width < 10 or self.height < 10:
                return
            g = self.geo = geometria_sala(self.width, self.height)
            ox, oy = self.x, self.y

            def mover(pts):
                return [v + (ox if i % 2 == 0 else oy) for i, v in enumerate(pts)]

            self.canvas.clear()
            with self.canvas:
                Color(0.01, 0.02, 0.03, 1)
                Rectangle(pos=self.pos, size=self.size)
                for nombre, rgba in (("suelo", (0.02, 0.09, 0.06, 1)), ("techo", (0.02, 0.04, 0.07, 1)),
                                     ("izquierda", (0.03, 0.06, 0.09, 1)), ("derecha", (0.03, 0.06, 0.09, 1))):
                    Color(*rgba)
                    Quad(points=mover(g["polis"][nombre]))
                Color(0.1, 0.9, 0.5, 0.32)
                for (xa, ya), (xb, yb) in g["lineas"]:
                    Line(points=[xa + ox, ya + oy, xb + ox, yb + oy], width=1)
                x0, y0, iw, ih = g["fondo"]
                Color(0.04, 0.06, 0.09, 1)
                Rectangle(pos=(x0 + ox, y0 + oy), size=(iw, ih))
                for nombre in PUERTAS_ORDEN:
                    rx, ry, rw, rh = g["puertas"][nombre]
                    rx, ry = rx + ox, ry + oy
                    r, gg, b = COLORES_PUERTA[nombre]
                    activa = nombre == self.puerta_activa
                    prog = self.abre if activa else 0.0
                    Color(r, gg, b, 0.12)                                   # resplandor
                    Rectangle(pos=(rx - dp(5), ry - dp(5)), size=(rw + dp(10), rh + dp(10)))
                    Color(r, gg, b, 0.25 + 0.7 * prog)                      # luz del interior
                    Rectangle(pos=(rx, ry), size=(rw, rh))
                    Color(r * 0.18, gg * 0.18, b * 0.18, 1)                 # hoja de la puerta (se abre)
                    Rectangle(pos=(rx, ry), size=(rw * (1 - prog), rh))
                    Color(r, gg, b, 1)
                    Line(rectangle=(rx, ry, rw, rh), width=dp(1.6))
                    tex = ajustada(NOMBRES_PUERTA[nombre], sp(12), g["etiquetas_ancho"][nombre])
                    ex, ey = g["etiquetas"][nombre]
                    Color(r, gg, b, 1)
                    Rectangle(texture=tex, size=tex.size, pos=(ex + ox - tex.width / 2, ey + oy + dp(6)))
                pista = textura("toca una puerta para entrar", sp(12))
                Color(0.6, 0.9, 0.75, 0.7)
                Rectangle(texture=pista, size=pista.size, pos=(self.center_x - pista.width / 2, self.y + dp(14)))

        def on_touch_down(self, touch):
            if not self.collide_point(*touch.pos) or self.geo is None or self._animando:
                return super().on_touch_down(touch)
            nombre = puerta_en(self.geo, touch.x - self.x, touch.y - self.y, margen=dp(6))
            if nombre is None:
                return super().on_touch_down(touch)
            if not self.animar:
                if self.al_entrar:
                    self.al_entrar(nombre)
                return True
            self._animando, self.puerta_activa = True, nombre
            anim = Animation(abre=1.0, duration=0.55, t="in_quad")
            anim.bind(on_complete=lambda *_: self._terminar(nombre))
            anim.start(self)
            return True

        def _terminar(self, nombre):
            self.abre, self.puerta_activa, self._animando = 0, None, False
            if self.al_entrar:
                self.al_entrar(nombre)

    return LluviaCodigo, SalaEntrada
