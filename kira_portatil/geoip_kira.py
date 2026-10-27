# -*- coding: utf-8 -*-
"""
geoip_kira.py - Ubicar una IP (país) y saber DE QUIÉN es (su dueño/ASN), todo EN LOCAL, sin internet.

Se apoya en una base gratuita «IP → ASN» (la de iptoasn.com, formato TSV) que el instalador baja UNA vez al portátil
(`~/.kira_ip2asn.tsv` o `.tsv.gz`). Con eso:
  - buscar(ip)      -> {asn, pais, org}  (de qué país es y de quién)
  - tipo_infra(org) -> «proveedor de internet (probablemente un particular)» / «centro de datos / hosting» / …
  - informe(ip)     -> todo junto + lat/lon del país para pintarlo en el mapa.

SINCERIDAD: la IP es el origen APARENTE. Con VPN, Tor, proxys o una red de equipos infectados (botnet) la IP puede NO
ser la del atacante real, y la ubicación es a nivel de PAÍS (aproximada). Esto ayuda a entender el ataque, no a señalar
con certeza a una persona. Solo lectura, solo librería estándar.
"""
import bisect
import gzip
import ipaddress
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(os.path.expanduser("~"), ".kira_ip2asn.tsv")

# Centro aproximado (lat, lon, nombre) de los países que más aparecen. Para pintar el punto en el mapa.
# (Dominio público; si un país no está aquí, se ubica igual por nombre pero sin punto en el mapa.)
CENTROS = {
    "US": (39.0, -98.0, "Estados Unidos"), "CN": (35.9, 104.2, "China"), "RU": (61.5, 105.3, "Rusia"),
    "DE": (51.2, 10.5, "Alemania"), "NL": (52.1, 5.3, "Países Bajos"), "FR": (46.6, 2.2, "Francia"),
    "GB": (54.0, -2.0, "Reino Unido"), "BR": (-10.3, -53.2, "Brasil"), "IN": (22.0, 79.0, "India"),
    "VN": (16.2, 107.8, "Vietnam"), "KR": (36.5, 127.8, "Corea del Sur"), "JP": (36.2, 138.3, "Japón"),
    "UA": (48.4, 31.2, "Ucrania"), "RO": (45.9, 24.9, "Rumanía"), "ID": (-2.5, 118.0, "Indonesia"),
    "IR": (32.4, 53.7, "Irán"), "TR": (39.0, 35.2, "Turquía"), "IT": (42.8, 12.8, "Italia"),
    "ES": (40.2, -3.7, "España"), "PL": (52.1, 19.4, "Polonia"), "CA": (56.1, -106.3, "Canadá"),
    "MX": (23.6, -102.5, "México"), "AR": (-38.4, -63.6, "Argentina"), "TH": (15.9, 100.9, "Tailandia"),
    "SG": (1.35, 103.8, "Singapur"), "HK": (22.3, 114.2, "Hong Kong"), "TW": (23.7, 121.0, "Taiwán"),
    "AU": (-25.3, 133.8, "Australia"), "ZA": (-30.6, 22.9, "Sudáfrica"), "EG": (26.8, 30.8, "Egipto"),
    "SA": (23.9, 45.1, "Arabia Saudí"), "AE": (23.4, 53.8, "Emiratos"), "PK": (30.4, 69.3, "Pakistán"),
    "BD": (23.7, 90.4, "Banglades"), "PH": (12.9, 121.8, "Filipinas"), "MY": (4.2, 101.9, "Malasia"),
    "CO": (4.6, -74.3, "Colombia"), "CL": (-35.7, -71.5, "Chile"), "PE": (-9.2, -75.0, "Perú"),
    "NG": (9.1, 8.7, "Nigeria"), "KE": (-0.0, 37.9, "Kenia"), "IL": (31.0, 34.9, "Israel"),
    "SE": (60.1, 18.6, "Suecia"), "NO": (60.5, 8.5, "Noruega"), "FI": (64.0, 26.0, "Finlandia"),
    "DK": (56.3, 9.5, "Dinamarca"), "CH": (46.8, 8.2, "Suiza"), "AT": (47.5, 14.6, "Austria"),
    "BE": (50.5, 4.5, "Bélgica"), "PT": (39.4, -8.2, "Portugal"), "IE": (53.4, -8.2, "Irlanda"),
    "CZ": (49.8, 15.5, "Chequia"), "HU": (47.2, 19.5, "Hungría"), "GR": (39.1, 21.8, "Grecia"),
    "BG": (42.7, 25.5, "Bulgaria"), "RS": (44.0, 21.0, "Serbia"), "KZ": (48.0, 66.9, "Kazajistán"),
    "BY": (53.7, 27.9, "Bielorrusia"), "MD": (47.4, 28.4, "Moldavia"), "LT": (55.2, 23.9, "Lituania"),
    "LV": (56.9, 24.6, "Letonia"), "EE": (58.6, 25.0, "Estonia"), "SK": (48.7, 19.7, "Eslovaquia"),
    "HR": (45.1, 15.2, "Croacia"), "MA": (31.8, -7.1, "Marruecos"), "DZ": (28.0, 1.7, "Argelia"),
    "TN": (33.9, 9.6, "Túnez"), "NZ": (-40.9, 174.9, "Nueva Zelanda"), "EC": (-1.8, -78.2, "Ecuador"),
    "VE": (6.4, -66.6, "Venezuela"), "UZ": (41.4, 64.6, "Uzbekistán"), "IQ": (33.2, 43.7, "Irak"),
    "LK": (7.9, 80.8, "Sri Lanka"), "NP": (28.4, 84.1, "Nepal"), "MM": (21.9, 95.9, "Birmania"),
    "KH": (12.6, 104.9, "Camboya"), "LU": (49.8, 6.1, "Luxemburgo"), "SI": (46.1, 14.8, "Eslovenia"),
}


class _Base:
    def __init__(self):
        self.inicios = []     # IP de inicio de cada rango (como entero), ORDENADAS
        self.datos = []       # (fin_int, asn, pais, org) en el mismo orden
        self.cargada = False


_BASE = _Base()


def _abrir(ruta):
    if ruta.endswith(".gz") or (os.path.isfile(ruta) and open(ruta, "rb").read(2) == b"\x1f\x8b"):
        return gzip.open(ruta, "rt", encoding="utf-8", errors="replace")
    return open(ruta, encoding="utf-8", errors="replace")


def cargar_base(ruta=None, forzar=False):
    """Carga la base IP→ASN en memoria (una vez). Formato iptoasn: inicio<tab>fin<tab>asn<tab>pais<tab>descripcion."""
    ruta = ruta or (RUTA if os.path.isfile(RUTA) else RUTA + ".gz")
    if _BASE.cargada and not forzar:
        return True
    if not os.path.isfile(ruta):
        return False
    inicios, datos = [], []
    with _abrir(ruta) as f:
        for linea in f:
            p = linea.rstrip("\n").split("\t")
            if len(p) < 5:
                continue
            try:
                ini = int(ipaddress.ip_address(p[0]))
                fin = int(ipaddress.ip_address(p[1]))
            except ValueError:
                continue
            inicios.append(ini)
            datos.append((fin, p[2], p[3], p[4]))
    # vienen ordenados, pero por si acaso
    orden = sorted(range(len(inicios)), key=lambda i: inicios[i])
    _BASE.inicios = [inicios[i] for i in orden]
    _BASE.datos = [datos[i] for i in orden]
    _BASE.cargada = True
    return True


def hay_base(ruta=None):
    ruta = ruta or RUTA
    return os.path.isfile(ruta) or os.path.isfile(ruta + ".gz")


def buscar(ip, ruta=None):
    """{asn, pais, org} de una IP, o None si no está en la base / no hay base."""
    if not cargar_base(ruta):
        return None
    try:
        n = int(ipaddress.ip_address(str(ip).strip()))
    except ValueError:
        return None
    i = bisect.bisect_right(_BASE.inicios, n) - 1
    if i < 0:
        return None
    fin, asn, pais, org = _BASE.datos[i]
    if n > fin or asn in ("", "0", "Not routed"):
        return None
    return {"asn": asn, "pais": pais, "org": org}


_HOSTING = ("hosting", "datacenter", "data center", "cloud", "server", "vps", "colo", "dedicated",
            "amazon", "aws", "google", "microsoft", "azure", "ovh", "hetzner", "digitalocean", "linode",
            "vultr", "contabo", "leaseweb", "cloudflare", "oracle", "alibaba", "tencent", "scaleway", "online s.a.s")
_ISP = ("telecom", "telefon", "vodafone", "orange", "movistar", "comcast", "verizon", "at&t", "broadband",
        "dsl", "fiber", "fibre", "cable", "mobile", "wireless", "movil", "net s.p.a", "communications",
        "internet services", "isp", "jazztel", "masmovil", "digi")


def tipo_infra(org):
    """A partir del dueño (org) de la IP, una pista de QUIÉN puede haber detrás. Es solo una pista, no una certeza."""
    o = (org or "").lower()
    if any(k in o for k in _HOSTING):
        return {"clase": "hosting", "texto": "Centro de datos / hosting (a menudo automatizado o con recursos)"}
    if any(k in o for k in _ISP):
        return {"clase": "isp", "texto": "Proveedor de internet (probablemente un particular)"}
    return {"clase": "desconocido", "texto": "Dueño sin clasificar"}


def informe(ip, ruta=None):
    """Todo lo que Kira puede saber de una IP, para enseñarlo y pintarlo en el mapa."""
    r = buscar(ip, ruta)
    out = {"ip": str(ip), "pais": "??", "pais_nombre": "desconocido", "asn": "", "org": "desconocido",
           "lat": None, "lon": None, "infra": tipo_infra(""), "aviso": "Origen APARENTE (puede ir por VPN/proxy/botnet)."}
    if r:
        out.update({"pais": r["pais"], "asn": r["asn"], "org": r["org"], "infra": tipo_infra(r["org"])})
        c = CENTROS.get(r["pais"])
        if c:
            out["lat"], out["lon"], out["pais_nombre"] = c[0], c[1], c[2]
    return out
