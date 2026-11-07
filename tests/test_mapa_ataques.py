# -*- coding: utf-8 -*-
"""v2.96: el MAPA DE ATAQUES estilo Norse. Datos: cada ataque con su hora y puerto, «lo que buscan en ti», tipos,
países y tu portátil como destino; los registros se leen SOLO desde la última vez (antes se contaba lo mismo una y otra
vez). Fronteras de verdad: se bajan una vez y se guardan. La página se prueba en Chromium (si hay playwright) con un
mapa TopoJSON hecho a mano en el mismo formato que el de verdad (aquí no hay internet para bajar el real)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp()
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
import ataques_kira as at  # noqa: E402

n = 0


def ok(c, m):
    global n
    n += 1
    print(("[OK] " if c else "[X] ") + m)
    if not c:
        sys.exit(1)


# ---------- horas y servicios ----------
ok(time.gmtime(at.hora_de("2026-11-07T18:05:01.123456+01:00 papi sshd[9]: Failed password"))[3:5] == (17, 5),
   "lee la hora ISO de Ubuntu 24.04 (con su zona)")
ok(at.hora_de("Nov  7 18:05:01 papi sshd[9]: x") is not None, "y la clásica «Nov  7 18:05:01»")
ok(at.hora_de("basura sin hora") is None, "sin hora: None (se usa la de ahora)")
ok(at.servicio_de(22) == "ssh" and at.servicio_de(23) == "telnet" and at.servicio_de(3389) == "escritorio remoto"
   and at.servicio_de(40000) == "puerto 40000", "servicio de cada puerto")
ok(at.clase_de("Intento de entrar por SSH (fuerza bruta)") == "fuerza bruta" and at.clase_de("Cebo: telnet") == "cebo"
   and at.clase_de("Conexión bloqueada / escaneo de puertos") == "escaneo", "tipo corto del ataque")


# ---------- geo de mentira ----------
class Geo:
    PAISES = {"8.": ("US", "Estados Unidos", 39.0, -98.0, "GOOGLE", "hosting"),
              "5.": ("RU", "Rusia", 61.5, 105.3, "SELECTEL", "hosting"),
              "80.": ("ES", "España", 40.2, -3.7, "Telefonica de Espana", "isp")}

    def __init__(self):
        self.llamadas = 0

    def informe(self, ip):
        self.llamadas += 1
        for pre, (c, nom, la, lo, org, cl) in self.PAISES.items():
            if ip.startswith(pre):
                return {"pais": c, "pais_nombre": nom, "org": org, "asn": "1", "lat": la, "lon": lo,
                        "infra": {"texto": cl, "clase": cl}}
        return {"pais": "??", "pais_nombre": "desconocido", "org": "desconocido", "asn": "", "lat": None, "lon": None,
                "infra": {"texto": "?", "clase": "desconocido"}}


# ---------- leer SOLO lo nuevo (antes: lo mismo contado en cada pasada) ----------
AUTH = os.path.join(T, "auth.log")
UFW = os.path.join(T, "ufw.log")
EST = os.path.join(T, "ataques.json")
open(AUTH, "w").write(
    "2026-11-07T18:00:01+01:00 papi sshd[1]: Failed password for root from 5.188.0.5 port 4000 ssh2\n"
    "2026-11-07T18:00:03+01:00 papi sshd[1]: Invalid user admin from 5.188.0.5 port 4001\n"
    "2026-11-07T18:00:05+01:00 papi sshd[1]: Accepted publickey for papi from 192.168.18.20\n")
open(UFW, "w").write(
    "2026-11-07T18:01:00+01:00 papi kernel: [UFW BLOCK] IN=wlp3s0 SRC=8.8.4.4 DST=192.168.18.19 PROTO=TCP DPT=23\n"
    "2026-11-07T18:01:02+01:00 papi kernel: [UFW BLOCK] IN=wlp3s0 SRC=80.58.1.1 DST=192.168.18.19 PROTO=TCP DPT=3389\n"
    "2026-11-07T18:01:04+01:00 papi kernel: [UFW BLOCK] IN=wlp3s0 SRC=192.168.18.1 DST=192.168.18.19 DPT=53\n")
geo = Geo()
nuevas = at.paso(EST, rutas_log=[AUTH, UFW], geo=geo, ahora=1794070000)
ok(len(nuevas) == 3, "primera pasada: 3 IPs de fuera (las de casa no cuentan)")
e = at.cargar(EST)
ok(e["ips"]["5.188.0.5"]["veces"] == 2 and len(e["eventos"]) == 4, "4 ataques apuntados uno a uno")
at.paso(EST, rutas_log=[AUTH, UFW], geo=geo, ahora=1794070600)
e = at.cargar(EST)
ok(e["ips"]["5.188.0.5"]["veces"] == 2 and len(e["eventos"]) == 4,
   "segunda pasada sin nada nuevo: NO vuelve a contar lo mismo (antes sí)")
with open(UFW, "a") as f:
    f.write("2026-11-07T18:10:00+01:00 papi kernel: [UFW BLOCK] IN=wlp3s0 SRC=8.8.4.4 DST=192.168.18.19 DPT=445\n")
at.paso(EST, rutas_log=[AUTH, UFW], geo=geo, ahora=1794071200)
e = at.cargar(EST)
ok(e["ips"]["8.8.4.4"]["veces"] == 2 and len(e["eventos"]) == 5 and e["ips"]["8.8.4.4"]["puertos"] == [23, 445],
   "lo nuevo sí se suma, con su puerto")
ok(geo.llamadas == 3, "el país/dueño se averigua UNA vez por IP")
ev = e["eventos"][-1]
ok(ev["servicio"] == "smb" and ev["clase"] == "escaneo" and ev["pais_nombre"] == "Estados Unidos"
   and time.gmtime(ev["t"])[3:5] == (17, 10), "cada ataque: hora del registro, servicio, tipo y país")
os.replace(UFW, UFW + ".1")                                   # el registro rota (logrotate)
open(UFW, "w").write("2026-11-07T19:00:00+01:00 papi kernel: [UFW BLOCK] SRC=5.188.0.9 DST=192.168.18.19 DPT=22\n")
at.paso(EST, rutas_log=[AUTH, UFW], geo=geo, ahora=1794074000)
ok("5.188.0.9" in at.cargar(EST)["ips"], "si el registro rota, empieza a leer el nuevo desde el principio")

d = at.mapa_datos(at.cargar(EST))
ok([o["pais"] for o in d["origenes"]][:2] == ["RU", "US"] and d["origenes"][0]["veces"] == 3, "ranking de países")
ok({s["servicio"] for s in d["servicios"]} >= {"ssh", "telnet", "smb", "escritorio remoto"}, "lo que buscan en ti")
ok({c["clase"] for c in d["clases"]} == {"fuerza bruta", "escaneo"}, "tipos de ataque")
ok(d["objetivo"]["lat"] is not None and "Tu portátil" in d["objetivo"]["texto"], "tu portátil es el destino (solo país)")
os.environ["KIRA_PAIS"] = "MX"
ok(at.objetivo()["nombre"] != "España" or "MX" not in __import__("geoip_kira").CENTROS, "se puede elegir el país")
os.environ.pop("KIRA_PAIS")

# tope de ataques guardados
grande = at._vacio()
at.registrar(grande, [{"ip": "8.8.8.8", "tipo": "escaneo", "puerto": 80, "t": i} for i in range(at.MAX_EVENTOS + 50)],
             geo=Geo())
ok(len(grande["eventos"]) == at.MAX_EVENTOS, "no crece sin fin (tope de ataques guardados)")

# ---------- las fronteras del mundo: se bajan UNA vez ----------
import kiraos  # noqa: E402


def topo_ejemplo():
    """Un TopoJSON cuantizado (como el de world-atlas): arcos con deltas y «transform»."""
    k = 10000
    sc = [360 / (k - 1), 180 / (k - 1)]
    tr = [-180, -90]

    def cuant(pts):
        q = [(round((lo - tr[0]) / sc[0]), round((la - tr[1]) / sc[1])) for lo, la in pts]
        out, px, py = [], 0, 0
        for x, y in q:
            out.append([x - px, y - py])
            px, py = x, y
        return out
    formas = {
        "Spain": [(-9, 43.5), (3, 42.5), (3, 36.5), (-7, 36.5), (-9, 43.5)],
        "France": [(-4, 48.5), (8, 49), (7, 43.5), (3, 42.5), (-1.5, 43.5), (-4, 48.5)],
        "Russia": [(30, 60), (170, 70), (179.99, 65), (175, 55), (30, 50), (30, 60)],
        "Fiji": [(178, -17), (-179, -17), (-179.5, -19), (178, -19), (178, -17)],
        "United States of America": [(-125, 48), (-67, 47), (-80, 25), (-117, 32), (-125, 48)],
        "China": [(75, 40), (125, 50), (122, 25), (100, 22), (75, 40)],
        "Antarctica": [(-180, -80), (180, -80), (180, -89), (-180, -89), (-180, -80)],
    }
    arcs, geos = [], []
    for i, (nom, pts) in enumerate(formas.items()):
        arcs.append(cuant(pts))
        geos.append({"type": "Polygon", "arcs": [[i]], "id": "010" if nom == "Antarctica" else str(100 + i),
                     "properties": {"name": nom}})
    arcs += [[[0, 0], [1, 1]]] * 100                     # relleno: un mapa de verdad tiene cientos de arcos
    return {"type": "Topology", "transform": {"scale": sc, "translate": tr}, "arcs": arcs,
            "objects": {"countries": {"type": "GeometryCollection", "geometries": geos}}}


TOPO = topo_ejemplo()
R = os.path.join(T, "mundo.json")
pedidas = []


def abrir_bien(url):
    pedidas.append(url)
    if "jsdelivr" in url:
        raise OSError("bloqueado")                       # la primera web falla: prueba la segunda
    return json.dumps(TOPO).encode()


r = kiraos.mundo_kira(R, abrir=abrir_bien)
ok(r["ok"] and r["de"] == "bajado" and len(pedidas) == 2 and os.path.isfile(R),
   "baja las fronteras (si una web falla, prueba la otra) y las guarda")
r = kiraos.mundo_kira(R, abrir=lambda u: (_ for _ in ()).throw(AssertionError("no debía bajar")))
ok(r["ok"] and r["de"] == "guardado", "la siguiente vez, sin internet: usa lo guardado")
r = kiraos.mundo_kira(os.path.join(T, "otro.json"), abrir=lambda u: b'{"hola": 1}')
ok(not r["ok"], "si lo bajado no es un mapa, no lo guarda y el mapa usa el dibujo de reserva")
api = kiraos.Api.__new__(kiraos.Api)
ok(callable(getattr(api, "mapa_mundo", None)) and callable(getattr(api, "mapa_ataques", None)),
   "la pantalla puede pedir el mundo y los ataques")
esc = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html"), encoding="utf-8").read()
ok('"mapa_mundo"' in esc, "el escritorio deja pasar «mapa_mundo» al mapa (que va en un marco)")

# ---------- el mapa del mundo va DENTRO (sin internet) ----------
WEB = os.path.join(RAIZ, "kira_portatil", "kiraos_web")
mjs = open(os.path.join(WEB, "mundo_50m.js"), encoding="utf-8").read()
ok("window.KIRA_MUNDO=" in mjs and "window.KIRA_ISO_NUM=" in mjs and len(mjs) > 500_000, "mundo_50m.js: el mapa de verdad, dentro")
ok("dominio público" in open(os.path.join(WEB, "MUNDO_LICENCIA.txt"), encoding="utf-8").read().lower(), "con su licencia")
ok('<script src="mundo_50m.js">' in open(os.path.join(WEB, "mapa.html"), encoding="utf-8").read(), "el mapa lo carga")

# ---------- la pantalla de verdad (Chromium) ----------
DATOS = at.mapa_datos(at.cargar(EST))
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "mapa.html")
if node:
    js = r"""
const { chromium } = require('playwright');
const fs = require('fs');
const [html, datos, topo, foto1, foto2] = process.argv.slice(2);
let b; (async () => { b = await chromium.launch(); const out = {};
  async function pagina(ej){
    const pg = await b.newPage({viewport:{width:1300,height:640}});
    const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
    await pg.addInitScript(([d,t]) => { window.KIRA_EJEMPLO = d; window.KIRA_MUNDO_EJEMPLO = t; }, [ej, JSON.parse(fs.readFileSync(topo,'utf8'))]);
    await pg.goto('file://' + html); await pg.waitForTimeout(900);
    return [pg, errs];
  }
  // 1) con ataques reales (y el mapa hecho a mano: así se comprueba el decodificador)
  let [pg, errs] = await pagina(JSON.parse(fs.readFileSync(datos,'utf8')));
  await pg.waitForTimeout(3500);
  const m = await pg.evaluate(() => KIRA_MAPA);
  out.paises = m.paises; out.trozos = m.trozos; out.real = m.real; out.disparados = m.disparados; out.puntos = m.puntos;
  out.resaltados = m.resaltados;
  out.pixelesFx = await pg.evaluate(() => { const c=document.getElementById('cFx'), d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
    let n=0; for(let i=3;i<d.length;i+=4) if(d[i]>0) n++; return n; });
  out.origen = await pg.$$eval('#tOrigen td', l => l.map(x => x.textContent));
  out.buscan = await pg.$$eval('#tBuscan td', l => l.map(x => x.textContent));
  out.tipos = await pg.$$eval('#tTipos td', l => l.map(x => x.textContent));
  out.filas = await pg.$$eval('#tAtaques tr', l => l.map(x => x.textContent));
  out.estado = await pg.textContent('#estado');
  out.cuenta = await pg.textContent('#cuenta');
  await pg.click('#tAtaques tr'); await pg.waitForTimeout(200);
  out.ficha = await pg.textContent('#ficha');
  out.errs = errs; await pg.close();
  // 2) sin ataques: lo explica y ofrece la demostración; con el mapa DE VERDAD que va dentro (mundo_50m.js)
  const pg2 = await b.newPage({viewport:{width:1300,height:640}}); errs=[]; pg2.on('pageerror', e => errs.push(String(e)));
  await pg2.addInitScript(() => { window.KIRA_EJEMPLO = {ataques:[]}; });
  await pg2.goto('file://' + html); await pg2.waitForTimeout(1200);
  const m2 = await pg2.evaluate(() => KIRA_MAPA); out.realDentro = m2.real; out.paisesDentro = m2.paises;
  out.vacio = await pg2.textContent('#vacio'); out.vacioVis = await pg2.isVisible('#vacio');
  await pg2.click('#vacioDemo'); await pg2.waitForTimeout(2600);
  out.demoEstado = await pg2.textContent('#estado'); out.demoFilas = await pg2.$$eval('#tAtaques tr', l => l.length);
  out.demoIps = await pg2.$$eval('#tAtaques td.ip', l => l.map(x => x.textContent));
  out.demoBoton = await pg2.textContent('#btnDemo');
  await pg2.screenshot({path: foto1});
  await pg2.click('#btnDemo'); await pg2.waitForTimeout(300);
  out.vuelve = await pg2.isVisible('#vacio');
  out.errs2 = errs; await pg2.close();
  // 3) si faltara el archivo del mapa: dibujo de reserva
  const pg3 = await b.newPage({viewport:{width:1300,height:640}});
  await pg3.addInitScript(d => { window.KIRA_EJEMPLO = d; window.KIRA_SIN_MUNDO = true; }, JSON.parse(fs.readFileSync(datos,'utf8')));
  await pg3.goto('file://' + html); await pg3.waitForTimeout(1500);
  out.reserva = await pg3.evaluate(() => KIRA_MAPA.real === false && KIRA_MAPA.paises === 8);
  await pg3.screenshot({path: foto2});
  console.log(JSON.stringify(out));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    f = os.path.join(T, "m.js")
    open(f, "w").write(js)
    fd = os.path.join(T, "datos.json")
    json.dump(DATOS, open(fd, "w"))
    ft = os.path.join(T, "topo.json")
    json.dump(TOPO, open(ft, "w"))
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    f1, f2 = os.path.join(T, "mapa_demo.png"), os.path.join(T, "mapa_reserva.png")
    r = subprocess.run([node, f, html, fd, ft, f1, f2], capture_output=True, text=True, timeout=180, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"] and not d["errs2"], "Chromium: sin errores " + str(d["errs"] + d["errs2"]))
        ok(d["real"] and d["paises"] == 6, "Chromium: dibuja cada país del TopoJSON (y quita la Antártida)")
        ok(d["trozos"]["Russia"] == 1 and d["trozos"]["Fiji"] == 2,
           "Chromium: un país que cruza la línea de cambio de fecha queda cerrado y se ve a los dos lados")
        ok(d["realDentro"] and d["paisesDentro"] > 200, "Chromium: el mapa de verdad (Natural Earth 1:50m) va dentro, sin internet")
        ok(d["resaltados"]["casa"] == "724" and "643" in d["resaltados"]["origenes"],
           "Chromium: tu país (España) en azul y los países de donde vienen, coloreados")
        ok("Rusia" in " ".join(d["origen"]) and "3" in d["origen"], "Chromium: panel ORIGEN con países y veces")
        ok("ssh" in " ".join(d["buscan"]) and "3389" in d["buscan"], "Chromium: panel QUÉ BUSCAN EN TI (servicio y puerto)")
        ok(any("Fuerza bruta" in x for x in d["tipos"]), "Chromium: panel TIPO DE ATAQUE")
        ok(len(d["filas"]) >= 3 and any("5.188.0.5" in x for x in d["filas"]), "Chromium: la lista de ATAQUES se va llenando")
        ok(d["disparados"] >= 3 and d["pixelesFx"] > 500, "Chromium: las líneas vuelan desde su país hasta tu portátil")
        ok(d["puntos"] >= 3, "Chromium: un punto por cada IP atacante")
        ok("Repitiendo" in d["estado"] or "vivo" in d["estado"].lower(), "Chromium: dice si es repetición o en vivo")
        ok("IP" in d["cuenta"] and "países" in d["cuenta"], "Chromium: contadores arriba")
        ok("Dueño de la IP" in d["ficha"] and "APARENTE" in d["ficha"], "Chromium: pulsar un ataque abre su ficha (honesta)")
        ok(d["vacioVis"] and "router" in d["vacio"], "Chromium: sin ataques lo explica (el router de casa frena casi todo)")
        ok("Demostración" in d["demoEstado"] and d["demoFilas"] >= 4, "Chromium: la demostración se ve, marcada como tal")
        ok(all(x.startswith(("203.0.113.", "198.51.100.")) for x in d["demoIps"]),
           "Chromium: la demo usa IPs de documentación (inventadas), nunca de nadie")
        ok("reales" in d["demoBoton"] and d["vuelve"], "Chromium: se vuelve a tus datos reales")
        ok(d["reserva"], "Chromium: si faltara el archivo del mapa, usa el dibujo de reserva")
        esp = "/tmp/claude-0/-home-claude/c4932b0e-9cad-5b68-a590-3e4b8a3549d8/scratchpad"
        if os.path.isdir(esp):
            shutil.copy(f1, esp)
            shutil.copy(f2, esp)
    else:
        print("(sin Chromium utilizable: me salto la pantalla)", out[:300])

print("\nTODO BIEN", n)
