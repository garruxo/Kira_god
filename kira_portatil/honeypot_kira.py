# -*- coding: utf-8 -*-
"""
honeypot_kira.py - El CEBO (honeypot) de Kira: un sensor de la comunidad de ciberseguridad. SOLO DEFENSA.

Qué es: Kira abre unos puertos "señuelo" que fingen ser servicios jugosos (SSH, Telnet, web…). Nadie legítimo se
conecta ahí, así que TODO lo que llega es, casi seguro, alguien rastreando o atacando. El cebo APUNTA quién se
conecta (IP, puerto, qué banner pidió, qué usuario/clave intentó) y lo guarda. Con miles de sensores así por el
mundo, la comunidad ve una oleada nueva de ataques antes de que llegue a todos (idea de DShield / SANS ISC).

BLINDAJE (candado de verdad, esto NO es ofensivo):
  - El cebo SOLO ESCUCHA y apunta. Nunca se conecta a nadie, nunca ejecuta ni "contesta de verdad" lo que recibe,
    nunca manda los datos a ningún sitio (eso sería un paso aparte, con TU cuenta, y no está hecho).
  - Lee como mucho MAX_BYTES por conexión y guarda una muestra corta; no se traga ficheros ni se llena el disco.
  - Límite de IPs y de muestras por IP; cierra cada conexión enseguida.

Solo librería estándar. La parte que apunta (registrar/resumen/informe) es pura y se prueba; la parte de red
(Sensor) se prueba con sockets de verdad en localhost.
"""
import ipaddress
import json
import os
import socket
import threading
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(os.path.expanduser("~"), ".kira_honeypot.json")

MAX_BYTES = 512          # lo máximo que leemos de cada conexión (no nos tragamos nada grande)
MAX_IPS = 1000           # no crecer sin fin
MAX_MUESTRAS = 5         # muestras guardadas por IP
TIEMPO_LECTURA = 3.0     # segundos que esperamos a que el atacante "hable"

# Puertos señuelo por defecto (ALTOS, no hacen falta permisos de root). Los clásicos 22/23/3389 necesitan root o
# redirección; se pueden pasar a mano. Cada uno finge un servicio y manda un banner creíble.
SENUELOS = {
    2222: ("SSH", b"SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.4\r\n"),
    2323: ("Telnet", b"\r\nUbuntu 22.04.3 LTS\r\nlogin: "),
    8080: ("HTTP", b"HTTP/1.1 401 Unauthorized\r\nWWW-Authenticate: Basic realm=\"router\"\r\n\r\n"),
    8023: ("Telnet", b"\r\nlogin: "),
    5900: ("VNC", b"RFB 003.008\n"),
}


def servicio_de(puerto):
    """Nombre del servicio que finge ese puerto (para el informe)."""
    if puerto in SENUELOS:
        return SENUELOS[puerto][0]
    return {22: "SSH", 23: "Telnet", 21: "FTP", 25: "SMTP", 80: "HTTP", 443: "HTTPS",
            3389: "RDP", 445: "SMB", 3306: "MySQL"}.get(puerto, "desconocido")


def _externa(ip):
    try:
        return not ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def _muestra_legible(datos):
    """Convierte los bytes recibidos en algo corto y legible para apuntar (sin reventar la pantalla)."""
    if not datos:
        return ""
    txt = datos.decode("utf-8", "replace").strip()
    txt = "".join(c if (c.isprintable() or c == " ") else "." for c in txt)
    return txt[:120]


def credenciales_de(datos):
    """Intenta sacar usuario/clave que el atacante probó (lo más valioso del cebo). Mira líneas tipo
    'user: root' / 'password=1234' y, si no, las dos primeras líneas sueltas (login/clave de un telnet)."""
    txt = datos.decode("utf-8", "replace")
    lineas = [l.strip() for l in txt.replace("\r", "\n").split("\n") if l.strip()]
    usuario = clave = ""
    for l in lineas:
        bajo = l.lower()
        for etiqueta in ("user", "usuario", "login"):
            if bajo.startswith(etiqueta):
                usuario = l.split(":", 1)[-1].split("=", 1)[-1].strip()[:40]
        for etiqueta in ("pass", "clave", "contrase"):
            if bajo.startswith(etiqueta):
                clave = l.split(":", 1)[-1].split("=", 1)[-1].strip()[:40]
    if not usuario and not clave and len(lineas) >= 1:
        usuario = lineas[0][:40]
        if len(lineas) >= 2:
            clave = lineas[1][:40]
    return usuario, clave


# ---------------------------------------------------------------------------
#  Estado: apuntar lo que llega (parte PURA, se prueba sin red)
# ---------------------------------------------------------------------------
def _vacio():
    return {"ips": {}, "total": 0, "desde": int(time.time())}


def cargar(ruta=None):
    try:
        with open(ruta or RUTA, encoding="utf-8") as f:
            d = json.load(f)
        d.setdefault("ips", {})
        d.setdefault("total", 0)
        d.setdefault("desde", int(time.time()))
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


def registrar(estado, ev, geo=None, ahora=None):
    """Apunta un toque del cebo. ev = {ip, puerto, servicio, muestra, usuario, clave}. Solo IPs EXTERNAS cuentan
    como 'de fuera' (las de tu red se apuntan igual, marcadas como locales). Devuelve el registro de esa IP y si
    la IP era NUEVA (para avisar)."""
    ahora = int(ahora if ahora is not None else time.time())
    ip = ev.get("ip", "")
    estado["total"] = estado.get("total", 0) + 1
    reg = estado["ips"].get(ip)
    nueva = reg is None
    if nueva:
        info = {"pais": None, "pais_nombre": "", "org": "", "asn": None, "lat": None, "lon": None,
                "infra": "", "infra_clase": ""}
        if _externa(ip):
            if geo is None:
                try:
                    import geoip_kira as geo
                except Exception:
                    geo = None
            if geo is not None:
                try:
                    g = geo.informe(ip)
                    info = {"pais": g["pais"], "pais_nombre": g["pais_nombre"], "org": g["org"],
                            "asn": g["asn"], "lat": g["lat"], "lon": g["lon"],
                            "infra": g["infra"]["texto"], "infra_clase": g["infra"]["clase"]}
                except Exception:
                    pass
        reg = {"ip": ip, "externa": _externa(ip), "veces": 0, "puertos": [], "servicios": [],
               "primera": ahora, "ultima": ahora, "muestras": [], "credenciales": [], **info}
        estado["ips"][ip] = reg
    reg["veces"] += 1
    reg["ultima"] = ahora
    p = ev.get("puerto")
    if p is not None and p not in reg["puertos"]:
        reg["puertos"].append(p)
    serv = ev.get("servicio") or servicio_de(p or 0)
    if serv and serv not in reg["servicios"]:
        reg["servicios"].append(serv)
    muestra = (ev.get("muestra") or "").strip()
    if muestra and muestra not in reg["muestras"] and len(reg["muestras"]) < MAX_MUESTRAS:
        reg["muestras"].append(muestra)
    u, c = ev.get("usuario", ""), ev.get("clave", "")
    if (u or c):
        par = {"usuario": u, "clave": c}
        if par not in reg["credenciales"] and len(reg["credenciales"]) < MAX_MUESTRAS:
            reg["credenciales"].append(par)
    if len(estado["ips"]) > MAX_IPS:
        orden = sorted(estado["ips"].values(), key=lambda r: r["ultima"], reverse=True)[:MAX_IPS]
        estado["ips"] = {r["ip"]: r for r in orden}
    return reg, nueva


def resumen(estado):
    """Texto corto para Kira: cuántos toques, cuántas IPs, los puertos más buscados y las claves más probadas."""
    ips = estado.get("ips", {})
    if not ips:
        return "El cebo está puesto pero aún no ha picado nadie. (Es buena señal… o es que todavía nadie lo ve.)"
    externas = [r for r in ips.values() if r.get("externa")]
    puertos = {}
    claves = {}
    for r in ips.values():
        for p in r.get("puertos", []):
            puertos[p] = puertos.get(p, 0) + r["veces"]
        for par in r.get("credenciales", []):
            k = (par.get("usuario", ""), par.get("clave", ""))
            if any(k):
                claves[k] = claves.get(k, 0) + 1
    top_p = sorted(puertos.items(), key=lambda x: -x[1])[:5]
    top_c = sorted(claves.items(), key=lambda x: -x[1])[:5]
    partes = [f"El cebo ha registrado {estado.get('total', 0)} toque(s) de {len(ips)} IP(s) "
              f"({len(externas)} de fuera de tu red)."]
    if top_p:
        partes.append("Puertos más buscados: " + ", ".join(f"{p} ({servicio_de(p)}) x{n}" for p, n in top_p) + ".")
    if top_c:
        partes.append("Usuario/clave más probados: " + ", ".join(
            f"{u or '-'}/{c or '-'} x{n}" for (u, c), n in top_c) + ".")
    partes.append("Recuerda: esto SOLO observa; no ataca a nadie ni envía nada fuera.")
    return " ".join(partes)


def informe_comunidad(estado):
    """Lo que un analista compartiría con la comunidad (sin enviarlo: eso lo decides tú, con tu cuenta). Una línea por
    IP externa: IP, veces, puertos, país y dueño. Pensado para listas tipo AbuseIPDB / feeds de la comunidad."""
    filas = []
    for r in sorted(estado.get("ips", {}).values(), key=lambda r: r["veces"], reverse=True):
        if not r.get("externa"):
            continue
        filas.append({"ip": r["ip"], "veces": r["veces"], "puertos": r.get("puertos", []),
                      "servicios": r.get("servicios", []), "pais": r.get("pais"),
                      "org": r.get("org", ""), "primera": r.get("primera"), "ultima": r.get("ultima")})
    return {"fuente": "honeypot Kira (baja interacción)", "total_ips": len(filas), "ips": filas,
            "aviso": "Origen APARENTE (puede ser VPN/proxy/bot). Compartir es decisión del dueño."}


# ---------------------------------------------------------------------------
#  Sensor: la parte de RED (abre los puertos señuelo y apunta lo que llega)
# ---------------------------------------------------------------------------
class Sensor:
    """Abre los puertos señuelo y, por cada conexión, apunta quién fue y qué intentó. Un hilo por puerto.
    `al_evento(ev, nueva)` se llama con cada toque (para avisar/guardar). `host='0.0.0.0'` escucha en toda la red
    del portátil; en pruebas se usa '127.0.0.1' y puerto 0 (el sistema elige uno libre)."""

    def __init__(self, senuelos=None, host="0.0.0.0", al_evento=None, ruta_estado=None, geo=None):
        self.senuelos = dict(senuelos if senuelos is not None else SENUELOS)
        self.host = host
        self.al_evento = al_evento
        self.ruta_estado = ruta_estado
        self.geo = geo
        self._socks = []
        self._hilos = []
        self._parar = threading.Event()
        self._lock = threading.Lock()
        self.puertos_reales = {}      # puerto pedido -> puerto real (por si fue 0 en pruebas)

    def _apuntar(self, ev):
        """Guarda el evento en el estado y llama a al_evento. Serializado con un lock."""
        with self._lock:
            estado = cargar(self.ruta_estado)
            reg, nueva = registrar(estado, ev, geo=self.geo)
            guardar(estado, self.ruta_estado)
        if self.al_evento:
            try:
                self.al_evento(ev, nueva)
            except Exception:
                pass

    def _atender(self, conn, addr, puerto_pedido, puerto_real):
        try:
            conn.settimeout(TIEMPO_LECTURA)
            serv, banner = self.senuelos.get(puerto_pedido, ("desconocido", b""))
            if banner:
                try:
                    conn.sendall(banner)      # un banner creíble para que el atacante "hable"; NO es un servicio real
                except OSError:
                    pass
            datos = b""
            try:
                while len(datos) < MAX_BYTES:
                    trozo = conn.recv(MAX_BYTES - len(datos))
                    if not trozo:
                        break
                    datos += trozo
            except (OSError, socket.timeout):
                pass
            u, c = credenciales_de(datos)
            ev = {"ip": addr[0], "puerto": puerto_real, "servicio": serv,
                  "muestra": _muestra_legible(datos), "usuario": u, "clave": c, "cuando": int(time.time())}
            self._apuntar(ev)
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _escuchar_puerto(self, puerto):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, puerto))
            s.listen(16)
            s.settimeout(0.5)
        except OSError:
            return
        with self._lock:
            self._socks.append(s)
            self.puertos_reales[puerto] = s.getsockname()[1]
        while not self._parar.is_set():
            try:
                conn, addr = s.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._atender,
                             args=(conn, addr, puerto, self.puertos_reales.get(puerto, puerto)),
                             daemon=True).start()

    def iniciar(self):
        self._parar.clear()
        for puerto in self.senuelos:
            h = threading.Thread(target=self._escuchar_puerto, args=(puerto,), daemon=True)
            h.start()
            self._hilos.append(h)
        # dar un instante a que los bind ocurran (útil en pruebas con puerto 0)
        for _ in range(50):
            if len(self.puertos_reales) >= len(self.senuelos):
                break
            time.sleep(0.01)
        return self.puertos_reales

    def detener(self):
        self._parar.set()
        with self._lock:
            socks = list(self._socks)
            self._socks = []
        for s in socks:
            try:
                s.close()
            except OSError:
                pass


def ip_local():
    """La IP PRIVADA de este portátil en su red local (para el modo seguro de casa). No manda nada a internet:
    solo le pregunta al sistema qué IP usaría de salida. Si no es privada o no se sabe, devuelve None."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))      # truco: NO envía paquetes, solo fija la IP de salida
            ip = s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None
    try:
        if ipaddress.ip_address(ip).is_private:
            return ip
    except ValueError:
        pass
    return None


def host_para(solo_casa, host="0.0.0.0"):
    """Decide en qué dirección escuchar. Pura y testeable. En modo seguro de casa NUNCA devuelve 0.0.0.0:
      - si encuentro mi IP de red local, escucho SOLO ahí (nada de fuera de tu red llega);
      - si no la encuentro, escucho SOLO en 127.0.0.1 (solo este portátil: lo más cerrado posible)."""
    if not solo_casa:
        return host, "TODA la red del portátil (0.0.0.0)"
    ip = ip_local()
    if ip:
        return ip, f"SOLO TU RED LOCAL (escucho únicamente en {ip}; nada de fuera de tu red llega al cebo)"
    return "127.0.0.1", "SOLO ESTE PORTÁTIL (no encontré tu IP de red; escucho solo en 127.0.0.1, lo más cerrado)"


def _al_mapa(ev):
    """Puente opcional: un toque del cebo de una IP EXTERNA se apunta también en `ataques_kira`, para que salga en
    el mapa del mundo que ya existe. Si algo falla, no pasa nada (el cebo sigue a lo suyo)."""
    if not _externa(ev.get("ip", "")):
        return
    try:
        import ataques_kira as at
        est = at.cargar()
        at.registrar(est, [{"ip": ev["ip"], "tipo": f"Cebo: intento contra {ev.get('servicio', '?')}",
                            "puerto": ev.get("puerto")}])
        at.guardar(est)
    except Exception:
        pass


def escuchar(puertos=None, host="0.0.0.0", solo_casa=False, ruta_estado=None):
    """Arranca el cebo y se queda escuchando hasta Ctrl+C. Para el servicio del sistema y para '--escuchar'.
    solo_casa=True: modo seguro de casa (escucha solo en tu red local, nunca hacia fuera)."""
    senuelos = SENUELOS if not puertos else {p: SENUELOS.get(p, (servicio_de(p), b"\r\n")) for p in puertos}
    host, modo = host_para(solo_casa, host)

    def aviso(ev, nueva):
        _al_mapa(ev)
        marca = " [IP NUEVA]" if nueva else ""
        print(f"[cebo] {ev['ip']}:{ev['puerto']} ({ev['servicio']}){marca} "
              f"{('user=' + ev['usuario']) if ev.get('usuario') else ''} "
              f"{('pass=' + ev['clave']) if ev.get('clave') else ''}".rstrip(), flush=True)

    sensor = Sensor(senuelos=senuelos, host=host, al_evento=aviso, ruta_estado=ruta_estado)
    reales = sensor.iniciar()
    print("Cebo de Kira ESCUCHANDO (solo observa; no ataca ni envía nada fuera).", flush=True)
    print("Modo:", modo, flush=True)
    print("Puertos señuelo:", ", ".join(f"{p}→{servicio_de(p)}" for p in reales), flush=True)
    if not solo_casa:
        print("AVISO: en este modo abres puertos a toda tu red. Para que lleguen ataques de internet tendrías que "
              "redirigir esos puertos en tu router (y asúmelo con cuidado). Usa --solo-casa para lo más seguro. "
              "Ctrl+C para parar.", flush=True)
    else:
        print("(Modo seguro de casa: nada de fuera de tu red local llega aquí.) Ctrl+C para parar.", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        sensor.detener()
        print("\nCebo parado.", flush=True)


def _cli(argv):
    import argparse
    p = argparse.ArgumentParser(description="Cebo (honeypot) DEFENSIVO de Kira: observa quién intenta atacar.")
    p.add_argument("--escuchar", action="store_true", help="arranca el cebo y escucha")
    p.add_argument("--estado", action="store_true", help="enseña lo que ha picado hasta ahora")
    p.add_argument("--informe", action="store_true", help="informe para la comunidad (no lo envía)")
    p.add_argument("--host", default="0.0.0.0", help="en qué dirección escuchar (por defecto, toda tu red)")
    p.add_argument("--solo-casa", action="store_true", dest="solo_casa",
                   help="modo seguro: escucha SOLO en tu red local, nunca hacia fuera")
    p.add_argument("--puertos", default="", help="puertos señuelo separados por comas (por defecto, los de serie)")
    a = p.parse_args(argv)
    if a.estado:
        print(resumen(cargar()))
        return 0
    if a.informe:
        print(json.dumps(informe_comunidad(cargar()), ensure_ascii=False, indent=2))
        return 0
    puertos = [int(x) for x in a.puertos.split(",") if x.strip().isdigit()] if a.puertos else None
    escuchar(puertos=puertos, host=a.host, solo_casa=a.solo_casa)
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_cli(sys.argv[1:]))
