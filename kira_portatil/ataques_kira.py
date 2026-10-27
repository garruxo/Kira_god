# -*- coding: utf-8 -*-
"""
ataques_kira.py - Detecta intentos de ataque CONTRA tu portátil/red y apunta DE DÓNDE vienen (para el mapa). SOLO
DEFENSA: solo lee los registros del propio sistema, no toca ni ataca nada.

De dónde saca los ataques (lo que un equipo de casa ve de verdad):
  - /var/log/auth.log : intentos fallidos de entrar por SSH (fuerza bruta, usuarios inventados).
  - /var/log/ufw.log  : conexiones entrantes BLOQUEADAS por el cortafuegos (escaneos de puertos).

Por cada IP atacante, con geoip_kira averigua el país, el dueño (ASN) y si parece un particular o un centro de datos,
y lo guarda en `~/.kira_ataques.json` para pintarlo en el mapa del mundo. Solo librería estándar. Se prueba con
registros y geoip de mentira.
"""
import ipaddress
import json
import os
import re
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(os.path.expanduser("~"), ".kira_ataques.json")
LOGS = ("/var/log/auth.log", "/var/log/ufw.log")
MAX_IPS = 500

_IP = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
_RE_SSH = re.compile(r"(?:Failed password|Invalid user|authentication failure).*?from " + _IP, re.I)
_RE_UFW_SRC = re.compile(r"\[UFW BLOCK\].*?SRC=" + _IP, re.I)
_RE_DPT = re.compile(r"DPT=(\d+)", re.I)


def _externa(ip):
    try:
        return not ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def leer_auth(texto):
    """Intentos fallidos de SSH -> [{ip, tipo}]."""
    out = []
    for linea in texto.splitlines():
        m = _RE_SSH.search(linea)
        if m and _externa(m.group(1)):
            out.append({"ip": m.group(1), "tipo": "Intento de entrar por SSH (fuerza bruta)"})
    return out


def leer_ufw(texto):
    """Conexiones entrantes bloqueadas por el cortafuegos -> [{ip, tipo, puerto}]."""
    out = []
    for linea in texto.splitlines():
        m = _RE_UFW_SRC.search(linea)
        if m and _externa(m.group(1)):
            dpt = _RE_DPT.search(linea)
            out.append({"ip": m.group(1), "tipo": "Conexión bloqueada / escaneo de puertos",
                        "puerto": int(dpt.group(1)) if dpt else None})
    return out


def recolectar(rutas=None, leer=None):
    """Lee los registros del sistema y saca los ataques (IPs externas). `leer(ruta)` se inyecta en las pruebas."""
    rutas = rutas if rutas is not None else LOGS
    leer = leer or (lambda r: open(r, encoding="utf-8", errors="replace").read() if os.path.isfile(r) else "")
    eventos = []
    for r in rutas:
        try:
            texto = leer(r)
        except OSError:
            continue
        if "auth" in r:
            eventos += leer_auth(texto)
        elif "ufw" in r:
            eventos += leer_ufw(texto)
        else:
            eventos += leer_auth(texto) + leer_ufw(texto)
    return eventos


def _vacio():
    return {"ips": {}}


def cargar(ruta=None):
    try:
        with open(ruta or RUTA, encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("ips", {})
        return d
    except (OSError, ValueError):
        return _vacio()


def guardar(estado, ruta=None):
    ruta = ruta or RUTA
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False)
    os.replace(tmp, ruta)
    try:
        os.chmod(ruta, 0o600)
    except OSError:
        pass


def registrar(estado, eventos, geo=None, ahora=None):
    """Mete los ataques en el estado: agrupa por IP, cuenta, guarda tipos, y averigua país/dueño una vez por IP.
    Devuelve las IPs que son NUEVAS en esta pasada (para avisar)."""
    if geo is None:
        import geoip_kira as geo
    ahora = int(ahora if ahora is not None else time.time())
    nuevas = []
    for ev in eventos:
        ip = ev["ip"]
        reg = estado["ips"].get(ip)
        if reg is None:
            info = geo.informe(ip)
            reg = {"ip": ip, "veces": 0, "tipos": [], "primera": ahora, "ultima": ahora,
                   "pais": info["pais"], "pais_nombre": info["pais_nombre"], "org": info["org"],
                   "asn": info["asn"], "lat": info["lat"], "lon": info["lon"],
                   "infra": info["infra"]["texto"], "infra_clase": info["infra"]["clase"]}
            estado["ips"][ip] = reg
            nuevas.append(reg)
        reg["veces"] += 1
        reg["ultima"] = ahora
        if ev["tipo"] not in reg["tipos"]:
            reg["tipos"].append(ev["tipo"])
    # no crecer sin fin: deja las más recientes
    if len(estado["ips"]) > MAX_IPS:
        orden = sorted(estado["ips"].values(), key=lambda r: r["ultima"], reverse=True)[:MAX_IPS]
        estado["ips"] = {r["ip"]: r for r in orden}
    return nuevas


def mapa_datos(estado):
    """Lo que necesita el mapa: un punto por IP atacante, con su info. Los que no tienen país ubicado van igual en la
    lista (sin punto en el mapa)."""
    puntos = sorted(estado["ips"].values(), key=lambda r: r["veces"], reverse=True)
    return {"ataques": puntos, "total": len(puntos),
            "con_mapa": sum(1 for p in puntos if p.get("lat") is not None)}


def paso(ruta_estado=None, rutas_log=None, geo=None, leer=None, ahora=None):
    """Una pasada completa: lee los registros, apunta los ataques nuevos y guarda. Devuelve las IPs nuevas."""
    estado = cargar(ruta_estado)
    nuevas = registrar(estado, recolectar(rutas_log, leer=leer), geo=geo, ahora=ahora)
    guardar(estado, ruta_estado)
    return nuevas
