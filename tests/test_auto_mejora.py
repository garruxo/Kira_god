# -*- coding: utf-8 -*-
"""v2.79: AUTO-MEJORA (aplicar sola SOLO si pasa TODO, con copia de seguridad y RETORNO si falla al arrancar; avisar
y «llévame al código») + APP WEB instalable. La lógica pura (interruptor, verificación/retorno, registro) y la app web
se prueban DE VERDAD; el resto (panel/núcleo/interfaz/main) usa Kivy o el promotor, así que se comprueba por AST/texto.
Regla que NO cambia: aplicar sola exige pasar el laboratorio y las pruebas (eso lo decide el promotor)."""
import ast
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import auto_mejora_kira as am
import app_web_kira as aw

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


# ---------- PURO: interruptor (viene APAGADO) ----------
d = tempfile.mkdtemp()
ok(am.encendido(d) is False, "la auto-mejora viene APAGADA")
am.encender(d, True)
ok(am.encendido(d) is True, "se puede encender")
am.encender(d, False)
ok(am.encendido(d) is False, "se puede apagar")

# ---------- PURO: aplicar sola -> verificación pendiente -> retorno si hubo crash ----------
am.marcar_aplicada(d, "mi_modulo", "suma dos números", "/ruta/mi_modulo.py")
ok(am.pendiente_verificar(d) is not None, "queda una mejora a la espera de confirmar")
# si al arrancar hubo crash -> hay que REVERTIR (retorno)
ok(am.decidir_al_arrancar(d, True) == ("revertir", "mi_modulo"), "si se cayó -> revertir")
# si no hubo crash -> confirmar
ok(am.decidir_al_arrancar(d, False) == ("confirmar", "mi_modulo"), "si arrancó bien -> confirmar")

# confirmar la deja puesta y ya no hay pendiente
am.confirmar(d, "mi_modulo")
ok(am.pendiente_verificar(d) is None, "tras confirmar no queda pendiente")
ok(am.decidir_al_arrancar(d, True) == ("nada", ""), "sin pendiente no hay nada que hacer")
ok("mi_modulo" in am.texto_hechas(d) and "funcion" in am.texto_hechas(d).lower(), "el registro menciona lo hecho")

# otra aplicada que SÍ se revierte
d2 = tempfile.mkdtemp()
am.marcar_aplicada(d2, "malo", "rompe algo")
am.revertida(d2, "malo", "la app se cayó")
ok(am.pendiente_verificar(d2) is None, "tras revertir no queda pendiente")
ok("quit" in am.texto_hechas(d2).lower() or "revert" in am.texto_hechas(d2).lower() or "fallaba" in am.texto_hechas(d2).lower(),
   "el registro marca la revertida")

# ---------- APP WEB de verdad ----------
h = aw.html_app("print('holakira', 6*7)", titulo="Prueba")
ok("<!DOCTYPE html" in h, "la app web es un html")
ok("holakira" in h, "el html lleva el programa dentro")
ok("brython" in h.lower(), "lleva Brython metido (sin internet)")
ok(aw.nombre_archivo("Mi App Genial").endswith(".html"), "nombre de archivo .html")
try:
    aw.html_app("import requests\nprint(1)")
    ok(False, "debería rechazar imports no soportados en web")
except aw.WebError:
    ok(True, "rechaza lo que no va en web (con WebError claro)")

# ---------- CABLEADO por AST/texto ----------
src_p = open(os.path.join(RAIZ, "panel_kira.py"), encoding="utf-8").read()
src_g = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
src_i = open(os.path.join(RAIZ, "interfaz_kira.py"), encoding="utf-8").read()
src_m = open(os.path.join(RAIZ, "main.py"), encoding="utf-8").read()

met_p = {nd.name for nd in ast.walk(ast.parse(src_p)) if isinstance(nd, ast.FunctionDef)}
for m in ("auto_mejora", "auto_implementar", "verificar_auto_mejora", "llevar_al_codigo", "auto_hechas_texto"):
    ok(m in met_p, f"panel_kira define {m}")
# el panel aplica SOLO si pasa (preparar.aprobable) y usa el promotor (copia de seguridad) y marca para el retorno
ai = next(nd for nd in ast.walk(ast.parse(src_p)) if isinstance(nd, ast.FunctionDef) and nd.name == "auto_implementar")
cuerpo_ai = ast.get_source_segment(src_p, ai) or ""
ok("aprobable" in cuerpo_ai, "solo aplica si la mejora es aprobable (pasó el laboratorio)")
ok("self.promotor.aplicar" in cuerpo_ai and "marcar_aplicada" in cuerpo_ai, "aplica con el promotor y marca para el retorno")
ok("encendido" in cuerpo_ai, "respeta el interruptor (no aplica sola si está apagado)")
vm = next(nd for nd in ast.walk(ast.parse(src_p)) if isinstance(nd, ast.FunctionDef) and nd.name == "verificar_auto_mejora")
ok("revertir" in (ast.get_source_segment(src_p, vm) or ""), "al arrancar puede revertir (retorno)")

# panel al construir: engancha core._panel y verifica al arrancar
ok("core._panel = ctl" in src_p and "verificar_auto_mejora" in src_p, "construir_panel engancha el panel y verifica")

# núcleo: voz + puente
met_g = {nd.name for nd in ast.walk(ast.parse(src_g)) if isinstance(nd, ast.FunctionDef)}
for m in ("_auto_mejora", "_auto_llevar_codigo", "auto_implementar", "auto_mejora_encendida"):
    ok(m in met_g, f"kira_god define {m}")
ok("usar_solucion" in met_g, "usar_solucion existe")
us = next(nd for nd in ast.walk(ast.parse(src_g)) if isinstance(nd, ast.FunctionDef) and nd.name == "usar_solucion")
ok("app_web_kira" in (ast.get_source_segment(src_g, us) or ""), "usar_solucion «app» hace una app web (no solo maqueta)")

# interfaz: con auto-mejora encendida implementa sola; aviso de arranque
ok("auto_mejora_encendida" in src_i, "la interfaz mira si la auto-mejora está encendida")
ok("core.auto_implementar" in src_i, "con la auto-mejora, la interfaz implementa sola")
ok("aviso_auto_mejora" in src_i, "la interfaz muestra el aviso de arranque (retorno/confirmación)")

# main: calcula si hubo crash para el retorno
ok("hubo_crash = bool(aviso)" in src_m, "main marca hubo_crash para el retorno")

print(f"\nTODO BIEN {n}")
