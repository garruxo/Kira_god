# -*- coding: utf-8 -*-
"""v2.76 (arreglo visto en el móvil REAL): al experimentar pensando salía «no pude experimentar: 'tuple' object has
no attribute 'get'». Causa: programar_kira.probar_programa devuelve una TUPLA (ok, motivo, dato), y _experimentar_pensando
la usaba como diccionario (r.get(...)). Aquí se comprueba el contrato de la tupla y que el núcleo la desempaqueta bien."""
import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import programar_kira as pk

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


# contrato: probar_programa devuelve (ok, motivo, dato), NO un dict
r = pk.probar_programa("print(1+1)")
ok(isinstance(r, tuple) and len(r) == 3, "probar_programa devuelve una tupla de 3")
ok_prog, motivo, dato = r
ok(ok_prog is True, "un print simple pasa")
ok((dato or {}).get("salida", "").strip() == "2", "la salida sale del dato, no del propio resultado")
# el bug de antes: tratar la tupla como dict revienta con exactamente ese error
try:
    r.get("ok")
    ok(False, "una tupla NO tiene .get (debería haber reventado)")
except AttributeError as e:
    ok("tuple" in str(e) and "get" in str(e), "reproduce el error del móvil si se usa como dict")

# un programa que falla -> ok_prog False y motivo con texto (lo que usa _experimentar_pensando como err)
okf, motivof, datof = pk.probar_programa("print(")
ok(okf is False and str(motivof), "un programa roto da ok=False y un motivo")

# el núcleo desempaqueta la tupla y NO llama .get('ok') sobre el resultado de probar_programa
src = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
arb = ast.parse(src)
ep = next(nd for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef) and nd.name == "_experimentar_pensando")
cuerpo = ast.get_source_segment(src, ep) or ""
ok("= pk.probar_programa(codigo)" in cuerpo, "llama a probar_programa")
ok(", motivo, dato = pk.probar_programa(codigo)" in cuerpo or ", _motivo, dato = pk.probar_programa(codigo)" in cuerpo
   or "ok_prog, motivo, dato = pk.probar_programa(codigo)" in cuerpo, "desempaqueta la tupla (ok, motivo, dato)")
ok("r.get(\"ok\")" not in cuerpo and "r.get('ok')" not in cuerpo, "ya NO trata el resultado como diccionario")

print(f"\nTODO BIEN {n}")
