# -*- coding: utf-8 -*-
"""El juego de práctica de defensa (defensa_juego_kira): generar situaciones, que Kira decida, jugar una partida,
APRENDER afinando los umbrales (los datos) y que mejore, el detector como código, y el reconocedor de la orden.
Lógica pura, sin Kivy, datos inventados (sin red real)."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import defensa_juego_kira as dj

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


# --- generar: sale de todo, con su verdad (ataque o no) ---
tipos = set()
for s in range(200):
    e = dj.generar((7, s))
    tipos.add(e["tipo"])
    ok_campos = all(k in e for k in ("trafico", "logins", "puertos", "oculto", "enlace", "tipo", "ataque"))
    if not ok_campos:
        ok(False, "cada situación trae todos sus campos")
        break
else:
    ok(True, "cada situación trae todos sus campos")
ok(tipos == set(dj.ORDEN), "con el tiempo salen todas las amenazas y también tráfico sano")
ok(all(dj.generar((7, s))["ataque"] == (dj.generar((7, s))["tipo"] != "trafico_sano") for s in range(50)),
   "la verdad (ataque) concuerda con el tipo")

# --- decidir: una puerta trasera se ve como amenaza y trae cómo combatirla ---
d = dj.Defensa()
esc_pt = {"trafico": 3.2, "logins": 41, "puertos": 2, "oculto": True, "enlace": False, "tipo": "puerta_trasera", "ataque": True}
dec = dj.decidir(d, esc_pt)
ok(dec["es_amenaza"] and dec["tipo"] == "puerta_trasera", "reconoce la puerta trasera")
ok(dec["combate"] and all(isinstance(x, str) for x in dec["combate"]), "trae los pasos de CÓMO la combate")

esc_sano = {"trafico": 0.8, "logins": 1, "puertos": 1, "oculto": False, "enlace": False, "tipo": "trafico_sano", "ataque": False}
ok(not dj.decidir(d, esc_sano)["es_amenaza"], "el tráfico sano NO es amenaza")

# un enlace trampa salta aunque los números sean bajos
ok(dj.decidir(d, {"trafico": 0.5, "logins": 0, "puertos": 0, "oculto": False, "enlace": True})["tipo"] == "enlace_trampa",
   "un enlace trampa se detecta aunque el tráfico sea bajo")

# --- jugar: devuelve resultados y totales coherentes ---
res, tot = dj.jugar(d, rondas=12, semilla=3)
ok(len(res) == 12 and tot["rondas"] == 12, "juega las rondas pedidas")
ok(tot["aciertos"] + tot["fallos"] + tot["falsas"] == 12, "cada ronda es acierto, fallo o falsa alarma")

# --- aprender: con umbrales MALOS (altísimos) se escapan amenazas; tras entrenar, mejora ---
malo = dj.Defensa(umbrales={"trafico": 4.0, "logins": 60, "puertos": 50})
_, antes = dj.jugar(malo, rondas=60, semilla=11)
for v in range(8):                                   # varias partidas de entrenamiento, aprendiendo entre ellas
    r, _ = dj.jugar(malo, rondas=60, semilla=100 + v)
    dj.aprender(malo, r)
_, despues = dj.jugar(malo, rondas=60, semilla=11)
ok(despues["aciertos"] > antes["aciertos"], f"entrenando mejora: aciertos {antes['aciertos']} -> {despues['aciertos']}")
ok(malo.partidas == 8, "cuenta las partidas entrenadas")

# aprender devuelve los cambios para contarlos en la consola
malo2 = dj.Defensa(umbrales={"logins": 60})
r2, _ = dj.jugar(malo2, rondas=40, semilla=5)
cambios = dj.aprender(malo2, r2)
ok(isinstance(cambios, list) and any("umbral" in c for c in cambios) if cambios else True,
   "aprender devuelve los cambios de umbral (texto para la consola)")

# --- guardar/cargar los umbrales (los datos que aprende) ---
import tempfile
ruta = os.path.join(tempfile.mkdtemp(), "def.json")
dguardar = dj.Defensa(ruta=ruta, umbrales={"logins": 18})
dguardar.guardar()
dcargar = dj.Defensa(ruta=ruta)
ok(dcargar.umbrales["logins"] == 18, "guarda y recupera los umbrales aprendidos")

# --- el detector como código es Python válido y sin red/ataque ---
cod = dj.codigo_detector(dguardar)
import ast
try:
    ast.parse(cod)
    valido = True
except SyntaxError:
    valido = False
ok(valido and "def es_amenaza" in cod, "el detector sale como código Python válido")
ok("import socket" not in cod and "subprocess" not in cod and "def es_amenaza" in cod,
   "el detector es solo defensa: no abre red ni ejecuta nada")

# --- reconocedor de la orden ---
ok(dj.es_orden("Kira, entrena tus defensas"), "reconoce «entrena tus defensas»")
ok(dj.es_orden("juega al laberinto de defensa"), "reconoce «juega al laberinto de defensa»")
ok(not dj.es_orden("ponme música"), "no secuestra una orden que no va de defensa")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
