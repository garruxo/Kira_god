# -*- coding: utf-8 -*-
"""v3.71: «crea un botón … en la ventana de la WiFi» (o de cualquier sala) es una VENTANA nueva, no la WiFi."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import ventanas_kira as vk
import wifi_kira as wk
import kira_escritorio as ke

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


VENTANAS = ["crea un botón con esta función en la ventana de WiFi",
            "crea un botón en la ventana de wifi que busque redes",
            "añade en la wifi una sección con mis redes",
            "en la ventana de la máquina pon un botón que la encienda",
            "en programando añade una sección con mis programas",
            "en el cuaderno, crea un botón que piense",
            "pon un botón en la ventana del mapa que busque ataques nuevos",
            "pon un botón en la ventana del móvil que sincronice"]
for t in VENTANAS:
    ok(vk.orden(t) and vk.orden(t)[0] == "crear", f"es una ventana nueva: «{t}»")
    ok(wk.orden_wifi(t) is None, f"la WiFi no se lo come: «{t}»")

for t, esperado in (("busca redes wifi", "redes"), ("conéctate a la wifi Casa", "conectar"),
                    ("apaga la wifi", "apagar"), ("cómo está la wifi", "estado")):
    ok((wk.orden_wifi(t) or [None])[0] == esperado, f"la WiFi sigue igual: «{t}» → {esperado}")
for t in ("crea un programa con botones", "en el cuaderno, letra más grande", "hazme un juego de naves"):
    ok(vk.orden(t) is None, f"no es una ventana: «{t}»")


class Nucleo:
    def __init__(self):
        self.recibido = None

    def disponible(self):
        return True

    def orden(self, t, al_paso=None):
        self.recibido = t
        return {"respuesta": "Preparo la ventana."}


class WifiNo:                                        # si la llamaran, la prueba lo notaría
    WifiError = Exception

    def orden_wifi(self, t):
        return wk.orden_wifi(t)

    def hacer(self, *a):
        raise AssertionError("no debía tocar la WiFi")

    def trae_clave(self, t):
        return False


nuc, lineas, trozos = Nucleo(), [], []
r = ke.manejar(None, VENTANAS[0], lineas.append, trozos.append, nucleo=nuc, wifi=WifiNo())
ok(r == "kira" and nuc.recibido == VENTANAS[0] and "Preparo" in "".join(trozos),
   "en la pantalla de KiraOS va a Kira (que prepara la ventana), no enseña los datos de la WiFi")

print("TODO BIEN" if not fallos else f"{fallos} FALLOS")
sys.exit(1 if fallos else 0)
