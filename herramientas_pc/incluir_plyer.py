# -*- coding: utf-8 -*-
"""
incluir_plyer.py - Mete la librería 'plyer' (la voz de Kira) DENTRO de la carpeta del proyecto.

Por qué: si 'plyer' va en requirements de buildozer.spec, python-for-android crea un entorno de Python aparte y hace
"pip install -U pip" para instalarlo; en algunos equipos esa actualización de pip se rompe siempre
(ImportError: cannot import name 'BuildDependencyInstallError'). Con plyer dentro del proyecto ese paso no existe.

Uso (desde la carpeta Kira_god, con internet):   python herramientas_pc/incluir_plyer.py
       o con un .whl ya descargado:              python herramientas_pc/incluir_plyer.py ruta/plyer-X.whl
Deja la carpeta  Kira_god/plyer/  y no toca nada más. Se puede repetir sin problema.
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def descargar(destino):
    r = subprocess.run([sys.executable, "-m", "pip", "download", "plyer", "--no-deps", "--only-binary=:all:", "-d", destino],
                       capture_output=True, text=True)
    ruedas = glob.glob(os.path.join(destino, "plyer-*.whl"))
    if r.returncode != 0 or not ruedas:
        raise SystemExit("No se pudo descargar plyer:\n" + (r.stdout + r.stderr)[-800:])
    return ruedas[0]


def incluir(rueda):
    with zipfile.ZipFile(rueda) as z:
        nombres = [n for n in z.namelist() if n.startswith("plyer/")]
        if not nombres:
            raise SystemExit(f"{rueda} no contiene la carpeta plyer/")
        with tempfile.TemporaryDirectory() as tmp:
            z.extractall(tmp, members=nombres)
            destino = os.path.join(RAIZ, "plyer")
            if os.path.isdir(destino):
                shutil.rmtree(destino)
            shutil.copytree(os.path.join(tmp, "plyer"), destino)
    n = sum(len(f) for _r, _d, f in os.walk(os.path.join(RAIZ, "plyer")))
    print(f"[OK] plyer incluido en {os.path.join(RAIZ, 'plyer')} ({n} archivos). Ya no hace falta en requirements.")


def main():
    if len(sys.argv) > 1:
        incluir(sys.argv[1])
        return
    with tempfile.TemporaryDirectory() as tmp:
        incluir(descargar(tmp))


if __name__ == "__main__":
    main()
