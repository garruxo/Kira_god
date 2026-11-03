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
ok(len(pk.generar_preguntas("una pila")) == 10, "10 preguntas")
ok(pk.es_programable("un grafo") and not pk.es_programable("la amistad"), "detecta lo programable")
ok(pk.clasificar_respuesta("No lo sé")[1] is True, "duda")

# --- un pensamiento con todo de mentira, y que se guarde en disco ---
def preguntar(p):
    return "Un grafo son nodos unidos por aristas; sirve para mapas y redes."


def experimentar(preg, sem):
    return {"ok": True, "resultado": "nodos=3 aristas=2", "codigo": "g={}"}


def comparar(preg, sem, codigo):
    return {"fuente": "GitHub", "resumen": "el de fuera usa una cola; el mío una lista. Podría optimizar."}


est = pk.cargar(ruta)
nota = pk.pensar_una(est, preguntar, experimentar=experimentar, comparar=comparar, semillas=["un grafo"])
pk.guardar(est, ruta)
ok(nota and nota["tipo"] == "experimento", "tema de código -> experimenta")
ok(nota.get("comparacion", {}).get("fuente") == "GitHub", "comparó su código con uno de fuera")
ok("comparé con GitHub" in pk.texto_cuaderno(est), "el cuaderno muestra la comparación")
est2 = pk.cargar(ruta)
ok(est2["notas"] and est2["notas"][0]["pregunta"] == nota["pregunta"], "se guardó y se relee del disco")
ok("Cuaderno de Kira" in pk.texto_cuaderno(est2), "cuaderno legible")

# --- ciclo de mejora: varias rondas, se queda con la mejor y guarda el recorrido ---
veces = {"n": 0}


def exp_ciclo(pedido, sem):
    veces["n"] += 1
    return {"ok": veces["n"] >= 2, "resultado": f"intento {veces['n']}", "codigo": "x=1"}


estc = pk._vacio()
nc = pk.ciclo(estc, "una pila", preguntar, estudiar=lambda q: "info de pilas",
              experimentar=exp_ciclo, comparar=comparar, rondas=3)
ok(nc["tipo"] == "ciclo" and len(nc["historial"]) >= 2, "ciclo con varias rondas")
ok(any(h["ok"] for h in nc["historial"]) and nc.get("experimento"), "se quedó con la versión que funcionó")
ok("ciclo de mejora" in pk.texto_cuaderno(estc) and "ronda 1" in pk.texto_cuaderno(estc), "cuaderno muestra el ciclo")

# --- si el cerebro falla, NO se queda mudo: anota el motivo (en pensar_una y en ciclo) ---
def preguntar_roto(p):
    raise RuntimeError("cerebro no listo")


estx = pk._vacio()
nerr = pk.pensar_una(estx, preguntar_roto, semillas=["una función"])
ok(nerr and nerr["fuente"] == "sin cerebro" and "no pude pensar" in nerr["respuesta"], "fallo del cerebro -> nota")
ok(estx["notas"], "la nota de error queda en el cuaderno (no vacío)")
nce = pk.ciclo(pk._vacio(), "una pila", preguntar_roto)
ok(nce["fuente"] == "sin cerebro", "ciclo sin cerebro -> nota clara")

# --- INSISTE: si sigue sin saber, estudia y repiensa varias veces ---
cuenta = {"e": 0}
pk.pensar_una(pk._vacio(), lambda p: "No lo sé", estudiar=lambda q: (cuenta.__setitem__("e", cuenta["e"] + 1), "info")[1],
              insistir=2, semillas=["x"])
ok(cuenta["e"] == 2, "insistir=2 estudia 2 veces si sigue sin saber")
cuenta["e"] = 0
pk.pensar_una(pk._vacio(), lambda p: "No lo sé", estudiar=lambda q: (cuenta.__setitem__("e", cuenta["e"] + 1), "info")[1],
              insistir=1, semillas=["x"])
ok(cuenta["e"] == 1, "por defecto (insistir=1) estudia una vez")

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
