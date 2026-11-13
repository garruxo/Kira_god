# -*- coding: utf-8 -*-
"""v3.25: cuando aprende siguiendo enlaces, Kira se CENTRA en lo pedido:
- de la página principal solo mira los enlaces que parecen tratar el tema;
- al ABRIR cada enlace, solo lo sigue estudiando si de verdad está lo que busca (o es la página siguiente del curso);
  si no, vuelve a la página anterior y pasa al siguiente enlace;
- y lo que APRENDE lo deja apuntado para EXPERIMENTAR y sacar una mejora, una función nueva o una app (móvil/portátil).
"""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
import internet_kira as ik  # noqa: E402

n = fallos = 0


def ok(c, m):
    global n, fallos
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ---------------- trata_del_tema (puro) ----------------
ok(ik.trata_del_tema("Las variables en Python guardan datos", "python"), "contenido que SÍ trata del tema")
ok(not ik.trata_del_tema("Recetas de cocina y repostería casera", "python"), "contenido que NO trata del tema")
ok(ik.trata_del_tema("Las redes neuronales y el aprendizaje profundo", "redes neuronales"),
   "tema de dos palabras: el contenido las trae")
ok(not ik.trata_del_tema("redes de ordenadores y cables", "redes neuronales"),
   "tema de dos palabras: solo una no basta (no lo confunde)")
ok(ik.trata_del_tema("cualquier cosa", ""), "sin tema no filtra (todo vale)")

# ---------------- páginas de mentira ----------------
A = "https://ej.es/py/variables"
B = "https://ej.es/py/trucos"
C = "https://ej.es/cocina"
PRINC = {"url": "https://ej.es/py/", "titulo": "Curso de Python", "texto": "Curso de Python. " * 3, "enlaces": [
    {"url": A, "texto": "Variables en Python"},
    {"url": B, "texto": "Trucos de Python"},          # el texto habla de python, pero el contenido NO
    {"url": C, "texto": "Recetas de cocina"},          # ni el texto ni el contenido: ni se abre
]}
CONT = {
    A: {"url": A, "titulo": "Variables", "texto": "Las variables en Python guardan datos y valores. " * 5, "enlaces": []},
    B: {"url": B, "titulo": "Trucos", "texto": "Hoy te traigo recetas de cocina y repostería casera. " * 5, "enlaces": []},
}
leidas = []


class FalsaNet:
    pagina = None

    def leer(self, url):
        leidas.append(url)
        pag = CONT.get(url) or PRINC if url == PRINC["url"] else CONT.get(url, {
            "url": url, "titulo": url, "texto": "Página sin relación. " * 3, "enlaces": []})
        self.pagina = pag
        return pag


import kira_god  # noqa: E402

core = kira_god.KiraGodCore()
core.internet = FalsaNet()
core.resumir_pagina = lambda pag, tema="": ((pag.get("texto", "") or "")[:200], True)
core._repasar_con_claude = lambda *a: False

# ---------------- seguir_enlaces: vuelve y pasa al siguiente si el enlace no trata del tema ----------------
leidas.clear()
res, guardadas = core.seguir_enlaces(PRINC, "python", por_pagina=5, maximo=5)
urls_seguidas = [u for _t, u in res]
ok(A in urls_seguidas, "sigue estudiando el enlace que SÍ trata del tema (variables)")
ok(B not in urls_seguidas, "el enlace cuyo contenido NO trata del tema: vuelve y pasa al siguiente (no lo estudia)")
ok(C not in leidas, "el enlace que ni por el texto trata del tema ni se abre (me centro en lo pedido)")
ok(guardadas == 1, "solo guarda el que de verdad trata del tema")

# ---------------- estudiar_pagina con un tema pedido (orden) ----------------
leidas.clear()
try:
    os.remove(core._ruta_estudio_web())
except OSError:
    pass
r = core.estudiar_pagina(PRINC["url"], orden="python", maximo=20)
ok(r.startswith("[OK]") and "1 página(s)" in r, "estudia solo el enlace que trata del tema: " + r[:80])
ok("no trataban de lo pedido" in r, "dice que volvió y siguió con el siguiente en los que no trataban del tema")
ok(A in leidas and B in leidas, "abrió los dos candidatos del tema (por su texto)")
ok(C not in leidas, "de la principal NO siguió el enlace ajeno al tema (centrado)")

# ---------------- Parte 2: lo aprendido queda para EXPERIMENTAR ----------------
import investigar_kira as iv  # noqa: E402

pend = iv.pendiente(core.dir)
ok(pend and "experimenta con" in pend.lower(), "tras estudiar, deja un encargo de EXPERIMENTAR: " + str(pend))
ok(iv.clasificar_peticion(pend) == "programa", "el encargo es de PROGRAMAR (mejora/función), no una reflexión")

# y _tras_estudiar, directo, para «estudia X»
core._tras_estudiar("redes neuronales")
hay = any("redes neuronales" in (p.get("texto") or "").lower() for p in iv.listar(core.dir))
ok(hay, "«estudia X» (estudiar_a_fondo) también deja el encargo de experimentar con X")
# no duplica el mismo encargo
antes = len(iv.listar(core.dir))
core._tras_estudiar("redes neuronales")
ok(len(iv.listar(core.dir)) == antes, "no apunta dos veces el mismo tema")

# cableado: estudiar_a_fondo y estudiar_pagina llaman a _tras_estudiar
src = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
ok(src.count("_tras_estudiar(") >= 3, "estudiar_a_fondo y estudiar_pagina enganchan _tras_estudiar")
ok("def trata_del_tema" in open(os.path.join(RAIZ, "internet_kira.py"), encoding="utf-8").read(),
   "internet tiene la comprobación de relevancia por contenido")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
