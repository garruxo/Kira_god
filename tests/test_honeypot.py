# -*- coding: utf-8 -*-
"""v2.64: el cebo (honeypot) DEFENSIVO de Kira. Parte pura (apuntar/resumen/informe/credenciales) + un cebo de
verdad en localhost (abre un puerto, nos conectamos, mandamos un login y comprobamos que lo apuntó). SOLO observa:
no envía nada fuera ni ejecuta lo que recibe."""
import os
import socket
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
os.environ["HOME"] = tempfile.mkdtemp()      # que cargar/guardar use un HOME temporal

import honeypot_kira as hp

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


# geo de mentira: no dependemos de la base real de IPs
class GeoFalso:
    @staticmethod
    def informe(ip):
        return {"pais": "CN", "pais_nombre": "China", "org": "Chrani Hosting", "asn": 4134,
                "lat": 35.0, "lon": 105.0, "infra": {"texto": "centro de datos", "clase": "hosting"}}


# --- credenciales_de: saca usuario/clave que probaron ---
u, c = hp.credenciales_de(b"user: root\npassword: 123456\n")
ok(u == "root" and c == "123456", f"credenciales etiquetadas: {u}/{c}")
u, c = hp.credenciales_de(b"admin\r\nadmin123\r\n")
ok(u == "admin" and c == "admin123", f"credenciales de telnet (dos líneas): {u}/{c}")

# --- servicio_de ---
ok(hp.servicio_de(2222) == "SSH" and hp.servicio_de(8080) == "HTTP", "servicio por puerto")

# --- registrar (puro): agrupa por IP, cuenta, geoloc una vez, IP nueva ---
est = hp._vacio()
reg, nueva = hp.registrar(est, {"ip": "1.2.3.4", "puerto": 2222, "servicio": "SSH",
                                "muestra": "root/1234", "usuario": "root", "clave": "1234"}, geo=GeoFalso)
ok(nueva and reg["externa"] and reg["pais"] == "CN" and reg["asn"] == 4134, "IP externa nueva con geoloc")
reg2, nueva2 = hp.registrar(est, {"ip": "1.2.3.4", "puerto": 2323, "servicio": "Telnet",
                                  "usuario": "admin", "clave": "admin"}, geo=GeoFalso)
ok(not nueva2 and reg2["veces"] == 2 and set(reg2["puertos"]) == {2222, 2323}, "misma IP suma y junta puertos")
ok(len(reg2["credenciales"]) == 2, "guarda los distintos usuario/clave probados")
ok(est["total"] == 2, "cuenta el total de toques")

# IP local: se apunta pero marcada como no externa y SIN geoloc (no llama a geo)
rl, _ = hp.registrar(est, {"ip": "192.168.1.50", "puerto": 2222}, geo=GeoFalso)
ok(not rl["externa"] and rl["pais"] is None, "IP de tu red: apuntada pero local, sin geoloc")

# --- resumen e informe_comunidad ---
r = hp.resumen(est)
ok("toque" in r and "no ataca" in r.lower() or "observa" in r.lower(), "resumen habla claro")
inf = hp.informe_comunidad(est)
ok(inf["total_ips"] == 1 and inf["ips"][0]["ip"] == "1.2.3.4", "informe comunidad: solo IPs externas")
ok("aparente" in inf["aviso"].lower(), "informe avisa de origen aparente")

# --- MODO SEGURO DE CASA: nunca escucha en 0.0.0.0 ---
h_normal, _ = hp.host_para(False)
ok(h_normal == "0.0.0.0", "modo normal: toda la red")
h_casa, modo_casa = hp.host_para(True)
ok(h_casa != "0.0.0.0", f"modo casa NUNCA es 0.0.0.0 (es {h_casa})")
import ipaddress as _ipa
ok(h_casa == "127.0.0.1" or _ipa.ip_address(h_casa).is_private, "modo casa: solo IP local o privada")
ip = hp.ip_local()
ok(ip is None or _ipa.ip_address(ip).is_private, "ip_local es privada o None (nunca pública)")

# --- CEBO DE VERDAD en localhost: abre un puerto, nos conectamos y comprueba que lo apuntó ---
ruta = os.path.join(os.environ["HOME"], "hp.json")
sensor = hp.Sensor(senuelos={0: ("SSH", b"SSH-2.0-OpenSSH_8.9\r\n")}, host="127.0.0.1",
                   ruta_estado=ruta, geo=GeoFalso)
reales = sensor.iniciar()
puerto = reales[0]
ok(puerto > 0, "el cebo abrió un puerto")
try:
    s = socket.create_connection(("127.0.0.1", puerto), timeout=3)
    banner = s.recv(100)
    ok(banner.startswith(b"SSH-2.0"), "el cebo manda un banner creíble")
    s.sendall(b"root\r\nhunter2\r\n")
    time.sleep(0.4)
    s.close()
finally:
    # dar un momento a que el hilo apunte y luego parar
    time.sleep(0.4)
    sensor.detener()

guardado = hp.cargar(ruta)
ok(guardado["total"] >= 1, "el toque quedó guardado")
reg = guardado["ips"].get("127.0.0.1")
ok(reg is not None and "SSH" in reg["servicios"], "apuntó la conexión al señuelo SSH")
ok(any(par.get("usuario") == "root" for par in reg["credenciales"]), "apuntó el usuario que probó (root)")

print(f"\nTODO BIEN {n}")
