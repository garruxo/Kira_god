# -*- coding: utf-8 -*-
"""
incluir_pypdf.py - Mete la librería 'pypdf' (el lector de PDF de Kira, Python puro, licencia BSD) DENTRO del proyecto,
igual que incluir_plyer.py: así va seguro dentro del APK sin pasar por requirements de buildozer.

Uso (con internet):          python herramientas_pc/incluir_pypdf.py
    con un .whl ya bajado:   python herramientas_pc/incluir_pypdf.py ruta/pypdf-X.whl
Deja la carpeta  Kira_god/pypdf/ (no se sube a git). La compilación en GitHub lo hace sola.
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "5.9.0"


def descargar(destino):
    r = subprocess.run([sys.executable, "-m", "pip", "download", f"pypdf=={VERSION}", "--no-deps", "--only-binary=:all:",
                        "-d", destino], capture_output=True, text=True)
    ruedas = glob.glob(os.path.join(destino, "pypdf-*.whl"))
    if r.returncode != 0 or not ruedas:
        raise SystemExit("No se pudo descargar pypdf:\n" + (r.stdout + r.stderr)[-800:])
    return ruedas[0]


def incluir(rueda):
    with zipfile.ZipFile(rueda) as z:
        nombres = [n for n in z.namelist() if n.startswith("pypdf/")]
        if not nombres:
            raise SystemExit(f"{rueda} no contiene la carpeta pypdf/")
        with tempfile.TemporaryDirectory() as tmp:
            z.extractall(tmp, members=nombres)
            destino = os.path.join(RAIZ, "pypdf")
            if os.path.isdir(destino):
                shutil.rmtree(destino)
            shutil.copytree(os.path.join(tmp, "pypdf"), destino)
    n = sum(len(f) for _r, _d, f in os.walk(os.path.join(RAIZ, "pypdf")))
    print(f"[OK] pypdf {VERSION} incluido en {os.path.join(RAIZ, 'pypdf')} ({n} archivos).")


def main():
    if len(sys.argv) > 1:
        incluir(sys.argv[1])
        return
    with tempfile.TemporaryDirectory() as tmp:
        incluir(descargar(tmp))


if __name__ == "__main__":
    main()
