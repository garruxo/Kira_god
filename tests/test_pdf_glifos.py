# -*- coding: utf-8 -*-
"""v2.70: al leer un PDF de matemáticas/lógica, los símbolos salían como nombres de fuente («comma.math», «period.math»)
o cuadritos. `pdf_kira._limpiar` ahora los limpia. Lógica pura."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pdf_kira as pk

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


# lo que salía roto en el móvil
roto = "¬(/p.math/q.math) ≡ ¬/p.math/comma.math ∨ ¬/q.math/period.math �"
limpio = pk._limpiar(roto)
ok(".math" not in limpio, "quita los nombres de glifo .math")
ok("/p.math" not in limpio and "/q.math" not in limpio, "quita /p.math y /q.math")
ok("," in limpio and "." in limpio, "comma.math -> ',' y period.math -> '.'")
ok("p" in limpio and "q" in limpio, "deja las variables p y q")
ok("�" not in limpio and "" not in limpio, "quita los cuadritos/reemplazo")

# símbolos lógicos con nombre de fuente
ok("¬" in pk._limpiar("/logicalnot.math a"), "logicalnot.math -> ¬")
ok("∧" in pk._limpiar("a /logicaland.math b"), "logicaland.math -> ∧")
ok("∈" in pk._limpiar("x /element.math A"), "element.math -> ∈")

# no rompe texto normal
normal = "Las leyes de De Morgan dicen que no (a y b) es no-a o no-b."
ok(pk._limpiar(normal) == normal, "el texto normal se queda igual")

print(f"\nTODO BIEN {n}")
