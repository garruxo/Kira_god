# -*- coding: utf-8 -*-
"""Detectar ataques y prepararlos para el mapa (ataques_kira): leer los registros del sistema (SSH/cortafuegos),
quedarse solo con IPs externas, agrupar por IP con su país/dueño, y los datos del mapa. Con registros y geoip de
mentira (sin red, sin internet)."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import ataques_kira as at

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


AUTH = """\
Oct 27 10:00:01 host sshd[111]: Failed password for root from 5.188.0.5 port 50 ssh2
Oct 27 10:00:02 host sshd[112]: Invalid user admin from 1.0.0.1 port 51
Oct 27 10:00:03 host sshd[113]: Failed password for pi from 192.168.1.5 port 52 ssh2
Oct 27 10:00:04 host sshd[114]: Accepted password for juan from 192.168.1.9 port 53 ssh2
"""
UFW = """\
Oct 27 10:05:00 host kernel: [UFW BLOCK] IN=eth0 SRC=80.58.0.1 DST=192.168.1.10 PROTO=TCP DPT=23
Oct 27 10:05:01 host kernel: [UFW BLOCK] IN=eth0 SRC=10.0.0.5 DST=192.168.1.10 PROTO=TCP DPT=22
"""

ssh = at.leer_auth(AUTH)
ok(any(e["ip"] == "5.188.0.5" for e in ssh) and any(e["ip"] == "1.0.0.1" for e in ssh),
   "lee los intentos fallidos de SSH")
ok(not any(e["ip"].startswith("192.168.") for e in ssh), "NO cuenta como ataque lo de tu propia red (IP privada)")

ufw = at.leer_ufw(UFW)
ok(any(e["ip"] == "80.58.0.1" and e["puerto"] == 23 for e in ufw), "lee las conexiones bloqueadas (con el puerto)")
ok(not any(e["ip"].startswith("10.") for e in ufw), "ignora las IPs privadas en el cortafuegos")

# recolectar con registros de mentira (inyectando el lector)
textos = {"/var/log/auth.log": AUTH, "/var/log/ufw.log": UFW}
eventos = at.recolectar(rutas=list(textos), leer=lambda r: textos[r])
ok(len(eventos) == 3, "recolecta 3 ataques externos (2 SSH + 1 cortafuegos)")


class GeoFalso:
    def informe(self, ip):
        datos = {"5.188.0.5": ("RU", "Rusia", "SELECTEL hosting", 61.5, 105.3, "hosting", "Centro de datos / hosting"),
                 "1.0.0.1": ("US", "Estados Unidos", "CLOUDFLARENET", 39.0, -98.0, "hosting", "Centro de datos / hosting"),
                 "80.58.0.1": ("ES", "España", "Telefonica broadband", 40.2, -3.7, "isp", "Proveedor de internet (particular)")}
        d = datos.get(ip)
        if not d:
            return {"ip": ip, "pais": "??", "pais_nombre": "desconocido", "asn": "", "org": "?", "lat": None,
                    "lon": None, "infra": {"clase": "desconocido", "texto": "?"}, "aviso": ""}
        return {"ip": ip, "pais": d[0], "pais_nombre": d[1], "asn": "1", "org": d[2], "lat": d[3], "lon": d[4],
                "infra": {"clase": d[5], "texto": d[6]}, "aviso": ""}


R = os.path.join(tempfile.mkdtemp(), "ataques.json")
est = at.cargar(R)
nuevas = at.registrar(est, eventos, geo=GeoFalso(), ahora=1000)
ok(len(nuevas) == 3, "la 1.ª vez las 3 IPs son nuevas")
ok(est["ips"]["5.188.0.5"]["pais_nombre"] == "Rusia" and est["ips"]["5.188.0.5"]["lat"] == 61.5,
   "a cada IP le pone país y lat/lon para el mapa")
ok(est["ips"]["80.58.0.1"]["infra_clase"] == "isp", "distingue particular (ISP) de empresa (hosting)")

# segunda pasada: los mismos no son «nuevos», pero suben el contador
nuevas = at.registrar(est, eventos, geo=GeoFalso(), ahora=1100)
ok(nuevas == [] and est["ips"]["5.188.0.5"]["veces"] == 2, "repetir no da falsos «nuevos»; cuenta los intentos")

m = at.mapa_datos(est)
ok(m["total"] == 3 and m["con_mapa"] == 3 and m["ataques"][0]["veces"] >= m["ataques"][-1]["veces"],
   "los datos del mapa salen ordenados por nº de ataques")

# guardar/cargar 0600
at.guardar(est, R)
ok((os.stat(R).st_mode & 0o777) == 0o600, "guarda los ataques en un archivo solo del dueño (0600)")
ok(at.cargar(R)["ips"].get("1.0.0.1") is not None, "lo guardado se recupera")

# paso completo con registros y geo de mentira
R2 = os.path.join(tempfile.mkdtemp(), "a2.json")
nv = at.paso(ruta_estado=R2, rutas_log=list(textos), geo=GeoFalso(), leer=lambda r: textos[r], ahora=1)
ok(len(nv) == 3 and os.path.isfile(R2), "una pasada completa detecta, atribuye y guarda")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
