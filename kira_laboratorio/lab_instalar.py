# -*- coding: utf-8 -*-
"""
lab_instalar.py  -  NO VA EN EL APK. Instalación OPCIONAL de dependencias en el PC del laboratorio.

Desactivada por defecto: solo funciona si arrancas el servidor con --permitir-instalar. Aun así:
  - solo paquetes de una LISTA BLANCA (nombre exacto; opcionalmente ==versión), nada de URLs ni archivos;
  - se ejecuta `python -m pip install` sin shell, con tiempo límite, y el móvil pide tu confirmación antes;
  - lo que instala vive en el Python del PC (o en tu entorno virtual si arrancaste el servidor desde uno).
"""
import importlib.metadata
import re
import subprocess
import sys

HABILITADO = False
LISTA_BLANCA = {
    "pillow": "dibujo de fotogramas (motor de vídeo)",
    "numpy": "cálculo numérico para audio e imagen",
    "imageio-ffmpeg": "trae un ffmpeg listo (vídeo y audio)",
    "pydub": "utilidades de audio de alto nivel",
    "mutagen": "leer etiquetas de música (título, artista…)",
    "soundfile": "leer y escribir audio (wav, flac, ogg)",
    "scipy": "filtros y análisis de señal",
}
_VERSION = re.compile(r"^[0-9]{1,3}(\.[0-9]{1,3}){0,3}$")


def normalizar(paquetes):
    """Lista de 'nombre' o 'nombre==x.y.z' validada contra la lista blanca. Lanza ValueError si algo no está permitido."""
    if not isinstance(paquetes, list) or not 1 <= len(paquetes) <= 8:
        raise ValueError("Indica entre 1 y 8 paquetes.")
    res = []
    for p in paquetes:
        nombre, _, ver = str(p).strip().lower().partition("==")
        if nombre not in LISTA_BLANCA:
            raise ValueError(f"'{nombre[:30]}' no está en la lista permitida: {', '.join(sorted(LISTA_BLANCA))}.")
        if ver and not _VERSION.match(ver):
            raise ValueError("Versión no válida.")
        res.append(nombre + (f"=={ver}" if ver else ""))
    return res


def estado_paquetes():
    """[{'nombre', 'para_que', 'instalado': versión|None}]"""
    out = []
    for n, para in sorted(LISTA_BLANCA.items()):
        try:
            v = importlib.metadata.version(n)
        except importlib.metadata.PackageNotFoundError:
            v = None
        out.append({"nombre": n, "para_que": para, "instalado": v})
    return out


def instalar(paquetes, timeout=900):
    """(ok, últimas líneas del registro de pip)."""
    try:
        lista = normalizar(paquetes)
    except ValueError as e:
        return False, str(e)
    try:
        p = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", *lista],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"pip tardó más de {timeout} s."
    except OSError as e:
        return False, f"No se pudo lanzar pip: {e}"
    return p.returncode == 0, (p.stdout + p.stderr).strip()[-600:]
