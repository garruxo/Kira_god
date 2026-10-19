# -*- coding: utf-8 -*-
"""Estudio: Kira aprende sola de la Wikipedia (simulada) y de la documentación de Python del móvil."""
import json, os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import recuerdos_kira as rk, estudio_kira as ek, red_kira
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

ARTS = {"Red neuronal artificial": "Las redes neuronales artificiales son un modelo computacional inspirado en las neuronas del cerebro, usado en aprendizaje automático.",
        "Perceptrón": "El perceptrón es la red neuronal más sencilla, inventada por Frank Rosenblatt en 1957 para clasificar patrones.",
        "Neurona": "Ver otros usos.", "Desambig": "x"}
pedidos = []
def wiki(url):
    pedidos.append(url)
    assert url.startswith("https://es.wikipedia.org/")
    if "list=search" in url:
        return {"query": {"search": [{"title": t} for t in ARTS]}}
    titulo = url.rsplit("/", 1)[1].replace("_", " ")
    import urllib.parse; titulo = urllib.parse.unquote(titulo)
    if titulo == "Desambig":
        return {"type": "disambiguation", "extract": "x" * 100}
    return {"type": "standard", "extract": ARTS[titulo] + " <b>negrita</b>"}

B = rk.Recuerdos(os.path.join(T, "baul"))
E = ek.Estudiante(B, os.path.join(T, "estudio.json"), pedir=wiki)

# ---------- Wikipedia ----------
t = E.estudiar("redes neuronales")
ok(t == ["Red neuronal artificial", "Perceptrón"], "guarda los artículos útiles (no textos cortos ni desambiguaciones)")
r = B.respuesta_directa("qué es el perceptrón")
ok(r and "Rosenblatt" in r["texto"] and r["fuente"].startswith("https://es.wikipedia.org/wiki/"), "lo responde desde el baúl con su fuente")
ok("<b>" not in r["texto"], "sin etiquetas HTML")
ok(E.estudiar("redes neuronales") == [], "no guarda dos veces lo mismo")
ok("ignora" not in B.contexto("perceptrón") and B.contexto("perceptrón") == "", "lo de internet no va al contexto de la IA")
try:
    E.estudiar(" "); ok(False, "tema vacío")
except ValueError:
    ok(True, "tema vacío")
try:
    ek._pedir_wikipedia("https://malo.example.com/x"); ok(False, "dominio")
except ValueError:
    ok(True, "solo la Wikipedia en español")

# ---------- documentación de Python ----------
k = E.estudiar_python("json")
ok(k >= 3, "fichas de json")
f = B.respuesta_directa("qué hace json.loads")
ok(f and f["texto"].startswith("json.loads(") and f["fuente"] == "documentación de Python", "explica json.loads sin internet")
ok(f["puntuacion"] >= 0.9, "la pregunta encaja bien")
ok(E.estudiar_python("json") == 0, "no duplica")
try:
    E.estudiar_python("subprocess"); ok(False, "módulo peligroso")
except ValueError:
    ok(True, "solo módulos de la lista segura")
ok(E.estudiar_python("os.path") > 0, "os.path (funciones de posixpath)")
ok(B.respuesta_directa("qué hace os.path.join") is not None, "encuentra os.path.join")

# ---------- plan ----------
tema, _ = E.paso()
ok(tema == ek.PLAN[0] and E.indice == 1, "el plan avanza")
E2 = ek.Estudiante(B, os.path.join(T, "estudio.json"), pedir=wiki)
ok(E2.indice == 1 and E2.aprendidos == E.aprendidos, "el progreso se guarda")
ok("✓ Programación" in E.texto_plan() and "→ Python" in E.texto_plan(), "plan legible")
ok("Plan: 1 de" in E.estado_texto(), "estado")

# aprender sola: hilo en segundo plano
E.poner_sola(True, intervalo=0.05)
fin = time.time() + 3
while E.indice < 4 and time.time() < fin:
    time.sleep(0.05)
ok(E.indice >= 4, "estudia sola en segundo plano")
E.poner_sola(False)
time.sleep(0.2); i = E.indice; time.sleep(0.3)
ok(E.indice == i and not ek.Estudiante(B, os.path.join(T, "estudio.json")).sola, "deja de estudiar y lo recuerda")
def caido(url):
    raise OSError("sin internet")
E3 = ek.Estudiante(B, os.path.join(T, "e3.json"), pedir=caido)
E3.poner_sola(True, intervalo=0.05); time.sleep(0.3); E3.poner_sola(False)
ok("sin internet" in E3.ultimo_error, "sin internet no se cae, apunta el problema")

# ---------- https en Android ----------
ok(red_kira.contexto_ssl().verify_mode.name == "CERT_REQUIRED", "https verifica siempre los certificados")

# ---------- núcleo ----------
import kira_god
core = kira_god.KiraGodCore()
core.estudio._pedir = wiki
ok("Perceptrón" in core.procesar_orden("estudia: redes neuronales"), "orden estudia:")
ok("ficha" in core.procesar_orden("estudia python: math"), "orden estudia python:")
ok("lista de módulos seguros" in core.procesar_orden("estudia python: ctypes"), "rechaza módulos peligrosos")
ok("Plan de estudio" in core.procesar_orden("plan de estudio"), "plan de estudio")
ok("Estudio:" in core.procesar_orden("qué has aprendido"), "qué has aprendido")
core.estudio.paso = lambda: ("x", [])
ok("estudiar sola" in core.procesar_orden("aprende sola"), "aprende sola")
ok("Dejo de estudiar" in core.procesar_orden("deja de aprender"), "deja de aprender")
core.estudio._pedir = caido
ok("No pude conectar" in core.procesar_orden("estudia: algo"), "sin internet: mensaje claro")
print("ESTUDIO OK", n)
