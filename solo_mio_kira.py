# -*- coding: utf-8 -*-
"""
solo_mio_kira.py - v3.02: el interruptor «ESTUDIA SOLO LO QUE YO TE MANDE». VA EN EL APK y en KiraOS; puro.

Normalmente, cuando no le das nada, Kira piensa sola sobre temas suyos (lo de su baúl y una lista de serie). Con este
interruptor ENCENDIDO se dedica SOLO a lo tuyo: tus encargos («investiga…», «pregúntate…»), el tema en que la
centraste y los temas que le mandaste estudiar. Si no queda nada tuyo, se queda quieta (no elige temas por su cuenta).

  es_orden(texto)        -> 'on' | 'off' | None
  encendido(dir) / encender(dir, si)
  apuntar_tema(dir, tema) / temas(dir)  (lo que le mandaste estudiar, lo último primero)
"""
import json
import os
import re
import time
import unicodedata

ARCHIVO = "solo_mio.json"
MAX_TEMAS = 60


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", t)
    return re.sub(r"\s+", " ", t).strip(" .!¡?¿")


_ON = re.compile(
    r"^(?:(?:estudia|piensa|investiga|centrate|dedicate)(?:\s+(?:y\s+piensa|en))?\s+)?"
    r"solo\s+(?:en\s+)?(?:lo\s+(?:que\s+(?:yo\s+)?te\s+(?:mande|mando|pida|pido|encargue|encargo)|mio|nuestro)|"
    r"mis\s+(?:temas|encargos|cosas))$|"
    r"^no\s+(?:estudies|pienses|investigues)\s+(?:nada\s+)?(?:por\s+tu\s+cuenta|lo\s+que\s+quieras|sola)$|"
    r"^(?:activa|enciende|pon)\s+(?:el\s+)?(?:modo\s+)?solo\s+lo\s+mio$")
_OFF = re.compile(
    r"^(?:(?:ya\s+)?puedes\s+)?(?:estudiar?|pensar|piensa|estudia|investiga|investigar)\s+(?:tambien\s+)?"
    r"(?:lo\s+que\s+quieras|por\s+tu\s+cuenta|libre(?:mente)?|sola)$|"
    r"^(?:vuelve\s+a\s+)?pensar?\s+libre$|^piensa\s+en\s+lo\s+que\s+quieras$|"
    r"^(?:desactiva|apaga|quita)\s+(?:el\s+)?(?:modo\s+)?solo\s+lo\s+mio$")


def es_orden(texto):
    t = _norm(texto)
    if _ON.match(t):
        return "on"
    if _OFF.match(t):
        return "off"
    return None


def _ruta(dir_):
    return os.path.join(str(dir_ or "."), ARCHIVO)


def _leer(dir_):
    try:
        with open(_ruta(dir_), encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            return {"on": bool(d.get("on")), "temas": [str(x) for x in d.get("temas", []) if str(x).strip()]}
    except (OSError, ValueError):
        pass
    return {"on": False, "temas": []}


def _guardar(dir_, d):
    ruta = _ruta(dir_)
    try:
        os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
        tmp = ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, ruta)
        os.chmod(ruta, 0o600)
    except OSError:
        pass


def encendido(dir_):
    return _leer(dir_)["on"]


def encender(dir_, si=True):
    d = _leer(dir_)
    d["on"] = bool(si)
    d["cuando"] = int(time.time())
    _guardar(dir_, d)
    return d["on"]


def apuntar_tema(dir_, tema):
    """Apunta un tema que le MANDASTE estudiar (para pensar sobre él aunque el interruptor esté encendido)."""
    tema = " ".join(str(tema or "").split())[:80]
    if len(tema) < 2:
        return False
    d = _leer(dir_)
    d["temas"] = [x for x in d["temas"] if _norm(x) != _norm(tema)] + [tema]
    d["temas"] = d["temas"][-MAX_TEMAS:]
    _guardar(dir_, d)
    return True


def temas(dir_):
    return list(reversed(_leer(dir_)["temas"]))


def texto_estado(dir_, encendido_=None):
    on = encendido(dir_) if encendido_ is None else encendido_
    if on:
        return ("[OK] Desde ahora estudio y pienso SOLO lo que tú me mandes: tus encargos, el tema en que me centres y "
                "lo que me pidas estudiar. Si no me queda nada tuyo, me quedo quieta esperando. Para volver a pensar "
                "por mi cuenta, dime «piensa libre».")
    return ("[OK] Vuelvo a pensar también por mi cuenta cuando no me mandes nada (lo tuyo sigue yendo primero). "
            "Para que solo haga lo tuyo, dime «estudia solo lo que yo te mande».")
