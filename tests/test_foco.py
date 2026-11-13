# -*- coding: utf-8 -*-
"""v2.77: FOCO — pensar en algo CONCRETO sin parar hasta resolverlo; al resolver, preguntar App/Web/En Kira; y queda
SIEMPRE visible en la Sala Hacker ▸ Biblioteca ▸ Soluciones. kira_god/interfaz/sala usan Kivy (no importables aquí):
se comprueba el cableado por AST/texto. Lo puro (las preguntas de mejora) sí se prueba de verdad."""
import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import pensador_kira as pk

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


# --- PURO: el pensador también se pregunta cómo MEJORAR y cuál es la MEJOR forma ---
qs = pk.generar_preguntas("una pila")
ok(len(qs) == 10, "10 tipos de pregunta")
ok(any("MEJORAR" in q for q in qs), "se pregunta cómo MEJORAR y qué se necesita")
ok(any("MEJOR forma" in q for q in qs), "busca la MEJOR forma")
# actitud de programadora experta: incorporar a su sistema, mejorar su código, programar en Kivy/Python
ok(any("INCORPORAR" in q and "Kira" in q for q in qs), "se pregunta si incorporarlo a su sistema")
ok(any("mi propio código" in q for q in qs), "se pregunta qué mejorar en su propio código")
ok(any("Python/Kivy" in q for q in qs), "se pregunta cómo programarlo en Python/Kivy")

src_g = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
src_i = open(os.path.join(RAIZ, "interfaz_kira.py"), encoding="utf-8").read()
src_s = open(os.path.join(RAIZ, "sala_hacker_kira.py"), encoding="utf-8").read()
arb = ast.parse(src_g)
metodos = {nd.name for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef)}

for m in ("enfocar", "dejar_foco", "retomar_foco", "usar_solucion", "soluciones_lista", "_foco_cargar", "_foco_guardar"):
    ok(m in metodos, f"kira_god define {m}")

# el bucle de pensar: cuando hay foco activo, hace el CICLO sobre ese tema y, al resolver, avisa (al_solucion)
ps = next(nd for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef) and nd.name == "pensar_sola")
cuerpo_ps = ast.get_source_segment(src_g, ps) or ""
ok("_foco_cargar()" in cuerpo_ps and "ciclo_una(semilla=foco" in cuerpo_ps, "el bucle piensa en el foco con el ciclo")
ok("resuelto" in cuerpo_ps and "al_solucion" in cuerpo_ps, "al resolver marca resuelto y avisa")

# enfocar guarda el foco en DISCO y arranca el pensar
enf = next(nd for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef) and nd.name == "enfocar")
cuerpo_enf = ast.get_source_segment(src_g, enf) or ""
ok("_foco_guardar" in cuerpo_enf and "pensar_sola(True)" in cuerpo_enf, "enfocar guarda en disco y empieza a pensar")

# voz: «piensa en X hasta resolverlo», «céntrate/enfócate/resuélveme X», «déjalo para otro día», «retoma X»
op = next(nd for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef) and nd.name == "_orden_pensar")
cuerpo_op = ast.get_source_segment(src_g, op) or ""
ok("self.enfocar(" in cuerpo_op, "voz: enfocar un tema concreto")
ok("self.dejar_foco()" in cuerpo_op, "voz: déjalo para otro día")
ok("self.retomar_foco(" in cuerpo_op, "voz: retomar el foco")
# y el dispatch de procesar_orden deja pasar esas frases hacia _orden_pensar
po = next(nd for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef) and nd.name == "_procesar_orden")
cuerpo_po = ast.get_source_segment(src_g, po) or ""
for palabra in ("enf[oó]cate", "resu[eé]lveme", "d[eé]jalo", "retoma"):
    ok(palabra in cuerpo_po, f"el dispatch deja pasar «{palabra}»")

# interfaz: al resolver sale el popup con App / Web / En Kira (y Luego), enganchado por core.al_solucion
ok("def mostrar_solucion" in src_i, "la interfaz tiene el popup de solución")
ok("core.al_solucion" in src_i, "el popup se engancha a al_solucion")
for etq in ('"App"', '"Web"', '"En Kira"'):
    ok(etq in src_i, f"el popup ofrece {etq}")
ok('"app"' in src_i and '"web"' in src_i and '"kira"' in src_i, "los botones llaman a usar_solucion con app/web/kira")

# Sala Hacker ▸ Biblioteca: estante «Soluciones» SIEMPRE visible, tira de core.soluciones_lista()
ok('("solucion", "Soluciones")' in src_s, "estante Soluciones en la biblioteca")
ok("core.soluciones_lista()" in src_s, "la biblioteca muestra las soluciones (y el foco) siempre")

print(f"\nTODO BIEN {n}")
