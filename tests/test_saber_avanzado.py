# -*- coding: utf-8 -*-
"""v2.25: programación avanzada y DISEÑO. Cada receta pasa el laboratorio del móvil, el del PC y el editor seguro con
sus pruebas; las fichas van al baúl sin internet y Kira las responde sola; recetas, curso y órdenes."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import saber_avanzado_kira as sa, recetas_ingenieria_kira as ri, ejecutor_kira as ej, mejoras_ia_kira as mi
import saber_mejoras_kira as sm_, curso_avanzado_kira as ca, laboratorio_movil_kira as lm
import recuerdos_kira as rk, estudio_kira as ek
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- las recetas ----------
ok(len(sa.RECETAS) >= 18 and len(sa.CONCEPTOS) >= 24, "18 recetas y 24 fichas como mínimo")
ids = [r["id"] for r in sa.RECETAS]
otros = {r["id"] for r in ri.RECETAS} | {r["id"] for r in sm_.RECETAS if r not in sa.RECETAS}
ok(len(ids) == len(set(ids)) and not set(ids) & otros, "sin repetir ni pisar otras recetas")
ok(sum(1 for r in sa.RECETAS if r["area"].startswith("Diseño")) >= 10, "10 o más de diseño")
ok(sum(1 for r in sa.RECETAS if r["area"] == "Programación avanzada") >= 8, "8 o más de programación avanzada")
LAB_MOVIL = lm.LaboratorioMovil()
try:
    sys.path.insert(0, os.path.join(RAIZ, "kira_laboratorio"))
    import servidor_lab
except ImportError:
    servidor_lab = None
for r in sa.RECETAS:
    ok(all(r.get(k) for k in ("id", "titulo", "area", "temas", "idea", "complejidad", "codigo", "prueba")),
       f"{r['id']}: ficha completa")
    ok(mi.precomprobar(r["codigo"]) is None, f"{r['id']}: pasa la revisión previa")
    demo = sa.demo(r)
    ok(ej.revisar(demo) is None, f"{r['id']}: vale para el editor seguro: {ej.revisar(demo)}")
    s = ej.ejecutar(demo, limite=10)
    ok(s["ok"], f"{r['id']}: se ejecuta en el editor: {s['error']}")
    for orden, arg, espera in r["prueba"]:
        ok(espera in s["salida"], f"{r['id']}: «{orden} {arg}» da «{espera}»")
    v = LAB_MOVIL.probar(r["id"], r["codigo"])
    ok(v["ok"], f"{r['id']}: el laboratorio del móvil la aprueba: {[e for e in v['etapas'] if not e['ok']]}")
    if servidor_lab is not None:
        v = servidor_lab.probar(r["id"], r["codigo"])
        ok(v["ok"] and v["avisos"] == [], f"{r['id']}: el del PC también, sin avisos")

# ---------- fichas y estudio ----------
cids = [c["id"] for c in sa.CONCEPTOS]
ok(len(cids) == len(set(cids)) and not set(cids) & {c["id"] for c in ri.CONCEPTOS}, "conceptos sin repetir")
for c in sa.CONCEPTOS:
    ok(all(c.get(k) for k in ("id", "area", "titulo", "temas", "texto")) and len(c["texto"]) > 250, f"concepto {c['id']}")
ok(len(sa.fichas("diseño")) + len(sa.fichas("programación")) + len(sa.fichas("redes")) == len(sa.fichas())
   == len(sa.RECETAS) + len(sa.CONCEPTOS), "las fichas se reparten entre diseño, programación y redes neuronales")
ok(sum(1 for r in sa.RECETAS if r["area"] == "Redes neuronales") >= 7 and len(sa.fichas("redes")) >= 18,
   "v2.27: redes neuronales (7 recetas que entrenan de verdad y sus fichas)")
B = rk.Recuerdos(os.path.join(T, "baul"))
def sin_red(url):
    raise AssertionError("no debe usar internet")
E = ek.Estudiante(B, os.path.join(T, "estudio.json"), pedir=sin_red)
ok(E.avanzado_pendiente(), "al principio falta")
nd, td = E.estudiar_avanzado("diseño")
ok(nd == td == len(sa.fichas("diseño")), "estudia diseño")
ok(E.avanzado_pendiente(), "aún falta la programación avanzada")
nt, tt = E.estudiar_avanzado()
ok(nt == len(sa.fichas("programación")) + len(sa.fichas("redes")) and tt == len(sa.fichas()) and not E.avanzado_pendiente(), "y luego todo, sin duplicar")
preguntas = {"qué es la regla de los tercios": "tercios", "qué es la ley de fitts": "Fitts", "qué es un ecs": "ECS",
             "qué es una función pura": "funcional", "cómo pedirle una imagen al pintor": "pintor",
             "qué es el contraste wcag": "WCAG", "qué es el colapso de función de onda": "WFC",
             "principios de animación": "animación", "qué es la gestalt": "Gestalt"}
for q, esperado in preguntas.items():
    r = B.respuesta_directa(q)
    ok(r is not None and esperado.lower() in r["tema"].lower() and r["fuente"] == ek.FUENTE_AVANZADO,
       f"responde sola «{q}» ({r and r['tema']})")
ok("Programación avanzada y diseño: " in E.estado_texto(), "el estado del estudio lo cuenta")

# ---------- recetas, curso y órdenes ----------
ok(all(r in sm_.RECETAS for r in sa.RECETAS), "el saber de mejoras las usa")
ok(sm_.buscar("quiero una paleta de colores para mi web")[0][1]["id"] in ("paleta_armonica", "colores"), "las encuentra")
ok(sm_.buscar("repartir árboles al azar sin que se amontonen")[0][1]["id"] == "poisson_disco", "las encuentra (2)")
ok("Programación dinámica" not in sm_.lista("programación avanzada") and "ecs" in sm_.lista("programación avanzada"),
   "«recetas de programación avanzada» es solo esa área")
ok("paleta armonica" in sm_.lista("diseño") and "dijkstra" not in sm_.lista("diseño"), "«recetas de diseño»")
ok("paleta armonica" not in sm_.lista("ingeniería") and "dijkstra" in sm_.lista("ingeniería"), "«recetas de ingeniería» igual que antes")
ok(len(ca.CURSO_DISENO) == len(sa.RECETAS) and all(l in ca.todas() for l in ca.CURSO_DISENO), "lecciones en el curso")
import kira_god
core = kira_god.KiraGodCore()
ok("ficha(s) nuevas" in core.procesar_orden("estudia diseño"), "«estudia diseño»")
ok("programación avanzada" in core.procesar_orden("estudia programación avanzada"), "«estudia programación avanzada»")
ok("0 ficha(s) nuevas" in core.procesar_orden("estudia diseño gráfico"), "«estudia diseño gráfico» no duplica")
ok("rejilla" in core.procesar_orden("recetas de diseño"), "«recetas de diseño»")
ok("ficha(s) nuevas" in core.procesar_orden("estudia redes neuronales") and "autograd" in
   core.procesar_orden("recetas de redes neuronales"), "«estudia redes neuronales» y «recetas de redes neuronales»")
for q, esperado in (("qué es la retropropagación", "Retropropagación"), ("cómo funciona un transformer", "Transformers"),
                    ("cómo pinta el pintor", "difusión"), ("qué es una lstm", "LSTM")):
    r = core.recuerdos.respuesta_directa(q)
    ok(r is not None and esperado.lower() in r["tema"].lower(), f"responde sola «{q}» ({r and r['tema']})")
for pedido, receta in (("una red neuronal que reconozca imágenes", "convolucional"), ("una red que escriba texto", "recurrente"),
                       ("un agente que aprenda a jugar solo", "q_learning"), ("un sistema experto con reglas lógicas", "mini_prolog")):
    ok(sm_.buscar(pedido, 1)[0][1]["id"] == receta, f"al programar «{pedido}», usa la receta {receta}")
ok(core.procesar_orden("abre la receta wfc").startswith("[OK] ABRIR_EN_EDITOR"), "«abre la receta wfc»")
print("SABER AVANZADO OK", n)
