# -*- coding: utf-8 -*-
"""
arranque_kira.py - «Preparando a Kira»: al abrir la app, Kira deja LISTO todo antes de empezar.

  - Oído propio: lo descarga si falta (39 MB) y lo enciende.
  - Cerebro propio: si falta y estás con WiFi, lo descarga (1,4 GB); si ya está, lo carga en la memoria.
    Si el cerebro seguía cargado de antes («Siempre activa»), se usa al momento.
  - Lector: descarga sus idiomas si faltan (6 MB, con WiFi).
  - Pantalla: si ya le diste permiso alguna vez, lo vuelve a pedir (Android lo pide cada vez que se abre la app).
La pantalla es limpia: el fondo de Kira con su botón de neón y, abajo, UNA barra con una línea corta («Descargando
el cerebro… 45 % · quedan 3 min»). Cuando todo está listo entra sola y Kira saluda. «Entrar ya» (discreto, abajo)
entra sin esperar: lo que falte sigue de fondo.
La lógica (Preparacion, progreso) es pura y se prueba en el PC; la pantalla está en montar_arranque.
"""
import threading
import time

PESOS = {"Oído": 1.0, "Cerebro": 6.0, "Lector": 0.5, "Pantalla": 0.3, "Cámara": 0.2, "Ojos": 0.0}
CARGA_CEREBRO = {"ligero": 25.0, "listo": 45.0}      # segundos que suele tardar en cargarse en la memoria


def texto_tiempo(segundos):
    """«quedan unos 20 s» / «quedan 3 min» (None si no se sabe)."""
    if segundos is None:
        return None
    s = max(0, int(segundos))
    if s < 60:
        return f"quedan unos {max(5, round(s / 5) * 5)} s"
    m = round(s / 60)
    return f"quedan {m} min" if m < 90 else f"quedan {m / 60:.1f} h"


class Preparacion:
    def __init__(self, core, oido, ajustes, encender_oido, red=None):
        self.core, self.oido, self.ajustes = core, oido, ajustes
        self._encender_oido = encender_oido
        self._red = red or (lambda: None)
        self.hecho = set()                 # acciones ya lanzadas (cada una, una sola vez)
        self.pantalla_respondida = False
        self._reloj = time.monotonic
        self._carga_desde = None           # cuándo empezó a cargarse el cerebro en la memoria
        self._muestras = []                # [(instante, fracción descargada)] para calcular la velocidad

    def _una_vez(self, clave, accion):
        if clave not in self.hecho:
            self.hecho.add(clave)
            accion()

    def _en_hilo(self, fn):
        threading.Thread(target=fn, daemon=True, name="kira-arranque").start()

    # ---------- cada pieza: (nombre, texto, lista) o None si no aplica ----------
    def _oido(self):
        o = self.oido
        if not (getattr(self.ajustes, "oido_propio", True) and getattr(self.ajustes, "escucha_permanente", True)
                and o.libreria_disponible()):
            return None
        self._una_vez("oido", self._encender_oido)
        if o.estado == "descargando":
            return "Oído", f"descargándolo… {getattr(o, 'progreso', 0) * 100:.0f} %", False
        if o.estado in ("escuchando", "pausa"):
            return "Oído", "listo, te escucho", True
        if o.estado == "error":
            return "Oído", "no arrancó: " + (o.mensaje or "?"), True
        return "Oído", "preparándolo…", False

    def _cerebro(self):
        c = getattr(self.core, "cerebro_propio", None)
        if c is None or not c.tiene_motor():
            return None
        if c.encendido():
            return "Cerebro", "listo", True
        if c.estado == "descargando":
            return "Cerebro", f"descargándolo… {c.progreso * 100:.1f} %", False
        if not c.modelo_instalado():
            if self._red() is True:
                def bajar():
                    try:
                        c.descargar()
                        c.encender()
                        self.core.cerebro_ia.local_disponible(forzar=True)
                    except Exception:
                        pass
                self._una_vez("cerebro_bajar", lambda: self._en_hilo(bajar))
                return "Cerebro", "empezando la descarga (1,4 GB, con WiFi)…", False
            return "Cerebro", "sin descargar: hace falta WiFi (1,4 GB). Menú › Cerebro y oído", True
        if c.estado == "error":
            return "Cerebro", "no arrancó: " + (c.mensaje or "?"), True
        if c.estado != "arrancando":
            self._una_vez("cerebro_encender", lambda: c.encender_en_segundo_plano(
                lambda ok: self.core.cerebro_ia.local_disponible(forzar=True)))
        return "Cerebro", "cargándolo en la memoria…", False

    def _lector(self):
        l = getattr(self.core, "lector", None)
        if l is None or not l.libreria_disponible():
            return None
        if l.idiomas_instalados():
            return "Lector", "listo", True
        if l.estado == "error":
            return "Lector", "no se pudo descargar", True
        if self._red() is True:
            self._una_vez("lector", lambda: self._en_hilo(lambda: _sin_error(l.descargar_idiomas)))
            return "Lector", "descargando idiomas (6 MB)…", False
        return "Lector", "sin idiomas: hace falta WiFi (6 MB)", True

    def _pantalla(self):
        v = getattr(self.core, "vista", None)
        if v is None or not v.disponible() or not v.quiere_ver:
            return None
        if v.puede_ver():
            return "Pantalla", "puede verla cuando se lo pidas", True
        if self.pantalla_respondida:
            return "Pantalla", "sin permiso esta vez", True

        def pedir():
            if v.siempre_activa:
                try:
                    v.java.iniciar(pantalla=False)
                except Exception:
                    pass
            v.pedir_ver(lambda ok: setattr(self, "pantalla_respondida", True))
        self._una_vez("pantalla", pedir)
        return "Pantalla", "Android te pide permiso…", False

    def _ojos(self):
        """Los ojos (visión, ~670 MB): con WiFi se descargan de fondo; no hacen esperar."""
        c = getattr(self.core, "cerebro_propio", None)
        if c is None or not c.tiene_motor() or not c.modelo_instalado() or not hasattr(c, "ojos_instalados"):
            return None
        if c.ojos_instalados():
            return ("Ojos", "listos", True) if c.con_ojos() or c.estado != "arrancando" else ("Ojos", "cargándolos…", True)
        if c.estado == "descargando":
            return "Ojos", f"descargándolos de fondo… {c.progreso * 100:.0f} %", True
        if self._red() is True and c.encendido():
            def bajar():
                try:
                    c.descargar_ojos()
                    c.apagar()
                    c.encender()
                    self.core.cerebro_ia.local_disponible(forzar=True)
                except Exception:
                    pass
            self._una_vez("ojos", lambda: self._en_hilo(bajar))
            return "Ojos", "los descargo de fondo (0,7 GB, con WiFi)", True
        return "Ojos", "sin descargar (hace falta WiFi)", True

    def _camara(self):
        cam = getattr(self.core, "camara", None)
        if cam is None or not cam.disponible():
            return None
        if cam.tiene_permiso():
            return "Cámara", "lista (solo mira cuando se lo pides)", True
        self._una_vez("camara", lambda: _sin_error(cam.java.pedir_permiso))
        return "Cámara", "te pido permiso", True

    def progreso(self):
        """{'fraccion': 0..1, 'texto': una línea corta, 'quedan': segundos o None, 'listo': bool} para la barra."""
        piezas = self.piezas()
        ahora = self._reloj()
        c = getattr(self.core, "cerebro_propio", None)
        o = self.oido
        total = suma = 0.0
        texto, quedan = None, None
        for nombre, _t, lista in piezas:
            peso = PESOS.get(nombre, 0.3)
            frac, linea = 1.0, None
            if not lista:
                frac, linea = 0.5, f"Preparando {nombre.lower()}…"
                if nombre == "Cerebro" and c is not None:
                    if c.estado == "descargando":
                        p = max(0.0, min(1.0, float(getattr(c, "progreso", 0) or 0)))
                        self._muestras = [m for m in self._muestras if ahora - m[0] < 20] + [(ahora, p)]
                        frac = 0.85 * p
                        linea = f"Descargando el cerebro… {p * 100:.0f} %"
                        t0, p0 = self._muestras[0]
                        if ahora - t0 > 2 and p > p0:
                            quedan = (1 - p) * (ahora - t0) / (p - p0) + CARGA_CEREBRO.get(getattr(c, "modelo", ""), 30)
                    elif c.modelo_instalado():
                        if self._carga_desde is None:
                            self._carga_desde = ahora
                        estimado = CARGA_CEREBRO.get(getattr(c, "modelo", ""), 30.0)
                        pasado = ahora - self._carga_desde
                        frac = 0.85 + 0.15 * min(0.95, pasado / estimado)
                        linea = "Despertando el cerebro de Kira…"
                        quedan = max(3.0, estimado - pasado)
                    else:
                        frac, linea = 0.0, "Empezando a descargar el cerebro…"
                elif nombre == "Oído":
                    if getattr(o, "estado", "") == "descargando":
                        p = float(getattr(o, "progreso", 0) or 0)
                        frac, linea = 0.8 * p, f"Descargando el oído… {p * 100:.0f} %"
                    else:
                        frac, linea = 0.9, "Preparando el oído…"
                elif nombre == "Lector":
                    linea = "Descargando el lector…"
                elif nombre == "Pantalla":
                    linea = "Esperando tu permiso para ver la pantalla…"
            total += peso
            suma += peso * frac
            if linea and (texto is None or nombre == "Cerebro"):
                texto = linea                   # lo que más tarda (el cerebro) es lo que se cuenta
        listo = all(l for _n, _t, l in piezas)
        return {"fraccion": 1.0 if listo or total == 0 else suma / total,
                "texto": "¡Lista!" if listo else (texto or "Preparando a Kira…"),
                "quedan": None if listo else quedan, "listo": listo}

    def piezas(self):
        return [p for p in (self._oido(), self._cerebro(), self._ojos(), self._lector(), self._pantalla(),
                            self._camara()) if p]

    def hace_falta(self):
        """¿Merece la pena enseñar «Preparando a Kira»? (algo que preparar en este dispositivo)"""
        return bool(self.piezas())

    def todo_listo(self):
        return all(lista for _n, _t, lista in self.piezas())


def _sin_error(fn):
    try:
        fn()
    except Exception:
        pass


def montar_arranque(sm, p):
    """Pantalla de carga: fondo de Kira y, abajo, una barra con una línea corta. p: boton, fondo_claro, TXT, NEON,
    VERDE, FUENTE, preparacion, al_terminar (y opcionales Portada, TENUE)."""
    from kivy.clock import Clock
    from kivy.graphics import Color, RoundedRectangle
    from kivy.metrics import dp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.label import Label
    from kivy.uix.screenmanager import Screen
    from kivy.uix.widget import Widget
    import escucha_kira as esk
    import estilo_kira as est

    prep, al_terminar = p["preparacion"], p["al_terminar"]
    NEON = p["NEON"]
    TENUE = p.get("TENUE", (0.44, 0.49, 0.56, 1))

    class Barra(Widget):
        """Barra de progreso redondeada (0..1)."""
        def __init__(self, **kw):
            super().__init__(**kw)
            self.valor = 0.0
            with self.canvas:
                Color(0.86, 0.89, 0.93, 1)
                self._pista = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(4)])
                Color(*NEON[:3], 1)
                self._lleno = RoundedRectangle(pos=self.pos, size=(0, self.height), radius=[dp(4)])
            self.bind(pos=self._pintar, size=self._pintar)

        def poner(self, v):
            self.valor = max(0.0, min(1.0, float(v)))
            self._pintar()

        def _pintar(self, *_):
            self._pista.pos, self._pista.size = self.pos, self.size
            self._lleno.pos, self._lleno.size = self.pos, (max(self.height, self.width * self.valor), self.height)

    pant = Screen(name="arranque")
    p["fondo_claro"](pant)
    capa = FloatLayout()
    Portada = p.get("Portada")
    modelo = esk.NeonModelo()
    modelo.poner_estado("pensando")
    fondo = Portada(modelo=modelo, al_tocar=lambda: None) if Portada else Widget()
    capa.add_widget(fondo)
    abajo = BoxLayout(orientation="vertical", size_hint=(1, None), height=dp(118), pos_hint={"x": 0, "y": 0},
                      padding=(dp(28), dp(6), dp(28), dp(10)), spacing=dp(8))
    with abajo.canvas.before:                       # franja blanca: el texto se lee limpio sobre el fondo
        Color(1, 1, 1, 0.92)
        franja = RoundedRectangle(pos=abajo.pos, size=abajo.size, radius=[dp(18), dp(18), 0, 0])
    abajo.bind(pos=lambda w, v: setattr(franja, "pos", v), size=lambda w, v: setattr(franja, "size", v))
    linea = est.ajustar(Label(text="Preparando a Kira…", color=p["TXT"], font_size=est.tam(15), size_hint_y=None,
                              height=dp(26), **p["FUENTE"]), minimo=11, lineas=1)
    barra = Barra(size_hint_y=None, height=dp(8))
    abajo.add_widget(linea)
    abajo.add_widget(barra)
    entrar = Button(text="Entrar ya", size_hint=(None, None), size=(dp(120), dp(36)), pos_hint={"center_x": 0.5},
                    background_normal="", background_down="", background_color=(0, 0, 0, 0), color=TENUE,
                    font_size=est.tam(13), **p["FUENTE"])
    abajo.add_widget(entrar)
    capa.add_widget(abajo)
    pant.add_widget(capa)
    sm.add_widget(pant)
    estado = {"reloj": None, "fin": False}

    def terminar():
        if estado["fin"]:
            return
        estado["fin"] = True
        if estado["reloj"] is not None:
            estado["reloj"].cancel()
        if hasattr(fondo, "detener"):
            fondo.detener()
        al_terminar()
    entrar.bind(on_release=lambda *_: terminar())

    def vuelta(_dt=0):
        pr = prep.progreso()
        barra.poner(pr["fraccion"])
        t = texto_tiempo(pr["quedan"])
        linea.text = pr["texto"] + (f"  ·  {t}" if t else "")
        if pr["listo"] and not estado["fin"]:
            Clock.schedule_once(lambda _dt: terminar(), 0.5)      # deja ver la barra llena un momento

    def empezar():
        if hasattr(fondo, "iniciar"):
            fondo.iniciar()
        vuelta()
        estado["reloj"] = Clock.schedule_interval(vuelta, 0.5)
    return {"empezar": empezar, "terminar": terminar}
