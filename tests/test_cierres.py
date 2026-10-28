# -*- coding: utf-8 -*-
"""El resumen del último cierre (cierres_kira.resumen_cierre): si la app se cerró de golpe, un aviso CORTO y claro,
SIN volcar el registro técnico de Kivy en la pantalla (el fallo que vio el dueño en el móvil real)."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import cierres_kira as ck

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


# un volcado de faulthandler como el del móvil (crash nativo), con la lista de módulos de Kivy al final
CRASH = """Fatal Python error: Segmentation fault

Current thread 0x0000 (most recent call first):
  File "kivy/graphics/instructions.pyx", line 1, in kivy.graphics.instructions
  File "main.py", line 200, in build
Extension modules: androidembed, kivy._clock, jnius.jnius, android._android,
kivy.graphics.context, kivy.core.window._window_sdl2, kivy.core.text._text_sdl2 (total: 34)
"""

r = ck.resumen_cierre(CRASH)
ok(r != "", "si hubo un cierre de golpe, avisa")
ok("me cerré sola" in r and "ya he vuelto" in r, "el aviso es corto y en cristiano")
ok("Extension modules" not in r and "kivy." not in r and "_window_sdl2" not in r,
   "NO vuelca la lista de módulos de Kivy en la pantalla (el fallo del móvil)")
ok("File " not in r, "no mete las rutas del traceback")
ok("Segmentation fault" in r, "sí deja ver el motivo técnico de una línea (Segmentation fault)")

# sin crash: no avisa de nada
ok(ck.resumen_cierre("=== arranque normal ===\ntodo bien\n") == "", "si no hubo cierre de golpe, no avisa")
ok(ck.resumen_cierre("") == "", "vacío no rompe")

# un crash de Python con una excepción con nombre: saca esa línea como motivo
CRASH2 = """Fatal Python error: Aborted

Current thread (most recent call first):
  File "x.py", line 1
MemoryError: out of memory
Extension modules: kivy._clock (total: 1)
"""
r2 = ck.resumen_cierre(CRASH2)
ok("MemoryError" in r2 and "Extension modules" not in r2, "saca el error de verdad (MemoryError) y no el ruido")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
