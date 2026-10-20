# -*- coding: utf-8 -*-
"""Ingeniería informática: cada receta pasa el laboratorio de verdad y se ejecuta en el editor seguro con sus pruebas;
las fichas de teoría van al baúl sin internet y Kira las responde sola; la terminal tiene el nivel «Ingeniería»."""
import os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import recetas_ingenieria_kira as ri, ejecutor_kira as ej, mejoras_ia_kira as mi, curso_avanzado_kira as ca
import recuerdos_kira as rk, estudio_kira as ek, saber_mejoras_kira as sm_
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- las recetas ----------
ok(len(ri.RECETAS) >= 50 and len(ri.CONCEPTOS) >= 40, "50 recetas y 40 fichas de teoría como mínimo")
ids = [r["id"] for r in ri.RECETAS]
ok(len(ids) == len(set(ids)), "recetas sin repetir")
ok(not set(ids) & {r["id"] for r in sm_.RECETAS if not r.get("area")}, "no pisan las recetas de gráficos")
ok(len(ri.areas()) >= 10, "repartidas en 10 áreas o más")
for r in ri.RECETAS:
    ok(all(r.get(k) for k in ("id", "titulo", "area", "temas", "idea", "complejidad", "codigo", "prueba")),
       f"{r['id']}: ficha completa")
    ok(mi.precomprobar(r["codigo"]) is None, f"{r['id']}: pasa la revisión previa del móvil")
    demo = ri.demo(r)
    ok(ej.revisar(demo) is None, f"{r['id']}: vale para el editor seguro: {ej.revisar(demo)}")
    s = ej.ejecutar(demo, limite=10)
    ok(s["ok"], f"{r['id']}: se ejecuta en el editor: {s['error']}")
    for orden, arg, espera in r["prueba"]:
        ok(espera in s["salida"], f"{r['id']}: «{orden} {arg}» da «{espera}» también en el editor")

# ---------- el laboratorio de verdad (carga aislada + tests fijos) ----------
LAB = os.path.join(RAIZ, "kira_laboratorio")
try:
    sys.path.insert(0, LAB)
    import servidor_lab
except ImportError:
    servidor_lab = None
if servidor_lab is not None:
    for r in ri.RECETAS:
        v = servidor_lab.probar(r["id"], r["codigo"])
        ok(v["ok"], f"{r['id']}: el laboratorio la aprueba: {[e for e in v['etapas'] if not e['ok']]}")
        ok(v["avisos"] == [], f"{r['id']}: sin avisos de código sensible: {v['avisos']}")

# ---------- conceptos y fichas ----------
cids = [c["id"] for c in ri.CONCEPTOS]
ok(len(cids) == len(set(cids)), "conceptos sin repetir")
for c in ri.CONCEPTOS:
    ok(all(c.get(k) for k in ("id", "area", "titulo", "temas", "texto")) and len(c["texto"]) > 250,
       f"concepto {c['id']} completo")
f = ri.fichas()
ok(len(f) == len(ri.RECETAS) + len(ri.CONCEPTOS) and all(len(t) <= 2000 for _, t in f), "una ficha por receta y concepto")

# ---------- estudiar ingeniería: al baúl, sin internet ----------
B = rk.Recuerdos(os.path.join(T, "baul_test"))
def sin_red(url):
    raise AssertionError("estudiar ingeniería no debe usar internet")
E = ek.Estudiante(B, os.path.join(T, "estudio_test.json"), pedir=sin_red)
ok(E.ingenieria_pendiente(), "al principio falta por estudiar")
nuevas, total = E.estudiar_ingenieria()
ok(nuevas == total == len(f), "guarda todas las fichas")
ok(E.estudiar_ingenieria()[0] == 0 and not E.ingenieria_pendiente(), "no duplica y lo recuerda")
ok(ek.Estudiante(B, os.path.join(T, "estudio_test.json")).ingenieria == total, "el progreso se guarda en disco")
preguntas = {"qué es el teorema CAP": "CAP", "cómo funciona dijkstra": "Dijkstra", "qué es un árbol B": "Árbol B",
             "qué es la notación O grande": "Notación O", "qué es un interbloqueo": "interbloqueo",
             "qué es la cuantización de un modelo": "cuantización", "para qué sirve git rebase": "Git",
             "qué es el algoritmo del banquero": "banquero", "qué es un filtro de bloom": "Bloom"}
for q, esperado in preguntas.items():
    r = B.respuesta_directa(q)
    ok(r is not None and esperado.lower() in r["tema"].lower() and r["fuente"] == ek.FUENTE_INGENIERIA,
       f"responde sola «{q}» ({r and r['tema']})")
ok(B.respuesta_directa("qué es la tortilla de patatas") is None, "lo que no sabe, no se lo inventa")
ok("SOLID" in B.contexto("principios solid de diseño"), "y se lo pasa al cerebro como contexto (no es de internet)")

# ---------- núcleo: órdenes ----------
import kira_god
core = kira_god.KiraGodCore()
core.estudio._pedir = sin_red
r = core.procesar_orden("estudia ingeniería")
ok("[OK]" in r and "ficha" in r and core.estudio.ingenieria == total, f"«estudia ingeniería»: {r[:80]}")
ok("0 ficha(s) nuevas" in core.procesar_orden("estudia: algoritmos"), "«estudia: algoritmos» es lo mismo y no duplica")
ok("Ingeniería informática:" in core.procesar_orden("qué has aprendido"), "el estado del estudio lo cuenta")
pedidas = []
core.estudio._pedir = lambda url: (pedidas.append(url), {"query": {"search": []}})[1]
core.procesar_orden("estudia: redes neuronales")
ok(pedidas and "wikipedia" in pedidas[0], "«estudia: otra cosa» sigue yendo a la Wikipedia")
r = core.procesar_orden("recetas de ingeniería")
ok("Grafos:" in r and "Dijkstra" in r and "Sistema de partículas" not in r, "«recetas de ingeniería» por áreas")
r = core.procesar_orden("recetas de grafos")
ok("Kruskal" in r and "KMP" not in r, "«recetas de grafos» solo las de grafos")
ok("[x]" in core.procesar_orden("recetas de cocina"), "un área que no existe")
r = core.procesar_orden("receta dijkstra")
ok("Coste:" in r and "def dijkstra" in r, "«receta dijkstra» con su coste y su código")
ok("ordenes = registrar()" in core.lector.ultimo, "lista para «abre lo leído en el editor», con sus pruebas")

# aprender sola: lo primero, su saber propio (sin internet)
B2 = rk.Recuerdos(os.path.join(T, "baul2"))
E2 = ek.Estudiante(B2, os.path.join(T, "e2.json"), pedir=lambda url: {"query": {"search": []}})
E2.poner_sola(True, intervalo=30)
fin = time.time() + 20
while E2.ingenieria == 0 and time.time() < fin:
    time.sleep(0.05)
E2.poner_sola(False)
ok(E2.ingenieria == total and B2.respuesta_directa("qué es el teorema CAP") is not None,
   "al «aprender sola» guarda primero su saber de ingeniería")

# ---------- saber de mejoras: búsqueda y contexto ----------
casos = {"la ruta más corta en un mapa con distancias": "dijkstra", "autocompletar palabras mientras escribo": "trie",
         "ordena tareas según sus dependencias": "orden_topologico", "una caché que recuerde lo último usado": "cache_lru",
         "juega al tres en raya contra mí": "minimax_alfabeta", "resuelve un sistema de ecuaciones": "gauss",
         "factoriza números grandes y dime si es primo": "primos_factores", "comprime un texto": "lzw",
         "compara dos versiones de un texto": "diff_lcs", "limita las peticiones a una API": "limitador_peticiones",
         "crea un lenguaje de programación": "kiralang", "mochila con objetos de peso y valor": "mochila",
         "haz una red neuronal que aprenda": "red_neuronal", "agrupa clientes parecidos": "kmeans",
         "detecta errores en datos transmitidos": "deteccion_errores", "asigna tareas a personas": "emparejamiento"}
for pedido, esperado in casos.items():
    hallado = sm_.buscar(pedido, 1)
    ok(hallado and hallado[0][1]["id"] == esperado, f"«{pedido}» -> {esperado} ({hallado and hallado[0][1]['id']})")
c = sm_.contexto_para("crea un lenguaje de programación", local=True)
ok("KiraLang" in c and "Coste:" in c and "```python" not in c, "receta larga: al modelo pequeño le llega solo la idea")
c = sm_.contexto_para("la ruta más corta en un mapa con distancias", local=True)
ok("def dijkstra" in c and "Coste:" in c, "receta corta: le llega el código entero")

# ---------- curso: nivel «Ingeniería» en la terminal y en los ejemplos del editor ----------
ok(len(ca.CURSO_INGENIERIA) == len(ri.RECETAS) and all(l["nivel"] == "ingeniería" for l in ca.CURSO_INGENIERIA),
   "una lección por receta")
ok(ca.buscar("ing_dijkstra") is not None, "se encuentran por id")
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
for _ in range(10):
    Clock.correr(1, 0.1)
def boton(txt, raiz):
    return next(w for w in raiz.walk() if type(w).__name__ == "Button" and w.text == txt)
sm.ir("terminal")
term = sm.get_screen("terminal")
boton("Ingeniería", term).press()
titulo = next(r for r in ri.RECETAS if r["id"] == "dijkstra")["titulo"]
ok(any(type(w).__name__ == "Button" and w.text == titulo for w in term.walk()), "nivel «Ingeniería» en la terminal")
boton(titulo, term).press()
boton("Abrir en el editor", term).press()
area = next(w for w in sm.get_screen("editor_codigo").walk() if type(w).__name__ == "TextInput" and getattr(w, "multiline", False))
ok(sm.current == "editor_codigo" and "def dijkstra" in area.text and "ordenes = registrar()" in area.text,
   "la lección de ingeniería se abre en el editor, lista para ejecutar")
boton("Ejecutar", sm.get_screen("editor_codigo")).press()
salida = [w for w in sm.get_screen("editor_codigo").walk() if type(w).__name__ == "Label"]
fin = time.time() + 10
while time.time() < fin and not any("coste 8" in getattr(w, "text", "") for w in salida):
    Clock.correr(1, 0.05)
    time.sleep(0.02)
ok(any("coste 8" in getattr(w, "text", "") for w in salida), "y al ejecutarla enseña el resultado")
sm.ir("inicio")
campo = next(w for w in sm.walk() if type(w).__name__ == "TextInput" and "Escríbele" in getattr(w, "hint_text", ""))
campo.text = "abre la receta kmp"
boton("Enviar", sm).press()
ok(sm.current == "editor_codigo" and "busca patron" in area.text and "print(" in area.text,
   "«abre la receta kmp» la abre con sus pruebas para ejecutarla")
print("INGENIERÍA OK", n)
