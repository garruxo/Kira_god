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


MAX_EVENTOS = 300

# v2.96: qué servicio busca cada puerto (para el mapa: «lo que buscan en ti»)
SERVICIOS = {21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns", 80: "http", 110: "pop3", 123: "ntp",
             135: "rpc", 137: "netbios", 138: "netbios", 139: "netbios", 143: "imap", 161: "snmp", 443: "https",
             445: "smb", 993: "imaps", 1433: "ms-sql", 1723: "pptp", 1900: "upnp", 2222: "ssh", 2323: "telnet",
             3306: "mysql", 3389: "escritorio remoto", 5060: "sip", 5432: "postgres", 5555: "adb", 5900: "vnc",
             6379: "redis", 7547: "router (tr-069)", 8023: "telnet", 8080: "http", 8443: "https", 8888: "http",
             9200: "elasticsearch", 27017: "mongodb"}


def servicio_de(puerto):
    try:
        return SERVICIOS.get(int(puerto), f"puerto {int(puerto)}")
    except (TypeError, ValueError):
        return "desconocido"


def clase_de(tipo):
    """Tipo corto para el mapa: fuerza bruta, escaneo o cebo."""
    t = str(tipo or "").lower()
    if t.startswith("cebo"):
        return "cebo"
    if "ssh" in t or "fuerza" in t:
        return "fuerza bruta"
    return "escaneo"


_MESES = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov",
                                       "dec"), 1)}
_RE_ISO = re.compile(r"^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(?:\.\d+)?([+-]\d\d:?\d\d|Z)?")
_RE_CLASICA = re.compile(r"^([A-Z][a-z]{2})\s+(\d{1,2})\s(\d\d):(\d\d):(\d\d)")


def hora_de(linea, ahora=None):
    """La hora del registro (ISO de Ubuntu 24.04 o la clásica «Nov  7 18:05:01»). Si no se entiende, None."""
    import calendar
    import datetime as dt
    m = _RE_ISO.match(linea)
    if m:
        y, mo, d, h, mi, se, zona = m.groups()
        try:
            t = dt.datetime(int(y), int(mo), int(d), int(h), int(mi), int(se))
            if zona and zona != "Z":
                signo = 1 if zona[0] == "+" else -1
                zz = zona[1:].replace(":", "")
                t -= signo * dt.timedelta(hours=int(zz[:2]), minutes=int(zz[2:]))
            return calendar.timegm(t.timetuple())
        except ValueError:
            return None
    m = _RE_CLASICA.match(linea)
    if m:
        mes = _MESES.get(m.group(1).lower())
        if not mes:
            return None
        ahora = ahora if ahora is not None else time.time()
        y = time.localtime(ahora).tm_year
        try:
            t = time.mktime((y, mes, int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), 0, 0, -1))
        except (OverflowError, ValueError):
            return None
        return int(t - 365 * 86400) if t > ahora + 86400 else int(t)      # «Dec 31» leído en enero
    return None


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
            out.append({"ip": m.group(1), "tipo": "Intento de entrar por SSH (fuerza bruta)", "puerto": 22,
                        "t": hora_de(linea)})
    return out


def leer_ufw(texto):
    """Conexiones entrantes bloqueadas por el cortafuegos -> [{ip, tipo, puerto}]."""
    out = []
    for linea in texto.splitlines():
        m = _RE_UFW_SRC.search(linea)
        if m and _externa(m.group(1)):
            dpt = _RE_DPT.search(linea)
            out.append({"ip": m.group(1), "tipo": "Conexión bloqueada / escaneo de puertos",
                        "puerto": int(dpt.group(1)) if dpt else None, "t": hora_de(linea)})
    return out


def leer_nuevo(ruta, marcas):
    """v2.96: lee SOLO lo que se ha escrito desde la última vez (antes releía el registro entero en cada pasada y
    contaba los mismos ataques una y otra vez). `marcas[ruta]` = {ino, pos}; si el registro rotó o encogió, empieza
    de nuevo. La primera vez lee como mucho el último 1 MB."""
    if not os.path.isfile(ruta):
        return ""
    st = os.stat(ruta)
    m = marcas.get(ruta) or {}
    pos = m.get("pos", 0) if m.get("ino") == st.st_ino and m.get("pos", 0) <= st.st_size else 0
    if not m and st.st_size > (1 << 20):
        pos = st.st_size - (1 << 20)
    with open(ruta, "rb") as f:
        f.seek(pos)
        datos = f.read(8 << 20)
    corte = datos.rfind(b"\n") + 1                      # solo líneas completas
    marcas[ruta] = {"ino": st.st_ino, "pos": pos + corte}
    return datos[:corte].decode("utf-8", "replace")


def recolectar(rutas=None, leer=None, marcas=None):
    """Lee los registros del sistema y saca los ataques (IPs externas). `leer(ruta)` se inyecta en las pruebas; con
    `marcas` (y sin `leer`) solo lee lo nuevo."""
    rutas = rutas if rutas is not None else LOGS
    if leer is None and marcas is not None:
        leer = lambda r: leer_nuevo(r, marcas)              # noqa: E731
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
    return {"ips": {}, "eventos": [], "marcas": {}}


def cargar(ruta=None):
    try:
        with open(ruta or RUTA, encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("ips", {})
        d.setdefault("eventos", [])
        d.setdefault("marcas", {})
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
        cuando = int(ev.get("t") or ahora)
        reg["veces"] += 1
        reg["ultima"] = max(reg.get("ultima", 0), cuando)
        if ev["tipo"] not in reg["tipos"]:
            reg["tipos"].append(ev["tipo"])
        p = ev.get("puerto")
        reg.setdefault("puertos", [])
        if p is not None and p not in reg["puertos"]:
            reg["puertos"] = (reg["puertos"] + [p])[-20:]
        estado.setdefault("eventos", []).append({
            "t": cuando, "ip": ip, "puerto": p, "servicio": servicio_de(p) if p is not None else "desconocido",
            "tipo": ev["tipo"], "clase": clase_de(ev["tipo"]), "pais": reg["pais"], "pais_nombre": reg["pais_nombre"],
            "org": reg["org"], "lat": reg["lat"], "lon": reg["lon"], "infra_clase": reg["infra_clase"]})
    estado["eventos"] = sorted(estado.get("eventos", []), key=lambda e: e["t"])[-MAX_EVENTOS:]
    # no crecer sin fin: deja las más recientes
    if len(estado["ips"]) > MAX_IPS:
        orden = sorted(estado["ips"].values(), key=lambda r: r["ultima"], reverse=True)[:MAX_IPS]
        estado["ips"] = {r["ip"]: r for r in orden}
    return nuevas


def mapa_datos(estado):
    """Lo que necesita el mapa: un punto por IP atacante, con su info. Los que no tienen país ubicado van igual en la
    lista (sin punto en el mapa)."""
    puntos = sorted(estado["ips"].values(), key=lambda r: r["veces"], reverse=True)
    eventos = sorted(estado.get("eventos", []), key=lambda e: e["t"])[-150:]
    origenes, servicios, clases = {}, {}, {}
    for r in puntos:                                    # países: todas las veces de cada IP
        k = r.get("pais") or "??"
        o = origenes.setdefault(k, {"pais": k, "nombre": r.get("pais_nombre") or "desconocido", "veces": 0, "ips": 0})
        o["veces"] += r.get("veces", 1)
        o["ips"] += 1
    for e in estado.get("eventos", []):                  # servicios y tipos: de los ataques apuntados uno a uno
        if e.get("puerto") is not None:
            sv = servicios.setdefault(e["puerto"], {"puerto": e["puerto"], "servicio": e["servicio"], "veces": 0})
            sv["veces"] += 1
        clases[e.get("clase", "escaneo")] = clases.get(e.get("clase", "escaneo"), 0) + 1
    return {"ataques": puntos, "total": len(puntos),
            "con_mapa": sum(1 for p in puntos if p.get("lat") is not None),
            "eventos": eventos,
            "origenes": sorted(origenes.values(), key=lambda o: o["veces"], reverse=True)[:12],
            "servicios": sorted(servicios.values(), key=lambda o: o["veces"], reverse=True)[:10],
            "clases": [{"clase": k, "veces": v} for k, v in sorted(clases.items(), key=lambda kv: -kv[1])],
            "objetivo": objetivo()}


_ZONAS = {"Europe/Madrid": "ES", "Atlantic/Canary": "ES", "Africa/Ceuta": "ES", "Europe/Lisbon": "PT",
          "Europe/Paris": "FR", "Europe/London": "GB", "Europe/Berlin": "DE", "Europe/Rome": "IT",
          "America/Mexico_City": "MX", "America/Bogota": "CO", "America/Argentina/Buenos_Aires": "AR",
          "America/Santiago": "CL", "America/Lima": "PE", "America/New_York": "US", "America/Los_Angeles": "US"}


def objetivo(pais=None):
    """Dónde está TU portátil (el destino de las líneas del mapa): por país (KIRA_PAIS o la zona horaria del
    sistema). Solo el país, nunca tu dirección."""
    pais = (pais or os.environ.get("KIRA_PAIS") or "").upper()
    if not pais:
        zona = ""
        try:
            zona = open("/etc/timezone", encoding="utf-8").read().strip()
        except OSError:
            try:
                zona = os.path.realpath("/etc/localtime").split("zoneinfo/")[-1]
            except OSError:
                zona = ""
        pais = _ZONAS.get(zona, "ES")
    try:
        import geoip_kira as geo
        c = geo.CENTROS.get(pais)
    except Exception:
        c = None
    lat, lon, nombre = c if c else (40.2, -3.7, "España")
    return {"pais": pais, "nombre": nombre, "lat": lat, "lon": lon, "texto": "Tu portátil (" + nombre + ")"}


def paso(ruta_estado=None, rutas_log=None, geo=None, leer=None, ahora=None):
    """Una pasada completa: lee los registros, apunta los ataques nuevos y guarda. Devuelve las IPs nuevas."""
    estado = cargar(ruta_estado)
    nuevas = registrar(estado, recolectar(rutas_log, leer=leer, marcas=estado.setdefault("marcas", {})),
                       geo=geo, ahora=ahora)
    guardar(estado, ruta_estado)
    return nuevas
