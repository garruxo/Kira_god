# -*- coding: utf-8 -*-
"""v2.83: el NACIMIENTO de Kira en el portátil (primera vez que se enciende KiraOS) y entrar SIN PIN."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import nacimiento_kira as nk
import bloqueo_kira as bl
import kiraos

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


T = tempfile.mkdtemp()
RN, RB, RP = os.path.join(T, "nac.json"), os.path.join(T, "baul"), os.path.join(T, "pin.txt")
EQ = {"nombre": "packard-bell", "ram_mb": 7900, "procesador": "Intel Core i5 M 430 @ 2.27GHz", "nucleos": 4,
      "disco_gb": 240, "sistema": "Ubuntu 24.04 LTS"}

# ---------- lo que sabe del equipo (puro, con textos de mentira) ----------
ok(nk.ram_mb("MemTotal:        8090000 kB\nMemFree: 1 kB") == 7900, "lee la RAM de /proc/meminfo")
ok(nk.procesador("model name\t: Intel(R) Core(TM) i5 CPU       M 430  @ 2.27GHz") == "Intel Core i5 M 430 @ 2.27GHz",
   "lee el procesador (y quita (R)/(TM))")
ok(nk.sistema('NAME="Ubuntu"\nPRETTY_NAME="Xubuntu 24.04 LTS"') == "Xubuntu 24.04 LTS", "lee el sistema")
e = nk.equipo()
ok(e["ram_mb"] > 0 and e["nucleos"] >= 1 and e["procesador"], "equipo() de verdad en este ordenador")

# ---------- nacer ----------
ok(not nk.ha_nacido(RN) and nk.cargar(RN) is None, "antes de nacer no hay partida")
try:
    nk.nacer("   ", ruta=RN, baul=RB, eq=EQ)
    ok(False, "sin nombre no nace")
except nk.NacimientoError:
    ok(True, "sin nombre no nace")
p = nk.nacer("Garru", "Jefe", ruta=RN, baul=RB, eq=EQ, ahora=1762509600)
ok(nk.ha_nacido(RN) and p["dueno"] == "Garru" and p["llamar"] == "Jefe", "nace y sabe quién eres y cómo llamarte")
ok("noviembre de 2025" in p["fecha"], "fecha en español")
ok(p["recuerdo"] is True, "su partida es su PRIMER recuerdo en el baúl")
ok(oct(os.stat(RN).st_mode & 0o777) == "0o600", "la partida se guarda solo para ti (0600)")
txt = nk.texto_partida(nk.cargar(RN))
ok("Garru" in txt and "Jefe" in txt and "i5 M 430" in txt and "7,7 GB" in txt and "240 GB" in txt, "partida legible")
p2 = nk.nacer("Otro", ruta=RN, baul=RB, eq=EQ)
ok(p2["dueno"] == "Garru", "solo nace UNA vez (no pisa la partida)")
ok(nk.cambiar_nombre("Garruxo", RN)["llamar"] == "Garruxo", "puede cambiar cómo te llama")
ok(nk.partida("Ana", eq=EQ, version="x")["llamar"] == "Ana", "si no dices cómo llamarte, usa tu nombre")
import recuerdos_kira as rk
ok(rk.Recuerdos(RB).total() >= 2, "el baúl tiene sus primeros recuerdos")

# ---------- KiraOS: puente con la pantalla, sin PIN ----------
RN2 = os.path.join(T, "nac2.json")
api = kiraos.Api(ruta_pin=RP, ruta_nacimiento=RN2, baul=os.path.join(T, "baul2"))
inf = api.info()
ok(inf["nacida"] is False and inf["hay_pin"] is False, "primera vez: toca nacer, y no hay PIN")
ok(api.nacer("", "")["ok"] is False, "nacer sin nombre lo dice")
r = api.nacer("Garru", "Jefe")
ok(r["ok"] and r["llamar"] == "Jefe" and "PARTIDA" in r["partida"], "nacer desde la pantalla")
inf = api.info()
ok(inf["nacida"] and inf["llamar"] == "Jefe", "luego la pantalla saluda «Hola, Jefe»")
ok(kiraos._reserva_consola(api) is True and api.entrado, "sin PIN entra directo (reserva sin ventana)")
# PIN opcional: se puede poner y quitar
ok(bl.crear_pin("1234", RP) and api.info()["hay_pin"], "se puede poner un PIN si se quiere")
ok(bl.quitar_pin(RP) is True and not api.info()["hay_pin"] and bl.quitar_pin(RP) is False, "y quitarlo")

# ---------- la pantalla: escena de nacimiento + saludo sin PIN ----------
h = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "arranque.html"), encoding="utf-8").read()
for k in ("function nacimiento", "chispa", "latenace", "¿Cómo te llamas?", "cómo quieres que te llame",
          "MI PARTIDA DE NACIMIENTO", "api().nacer(", "if(hayPin)", "Hola"):
    ok(k in h, "la pantalla tiene: " + k)
src = open(os.path.join(RAIZ, "kira_portatil", "kiraos.py"), encoding="utf-8").read()
ok("--poner-pin" in src and "--quitar-pin" in src and "--partida" in src, "órdenes para el PIN opcional y la partida")

# ---------- si hay Chromium (playwright), se juega la escena de verdad ----------
node = shutil.which("node")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage(); const errs=[];
  pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2] + '#nacer');
  await pg.waitForSelector('#campo.on', {timeout: 25000});
  await pg.fill('#resp','Garru'); await pg.keyboard.press('Enter'); await pg.waitForTimeout(200);
  const v = await pg.inputValue('#resp'); await pg.fill('#resp','Jefe'); await pg.keyboard.press('Enter');
  await pg.waitForSelector('#partida.on', {timeout: 8000}); await pg.click('#empezar');
  const a = await pg.getAttribute('body','data-entrado');
  const pg2 = await b.newPage(); await pg2.goto('file://' + process.argv[2] + '#quedarse'); await pg2.waitForTimeout(700);
  await pg2.keyboard.press('a'); await pg2.waitForTimeout(4600);
  const s = await pg2.textContent('#hola'); const a2 = await pg2.getAttribute('body','data-entrado');
  console.log(JSON.stringify({v, a, s, a2, errs})); await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    f = os.path.join(T, "p.js")
    open(f, "w").write(js)
    r = subprocess.run([node, f, os.path.join(RAIZ, "kira_portatil", "kiraos_web", "arranque.html")],
                       capture_output=True, text=True, timeout=120)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(d["v"] == "Garru", "Chromium: la 2.ª pregunta ofrece tu nombre")
        ok(d["a"] == "1", "Chromium: tras la partida, entra")
        ok(d["s"] == "Hola, Jefe" and d["a2"] == "1", "Chromium: ya nacida y sin PIN → «Hola, Jefe» y entra")
        ok(d["errs"] == [], "Chromium: sin errores de JavaScript")
    else:
        print("(sin Chromium utilizable:", out or r.stderr[-200:], ")")

print("\nTODO BIEN", n)
