# -*- coding: utf-8 -*-
"""v2.65: núcleo compartido de la curiosidad (pensador_kira de la RAÍZ, el que va en el APK). Prueba la lógica pura
y un pensamiento entero con cerebro/estudio/experimento de mentira. Además, GUARDA que la copia de la raíz y la del
portátil no se desvíen (mismas preguntas, misma clasificación)."""
import importlib.util
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)                      # importa el pensador de la RAÍZ (el del móvil)
os.environ.setdefault("HOME", tempfile.mkdtemp())

import pensador_kira as pk

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


ruta = os.path.join(tempfile.mkdtemp(), "pensamientos.json")

# --- pura ---
ok(len(pk.generar_preguntas("una pila")) == 5, "5 preguntas")
ok(pk.es_programable("un grafo") and not pk.es_programable("la amistad"), "detecta lo programable")
ok(pk.clasificar_respuesta("No lo sé")[1] is True, "duda")

# --- un pensamiento con todo de mentira, y que se guarde en disco ---
def preguntar(p):
    return "Un grafo son nodos unidos por aristas; sirve para mapas y redes."


def experimentar(preg, sem):
    return {"ok": True, "resultado": "nodos=3 aristas=2", "codigo": "g={}"}


est = pk.cargar(ruta)
nota = pk.pensar_una(est, preguntar, experimentar=experimentar, semillas=["un grafo"])
pk.guardar(est, ruta)
ok(nota and nota["tipo"] == "experimento", "tema de código -> experimenta")
est2 = pk.cargar(ruta)
ok(est2["notas"] and est2["notas"][0]["pregunta"] == nota["pregunta"], "se guardó y se relee del disco")
ok("Cuaderno de Kira" in pk.texto_cuaderno(est2), "cuaderno legible")

# --- GUARDA anti-divergencia: la copia del portátil debe dar lo mismo en lo puro ---
lap_path = os.path.join(RAIZ, "kira_portatil", "pensador_kira.py")
spec = importlib.util.spec_from_file_location("pensador_lap", lap_path)
lap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lap)
for s in ("una pila", "un grafo", "el phishing", "la amistad"):
    ok(pk.generar_preguntas(s) == lap.generar_preguntas(s), f"mismas preguntas para «{s}»")
    ok(pk.es_programable(s) == lap.es_programable(s), f"mismo es_programable para «{s}»")
for r in ("No lo sé", "Creo que sí", "Funciona porque la CPU lee instrucciones una tras otra sin parar nunca."):
    ok(pk.clasificar_respuesta(r) == lap.clasificar_respuesta(r), "misma clasificación raíz/portátil")
ok(pk.SEMILLAS == lap.SEMILLAS and pk._TIPOS_PREGUNTA == lap._TIPOS_PREGUNTA, "mismas semillas y tipos")

print(f"\nTODO BIEN {n}")
