# -*- coding: utf-8 -*-
"""v2.95: en el escritorio de KiraOS se VE cuándo está ocupada (y cuántas tareas esperan), y hay botones de PARAR y
de PAUSAR / SEGUIR. El puente se prueba con un núcleo de mentira; la pantalla, en Chromium si hay playwright."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp()
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
import escritorio_kira as ek  # noqa: E402

n = 0


def ok(c, m):
    global n
    n += 1
    print(("[OK] " if c else "[X] ") + m)
    if not c:
        sys.exit(1)


class NucleoFalso:
    def __init__(self):
        self.e = {"ocupada": True, "haciendo": "estudia Python", "en_cola": 3, "pausada": False, "cola": [],
                  "actividad": {"pensando": True}}
        self.llamadas = []

    def estado(self):
        self.llamadas.append("estado")
        return dict(self.e)

    def cancelar(self):
        self.llamadas.append("cancelar")
        self.e.update(ocupada=False, haciendo="")
        return {"ok": True}

    def pausar(self, si=True):
        self.llamadas.append(("pausar", si))
        self.e["pausada"] = bool(si)
        return {"pausada": bool(si)}

    def seguir(self):
        return self.pausar(False)


class Api(ek.EscritorioMixin):
    cli = None


api = Api()
nf = NucleoFalso()
api.nucleo_cli = nf
d = api.trabajo()
ok(d["nucleo"] and d["ocupada"] and d["en_cola"] == 3 and d["que"] == "estudia Python",
   "la barra sabe que está ocupada, con qué, y cuántas esperan")
api.trabajo()
ok(nf.llamadas.count("estado") == 1, "se guarda 2,5 s (no machaca al núcleo)")
r = api.parar()
ok(r["ok"] and "cancelar" in nf.llamadas, "el botón Parar corta lo de ahora")
d = api.trabajo()
ok(not d["ocupada"] and d["que"] == "pensando", "tras parar: ya no está ocupada; se ve que piensa por su cuenta")
ok(api.pausar_trabajo(True)["pausada"] is True and api.trabajo()["pausada"] is True, "Pausar")
ok(api.pausar_trabajo(False)["pausada"] is False and ("pausar", False) in nf.llamadas, "Seguir")

api2 = Api()
api2.nucleo_cli = None
ok(api2.trabajo()["nucleo"] is False, "sin núcleo, la barra no enseña nada raro")
ok(api2.parar()["ok"] is False, "sin núcleo, parar dice que no hay tarea")

src = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok('"/pausar"' in src and '"/seguir"' in src and '"/estado"' in src, "el núcleo tiene /estado, /pausar y /seguir")
ok("409" not in src.split('if u.path == "/orden":')[1].split('if u.path == "/pausar":')[0],
   "/orden ya no contesta 409: encola")

# el MÓVIL también entiende «en cola» (antes lo tomaba por acabado y salía como error)
cs = open(os.path.join(RAIZ, "casa_kira.py"), encoding="utf-8").read()
ok('not in ("en curso", "en cola")' in cs, "el móvil espera mientras su orden está en cola en KiraOS")
kg = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
ok('est in ("en curso", "en cola")' in kg, "el historial del móvil no marca como error una orden en cola")
import casa_kira as ck  # noqa: E402
c = ck.Casa()
estados = iter([{"estado": "en cola"}, {"estado": "en cola"}, {"estado": "en curso"}, {"estado": "hecho", "respuesta": "listo"}])
c._nucleo = lambda ruta, datos=None, **k: {"id": "t1"} if ruta == "/orden" else next(estados)
ok(c.orden("estudia Python", dormir=lambda s: None)["respuesta"] == "listo", "el móvil espera su turno y recoge la respuesta")

# ---------- la pantalla de verdad ----------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(900);
  const libreVisible = await pg.isVisible('#trabajo');
  const libreTexto = await pg.textContent('#trabQué');
  await pg.evaluate(() => { FAKE._trab = {nucleo:true,ocupada:true,haciendo:"estudia Python",en_cola:3,pausada:false,que:"estudia Python"}; refrescaTrabajo(); });
  await pg.waitForTimeout(300);
  const ocupTexto = await pg.textContent('#trabQué'); const cuantas = await pg.textContent('#trabCuantas');
  const pararVis = await pg.isVisible('#trabParar');
  await pg.screenshot({path: process.argv[3]});
  await pg.click('#trabParar'); await pg.waitForTimeout(300);
  const trasParar = await pg.isVisible('#trabParar');
  await pg.click('#trabPausar'); await pg.waitForTimeout(300);
  const pausaBoton = await pg.textContent('#trabPausar'); const pausaTexto = await pg.textContent('#trabQué');
  const pausaClase = await pg.evaluate(() => document.getElementById('trabajo').classList.contains('pausa'));
  await pg.click('#trabPausar'); await pg.waitForTimeout(300);
  const sigueBoton = await pg.textContent('#trabPausar');
  console.log(JSON.stringify({errs, libreVisible, libreTexto, ocupTexto, cuantas, pararVis, trasParar, pausaBoton,
                              pausaTexto, pausaClase, sigueBoton}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    f = os.path.join(T, "c.js")
    open(f, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, f, html, os.path.join(T, "ocupada.png")], capture_output=True, text=True, timeout=120,
                       env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(d["libreVisible"] and "pensando" in d["libreTexto"], "Chromium: se ve lo que hace por su cuenta («pensando»)")
        ok("Ocupada" in d["ocupTexto"] and "estudia Python" in d["ocupTexto"] and "3 en espera" in d["cuantas"],
           "Chromium: «Ocupada: estudia Python · 3 en espera»")
        ok(d["pararVis"] and not d["trasParar"], "Chromium: el botón Parar sale cuando está ocupada y se va al parar")
        ok(d["pausaBoton"] == "Seguir" and d["pausaTexto"] == "En pausa" and d["pausaClase"],
           "Chromium: Pausar la deja «En pausa» y el botón pasa a «Seguir»")
        ok(d["sigueBoton"] == "Pausar", "Chromium: Seguir la vuelve a poner a trabajar")
        shutil.copy(os.path.join(T, "ocupada.png"), "/tmp/claude-0/-home-claude/c4932b0e-9cad-5b68-a590-3e4b8a3549d8/scratchpad/ocupada.png") if os.path.isdir("/tmp/claude-0/-home-claude/c4932b0e-9cad-5b68-a590-3e4b8a3549d8/scratchpad") else None
    else:
        print("(sin Chromium utilizable: me salto la pantalla)", out[:200])

print("\nTODO BIEN", n)
