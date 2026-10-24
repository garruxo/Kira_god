# -*- coding: utf-8 -*-
"""
bloqueo_kira.py - El candado de entrada de KiraOS en el portátil: un PIN de 4 cifras.

Guarda el PIN cifrado (NO en claro): pbkdf2-sha256 con sal al azar, en `pin_kira.txt` (permisos 0600, solo el
dueño). Nunca se puede leer el PIN del archivo. La huella/cara las pone el sistema operativo (aquí solo se deja el
hueco: `biometria_disponible`), así que esto es la reserva por PIN, que siempre funciona.

Sin ventana a propósito: toda la lógica se puede probar (tests/test_bloqueo.py). La ventana es cosa de kiraos.py.

  hay_pin()            ¿ya hay un PIN creado?
  crear_pin("1234")    crea (o cambia) el PIN; debe ser 4 cifras
  comprobar("1234")    True si acierta; cuenta los fallos y aplica una espera corta tras varios
  estado()             info para la pantalla (si hay PIN, intentos fallidos, segundos de espera)
"""
import hashlib
import json
import os
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(AQUI, "pin_kira.txt")

_VUELTAS = 200_000          # pbkdf2: cuanto más alto, más caro de adivinar a la fuerza
_MAX_LIBRES = 5             # fallos seguidos antes de empezar a hacer esperar
_ESPERA = 30               # segundos de espera que se suman por cada fallo de más


class BloqueoError(ValueError):
    """El PIN no vale (p. ej. no son 4 cifras)."""


def _cifra(pin, sal):
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), sal, _VUELTAS).hex()


def _valida(pin):
    pin = (pin or "").strip()
    if len(pin) != 4 or not pin.isdigit():
        raise BloqueoError("El PIN tiene que ser de 4 cifras.")
    return pin


def _leer(ruta=None):
    ruta = ruta or RUTA
    if not os.path.isfile(ruta):
        return None
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        if "sal" in d and "hash" in d:
            return d
    except (ValueError, OSError):
        return None
    return None


def _guardar(d, ruta=None):
    ruta = ruta or RUTA
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(d, f)
    try:
        os.chmod(ruta, 0o600)
    except OSError:
        pass


def hay_pin(ruta=None):
    return _leer(ruta) is not None


def crear_pin(pin, ruta=None):
    """Crea o cambia el PIN. Lanza BloqueoError si no son 4 cifras."""
    pin = _valida(pin)
    sal = os.urandom(16)
    _guardar({"sal": sal.hex(), "hash": _cifra(pin, sal), "fallos": 0, "desde": 0}, ruta)
    return True


def _espera_restante(d):
    """Segundos que faltan por esperar tras demasiados fallos (0 si puede probar ya)."""
    de_mas = d.get("fallos", 0) - _MAX_LIBRES
    if de_mas <= 0:
        return 0
    fin = d.get("desde", 0) + de_mas * _ESPERA
    return max(0, int(round(fin - time.time())))


def comprobar(pin, ruta=None):
    """True si el PIN acierta. Cuenta los fallos y, tras varios, obliga a esperar (devuelve False mientras)."""
    d = _leer(ruta)
    if d is None:
        return False
    if _espera_restante(d) > 0:
        return False
    ok = False
    try:
        ok = (_cifra(_valida(pin), bytes.fromhex(d["sal"])) == d["hash"])
    except BloqueoError:
        ok = False
    if ok:
        d["fallos"] = 0
        d["desde"] = 0
    else:
        d["fallos"] = d.get("fallos", 0) + 1
        d["desde"] = int(time.time())
    _guardar(d, ruta)
    return ok


def estado(ruta=None):
    d = _leer(ruta)
    if d is None:
        return {"hay_pin": False, "fallos": 0, "espera": 0}
    return {"hay_pin": True, "fallos": d.get("fallos", 0), "espera": _espera_restante(d)}


def biometria_disponible():
    """Hueco para la huella/cara (lo pone el sistema). De momento, no en esta reserva por PIN."""
    return False
