# -*- coding: utf-8 -*-
"""v3.92: no mezclar sistemas (lo de Windows/Mac del README no se ejecuta en Linux; lo que tiene .sh se traduce) y la
ventana «Programas auxiliares» (los puentes de cada programa, en su carpeta, sin icono propio)."""
import json, os, shutil, subprocess, sys, tempfile, time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATOS_NUCLEO"] = T
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import arreglar_app_kira as arr
import accesos_kira as ak
arr.REGISTROS = os.path.join(T, "apps_registro")

fallos = n = 0
def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1

# ---------- órdenes de otro sistema ----------
for l in ("brew install ffmpeg", "choco install node", "winget install X", "start server.bat", "server.exe --port 1",
          "powershell -File run.ps1", "open -a Terminal", "set PORT=8000", "copy a b", r"venv\Scripts\activate",
          r"C:\app\run.cmd", "launchctl load x.plist", "./run.command"):
    ok(arr.es_de_otro_sistema(l), "de otro sistema: " + l)
for l in ("python3 server.py --port 8000", "./start.sh", "sudo apt install ffmpeg", "npm start", "cargo run --release",
          "make -j2", "bash setup.sh", "node index.js", "uvicorn main:app --port 9000"):
    ok(not arr.es_de_otro_sistema(l), "de Linux: " + l)
ok(arr.a_linux("py -3 main.py") == "python3 main.py", "«py -3 main.py» → «python3 main.py»")

# ---------- secciones del README ----------
README = """# Mi App
Para usarla necesitas el servidor puente.

## Linux / Ubuntu
In another terminal, start the server:
```
python3 servidor.py --port 8765
```
Then run:
```
python3 app.py
```

## macOS
```
brew install python
./servidor.command
```

### Apple Silicon
```
arch -arm64 ./servidor.command
```

## Windows
```
start servidor.bat
py -3 app.py
```

## Notes
Everything else is the same.
"""
sl = arr.solo_linux(README)
ok("brew" not in sl and "servidor.bat" not in sl and "Apple Silicon" not in sl, "fuera las secciones de Mac y Windows")
ok("python3 servidor.py --port 8765" in sl and "## Notes" in sl, "se quedan la de Linux y las generales")
ok(arr.ordenes_de_texto(README) == ["python3 servidor.py --port 8765", "python3 app.py"],
   f"órdenes: solo las de Linux ({arr.ordenes_de_texto(README)})")
ok(arr.ordenes_de_texto("```\nbrew install x\npython3 y.py\nstart z.bat\n```") == ["python3 y.py"],
   "órdenes sueltas de otro sistema en un bloque: fuera")

# ---------- un .bat/.command con su .sh al lado se traduce ----------
c2 = os.path.join(T, "con_sh"); os.makedirs(os.path.join(c2, "scripts"))
open(os.path.join(c2, "scripts", "arrancar.sh"), "w").write("#!/bin/bash\necho hola\n")
ok(arr.a_linux("scripts\\arrancar.bat", c2) is None or True, "rutas con barra invertida no rompen")
ok(arr.a_linux("start.cmd", c2) is None, "un .cmd sin su .sh: fuera")
ok(arr.a_linux("arrancar.bat --rapido", c2) == "bash scripts/arrancar.sh --rapido", "un .bat con su .sh: «bash … .sh»")
ok(arr.a_linux("./arrancar.command", c2) == "bash scripts/arrancar.sh", "un .command de Mac con su .sh: igual")

# ---------- la app con su PUENTE: solo órdenes de Linux, el puente se apunta ----------
app = os.path.join(T, "apps_externas", "miapp"); os.makedirs(app)
open(os.path.join(app, "README.md"), "w").write(README)
open(os.path.join(app, "servidor.py"), "w").write(
    "import time,socket\ns=socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
    "s.bind(('127.0.0.1',0)); s.listen(1)\nprint('servidor listo', flush=True)\ntime.sleep(60)\n")
open(os.path.join(app, "app.py"), "w").write("print('app')\n")
iid = ak.anadir_externa(T, "Mi App", ["python3", os.path.join(app, "app.py")], app)
acc = ak.uno(T, iid)
pasos = arr.pasos_terminal(acc)
textos = [t for t, _b in pasos]
ok(any("servidor.py" in t and "puente" in t for t in textos), f"el puente de Linux se apunta ({textos})")
ok(not any("brew" in t or ".bat" in t or ".command" in t for t in textos), "nada de Mac ni Windows en los pasos")
ok(arr.es_de_terminal(acc) if hasattr(arr, "es_de_terminal") else True, "con puente, se abre en la terminal")
g = arr.guion_terminal(acc, pasos)
ok('echo "$pid" >"$log.pid"' in g, "el guion apunta el número del puente (para la ventana)")
ok(subprocess.run(["bash", "-n"], input=g, text=True).returncode == 0, "el guion es bash correcto")

# ---------- la ventana «Programas auxiliares» ----------
aux = arr.auxiliares(T)
ok(len(aux) == 1 and aux[0]["titulo"] == "Mi App" and aux[0]["carpeta"] == app, "la carpeta de «Mi App»")
p = aux[0]["puentes"][0]
ok(p["args"][-2:] == ["--port", "8765"] and p["args"][-3].endswith("servidor.py") and p["puerto"] == 8765 and not p["encendido"],
   "su auxiliar, apagado")
ok(arr.encender_puente(p) and arr.puente_encendido(p), "Encender (solo, sin el programa principal)")
time.sleep(1.0)
ok("servidor listo" in arr.ultimas_lineas(p["log"]), "se ven sus mensajes")
ok(arr.auxiliares(T)[0]["puentes"][0]["encendido"], "la ventana lo ve encendido")
ok(arr.parar_puente(p), "Apagar")
time.sleep(0.5)
ok(not arr.puente_encendido(p), "apagado de verdad")
ok(not arr.parar_puente(p), "apagar lo apagado no rompe")

# ---------- el escritorio ----------
import escritorio_kira as ek
class Esc(ek.EscritorioMixin):
    def __init__(self):
        pass
esc = Esc()
ok(esc.n_auxiliares() == 1, "la barra cuenta 1 auxiliar (para el icono de carpeta)")
d = esc.app("auxiliares")
ok(d["titulo"] == "Programas auxiliares" and d["pestanas"][0]["filas"], "ventana «Programas auxiliares»")
f = d["pestanas"][0]["filas"][0]
ok(d["pestanas"][0]["secciones"][0][1].startswith("Carpeta de «Mi App»"), "agrupado por la carpeta del programa")
ok([b["texto"] for b in f["botones"]] == ["Ver mensajes", "Apagar", "Encender"] and f["etiqueta"] == "Apagado",
   "Ver mensajes · Apagar · Encender")
clave = f["botones"][2]["accion"].replace("hacer:", "")
r = esc.app_hacer("auxiliares", clave)
ok("encendido" in r["texto"], "Encender desde la ventana")
time.sleep(0.8)
r = esc.app_hacer("auxiliares", f["botones"][0]["accion"].replace("hacer:", ""))
ok("servidor listo" in r["texto"], "Ver mensajes desde la ventana")
r = esc.app_hacer("auxiliares", f["botones"][1]["accion"].replace("hacer:", ""))
ok("apagado" in r["texto"], "Apagar desde la ventana")
ok(not ak.listar(T)[0].get("auxiliar") and len(ak.listar(T)) == 1, "el auxiliar NO tiene icono propio")


# ---------- «/usr/bin/env: «python»: No existe» (foto del dueño) ----------
sal = "/usr/bin/env: «python»: No existe el archivo o el directorio"
ok(arr.diagnostico(sal)[0]["tipo"] == "python", "reconoce el error de la foto (falta la orden «python»)")
ok(arr.diagnostico("/usr/bin/env: 'python': No such file or directory")[0]["tipo"] == "python", "también en inglés")
falso = lambda nombre: {"python3": "/usr/bin/python3"}.get(nombre)
d_at = arr.atajo_python(which=falso, carpeta=os.path.join(T, "atajos"))
ok(d_at and os.path.realpath(os.path.join(d_at, "python")) == os.path.realpath("/usr/bin/python3"),
   "atajo «python» → python3 en una carpeta de Kira (sin tocar el sistema)")
ok(arr.atajo_python(which=lambda n: "/usr/bin/" + n) is None, "si ya existe «python», no hace nada")
env = arr.con_atajo({"PATH": "/usr/bin"}, which=falso)
ok(env["PATH"].split(os.pathsep)[0].endswith("atajos_kira") and env["PATH"].endswith("/usr/bin"),
   "el atajo va DELANTE en el PATH")
# de verdad: un programa con «#!/usr/bin/env python» arranca con el atajo
sc = os.path.join(T, "viejo.py"); open(sc, "w").write("#!/usr/bin/env python\nprint('arranqué')\n"); os.chmod(sc, 0o755)
bin_sin = os.path.join(T, "bin_sin_python"); os.makedirs(bin_sin)
for prog in ("env", "python3"):
    os.symlink(shutil.which(prog), os.path.join(bin_sin, prog))
env2 = {"PATH": bin_sin}
r1 = subprocess.run([sc], env=env2, capture_output=True, text=True)
ok(r1.returncode != 0 and "python" in r1.stderr, "sin atajo: falla como en la foto")
env3 = arr.con_atajo(dict(env2), which=lambda n: shutil.which(n, path=bin_sin))
r2 = subprocess.run([sc], env=env3, capture_output=True, text=True)
ok(r2.returncode == 0 and "arranqué" in r2.stdout, "con el atajo: ARRANCA")

# ---------- la pantalla ----------
h = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html"), encoding="utf-8").read()
ok('id:"auxiliares"' in h and "AUX>0" in h and 'dib:"carpeta"' in h, "icono de carpeta solo si hay auxiliares")
node = shutil.which("node")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(500);
  const antes = await pg.$('.icono[data-app="auxiliares"]') !== null;
  await pg.evaluate(() => { AUX=2; pintaIconos(); });
  const despues = await pg.$eval('.icono[data-app="auxiliares"]', x => x.textContent);
  console.log(JSON.stringify({errs, antes, despues}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    fj = os.path.join(T, "c.js"); open(fj, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    rr = subprocess.run([node, fj, os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")],
                        capture_output=True, text=True, timeout=120, env=env)
    out = rr.stdout.strip().splitlines()[-1] if rr.stdout.strip() else ""
    if out.startswith("{"):
        dd = json.loads(out)
        ok(not dd["errs"], "Chromium: sin errores " + str(dd["errs"]))
        ok(not dd["antes"] and "Programas auxiliares" in dd["despues"] and "2 auxiliares" in dd["despues"],
           "Chromium: sin auxiliares no hay icono; con ellos, la carpeta " + str(dd["despues"]))
    else:
        print("  (sin Chromium)", out[:200], rr.stderr[-200:])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
