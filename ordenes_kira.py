# -*- coding: utf-8 -*-
"""
ordenes_kira.py - Las ÓRDENES que le das a Kira: historial y cola para KiraOS (v2.87). VA EN EL APK; puro.

Lo pidió el dueño: en el panel del móvil quiere ver «las órdenes que le he enviado a Kira app y a KiraOS» y qué está
haciendo cada una. Además, fuera de casa, la Kira del móvil solo piensa y estudia: los TRABAJOS (programar,
experimentar, juegos, apps, diseños, pintar, su máquina virtual, mejoras…) se APUNTAN para KiraOS y se le mandan
solos en cuanto el móvil vuelve a casa.

Cada orden: {id, texto, destino: 'movil'|'kiraos', estado, cuando, respuesta, tarea}
  estado: 'pendiente' (esperando a llegar a casa) · 'enviada' · 'en curso' · 'hecha' · 'error' · 'cancelada'
Se guarda en ordenes.json (en disco), con un tope para no crecer sin fin.
"""
import json
import os
import time
import uuid

ARCHIVO = "ordenes.json"
MAX = 300
ESTADOS = ("pendiente", "enviada", "en curso", "hecha", "error", "cancelada")


def _ruta(dir_):
    return os.path.join(dir_, ARCHIVO)


def _leer(dir_):
    try:
        with open(_ruta(dir_), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _guardar(dir_, lista):
    os.makedirs(dir_, exist_ok=True)
    tmp = _ruta(dir_) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(lista[-MAX:], f, ensure_ascii=False)
    os.replace(tmp, _ruta(dir_))


def ocultar_claves(texto):
    """v2.88: una orden que traía una clave («…con la clave X») se apunta SIN la clave."""
    import re
    return re.sub(r"(\b(?:clave|contrase(?:ñ|n)a|password|pass)\b\s*(?:es|:|=)?\s*)\S+", r"\1••••", texto, flags=re.I)


def apuntar(dir_, texto, destino="movil", estado="en curso", respuesta=""):
    """Apunta una orden. Devuelve su id."""
    if destino not in ("movil", "kiraos"):
        destino = "movil"
    if estado not in ESTADOS:
        estado = "en curso"
    o = {"id": uuid.uuid4().hex[:10], "texto": ocultar_claves(str(texto or ""))[:400], "destino": destino, "estado": estado,
         "cuando": int(time.time()), "respuesta": str(respuesta or "")[:600], "tarea": None}
    lista = _leer(dir_)
    lista.append(o)
    _guardar(dir_, lista)
    return o["id"]


def actualizar(dir_, id_, **cambios):
    lista = _leer(dir_)
    for o in lista:
        if o.get("id") == id_:
            for k, v in cambios.items():
                if k == "estado" and v not in ESTADOS:
                    continue
                if k == "respuesta":
                    v = str(v or "")[:600]
                o[k] = v
            o["cambio"] = int(time.time())
            _guardar(dir_, lista)
            return True
    return False


def cerrar_huerfanas(dir_):
    """Al abrir la app: las órdenes que se quedaron «en curso» sin tarea de KiraOS se cortaron al cerrarla."""
    lista, n = _leer(dir_), 0
    for o in lista:
        if o.get("estado") == "en curso" and not o.get("tarea"):
            o["estado"], o["respuesta"], n = "cancelada", (o.get("respuesta") or "Se cortó al cerrar la app."), n + 1
    if n:
        _guardar(dir_, lista)
    return n


def pendientes_kiraos(dir_):
    """Órdenes apuntadas para KiraOS que aún no se le han mandado (las más antiguas primero)."""
    return [o for o in _leer(dir_) if o.get("destino") == "kiraos" and o.get("estado") == "pendiente"]


def en_kiraos(dir_):
    """Órdenes mandadas a KiraOS que aún no han acabado (hay que preguntar cómo van)."""
    return [o for o in _leer(dir_) if o.get("destino") == "kiraos" and o.get("estado") in ("enviada", "en curso")
            and o.get("tarea")]


def ultimas(dir_, n=20):
    return list(reversed(_leer(dir_)[-n:]))


def cuenta(dir_):
    c = {e: 0 for e in ESTADOS}
    for o in _leer(dir_):
        c[o.get("estado", "hecha")] = c.get(o.get("estado", "hecha"), 0) + 1
    return c


_ICONO = {"pendiente": "⏳", "enviada": "→", "en curso": "…", "hecha": "✓", "error": "✗", "cancelada": "■"}


def texto_ultimas(dir_, n=10):
    lista = ultimas(dir_, n)
    if not lista:
        return "Todavía no me has dado órdenes."
    filas = []
    for o in lista:
        donde = "KiraOS" if o.get("destino") == "kiraos" else "móvil"
        h = time.strftime("%d/%m %H:%M", time.localtime(o.get("cuando", 0)))
        linea = f"{_ICONO.get(o.get('estado'), '·')} [{donde}] {h} — {o.get('texto', '')[:70]}"
        if o.get("estado") == "pendiente":
            linea += " (la hará KiraOS al llegar a casa)"
        elif o.get("respuesta") and o.get("estado") in ("hecha", "error"):
            linea += "\n    " + o["respuesta"].replace("\n", " ")[:140]
        filas.append(linea)
    return "\n".join(filas)
