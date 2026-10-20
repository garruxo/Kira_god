# -*- coding: utf-8 -*-
"""v2.25: Kira INVENTA código experimental: plan de hipótesis, cada una escrita y probada en modo seguro (con
corrección si falla), puntuación, cuaderno, lección en el baúl, acuerdo con Claude y por voz al editor
(cerebro FALSO)."""
import os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import experimentos_kira as ex, saber_avanzado_kira as sa
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- frases ----------
for frase, tema in (("experimenta con colores y música", "colores y música"),
                    ("Kira, inventa un algoritmo nuevo para repartir árboles en un mapa", "repartir árboles en un mapa"),
                    ("hazme un código experimental de física", "física"),
                    ("inventa un juego nuevo de gravedad", "un juego de gravedad"),
                    ("haz un experimento con fractales", "fractales")):
    ok(ex.pedido_experimento(frase) == tema, f"«{frase}» -> {ex.pedido_experimento(frase)!r}")
for frase in ("escríbeme un programa que sume", "inventa algo", "hazme un juego de naves", "qué es un experimento"):
    ok(ex.pedido_experimento(frase) is None, f"«{frase}» no es un experimento")
import programar_kira as pk
ok(pk.pedido_programa("hazme un código experimental de física") is not None,
   "(la frase también parece un programa: por eso el experimento se mira ANTES)")

# ---------- plan y puntos ----------
pl = ex.plan("repartir árboles en un mapa")
ok([h["enfoque"] for h in pl] == ["mezcla", "otro_campo", "variante"] and pl[0]["recetas"][0]["id"] == "poisson_disco",
   "tres hipótesis con las técnicas que vienen al caso")
ok(len(ex.plan("algo rarísimo zzzqqq")) == 3 and not ex.plan("algo rarísimo zzzqqq")[0]["recetas"], "sin técnica: desde cero")
txt = ex.pedido_de("repartir árboles", pl[0])
ok("Hipótesis" in txt and "Poisson" in txt and "class " not in txt, "al cerebro le van las IDEAS, no el código (para que no copie)")
poisson = next(r for r in sa.RECETAS if r["id"] == "poisson_disco")
p_copia, notas_c = ex.puntuar(True, {"salida": "x 1"}, poisson["codigo"], [poisson])
p_nuevo, notas_n = ex.puntuar(True, {"salida": "Resultado 3\nConclusión: sí"}, "# Hipótesis: algo\nprint(3)\n", [poisson])
ok(p_nuevo > p_copia and any("demasiado" in x for x in notas_c) and "es original" in notas_n, "premia lo original y castiga copiar")
ok(ex.puntuar(False, {}, "", [])[0] == 0, "lo que no funciona, 0")

# ---------- el núcleo con un cerebro falso ----------
import cerebro_ia_kira as ci, kira_god
core = kira_god.KiraGodCore()
PROG_MAL = "# Hipótesis: dividir\nprint(1 / 0)\n"
PROG_A = ("# Hipótesis: con distancia mínima los árboles se reparten mejor\nimport random\nazar = random.Random(1)\n"
          "pts = [(azar.random(), azar.random()) for _ in range(30)]\nprint('Puntos:', len(pts))\n"
          "print('Conclusión: reparto más uniforme')\n")
PROG_B = "# Hipótesis: rejilla\nprint('celdas', 9)\n"
respuestas = [PROG_MAL, PROG_A, PROG_B, PROG_B]
pedidos = []
def api(clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None):
    pedidos.append((system, usuario))
    return f"NOMBRE: exp\n```python\n{respuestas.pop(0) if respuestas else PROG_B}```"
core._leer_clave = lambda *a: ci.LOCAL
core._llamar_api = api
core.reparto = lambda tarea: ("local", None)
pasos = []
r = core.experimentar("repartir árboles en un mapa", al_progreso=lambda f, t: pasos.append(t))
ok(r["ok"] and r["codigo"] == PROG_A, "se queda con la mejor hipótesis")
ok(len(r["resultados"]) == 2, "con el cerebro del móvil prueba 2 hipótesis (es más lento)")
ok("división" in pedidos[1][1].lower() or "ZeroDivision" in pedidos[1][1], "si falla, corrige con el error")
ok("★" in r["texto"] and "Conclusión: reparto más uniforme" in r["texto"], "informe con la mejor marcada y su conclusión")
ok(any("Hipótesis 1 de 2" in p for p in pasos) and pasos[-1] == "Experimento terminado.", "va contando por dónde va")
ok("Es un EXPERIMENTO" in pedidos[0][1] and "class UnionFind" not in pedidos[0][1], "le pide inventar, sin darle recetas a copiar")
# cuaderno y lección
ok(r["n"] == 1 and "1. repartir árboles" in core.procesar_orden("mis experimentos"), "lo apunta en el cuaderno")
ok(core.procesar_orden("abre el experimento 1").startswith("[OK] ABRIR_EN_EDITOR") and core.lector.ultimo == PROG_A,
   "«abre el experimento 1»")
ok(core.procesar_orden("abre el experimento 1 hipótesis 2").startswith("[OK]") and core.lector.ultimo == PROG_B,
   "y una hipótesis concreta")
ok(core.procesar_orden("abre el experimento 7").startswith("[x]"), "uno que no existe")
lec = core.recuerdos.buscar("experimento repartir árboles", n=3)
ok(any(x["fuente"] == ex.FUENTE_LECCION and "funcionó" in x["texto"] for x in lec), "la lección queda en el baúl")
respuestas[:] = [PROG_A]
pedidos.clear()
core.experimentar("repartir árboles en un mapa")
ok("experimento" in pedidos[0][1].lower() and "funcionó" in pedidos[0][1], "el siguiente experimento parte de lo aprendido")
ok(ex.Cuaderno(os.path.join(core.dir, "experimentos.json")).buscar(2) is not None, "el cuaderno se guarda en disco")
# sin cerebro
core.reparto = lambda tarea: (None, None)
try:
    core.experimentar("x y z"); ok(False, "sin cerebro debe avisar")
except RuntimeError as e:
    ok("cerebro" in str(e).lower() or "clave" in str(e).lower(), "sin cerebro, lo dice: " + str(e))

# en equipo con Claude
core.reparto = lambda tarea: ("local", "claude")
revisiones = []
def revisar(quien, pedido, de, codigo, informe, tipo="mejora", objecion=""):
    revisiones.append((quien, pedido))
    return {"acuerdo": True, "motivos": "Original y medible.", "codigo": None, "nombre": None}
core.revisar_codigo = revisar
respuestas[:] = [PROG_A, PROG_B]
r = core.experimentar("repartir árboles en un mapa")
ok(r["acuerdo"] is True and revisiones and revisiones[0][0] == "claude" and "ORIGINAL" in revisiones[0][1],
   "Claude revisa la mejor y están de acuerdo")
ok(len(r["resultados"]) == 2 and "ACUERDO entre Kira y Claude" in r["texto"], "y se cuenta")

# ---------- por voz (Kivy simulado) ----------
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
import inicio_kira as ik
class VozMuda:
    def __init__(s): s.dichos = []
    def puede_hablar(s): return True
    def puede_escuchar(s): return False
    def hablando(s): return False
    def hablar(s, t): s.dichos.append(t); return True
    def iniciar_escucha(s, idioma="es-ES"): return False, "no"
    def sondear(s): return "error", "no"
    def parar_escucha(s): pass
VOZ = VozMuda(); ik.Voz = lambda *a, **k: VOZ
core2 = kira_god.KiraGodCore()
core2._leer_clave = lambda *a: ci.LOCAL
core2._llamar_api = api
core2.reparto = lambda tarea: ("local", None)
core2.cerebro_para_codigo = lambda: "local"
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core2)
def correr(seg=3.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.3)
        if cond and cond(): return True
        time.sleep(0.01)
    return bool(cond and cond())
def textos(nombre): return [w.text for w in sm.get_screen(nombre).walk() if hasattr(w, "text") and isinstance(w.text, str)]
def decir_a_kira(frase):
    sm.ir("inicio"); correr(0.3)
    campo = next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "TextInput")
    campo.text = frase
    next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
correr(0.8)
respuestas[:] = [PROG_A, PROG_B]
decir_a_kira("Kira, hazme un código experimental para repartir árboles en un mapa")
ok(correr(8, lambda: sm.current == "editor_codigo"), "lo deja en el editor: " + sm.current)
ok(PROG_A.strip() in "\n".join(textos("editor_codigo")), "con el mejor experimento")
ok(any("EXPERIMENTAL" in t and "implementa este código" in t for t in textos("editor_codigo")), "explica qué es y cómo instalarlo")
ok(any("ideas funcionan" in d for d in VOZ.dichos), "lo dice")
decir_a_kira("abre el experimento 1 hipótesis 2")
ok(correr(3, lambda: sm.current == "editor_codigo" and any("print('celdas', 9)" in t for t in textos("editor_codigo"))),
   "«abre el experimento N» por voz")
print("EXPERIMENTOS OK", n)
