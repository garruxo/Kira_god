# -*- coding: utf-8 -*-
"""v3.96: un programa cuya carpeta trae un debian/ (empaquetado de Debian) NO se compila con debian/rules (necesita
debhelper/root): se ignora debian/, se compila el código de verdad (src/, configure/make) y se arranca el binario que
sale. Reproduce el fallo del dueño: «make … debian/rules:7 override_dh_auto_install Error 127»."""
import os, stat, sys, tempfile, time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATOS_NUCLEO"] = T
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import arreglar_app_kira as arr
import apps_externas_kira as aex
arr.REGISTROS = os.path.join(T, "reg")

fallos = n = 0
def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1

# ---- un paquete como el del dueño: raíz con debian/ + README, el código en src/ ----
app = os.path.join(T, "apps", "reaver", "contenido")
os.makedirs(os.path.join(app, "debian"))
os.makedirs(os.path.join(app, "src"))
# debian/rules: un Makefile EJECUTABLE que, si se toca, llama a dh (debhelper) y falla como en la foto
rules = os.path.join(app, "debian", "rules")
open(rules, "w").write("#!/usr/bin/make -f\n%:\n\tdh $@\noverride_dh_auto_install:\n\t"
                       "dh override_dh_auto_install --sourcedirectory=src\n")
os.chmod(rules, 0o755)
open(os.path.join(app, "debian", "control"), "w").write("Source: reaver\n")
# el código de verdad en src/: un configure (genera Makefile) y un Makefile que compila un binario
conf = os.path.join(app, "src", "configure")
open(conf, "w").write("#!/bin/sh\ncat > Makefile <<'M'\nreaver: reaver.c\n\tcc -o reaver reaver.c\nM\n")
os.chmod(conf, 0o755)
open(os.path.join(app, "src", "reaver.c"), "w").write("int main(void){return 0;}\n")
open(os.path.join(app, "README.md"), "w").write(
    "# reaver\n## Build (Linux)\n```\ncd src\n./configure\nmake\n```\n"
    "## Debian package\n```\ndpkg-buildpackage -us -uc\nfakeroot debian/rules binary\n```\n")

# 1) buscar el lanzador NO debe elegir debian/rules
lan = aex.buscar_lanzador(app)
ok(lan is None or "debian/rules" not in " ".join(lan), "buscar_lanzador NO coge debian/rules: " + str(lan))
ok(not aex._no_es_programa("rules") is False, "«rules» (Makefile de empaquetado) no es el programa")
ok("debian" in aex._NO_MIRAR, "debian/ está en lo que no se mira")

# 2) la carpeta donde se compila es src/
ok(arr.carpeta_construir(app) == os.path.join(app, "src"), "carpeta_construir → src/: " + arr.carpeta_construir(app))
ok(arr.necesita_construir(app), "ve que hay que compilar (src/ tiene configure)")
pasos = arr.pasos_por_defecto(app)
ok(pasos and pasos[0] == "cd src", "los pasos por defecto entran en src/: " + str(pasos))
ok(any("configure" in p for p in pasos) and any(p == "make" for p in pasos), "y hacen ./configure + make")

# 3) el README: se queda cd src/configure/make, se TIRAN dpkg-buildpackage y debian/rules
ordenes = arr.ordenes_de_texto(open(os.path.join(app, "README.md")).read(), app)
ok(any("configure" in o for o in ordenes), "del README saca ./configure")
ok(not any("dpkg-buildpackage" in o or "debian/rules" in o or o.strip().startswith("dh ") for o in ordenes),
   "del README NO saca el empaquetado .deb: " + str(ordenes))

# 4) construir DE VERDAD con bash: compila en src/, sale el binario, nunca toca debian/rules
import subprocess
def correr(args, cwd=None, timeout=600):
    p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    return p.returncode, p.stdout
r = arr.construir({"carpeta": app, "titulo": "reaver"}, correr=correr, admin=False)
ok(r["ok"], "construir funciona: " + str(r.get("error")))
ok(r["lanzar"] and r["lanzar"][-1].endswith(os.path.join("src", "reaver")), "arranca el binario de src/: " + str(r.get("lanzar")))
ok(os.path.isfile(os.path.join(app, "src", "reaver")), "el binario reaver se compiló en src/")
ok(not any("debian/rules" in str(h) or "dh " in str(h) for h in r["hecho"]), "nunca ejecutó debian/rules: " + str(r["hecho"]))

# 5) si SOLO hay debian/ (sin src/ con código), no se inventa: no hay dónde compilar → raíz
solo = os.path.join(T, "solo", "contenido"); os.makedirs(os.path.join(solo, "debian"))
open(os.path.join(solo, "debian", "rules"), "w").write("#!/usr/bin/make -f\n%:\n\tdh $@\n")
ok(arr.carpeta_construir(solo) == solo and not arr.necesita_construir(solo), "sin código real, no intenta compilar debian/")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
