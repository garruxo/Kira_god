# -*- coding: utf-8 -*-
"""
arranque_kira.py - «Preparando a Kira»: al abrir la app, Kira deja LISTO todo antes de empezar.

  - Oído propio: lo descarga si falta (39 MB) y lo enciende.
  - Cerebro propio: si falta y estás con WiFi, lo descarga (1,4 GB); si ya está, lo carga en la memoria.
    Si el cerebro seguía cargado de antes («Siempre activa»), se usa al momento.
  - Lector: descarga sus idiomas si faltan (6 MB, con WiFi).
  - Pantalla: si ya le diste permiso alguna vez, lo vuelve a pedir (Android lo pide cada vez que se abre la app).
Mientras, enseña una lista con cómo va cada cosa. «Entrar ya» entra sin esperar (lo que falte sigue de fondo).
La lógica (Preparacion) es pura y se prueba en el PC; la pantalla está en montar_arranque.
"""
import threading


class Preparacion:
    def __init__(self, core, oido, ajustes, encender_oido, red=None):
        self.core, self.oido, self.ajustes = core, oido, ajustes
        self._encender_oido = encender_oido
        self._red = red or (lambda: None)
        self.hecho = set()                 # acciones ya lanzadas (cada una, una sola vez)
        self.pantalla_respondida = False

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
    """Pantalla «Preparando a Kira». p: boton, fondo_claro, TXT, NEON, VERDE, FUENTE, preparacion, al_terminar."""
    from kivy.clock import Clock
    from kivy.metrics import dp, sp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.screenmanager import Screen
    from kivy.uix.widget import Widget

    prep, al_terminar = p["preparacion"], p["al_terminar"]
    pant = Screen(name="arranque")
    p["fondo_claro"](pant)
    caja = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(12))
    caja.add_widget(Widget(size_hint_y=0.25))
    caja.add_widget(Label(text="Preparando a Kira…", color=p["NEON"], font_size=sp(24), bold=True,
                          size_hint_y=None, height=dp(44), **p["FUENTE"]))
    lista = Label(text="", color=p["TXT"], font_size=sp(16), halign="left", valign="top",
                  size_hint_y=None, height=dp(200), **p["FUENTE"])
    lista.bind(width=lambda w, a: setattr(w, "text_size", (a, None)))
    caja.add_widget(lista)
    est = {"reloj": None, "fin": False}

    def terminar():
        if est["fin"]:
            return
        est["fin"] = True
        if est["reloj"] is not None:
            est["reloj"].cancel()
        al_terminar()

    caja.add_widget(p["boton"]("Entrar ya", terminar, p["VERDE"]))
    caja.add_widget(Widget())
    pant.add_widget(caja)
    sm.add_widget(pant)
    marca = {True: "[OK]", False: "[..]"}

    def vuelta(_dt=0):
        piezas = prep.piezas()
        lista.text = "\n\n".join(f"{marca[ok]}  {n}: {t}" for n, t, ok in piezas)
        if all(ok for _n, _t, ok in piezas):
            Clock.schedule_once(lambda _dt: terminar(), 0.6)      # deja ver el último «listo»

    def empezar():
        vuelta()
        est["reloj"] = Clock.schedule_interval(vuelta, 0.5)
    return {"empezar": empezar, "terminar": terminar}
