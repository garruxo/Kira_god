# -*- coding: utf-8 -*-
"""v3.15: la clave de GitHub (para las apps Android de verdad) se puede dar SIN «:» (el teclado del dueño no lo
tiene): «config github ghp_…» o «mi clave de github es ghp_…». Se guarda 0600 y nunca se enseña."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import kira_god
import ordenes_kira
import wifi_kira

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


TOK = "ghp_" + "A1b2C3d4" * 5
for frase in ("config github: " + TOK, "config github " + TOK, "mi clave de github es " + TOK, "Config GitHub " + TOK):
    d = tempfile.mkdtemp()
    core = kira_god.KiraGodCore.__new__(kira_god.KiraGodCore)
    core.dir = d
    try:
        r = core.procesar_orden(frase)
    except Exception as e:                       # noqa: BLE001
        r = f"excepción {e}"
    ruta = os.path.join(d, "github_token.txt")
    guardada = os.path.exists(ruta) and open(ruta).read() == TOK
    ok(guardada and "[OK]" in str(r) and TOK not in str(r), f"«{frase[:24]}…» guarda la clave: {str(r)[:70]}")
    if guardada:
        ok(oct(os.stat(ruta).st_mode & 0o777) == "0o600", "  …solo legible por ti (0600)")
    ok(TOK not in ordenes_kira.ocultar_claves(frase), "  …y nunca se enseña en la lista de tareas")
    ok(wifi_kira.orden_wifi(frase) is None, "  …y no la confunde con la WiFi")

d = tempfile.mkdtemp()
core = kira_god.KiraGodCore.__new__(kira_god.KiraGodCore)
core.dir = d
r = core.procesar_orden("config github hola")
ok("no tiene buena pinta" in str(r) and not os.path.exists(os.path.join(d, "github_token.txt")), "una clave rara: no la guarda")
print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
