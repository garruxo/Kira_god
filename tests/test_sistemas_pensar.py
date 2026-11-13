# -*- coding: utf-8 -*-
"""v3.27:
- cuando no tiene tareas, sus pensamientos son sobre SUS SISTEMAS, en el orden que pidió el dueño (su entorno, KiraOS,
  Xubuntu, Android/Kivy, Python);
- si estaba pensando sola, RETOMA el pensar justo al acabar tu orden (sin esperar los 5 min); una tarea a la vez;
- lo aprendido puede acabar en app o mejora (de KiraOS o de Kira móvil), por la vía segura;
- «superadministrador» SOLO cuando el dueño lo pida (sola nunca toca el sistema): Kira lo explica, no se da root sola.
"""
import ast
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))

n = fallos = 0


def ok(c, m):
    global n, fallos
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


import kira_god

core = kira_god.KiraGodCore()

# ---------- (A) semillas: sus sistemas primero y en orden ----------
sem = core._semillas_pensar()
ok(sem[:5] == kira_god.SISTEMAS_PROPIOS, "sin tareas, piensa primero en sus sistemas, en el orden pedido: " + str(sem[:5]))
ok(kira_god.SISTEMAS_PROPIOS[0] == "mi entorno" and "KiraOS" in kira_god.SISTEMAS_PROPIOS[1]
   and "Xubuntu" in kira_god.SISTEMAS_PROPIOS[2] and "Python" in kira_god.SISTEMAS_PROPIOS[4],
   "el orden es: entorno → KiraOS → Xubuntu → Android/Kivy → Python")

# ---------- (B) retomar el pensar justo al acabar la orden ----------
core._pensar_on = False
core._ultima_actividad = 12345.0
core._pensaba_al_ordenar = False
core.reanudar_pensar_ya()
ok(core._ultima_actividad == 12345.0, "si NO estaba pensando, reanudar_pensar_ya no hace nada")
# si la propia orden encendió el pensar (p. ej. «estudia X»), NO fuerza el pensar inmediato
core._pensar_on = True
core._pensaba_al_ordenar = False
core.reanudar_pensar_ya()
ok(core._ultima_actividad == 12345.0, "si la orden encendió el pensar, no lo fuerza (deja la vuelta suave)")
# si YA pensaba cuando llegó la orden, retoma enseguida al acabarla
core._pensaba_al_ordenar = True
core.reanudar_pensar_ya()
ok(core._ultima_actividad == 0, "si YA pensaba, retoma el pensar enseguida al acabar tu orden")

src = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
arb = ast.parse(src)
env = next(nd for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef) and nd.name == "procesar_orden")
cuerpo = ast.get_source_segment(src, env) or ""
ok("_procesar_orden" in cuerpo and "reanudar_pensar_ya" in cuerpo,
   "procesar_orden, al acabar tu orden, retoma el pensar (móvil)")

np = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("al_libre" in np and "_al_quedar_libre" in np and "reanudar_pensar_ya" in np,
   "KiraOS: al quedar la cola vacía tras tu orden, retoma el pensar")

# ---------- (C) lo aprendido → mejora/función (programa, no app suelta) ----------
import investigar_kira as iv

core._tras_estudiar("redes neuronales")
enc = [p.get("texto") or "" for p in iv.listar(core.dir)]
mio = [e for e in enc if "redes neuronales" in e.lower()]
ok(mio and iv.clasificar_peticion(mio[0]) == "programa",
   "lo aprendido deja un encargo de PROGRAMAR (→ Solución → eliges app/mejora), no una app suelta")
ok("KiraOS" in mio[0] and ("movil" in mio[0].lower() or "móvil" in mio[0].lower()),
   "el encargo menciona que puede ser para KiraOS o para Kira móvil")

# ---------- (D) superadministrador: solo cuando el dueño lo pida ----------
core.es_kiraos = False
r = core._orden_superadmin("quiero que seas administrador")
ok(r and "android" in r.lower(), "en el móvil: explica que el administrador es cosa del portátil")
core.es_kiraos = True
for frase in ("se superadministrador", "ponte de administrador", "activa el modo root", "dame permisos de administrador", "quiero que seas administrador del sistema"):
    r = core._orden_superadmin(frase)
    ok(bool(r), "reconoce la petición de administrador: «%s»" % frase)
r = core._orden_superadmin("se superadministrador")
ok("solo cuando tú me lo pidas" in r.lower() and "contraseña" in r.lower() and "terminal" in r.lower(),
   "KiraOS: admin SOLO cuando tú lo pidas, en la Terminal con tu contraseña; sola nunca")
ok(core._orden_superadmin("hazme un juego de coches") is None
   and core._orden_superadmin("administra mi agenda") is None,
   "no se dispara con órdenes normales")

# y está enrutado en el dispatch
po = next(nd for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef) and nd.name == "_procesar_orden")
ok("_orden_superadmin" in (ast.get_source_segment(src, po) or ""), "el dispatch mira la petición de administrador")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
