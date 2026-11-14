# -*- coding: utf-8 -*-
"""
avisos_kira.py — v3.44 (SOLO KiraOS): AVISOS PRIORITARIOS de Kira para el dueño.

Cuando Kira acaba algo importante (p. ej. estudiar el portátil), deja un aviso que se ve ENCIMA de todo en el
escritorio de KiraOS (una franja rosa con «Visto») y lo dice en voz alta y con notify-send si está.
El aviso se queda hasta que pulsas «Visto». Se guarda en ~/.kira_aviso_prioritario.json (0600).
Solo es un AVISO: no hace nada por su cuenta.
"""
import json
import os
import shutil
import subprocess
import time

RUTA = os.environ.get("KIRA_AVISOS", os.path.expanduser("~/.kira_aviso_prioritario.json"))
MAX = 10


def _leer(ruta=None):
    try:
        with open(ruta or RUTA, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _escribir(lista, ruta=None):
    ruta = ruta or RUTA
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(lista[-MAX:], f, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, ruta)


def prioritario(texto, titulo="Aviso de Kira", ruta=None, notificar=True):
    lista = [a for a in _leer(ruta) if a.get("texto") != texto]
    a = {"id": str(int(time.time() * 1000)), "titulo": str(titulo)[:80], "texto": str(texto)[:600],
         "cuando": time.strftime("%Y-%m-%d %H:%M"), "visto": False}
    lista.append(a)
    _escribir(lista, ruta)
    if notificar and shutil.which("notify-send"):
        try:
            subprocess.Popen(["notify-send", "-u", "critical", a["titulo"], a["texto"]],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except Exception:
            pass
    return a


def pendiente(ruta=None):
    """El último aviso sin ver, o None."""
    for a in reversed(_leer(ruta)):
        if not a.get("visto"):
            return a
    return None


def visto(iid=None, ruta=None):
    lista = _leer(ruta)
    for a in lista:
        if iid is None or a.get("id") == iid:
            a["visto"] = True
    _escribir(lista, ruta)
    return True
