# -*- coding: utf-8 -*-
"""v3.26 (solo KiraOS): cuando Kira crea un programa nuevo, deja un ACCESO DIRECTO con icono en el escritorio; al
pulsarlo abre el programa (su app web, aislada) y, con CLIC DERECHO, sale un menú para DESINSTALARLO (como en Windows)."""
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATOS_NUCLEO"] = os.path.join(T, "kira_datos")
os.makedirs(os.environ["KIRA_DATOS_NUCLEO"], exist_ok=True)
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))

n = fallos = 0


def ok(c, m):
    global n, fallos
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ---------------- accesos_kira (puro) ----------------
import accesos_kira as ak

D = os.path.join(T, "datos_acc")
os.makedirs(D, exist_ok=True)
iid = ak.anadir(D, "Calculadora de propinas", "print('propina:', 100*0.1)")
ok(iid and ak.existe(D, "Calculadora de propinas"), "crea el acceso directo del programa")
ok(os.path.exists(os.path.join(D, "apps", iid + ".html")), "guarda el programa como app web (para abrirlo)")
ok(ak.anadir(D, "Calculadora de propinas", "print(1)") is None, "no duplica el mismo programa")
iid2 = ak.anadir(D, "Otro juego", "print('hola')")
ok(len(ak.listar(D)) == 2 and ak.listar(D)[0]["id"] == iid2, "listar: del más nuevo al más viejo")
ok("Hola desde" not in (ak.html_de(D, iid) or "") and "<" in ak.html_de(D, iid), "html_de devuelve la app web")
ok(ak.quitar(D, iid) and not ak.existe(D, "Calculadora de propinas")
   and not os.path.exists(os.path.join(D, "apps", iid + ".html")), "desinstalar quita el acceso y borra su app web")
ok(not ak.quitar(D, "no_existe"), "desinstalar algo que no está no rompe")

# ---------------- núcleo: solo KiraOS crea el acceso al guardar un programa ----------------
import kira_god

core = kira_god.KiraGodCore()
# en el MÓVIL (es_kiraos falso) NO crea accesos de escritorio
core._guardar_solucion("programa del movil", codigo="print(1)")
ok(not ak.listar(core.dir), "en el móvil (no KiraOS) no deja accesos directos de escritorio")
# en KiraOS sí
core.es_kiraos = True
core._guardar_solucion("mi programa en kiraos", codigo="print('ok')")
acc = ak.listar(core.dir)
ok(len(acc) == 1 and "kiraos" in acc[0]["titulo"].lower(), "en KiraOS, cada programa nuevo deja su acceso directo")

# ---------------- puente del escritorio ----------------
import accesos_kira as ak2
DN = os.environ["KIRA_DATOS_NUCLEO"]
ak2.anadir(DN, "Programa de prueba", "print('hola')")
import kiraos  # noqa: E402

api = kiraos.Api(ruta_pin=os.path.join(T, "pin"))
lista = api.accesos()
ok(lista and lista[0]["titulo"] == "Programa de prueba" and "html" not in lista[0], "el escritorio lista los accesos (sin el html)")
ab = api.abrir_acceso(lista[0]["id"])
ok(ab.get("html") and "<" in ab["html"], "abrir_acceso devuelve la app web para mostrarla")
ok("accesos" in api.barra(), "barra() incluye los accesos (para pintar los iconos)")
ok(api.desinstalar_acceso(lista[0]["id"])["ok"] and not api.accesos(), "desinstalar_acceso lo quita")

# ---------------- en la pantalla de verdad (Chromium) ----------------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  pg.on('dialog', d => d.accept());                 // aceptar el confirm de «Desinstalar»
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(300);
  await pg.evaluate(() => { FAKE._accesos=[{id:"calc",titulo:"Calculadora",icono:"programa",tiene_html:true}]; refrescaBarra(); });
  await pg.waitForTimeout(400);
  const icono = await pg.$('.icono[data-app="acceso:calc"]') ? true : false;
  // abrir el programa
  await pg.click('.icono[data-app="acceso:calc"]'); await pg.waitForTimeout(400);
  const abre = await pg.$('#vcuerpo iframe') ? true : false;
  const bar = await pg.$('#vcuerpo .appbar') ? true : false;
  // cerrar la ventana para dejar el escritorio libre
  await pg.evaluate(() => { document.getElementById("ventana").classList.remove("on"); actual=null; });
  await pg.waitForTimeout(150);
  // clic derecho -> menú con Abrir / Desinstalar
  await pg.click('.icono[data-app="acceso:calc"]', {button:'right'}); await pg.waitForTimeout(200);
  const menu = await pg.$eval('#menuAcceso', m => m.textContent).catch(()=>'');
  // desinstalar
  await pg.click('#menuAcceso [data-a="desinstalar"]'); await pg.waitForTimeout(400);
  const sigue = await pg.$('.icono[data-app="acceso:calc"]') ? true : false;
  console.log(JSON.stringify({errs, icono, abre, bar, menu, sigue}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    fjs = os.path.join(T, "a.js")
    open(fjs, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, fjs, html], capture_output=True, text=True, timeout=180, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        import json as _j
        d = _j.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(d["icono"], "Chromium: el programa aparece como icono (acceso directo) en el escritorio")
        ok(d["abre"] and d["bar"], "Chromium: al pulsarlo abre el programa (su app web) en una ventana")
        ok("Desinstalar" in d["menu"] and "Abrir" in d["menu"], "Chromium: clic derecho → menú Abrir / Desinstalar (como Windows)")
        ok(not d["sigue"], "Chromium: «Desinstalar» quita el icono del escritorio")
    else:
        print("  (sin Chromium)", r.stdout[-500:], r.stderr[-300:])

# ---------------- cableado ----------------
kg = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
ok("accesos_kira" in kg and "es_kiraos" in kg, "kira_god crea el acceso al guardar una solución (solo KiraOS)")
npsrc = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok(npsrc.count("_crear_acceso(core") >= 2, "KiraOS crea el acceso también al escribir un programa / experimentar")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
