# -*- coding: utf-8 -*-
"""v2.98: menú K de KiraOS. (1) ARREGLO: Apagar y Reiniciar piden dos toques, pero al pintar «¿Seguro? Toca otra
vez» el menú se cerraba solo (el clic parecía «fuera») y el segundo toque nunca llegaba. (2) Apagar/reiniciar prueban
varias formas hasta que una funcione y, si ninguna, lo dicen claro. (3) Botón nuevo «Ir a Xubuntu»: cierra la
ventana de KiraOS (como Alt+F4)."""
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
import escritorio_kira as ek  # noqa: E402

n = 0


def ok(c, m):
    global n
    n += 1
    print(("[OK] " if c else "[X] ") + m)
    if not c:
        sys.exit(1)


class Api(ek.EscritorioMixin):
    cli = None


api = Api()

# ---------- apagar / reiniciar: varias formas, por orden ----------
probadas = []


def falla_systemctl(orden):
    probadas.append(orden[0])
    if orden[0] == "systemctl":
        return 1, "Failed to power off system via logind: Access denied"
    return 0, ""


r = api.sistema("apagar", correr=falla_systemctl)
ok(r["ok"] and probadas == ["systemctl", "xfce4-session-logout"],
   "si systemctl no deja, prueba la salida de la sesión de Xubuntu")
probadas.clear()
r = api.sistema("reiniciar", correr=falla_systemctl)
ok(r["ok"] and probadas == ["systemctl", "xfce4-session-logout"], "y lo mismo al reiniciar")
ok(api.ORDENES_SISTEMA["reiniciar"][1] == ["xfce4-session-logout", "--reboot", "--fast"]
   and api.ORDENES_SISTEMA["apagar"][1] == ["xfce4-session-logout", "--halt", "--fast"], "órdenes de Xubuntu correctas")
r = api.sistema("apagar", correr=lambda o: (1, "Access denied"))
ok(not r["ok"] and "Access denied" in r["texto"] and "Ir a Xubuntu" in r["texto"],
   "si ninguna funciona, lo dice (con el motivo) y cómo hacerlo a mano")
r = api.sistema("apagar", correr=lambda o: (_ for _ in ()).throw(OSError("sin dbus")))
ok(not r["ok"] and "sin dbus" in r["texto"], "un error raro tampoco revienta")
ok(not api.sistema("formatear", correr=lambda o: None)["ok"], "nada de órdenes raras")
ok(ek.EscritorioMixin._correr_sistema(["no_existe_esta_orden_kira"])[0] == 127, "una herramienta que falta no revienta")

# ---------- Ir a Xubuntu ----------
cerrada = []


class Ventana:
    def destroy(self):
        cerrada.append(True)


api._ventana = Ventana()
r = api.sistema("salir")
ok(r["ok"] and "Xubuntu" in r["texto"] and "Kira" in r["texto"], "Ir a Xubuntu: dice cómo volver")
time.sleep(1.0)
ok(cerrada == [True], "y cierra la ventana de KiraOS (tras contestar)")
api2 = Api()
ok(not api2.sistema("salir")["ok"] and "Alt + F4" in api2.sistema("salir")["texto"], "sin ventana: explica Alt + F4")

# ---------- el menú de verdad (Chromium) ----------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(800);
  await pg.evaluate(() => { window._ll=[]; const o=FAKE.sistema; FAKE.sistema=function(a){ _ll.push(a); return o(a); }; });
  const out = {};
  async function menu(){ if(!(await pg.evaluate(() => document.getElementById('menu').classList.contains('on')))) await pg.click('#btnKira'); await pg.waitForTimeout(150); }
  await menu();
  out.opciones = await pg.$$eval('#menu .op', l => l.map(x => x.textContent));
  await pg.click('#menu [data-sis="apagar"]'); await pg.waitForTimeout(150);
  out.abiertoTras1 = await pg.evaluate(() => document.getElementById('menu').classList.contains('on'));
  out.seguro = await pg.textContent('#menu [data-sis="apagar"]');
  out.llamadasTras1 = await pg.evaluate(() => _ll.slice());
  await pg.click('#menu [data-sis="apagar"]'); await pg.waitForTimeout(200);
  out.llamadasTras2 = await pg.evaluate(() => _ll.slice());
  await menu(); await pg.click('#menu [data-sis="reiniciar"]'); await pg.waitForTimeout(150);
  await pg.click('#menu [data-sis="reiniciar"]'); await pg.waitForTimeout(200);
  await menu(); await pg.click('#menu [data-sis="salir"]'); await pg.waitForTimeout(200);
  out.llamadas = await pg.evaluate(() => _ll.slice());
  out.cerradoTrasSalir = !(await pg.evaluate(() => document.getElementById('menu').classList.contains('on')));
  await menu(); await pg.mouse.click(700, 300); await pg.waitForTimeout(150);
  out.cierraFuera = !(await pg.evaluate(() => document.getElementById('menu').classList.contains('on')));
  out.errs = errs; console.log(JSON.stringify(out)); await b.close();
})().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    f = os.path.join(T, "m.js")
    open(f, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, f, html], capture_output=True, text=True, timeout=120, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok("Ir a Xubuntu" in d["opciones"], "Chromium: el menú K tiene «Ir a Xubuntu»")
        ok(d["abiertoTras1"] and "Seguro" in d["seguro"] and d["llamadasTras1"] == [],
           "Chromium: tras el 1.er toque el menú SIGUE abierto y pregunta «¿Seguro?» (antes se cerraba)")
        ok(d["llamadasTras2"] == ["apagar"], "Chromium: el 2.º toque apaga de verdad")
        ok(d["llamadas"] == ["apagar", "reiniciar", "salir"], "Chromium: reiniciar (dos toques) e Ir a Xubuntu (uno)")
        ok(d["cerradoTrasSalir"] and d["cierraFuera"], "Chromium: el menú se cierra al salir y al pulsar fuera")
    else:
        print("(sin Chromium utilizable: me salto la pantalla)", out[:200])

print("\nTODO BIEN", n)
