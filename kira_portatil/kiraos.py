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

Flujo: reposo (orbe latiendo + «pulsa cualquier tecla») → al pulsar, la cuenta atrás estalla → PIN (o huella/cara) →
ventana de Kira (kira_escritorio). Si el motor gráfico no estuviera, hay una reserva por PIN sencilla para entrar igual.

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

ARRANQUE = os.path.join(AQUI, "kiraos_web", "arranque.html")
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
class Api:
    def __init__(self, ruta_pin=None, cli=None, hablar=None):
        self.ruta_pin = ruta_pin
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
        return {"hay_pin": bl.hay_pin(self.ruta_pin), "nombre": nombre, "cerebro": CEREBRO_NOMBRE}

    def comprobar(self, pin):
        return bl.comprobar(pin, self.ruta_pin)

    def crear(self, pin):
        try:
            return bl.crear_pin(pin, self.ruta_pin)
        except bl.BloqueoError:
            return False

    def biometria(self):
        return bl.biometria_disponible()

    def voz(self, texto):
        threading.Thread(target=self._hablar, args=(texto,), daemon=True).start()
        return True

    def entrar(self):
        self.entrado = True
        try:
            if self._ventana is not None:
                self._ventana.destroy()
        except Exception:
            pass
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
    if not api.info()["hay_pin"]:
        while True:
            a = simpledialog.askstring("KiraOS", "Crea tu PIN (4 cifras):", show="*", parent=raiz)
            if a is None:
                raiz.destroy(); return False
            b = simpledialog.askstring("KiraOS", "Repite el PIN:", show="*", parent=raiz)
            if a == b and api.crear(a):
                break
            messagebox.showerror("KiraOS", "No coincide o no son 4 cifras.")
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
    if not api.info()["hay_pin"]:
        while True:
            a = getpass.getpass("Crea tu PIN (4 cifras): ")
            if a == getpass.getpass("Repítelo: ") and api.crear(a):
                break
            print("No coincide o no son 4 cifras.")
    for _ in range(10):
        if api.comprobar(getpass.getpass("PIN: ")):
            api.entrado = True
            return True
        print("PIN incorrecto.")
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="El arranque de KiraOS en el portátil")
    ap.add_argument("--url", default="http://127.0.0.1:8770")
    ap.add_argument("--pantalla", action="store_true", help="a pantalla completa (modo KiraOS)")
    a = ap.parse_args(argv)

    token = kc.leer_token()
    cli = kc.Cliente(a.url, token) if len(token) >= 16 else None
    api = Api(cli=cli)

    if not arrancar(api, pantalla=a.pantalla):
        return                                  # cerró sin entrar

    if cli is None:
        print("Entraste, pero no encuentro el cerebro de casa (falta el token). ¿Está arrancado el servidor?")
        return
    import kira_escritorio as ke
    ke.ventana(cli, pantalla_completa=a.pantalla)


if __name__ == "__main__":
    main()
