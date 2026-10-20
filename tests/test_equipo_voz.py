# -*- coding: utf-8 -*-
"""v2.17: por VOZ, Kira programa (al editor), diseña (al ordenador de diseño) y aprende mejoras SIN ordenador.
Cómo se reconocen las frases y cómo llegan a cada pantalla (Kivy simulado)."""
import os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import diseno_kira as dk, inicio_kira as ik, programar_kira as pk
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- qué frase es qué ----------
ok(pk.pedido_programa("escríbeme un programa que calcule la media de mis notas") == "programa que calcule la media de mis notas",
   "programa para el editor")
ok(pk.pedido_programa("hazme un juego de naves") == "juego de naves", "juego para el editor")
ok(pk.pedido_programa("hazme un café") is None and pk.pedido_programa("escribe un programa") is None, "lo demás no")
ok(dk.pedido_diseno("diséñame una web para mi bar de tapas")[0] == "web", "web")
ok(dk.pedido_diseno("hazme una maqueta de app de tareas")[0] == "app", "maqueta de app")
ok(dk.pedido_diseno("crea un videoclip de la playa al atardecer")[0] == "clip", "videoclip")
ok(dk.pedido_diseno("diseña algo bonito para la boda") == ("web", "algo bonito para la boda"), "«diséñame…» sin decir qué: web")
ok(dk.pedido_diseno("hazme un juego de naves") is None, "un juego no es un diseño")
ok(ik.pedido_mejora("aprende a convertir euros a dólares") == "convertir euros a dólares", "«aprende a…» sigue siendo mejora")
ok(pk.pedido_programa("programa un juego de naves") is None and ik.pedido_mejora("programa un juego de naves"),
   "«programa un juego…» es una MEJORA (se instala en Juegos con tus dos toques)")

# ---------- la interfaz ----------
class VozMuda:
    def __init__(self): self.dichos = []
    def puede_hablar(self): return True
    def puede_escuchar(self): return False
    def hablando(self): return False
    def hablar(self, t): self.dichos.append(t); return True
    def iniciar_escucha(self, idioma="es-ES"): return False, "no"
    def sondear(self): return "error", "no"
    def parar_escucha(self): pass
VOZ = VozMuda()
ik.Voz = lambda *a, **k: VOZ

import cerebro_ia_kira as ci, kira_god
core = kira_god.KiraGodCore()
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)

def correr(seg=3.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.3)
        if cond and cond(): return True
        time.sleep(0.01)
    return bool(cond and cond())
def textos(nombre): return [w.text for w in sm.get_screen(nombre).walk() if hasattr(w, "text") and isinstance(w.text, str)]
def decir_a_kira(frase):
    sm.ir("inicio"); correr(0.3)
    campo = next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "TextInput")
    campo.text = frase
    next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
def burbuja(): return " ".join(t for t in textos("inicio"))

# sin ningún cerebro: lo dice claro
correr(1.0)
core.cerebro_para_codigo = lambda: None
decir_a_kira("Kira, escríbeme un programa que calcule la media de mis notas")
ok(correr(2, lambda: "necesito un cerebro" in burbuja()), "sin cerebro, dice qué falta")

# con el cerebro del móvil (falso): escribe, prueba en modo seguro y lo deja en el editor
PROG = "notas = [7, 8.5, 6]\nprint('Tu media es', round(sum(notas) / len(notas), 2))\n"
pedidos = []
core.cerebro_para_codigo = lambda: "local"
core._leer_clave = lambda *a: ci.LOCAL
core._llamar_api = lambda clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None: (
    pedidos.append((system, usuario)), f"NOMBRE: media\n```python\n{PROG}```")[1]
decir_a_kira("Kira, escríbeme un programa que calcule la media de mis notas")
ok(correr(5, lambda: sm.current == "editor_codigo"), "abre el editor con el programa: " + sm.current)
ok(PROG.strip() in "\n".join(textos("editor_codigo")), "el programa está en el editor")
ok(any("probado en modo seguro" in t and "Ejecutar" in t for t in textos("editor_codigo")), "explica que está probado y qué pulsar")
ok(any("Te lo dejo en el editor" in d for d in VOZ.dichos), "lo dice en voz alta")
ok(pedidos and pedidos[0][0] == pk.SISTEMA_PROGRAMA_LOCAL, "lo escribe el cerebro del móvil, con sus reglas cortas")
ok(not os.path.isdir(os.path.join(T, "modulos")) or not os.listdir(os.path.join(T, "modulos")), "no instala nada en Kira")

# un programa que nunca funciona: no abre nada roto
pedidos.clear(); sm.ir("inicio")
core._llamar_api = lambda clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None: (
    pedidos.append(1), "NOMBRE: roto\n```python\nimport os\nprint(os.listdir())\n```")[1]
decir_a_kira("Kira, escríbeme un programa que liste mis archivos")
ok(correr(6, lambda: "No he conseguido un programa" in burbuja()), "si no pasa el modo seguro, lo dice")
ok(sm.current == "inicio" and len(pedidos) >= 2, "lo reintenta y no abre el editor con algo roto")

# diseño por voz desde cualquier sitio (sin IA: plantillas)
core._leer_clave = lambda *a: ""
VOZ.dichos.clear()
decir_a_kira("Kira, diséñame una web para mi bar de tapas")
ok(correr(4, lambda: sm.current == "estudio"), "va al ordenador de diseño")
ok(correr(4, lambda: any("<!DOCTYPE html>" in t for t in textos("estudio"))), "y crea la página")
ok(any("bar de tapas" in t for t in textos("estudio")), "con lo que le pediste")
ok(correr(3, lambda: any("plantillas" in d for d in VOZ.dichos)), "dice honestamente que usó sus plantillas")

# mejora sin ordenador: no pide el laboratorio del PC
ctl = sm.control
ctl.pasarela.url = ""
enviadas = []
ctl.enviar_orden = lambda p: (enviadas.append(p), {"ok": False, "aprobable": False, "intentos": 1, "texto": "[x] x"})[1]
VOZ.dichos.clear()
decir_a_kira("Kira, aprende a convertir euros a dólares")
ok(correr(5, lambda: enviadas), "la mejora se pone en marcha sin ordenador")
ok(any("aquí en el móvil" in t for t in textos("inicio") + VOZ.dichos), "dice que la prueba en el móvil")
print("EQUIPO VOZ OK", n)
