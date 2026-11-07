# -*- coding: utf-8 -*-
"""
fuera_kira.py - v3.00: KiraOS alcanzable FUERA DE CASA por Tailscale (decisión del dueño).

Tailscale es una red privada y cifrada (WireGuard) entre los aparatos del dueño: su móvil y su portátil. No hay que
abrir ningún puerto del router. Cada aparato recibe una dirección fija del tipo 100.x.y.z que solo ven sus aparatos.

Aquí solo se averigua esa dirección para dársela al móvil (en casa, por /hola del núcleo). Lo que se puede hacer desde
fuera lo decide el móvil: SINCRONIZAR y VER qué hace KiraOS (con Parar/Pausar/Seguir). Las órdenes de trabajo siguen
esperando a que llegue a casa (decisión del dueño en la v2.88), y el token del laboratorio sigue haciendo falta.
"""
import ipaddress
import re
import subprocess
import time

RED_TAILSCALE = ipaddress.ip_network("100.64.0.0/10")
_cache = {"t": 0.0, "ip": None}


def es_ip_tailscale(ip):
    try:
        d = ipaddress.ip_address(str(ip).strip())
    except ValueError:
        return False
    return d.version == 4 and d in RED_TAILSCALE


def _correr_real(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=5)
        return p.returncode, p.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def ip_tailscale(correr=None, cache_seg=60, ahora=None):
    """La dirección 100.x.y.z de este portátil en Tailscale, o None si Tailscale no está (o no ha entrado)."""
    ahora = time.time() if ahora is None else ahora
    if correr is None and ahora - _cache["t"] < cache_seg:
        return _cache["ip"]
    correr = correr or _correr_real
    ip = None
    cod, sal = correr(["tailscale", "ip", "-4"])
    if cod == 0:
        for linea in sal.splitlines():
            if es_ip_tailscale(linea):
                ip = linea.strip()
                break
    if ip is None:                                   # sin el comando: mirar la interfaz tailscale0
        cod, sal = correr(["ip", "-4", "-o", "addr", "show", "tailscale0"])
        if cod == 0:
            m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)/", sal)
            if m and es_ip_tailscale(m.group(1)):
                ip = m.group(1)
    _cache.update(t=ahora, ip=ip)
    return ip


def texto_estado(correr=None):
    ip = ip_tailscale(correr=correr)
    if ip:
        return (f"Fuera de casa: ACTIVADO por Tailscale ({ip}). Con la app de Tailscale en el móvil (misma cuenta), "
                "Kira app se sincroniza conmigo y ve lo que hago aunque no estéis en la misma WiFi.")
    return ("Fuera de casa: desactivado. Para activarlo, en la terminal: cd kira_god/kira_portatil y "
            "bash activar_fuera.sh (o escribe «bash act» y pulsa Tab).")
