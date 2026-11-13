# -*- coding: utf-8 -*-
"""v3.28 (solo KiraOS): instalar apps que el dueño pide (GitHub, AppImage…), ponerlas en el escritorio con su icono,
usarlas cuando se lo ordene, y desinstalarlas con clic derecho. Sin administrador por defecto; nunca sola."""
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


import apps_externas_kira as aex

# ---------------- reconocer las órdenes ----------------
ok(aex.es_orden_instalar("instala https://github.com/foo/bar") == "https://github.com/foo/bar", "instala una URL de GitHub")
ok(aex.es_orden_instalar("Kira, instálame la app foo/bar") == "foo/bar", "instálame la app owner/repo")
ok(aex.es_orden_instalar("instala el github https://github.com/x/y") == "https://github.com/x/y", "instala el github …")
ok(aex.es_orden_instalar("pon gimp en el escritorio") == "gimp", "pon X en el escritorio")
ok(aex.es_orden_instalar("instala las mejoras") is None and aex.es_orden_instalar("instala la receta fuerza") is None,
   "no se mete con «instala las mejoras / la receta»")
ok(aex.es_orden_usar("abre krita") == "krita" and aex.es_orden_usar("usa la app foo") == "foo", "«abre/usa X»")
ok(aex.es_orden_usar("abre la sala hacker") is None and aex.es_orden_usar("abre el buscador") is None,
   "«abre la sala/el buscador» NO son apps externas")

# ---------------- cómo instalar ----------------
ok(aex.metodo("foo/bar") == "github" and aex.metodo("https://github.com/x/y") == "github", "GitHub")
ok(aex.metodo("https://x.com/Krita.AppImage") == "appimage", "AppImage")
ok(aex.metodo("gimp") == "nombre", "un nombre suelto = del sistema (apt)")
ok(aex._url_github("foo/bar") == "https://github.com/foo/bar.git", "owner/repo → URL de clonar")
ok(aex._nombre_de("https://github.com/foo/mi-cosa.git") == "mi cosa", "saca el nombre del repo")

# ---------------- instalar SIN administrador (git/appimage de mentira) ----------------
BASE = os.path.join(T, "apps")


def git_falso(args, cwd=None, timeout=0):
    # simula «git clone … <carpeta>»: crea la carpeta con un main.py
    carpeta = args[-1]
    os.makedirs(carpeta, exist_ok=True)
    open(os.path.join(carpeta, "main.py"), "w").write("print('hola')\n")
    return 0, ""


r = aex.instalar("foo/bar", base=BASE, correr=git_falso)
ok(r["ok"] and r["lanzar"][0] == "python3" and r["lanzar"][1].endswith("main.py") and os.path.isdir(r["carpeta"]),
   "instala de GitHub sin tocar el sistema y sabe arrancarla (main.py)")


def bajar_falso(url, destino):
    open(destino, "wb").write(b"#!/bin/sh\necho hola\n")
    return 10


r2 = aex.instalar("https://x.com/Krita.AppImage", base=BASE, bajar=bajar_falso)
ok(r2["ok"] and r2["lanzar"] == [os.path.join(r2["carpeta"], "Krita.AppImage")], "descarga un AppImage y lo deja ejecutable")

r3 = aex.instalar("gimp", base=BASE)
ok(not r3["ok"] and r3["admin"] and "contraseña" in r3["mensaje"].lower() and "apt" in r3["mensaje"].lower(),
   "un programa del sistema: NO lo instala sola, pide la Terminal con tu contraseña")

# lanzar (con un «correr» de mentira)
lanzado = []
rl = aex.lanzar({"titulo": "Foo", "lanzar": ["python3", "x.py"], "carpeta": BASE}, correr=lambda a, cwd=None, timeout=0: lanzado.append(a))
ok(rl["ok"] and lanzado and lanzado[0] == ["python3", "x.py"], "«usa X» lanza la app")

# ---------------- accesos: app externa en el escritorio + desinstalar borra su carpeta ----------------
import accesos_kira as ak

D = os.environ["KIRA_DATOS_NUCLEO"]
carp = os.path.join(D, "una_app")
os.makedirs(carp, exist_ok=True)
open(os.path.join(carp, "x"), "w").write("1")
iid = ak.anadir_externa(D, "Una App", ["bash", os.path.join(carp, "x")], carp)
a = ak.uno(D, iid)
ok(a and a["tipo"] == "externa" and a["lanzar"][0] == "bash", "queda como acceso directo de app externa")
ok(ak.quitar(D, iid) and not os.path.isdir(carp), "desinstalar borra su carpeta (y el icono)")
# candado: no borra una carpeta de FUERA de los datos
fuera = os.path.join(T, "importante")
os.makedirs(fuera, exist_ok=True)
iid2 = ak.anadir_externa(D, "Mala", ["x"], fuera)
ak.quitar(D, iid2)
ok(os.path.isdir(fuera), "candado: NUNCA borra una carpeta de fuera de los datos de Kira")

# ---------------- cableado del núcleo (con instalar/lanzar de mentira) ----------------
import nucleo_portatil as npmod


class Core:
    dir = D


aex.instalar = lambda fuente, **k: {"ok": True, "admin": False, "nombre": "Pepe", "lanzar": ["python3", "m.py"],
                                    "carpeta": os.path.join(D, "pepe"), "mensaje": "Pepe instalada."}
r = npmod._instalar_app(Core(), "foo/pepe", lambda *a, **k: None)
ok("instalada" in r["texto"].lower() and npmod._buscar_app(Core(), "pepe"), "el núcleo instala y deja el icono")
lan2 = []
aex.lanzar = lambda a, correr=None: (lan2.append(a.get("titulo")), {"ok": True, "mensaje": "Abriendo Pepe…"})[1]
r = npmod._usar_app(Core(), "pepe")
ok("abriendo" in r["texto"].lower() and lan2, "«usa Pepe» la lanza")

# el dispatch de ejecutar mira instalar/usar
src = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("es_orden_instalar" in src and "es_orden_usar" in src and "_instalar_app" in src, "ejecutar enruta instalar/usar apps")
# la pantalla lanza las apps externas y FUERA de casa no se permite instalar (permitida_fuera)
eks = open(os.path.join(RAIZ, "kira_portatil", "escritorio_kira.py"), encoding="utf-8").read()
ok("externa" in eks and "apps_externas_kira" in eks, "la pantalla lanza las apps externas al pulsarlas")

# ---------------- en la pantalla de verdad (Chromium) ----------------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e))); pg.on('dialog', d => d.accept());
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(300);
  await pg.evaluate(() => { FAKE._accesos=[{id:"krita",titulo:"Krita",icono:"app",tipo:"externa"}]; refrescaBarra(); });
  await pg.waitForTimeout(400);
  const icono = await pg.$('.icono[data-app="acceso:krita"]') ? true : false;
  await pg.click('.icono[data-app="acceso:krita"]'); await pg.waitForTimeout(400);
  const txt = await pg.textContent('#vcuerpo');
  const iframe = await pg.$('#vcuerpo iframe') ? true : false;
  await pg.evaluate(() => { document.getElementById("ventana").classList.remove("on"); actual=null; });
  await pg.click('.icono[data-app="acceso:krita"]', {button:'right'}); await pg.waitForTimeout(200);
  const menu = await pg.$('#menuAcceso') ? true : false;
  await pg.click('#menuAcceso [data-a="desinstalar"]'); await pg.waitForTimeout(300);
  const sigue = await pg.$('.icono[data-app="acceso:krita"]') ? true : false;
  console.log(JSON.stringify({errs, icono, txt, iframe, menu, sigue}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    fjs = os.path.join(T, "ae.js")
    open(fjs, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    rr = subprocess.run([node, fjs, html], capture_output=True, text=True, timeout=180, env=env)
    out = rr.stdout.strip().splitlines()[-1] if rr.stdout.strip() else ""
    if out.startswith("{"):
        import json as _j
        d = _j.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(d["icono"], "Chromium: la app externa aparece como icono en el escritorio")
        ok("Abriendo" in d["txt"] and not d["iframe"], "Chromium: al pulsarla se LANZA (no abre un iframe)")
        ok(d["menu"], "Chromium: clic derecho → menú (Abrir / Desinstalar)")
        ok(not d["sigue"], "Chromium: «Desinstalar» quita el icono")
    else:
        print("  (sin Chromium)", rr.stdout[-400:], rr.stderr[-200:])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
