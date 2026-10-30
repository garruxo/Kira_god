# -*- coding: utf-8 -*-
"""v2.60: aprender más códigos avanzados y experimentar a partir de lo aprendido.
- saber_avanzado: las recetas nuevas están y son únicas.
- experimentos: `quiere_mejorar`, y `plan(mejorar=True)` mete una hipótesis «mejorar» con el código base.
- internet: `pedido_aprender_codigo` reconoce «aprende código de …».
- núcleo: `aprender_codigo` busca con un internet de mentira y guarda en el baúl."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ["KIRA_DATA_DIR"] = tempfile.mkdtemp()
os.environ.pop("KIRA_API_KEY", None)

import saber_avanzado_kira as sa
import experimentos_kira as ex
import internet_kira as ik

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


# --- recetas avanzadas nuevas ---
ids = [r["id"] for r in sa.RECETAS]
for nuevo in ("cache_menos_usado", "trie_autocompletar", "orden_dependencias", "limite_peticiones", "evaluar_expresion"):
    ok(nuevo in ids, f"la receta nueva «{nuevo}» está")
ok(len(ids) == len(set(ids)), "no hay recetas repetidas")

# --- experimentar a partir de lo aprendido ---
ok(ex.quiere_mejorar("experimenta MEJORANDO lo que sabes de grafos"), "reconoce «experimenta mejorando…»")
ok(ex.quiere_mejorar("optimiza el algoritmo que aprendiste"), "reconoce «optimiza…»")
ok(not ex.quiere_mejorar("experimenta con colores y música"), "un experimento normal no es «mejorar»")

RECETA = {"id": "demo", "titulo": "Caché LRU", "idea": "guarda lo reciente", "complejidad": "O(1)",
          "codigo": "class Cache:\n    def __init__(self):\n        self.d = {}\n"}
plan = ex.plan("caché", n=3, recetas=[RECETA], mejorar=True)
ok(plan and plan[0]["enfoque"] == "mejorar", "con mejorar=True, la 1.ª hipótesis es MEJORAR")
ok(plan[0].get("codigo_base") == RECETA["codigo"], "la hipótesis de mejorar lleva el código base")
pedido = ex.pedido_de("caché", plan[0], local=True)
ok("YA FUNCIONA" in pedido and "class Cache" in pedido, "el pedido al cerebro incluye el código que hay que mejorar")
# sin mejorar, no se cuela el código base
plan2 = ex.plan("caché", n=3, recetas=[RECETA], mejorar=False)
ok(all(h.get("enfoque") != "mejorar" for h in plan2), "sin mejorar=True no hay hipótesis «mejorar»")

# --- aprender código de internet (reconocedor) ---
ok(ik.pedido_aprender_codigo("aprende código de ordenar una lista") == "ordenar una lista", "reconoce «aprende código de …»")
ok(ik.pedido_aprender_codigo("Kira, aprende a programar un chat en python") == "un chat en python", "reconoce «aprende a programar …»")
ok(ik.pedido_aprender_codigo("aprende de este vídeo https://youtu.be/x") is None, "no se mete con los vídeos")
ok(ik.pedido_aprender_codigo("qué tal estás") is None, "una frase normal no es orden de aprender código")

# --- núcleo: aprender_codigo con un internet de mentira ---
import kira_god


class InternetFalso:
    def buscar(self, consulta, tipo="web", n=8):
        self._res = [{"url": "https://github.com/x/y", "fuente": "github.com", "titulo": "ejemplo"},
                     {"url": "https://stackoverflow.com/q/1", "fuente": "stackoverflow.com", "titulo": "resp"}]
        return self._res

    def leer(self, url):
        return {"url": url, "texto": "Aquí explican cómo ordenar una lista en Python.",
                "codigos": ["def ordena(x):\n    return sorted(x)"]}

    def codigo_de(self, pag):
        return (pag.get("codigos") or [""])[0]


core = kira_god.KiraGodCore()
core.internet = InternetFalso()
pasos = []
r = core.aprender_codigo("ordenar una lista", al_paso=lambda t: pasos.append(t))
ok(r.startswith("[OK]") and "github.com" in r, "aprende código y dice de dónde: " + r)
ok(pasos, "va contando lo que lee")
if getattr(core, "recuerdos", None) is not None:
    hits = core.recuerdos.buscar("ordenar una lista")
    ok(any("sorted" in h["texto"] or "ordena" in h["texto"] for h in hits),
       "el código aprendido queda guardado y se puede recordar (no se mete solo al cerebro: seguridad)")

print(f"\nTODO BIEN {n}" if True else "")
