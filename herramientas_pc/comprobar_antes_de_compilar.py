# -*- coding: utf-8 -*-
"""
comprobar_antes_de_compilar.py - Revisión RÁPIDA antes de lanzar buildozer (que en un PC antiguo tarda horas).

Uso (desde la carpeta Kira_god):   python herramientas_pc/comprobar_antes_de_compilar.py
Comprueba, sin compilar nada:
  1. Que todos los .py tienen la sintaxis bien.
  2. Que cada import de un módulo del proyecto apunta a un archivo que existe.
  3. Que ningún módulo importa AL ARRANCAR (fuera de try/funciones) una librería que no va en el APK
     (requirements de buildozer.spec): eso cierra la app nada más abrirla en el móvil.
  4. Lo básico de buildozer.spec (requirements, permisos, arquitectura, licencia del SDK).
Sale con código 0 si todo está bien.
"""
import ast
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUIDAS = {"tests", "extras", "legacy", "herramientas_pc", "bin", ".buildozer", "__pycache__"}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) or {
    "os", "sys", "re", "json", "time", "math", "random", "threading", "subprocess", "shutil", "tempfile", "hashlib", "hmac",
    "secrets", "types", "unicodedata", "zlib", "urllib", "html", "difflib", "inspect", "importlib", "logging", "ast", "wave",
    "struct", "glob", "argparse", "socket", "http", "io", "collections", "functools", "itertools", "datetime", "string"}
PERMITIDAS_PEREZOSAS = {"android", "jnius", "PIL", "psutil", "imageio_ffmpeg", "plyer"}   # solo dentro de try/def


def modulos_proyecto():
    return {f[:-3] for f in os.listdir(RAIZ) if f.endswith(".py")}


def requirements():
    try:
        txt = open(os.path.join(RAIZ, "buildozer.spec"), encoding="utf-8").read()
    except OSError:
        return set()
    m = re.search(r"^requirements\s*=\s*(.+)$", txt, re.M)
    return {r.strip().split("==")[0].lower() for r in m.group(1).split(",")} if m else set()


def imports_de(arbol):
    """[(modulo_raiz, linea, nivel_superior)] nivel_superior=True si se ejecuta al importar el archivo."""
    res = []

    def visitar(nodo, arriba):
        for h in ast.iter_child_nodes(nodo):
            sub = arriba and not isinstance(h, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Try, ast.ClassDef, ast.If))
            if isinstance(h, ast.ClassDef):
                sub = arriba                     # el cuerpo de una clase SÍ se ejecuta al importar
            if isinstance(h, ast.Import):
                for a in h.names:
                    res.append((a.name.split(".")[0], h.lineno, arriba))
            elif isinstance(h, ast.ImportFrom) and h.module and h.level == 0:
                res.append((h.module.split(".")[0], h.lineno, arriba))
            visitar(h, sub)
    visitar(arbol, True)
    return res


def main():
    errores, avisos = [], []
    propios, reqs = modulos_proyecto(), requirements()
    en_apk = reqs | {"kivy"}
    for f in sorted(os.listdir(RAIZ)):
        if not f.endswith(".py"):
            continue
        ruta = os.path.join(RAIZ, f)
        try:
            arbol = ast.parse(open(ruta, encoding="utf-8").read(), ruta)
        except SyntaxError as e:
            errores.append(f"{f}: error de sintaxis en la línea {e.lineno}: {e.msg}")
            continue
        for mod, linea, arriba in imports_de(arbol):
            if mod in propios or mod in STDLIB or mod == "__future__":
                continue
            if mod.lower() in en_apk:
                continue
            if arriba:
                errores.append(f"{f}:{linea}: importa '{mod}' al arrancar y NO va en el APK (requirements). "
                               "Muévelo dentro de una función o de un try/except.")
            elif mod not in PERMITIDAS_PEREZOSAS:
                avisos.append(f"{f}:{linea}: usa '{mod}' (no está en requirements; asegúrate de que tiene plan B).")
    # buildozer.spec
    try:
        spec = open(os.path.join(RAIZ, "buildozer.spec"), encoding="utf-8").read()
        for clave, patron, msg in (("requirements", r"^requirements\s*=.*kivy", "requirements debe incluir kivy"),
                                   ("archs", r"^android\.archs\s*=\s*\S+", "falta android.archs"),
                                   ("licencia", r"^android\.accept_sdk_license\s*=\s*True", "pon android.accept_sdk_license = True (si no, buildozer se queda esperando)"),
                                   ("api", r"^android\.api\s*=\s*3[3-9]", "pon android.api = 33 o más (permisos de medios de Android 13)")):
            if not re.search(patron, spec, re.M):
                (errores if clave in ("requirements", "archs") else avisos).append(f"buildozer.spec: {msg}")
    except OSError:
        errores.append("No encuentro buildozer.spec")
    if "plyer" not in reqs and not os.path.isfile(os.path.join(RAIZ, "plyer", "__init__.py")):
        avisos.append("plyer (voz de reserva si falla VozKira, y el reconocedor de Android si no hay oído propio) no está "
                      "ni en requirements ni dentro del proyecto. Ejecuta antes:  python herramientas_pc/incluir_plyer.py   "
                      "(la compilación en GitHub ya lo hace)")
    if not os.path.isfile(os.path.join(RAIZ, "main.py")):
        errores.append("Falta main.py (buildozer arranca la app desde ahí)")
    if sys.platform.startswith("linux") and any(x.startswith("/mnt/") for x in os.environ.get("PATH", "").split(":")):
        avisos.append("El PATH de Ubuntu incluye carpetas de Windows (/mnt/c/...). Con espacios como «Program Files» suelen "
                      "romper la compilación. Antes de buildozer ejecuta:  "
                      "export PATH=$(echo \"$PATH\" | tr ':' '\\n' | grep -v '^/mnt/' | paste -sd:)")
    for a in avisos:
        print("[aviso]", a)
    for e in errores:
        print("[ERROR]", e)
    print(f"\n{len(errores)} error(es), {len(avisos)} aviso(s).", "Listo para compilar." if not errores else "Arregla los errores antes de compilar.")
    if sys.platform.startswith("win"):
        print("\nOJO: estás en Windows. Esta revisión sirve aquí, pero COMPILAR (buildozer android debug) solo funciona en "
              "Ubuntu/WSL (escribe  wsl  y sigue la guía) o en GitHub (camino A de COMPILAR_PACKARD_BELL.md). "
              "El buildozer instalado en el Python de Windows no puede compilar Android.")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
