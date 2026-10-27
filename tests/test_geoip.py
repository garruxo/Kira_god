# -*- coding: utf-8 -*-
"""Ubicar y atribuir IPs en local (geoip_kira): buscar país/dueño en la base IP→ASN, clasificar particular vs
hosting, y el informe para el mapa. Con una base de mentira (sin internet)."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import geoip_kira as g

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


# base de mentira en formato iptoasn (inicio<tab>fin<tab>asn<tab>pais<tab>descripcion)
tmp = tempfile.mkdtemp()
R = os.path.join(tmp, "ip2asn.tsv")
with open(R, "w", encoding="utf-8") as f:
    f.write("1.0.0.0\t1.0.0.255\t13335\tUS\tCLOUDFLARENET\n")
    f.write("5.188.0.0\t5.188.255.255\t49505\tRU\tSELECTEL Hosting datacenter\n")
    f.write("80.58.0.0\t80.58.255.255\t3352\tES\tTelefonica de Espana broadband\n")

g._BASE.cargada = False
ok(g.hay_base(R), "detecta que hay base local")
r = g.buscar("1.0.0.1", R)
ok(r and r["pais"] == "US" and "CLOUDFLARE" in r["org"], "ubica una IP (país y dueño)")
r = g.buscar("5.188.0.5", R)
ok(r and r["pais"] == "RU", "ubica otra IP en su rango")
ok(g.buscar("9.9.9.9", R) is None, "una IP fuera de la base devuelve None (no inventa)")

ok(g.tipo_infra("SELECTEL Hosting datacenter")["clase"] == "hosting", "clasifica hosting/centro de datos")
ok(g.tipo_infra("Telefonica de Espana broadband")["clase"] == "isp", "clasifica proveedor de internet (particular)")
ok(g.tipo_infra("algo raro")["clase"] == "desconocido", "lo que no reconoce: desconocido (no inventa)")

inf = g.informe("5.188.0.5", R)
ok(inf["pais"] == "RU" and inf["lat"] is not None and inf["pais_nombre"] == "Rusia",
   "el informe trae país, nombre y lat/lon para el mapa")
ok("APARENTE" in inf["aviso"], "el informe avisa de que el origen es aparente (VPN/proxy/botnet)")
inf2 = g.informe("80.58.0.1", R)
ok(inf2["infra"]["clase"] == "isp", "el informe dice si parece particular o empresa")

# sin base, no rompe
g._BASE.cargada = False
ok(g.buscar("1.0.0.1", os.path.join(tmp, "no_existe.tsv")) is None, "sin base, devuelve None (no rompe)")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
