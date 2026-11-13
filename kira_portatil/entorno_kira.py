# -*- coding: utf-8 -*-
"""
entorno_kira.py — v3.29 (SOLO KiraOS): que Kira CONOZCA su entorno, para defenderse y para saber qué puede ejecutar.

Lo pidió el dueño: «quiero que conozca su entorno, dónde está instalado, qué programa, librería o recursos tiene en su
mano, para prevenir cualquier ataque».

Es SOLO LECTURA (mira, no toca nada; no necesita administrador): dónde está instalada, qué sistema, qué Python y
librerías tiene, qué herramientas hay a mano (git, firejail, nmap, tshark, qemu…) y sus recursos (RAM, disco, CPU).
`which` y `correr` se inyectan para poder probarlo.
"""
import os
import re
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # la carpeta de kira_god (donde está instalada)

# herramientas que a Kira le importan (para programar, aislar/experimentar, defender la red, su máquina, sentidos…)
HERRAMIENTAS = {
    "git": "clonar repos", "python3": "su lenguaje", "pip3": "instalar librerías de Python",
    "node": "JavaScript", "npm": "paquetes de JavaScript",
    "firejail": "aislar lo que prueba", "bwrap": "aislar lo que prueba (bubblewrap)",
    "nmap": "mirar su red (defensa)", "tshark": "mirar el tráfico (defensa)",
    "qemu-system-x86_64": "su máquina virtual", "tailscale": "conectarse fuera de casa",
    "nmcli": "la WiFi", "tesseract": "leer texto de imágenes (OCR)", "fswebcam": "la cámara",
    "scrot": "capturar la pantalla", "ffmpeg": "vídeo/audio", "brightnessctl": "el brillo",
}


def donde():
    return RAIZ


def sistema():
    datos = {}
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for linea in f:
                if "=" in linea:
                    k, v = linea.split("=", 1)
                    datos[k.strip()] = v.strip().strip('"')
    except OSError:
        pass
    return datos.get("PRETTY_NAME") or datos.get("NAME") or "Linux"


def python_info():
    return {"version": sys.version.split()[0], "ejecutable": sys.executable}


def herramientas(which=None):
    which = which or shutil.which
    return {h: bool(which(h)) for h in HERRAMIENTAS}


def librerias(correr=None, maximo=40):
    """Las librerías de Python instaladas (nombre==versión), de `pip3 list`. Lista acotada."""
    correr = correr or _correr
    try:
        rc, salida = correr(["pip3", "list", "--format=freeze"])
    except Exception:
        return []
    if rc != 0:
        return []
    libs = []
    for linea in (salida or "").splitlines():
        m = re.match(r"^([A-Za-z0-9_.\-]+)==", linea.strip())
        if m:
            libs.append(m.group(1))
    return sorted(set(libs))[:maximo]


def recursos():
    try:
        import nacimiento_kira as nk
        return nk.equipo()
    except Exception:
        return {}


def _correr(args, cwd=None, timeout=20):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def resumen(which=None, correr=None):
    h = herramientas(which)
    return {"donde": donde(), "sistema": sistema(), "python": python_info(),
            "herramientas": {k: v for k, v in h.items() if v},
            "faltan": [k for k, v in h.items() if not v],
            "librerias": librerias(correr), "recursos": recursos()}


def texto(res=None, which=None, correr=None):
    r = res or resumen(which, correr)
    tengo = ", ".join(sorted(r["herramientas"])) or "ninguna especial"
    recu = r.get("recursos") or {}
    partes = [
        f"Estoy instalada en {r['donde']}, sobre {r['sistema']}.",
        f"Mi Python es la versión {r['python']['version']}.",
        f"Herramientas que tengo a mano: {tengo}.",
    ]
    if r.get("faltan"):
        partes.append("Me faltan (no las necesito siempre): " + ", ".join(sorted(r["faltan"])) + ".")
    if r.get("librerias"):
        libs = r["librerias"]
        partes.append(f"Tengo {len(libs)} librerías de Python, por ejemplo: " + ", ".join(libs[:12]) + ".")
    if recu.get("ram") or recu.get("disco"):
        partes.append("Recursos: " + ", ".join(
            str(recu[k]) for k in ("procesador", "ram", "disco") if recu.get(k)) + ".")
    partes.append("Todo esto lo miro en modo lectura, para saber con qué defenderme y qué puedo ejecutar con seguridad.")
    return " ".join(partes)


def es_orden(texto):
    """«conoce/estudia/analiza tu entorno», «qué tienes instalado / a mano», «qué herramientas/librerías/recursos
    tienes», «dónde estás instalada». Devuelve True, o None."""
    t = str(texto or "").lower()
    if re.search(r"\b(tu|su)\s+entorno\b", t) and re.search(r"\b(conoce|conocer|estudia|analiza|mira|revisa|describe|cu[aá]l|qu[eé])\b", t):
        return True
    if re.search(r"\bqu[eé]\s+(tienes|hay)\b.*\b(instalad|a\s+mano|herramienta|librer|recurso|programa)", t):
        return True
    if re.search(r"\bqu[eé]\s+(herramientas|librer[ií]as|recursos|programas)\b.*\btienes\b", t):
        return True
    if re.search(r"\bd[oó]nde\s+est[aá]s\s+instalad", t):
        return True
    return None
