# -*- coding: utf-8 -*-
"""El puente de la pantalla de arranque de KiraOS (kiraos.Api) y la voz, sin abrir ninguna ventana. Con un archivo de
PIN temporal."""
import os
import sys
import tempfile
import threading

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import kiraos
import bloqueo_kira as bl

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


R = os.path.join(tempfile.mkdtemp(), "pin_kira.txt")
api = kiraos.Api(ruta_pin=R)

inf = api.info()
ok(inf["hay_pin"] is False, "al principio no hay PIN (la pantalla pedirá crearlo)")
ok(inf["cerebro"] == "Qwen 35B", "info dice el cerebro (uno solo)")

ok(api.crear("1234") is True, "se crea el PIN desde la pantalla")
ok(api.info()["hay_pin"] is True, "ya hay PIN")
ok(api.crear("12") is False, "un PIN mal (no 4 cifras) no se crea")

ok(api.comprobar("1234") is True, "el PIN correcto entra")
ok(api.comprobar("9999") is False, "el PIN incorrecto no entra")
ok(api.biometria() is False, "la huella/cara la pone el sistema (de momento no)")

# entrar() marca que se entró (sin ventana no rompe)
ok(api.entrado is False and api.entrar() is True and api.entrado is True, "«entrar» marca que el dueño pasó")

# la voz: se llama en un hilo; con un hablar de mentira lo comprobamos
dicho = []
ev = threading.Event()
api2 = kiraos.Api(ruta_pin=R, hablar=lambda t: (dicho.append(t), ev.set()))
api2.voz("Sistema Kira activado")
ev.wait(1.5)
ok(dicho == ["Sistema Kira activado"], "«voz» dice el texto (en un hilo, no bloquea)")

# voz_portatil: si hay un lector, lo lanza; si no, no pasa nada
_which = kiraos.shutil.which
try:
    kiraos.shutil.which = lambda prog: "/usr/bin/" + prog if prog == "spd-say" else None
    ordenes = []
    r = kiraos.voz_portatil("hola", correr=lambda o: ordenes.append(o))
    ok(r is True and ordenes and "hola" in ordenes[0], "voz_portatil usa el lector del sistema cuando lo hay")
    kiraos.shutil.which = lambda prog: None
    ok(kiraos.voz_portatil("hola", correr=lambda o: ordenes.append(o)) is False,
       "si no hay lector, la voz no rompe (calla)")
finally:
    kiraos.shutil.which = _which

# el mapa de ataques: el puente devuelve los datos aunque no haya ataques aún
m = api.mapa_ataques()
ok(isinstance(m, dict) and "ataques" in m and m["total"] == 0, "el puente del mapa responde (vacío si no hay ataques)")
mapa_html = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "mapa.html"), encoding="utf-8").read()
ok("mapa_ataques" in mapa_html and "APARENTE" in mapa_html, "el mapa pide los datos y avisa de que el origen es aparente")

# la pantalla HTML existe y tiene lo esencial
html = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "arranque.html"), encoding="utf-8").read()
ok("pulsa cualquier tecla" in html.lower(), "la pantalla trae el «pulsa cualquier tecla»")
ok("Sistema Kira activado" in html, "la pantalla dispara la voz «Sistema Kira activado»")
ok("pywebview" in html, "la pantalla habla con Python por el puente (pywebview)")
ok("api().comprobar" in html, "la pantalla comprueba el PIN con el candado")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
