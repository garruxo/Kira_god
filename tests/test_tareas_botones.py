# -*- coding: utf-8 -*-
"""v3.10: la pestaña Tareas del cuaderno: en TERMINADAS dice si se implementó, se mejoró o falló (y por qué); cada
tarea de ACTIVAS / EN ESPERA / TERMINADAS tiene Parar · Borrar · Empezar; borrar una que espera la pasa a
Terminadas como «Quitada». Núcleo de verdad (cola), puente, servidor y la pantalla en Chromium."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
os.environ["KIRA_DATOS_NUCLEO"] = T
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import cuaderno_clases_kira as cc
import investigar_kira as iv
import nucleo_portatil as npk

fallos = 0
n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


R = cc.resultado_tarea
ok(R("hecho", "[OK] Me he puesto 3 mejora(s) (versión 3.08 → 3.09)")[0] == "Implementado", "«me he puesto…» = Implementado")
ok(R("hecho", "[OK] Mejora 'x' aplicada. YA ESTÁ INSTALADA.")[0] == "Implementado", "instalada = Implementado")
ok(R("hecho", "He mejorado el código: versión más rápida")[0] == "Mejorado", "mejorado = Mejorado")
e, p = R("hecho", "No he podido ponerme las mejoras: sin internet. No he cambiado nada.")
ok(e == "Falló" and p.startswith("No hizo nada:") and "sin internet" in p, "falló: «No hizo nada» + por qué")
ok(R("error", "[x] se cayó la red")[1] == "No hizo nada: se cayó la red", "error: por qué")
ok(R("hecho", "Mejora «x» aprobada. NO la he instalado: ábrela…")[0] == "Preparado (espera tu permiso)", "espera permiso")
ok(R("hecho", "Ya tengo todas las mejoras: soy la versión 3.09.")[0] == "Nada que hacer", "ya al día: nada que hacer")
ok(R("cancelado", "Parado.")[0] == "Parada" and R("quitado")[0] == "Quitada", "parada / quitada")
ok(R("hecho", "Programa escrito y probado.")[0] == "Hecho", "lo demás: Hecho")

# ---------- la cola de verdad ----------
puerta = threading.Event()
hechas = []


def hacer(orden, paso):
    if orden == "lenta":
        paso(0.3, "a medias")
        puerta.wait(10)
        raise type("Cancelada", (Exception,), {})("parada")
    hechas.append(orden)
    if orden == "falla":
        return {"texto": "No me ha salido: sin cerebro", "ok": False}
    return {"texto": "[OK] Me he puesto 1 mejora(s)"}


core = types.SimpleNamespace(dir=T, cancelar=lambda: puerta.set())
nuc = npk.Nucleo.__new__(npk.Nucleo)
nuc.core = core
nuc.trabajos = npk.Trabajos(hacer)
tb = nuc.trabajos


def espera(cond, s=5):
    lim = time.time() + s
    while time.time() < lim and not cond():
        time.sleep(0.02)
    return cond()


lenta = tb.empezar("lenta")
espera(lambda: tb.ocupado())
a = tb.empezar("primera")
bq = tb.empezar("segunda")
c = tb.empezar("tercera")
lista = tb.lista()
ok([x["estado"] for x in lista] == ["en curso", "en cola", "en cola", "en cola"] and all(x.get("id") for x in lista),
   "la lista lleva el id de cada tarea")
r = nuc.tarea_accion(bq, "borrar")
ok(r["ok"] and bq not in tb.cola, "Borrar una que espera la saca de la cola")
h = {x["id"]: x for x in tb.hechas()}
ok(h[bq]["estado"] == "quitado" and h[bq]["resultado"] == "Quitada" and "antes de empezar" in h[bq]["por_que"],
   "…y sale en Terminadas como «Quitada», con el porqué")
ok(nuc.tarea_accion(a, "parar")["ok"] and tb.tareas[a]["retenida"], "Parar una que espera: se queda parada")
ok(nuc.tarea_accion(c, "empezar")["ok"] and tb.cola[0] == c, "Empezar una que espera: pasa la primera")
ok("Ya la estoy" in nuc.tarea_accion(lenta, "empezar")["texto"], "Empezar la que ya hace: lo dice")
nuc.tarea_accion(lenta, "parar")
espera(lambda: "tercera" in hechas)
time.sleep(0.2)
h = {x["id"]: x for x in tb.hechas()}
ok(h[lenta]["resultado"] == "Parada", "Parar la que hace: acaba como «Parada»")
ok(h[c]["resultado"] == "Implementado", "la tercera se hizo: Implementado")
ok("primera" not in hechas and a in tb.cola, "la parada sigue esperando y NO se hace")
nuc.tarea_accion(a, "empezar")
espera(lambda: "primera" in hechas)
ok("primera" in hechas, "Empezar la parada: se hace")
f = tb.empezar("falla")
espera(lambda: tb.tareas.get(f, {}).get("estado") == "hecho")
time.sleep(0.1)
ok(tb.tareas[f]["resultado"] == "Falló" and "sin cerebro" in tb.tareas[f]["por_que"], "si falla, «Falló» y por qué")
r = nuc.tarea_accion(f, "empezar")
ok(r["ok"] and r.get("id"), "Empezar una terminada: la vuelve a hacer")
espera(lambda: hechas.count("falla") == 2)
ok(nuc.tarea_accion(c, "borrar")["ok"] and c not in tb.tareas, "Borrar una terminada la quita de la lista")
ok(not nuc.tarea_accion("nada", "parar")["ok"], "una que no existe: lo dice")

# ---------- servidor (solo en el portátil) ----------
srv = npk.crear_servidor("127.0.0.1", 0, "tok", nuc)
threading.Thread(target=srv.serve_forever, daemon=True).start()
cli = npk.ClienteNucleo(f"http://127.0.0.1:{srv.server_address[1]}", "tok")
x = tb.empezar("lenta")
espera(lambda: tb.ocupado())
y = tb.empezar("cuarta")
ok(cli.tarea_accion(y, "borrar")["ok"] and y not in tb.cola, "por el servidor: Borrar")
import urllib.error
viejo = npk.es_local
npk.es_local = lambda ip: False
try:
    cli.tarea_accion(x, "parar")
    ok(False, "desde fuera no")
except urllib.error.HTTPError as e:
    ok(e.code == 403, "desde el móvil: 403")
finally:
    npk.es_local = viejo
cli.tarea_accion(x, "parar")
srv.shutdown()

# ---------- filas con botones ----------
tr = {"cola": [{"id": "c1", "orden": "estudia python", "estado": "en curso"},
               {"id": "e1", "orden": "kira implementa las mejoras", "estado": "en cola"},
               {"id": "e2", "orden": "otra", "estado": "en cola", "retenida": True}],
      "hechas": [{"id": "h1", "orden": "mejorar asyncio", "estado": "hecho", "resultado": "Mejorado",
                  "por_que": "versión más rápida", "fin": time.time() - 240}],
      "pausada": True, "actividad": {"pensando": True}}
enc = [{"texto": "qué es un hash", "hecha": False}, {"texto": "grep", "hecha": True}]
fl = cc.filas_tareas(tr, enc, {})
secc = {}
for fx in fl:
    secc.setdefault(fx["seccion"], []).append(fx)
ok(all(len(fx["botones"]) == 3 and [b["texto"] for b in fx["botones"]] == ["Parar", "Borrar", "Empezar"] for fx in fl),
   "TODAS las filas llevan Parar · Borrar · Empezar")
ok(any("En pausa" in fx["texto"] for fx in secc["activas"]) and any(fx["texto"] == "estudia python" for fx in secc["activas"]),
   "Activas: la pausa y la de curso")
c1 = next(fx for fx in secc["activas"] if fx["texto"] == "estudia python")
ok(c1["botones"][0]["accion"] == "hacer:tarea:parar:c1" and c1["botones"][2].get("off"), "la de curso: Parar sí, Empezar no")
e2 = next(fx for fx in secc["espera"] if fx["texto"] == "otra")
ok(e2["botones"][0].get("off") and "Empezar" in e2["detalle"], "una parada en espera lo dice")
ok(any(fx["texto"].startswith("Encargo: qué es un hash") for fx in secc["espera"]), "tus encargos en espera")
h1 = next(fx for fx in secc["terminadas"] if fx["texto"] == "mejorar asyncio")
ok(h1["etiqueta"] == "Mejorado" and "hace 4 min" in h1["detalle"] and "versión más rápida" in h1["detalle"]
   and h1["botones"][0].get("off"), "Terminadas: Mejorado, cuándo y por qué")
ok(all(b.get("dos") for fx in secc["espera"] for b in fx["botones"] if b["texto"] == "Borrar"),
   "Borrar en espera pide dos toques")

# ---------- encargos ----------
iv.anadir(T, "qué es un hash")
iv.anadir(T, "qué es un árbol")
ok(iv.adelantar(T, 1) == "qué es un árbol" and iv.listar(T)[0]["texto"] == "qué es un árbol", "Empezar un encargo: el primero")
ok(iv.quitar(T, 0) == "qué es un árbol" and len(iv.listar(T)) == 1, "Borrar un encargo")

# ---------- el puente ----------
import escritorio_kira as ek


class CliN:
    def __init__(self):
        self.hechas = []

    def estado(self):
        return tr

    def mejoras(self):
        return {"pendiente": None, "instaladas": []}

    def tarea_accion(self, tid, acc):
        self.hechas.append((tid, acc))
        return {"ok": True, "texto": "hecho"}


esc = ek.EscritorioMixin()
esc.cli = None
esc.nucleo_cli = CliN()
a = esc.app("cuaderno")
tar = next(p for p in a["pestanas"] if p["id"] == "tareas")
ok(tar.get("filas") and tar["botones"] == [], "la pestaña Tareas trae filas con botones")
ok(esc.app_hacer("cuaderno", "tarea:borrar:e1")["refrescar"] and esc.nucleo_cli.hechas[-1] == ("e1", "borrar"),
   "el botón llega al núcleo")
ok("primero" in esc.app_hacer("cuaderno", "encargo:empezar:0")["texto"], "encargo: Empezar")
ok(esc.app_hacer("cuaderno", "rm:-rf")["texto"] == "No conozco ese botón.", "botones raros no")

node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(600);
  await pg.click('.icono[data-app="cuaderno"]'); await pg.waitForTimeout(400);
  await pg.click('[data-pest="tareas"]'); await pg.waitForTimeout(200);
  const secc = await pg.$$eval('.secc h4', l => l.map(x => x.textContent));
  const filas = await pg.$$eval('.fila', l => l.length);
  const bots = await pg.$$eval('.fila', l => Array.from(l[0].querySelectorAll('.fbot button')).map(x => x.textContent));
  const etq = await pg.textContent('.etq');
  const off = await pg.$$eval('.b.mini.off', l => l.length);
  await pg.click('[data-acc="hacer:tarea:borrar:a1"]'); await pg.waitForTimeout(100);
  const tras1 = await pg.textContent('[data-acc="hacer:tarea:borrar:a1"]');
  await pg.click('[data-acc="hacer:tarea:borrar:a1"]'); await pg.waitForTimeout(400);
  const res = await pg.evaluate(() => (document.getElementById('resultado')||{}).textContent || '');
  await pg.screenshot({path: process.argv[3]});
  console.log(JSON.stringify({errs, secc, filas, bots, etq, off, tras1, res}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    f = os.path.join(T, "t.js")
    open(f, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, f, html, os.path.join(T, "tareas.png")], capture_output=True, text=True, timeout=120,
                       env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(d["secc"] == ["Activas (0)", "En espera (1)", "Terminadas (1)"], "Chromium: las tres listas " + str(d["secc"]))
        ok(d["filas"] == 2 and d["bots"] == ["Parar", "Borrar", "Empezar"], "Chromium: cada fila con sus tres botones")
        ok(d["etq"] == "Mejorado" and d["off"] >= 1, "Chromium: la etiqueta del resultado y botones apagados")
        ok("Seguro" in d["tras1"] and "borrar" in d["res"], "Chromium: Borrar con dos toques")
        print("  captura:", os.path.join(T, "tareas.png"))
    else:
        print("  (sin Chromium)", out[:200])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
