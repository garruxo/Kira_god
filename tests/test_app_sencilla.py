# -*- coding: utf-8 -*-
"""v2.87: la app del móvil en DOS pantallas (hablar con Kira + el panel). Con el Kivy de mentira: qué pantallas hay,
cómo se reparten las órdenes (trabajo → KiraOS, o a la cola si no está; estudiar/pensar/charla → aquí), el panel y
las mejoras que manda KiraOS (laboratorio del móvil + DOS toques)."""
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso
kivy_falso.instalar()
from kivy_falso import Clock
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp()
os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import kira_god
import ordenes_kira as okr
import sincronia_kira as sc

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


core = kira_god.KiraGodCore()
charlas, estudios = [], []
core.conversar = lambda t, h=(): (charlas.append(t), "Te escucho.")[1]
core.estudiar_a_fondo = lambda tema, al_paso=None: (estudios.append(tema), f"Estudiado {tema}.")[1]
core.mando_listo = lambda esperar=False: False             # fuera de casa
MOD = "def hora(texto):\n    return 'Son las tantas.'\n\n\ndef registrar():\n    return {'hora de kiraos': hora}\n"
sc.guardar_mejoras_recibidas(T, [{"nombre": "hora_kiraos", "codigo": MOD, "descripcion": "dice la hora",
                                  "hash": sc._hash(MOD)}])
from interfaz_kira import construir_interfaz, leer_modo_app
ok(leer_modo_app(T) == "sencillo", "la app viene en modo SENCILLO")
sm = construir_interfaz(core)
ok(sm.modo == "sencillo", "se construye en modo sencillo")
nombres = set(sm.screen_names)
ok({"inicio", "menu", "panel", "cerebro_kira"} <= nombres, "están hablar, el panel, ajustes y cerebro: " + str(nombres))
for sala in ("sala_hacker", "sala_diseno", "sala_ciber", "taller", "pintor", "internet", "pdf", "juegos", "editor",
             "bitacora", "defensa", "librerias"):
    ok(sala not in nombres, f"«{sala}» ya no está en el móvil")


def buscar(tipo, raiz=None, **atr):
    for w in (raiz or sm).walk():
        if type(w).__name__ == tipo and all(getattr(w, k, None) == v for k, v in atr.items()):
            return w
    raise AssertionError(f"no hay {tipo} {atr}")


def textos(raiz=None):
    return [getattr(w, "text", "") for w in (raiz or sm).walk() if type(w).__name__ in ("Label", "Button")]


def esperar(cond, seg=4):
    t0 = time.time()
    while time.time() - t0 < seg:
        Clock.correr(1, 0.1)
        if cond():
            return True
        time.sleep(0.02)
    return False


campo = buscar("TextInput", hint_text="Escríbele a Kira…")
Clock.correr(40, 0.1)


def decir_a_kira(t):
    campo.text = t
    buscar("Button", text="Enviar").press()


# --- trabajo para KiraOS sin KiraOS en casa: se APUNTA ---
decir_a_kira("Kira, hazme un juego de carreras")
pend = okr.pendientes_kiraos(T)
ok(pend and pend[0]["texto"] == "hazme un juego de carreras", "fuera de casa, el trabajo se apunta para KiraOS")
ok(esperar(lambda: any("Te lo apunto" in x for x in textos())), "y lo dice")
decir_a_kira("mejora tu forma de contar chistes")
ok(okr.pendientes_kiraos(T)[-1]["texto"].startswith("prepara una mejora para el móvil:"),
   "una mejora para mí se la pide a KiraOS")
# --- estudiar y charlar: aquí ---
decir_a_kira("estudia python")
ok(esperar(lambda: estudios == ["python"]), "estudiar lo hace el móvil")
ok(esperar(lambda: any(o["texto"] == "estudia python" and o["estado"] == "hecha" for o in okr.ultimas(T, 20))),
   "y queda apuntado en las órdenes")
decir_a_kira("hola kira, ¿qué tal?")
ok(esperar(lambda: charlas), "la charla la contesta el móvil")
ok(esperar(lambda: any(o["destino"] == "movil" and o["estado"] == "hecha" and "Te escucho" in o["respuesta"]
                       for o in okr.ultimas(T, 20))), "con su respuesta en el historial")
# --- una sala que ya no está ---
decir_a_kira("abre la sala hacker")
ok(esperar(lambda: any("ya no está en el móvil" in x for x in textos())), "una sala que ya no está: lo dice")
ok(sm.current != "sala_hacker", "y no intenta abrirla")
sm.ir("sala_hacker")
ok(sm.current == "menu", "ir a una pantalla que no existe lleva al panel")

# --- el panel ---
sm.ir("menu")
Clock.correr(5, 0.1)
tx = "\n".join(textos(sm.get_screen("menu")))
for titulo in ("KIRA APP (este móvil)", "KIRAOS (el portátil)", "CEREBRO", "SINCRONÍA CON KIRAOS", "ÓRDENES",
               "CONVERSACIONES", "MEJORAS QUE ME MANDA KIRAOS", "AJUSTES"):
    ok(titulo in tx, f"el panel enseña «{titulo}»")
ok("No la veo ni en la WiFi" in tx and "hazme un juego de carreras" in tx and "EN ESPERA" in tx,
   "sin KiraOS lo dice, y enseña las órdenes que esperan")
# probar la mejora de KiraOS en el laboratorio del móvil
buscar("Button", text="Probar «hora_kiraos»").press()
ok(esperar(lambda: sc.mejoras_recibidas(T, False)[0]["estado"] == "probada", 8), "la mejora pasa el laboratorio del móvil")
instalada_antes = "hora de kiraos" in getattr(core, "comandos_modulos", {})
ok(not instalada_antes, "todavía no está instalada")
sm.get_screen("menu")
esperar(lambda: any("Instalar «hora_kiraos»" in x for x in textos(sm.get_screen("menu"))))
buscar("Button", text="Instalar «hora_kiraos» (2 toques)").press()        # PRIMER toque
ok("hora de kiraos" not in getattr(core, "comandos_modulos", {}), "con UN toque no se instala")
buscar("Button", text="Toca OTRA VEZ para instalar «hora_kiraos»").press()  # SEGUNDO toque
ok(esperar(lambda: "hora de kiraos" in getattr(core, "comandos_modulos", {})), "con DOS toques, sí")
ok(sc.mejoras_recibidas(T, False)[0]["estado"] == "instalada", "y queda marcada como instalada")

# --- cambiar de modo: por si hace falta volver a las pantallas de antes ---
decir_a_kira("modo completo")
ok(leer_modo_app(T) == "completo", "«modo completo» lo guarda para el próximo arranque")
decir_a_kira("modo sencillo")
ok(leer_modo_app(T) == "sencillo", "«modo sencillo» lo devuelve")

# --- al rato de abrir: vigila la casa y se pone a pensar (si nunca lo decidiste) ---
Clock.correr(80, 0.1)
ok(getattr(core, "_vigilando_casa", False), "vigila si llega a casa para sincronizarse sola")
ok(json.load(open(os.path.join(T, "pensar_sola.json"))).get("on") is True, "Kira app se pone a pensar (suave)")
core.pensar_sola(False)
core._vigilando_casa = False

# --- en casa: el trabajo va directo a KiraOS ---
core.mando_listo = lambda esperar=False: True


class CasaFalsa:
    def orden(self, texto, al_paso=None, parar=None, **k):
        al_paso(0.5, "a mitad")
        return {"estado": "hecho", "respuesta": "Juego hecho y probado.", "codigo": "print('juego')", "nombre": "j"}


core._casa = lambda: CasaFalsa()
decir_a_kira("escríbeme un programa que sume")
ok(esperar(lambda: any(o["texto"] == "escríbeme un programa que sume" and o["destino"] == "kiraos"
                       and o["estado"] == "hecha" for o in okr.ultimas(T, 30))), "en casa se lo pasa a KiraOS al momento")
sm.ir("menu")
Clock.correr(5, 0.1)
ok(any("ÚLTIMO TRABAJO DE KIRAOS" in x for x in textos(sm.get_screen("menu"))), "y el panel enseña su último trabajo")
ok(any("print('juego')" in x for x in textos(sm.get_screen("menu"))), "con el código (que tiene KiraOS)")

# --- y el modo completo sigue construyéndose ---
sm2 = construir_interfaz(core, modo="completo")
ok(sm2.modo == "completo" and "sala_hacker" in sm2.screen_names, "en modo completo vuelven todas las salas")
print("\nTODO BIEN", n)
