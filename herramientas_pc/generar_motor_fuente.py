# -*- coding: utf-8 -*-
"""Genera motor_fuente_kira.py: el TEXTO del motor de juegos guardado como una cadena.
Dentro del APK los .py se convierten a .pyc y el original desaparece; la versión web y la app de verdad necesitan
el texto del motor, así que va aquí. (La compilación de GitHub lo regenera; tests/test_web_juegos.py comprueba
que coincide.)"""
import os

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(AQUI, "motor_juegos_kira.py"), encoding="utf-8") as f:
    texto = f.read()
with open(os.path.join(AQUI, "motor_fuente_kira.py"), "w", encoding="utf-8") as f:
    f.write("# -*- coding: utf-8 -*-\n# GENERADO por herramientas_pc/generar_motor_fuente.py: no lo cambies a mano.\n"
            "MOTOR = " + repr(texto) + "\n")
print("motor_fuente_kira.py listo")
