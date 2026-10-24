# -*- coding: utf-8 -*-
"""
red_defensa_kira.py - Vigilancia DEFENSIVA de TU red de casa, para el cerebro de casa (portátil). SOLO DEFENSA.

Usa Nmap y Wireshark (tshark) para que Kira pueda:
  - inventario():  ver qué aparatos hay conectados a tu red (los que no reconozcas, ojo).
  - puertos(host): ver qué puertos tiene abierto UNO de tus aparatos (puertas que podrían estar de más).
  - trafico(seg):  mirar un rato el tráfico de tu red y resumir quién habla con quién (patrones raros).

CANDADO DE VERDAD (no es solo una nota): todo se limita a TU red local privada. `en_mi_red(host)` comprueba que el
objetivo está en una de las subredes privadas de ESTE portátil; cualquier otra cosa (una IP de internet, la red del
vecino) se RECHAZA con error. No hay forma de pedirle a esta herramienta que ataque ni que escanee fuera de tu red:
Nmap se usa solo para descubrir y ver puertos (sin exploits), y tshark solo para mirar, nunca para inyectar.

Solo librería estándar (llama a nmap/tshark por consola). Se prueba con un «correr» de mentira (sin red real).
"""
import ipaddress
import re
import shutil
import socket
import subprocess


class DefensaError(RuntimeError):
    pass


# =====================================================================================
#  ¿QUÉ ES «MI RED»? (y el candado)
# =====================================================================================
def _ips_locales():
    """Las IPv4 privadas de este portátil (la de la WiFi de casa, etc.)."""
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
        finally:
            s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    out = []
    for ip in ips:
        try:
            a = ipaddress.ip_address(ip)
            if a.is_private and not a.is_loopback and not a.is_link_local:
                out.append(str(a))
        except ValueError:
            continue
    return sorted(out)


def mis_subredes():
    """Las redes /24 privadas a las que está conectado este portátil (p. ej. 192.168.1.0/24)."""
    redes = []
    for ip in _ips_locales():
        try:
            redes.append(ipaddress.ip_network(ip + "/24", strict=False))
        except ValueError:
            continue
    return redes


def en_mi_red(host):
    """True solo si 'host' es una IP de TU red local (una de las subredes privadas de este portátil)."""
    try:
        a = ipaddress.ip_address(str(host).strip())
    except ValueError:
        return False
    if not a.is_private:
        return False
    return any(a in red for red in mis_subredes())


def _exigir_mi_red(host):
    if not en_mi_red(host):
        raise DefensaError(f"«{host}» no está en tu red de casa. Esto es solo para vigilar y proteger TU red: no "
                           "escaneo nada de fuera.")


def _hay(programa):
    return shutil.which(programa) is not None


# =====================================================================================
#  NMAP (descubrir aparatos y ver puertos) — SIN exploits
# =====================================================================================
def inventario(correr=subprocess.run, timeout=180):
    """Los aparatos conectados a tu red. [{'ip', 'nombre', 'mac'}]. Lanza DefensaError."""
    if not _hay("nmap"):
        raise DefensaError("Falta Nmap. Instálalo en el portátil: sudo apt install nmap")
    redes = mis_subredes()
    if not redes:
        raise DefensaError("No veo ninguna red de casa (¿el portátil está conectado a la WiFi?).")
    aparatos = {}
    for red in redes:
        try:
            r = correr(["nmap", "-sn", "-R", str(red)], capture_output=True, text=True,
                       timeout=timeout)
        except (OSError, subprocess.SubprocessError) as e:
            raise DefensaError(f"No pude ejecutar Nmap: {e}")
        aparatos.update(_parsear_inventario(r.stdout or ""))
    return [aparatos[k] for k in sorted(aparatos)]


def _parsear_inventario(salida):
    """Saca de la salida de «nmap -sn» los aparatos: ip, nombre (si lo hay) y MAC (si la hay)."""
    out = {}
    ip = None
    for linea in salida.splitlines():
        m = re.search(r"Nmap scan report for (?:([^\s(]+) )?\(?(\d+\.\d+\.\d+\.\d+)\)?", linea)
        if m:
            ip = m.group(2)
            out[ip] = {"ip": ip, "nombre": m.group(1) or "", "mac": "", "fabricante": ""}
            continue
        m = re.search(r"MAC Address: ([0-9A-Fa-f:]{17})\s*(?:\(([^)]*)\))?", linea)
        if m and ip:
            out[ip]["mac"] = m.group(1)
            out[ip]["fabricante"] = (m.group(2) or "").strip()
    return out


def puertos(host, correr=subprocess.run, timeout=180):
    """Los puertos abiertos de UNO de tus aparatos. {'host', 'abiertos': [{'puerto','servicio'}]}. Solo tu red."""
    _exigir_mi_red(host)
    if not _hay("nmap"):
        raise DefensaError("Falta Nmap. Instálalo en el portátil: sudo apt install nmap")
    try:
        r = correr(["nmap", "-F", "-T4", str(host)], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        raise DefensaError(f"No pude ejecutar Nmap: {e}")
    abiertos = []
    for linea in (r.stdout or "").splitlines():
        m = re.match(r"(\d+)/tcp\s+open\s+(\S+)", linea.strip())
        if m:
            abiertos.append({"puerto": int(m.group(1)), "servicio": m.group(2)})
    return {"host": str(host), "abiertos": abiertos}


# =====================================================================================
#  WIRESHARK / tshark (mirar el tráfico de TU red) — solo lectura
# =====================================================================================
def trafico(segundos=20, correr=subprocess.run, interfaz=None):
    """Mira el tráfico de tu red un rato y lo resume: con quién habla tu red y por qué protocolos. Solo mira."""
    prog = "tshark" if _hay("tshark") else None
    if prog is None:
        raise DefensaError("Falta Wireshark (tshark). Instálalo: sudo apt install tshark")
    segundos = max(3, min(120, int(segundos)))
    args = [prog, "-a", f"duration:{segundos}", "-q", "-z", "conv,ip", "-z", "io,phs"]
    if interfaz:
        args += ["-i", str(interfaz)]
    try:
        r = correr(args, capture_output=True, text=True, timeout=segundos + 60)
    except (OSError, subprocess.SubprocessError) as e:
        raise DefensaError(f"No pude ejecutar tshark (¿tienes permiso para capturar? «sudo usermod -aG wireshark "
                           f"$USER» y vuelve a entrar): {e}")
    return _parsear_trafico(r.stdout or "")


def _parsear_trafico(salida):
    """Resume la salida de tshark: conversaciones entre IP y protocolos vistos."""
    conversaciones, protocolos = [], []
    for linea in salida.splitlines():
        m = re.match(r"(\d+\.\d+\.\d+\.\d+)\s+<->\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+)", linea.strip())
        if m:
            conversaciones.append({"a": m.group(1), "b": m.group(2), "paquetes": int(m.group(3))})
        m2 = re.match(r"([a-z0-9_.-]+)\s+frames:(\d+)\s+bytes:(\d+)", linea.strip(), re.I)
        if m2 and m2.group(1) not in ("eth", "frame"):
            protocolos.append({"protocolo": m2.group(1), "paquetes": int(m2.group(2))})
    conversaciones.sort(key=lambda c: -c["paquetes"])
    return {"conversaciones": conversaciones[:30], "protocolos": protocolos[:20]}


def disponibles():
    """Qué herramientas defensivas hay instaladas en el portátil."""
    return {"nmap": _hay("nmap"), "tshark": _hay("tshark"), "mis_redes": [str(r) for r in mis_subredes()]}
