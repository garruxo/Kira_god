# -*- coding: utf-8 -*-
"""v2.80: el dueño le da encargos («investiga …», «pregúntate …»); Kira los clasifica y, según sean, los GUARDA
(reflexión), los PROGRAMA o hace una APP. Lógica pura (clasificar, reconocer la orden, guardar las preguntas del
dueño) probada de verdad; el «investigar» real (estudiar/programar/app) y el bucle se comprueban por AST/texto."""
import ast
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import investigar_kira as iv

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


# ---------- clasificar el encargo ----------
ok(iv.clasificar_peticion("qué es un árbol binario") == "reflexion", "«qué es…» -> reflexión")
ok(iv.clasificar_peticion("por qué funciona la recursión") == "reflexion", "«por qué funciona» NO es programa")
ok(iv.clasificar_peticion("qué es una función") == "reflexion", "«qué es una función» -> reflexión")
ok(iv.clasificar_peticion("hazme un programa que ordene una lista") == "programa", "«hazme un programa» -> programa")
ok(iv.clasificar_peticion("puedes hacer lo mismo que una calculadora") == "programa", "«puedes hacer lo mismo» -> programa")
ok(iv.clasificar_peticion("implementa una pila") == "programa", "«implementa» -> programa")
ok(iv.clasificar_peticion("una app de notas") == "app", "«app» -> app")
ok(iv.clasificar_peticion("hazme una app de recetas") == "app", "app gana a programa")

# ---------- reconocer la orden ----------
ok(iv.es_orden("investiga qué es un trie") == ("investiga", "qué es un trie"), "«investiga X»")
ok(iv.es_orden("pregúntate si puedes hacer lo mismo que un cronómetro")[0] == "investiga", "«pregúntate si…»")
ok(iv.es_orden("averigua cómo se hace un hash")[0] == "investiga", "«averigua…»")
ok(iv.es_orden("investiga la búsqueda binaria hasta resolverlo")[0] is None, "«…hasta resolverlo» es FOCO, no esto")
ok(iv.es_orden("pregúntate también qué es un grafo")[0] == "recordar", "«pregúntate también» -> recordar")
ok(iv.es_orden("añade la pregunta: qué es un árbol")[0] == "recordar", "«añade la pregunta» -> recordar")
ok(iv.es_orden("tus preguntas")[0] == "listar", "«tus preguntas» -> listar")
ok(iv.es_orden("hola qué tal")[0] is None, "charla normal no es un encargo")

# ---------- guardar las preguntas del dueño (en disco) ----------
d = tempfile.mkdtemp()
ok(iv.pendiente(d) is None, "sin preguntas, no hay pendiente")
ok(iv.anadir(d, "qué es un trie") is True, "añade una pregunta")
ok(iv.anadir(d, "qué es un trie") is False, "no repite la misma")
ok(iv.pendiente(d) == "qué es un trie", "la pendiente es la que añadí")
iv.marcar_hecha(d, "qué es un trie")
ok(iv.pendiente(d) is None, "tras hacerla no queda pendiente")
ok("trie" in iv.texto_listar(d), "el listado la menciona")
# una recurrente se vuelve a mirar
iv.anadir(d, "mira las novedades", recurrente=True)
iv.marcar_hecha(d, "mira las novedades")
ok(iv.pendiente(d) == "mira las novedades", "una recurrente sigue pendiente tras hacerla")

# ---------- cableado en el núcleo (Kivy/cerebro no importables: por AST) ----------
src = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
arb = ast.parse(src)
met = {nd.name for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef)}
for m in ("investigar", "encargar", "investigar_listar", "_investigar_reflexion", "_investigar_programa",
          "_investigar_app", "_guardar_solucion"):
    ok(m in met, f"kira_god define {m}")
# las preguntas del dueño se GUARDAN para cuando piensa (la voz llama a encargar, no ejecuta al vuelo)
ok("self.encargar(carga)" in src, "la voz guarda el encargo (no lo hace al instante)")
enc = next(nd for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef) and nd.name == "encargar")
ok("iv.anadir" in (ast.get_source_segment(src, enc) or ""), "encargar guarda la pregunta en disco")
inv = next(nd for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef) and nd.name == "investigar")
ci = ast.get_source_segment(src, inv) or ""
ok("clasificar_peticion" in ci, "investigar clasifica el encargo")
ok("_investigar_app" in ci and "_investigar_programa" in ci and "_investigar_reflexion" in ci, "enruta a los tres")
# reflexión guarda en el baúl; programa prueba en modo seguro; app hace la app web
ok("recuerdos" in (ast.get_source_segment(src, next(x for x in ast.walk(arb) if isinstance(x, ast.FunctionDef) and x.name == "_investigar_reflexion")) or ""),
   "la reflexión se guarda en el baúl")
ok("_experimentar_pensando" in (ast.get_source_segment(src, next(x for x in ast.walk(arb) if isinstance(x, ast.FunctionDef) and x.name == "_investigar_programa")) or ""),
   "el programa se prueba en modo seguro")
ok("app_web_kira" in (ast.get_source_segment(src, next(x for x in ast.walk(arb) if isinstance(x, ast.FunctionDef) and x.name == "_investigar_app")) or ""),
   "la app usa app_web_kira")
# voz enrutada y el bucle prioriza los encargos del dueño
ok("investigar_kira" in src and "es_orden(command)" in src, "la voz enruta «investiga/pregúntate»")
ok("_iv.pendiente(self.dir)" in src and "self.investigar(encargo)" in src, "el bucle hace tus encargos primero")

print(f"\nTODO BIEN {n}")
