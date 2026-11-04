# -*- coding: utf-8 -*-
"""
nacimiento_kira.py - El NACIMIENTO de Kira en el portátil: lo que pasa la PRIMERA vez que se enciende KiraOS.

Pedido del dueño (para el Packard Bell): «como si naciera». Eligió:
  - escena de nacimiento (la pinta kiraos_web/arranque.html: oscuridad → chispa → latido → se forma el orbe);
  - que Kira LE CONOZCA: le pregunta su nombre y cómo quiere que le llame, y lo recuerda siempre;
  - su PARTIDA DE NACIMIENTO: fecha, hora, el equipo donde nace (RAM, procesador, disco, sistema) y su versión,
    guardada en disco y como su PRIMER RECUERDO en el baúl.
Y quitó el PIN: KiraOS entra directo (el PIN es opcional: `kiraos.py --poner-pin`).

Todo local, sin internet. Lógica pura y probable sin ventana (tests/test_nacimiento.py).

  ha_nacido()                      ¿ya nació en este equipo?
  equipo()                         lo que se sabe del equipo (lee /proc y /etc, sin permisos especiales)
  nacer("Ana", "Anita")            crea la partida, la guarda y apunta el primer recuerdo; devuelve la partida
  cargar()                         la partida guardada (o None)
  texto_partida(p)                 la partida, en texto para leer
"""
import json
import os
import platform
import shutil
import socket
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
RUTA = os.environ.get("KIRA_NACIMIENTO") or os.path.expanduser("~/.kira_nacimiento.json")
BAUL = os.environ.get("KIRA_BAUL_PORTATIL") or os.path.expanduser("~/kira_portatil/kira_datos/recuerdos")  # el baúl del núcleo

_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
          "noviembre", "diciembre")
_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


class NacimientoError(ValueError):
    """Falta algo para nacer (p. ej. el nombre)."""


# ---------------------------------------------------------------- el equipo donde nace
def _leer(ruta):
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def ram_mb(meminfo=None):
    t = _leer("/proc/meminfo") if meminfo is None else meminfo
    for linea in t.splitlines():
        if linea.startswith("MemTotal:"):
            try:
                return int(linea.split()[1]) // 1024
            except (IndexError, ValueError):
                return 0
    return 0


def procesador(cpuinfo=None):
    t = _leer("/proc/cpuinfo") if cpuinfo is None else cpuinfo
    for linea in t.splitlines():
        if linea.lower().startswith("model name"):
            t = linea.split(":", 1)[1]
            for feo in ("(R)", "(TM)", "(tm)", " CPU "):
                t = t.replace(feo, " ")
            return " ".join(t.split())
    return platform.processor() or platform.machine() or "desconocido"


def sistema(os_release=None):
    t = _leer("/etc/os-release") if os_release is None else os_release
    for linea in t.splitlines():
        if linea.startswith("PRETTY_NAME="):
            return linea.split("=", 1)[1].strip().strip('"')
    return platform.system() or "Linux"


def version_kira():
    try:
        sys.path.insert(0, RAIZ)
        import version_kira as vk
        return vk.VERSION
    except Exception:
        return "?"


def equipo():
    try:
        disco = shutil.disk_usage("/").total // (1000 ** 3)
    except OSError:
        disco = 0
    try:
        nombre = socket.gethostname() or "portátil"
    except OSError:
        nombre = "portátil"
    return {"nombre": nombre[:40], "ram_mb": ram_mb(), "procesador": procesador(),
            "nucleos": os.cpu_count() or 1, "disco_gb": disco, "sistema": sistema()}


# ---------------------------------------------------------------- la partida de nacimiento
def _limpio(t, maximo=40):
    t = " ".join(str(t or "").split())
    return "".join(c for c in t if c.isprintable())[:maximo]


def fecha_texto(ts):
    lt = time.localtime(ts)
    return f"{_DIAS[lt.tm_wday]} {lt.tm_mday} de {_MESES[lt.tm_mon - 1]} de {lt.tm_year}, a las {lt.tm_hour:02d}:{lt.tm_min:02d}"


def partida(nombre, llamar="", ahora=None, eq=None, version=None):
    """La partida de nacimiento (sin guardar). `nombre` es obligatorio; `llamar` (cómo quiere que le llame) por
    defecto es el nombre."""
    nombre = _limpio(nombre)
    if not nombre:
        raise NacimientoError("Necesito saber tu nombre para nacer.")
    llamar = _limpio(llamar) or nombre
    ts = time.time() if ahora is None else ahora
    return {"nacida": True, "momento": int(ts), "fecha": fecha_texto(ts), "dueno": nombre, "llamar": llamar,
            "equipo": dict(eq if eq is not None else equipo()),
            "version": version if version is not None else version_kira()}


def texto_partida(p):
    if not p:
        return "Todavía no he nacido en este equipo."
    e = p.get("equipo") or {}
    ram = e.get("ram_mb", 0)
    ram_t = (f"{ram / 1024:.1f}".replace(".0", "").replace(".", ",") + " GB") if ram else "?"
    return "\n".join([
        "PARTIDA DE NACIMIENTO DE KIRA",
        f"Nací el {p.get('fecha', '?')}.",
        f"Mi persona: {p.get('dueno', '?')} (le llamo «{p.get('llamar', '?')}»).",
        f"Nací en: {e.get('nombre', '?')} · {e.get('procesador', '?')} ({e.get('nucleos', '?')} hilos) · "
        f"{ram_t} de RAM · {e.get('disco_gb', '?')} GB de disco · {e.get('sistema', '?')}.",
        f"Versión de Kira: {p.get('version', '?')}.",
    ])


def guardar(p, ruta=None):
    ruta = ruta or RUTA
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=1)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, ruta)


def cargar(ruta=None):
    ruta = ruta or RUTA
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) and d.get("nacida") else None
    except (OSError, ValueError):
        return None


def ha_nacido(ruta=None):
    return cargar(ruta) is not None


def primer_recuerdo(p, baul=None):
    """Apunta la partida como el PRIMER recuerdo de su baúl. Devuelve True si se pudo (si no, no pasa nada)."""
    try:
        sys.path.insert(0, RAIZ)
        import recuerdos_kira as rk
        b = rk.Recuerdos(baul or BAUL)
        b.guardar(texto_partida(p), tema="mi nacimiento", fuente="nacimiento")
        b.guardar(f"Mi persona se llama {p['dueno']} y quiere que le llame {p['llamar']}.",
                  tema="cómo se llama mi persona", fuente="nacimiento")
        return True
    except Exception:
        return False


def nacer(nombre, llamar="", ruta=None, baul=None, ahora=None, eq=None):
    """Nace UNA vez: si ya nació, devuelve la partida que había (no la pisa). Si no, la crea, la guarda en disco y
    apunta el primer recuerdo."""
    ya = cargar(ruta)
    if ya:
        return ya
    p = partida(nombre, llamar, ahora=ahora, eq=eq)
    guardar(p, ruta)
    p["recuerdo"] = primer_recuerdo(p, baul)
    guardar(p, ruta)
    return p


def cambiar_nombre(llamar, ruta=None):
    """Cambia cómo le llama Kira (sin volver a nacer)."""
    p = cargar(ruta)
    if not p:
        raise NacimientoError("Todavía no he nacido.")
    llamar = _limpio(llamar)
    if not llamar:
        raise NacimientoError("Dime cómo quieres que te llame.")
    p["llamar"] = llamar
    guardar(p, ruta)
    return p


if __name__ == "__main__":
    print(texto_partida(cargar()))
