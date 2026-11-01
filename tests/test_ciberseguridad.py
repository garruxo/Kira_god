# -*- coding: utf-8 -*-
"""v2.63: ciberseguridad DEFENSIVA. Cada receta pasa el editor seguro y el laboratorio del móvil con sus pruebas;
las fichas van al baúl sin internet; ids únicos y sin pisar otras recetas; las fuentes son sitios oficiales (https).
SOLO defensa: las recetas no abren red ni ejecutan el sistema."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ["KIRA_DATA_DIR"] = tempfile.mkdtemp()

import saber_ciberseguridad_kira as cs
import recetas_ingenieria_kira as ri
import saber_avanzado_kira as sa
import mejoras_ia_kira as mi
import ejecutor_kira as ej
import laboratorio_movil_kira as lm

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


# --- ids únicos y sin chocar con otras recetas/conceptos ---
ids = [r["id"] for r in cs.RECETAS]
otros_r = {r["id"] for r in ri.RECETAS} | {r["id"] for r in sa.RECETAS}
ok(len(ids) == len(set(ids)) and not set(ids) & otros_r, "recetas con id único y sin pisar otras")
cids = [c["id"] for c in cs.CONCEPTOS]
otros_c = {c["id"] for c in ri.CONCEPTOS} | {c["id"] for c in sa.CONCEPTOS}
ok(len(cids) == len(set(cids)) and not set(cids) & otros_c, "conceptos con id único")
ok(len(cs.RECETAS) >= 6 and len(cs.CONCEPTOS) >= 10, "al menos 6 recetas y 10 fichas")

# --- cada receta: ficha completa, segura, corre en el editor y pasa sus pruebas y el laboratorio ---
LAB = lm.LaboratorioMovil()
for r in cs.RECETAS:
    ok(all(r.get(k) for k in ("id", "titulo", "area", "temas", "idea", "complejidad", "codigo", "prueba")),
       f"{r['id']}: ficha completa")
    ok(r["area"] == "Ciberseguridad", f"{r['id']}: área Ciberseguridad")
    ok(mi.precomprobar(r["codigo"]) is None, f"{r['id']}: pasa la revisión previa")
    # SOLO defensa: nada de red ni sistema
    ok(not any(x in r["codigo"] for x in ("import socket", "import os", "subprocess", "urllib", "open(")),
       f"{r['id']}: no abre red/sistema (solo defensa)")
    demo = cs.demo(r)
    ok(ej.revisar(demo) is None, f"{r['id']}: vale para el editor seguro: {ej.revisar(demo)}")
    s = ej.ejecutar(demo, limite=10)
    ok(s["ok"], f"{r['id']}: se ejecuta: {s['error']}")
    for orden, arg, espera in r["prueba"]:
        ok(espera in s["salida"], f"{r['id']}: «{orden} {arg}» -> «{espera}»\n{s['salida']}")
    v = LAB.probar(r["id"], r["codigo"])
    ok(v["ok"], f"{r['id']}: el laboratorio del móvil la aprueba: {[e for e in v['etapas'] if not e['ok']]}")

# --- fichas para el baúl ---
f = cs.fichas()
ok(len(f) == len(cs.RECETAS) + len(cs.CONCEPTOS) and all(len(t) == 2 for t in f), "fichas = recetas + conceptos")
ok(all(len(texto) > 60 for _tema, texto in f), "cada ficha trae texto")

# --- se guardan en el baúl SIN internet ---
import recuerdos_kira as rk
B = rk.Recuerdos(os.path.join(os.environ["KIRA_DATA_DIR"], "baul"))
nuevas = 0
for tema, texto in cs.fichas():
    if B.guardar(texto, tema=tema, fuente="saber de ciberseguridad de Kira"):
        nuevas += 1
ok(nuevas >= len(cs.CONCEPTOS), "guarda las fichas en el baúl")
ok("phishing" in B.contexto("qué es el phishing").lower(), "luego responde sobre phishing desde el baúl")

# --- fuentes oficiales: todas https y de sitios reconocidos ---
ok(cs.FUENTES_OFICIALES and all(x["url"].startswith("https://") for x in cs.FUENTES_OFICIALES), "fuentes con https")
ok(all(any(s in x["url"] for s in ("incibe.es", "owasp.org", "wikipedia.org")) for x in cs.FUENTES_OFICIALES),
   "fuentes de sitios oficiales/reconocidos (INCIBE, OWASP, Wikipedia)")

print(f"\nTODO BIEN {n}" if not False else "")
