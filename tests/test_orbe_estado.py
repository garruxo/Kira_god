# -*- coding: utf-8 -*-
"""v3.09: el ORBE del escritorio dice qué hace Kira (Estudiando / Pensando / Programando / Trabajando / En pausa /
Sin tareas) y cuánto le queda a la tarea (estimado); «Mejoras» ya no está en el escritorio: se abre desde el Cuaderno."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
os.environ["KIRA_DATOS_NUCLEO"] = T
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import escritorio_kira as ek
import nucleo_portatil as npk

fallos = 0
n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


E = ek.estado_orbe
ahora = 10000.0
ok(E({}, ahora) == {"modo": "Sin tareas", "eta": ""}, "sin nada: «Sin tareas»")
ok(E({"actividad": {"pensando": True}}, ahora)["modo"] == "Pensando", "pensando sola")
ok(E({"actividad": {"estudiando": True}}, ahora)["modo"] == "Estudiando", "estudiando sola")
ok(E({"pausada": True}, ahora)["modo"] == "En pausa", "en pausa")
r = E({"ocupada": True, "haciendo": "estudia python", "fraccion": 0.25, "inicio": ahora - 300}, ahora)
ok(r == {"modo": "Estudiando", "eta": "termina en unos 15 min"}, "estudiando una orden: 5 min y 25 % → unos 15 min más: " + str(r))
r = E({"ocupada": True, "haciendo": "hazme una app android que cuente", "fraccion": 0.5, "inicio": ahora - 30,
       "en_cola": 2}, ahora)
ok(r["modo"] == "Programando" and r["eta"] == "termina en menos de 1 min · 2 en espera", "programando + en espera: " + str(r))
r = E({"ocupada": True, "haciendo": "busca la wifi", "fraccion": 0.0, "inicio": ahora}, ahora)
ok(r["eta"] == "calculando el tiempo…", "sin fracción aún: calculando")
r = E({"ocupada": True, "haciendo": "dime un chiste", "fraccion": 0.1, "inicio": ahora - 600}, ahora)
ok(r["modo"] == "Trabajando" and r["eta"] == "termina en 1 h 30 min", "trabajando, con horas: " + str(r))
ok(ek.texto_eta(20) == "menos de 1 min" and ek.texto_eta(3600 * 2 + 300) == "2 h 05 min", "cómo se dice el tiempo")


class CliN:
    def estado(self):
        return {"ocupada": True, "haciendo": "estudia redes", "fraccion": 0.5, "inicio": time.time() - 120,
                "en_cola": 0, "actividad": {}}


esc = ek.EscritorioMixin()
esc.cli = None
esc.nucleo_cli = CliN()
d = esc.trabajo()
ok(d["modo"] == "Estudiando" and d["eta"].startswith("termina en"), "el puente lo da a la pantalla: " + str(d))

# el núcleo da la fracción y el inicio de la tarea en curso
import threading
ev = threading.Event()
tb = npk.Trabajos(lambda o, paso: (paso(0.4, "a medias"), ev.wait(5), {"texto": "ok"})[-1])
nuc = npk.Nucleo.__new__(npk.Nucleo)
nuc.trabajos = tb
nuc.core = type("C", (), {"dir": T})()
tb.empezar("estudia algo")
lim = time.time() + 5
while time.time() < lim and not tb.ocupado():
    time.sleep(0.02)
time.sleep(0.1)
e = nuc.estado()
ok(e["ocupada"] and abs(e["fraccion"] - 0.4) < 1e-9 and e["inicio"] and e["avance"] == "a medias",
   "el núcleo da fracción, inicio y último paso")
ev.set()

ok("mejoras" not in [i["id"] for i in ek.ICONOS] and len(ek.ICONOS) == 11, "«Mejoras» ya no está en el escritorio")

node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(800);
  const iconos = await pg.$$eval('.icono', l => l.map(x => x.dataset.app));
  const modo1 = await pg.textContent('#orbeModo');
  await pg.evaluate(() => pintaTrabajo({nucleo:true, ocupada:true, haciendo:"estudia python", modo:"Estudiando",
                                        eta:"termina en unos 12 min · 1 en espera", en_cola:1}));
  const modo2 = await pg.textContent('#orbeModo'); const eta = await pg.textContent('#orbeEta');
  const ocupada = await pg.evaluate(() => document.querySelector('#fondo .orbe').classList.contains('ocupada'));
  await pg.screenshot({path: process.argv[3]});
  await pg.click('.icono[data-app="cuaderno"]'); await pg.waitForTimeout(400);
  await pg.click('[data-pest="mejoras"]'); await pg.waitForTimeout(150);
  const boton = await pg.textContent('[data-acc="app:mejoras"]');
  await pg.click('[data-pest="tareas"]'); await pg.waitForTimeout(150);
  const sinBoton = await pg.$$eval('[data-acc="app:mejoras"]', l => l.length);
  await pg.click('[data-pest="mejoras"]'); await pg.waitForTimeout(150);
  await pg.click('[data-acc="app:mejoras"]'); await pg.waitForTimeout(400);
  const titulo = await pg.textContent('#vtitulo');
  console.log(JSON.stringify({errs, iconos, modo1, modo2, eta, ocupada, boton, sinBoton, titulo}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    f = os.path.join(T, "o.js")
    open(f, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, f, html, os.path.join(T, "orbe.png")], capture_output=True, text=True, timeout=120, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok("mejoras" not in d["iconos"] and len(d["iconos"]) == 11, "Chromium: sin el icono Mejoras")
        ok(d["modo1"] == "Pensando", "Chromium: el orbe dice «Pensando»")
        ok(d["modo2"] == "Estudiando" and "12 min" in d["eta"] and d["ocupada"], "Chromium: «Estudiando» + tiempo estimado")
        ok("Instalar o deshacer" in d["boton"] and d["sinBoton"] == 0, "Chromium: el botón de Mejoras solo en su pestaña")
        ok(d["titulo"] == "Mejoras", "Chromium: desde el Cuaderno se abre la ventana Mejoras")
        print("  captura:", os.path.join(T, "orbe.png"))
    else:
        print("  (sin Chromium)", out[:200])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
