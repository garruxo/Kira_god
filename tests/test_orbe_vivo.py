# -*- coding: utf-8 -*-
"""v3.14: pulsar el ORBE lleva a lo que Kira está haciendo; «Programando» enseña EN VIVO el código que escribe su
núcleo; la ventana de la Máquina enseña en vivo lo que hace dentro (comandos, lo que sale, páginas visitadas); y las
claves («config github: ghp_…») nunca se enseñan en la barra, el cuaderno ni el móvil."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
os.environ["KIRA_DATOS_NUCLEO"] = T
os.environ["KIRA_MAQUINA"] = os.path.join(T, "maquina")
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import escritorio_kira as ek
import nucleo_portatil as npk
import maquina_kira as mq
import ordenes_kira as ok_

fallos = 0
n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ---------- claves que nunca se enseñan ----------
oc = ok_.ocultar_claves
ok("ghp_" not in oc("config github: ghp_AAAAbbbbCCCCdddd1234") and "config github" in oc("config github: ghp_x1234567890"),
   "«config github: …» sin la clave")
ok(oc("toma github_pat_11ABCDEFG_zzzzzzzz y ya") == "toma •••• y ya", "una clave de GitHub suelta, tapada")
ok("sk-ant" not in oc("config clave: sk-ant-api03-abcdefghijk"), "la clave de Claude, tapada")
ok(oc("estudia python a fondo") == "estudia python a fondo", "lo normal, intacto")

# ---------- de lo que va escribiendo el cerebro, el CÓDIGO ----------
P = ek.codigo_de_pizarra
ok(P("Claro, aquí va:\n```python\ndef hola():\n    return 1\n```\nY ya.") == "def hola():\n    return 1",
   "un bloque cerrado")
ok(P("Te lo escribo:\n```python\nimport os\ndef a(") == "import os\ndef a(", "un bloque a medio escribir (en vivo)")
ok(P("```python\nx = 1\n```\notro:\n```py\ny = 2\n") == "y = 2", "varios bloques: el último")
ok(P("def f(x):\n    return x") == "def f(x):\n    return x", "sin bloque pero ya es código")
ok(P("Hola, ¿qué tal?") == "" and P("") == "", "charla normal: nada")

# ---------- el núcleo apunta lo que escribe (pizarra) ----------
import kira_god
core = kira_god.KiraGodCore.__new__(kira_god.KiraGodCore)
vistos = []
f = core._con_pizarra(lambda t: vistos.append(t))
f("```python\ndef a")
ok(core.pizarra["texto"] == "```python\ndef a" and vistos == ["```python\ndef a"], "cada trozo queda en la pizarra y sigue su camino")
ok(core._con_pizarra(None) is None, "si nadie lee a trozos, no cambia nada (no fuerza el stream)")
g = core._con_pizarra(None, True)
g("abc")
ok(core.pizarra["texto"] == "abc", "con el cerebro propio, siempre a la pizarra")

ev = threading.Event()


def hacer(o, paso):
    if o == "config github: ghp_AAAAAAAAAAAAAAAAAAAA":
        return {"texto": "Clave guardada."}
    paso(0.3, "escribo el código")
    ev.wait(6)
    return {"texto": "Hecho", "codigo": "def final():\n    return 2\n", "nombre": "final"}


tb = npk.Trabajos(hacer)
nuc = npk.Nucleo.__new__(npk.Nucleo)
nuc.trabajos = tb
nuc.core = type("C", (), {"dir": T})()
tb.empezar("config github: ghp_AAAAAAAAAAAAAAAAAAAA")
lim = time.time() + 5
while time.time() < lim and tb.ocupado() or (time.time() < lim and not tb.hechas()):
    time.sleep(0.02)
ok(all("ghp_" not in x["orden"] for x in tb.hechas()), "en Terminadas, la orden con la clave sale tapada")
tb.empezar("escríbeme un programa que salude")
lim = time.time() + 5
while time.time() < lim and not tb.ocupado():
    time.sleep(0.02)
nuc.core.pizarra = {"texto": "Aquí va:\n```python\ndef saluda():\n    print('ho", "inicio": time.time(), "cuando": time.time()}
e = nuc.estado()
ok(e["pizarra"] and "def saluda" in e["pizarra"]["texto"], "el estado del núcleo da lo que escribe AHORA")
ok(e["ultimo_codigo"] is None, "aún no hay código terminado")

# ---------- «Programando» en vivo ----------
class CliN:
    def __init__(self, nuc):
        self.nuc = nuc

    def estado(self):
        return json.loads(json.dumps(self.nuc.estado()))


esc = ek.EscritorioMixin()
esc.cli = None
esc.nucleo_cli = CliN(nuc)
v = esc.programando_vivo()
ok(v.get("estado") == "en_vivo" and v["codigo"].startswith("def saluda") and v["lineas"], "Programando: en vivo, con su explicación")
ok(v["pedido"] == "escríbeme un programa que salude", "…y lo que le pediste")
ok(esc.hay_programa(), "con código en vivo, la ventana se abre (no «aún no he escrito código»)")
nuc.core.pizarra = {"texto": "Déjame pensarlo…", "inicio": time.time(), "cuando": time.time()}
v = esc.programando_vivo()
ok(v.get("estado") == "esperando" and esc.hay_programa(), "programando pero aún sin código: «pensando el código»")
ev.set()
lim = time.time() + 5
while time.time() < lim and tb.ocupado():
    time.sleep(0.02)
time.sleep(0.1)
v = esc.programando_vivo()
ok(v.get("estado") == "listo" and "def final" in v["codigo"] and v["archivo"] == "final.py", "al acabar: el código terminado")
ok(nuc.estado()["pizarra"] is None, "sin tarea en curso no hay pizarra")

# ---------- pulsar el orbe ----------
D = ek.destino_orbe
ok(D({"modo": "Programando"}) == {"app": "programando"}, "programando → Programando")
ok(D({"modo": "Estudiando", "actividad": {"maquina": True}}) == {"app": "maquina"}, "estudiando con la máquina → Máquina")
ok(D({"modo": "Trabajando", "haciendo": "ejecuta ls en tu máquina", "actividad": {"maquina": True}}) == {"app": "maquina"},
   "trabajando en su máquina → Máquina")
ok(D({"modo": "Estudiando", "actividad": {}}) == {"app": "cuaderno", "pestana": "tareas"}, "estudiando sin máquina → Tareas")
ok(D({"modo": "Pensando"}) == {"app": "cuaderno", "pestana": "pensamiento"}, "pensando → Pensamiento")
ok(D({"modo": "Sin tareas"}) == {"app": "cuaderno", "pestana": "tareas"} and D(None)["app"] == "cuaderno", "sin tareas → Tareas")
esc._trab_cache = None
nuc.core.pizarra = None
tb.empezar("hazme un programa que cuente")
ev.clear()
lim = time.time() + 5
while time.time() < lim and not tb.ocupado():
    time.sleep(0.02)
ok(esc.trabajo()["ir"] == {"app": "programando"}, "el puente dice a dónde lleva el orbe")
ev.set()

# ---------- la máquina, en vivo ----------
os.makedirs(mq.BASE, exist_ok=True)
with open(os.path.join(mq.BASE, "maquina.log"), "w", encoding="utf-8") as fh:
    fh.write("=== máquina encendida ===\n" + "".join(f"kira@maquina$ echo {i}\n{i}\n" for i in range(60)) +
             "kira visita https://docs.python.org/3/\n  ← 200 · 34 KB · «Python docs»\n" + "x" * 400 + "\n")
with open(os.path.join(mq.BASE, "puerta.log"), "w", encoding="utf-8") as fh:
    fh.write("12:00 OK docs.python.org:443\n")
r = ek.registro_maquina(mq.BASE, n=10)
ok(len(r) == 10 and "Python docs" in r[-2] and r[-1].endswith("…") and len(r[-1]) < 230, "las últimas líneas, sin líneas larguísimas")
ok(ek.registro_maquina(os.path.join(T, "no_existe")) == [], "sin registro: nada")
a = esc._app_maquina()
ok(a.get("refrescar_cada") == 3 and "LO QUE HAGO DENTRO" in a["texto"] and "kira@maquina$ echo 59" in a["texto"],
   "la ventana de la máquina enseña lo que hace dentro y se refresca sola")
ok("PÁGINAS QUE HE VISITADO" in a["texto"] and "docs.python.org" in a["texto"], "…y las páginas visitadas")
ok("Enséñamela" in [b["texto"] for b in a["botones"]], "sigue el botón de ver su pantalla")
ok(mq.nota_visita({"status": 200, "cuerpo": b"<html><title>Hola &amp; adi\xc3\xb3s</title>" + b"x" * 3000}) ==
   "  ← 200 · 2 KB · «Hola & adiós»", "lo que trajo una visita: estado, tamaño y título")
ok(mq.nota_visita({"error": "403 no deja ir a tu casa"}).startswith("  ← no pude"), "una visita que no salió")

# ---------- en la pantalla de verdad (Chromium) ----------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
prog = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "programando.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(700);
  await pg.evaluate(() => { FAKE._trab = {nucleo:true, ocupada:true, haciendo:"hazme un programa", modo:"Programando",
                                           eta:"", en_cola:0, ir:{app:"programando"}}; });
  const encima = await pg.evaluate(() => { const r=document.getElementById('orbe').getBoundingClientRect();
      const el=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); return !!el.closest('#orbe'); });
  await pg.click('#orbe', {force:true}); await pg.waitForTimeout(500);
  const t1 = await pg.textContent('#vtitulo');
  const marco = await pg.$$eval('#vcuerpo iframe', l => l.length);
  await pg.click('#volver'); await pg.waitForTimeout(200);
  await pg.evaluate(() => { FAKE._trab = {nucleo:true, ocupada:false, modo:"Pensando", ir:{app:"cuaderno", pestana:"pensamiento"}}; });
  await pg.click('#orbe', {force:true}); await pg.waitForTimeout(500);
  const t2 = await pg.textContent('#vtitulo');
  const pest = await pg.$$eval('.pestapp .pest.on', l => l.map(x => x.dataset.pest));
  // una ventana EN VIVO se vuelve a pedir sola
  let pedidas = 0;
  await pg.evaluate(() => { window._n=0; var vieja=FAKE.app; FAKE.app=function(id){ if(id==="maquina"){ window._n++;
      return Promise.resolve({titulo:"Máquina", texto:"vuelta "+window._n, refrescar_cada:1, botones:[]}); } return vieja(id); }; });
  await pg.click('#volver'); await pg.waitForTimeout(100);
  await pg.evaluate(() => abrir("maquina")); await pg.waitForTimeout(2600);
  pedidas = await pg.evaluate(() => window._n);
  const txt = await pg.textContent('#vcuerpo .texto');
  await pg.click('#volver'); await pg.waitForTimeout(1500);
  const trasCerrar = await pg.evaluate(() => window._n);
  // programando.html en vivo: el código va creciendo
  const p2 = await b.newPage({viewport:{width:1200,height:700}}); p2.on('pageerror', e => errs.push(String(e)));
  await p2.addInitScript(() => { window._k=0; const trozos=["def suma(a, b):", "def suma(a, b):\n    return a + b", "def suma(a, b):\n    return a + b\n\nprint(suma(2, 3))"];
    window.pywebview = {api:{programando_datos:function(){ var i=Math.min(window._k++, 3);
      if(i<3) return Promise.resolve({estado:"en_vivo", pedido:"una suma", archivo:"programa.py", codigo:trozos[i], lineas:[{n:1,codigo:"def suma(a, b):",nota:"def: define <b>"}]});
      return Promise.resolve({estado:"listo", pedido:"una suma", archivo:"suma.py", codigo:trozos[2], resumen:"Una función.", lineas:[{n:1,codigo:"def suma(a, b):",nota:"def: define <b>"}]}); }}}; });
  await p2.goto('file://' + process.argv[3]); await p2.waitForTimeout(900);
  const vivo1 = await p2.evaluate(() => window.KIRA_PROG);
  const est1 = await p2.textContent('#estado');
  await p2.waitForTimeout(8600);
  const vivo2 = await p2.evaluate(() => window.KIRA_PROG);
  const est2 = await p2.textContent('#estado');
  const notas = await p2.$$eval('.nota', l => l.length);
  const html = await p2.$eval('.nota .t', x => x.innerHTML);
  await p2.screenshot({path: process.argv[4]});
  console.log(JSON.stringify({errs, encima, t1, marco, t2, pest, pedidas, txt, trasCerrar, vivo1, est1, vivo2, est2, notas, html}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    fjs = os.path.join(T, "o.js")
    open(fjs, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, fjs, html, prog, os.path.join(T, "prog.png")], capture_output=True, text=True,
                       timeout=180, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(d["encima"], "Chromium: nada tapa el orbe (se puede pulsar de verdad)")
        ok(d["t1"] == "Programando" and d["marco"] == 1, "Chromium: el orbe programando abre «Programando»")
        ok(d["t2"] == "Cuaderno" and d["pest"] == ["pensamiento"], "Chromium: el orbe pensando abre Cuaderno ▸ Pensamiento")
        ok(d["pedidas"] >= 2 and d["txt"].startswith("vuelta"), "Chromium: la ventana de la máquina se refresca sola")
        ok(d["trasCerrar"] <= d["pedidas"] + 1, "Chromium: al cerrarla deja de pedir")
        ok(d["vivo1"] and d["vivo1"]["estado"] == "en_vivo" and "Escribiendo en vivo" in d["est1"],
           "Chromium: «Programando» dice que escribe en vivo")
        ok(d["vivo2"]["estado"] == "listo" and "print(suma(2, 3))" in d["vivo2"]["escrito"] and "Listo" in d["est2"],
           "Chromium: el código fue creciendo y al final «Listo» " + str(d["vivo2"]))
        ok(d["notas"] == 1, "Chromium: la explicación sin repetirse")
        ok("&lt;b&gt;" in d["html"], "Chromium: la explicación en vivo se enseña como texto (sin HTML)")
        print("  captura:", os.path.join(T, "prog.png"))
    else:
        print("  (sin Chromium)", r.stdout[-1500:], r.stderr[-600:])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
