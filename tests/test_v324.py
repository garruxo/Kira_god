# -*- coding: utf-8 -*-
"""v3.24:
- Parte A: la TERMINAL de KiraOS abre la terminal DE VERDAD de Xubuntu (xfce4-terminal) y se pueden abrir varias;
  si no hay ninguna instalada, cae a la terminal dentro de Kira.
- Parte B: con el cerebro pequeño el código salía casi siempre IGUAL. Dos causas arregladas:
    1) `contexto_para` metía el código completo de una receta aunque se pareciera POCO → el 2B lo copiaba. Ahora,
       en local, el código completo solo si el parecido es FUERTE (2+ palabras); si es flojo, va solo la IDEA.
    2) las penalizaciones por repetir (frequency/presence) castigaban lo normal del código. Al programar se quitan
       y se sube un pelín la temperatura (muestreo más variado).
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ====================== Parte A: la terminal de Xubuntu ======================
import escritorio_kira as ek


class Pantalla(ek.EscritorioMixin):
    pass


ok(ek.TERMINALES[0] == "xfce4-terminal", "la primera terminal que prueba es la de Xubuntu (xfce4-terminal)")

p = Pantalla()
# no hay ninguna terminal instalada
_which = shutil.which
shutil.which = lambda prog: None
try:
    r = p.terminal_externa()
finally:
    shutil.which = _which
ok(not r["ok"] and "ninguna" in r["motivo"], "si no hay terminal instalada, lo dice (y la pantalla cae a la de dentro)")

# hay xfce4-terminal: la abre en una ventana aparte
abiertas = []
_popen = ek.subprocess.Popen
ek.subprocess.Popen = lambda args, **kw: abiertas.append((args, kw)) or object()
shutil.which = lambda prog: "/usr/bin/" + prog if prog == "xfce4-terminal" else None
try:
    r1 = p.terminal_externa()
    r2 = p.terminal_externa()        # se puede abrir OTRA
finally:
    ek.subprocess.Popen = _popen
    shutil.which = _which
ok(r1["ok"] and r1["cual"] == "xfce4-terminal", "abre la terminal de Xubuntu")
ok(len(abiertas) == 2, "se pueden abrir varias (llamarla otra vez abre otra)")
ok(abiertas[0][1].get("start_new_session") is True and abiertas[0][1].get("env", {}).get("DISPLAY"),
   "la lanza aparte (start_new_session) y con DISPLAY puesto")

# la HTML tiene la terminal integrada de reserva, el terminal_externa en FAKE y el cableado
html = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html"), encoding="utf-8").read()
ok("function pintaTerminalIntegrada(" in html and "terminal_externa" in html, "la HTML tiene la de dentro de reserva y llama a terminal_externa")
ok("terminal_externa:function" in html, "el FAKE de pruebas tiene terminal_externa")


# ====================== Parte B.1: no copiar la receta si se parece poco ======================
import saber_mejoras_kira as sm

sm.mejor_propia = lambda *a, **k: None          # sin mejoras propias aprobadas que estorben la prueba
sm.RECETAS = [{"id": "zorro_juego", "titulo": "Juego del zorro", "temas": "zorro bosque juego",
               "idea": "un zorro que corre", "codigo": "def f():\n    return 1", "complejidad": "O(1)"}]

# parecido GENÉRICO (solo coincide «juego», que no dice de qué va): en el móvil, SOLO la idea; el PC sí el código
gen_local = sm.contexto_para("hazme un juego", local=True)
gen_pc = sm.contexto_para("hazme un juego", local=False)
ok("```python" not in gen_local and "un zorro que corre" in gen_local,
   "parecido solo genérico («juego») + cerebro pequeño: solo la IDEA (no copia) → programas variados")
ok("```python" in gen_pc, "el cerebro grande (PC) sí recibe el código aunque el parecido sea genérico")

# parecido ESPECÍFICO (coincide «zorro», que sí dice de qué va): el móvil también recibe el código, para adaptarlo
esp_local = sm.contexto_para("un juego de un zorro", local=True)
ok("```python" in esp_local, "parecido específico («zorro»): el móvil sí recibe el código para adaptarlo")


# ====================== Parte B.2: muestreo más suave al programar ======================
import cerebro_ia_kira as ci


class Resp:
    def __init__(self, cuerpo):
        self._c = cuerpo
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def read(self, n=0):
        return self._c


cuerpos = {}


def abrir_falso(req, timeout=0):
    cuerpos["ultimo"] = json.loads(req.data.decode("utf-8"))
    return Resp(b'{"choices":[{"message":{"content":"ok"}}]}')


cer = ci.Cerebro(T, abrir=abrir_falso)
cer.url = "http://127.0.0.1:8081"
cer.casa_disponible = lambda *a, **k: False       # que no se vaya al portátil: probamos el muestreo del móvil

cer._chat_local([{"role": "user", "content": "hola"}], 200, 60, None, None, codigo=False)
charla = dict(cuerpos["ultimo"])
cer._chat_local([{"role": "user", "content": "programa"}], 200, 60, None, None, codigo=True)
prog = dict(cuerpos["ultimo"])

ok(charla.get("frequency_penalty") == 0.4 and charla.get("presence_penalty") == 0.2,
   "al charlar/resumir se quedan las penalizaciones por repetir (como antes)")
ok("frequency_penalty" not in prog and "presence_penalty" not in prog,
   "al PROGRAMAR se quitan las penalizaciones (castigaban lo normal del código)")
ok(prog.get("temperature") == 0.78 and prog.get("top_p") == 0.95 and prog.get("repeat_penalty") == 1.08,
   "al programar: más temperatura y menos penalización por repetir (código más variado y completo)")

# el cerebro de casa (portátil) también afina al programar
import casa_kira as ck
ck.pc.leer_config = lambda: {"portatil_url": "http://127.0.0.1:8770", "token": "t"}
casa = ck.Casa(abrir=abrir_falso)
casa.chat("sys", [{"role": "user", "content": "programa"}], codigo=True)
cprog = dict(cuerpos["ultimo"])
ok(cprog.get("temperature") == 0.78 and cprog.get("top_p") == 0.95, "el cerebro grande de casa también afina al programar")

# ====================== Parte A en la pantalla de verdad (Chromium) ======================
node = shutil.which("node")
html_ruta = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(300);
  // 1) hay terminal de Xubuntu: sale el panel con los dos botones
  await pg.evaluate(() => { FAKE._termext={ok:true,cual:"xfce4-terminal"}; abrir("terminal"); });
  await pg.waitForTimeout(400);
  const txt1 = await pg.textContent('#vcuerpo');
  const bots = await pg.$$eval('#vcuerpo button', l => l.map(x => x.textContent));
  // «Terminal dentro de Kira» → la terminal integrada (campo de órdenes)
  await pg.evaluate(() => { [].slice.call(document.querySelectorAll('#vcuerpo button'))
    .filter(b => /dentro de Kira/.test(b.textContent))[0].click(); });
  await pg.waitForTimeout(400);
  const dentro = await pg.$('#termIn') ? true : false;
  // 2) no hay ninguna terminal: cae directo a la integrada
  await pg.evaluate(() => { FAKE._termext={ok:false,motivo:"nada"}; abrir("terminal"); });
  await pg.waitForTimeout(400);
  const cae = await pg.$('#termIn') ? true : false;
  console.log(JSON.stringify({errs, txt1, bots, dentro, cae}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    fjs = os.path.join(T, "t.js")
    open(fjs, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, fjs, html_ruta], capture_output=True, text=True, timeout=180, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok("terminal de Xubuntu" in d["txt1"], "Chromium: al abrir la terminal, el panel dice que abrió la de Xubuntu")
        ok(any("Abrir otra" in x for x in d["bots"]) and any("dentro de Kira" in x for x in d["bots"]),
           "Chromium: botones «Abrir otra terminal» y «Terminal dentro de Kira»")
        ok(d["dentro"], "Chromium: «Terminal dentro de Kira» abre la terminal integrada")
        ok(d["cae"], "Chromium: si no hay terminal de Xubuntu, cae directo a la integrada")
    else:
        print("  (sin Chromium)", r.stdout[-500:], r.stderr[-300:])

# ====================== que el cableado del flag llega desde generar_programa / generar_mejora ======================
src = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
ok(src.count("codigo=True") >= 2, "generar_programa y generar_mejora piden muestreo de código (codigo=True)")
ok("def _llamar_api(self, clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None, codigo=False)" in src,
   "_llamar_api acepta el flag y lo pasa al cerebro")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
