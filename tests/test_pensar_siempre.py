# -*- coding: utf-8 -*-
"""v2.76: pensar SIN PARAR con pausa al atender al dueño y retoma tras 5 min + no pararse al pedir permiso.
Como kira_god/interfaz usan Kivy (no importables aquí), se comprueba el cableado por AST/texto."""
import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


src_g = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
src_i = open(os.path.join(RAIZ, "interfaz_kira.py"), encoding="utf-8").read()
arb = ast.parse(src_g)

metodos = {node.name for node in ast.walk(arb) if isinstance(node, ast.FunctionDef)}
for m in ("registrar_actividad", "reanudar_pensar", "pensar_sola", "procesar_orden"):
    ok(m in metodos, f"kira_god define {m}")

# procesar_orden marca actividad del dueño (para pausar el pensar y atenderle)
po = next(node for node in ast.walk(arb) if isinstance(node, ast.FunctionDef) and node.name == "procesar_orden")
cuerpo_po = ast.get_source_segment(src_g, po) or ""
ok("registrar_actividad()" in cuerpo_po, "procesar_orden registra actividad al recibir una orden")

# pensar_sola: tiene la ventana de inactividad y NO se para al pedir permiso (apunta y sigue)
ps = next(node for node in ast.walk(arb) if isinstance(node, ast.FunctionDef) and node.name == "pensar_sola")
cuerpo_ps = ast.get_source_segment(src_g, ps) or ""
ok("_inactivo_seg" in cuerpo_ps and "_ultima_actividad" in cuerpo_ps, "pensar_sola usa la ventana de inactividad")
ok("apuntar_permiso" in cuerpo_ps, "pensar_sola avisa del permiso")
tras = cuerpo_ps.split("apuntar_permiso", 1)[1].split("except", 1)[0]
ok("fallo = False" in tras, "tras avisar del permiso NO cuenta como fallo (no se para)")
ok("inactivo_seg=300" in cuerpo_ps or "inactivo_seg = 300" in cuerpo_ps, "la espera por defecto son 5 minutos")

# la interfaz reanuda al abrir y marca actividad cuando el dueño habla/escribe
ok("reanudar_pensar" in src_i, "la interfaz reanuda el pensar al abrir")
ok(src_i.count("registrar_actividad") >= 2, "la interfaz marca actividad al hablar y al escribir")

print(f"\nTODO BIEN {n}")
