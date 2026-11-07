# -*- coding: utf-8 -*-
"""
kiraos.py - El arranque de KiraOS en el portátil: la pantalla de inicio (orbe que late) + el candado (PIN) y, al
entrar, la ventana de Kira.

«KiraOS» no es un sistema operativo desde cero: por debajo está Linux (es quien maneja la pantalla, el teclado y la
WiFi). Esto es Kira adueñándose de la pantalla completa para que PAREZCA su propio sistema. TODO es local: la pantalla
de inicio es un archivo HTML del disco que se dibuja con el motor que ya trae el escritorio de Ubuntu (WebKitGTK, vía
`pywebview`); no abre ningún navegador ni se conecta a internet.

  python kiraos.py                 ventana
  python kiraos.py --pantalla      a pantalla completa (lo normal en el portátil)

Flujo: la PRIMERA vez, el NACIMIENTO (oscuridad → chispa → latido → se forma el orbe → te pregunta tu nombre y cómo
llamarte → partida de nacimiento; nacimiento_kira.py). Las demás: reposo (orbe latiendo + «pulsa cualquier tecla») →
cuenta atrás que estalla → «Hola, <tu nombre>» → ventana de Kira (kira_escritorio). SIN PIN por decisión del dueño
(v2.83); si se pone uno (`--poner-pin`), se pide tras el estallido. Sin motor gráfico, hay una reserva sencilla.

La lógica (el puente `Api`) se prueba sin ventana (tests/test_kiraos.py). El PIN lo lleva bloqueo_kira.py.
"""
import argparse
import os
import shutil
import subprocess
import sys
import threading

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import bloqueo_kira as bl
import kira_consola as kc
import nacimiento_kira as nk
from escritorio_kira import EscritorioMixin

ARRANQUE = os.path.join(AQUI, "kiraos_web", "arranque.html")
ESCRITORIO = os.path.join(AQUI, "kiraos_web", "escritorio.html")
MAPA = os.path.join(AQUI, "kiraos_web", "mapa.html")
PROGRAMANDO = os.path.join(AQUI, "kiraos_web", "programando.html")
sys.path.insert(0, os.path.dirname(AQUI))   # para la pieza compartida con el móvil
CEREBRO_NOMBRE = "Qwen 35B"          # un solo cerebro


# =====================================================================================
#  LA VOZ («Sistema Kira activado») — con lo que haya en el portátil; si no hay, calla
# =====================================================================================
def voz_portatil(texto, correr=None):
    """Dice `texto` en voz alta con el lector de Ubuntu (spd-say / espeak), sin bloquear. Si no hay ninguno, no pasa
    nada (devuelve False). `correr` se puede inyectar en las pruebas."""
    correr = correr or (lambda orden: subprocess.Popen(orden, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for prog, orden in (("spd-say", ["spd-say", "-l", "es", texto]),
                        ("espeak-ng", ["espeak-ng", "-v", "es", texto]),
                        ("espeak", ["espeak", "-v", "es", texto])):
        if shutil.which(prog):
            try:
                correr(orden)
                return True
            except Exception:
                return False
    return False


# =====================================================================================
#  EL PUENTE con la pantalla (lo llama el HTML). Sin ventana: se puede probar.
# =====================================================================================
class Api(EscritorioMixin):
    def __init__(self, ruta_pin=None, cli=None, hablar=None, ruta_nacimiento=None, baul=None):
        self.ruta_pin = ruta_pin
        self.ruta_nac = ruta_nacimiento
        self.baul = baul
        self.cli = cli
        self.entrado = False
        self._ventana = None
        self._hablar = hablar or voz_portatil

    def info(self):
        nombre = "tu portátil"
        if self.cli is not None:
            try:
                nombre = (self.cli.hola() or {}).get("nombre", nombre)
            except Exception:
                pass
        p = nk.cargar(self.ruta_nac)
        return {"hay_pin": bl.hay_pin(self.ruta_pin), "nombre": nombre, "cerebro": CEREBRO_NOMBRE,
                "nacida": bool(p), "llamar": (p or {}).get("llamar", ""), "fecha": (p or {}).get("fecha", "")}

    def equipo(self):
        """Lo que se ve del equipo en la escena del nacimiento."""
        return nk.equipo()

    def nacer(self, nombre, llamar=""):
        """El nacimiento: guarda la partida y su primer recuerdo. Devuelve lo que enseña la pantalla."""
        try:
            p = nk.nacer(nombre, llamar, ruta=self.ruta_nac, baul=self.baul)
        except nk.NacimientoError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "llamar": p["llamar"], "fecha": p["fecha"], "partida": nk.texto_partida(p)}

    def comprobar(self, pin):
        return bl.comprobar(pin, self.ruta_pin)

    def crear(self, pin):
        try:
            return bl.crear_pin(pin, self.ruta_pin)
        except bl.BloqueoError:
            return False

    def biometria(self):
        return bl.biometria_disponible()

    def mapa_ataques(self):
        """Los datos para el mapa del mundo: de dónde intentan atacarte (país, dueño, tipo)."""
        import ataques_kira as at
        return at.mapa_datos(at.cargar())

    def explicar_codigo(self, codigo):
        """Explica un código línea por línea (técnico, para aprender). Lo usa la pantalla «Kira programando»."""
        import explicacion_codigo_kira as ex
        return ex.explicar(codigo)

    def programando_datos(self):
        """Lo que enseña la pantalla «Kira programando»: el programa y su explicación."""
        return getattr(self, "programa", None) or {}

    def voz(self, texto):
        threading.Thread(target=self._hablar, args=(texto,), daemon=True).start()
        return True

    def entrar(self):
        """v2.90: al entrar, la MISMA ventana pasa al ESCRITORIO (la pantalla principal, como Windows)."""
        self.entrado = True
        self._ini_escritorio()
        return True


# =====================================================================================
#  ABRIR LA PANTALLA DE ARRANQUE
# =====================================================================================
def arrancar(api, pantalla=True):
    """Abre la pantalla de inicio + PIN. Devuelve True si el dueño entró (acertó el PIN). Bloquea hasta que se cierra.
    Usa el motor de Ubuntu (pywebview); si no está, cae en una reserva por PIN (Tkinter o consola)."""
    try:
        import webview
    except Exception:
        return _reserva(api, pantalla)
    win = webview.create_window("KiraOS", ARRANQUE, js_api=api, fullscreen=pantalla,
                                background_color="#04050a", min_size=(900, 640))
    api._ventana = win
    api.web = True                              # el escritorio vive en esta misma ventana
    webview.start()
    return api.entrado


def _reserva(api, pantalla=True):
    """Sin motor gráfico fino: PIN en una ventana sencilla de Tkinter; y si tampoco hay, por consola."""
    try:
        import tkinter as tk
        from tkinter import simpledialog, messagebox
    except Exception:
        return _reserva_consola(api)
    raiz = tk.Tk()
    raiz.withdraw()
    inf = api.info()
    if not inf["nacida"]:
        nombre = None
        while not nombre:
            nombre = simpledialog.askstring("KiraOS", "Acabo de nacer. ¿Cómo te llamas?", parent=raiz)
            if nombre is None:
                raiz.destroy(); return False
        llamar = simpledialog.askstring("KiraOS", "¿Cómo quieres que te llame?", initialvalue=nombre, parent=raiz)
        r = api.nacer(nombre, llamar or "")
        if r.get("ok"):
            messagebox.showinfo("KiraOS", r["partida"])
        inf = api.info()
    if not inf["hay_pin"]:
        api.entrado = True
        raiz.destroy(); return True
    for _ in range(10):
        p = simpledialog.askstring("KiraOS", "Introduce tu PIN:", show="*", parent=raiz)
        if p is None:
            raiz.destroy(); return False
        if api.comprobar(p):
            api.entrado = True
            raiz.destroy(); return True
        messagebox.showerror("KiraOS", "PIN incorrecto.")
    raiz.destroy()
    return False


def _reserva_consola(api):
    import getpass
    inf = api.info()
    if not inf["nacida"]:
        nombre = ""
        while not nombre.strip():
            nombre = input("Acabo de nacer. ¿Cómo te llamas? ")
        llamar = input(f"¿Cómo quieres que te llame? [{nombre.strip()}] ")
        r = api.nacer(nombre, llamar)
        if r.get("ok"):
            print(r["partida"])
        inf = api.info()
    if not inf["hay_pin"]:
        api.entrado = True
        return True
    for _ in range(10):
        if api.comprobar(getpass.getpass("PIN: ")):
            api.entrado = True
            return True
        print("PIN incorrecto.")
    return False


def abrir_mapa(pantalla=True):
    """Abre el mapa del mundo de ataques (ventana propia). Solo mira, no toca nada."""
    try:
        import webview
    except Exception:
        print("Falta pywebview para ver el mapa (instálalo en el portátil).")
        return
    webview.create_window("Mapa de ataques · KiraOS", MAPA, js_api=Api(), fullscreen=pantalla,
                          background_color="#04050a", min_size=(900, 600))
    webview.start()


def abrir_programando(archivo=None, pedido="", pantalla=False):
    """Abre la pantalla «Kira programando»: escribe el código en vivo y lo explica línea a línea. Si se da un
    archivo (.py), explica ese; si no, la pantalla enseña su ejemplo."""
    try:
        import webview
    except Exception:
        print("Falta pywebview para esta pantalla.")
        return
    api = Api()
    if archivo and os.path.isfile(archivo):
        import explicacion_codigo_kira as ex
        codigo = open(archivo, encoding="utf-8", errors="replace").read()
        r = ex.explicar(codigo)
        api.programa = {"pedido": pedido or os.path.basename(archivo), "archivo": os.path.basename(archivo),
                        "lineas": r["lineas"], "resumen": r["resumen"]}
    webview.create_window("Kira programando · KiraOS", PROGRAMANDO, js_api=api, fullscreen=pantalla,
                          background_color="#060d09", min_size=(900, 600))
    webview.start()


def _ajustes_grafica_vieja():
    """v2.94: en gráficas viejas (como el Packard Bell) WebKit dibuja con «efecto agua»/artefactos al animar las
    ventanas. Desactivando su compositor acelerado se ve estable. Solo se pone si no estaba ya puesto, y no afecta a
    equipos modernos de forma notable."""
    os.environ.setdefault("WEBKIT_DISABLE_COMPOSITING_MODE", "1")
    os.environ.setdefault("WEBKIT_DISABLE_DMABUF_RENDERER", "1")


def main(argv=None):
    _ajustes_grafica_vieja()
    ap = argparse.ArgumentParser(description="El arranque de KiraOS en el portátil")
    ap.add_argument("--url", default="http://127.0.0.1:8770")
    ap.add_argument("--pantalla", action="store_true", help="a pantalla completa (modo KiraOS)")
    ap.add_argument("--mapa", action="store_true", help="abre el mapa de ataques y sale")
    ap.add_argument("--programando", nargs="?", const="", metavar="ARCHIVO",
                    help="abre la pantalla «Kira programando» (opcional: un archivo .py que explicar)")
    ap.add_argument("--poner-pin", action="store_true", help="pone (o cambia) un PIN para entrar")
    ap.add_argument("--quitar-pin", action="store_true", help="quita el PIN: entra directo")
    ap.add_argument("--partida", action="store_true", help="enseña la partida de nacimiento de Kira")
    a = ap.parse_args(argv)

    if a.partida:
        print(nk.texto_partida(nk.cargar()))
        return
    if a.quitar_pin:
        print("PIN quitado: KiraOS entrará directo." if bl.quitar_pin() else "No había PIN.")
        return
    if a.poner_pin:
        import getpass
        p1 = getpass.getpass("PIN nuevo (4 cifras): ")
        if p1 != getpass.getpass("Repítelo: "):
            sys.exit("No coincide.")
        try:
            bl.crear_pin(p1)
        except bl.BloqueoError as e:
            sys.exit(str(e))
        print("PIN puesto: KiraOS lo pedirá al entrar.")
        return
    if a.mapa:
        abrir_mapa(pantalla=a.pantalla)
        return
    if a.programando is not None:
        abrir_programando(archivo=a.programando or None, pantalla=a.pantalla)
        return

    token = kc.leer_token()
    cli = kc.Cliente(a.url, token) if len(token) >= 16 else None
    api = Api(cli=cli)

    if not arrancar(api, pantalla=a.pantalla):
        return                                  # cerró sin entrar
    if getattr(api, "web", False):
        return                                  # v2.90: el escritorio ya estuvo en la misma ventana; al cerrarla, fin

    if cli is None:
        print("Entraste, pero no encuentro el cerebro de casa (falta el token). ¿Está arrancado el servidor?")
        return
    import kira_escritorio as ke
    ke.ventana(cli, pantalla_completa=a.pantalla)


if __name__ == "__main__":
    main()
