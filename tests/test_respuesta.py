# -*- coding: utf-8 -*-
"""La charla no repite tu orden, no empieza por «Kira,» ni dice «no puedo» lo que Kira sí sabe hacer."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import respuesta_kira as rk

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


orden = ("Kira, busca en internet una biblioteca de juegos 3D para crear un laberinto con IA en Android, luego "
         "implementa el código en el editor con la lógica de vida y enemigos.")
r, c = rk.arreglar(orden, orden)
ok(c and "hazme un juego de laberinto retro" in r and "2D" in r, "un eco de una orden se cambia por órdenes que sí entiende")
r, c = rk.arreglar("Kira, no puedo modificar las funciones de esta app ni crear juegos ni aprender habilidades nuevas.",
                   "Kira, aprende a crear juegos nuevos y pruébalos en tu laboratorio")
ok(c and "aprende a" in r and "no puedo" not in r, "«no puedo crear juegos» se corrige")
r, c = rk.arreglar("Kira, el ciclo de vida de una app se rige por los procesos.", "Kira, ¿cómo es el ciclo de vida de una app?")
ok(r.startswith("El ciclo") and "orden" not in r, "a una pregunta se le deja contestar (solo se quita el «Kira,»)")
r, c = rk.arreglar("Hoy hace sol y unos 20 grados.", "qué tiempo hace")
ok(not c and r == "Hoy hace sol y unos 20 grados.", "una respuesta normal no se toca")
ok(rk.sugerencias("hazme un juego de naves en 3d") [:1] == ["hazme un juego de naves espaciales"], "sugerencia por género")
ok(rk.sugerencias("cuéntame un chiste") == [], "sin tema, sin sugerencias")
r, c = rk.arreglar("Kira, debe priorizar la profundidad sobre la amplitud para construir una base sólida.",
                   "Enfatiza la profundidad sobre la amplitud para construir una base sólida")
ok(c and "una cosa cada vez" in r, "eco sin tema conocido: explica cómo pedir")
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kira_god.py"), encoding="utf-8").read()
ok("respuesta_kira.arreglar(r, texto)" in src and "no empieces con «Kira»" in src, "la charla pasa por el arreglo")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
