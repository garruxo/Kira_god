# -*- coding: utf-8 -*-
"""Cableado de la Sala de Ciberseguridad con un Kivy falso."""
import sys, os, tempfile, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import kira_god, salas_kira as sk, habitacion_kira as hk, ciber_kira as ck
core = kira_god.KiraGodCore(); core._leer_clave = lambda: ""
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
from kivy.core.window import Window as W2
tecla = W2._b["on_keyboard"][0]
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
def P(nombre): return sm.get_screen(nombre)
def botones(raiz): return [w for w in raiz.walk() if type(w).__name__ == "Button"]
def boton(raiz, t): return next(b for b in botones(raiz) if b.text == t)
def boton_pre(raiz, p): return next(b for b in botones(raiz) if b.text.startswith(p))
def textos(raiz): return [w.text for w in raiz.walk() if type(w).__name__ == "Label"]
def esperar(cond, seg=4):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.1)
        if cond(): return True
        time.sleep(0.03)
    return False

import menu_kira as mk
ok(any(a["id"] == "ciber" and a["destino"] == ("pantalla", "sala_ciber") for a in mk.APARTADOS), "el menú tiene la sala de ciber")
ok(all(any(s.name == d for s in sm.children) for d in ("sala_ciber", "centro")), "las pantallas existen")

sm.ir("sala_ciber")
hc = next(w for w in P("sala_ciber").walk() if type(w).__name__ == "HabitacionWidget")
ok(hc.rec.cfg is sk.CFG_CIBER and hc.rec.estado == "caminando", "entra caminando en el búnker")
Clock.correr(120, 0.05); ok(hc.rec.estado == "libre", "llega a la consola")
ok({b.text for b in botones(P("sala_ciber"))} >= {"Salir", "< Dispositivo", "Kira (centro)", "Salir >"}, "botones de la sala")
# tocar la pantalla central
hc.rec.pose = sk.POSE_X_MESA
class Toque:
    def __init__(s, x, y): s.x, s.y, s.pos, s.dx, s.dy, s.grab_current = x, y, (x, y), 0, 0, None
    def grab(s, w): s.grab_current = w
    def ungrab(s, w): s.grab_current = None
mx, my = hk.proyectar(hk.a_camara((0, 1.45, 7.8), sk.POSE_X_MESA), 100, 100, 90)
t = Toque(mx, my); hc.on_touch_down(t); hc.on_touch_up(t); ok(hc.rec.estado == "yendo", "tocar la pantalla te acerca")
Clock.correr(60, 0.05); Clock.correr(20, 0.05); ok(sm.current == "centro", "abre la consola central: " + sm.current)

# ESTUDIAR
C = P("centro")
ok(boton_pre(C, "[ ] ") or any(b.text.startswith(("[ ]", "[OK]", "[*]")) for b in botones(C)), "lista de conceptos")
ok(any("Por estudiar" in x for x in textos(C)), "muestra el progreso")
ph = next(b for b in botones(C) if "Phishing" in b.text); ph.press()
ok(any("Cómo protegerse" in x for x in textos(C)) and any("2FA" in x for x in textos(C)), "enseña la defensa del phishing")
ok(any("no ejecuta" in x.lower() for x in textos(C)), "recuerda que solo lee/enseña")
boton(C, "Marcar estudiado").press()
ok(ck.Aprendizaje(os.path.join(T, "ciber_aprendizaje.json")).estado("phishing") == "estudiado", "guarda el progreso en disco")
ok(json.loads(open(os.path.join(T, "ciber_aprendizaje.json")).read()) == {"phishing": "estudiado"}, "solo guarda estados, nada ejecutable")

# REVISIÓN (solo lectura)
boton(C, "REVISIÓN").press()
boton(C, "Revisar ahora").press()
ok(esperar(lambda: any("Revisión de seguridad" in x for x in textos(C))) and any("solo lectura" in x.lower() for x in textos(C)), "la revisión corre y es de solo lectura")

# DISPOSITIVO (datos reales)
boton(C, "DISPOSITIVO").press()
ok(esperar(lambda: any("Memoria RAM" in x for x in textos(C))), "muestra datos reales del dispositivo")

# SI TE PASA
boton(C, "SI TE PASA").press()
next(b for b in botones(C) if b.text.startswith("He perdido el móvil")).press()
ok(any("Encontrar mi dispositivo" in x for x in textos(C)), "«SI TE PASA» da los pasos del caso")
# pregunta libre (núcleo simulado)
boton(C, "ESTUDIAR").press()
preg = []
core.explicar_defensa = lambda q: (preg.append(q), ("Respuesta defensiva de prueba.", "ia"))[1]
cp = next(w for w in C.walk() if type(w).__name__ == "TextInput" and getattr(w, "hint_text", "").startswith("Pregúntale a Kira"))
cp.text = "cómo me protejo del phishing"; boton(C, "Preguntar").press()
ok(esperar(lambda: any("Respuesta defensiva de prueba" in x for x in textos(C))), "la pregunta llega a Kira y se muestra la respuesta")
ok(preg == ["cómo me protejo del phishing"], "envía exactamente lo escrito")
# volver con Esc
ok(tecla(W2, 27) is True and sm.current == "sala_ciber", "Esc en la consola vuelve a la sala")
hc.rec.pose = sk.POSE_X_MESA; hc.rec.estado = "libre"
# por voz/texto
import inicio_kira as ik
campo = next(w for w in P("sala_ciber").walk() if type(w).__name__ == "TextInput")
campo.text = "estudiar phishing"; boton(P("sala_ciber"), "Ir").press(); Clock.correr(80, 0.05)
ok(sm.current == "centro", "por texto «estudiar» abre la consola: " + sm.current)
tecla(W2, 27); hc.rec.pose = sk.POSE_X_MESA; hc.rec.estado = "libre"
campo.text = "salir"; boton(P("sala_ciber"), "Ir").press(); Clock.correr(80, 0.05)
ok(sm.current == "menu", "«salir» vuelve al menú")
# botón Salir
sm.ir("sala_ciber"); Clock.correr(120, 0.05)
boton(P("sala_ciber"), "Salir").press(); ok(sm.current == "menu", "el botón Salir va al menú")
# al salir se paran los relojes
sm.ir("menu")
ok(hc._reloj is None, "al salir se para el reloj de la sala de ciber")
# las demás salas intactas
sm.ir("sala_hacker"); ok(next(w for w in sm.walk() if type(w).__name__ == "HabitacionWidget" and getattr(w.rec, "cfg", None) is hk.CFG_HACKER), "la Sala Hacker sigue")
print("CABLEADO CIBER OK", n)
