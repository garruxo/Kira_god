# -*- coding: utf-8 -*-
"""v3.06: «implementa las mejoras» / «actualízate» / «¿hay mejoras?». Antes Kira decía «No reconozco la orden»
(foto del dueño en KiraOS). Ahora KiraOS mira en GitHub sus mejoras nuevas, te las enseña y, si se lo pides, se las
pone (solo avanzar; si hay cambios tuyos, no toca nada), te dice la versión y qué lanzar a mano si hace falta.
Aquí: con git DE VERDAD sobre un «GitHub» de mentira (un repositorio local)."""
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
import actualizar_kira as ak  # noqa: E402

n = 0


def ok(c, m):
    global n
    n += 1
    print(("[OK] " if c else "[X] ") + m)
    if not c:
        sys.exit(1)


for f in ("implementa las mejoras", "Kira, implementa las mejoras", "actualízate", "aplica las mejoras pendientes",
          "instala las actualizaciones", "pon las nuevas mejoras", "actualiza kiraos", "ponte al día"):
    ok(ak.es_orden(f) == "poner", f"«{f}» = ponerse las mejoras")
for f in ("hay mejoras nuevas", "¿qué mejoras hay?", "busca actualizaciones", "hay actualizaciones"):
    ok(ak.es_orden(f) == "mirar", f"«{f}» = mirar si hay")
for f in ("implementa este código", "mejora la voz", "hazme un juego", "estudia python", "qué tal estás"):
    ok(ak.es_orden(f) is None, f"«{f}» no es esto")

if not shutil.which("git"):
    print("(sin git: me salto la parte de verdad)")
    print("\nTODO BIEN", n)
    sys.exit(0)


def g(*a, cwd=None):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True,
                       env=dict(os.environ, GIT_AUTHOR_NAME="k", GIT_AUTHOR_EMAIL="k@k", GIT_COMMITTER_NAME="k",
                                GIT_COMMITTER_EMAIL="k@k"))
    assert r.returncode == 0, r.stderr
    return r.stdout


origen = os.path.join(T, "github.git")
g("init", "-q", "--bare", "-b", "main", origen)
trabajo = os.path.join(T, "claude")
g("clone", "-q", origen, trabajo)
open(os.path.join(trabajo, "version_kira.py"), "w").write('VERSION = "3.05"\n')
g("add", "-A", cwd=trabajo)
g("commit", "-qm", "v3.05: al encender, solo Kira", cwd=trabajo)
g("push", "-q", "origin", "HEAD:main", cwd=trabajo)
portatil = os.path.join(T, "kira_god")
g("clone", "-q", origen, portatil)
ok(ak.version_de(portatil) == "3.05" and ak.hay_repo(portatil), "el portátil tiene su código como repositorio")

r = ak.actualizar(portatil, poner=False)
ok(r["ok"] and "Ya tengo todas las mejoras" in r["texto"] and "3.05" in r["texto"], "sin novedades: lo dice")

open(os.path.join(trabajo, "version_kira.py"), "w").write('VERSION = "3.06"\n')
os.makedirs(os.path.join(trabajo, "kira_portatil"))
open(os.path.join(trabajo, "kira_portatil", "solo_kira.sh"), "w").write("echo hola\n")
g("add", "-A", cwd=trabajo)
g("commit", "-qm", "v3.06: Kira se pone sus mejoras cuando se lo pides", cwd=trabajo)
g("push", "-q", "origin", "HEAD:main", cwd=trabajo)

r = ak.actualizar(portatil, poner=False)
ok(r["ok"] and r["nuevas"] == ["v3.06: Kira se pone sus mejoras cuando se lo pides"]
   and "implementa las mejoras" in r["texto"], "«¿hay mejoras?»: las enseña con su título")
ok(ak.version_de(portatil) == "3.05", "y mirar NO cambia nada")

r = ak.actualizar(portatil, poner=True)
ok(r["ok"] and r["antes"] == "3.05" and r["despues"] == "3.06" and "3.05 → 3.06" in r["texto"],
   "«implementa las mejoras»: se las pone y dice la versión")
ok("reinicia" in r["texto"].lower(), "y que reinicie para usarlas")
ok("bash solo" in r["texto"], "si cambió algo que pide tu contraseña, dice qué lanzar (bash solo + Tab)")
ok(ak.actualizar(portatil, poner=True)["texto"].startswith("Ya tengo todas"), "otra vez: ya las tiene")

# un cambio tuyo a mano: no se toca nada
open(os.path.join(trabajo, "version_kira.py"), "w").write('VERSION = "3.07"\n')
g("commit", "-qam", "v3.07", cwd=trabajo)
g("push", "-q", "origin", "HEAD:main", cwd=trabajo)
open(os.path.join(portatil, "version_kira.py"), "w").write('VERSION = "toqueteado"\n')
r = ak.actualizar(portatil, poner=True)
ok(not r["ok"] and "No he cambiado nada" in r["texto"], "si tocaste archivos a mano, no los pisa: " + r["texto"][:80])
ok(open(os.path.join(portatil, "version_kira.py")).read() == 'VERSION = "toqueteado"\n', "(de verdad intacto)")
r = ak.actualizar(os.path.join(T, "no_es_repo"), poner=True)
ok(not r["ok"] and "repositorio" in r["texto"], "sin repositorio, lo dice")
r = ak.actualizar(portatil, poner=False, correr=lambda a, e=0: (1, "", "fatal: unable to access github.com\n")
                  if "fetch" in a else (0, "", ""))
ok(not r["ok"] and "internet" in r["texto"], "sin internet, lo dice")

# ---------- el núcleo y la pantalla ----------
import kira_god  # noqa: E402
core = kira_god.KiraGodCore()
core.dir = os.path.join(T, "datos")
os.makedirs(core.dir)
ak.hay_repo = lambda raiz=None: False
r = core.procesar_orden("implementa las mejoras")
ok("No reconozco" not in r and "APK" in r, "en el móvil: explica que sus mejoras llegan como APK")
ak.hay_repo = lambda raiz=None: True
ak.actualizar = lambda raiz=None, poner=True, correr=None: {"texto": "PUESTAS" if poner else "MIRADAS"}
ok(core.procesar_orden("Kira, implementa las mejoras").startswith("PUESTAS"), "en KiraOS: se las pone")
ok(core.procesar_orden("hay mejoras nuevas").startswith("MIRADAS"), "y «¿hay mejoras?» solo mira")
itf = open(os.path.join(RAIZ, "interfaz_kira.py"), encoding="utf-8").read()
ok(itf.count("es_orden(orden):                         # v3.06") + itf.count("es_orden(orden):                        # v3.06") == 2,
   "la app lo reconoce en los dos modos (antes lo mandaba a «prepara una mejora»)")
import escritorio_kira as esk  # noqa: E402
ok(all(esk._TRANSITORIA.match(x) for x in ("En cola: lo haré en cuanto acabe lo de antes.", "Pensando…")),
   "KiraOS quita los avisos de espera («En cola…», «Pensando…») cuando ya ha contestado")
ok(not esk._TRANSITORIA.match("[OK] Me he puesto 2 mejoras"), "pero no lo demás")
ok(not esk.EscritorioMixin().es_busqueda("busca actualizaciones"), "«busca actualizaciones» no abre el Buscador")
print("\nTODO BIEN", n)
