# -*- coding: utf-8 -*-
"""
capturas_pantallas.py - Hace CAPTURAS DE VERDAD de las pantallas (con datos de ejemplo), para enseñárselas al dueño.

  --movil  CARPETA   la app del móvil (Kivy de verdad, modo sencillo): hablar con Kira y el panel
  --kiraos CARPETA   la ventana de KiraOS en el portátil (Tkinter de verdad) y su ventana de WiFi

Se usa en GitHub con una pantalla virtual (xvfb). Los datos son de EJEMPLO (órdenes, conversación, KiraOS conectada…).
"""
import glob
import json
import os
import shutil
import sys
import tempfile
import textwrap
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)


# =====================================================================================
#  datos de ejemplo
# =====================================================================================
def sembrar(datos):
    import ordenes_kira as okr
    import pensador_kira as pn
    import sincronia_kira as sc
    ahora = time.time()
    o1 = okr.apuntar(datos, "estudia python", "movil")
    okr.actualizar(datos, o1, estado="hecha", respuesta="Estudiado: 5 webs oficiales y 2 cursos completos de YouTube.")
    o2 = okr.apuntar(datos, "qué wifi tiene el portátil", "kiraos")
    okr.actualizar(datos, o2, estado="hecha", respuesta="Conectada a «MiCasa», señal 72 %, con internet.")
    okr.apuntar(datos, "hazme un juego de carreras", "kiraos", "en curso")
    okr.apuntar(datos, "diséñame una web para mi taller", "kiraos", "pendiente")
    est = pn.cargar(os.path.join(datos, "pensamientos.json"))
    for i in range(37):
        est["notas"].append({"pregunta": f"¿cómo funciona la idea {i}?", "respuesta": "…", "cuando": ahora - i * 600,
                             "seguridad": "media", "semilla": f"tema {i % 7}"})
    for t in ("ordenar una lista", "un trie", "detectar anomalías", "una caché LRU", "un grafo", "una calculadora"):
        est["soluciones"][t] = {"tema": t, "resumen": "…", "cuando": ahora - 3600, "veces": 1}
    pn.guardar(est, os.path.join(datos, "pensamientos.json"))
    e = sc.estado_movil(datos)
    e.update(ultima=ahora - 420, resumen="Envié 12 cosas nuevas a KiraOS y recibí 4.", enviados_total=348,
             recibidos_total=27)
    sc.guardar_estado_movil(datos, e)
    mod = "def hora(texto):\n    return 'Son las tantas.'\n\n\ndef registrar():\n    return {'qué hora es': hora}\n"
    sc.guardar_mejoras_recibidas(datos, [{"nombre": "hora_exacta", "codigo": mod, "hash": sc._hash(mod),
                                          "descripcion": "decirte la hora exacta cuando se la pidas"}])
    charla = [("tu", "Kira, ¿qué has hecho hoy?"),
              ("kira", "He estudiado Python (webs oficiales y dos cursos) y he pensado 37 cosas. KiraOS está haciendo "
                       "tu juego de carreras."),
              ("tu", "Genial. Luego me lo enseñas.")]
    with open(os.path.join(datos, "conversacion.json"), "w", encoding="utf-8") as f:
        json.dump([{"rol": r, "texto": t, "t": ahora - 300 + i} for i, (r, t) in enumerate(charla)], f,
                  ensure_ascii=False)


HOLA_KIRAOS = {"kira_nucleo": 1, "version": "2.88", "recuerdos": 1240, "llamar": "Jefe", "ocupada": True,
               "haciendo": "hazme un juego de carreras",
               "actividad": {"pensando": True, "estudiando": False, "foco": "", "pensamientos": 112, "soluciones": 14,
                             "maquina": False, "wifi": {"radio": True, "ssid": "MiCasa", "senal": 72, "internet": "full"}},
               "equipo": {"procesador": "Intel Core i5 M430", "ram_mb": 7900, "disco_libre_gb": 181, "carga": "1.35",
                          "encendido_h": 5.2}}


# =====================================================================================
#  EL MÓVIL (Kivy de verdad)
# =====================================================================================
def movil(salida):
    os.makedirs(salida, exist_ok=True)
    datos = tempfile.mkdtemp()
    os.environ["KIRA_DATA_DIR"] = datos
    os.environ["KIVY_NO_ARGS"] = "1"
    os.environ.setdefault("KIVY_METRICS_DENSITY", "2.75")
    from kivy.config import Config
    Config.set("graphics", "width", "1080")
    Config.set("graphics", "height", "2340")
    Config.set("graphics", "resizable", "0")
    Config.set("kivy", "exit_on_escape", "0")
    sembrar(datos)
    import arranque_kira
    arranque_kira.Preparacion.hace_falta = lambda self: False
    import kira_god
    core = kira_god.KiraGodCore()

    class CasaDemo:
        def nucleo_disponible(self):
            return True

        def nucleo_hola(self):
            return HOLA_KIRAOS

        def disponible(self, forzar=False):
            return True

    core._casa = lambda: CasaDemo()
    core.mando_listo = lambda esperar=False: True
    core.vigilar_casa = lambda *a, **k: None
    core.pensar_sola = lambda *a, **k: None
    core._pensar_on, core._ultima_actividad = True, 0
    core.cerebro_ia.estado_texto = lambda *a, **k: (
        "En casa pienso con el cerebro de KiraOS (portátil): conectado.\nMi cerebro propio del móvil "
        "(Qwen3.5 2B) está descargado: lo uso fuera de casa.")
    core.conversar = lambda texto, h=(): ("¡Muy bien! Llevo un rato pensando sobre lo que estudié de Python y "
                                          "KiraOS sigue con tu juego de carreras. ¿Quieres que te lo enseñe cuando acabe?")
    from interfaz_kira import construir_interfaz
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.uix.scrollview import ScrollView

    def foto(nombre):
        Window.screenshot(name=os.path.join(salida, nombre))
        for f in glob.glob(os.path.join(salida, nombre[:-4] + "0*.png")):
            shutil.move(f, os.path.join(salida, nombre))
        print("foto", nombre, flush=True)

    class Capturas(App):
        def build(self):
            self.sm = construir_interfaz(core, modo="sencillo")
            return self.sm

        def on_start(self):
            sm = self.sm

            def buscar(pantalla, tipo, **atr):
                for w in sm.get_screen(pantalla).walk():
                    if type(w).__name__ == tipo and all(getattr(w, k, None) == v for k, v in atr.items()):
                        return w
                return None

            def escribir(_dt):
                campo = buscar("inicio", "TextInput", hint_text="Escríbele a Kira…")
                if campo is not None:
                    campo.text = "Kira, ¿qué tal vas?"
                    boton = buscar("inicio", "Button", text="Enviar")
                    boton.dispatch("on_release")

            def panel(_dt):
                sm.ir("menu")

            def bajar(pos):
                def hacer(_dt):
                    sv = next((w for w in sm.get_screen("menu").walk() if isinstance(w, ScrollView)), None)
                    if sv is not None:
                        sv.scroll_y = pos
                return hacer

            pasos = [(2.0, lambda dt: sm.ir("inicio")), (4.5, lambda dt: foto("app_1_inicio.png")),
                     (5.0, escribir), (10.0, lambda dt: foto("app_2_charla.png")),
                     (10.5, panel), (14.0, lambda dt: foto("app_3_panel.png")),
                     (14.5, bajar(0.55)), (16.0, lambda dt: foto("app_4_panel_medio.png")),
                     (16.5, bajar(0.0)), (18.0, lambda dt: foto("app_5_panel_final.png")),
                     (19.0, lambda dt: self.stop())]
            for t, fn in pasos:
                Clock.schedule_once(fn, t)

    Capturas().run()


# =====================================================================================
#  KiraOS (Tkinter de verdad)
# =====================================================================================
NMCLI = r'''
import json, sys
E = %r
a = sys.argv[1:]
e = json.load(open(E))
def fin(code=0, out="", err=""):
    json.dump(e, open(E, "w")); sys.stdout.write(out); sys.stderr.write(err); sys.exit(code)
def esc(s): return s.replace("\\", "\\\\").replace(":", "\\:")
if a == ["-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"]:
    fin(0, "wlp2s0:wifi:connected:%%s\n" %% esc(e["conectada"]))
if a == ["radio", "wifi"]: fin(0, "enabled\n")
if a == ["-t", "-f", "NAME,TYPE", "connection", "show"]:
    fin(0, "".join(esc(n) + ":802-11-wireless\n" for n in e["guardadas"]))
if a[:6] == ["-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY,CHAN", "device", "wifi", "list"]:
    fin(0, "".join(("*" if r[0] == e["conectada"] else " ") + ":" + esc(r[0]) + ":%%d:%%s:%%d\n" %% (r[1], r[2], r[3])
                   for r in e["visibles"]))
if a[:2] == ["networking", "connectivity"]: fin(0, "full\n")
if a[:2] == ["-g", "IP4.ADDRESS"]: fin(0, "192.168.1.40/24\n")
fin(0)
'''


def kiraos(salida):
    import tkinter as tk
    from PIL import ImageGrab
    os.makedirs(salida, exist_ok=True)
    t = tempfile.mkdtemp()
    estado = os.path.join(t, "nm.json")
    json.dump({"conectada": "MiCasa", "guardadas": ["MiCasa"],
               "visibles": [["MiCasa", 72, "WPA2", 6], ["MOVISTAR_8A21", 48, "WPA2", 1], ["Vecino_5G", 31, "WPA2", 44],
                            ["Bar Pepe", 22, "--", 11]]}, open(estado, "w"))
    nm = os.path.join(t, "nmcli")
    with open(nm, "w") as f:
        f.write("#!" + sys.executable + "\n" + textwrap.dedent(NMCLI % estado))
    os.chmod(nm, 0o755)
    os.environ["KIRA_NMCLI"] = nm
    os.environ["KIRA_WIFI_ESTADO"] = os.path.join(t, "wifi.json")
    sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
    import kira_escritorio as ke

    class CliDemo:
        grande, url, token = False, "http://127.0.0.1:8770", "x" * 32

        def hola(self):
            return {"nombre": "el Packard Bell", "cargado": "rapido", "cerebros": {"rapido": "Qwen3.5 2B"}}

        def charla(self, texto, al_trozo=None, **k):
            r = ("¡Hola, Jefe! Hoy he pensado 112 cosas y tengo 14 soluciones guardadas. Ahora estoy con tu juego "
                 "de carreras; el móvil se sincronizó conmigo hace 7 minutos.")
            for trozo in r.split(" "):
                al_trozo(trozo + " ")
                time.sleep(0.005)
            return r

    raiz = ke.construir(CliDemo(), nucleo=None)
    raiz.geometry("1366x768+0+0")

    def campo():
        pila = [raiz]
        while pila:
            w = pila.pop()
            if isinstance(w, tk.Entry):
                return w
            pila.extend(w.winfo_children())

    def foto(nombre):
        raiz.update_idletasks()
        ImageGrab.grab(xdisplay=os.environ["DISPLAY"]).crop((0, 0, 1366, 768)).save(os.path.join(salida, nombre))
        print("foto", nombre, flush=True)

    def decir(frase):
        c = campo()
        c.delete(0, "end")
        c.insert(0, frase)
        raiz._kira_enviar()

    vent = {}

    def abrir_wifi():
        vent["w"] = raiz._kira_wifi()
        vent["w"].geometry("560x480+403+120")

    # todo dentro del bucle de Tk (como en el portátil de verdad)
    raiz.after(1000, lambda: decir("hola Kira, ¿qué tal?"))
    raiz.after(4000, lambda: decir("qué wifi tienes"))
    raiz.after(7000, lambda: foto("os_7_ventana.png"))
    raiz.after(7500, abrir_wifi)
    raiz.after(11000, lambda: foto("os_8_wifi.png"))
    raiz.after(11500, raiz.destroy)
    raiz.mainloop()


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--movil":
        movil(sys.argv[2])
    elif len(sys.argv) >= 3 and sys.argv[1] == "--kiraos":
        kiraos(sys.argv[2])
    else:
        print(__doc__)
