# -*- coding: utf-8 -*-
"""v3.32 (SOLO KiraOS): si una app necesita librerías para funcionar, Kira las busca y las descarga — pero PREGUNTANDO
antes al dueño (nunca sola). pip --user / npm sin administrador; lo del sistema (apt) va a la Terminal con su contraseña."""
import io
import os
import shutil
import sys
import tarfile
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATOS_NUCLEO"] = os.path.join(T, "kira_datos")
os.makedirs(os.environ["KIRA_DATOS_NUCLEO"], exist_ok=True)
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))

n = fallos = 0


def ok(c, m):
    global n, fallos
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


import apps_externas_kira as aex

# ---------------- detectar lo que necesita ----------------
d = os.path.join(T, "app_py")
os.makedirs(d)
open(os.path.join(d, "requirements.txt"), "w").write("# comentario\nnumpy==1.26\nrequests>=2\n-e .\ngit+https://x/y\nrich\n")
dep = aex.dependencias(d)
ok(dep["tiene"] and dep["pip"] == ["numpy", "requests", "rich"] and dep["archivo_req"],
   "requirements.txt: saca los paquetes (ignora comentarios, -e, git+)")
ok("numpy" in dep["resumen"], "el resumen nombra los paquetes")

d2 = os.path.join(T, "app_pyproject")
os.makedirs(d2)
open(os.path.join(d2, "pyproject.toml"), "w").write('[project]\ndependencies = ["flask>=2", "click"]\n')
ok(aex.dependencias(d2)["pip"] == ["click", "flask"], "pyproject.toml: saca dependencies")

d3 = os.path.join(T, "app_setup")
os.makedirs(d3)
open(os.path.join(d3, "setup.py"), "w").write("setup(name='x', install_requires=['pillow', 'tqdm>=4'])\n")
ok(aex.dependencias(d3)["pip"] == ["pillow", "tqdm"], "setup.py: saca install_requires")

d4 = os.path.join(T, "app_npm")
os.makedirs(d4)
open(os.path.join(d4, "package.json"), "w").write('{"name":"x","dependencies":{"left-pad":"1.0.0"}}')
dn = aex.dependencias(d4)
ok(dn["npm"] and not dn["pip"], "package.json con dependencies: npm")

d5 = os.path.join(T, "app_sin")
os.makedirs(d5)
open(os.path.join(d5, "main.py"), "w").write("print('hola')\n")
ok(not aex.dependencias(d5)["tiene"], "una app sin requisitos: no necesita nada")

# ---------------- descargar lo que necesita (pip/npm de mentira) ----------------
llamadas = []


def correr_ok(args, cwd=None, timeout=0):
    llamadas.append(args)
    return 0, "Successfully installed numpy requests rich"


r = aex.instalar_dependencias(d, correr=correr_ok)
ok(r["ok"] and "Descargué" in r["mensaje"] and llamadas and llamadas[0][:3] == ["pip3", "install", "--user"]
   and "-r" in llamadas[0], "descarga con pip --user -r requirements.txt (sin administrador)")


def correr_sin_pip(args, cwd=None, timeout=0):
    return 127, "pip3: command not found"


r = aex.instalar_dependencias(d, correr=correr_sin_pip)
ok("python3-pip" in r["mensaje"], "sin pip: dice de instalarlo en la Terminal")


def correr_falta_sistema(args, cwd=None, timeout=0):
    return 1, "ERROR: Failed building wheel ... fatal error: Python.h: No such file"


r = aex.instalar_dependencias(d, correr=correr_falta_sistema)
ok("no se pudo bajar" in r["mensaje"].lower(), "si un paquete falla, lo dice (puede necesitar algo del sistema)")

r = aex.instalar_dependencias(d4, correr=correr_ok)
ok(["npm", "install"] in llamadas, "npm: instala en la carpeta de la app")

ok(aex.instalar_dependencias(d5, correr=correr_ok)["ok"] and "tal cual" in aex.instalar_dependencias(d5)["mensaje"],
   "sin dependencias: no descarga nada")

# ---------------- de un error, saber qué falta ----------------
f = aex.faltan_por_error("Traceback...\nModuleNotFoundError: No module named 'numpy'")
ok(f and f["tipo"] == "pip" and f["que"] == "numpy" and "pip3 install --user numpy" in f["consejo"],
   "error «No module named numpy» → pip")
f = aex.faltan_por_error("./app: error while loading shared libraries: libGL.so.1: cannot open")
ok(f and f["tipo"] == "sistema" and "libGL.so.1" in f["que"], "librería del sistema que falta (.so) → Terminal")
f = aex.faltan_por_error("bash: ffmpeg: command not found")
ok(f and f["tipo"] == "sistema" and f["que"] == "ffmpeg", "una orden que falta → apt en la Terminal")
ok(aex.faltan_por_error("todo bien") is None, "sin error reconocible → None")

# ---------------- reconocer la orden ----------------
for s in ["descarga las dependencias de krita", "instala las dependencias de la app foo",
          "descarga lo que necesita krita", "baja lo que le falta a gimp", "consigue las librerías de blender",
          "Kira, descarga lo que le hace falta a inkscape"]:
    ok(aex.es_orden_dependencias(s), "reconoce: " + s)
for s in ["instala krita", "descarga e instala esto", "qué necesitas", "descarga el curso de python",
          "instala las mejoras"]:
    ok(not aex.es_orden_dependencias(s), "NO se dispara: " + s)
ok(aex.es_orden_dependencias("descarga las dependencias de krita") == "krita", "saca el nombre de la app")

# ---------------- instalar INCLUYE las dependencias detectadas ----------------
tgz = os.path.join(T, "con_req.tar.gz")
with tarfile.open(tgz, "w:gz") as tf:
    for nom, cont in [("app/main.py", b"print(1)\n"), ("app/requirements.txt", b"numpy\nrich\n")]:
        info = tarfile.TarInfo(nom)
        info.size = len(cont)
        tf.addfile(info, io.BytesIO(cont))
r = aex.instalar("https://x/app-1.0.tar.gz", base=os.path.join(T, "apps"), bajar=lambda u, dst: (shutil.copy(tgz, dst), 1)[1])
ok(r["ok"] and r.get("dependencias", {}).get("pip") == ["numpy", "rich"],
   "instalar un comprimido detecta sus dependencias (no las instala aún)")
ok("descarga las dependencias de" in aex.aviso_dependencias(r["dependencias"], r["nombre"]),
   "aviso_dependencias pregunta cómo pedir la descarga")
ok(aex.aviso_dependencias({"tiene": False}, "x") == "", "sin dependencias: no avisa")

# ---------------- de punta a punta con el núcleo ----------------
import accesos_kira as ak
import nucleo_portatil as nk

DATOS = os.environ["KIRA_DATOS_NUCLEO"]
app_dir = os.path.join(T, "apps", "miapp")
os.makedirs(app_dir, exist_ok=True)
open(os.path.join(app_dir, "main.py"), "w").write("import numpy\n")
open(os.path.join(app_dir, "requirements.txt"), "w").write("numpy\n")
ak.anadir_externa(DATOS, "miapp", ["python3", os.path.join(app_dir, "main.py")], app_dir)


class Core:
    dir = DATOS


aex._correr_defecto = correr_ok   # pip de mentira (no toca la red de verdad)
pasos = []
res = nk._dependencias_app(Core(), "miapp", lambda fr, t: pasos.append(t))
ok("Descargué" in res["texto"], "«descarga las dependencias de miapp» descarga lo que necesita")
res = nk._dependencias_app(Core(), "noexiste", lambda fr, t: None)
ok(res.get("ok") is False and "No tengo instalada" in res["texto"], "una app que no tiene: lo dice")

# cableado por AST
src = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("es_orden_dependencias" in src and "_dependencias_app" in src, "el núcleo enruta «descarga las dependencias de X»")
ok("aviso_dependencias" in src, "al instalar, el núcleo avisa de las dependencias")
src_e = open(os.path.join(RAIZ, "kira_portatil", "escritorio_kira.py"), encoding="utf-8").read()
ok("aviso_dependencias" in src_e, "el escritorio también avisa de las dependencias al instalar")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
