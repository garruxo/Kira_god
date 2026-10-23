# -*- coding: utf-8 -*-
"""
preparar_brython.py - Prepara lo que hace falta para que los juegos de Kira funcionen en el NAVEGADOR (web_kira/).

Brython (https://brython.info, licencia BSD-3) es Python escrito en JavaScript: con él, el MISMO código del juego
(motor_juegos_kira + tu juego) funciona en una página web, sin traducirlo.

    git clone --depth 1 --branch 3.14.3 https://github.com/brython-dev/brython
    python herramientas_pc/preparar_brython.py brython/www/src

Copia brython.js y saca de brython_stdlib.js (4,8 MB) solo los módulos que usan los juegos:
  - stdlib_base.js     (math y random: casi todos los juegos)
  - stdlib_ampliada.js (además collections, itertools, functools, colorsys, json, string, time, heapq, copy)
Las listas se sacaron probando en Chromium qué pide de verdad cada import (cmath no funciona en Brython).
"""
import json
import os
import shutil
import sys

BASE = ["math", "_random", "random", "warnings", "sys", "_py_warnings", "_contextvars", "_thread", "os", "abc",
        "_py_abc", "_weakrefset", "_weakref", "types", "posix", "posixpath", "stat", "genericpath",
        "_collections_abc", "operator", "itertools", "bisect", "hashlib"]
AMPLIADA = BASE + ["collections", "_collections", "keyword", "reprlib", "functools", "colorsys", "json", "_json",
                   "json.encoder", "re", "enum", "python_re", "string", "_string", "time", "_locale", "heapq", "copy",
                   "weakref", "copyreg"]


def escribir(vfs, modulos, ruta):
    sal = {"$timestamp": vfs["$timestamp"]}
    sal.update({m: vfs[m] for m in modulos})
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("__BRYTHON__.use_VFS = true;\nvar scripts = " + json.dumps(sal, ensure_ascii=False)
                + "\n__BRYTHON__.update_VFS(scripts)\n")


def main(origen, destino):
    with open(os.path.join(origen, "brython_stdlib.js"), encoding="utf-8") as f:
        src = f.read()
    a = src.index("var scripts = ") + len("var scripts = ")
    b = src.rindex("\n__BRYTHON__.update_VFS")
    vfs = json.loads(src[a:b])
    os.makedirs(destino, exist_ok=True)
    shutil.copyfile(os.path.join(origen, "brython.js"), os.path.join(destino, "brython.js"))
    escribir(vfs, BASE, os.path.join(destino, "stdlib_base.js"))
    escribir(vfs, AMPLIADA, os.path.join(destino, "stdlib_ampliada.js"))
    for n in ("brython.js", "stdlib_base.js", "stdlib_ampliada.js"):
        print(n, os.path.getsize(os.path.join(destino, n)) // 1024, "KB")


if __name__ == "__main__":
    aqui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(aqui, "web_kira"))
