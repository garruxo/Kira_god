# -*- coding: utf-8 -*-
"""v3.17: (1) la VERSIÓN en el inicio de KiraOS (y si la pantalla, lo descargado y el núcleo no van iguales, avisa de
reiniciar); (2) la TERMINAL dentro de Kira: un bash de verdad, con contraseña en puntitos, Ctrl+C, Tab y los signos
que le faltan al teclado del dueño. Solo en el portátil (no por la red ni desde los marcos)."""
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
import terminal_kira as tk
import version_kira

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ---------- versión ----------
V = ek.estado_version
r = V("3.17", "3.17", "3.17")
ok(r["al_dia"] and r["texto"] == "KiraOS versión 3.17 · todo con la misma versión" and not r["aviso"], "todo igual: al día")
r = V("3.16", "3.17", "3.16")
ok(not r["al_dia"] and "descargada la 3.17" in r["aviso"] and "reinicia" in r["aviso"], "descargada pero sin reiniciar: avisa")
r = V("3.17", "3.17", "3.13")
ok(not r["al_dia"] and "núcleo va con la 3.13" in r["aviso"], "núcleo viejo (lo de la v3.11): avisa")
r = V("3.17", "3.17", None)
ok(r["al_dia"] and r["texto"] == "KiraOS versión 3.17", "sin núcleo: solo la versión")
ok(ek.VERSION_AL_ABRIR == version_kira.VERSION, "la pantalla sabe con qué versión se abrió")
ok(ek.version_en_disco() == version_kira.VERSION, "lee la versión descargada en el disco")
f = os.path.join(T, "v.py")
open(f, "w").write('VERSION = "9.99"\n')
ok(ek.version_en_disco(f) == "9.99" and ek.version_en_disco(os.path.join(T, "no")) is None, "versión en disco de un archivo")


class N:
    def hola(self):
        return {"version": "3.01"}


esc = ek.EscritorioMixin()
esc.cli = None
esc.nucleo_cli = N()
ok("núcleo va con la 3.01" in esc.version()["aviso"], "el puente pregunta la versión al núcleo")
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import kiraos
api = kiraos.Api.__new__(kiraos.Api)
api.cli, api.ruta_pin, api.ruta_nac = None, os.path.join(T, "pin"), os.path.join(T, "nac.json")
ok(api.info().get("version") == version_kira.VERSION, "el arranque (orbe) también recibe la versión")

# ---------- limpiar lo que sale de la terminal ----------
ok(tk.limpiar("\x1b[01;34mcarpeta\x1b[0m  archivo\r\n") == "carpeta  archivo\n", "sin colores ni \\r")
ok(tk.limpiar("10%\r50%\r100%\n") == "100%\n", "las barras de progreso dejan solo lo último")
ok(tk.limpiar("abc\x08\x08x") == "ax", "el retroceso borra")
ok(tk.pide_clave("bla\n[sudo] contraseña para papi: ") and tk.pide_clave("Password: "), "reconoce cuándo pide contraseña")
ok(not tk.pide_clave("papi@kiraos:~$ ") and not tk.pide_clave("la contraseña es fuerte\n$ "), "y cuándo no")

# ---------- una terminal DE VERDAD ----------
t = tk.Terminal(cwd=T)
t.iniciar()


def espera(cond, s=5):
    lim = time.time() + s
    while time.time() < lim:
        if cond():
            return True
        time.sleep(0.05)
    return False


ok(espera(lambda: "$ " in t.leer(0)["texto"]), "arranca bash con su prompt «…@kiraos:…$»")
t.escribir("echo hola-kira; printf 'a\\033[31mrojo\\033[0m\\n'")
ok(espera(lambda: "arojo" in t.leer(0)["texto"] and "hola-kira\n" in t.leer(0)["texto"]), "ejecuta y enseña la salida sin colores")
p = t.leer(0)["pos"]
t.escribir("mkdir -p sub && cd sub && pwd")
ok(espera(lambda: os.path.join(T, "sub") in t.leer(p)["texto"]), "«cd» se queda (es la misma terminal)")
ok(t.directorio() == os.path.join(T, "sub"), "sabe en qué carpeta está")
open(os.path.join(T, "sub", "documento_largo.txt"), "w").close()
c = t.completar("cat docu")
ok(c["linea"] == "cat documento_largo.txt ", "Tab completa un archivo: " + repr(c))
ok(t.completar("ech")["linea"].startswith("ech") and t.completar("zzzqqq")["linea"] == "zzzqqq", "Tab con órdenes y sin nada")
t.escribir("read -s -p 'Contraseña: ' x; echo; echo largo=${#x}")
ok(espera(lambda: t.leer(0)["clave"]), "cuando pide contraseña, la ventana lo sabe (puntitos)")
t.escribir("supersecreta", clave=True)
ok(espera(lambda: "largo=12" in t.leer(0)["texto"]), "la contraseña llega a Linux…")
ok("supersecreta" not in t.leer(0)["texto"], "…pero no se ve ni se guarda en la pantalla")
p = t.leer(0)["pos"]
t.escribir("sleep 30")
time.sleep(0.3)
t.tecla("ctrl_c")
t.escribir("echo sigo")
ok(espera(lambda: "sigo" in t.leer(p)["texto"], 4), "Ctrl+C corta un programa y la terminal sigue")
t.limpiar_pantalla()
ok(t.leer(t.leer(0)["pos"])["texto"] == "", "limpiar deja la pantalla vacía")
viejo = tk.MAX_BUFFER
tk.MAX_BUFFER = 2000
t.escribir("seq 1 3000")
ok(espera(lambda: "3000" in t.leer(0)["texto"]), "mucha salida")
r = t.leer(0)
ok(len(r["texto"]) <= 2100 and r["reinicio"], "guarda solo lo último (lo viejo se tira) y avisa al pedir desde atrás")
tk.MAX_BUFFER = viejo
t.escribir("exit")
ok(espera(lambda: not t.leer(0)["vivo"]), "al salir de bash, la terminal se cierra")
ok("pulsa «Nueva»" in t.leer(0)["texto"], "y dice cómo abrir otra")

# puente
esc2 = ek.EscritorioMixin()
esc2.cli = None
os.environ["HOME"] = T
r = esc2.terminal_abrir()
ok(r["vivo"], "el escritorio abre su terminal")
esc2.terminal_escribir("echo desde-el-puente")
ok(espera(lambda: "desde-el-puente\n" in esc2.terminal_leer(0)["texto"]), "escribe y lee por el puente")
r = esc2.terminal_nueva()
ok(r["vivo"] and "desde-el-puente" not in r["texto"], "«Nueva» empieza otra limpia")
esc2._terminal.cerrar()

# solo en el portátil: no está en el servidor del núcleo ni la pueden pedir los marcos (mapa/programando)
fuente_nucleo = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("terminal" not in fuente_nucleo.lower(), "el servidor del núcleo (red/móvil) no tiene terminal")
html = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html"), encoding="utf-8").read()
ok('["mapa_ataques","mapa_mundo","programando_datos"].indexOf(d.metodo)<0' in html, "los marcos solo pueden pedir sus datos, no la terminal")
ok([i["id"] for i in ek.ICONOS].count("terminal") == 1 and len(ek.ICONOS) == 11, "icono «Terminal» en el escritorio")

# ---------- en la pantalla de verdad (Chromium) ----------
node = shutil.which("node")
h = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
arr = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "arranque.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(900);
  const ver = await pg.textContent('#version');
  await pg.evaluate(() => { FAKE._ver={version:"3.16",aviso:"Ya tengo descargada la 3.17, pero esta pantalla aún va con la 3.16: reinicia el portátil para estrenarla.",al_dia:false}; pintaVersion(); });
  await pg.waitForTimeout(200);
  const aviso = await pg.textContent('#version'); const esAviso = await pg.$eval('#version', x => x.classList.contains('aviso'));
  await pg.click('.icono[data-app="terminal"]'); await pg.waitForTimeout(700);
  const titulo = await pg.textContent('#vtitulo');
  await pg.click('[data-k="."]'); await pg.click('[data-k="/"]');
  await pg.type('#termIn', 'ls'); await pg.keyboard.press('Enter'); await pg.waitForTimeout(900);
  const sal1 = await pg.textContent('#termSal');
  await pg.type('#termIn', 'sudo ls'); await pg.keyboard.press('Enter'); await pg.waitForTimeout(900);
  const tipo = await pg.$eval('#termIn', x => x.classList.contains('secreto') && getComputedStyle(x).webkitTextSecurity==='disc' ? 'password' : x.type);
  await pg.type('#termIn', 'mi-clave'); await pg.keyboard.press('Enter'); await pg.waitForTimeout(900);
  const sal2 = await pg.textContent('#termSal');
  await pg.focus('#termIn'); await pg.keyboard.press('ArrowUp'); await pg.keyboard.press('ArrowUp');
  const hist = await pg.$eval('#termIn', x => x.value);
  await pg.keyboard.press('Escape'); await pg.waitForTimeout(300);
  const cerrada = await pg.evaluate(() => !document.getElementById('ventana').classList.contains('on'));
  const p2 = await b.newPage(); p2.on('pageerror', e => errs.push(String(e)));
  await p2.addInitScript(() => { window.pywebview={api:{info:()=>Promise.resolve({nacida:true,llamar:"Jefe",cerebro:"Qwen3.5 2B",version:"3.17"}),
     entrar:()=>Promise.resolve(true)}}; });
  await p2.goto('file://' + process.argv[3] + '#quedarse'); await p2.waitForTimeout(900);
  const pie = await p2.textContent('#foot');
  console.log(JSON.stringify({errs, ver, aviso, esAviso, titulo, sal1, tipo, sal2, hist, cerrada, pie}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    fjs = os.path.join(T, "t.js")
    open(fjs, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, fjs, h, arr], capture_output=True, text=True, timeout=180, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok("KiraOS versión 3.17" in d["ver"], "Chromium: la versión se ve en el inicio: " + d["ver"])
        ok(d["esAviso"] and "reinicia" in d["aviso"], "Chromium: y si no va al día, el aviso resaltado")
        ok(d["titulo"] == "Terminal" and "(ejemplo) ./ls" in d["sal1"], "Chromium: la terminal ejecuta (con los signos . y / de los botones)")
        ok(d["tipo"] == "password" and "mi-clave" not in d["sal2"], "Chromium: la contraseña va en puntitos y no se ve")
        ok(d["hist"] == "./ls", "Chromium: flecha arriba = órdenes anteriores (sin la contraseña): " + d["hist"])
        ok(d["cerrada"], "Chromium: Escape vuelve al escritorio")
        ok("KiraOS versión 3.17" in d["pie"], "Chromium: el orbe del arranque también dice la versión: " + d["pie"])
    else:
        print("  (sin Chromium)", r.stdout[-800:], r.stderr[-400:])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
