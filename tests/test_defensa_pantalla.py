# -*- coding: utf-8 -*-
"""Prueba de humo de la PANTALLA del juego de defensa (pantalla_defensa_kira) con el Kivy de mentira: que se monta,
que al abrir juega una partida entera (rondas automáticas) hasta aprender, y que no revienta el cableado (canvas,
Window, Clock, decisiones). No comprueba el dibujo (eso se ve en el móvil)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso
kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
import pantalla_defensa_kira as pdk

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


botones = {}


def boton(texto, accion, color=None, **kw):
    b = Button(text=texto)
    botones[texto] = accion
    return b


def texto_largo(t=""):
    return (Widget(), Label(text=t))


class CoreStub:
    def __init__(self):
        self.dir = tempfile.mkdtemp()


class VozStub:
    def __init__(self):
        self.dichos = []

    def hablar(self, t):
        self.dichos.append(t)


class ConStub:
    activa = True

    def empezar(self, *a, **k): pass
    def linea(self, *a, **k): pass
    def terminar(self, *a, **k): pass
    def codigo_vivo(self, *a, **k): pass
    def poner_codigo(self, *a, **k): pass


sm = ScreenManager()
irs = []
ctx = {"boton": boton, "texto_largo": texto_largo, "FUENTE": {}, "FUENTE_MONO": {},
       "NEON": (0, 1, 1, 1), "VERDE": (0, 1, 0, 1), "ROJO": (1, 0, 0, 1), "TENUE": (.5, .5, .5, 1),
       "GRIS": (.3, .3, .3, 1), "TXT": (1, 1, 1, 1),
       "en_hilo": lambda f, cb: cb(f()), "ir": lambda nombre, *a, **k: (irs.append(nombre), setattr(sm, "current", nombre)),
       "core": CoreStub(), "voz": VozStub(), "ganchos": {}, "dir_datos": tempfile.mkdtemp(), "consola": ConStub()}

d = pdk.montar_defensa(sm, ctx)
ok(isinstance(d, dict) and "abrir" in d and "detener" in d, "montar_defensa devuelve {abrir, detener}")
ok(any(getattr(s, "name", "") == "defensa" for s in sm.children), "añade la pantalla 'defensa' al gestor")

d["abrir"]()
ok(sm.current == "defensa", "al abrir va a la pantalla de defensa")
ok(botones.get("COMBATIR") and botones.get("dejar pasar"), "están los botones COMBATIR / dejar pasar")

# juega la partida: corre el reloj (decisiones automáticas) y, a ratos, decidimos nosotros (abre la ventana de
# código) y la cerramos con «Saltar» / «Comprobar» (no debe petar ni quedarse atascada)
for i in range(240):
    Clock.correr(1, dt=1.0)
    for b in ("COMBATIR", "Saltar", "Comprobar"):
        if botones.get(b):
            try:
                botones[b]()
            except Exception as e:
                ok(False, f"pulsar «{b}» no debe petar: " + repr(e))
                raise SystemExit(1)

# al terminar las rondas, Kira ha guardado sus umbrales (los datos que aprende)
ruta = os.path.join(ctx["core"].dir, "defensa.json")
ok(os.path.exists(ruta), "tras la partida guarda sus defensas (umbrales) en defensa.json")

# salir no revienta
d["detener"]()
ok(True, "detener() sin errores")

print(f"\nDEFENSA PANTALLA OK {n}")
