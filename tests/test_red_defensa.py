# -*- coding: utf-8 -*-
"""Vigilancia defensiva de la red (portátil): inventario y puertos con un Nmap de mentira, resumen de tráfico con un
tshark de mentira, y el CANDADO: nada fuera de la red local. Sin red real."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import red_defensa_kira as rd

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


# --- el candado: solo la red local ---
rd.mis_subredes = lambda: [__import__("ipaddress").ip_network("192.168.1.0/24")]
ok(rd.en_mi_red("192.168.1.50") and rd.en_mi_red("192.168.1.1"), "una IP de tu red: sí")
ok(not rd.en_mi_red("8.8.8.8") and not rd.en_mi_red("192.168.2.10") and not rd.en_mi_red("google.com"),
   "una IP de internet o de otra red: NO")

for accion in ("puertos",):
    try:
        rd.puertos("8.8.8.8", correr=lambda *a, **k: None)
        ok(False, "escanear fuera debería fallar")
    except rd.DefensaError as e:
        ok("tu red" in str(e), "escanear una IP de fuera se rechaza con aviso claro")


class Falso:
    def __init__(self, salida):
        self.salida = salida

    def __call__(self, args, **k):
        class R:
            pass
        r = R()
        r.stdout = self.salida
        r.returncode = 0
        return r


rd.shutil.which = lambda p: "/usr/bin/" + p        # fingimos que nmap/tshark están instalados

INV = """Starting Nmap
Nmap scan report for router.casa (192.168.1.1)
Host is up.
MAC Address: AA:BB:CC:00:11:22 (Movistar)
Nmap scan report for 192.168.1.50
Host is up.
MAC Address: DE:AD:BE:EF:00:01 (Samsung)
Nmap scan report for pc.casa (192.168.1.77)
Host is up.
"""
ap = rd.inventario(correr=Falso(INV))
ok(len(ap) == 3 and ap[0]["ip"] == "192.168.1.1" and ap[0]["nombre"] == "router.casa"
   and ap[0]["fabricante"] == "Movistar", "inventario: saca aparatos, nombre y fabricante")
ok(any(a["ip"] == "192.168.1.50" and a["fabricante"] == "Samsung" for a in ap), "y los demás aparatos")

PUE = """Nmap scan report for 192.168.1.50
PORT     STATE SERVICE
22/tcp   open  ssh
80/tcp   open  http
443/tcp  closed https
8080/tcp open  http-proxy
"""
r = rd.puertos("192.168.1.50", correr=Falso(PUE))
ok([p["puerto"] for p in r["abiertos"]] == [22, 80, 8080], "puertos: solo los ABIERTOS")
ok(r["abiertos"][0]["servicio"] == "ssh", "y su servicio")

TRA = """================================================================================
IPv4 Conversations
192.168.1.50         <-> 192.168.1.1              120
192.168.1.77         <-> 142.250.1.1               40
================================================================================
Protocol Hierarchy
  ip     frames:160 bytes:90000
  tcp    frames:140 bytes:85000
  tls    frames:90 bytes:70000
  dns    frames:12 bytes:1500
"""
t = rd.trafico(20, correr=Falso(TRA))
ok(t["conversaciones"][0]["paquetes"] == 120 and t["conversaciones"][0]["a"] == "192.168.1.50",
   "tráfico: conversaciones ordenadas por paquetes")
ok(any(p["protocolo"] == "tls" for p in t["protocolos"]), "y los protocolos vistos")

# sin herramientas instaladas, avisa de cómo instalarlas
rd.shutil.which = lambda p: None
for fn, nombre in ((lambda: rd.inventario(correr=Falso("")), "nmap"), (lambda: rd.trafico(5, correr=Falso("")), "tshark")):
    try:
        fn()
        ok(False, f"sin {nombre} debería avisar")
    except rd.DefensaError as e:
        ok(nombre in str(e) or "Wireshark" in str(e), f"sin {nombre}: dice cómo instalarlo")

srv = open(os.path.join(RAIZ, "kira_portatil", "servidor_portatil.py"), encoding="utf-8").read()
ok('ruta == "/defensa"' in srv and "rd.inventario()" in srv, "el servidor del portátil expone /defensa")
doc = open(os.path.join(RAIZ, "kira_portatil", "red_defensa_kira.py"), encoding="utf-8").read()
ok("SOLO DEFENSA" in doc and "Metasploit" not in doc, "el módulo es defensivo (sin herramientas de ataque)")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
