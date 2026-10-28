# -*- coding: utf-8 -*-
"""Explicar código línea por línea de forma técnica (explicacion_codigo_kira): reconoce funciones, argumentos,
bucles, condiciones, variables, return, import…; y aguanta código a medio escribir (explicación por patrones)."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import explicacion_codigo_kira as ex

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


CODIGO = '''# avisa si una app gasta mucha bateria
import os

def registrar(nucleo):
    nucleo.anadir_orden("bateria", revisar)

def revisar(nucleo, texto):
    apps = nucleo.consumo()
    altas = [a for a in apps if a.pct > 20]
    if not altas:
        return "Ninguna gasta de mas."
    return "Gastan mucho"
'''

r = ex.explicar(CODIGO)
porlinea = {l["n"]: l["nota"] for l in r["lineas"]}

ok(porlinea[1].startswith("comentario"), "reconoce un comentario")
ok("import" in porlinea[2] and "os" in porlinea[2], "reconoce el import y nombra el módulo")
ok("función «registrar»" in porlinea[4] and "nucleo" in porlinea[4], "reconoce la función y sus argumentos")
ok("variable" in porlinea[8] and "apps" in porlinea[8], "reconoce una variable")
ok("for" in porlinea[9] or "bucle" in porlinea[9], "reconoce el bucle de la comprensión de lista")
ok("if" in porlinea[10] and "condición" in porlinea[10], "reconoce la condición")
ok("return" in porlinea[11].lower() and "devuelve" in porlinea[11], "reconoce el return")
ok("registrar" in r["resumen"] and "revisar" in r["resumen"], "el resumen nombra las funciones definidas")

# código a medio escribir (no es válido aún): no rompe, explica por patrones
med = "def suma(a, b):\n    return a +"
r2 = ex.explicar(med)
notas2 = [l["nota"] for l in r2["lineas"]]
ok(any("suma" in n for n in notas2), "con código a medio escribir, sigue explicando (por patrones)")
ok("medio escribir" in r2["resumen"], "avisa de que el código está a medio escribir")

# texto plano para la charla/voz
t = ex.texto_plano(CODIGO)
ok("Línea 4:" in t and "función" in t, "la versión en texto corrido sale bien")

# vacío no rompe
ok(ex.explicar("")["lineas"] == [] or all(l["nota"] == "" for l in ex.explicar("")["lineas"]), "código vacío no rompe")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
