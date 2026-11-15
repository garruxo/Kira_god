# -*- coding: utf-8 -*-
"""v3.85: los programas DE TERMINAL se abren en la TERMINAL DE DENTRO DE KIRA (delante, en su pantalla): la de
Xubuntu se quedaba detrás de la pantalla completa y el dueño no la veía. Kira escribe ahí los pasos y lo arranca."""
import json, os, shutil, subprocess, sys, tempfile, time

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATOS_NUCLEO"] = T
sys.path[:0] = [R, os.path.join(R, "kira_portatil")]
import arreglar_app_kira as arr
import accesos_kira as ak
arr.REGISTROS = os.path.join(T, "reg")

fallos = n = 0
def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1

def escribe(c, nombre, texto):
    p = os.path.join(c, nombre); open(p, "w").write(texto); return p

c = tempfile.mkdtemp(dir=T)
escribe(c, "main.py", "print(open('modelo.bin').read())\nx = input('¿Cómo te llamas? ')\nprint('hola', x)\n")
escribe(c, "descargar.py", "open('modelo.bin','w').write('MODELO-OK')\n")
escribe(c, "README.md", "```\npython3 descargar.py\npython3 main.py\n```\n")
iid = ak.anadir_externa(T, "Preguntón", ["python3", os.path.join(c, "main.py")], c)
a = ak.uno(T, iid)

# ---------- sin la pantalla de KiraOS: la terminal de Xubuntu (como antes) ----------
llam = []
class P:
    pid = 99
    def __init__(self, args, **kw): llam.append(args)
w = lambda p: "/usr/bin/" + p if p == "xfce4-terminal" else None
ok(not arr.pantalla_viva(), "sin pantalla abierta")
r = arr.abrir_vigilando(a, T, popen=P, which=w, admin=False, en_hilo=False)
ok(r.get("terminal") is True and llam and llam[-1][0].endswith("xfce4-terminal"), "sin pantalla: terminal de Xubuntu")

# ---------- con la pantalla abierta: en la terminal de Kira ----------
arr.marcar_pantalla_viva()
ok(arr.pantalla_viva(), "la pantalla avisa de que está abierta")
llam.clear()
r = arr.abrir_vigilando(a, T, popen=P, which=w, admin=False, en_hilo=False)
ok(r.get("terminal") == "kira" and not llam, "con pantalla: NO abre otra ventana, va a la terminal de Kira")
ok("mi Terminal" in r["texto"] and "el paso de su README" in r["texto"], "lo dice: " + r["texto"][:70])
t = arr.tomar_pendiente()
ok(t and t["orden"].startswith("bash ") and t["guion"].endswith("_terminal.sh") and t["titulo"] == "Preguntón",
   "la pantalla recoge qué abrir")
ok(arr.tomar_pendiente() is None, "solo una vez")
ok(not arr.guion_valido("/etc/passwd") and not arr.guion_valido(os.path.join(T, "x_terminal.sh")),
   "solo guiones de Kira (nada de fuera)")
# uno viejo no vale
arr.pedir_terminal_kira(a, admin=False)
d = json.load(open(arr._ruta_pendiente())); d["cuando"] -= 600
json.dump(d, open(arr._ruta_pendiente(), "w"))
ok(arr.tomar_pendiente() is None, "un aviso viejo (10 min) no se abre")

# ---------- la pantalla: abrir_acceso lo trae y la terminal de dentro lo ejecuta DE VERDAD ----------
import escritorio_kira as ek
esc = ek.EscritorioMixin(); esc.cli = None; esc.nucleo_cli = None
import manejo_apps_kira as ma
viejo = ma.lista_ordenes
ma.lista_ordenes = lambda *a_, **k_: []
d = esc.abrir_acceso(iid)
ma.lista_ordenes = viejo
tk = d.get("terminal_kira") or {}
ok(d.get("externa") and tk.get("orden", "").startswith("bash "), "clic en el icono: viene para la terminal de Kira")
ok(esc.terminal_pendiente() is None, "ya consumido (no se abre dos veces)")
esc.terminal_nueva()
esc.terminal_escribir(tk["orden"])
txt, pos = "", 0
fin = time.time() + 15
while time.time() < fin and "¿Cómo te llamas?" not in txt:
    time.sleep(0.3); r_ = esc.terminal_leer(pos); txt += r_.get("texto", ""); pos = r_.get("pos", pos)
ok("$ python3" in txt and "descargar.py" in txt, "se ve la orden que escribe Kira (el paso del README)")
ok("MODELO-OK" in txt and "¿Cómo te llamas?" in txt, "el programa arranca DESPUÉS y te pregunta")
esc.terminal_escribir("Papi")
fin = time.time() + 8
while time.time() < fin and "hola Papi" not in txt:
    time.sleep(0.3); r_ = esc.terminal_leer(pos); txt += r_.get("texto", ""); pos = r_.get("pos", pos)
ok("hola Papi" in txt, "le contestas en la terminal de Kira y sigue")
ok(not esc.abrir_guion_xubuntu("/etc/passwd")["ok"], "el botón de Xubuntu solo abre guiones de Kira")
try:
    esc._terminal.cerrar()
except Exception:
    pass

# ---------- Chromium ----------
node = shutil.which("node")
html = os.path.join(R, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(500);
  await pg.evaluate(() => { window.ESCRITO=[]; var e0=FAKE.terminal_escribir;
    FAKE.terminal_escribir=function(l,c){ window.ESCRITO.push(l); return e0(l,c); };
    FAKE._pend={orden:"bash '/x/reg/p_terminal.sh'", titulo:"Preguntón", guion:"/x/reg/p_terminal.sh"};
    FAKE.terminal_pendiente=function(){ var p=FAKE._pend; FAKE._pend=null; return Promise.resolve(p); };
    FAKE.abrir_guion_xubuntu=function(g){ window.XU=g; return Promise.resolve({ok:true,texto:"Abierta en Xubuntu"}); }; });
  await pg.evaluate(() => refrescaTrabajo()); await pg.waitForTimeout(800);
  const tit = await pg.$eval('#vtitulo', x => x.textContent);
  const aviso = await pg.$eval('.termprog span', x => x.textContent);
  const escrito = await pg.evaluate(() => window.ESCRITO);
  const sal = await pg.$eval('#termSal', x => x.textContent);
  await pg.click('[data-x="xubuntu"]'); await pg.waitForTimeout(150);
  const xu = await pg.evaluate(() => window.XU);
  await pg.screenshot({path: process.argv[3]});
  console.log(JSON.stringify({errs, tit, aviso, escrito, sal, xu}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    f = os.path.join(T, "c.js"); open(f, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, f, html, os.path.join(T, "term.png")], capture_output=True, text=True, timeout=120, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(d["tit"] == "Terminal · Preguntón", "Chromium: se abre SOLA la terminal de Kira con el programa")
        ok(d["escrito"] == ["bash '/x/reg/p_terminal.sh'"] and "bash '/x/reg/p_terminal.sh'" in d["sal"],
           "Chromium: Kira escribe la orden en la terminal")
        ok("Preguntón" in d["aviso"] and d["xu"] == "/x/reg/p_terminal.sh", "Chromium: aviso y botón «terminal de Xubuntu»")
        print("  captura:", os.path.join(T, "term.png"))
    else:
        print("  (sin Chromium)", out[:300], r.stderr[-300:])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
