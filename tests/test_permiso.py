# -*- coding: utf-8 -*-
"""v2.74: cuando un experimento necesita una librería que no está, Kira la DETECTA (para parar y preguntar al dueño
con la ventana emergente). La información la mira libre; instalar algo, nunca sola. Lógica pura del detector."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import librerias_kira as lk

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


ok(lk.necesita_libreria("Línea 3: el modo seguro no permite importar «requests».") == "requests", "modo seguro -> requests")
ok(lk.necesita_libreria("el modo seguro no permite importar «bs4»") == "bs4", "modo seguro -> bs4")
ok(lk.necesita_libreria("No module named 'pandas'") == "pandas", "No module named -> pandas")
ok(lk.necesita_libreria("ModuleNotFoundError: No module named 'sklearn'") == "sklearn", "ModuleNotFoundError -> sklearn")
ok(lk.necesita_libreria("No module named 'os'") is None, "os NO es instalable -> None")
ok(lk.necesita_libreria("algo falló por otra cosa") is None, "sin librería que falte -> None")
ok(lk.necesita_libreria("") is None and lk.necesita_libreria(None) is None, "vacío -> None")

print(f"\nTODO BIEN {n}")
