# -*- coding: utf-8 -*-
"""
portada_kira.py - Portada de Kira (Kivy): fondo BLANCO con la palabra «Kira» repetida por todo el fondo y, en el
centro, un BOTÓN REDONDO rodeado de luz de NEÓN. Tocarlo lleva al menú.
La luz brilla más cuando Kira escucha de verdad (tras oír su nombre) y cuando habla. La lógica está en escucha_kira.
"""
import escucha_kira as ek


def crear_widgets():
    from kivy.clock import Clock
    from kivy.core.text import Label as CoreLabel
    from kivy.graphics import Color, Ellipse, Line, Rectangle
    from kivy.metrics import dp, sp
    from kivy.properties import NumericProperty
    from kivy.uix.widget import Widget

    def textura(texto, tam, negrita=False):
        lb = CoreLabel(text=texto, font_size=tam, bold=negrita)
        lb.refresh()
        return lb.texture

    class PortadaKira(Widget):
        zoom = NumericProperty(1.0)       # la animación de entrada agranda el botón…
        brillo = NumericProperty(1.0)     # …y lo desvanece

        def __init__(self, modelo=None, al_tocar=None, **kw):
            super().__init__(**kw)
            self.modelo = modelo or ek.NeonModelo()
            self.al_tocar = al_tocar
            self._reloj = None
            self._tx_fondo = textura("Kira", sp(30), negrita=True)
            self._tx_boton = textura("KIRA", sp(26), negrita=True)
            self.bind(size=self._fondo, pos=self._fondo)
            self.bind(size=self._dibujar, pos=self._dibujar, zoom=self._dibujar, brillo=self._dibujar)

        # ---- animación ----
        def iniciar(self):
            if self._reloj is None:
                self._reloj = Clock.schedule_interval(self._tick, 1 / 24.0)   # 24 fps: suave y gasta menos

        def detener(self):
            if self._reloj is not None:
                self._reloj.cancel()
                self._reloj = None

        def _tick(self, dt):
            self.modelo.paso(dt)
            self._dibujar()

        # ---- geometría ----
        def centro_boton(self):
            return self.x + self.width / 2.0, self.y + self.height * 0.60

        def radio(self):
            return min(self.width, self.height) * 0.17 * self.zoom

        # ---- fondo blanco con «Kira» por todas partes (solo se redibuja al cambiar de tamaño) ----
        def _fondo(self, *_):
            self.canvas.before.clear()
            with self.canvas.before:
                Color(1, 1, 1, 1)
                Rectangle(pos=self.pos, size=self.size)
                tw, th = self._tx_fondo.size
                Color(0.935, 0.947, 0.975, 1)                 # muy suave: es fondo, no debe distraer
                for x, y in ek.rejilla_letras(self.width, self.height, tw + dp(26), th + dp(22)):
                    Rectangle(texture=self._tx_fondo, pos=(self.x + x, self.y + y), size=(tw, th))

        # ---- botón con neón (las piezas se crean UNA vez; en cada fotograma solo cambian de sitio y de color) ----
        def _crear_piezas(self):
            self.canvas.clear()
            with self.canvas:
                self._halo = [(Color(0, 0, 0, 0), Ellipse()) for _k in range(9)]
                Color(1, 1, 1, 1)
                self._disco = Ellipse()
                self._tubo = [(Color(0, 0, 0, 0), Line(circle=(0, 0, 1), width=ancho))
                              for ancho in (dp(7), dp(4.5), dp(2.5))]
                self._nucleo_c = Color(1, 1, 1, 0)
                self._nucleo = Line(circle=(0, 0, 1), width=dp(1))
                self._letras_c = Color(0, 0, 0, 0)
                self._letras = Rectangle(texture=self._tx_boton, size=self._tx_boton.size)

        def _dibujar(self, *_):
            if self.width < 10 or self.height < 10:
                return
            if getattr(self, "_halo", None) is None:
                self._crear_piezas()
            cx, cy = self.centro_boton()
            R = self.radio()
            g = max(0.0, min(1.0, self.modelo.intensidad)) * max(0.0, min(1.0, self.brillo))
            r, gr, b = self.modelo.color
            for k, (c, e) in zip(range(9, 0, -1), self._halo):    # halo de neón: más ancho y fuerte con g
                ext = R + dp(3) * k * (0.5 + g)
                c.rgba = (r, gr, b, 0.035 * g * (10 - k) / 3.0)
                e.pos, e.size = (cx - ext, cy - ext), (2 * ext, 2 * ext)
            self._disco.pos, self._disco.size = (cx - R, cy - R), (2 * R, 2 * R)
            for (c, ln), alfa in zip(self._tubo, (0.18, 0.35, 0.85)):   # tubo de neón en capas
                c.rgba = (r, gr, b, alfa * (0.45 + 0.55 * g))
                ln.circle = (cx, cy, R)
            self._nucleo_c.rgba = (1, 1, 1, 0.9 * g)                   # núcleo brillante del tubo
            self._nucleo.circle = (cx, cy, R)
            tw, th = self._tx_boton.size
            self._letras_c.rgba = (r * 0.8, gr * 0.8, b * 0.8, 0.55 + 0.45 * g)
            self._letras.pos = (cx - tw / 2, cy - th / 2)

        def on_touch_down(self, touch):
            cx, cy = self.centro_boton()
            if ek.dentro_del_boton(touch.x, touch.y, cx, cy, self.radio()):
                if self.al_tocar:
                    self.al_tocar()
                return True
            return super().on_touch_down(touch)

    return PortadaKira
