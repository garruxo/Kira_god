# -*- coding: utf-8 -*-
"""v3.08: el CUADERNO de KiraOS en pestañas: Pensamiento, Conocimiento, Mejoras (portátil / móvil; se puede o se
debe) y Tareas (activas, en espera, terminadas). Lógica pura + la ventana (puente y Chromium)."""
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
import cuaderno_clases_kira as cc

fallos = 0
n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


DUDA = {"pregunta": "¿por qué la memoria caché funciona así por dentro?", "respuesta": "No lo tengo claro…",
        "seguridad": "media", "duda": True, "fuente": "lo que sé", "tipo": "idea"}
SABE = {"pregunta": "¿por qué el cifrado funciona así por dentro?", "respuesta": "Matemáticas y claves.",
        "seguridad": "alta", "duda": False, "fuente": "estudiado", "tipo": "experimento",
        "experimento": {"ok": True, "resultado": "Cifrado (MD5)…"}}
EXP_MAL = dict(SABE, pregunta="¿cómo se construye un árbol?", experimento={"ok": False, "resultado": "error"})
MEJ_PORT = {"pregunta": "¿hay algo de la caché que pueda MEJORAR en mi propio código?",
            "respuesta": "En KiraOS el buscador va lento: debería guardar las páginas leídas.", "seguridad": "media"}
MEJ_MOV = {"pregunta": "¿se podría INCORPORAR la caché a mi propio sistema (Kira) como una función nueva, y cómo?",
           "respuesta": "En el móvil podría guardar respuestas para gastar menos batería.", "seguridad": "media"}
SIN = {"pregunta": "¿qué pasaría si un proceso fallara?", "respuesta": "(no pude pensar ahora: 401)",
       "seguridad": "alta", "duda": False, "fuente": "sin cerebro"}

ok(cc.clase(DUDA) == "pensamiento" and cc.clase(SABE) == "conocimiento", "duda = pensamiento; comprobado = conocimiento")
ok(cc.clase(EXP_MAL) == "pensamiento", "un experimento que falló aún es pensamiento")
ok(cc.clase(SIN) == "pensamiento", "lo que no pudo pensar (sin cerebro) no cuenta como conocimiento")
ok(cc.clase(MEJ_PORT) == "mejora" and cc.clase(MEJ_MOV) == "mejora", "las preguntas sobre SU sistema son mejoras")
ok(cc.donde(MEJ_PORT) == "portatil" and cc.donde(MEJ_MOV) == "movil", "separa portátil y móvil")
ok(cc.donde({"pregunta": "mejorar en mi propio código", "respuesta": "ordenar mejor"}) == "los dos", "si no dice: los dos")
ok(cc.urgencia(MEJ_PORT) == "debe" and cc.urgencia(MEJ_MOV) == "puede", "«va lento / debería» = SE DEBE; idea = SE PUEDE")
ok(cc.urgencia(dict(MEJ_MOV, experimento={"ok": False})) == "debe", "si su prueba falló: se debe")

est = {"notas": [DUDA, SABE, EXP_MAL, MEJ_PORT, MEJ_MOV, SIN],
       "soluciones": {"cifrado": {"respuesta": "Así funciona…", "codigo": "print(1)", "veces": 3, "cuando": 5}}}
p = cc.pestanas(est)
ok([x["id"] for x in p] == ["pensamiento", "conocimiento", "mejoras", "tareas"], "cuatro pestañas")
ok(p[0]["titulo"] == "Pensamiento (3)" and p[1]["titulo"] == "Conocimiento (2)" and p[2]["titulo"] == "Mejoras (2)",
   "cada pestaña dice cuántas tiene")
ok("memoria caché" in p[0]["texto"] and "cifrado" not in p[0]["texto"].split("caché")[0], "Pensamiento: las dudas")
ok("SOLUCIONES GUARDADAS (1)" in p[1]["texto"] and "mejorada 3 veces" in p[1]["texto"]
   and "con código que funciona" in p[1]["texto"], "Conocimiento: soluciones guardadas y lo comprobado")
m = p[2]["texto"]
ok("KIRAOS (el portátil)" in m and "KIRA APP (el móvil)" in m and m.index("KIRAOS") < m.index("KIRA APP"),
   "Mejoras: separadas en portátil y móvil")
ok("SE DEBE mejorar" in m and "SE PUEDE mejorar" in m, "Mejoras: se debe / se puede")
ok("nada se aplica solo" in m, "Mejoras: recuerda que nada se aplica solo")
m2 = cc.pestana_mejoras(est, {"kiraos_pendiente": {"nombre": "decir_hora"}, "para_movil": [{"nombre": "atajos"}],
                              "permisos": {"numpy": {"motivo": "calcular"}}, "kiraos_instaladas": [{"nombre": "saludar"}]})
ok("ESPERAN TU PERMISO" in m2 and "decir_hora" in m2 and "atajos" in m2 and "numpy" in m2 and "saludar" in m2,
   "Mejoras: también las de verdad que esperan tus dos toques y las instaladas")
ok("Aún no he pensado nada sobre mejorar" in cc.pestana_mejoras({"notas": [DUDA]}), "sin ideas de mejora: lo dice")

ahora = time.time()
tr = {"cola": [{"orden": "estudia python", "estado": "en curso"}, {"orden": "hazme una app android", "estado": "en cola"}],
      "hechas": [{"orden": "busca la wifi", "estado": "hecho", "fin": ahora - 120},
                 {"orden": "experimenta con grafos", "estado": "error", "fin": ahora - 7200},
                 {"orden": "piensa una", "estado": "cancelado", "fin": ahora - 30}],
      "actividad": {"pensando": True}, "pausada": False}
enc = [{"texto": "qué es un hash", "hecha": False}, {"texto": "puedes hacer lo mismo que grep", "hecha": True,
                                                     "ultima": ahora - 60}]
t = cc.pestana_tareas(tr, enc, {"tema": "la caché", "activo": True, "resuelto": False}, ahora)
a, e, h = t.split("\n\nEN ESPERA")[0], t.split("EN ESPERA")[1].split("TERMINADAS")[0], t.split("TERMINADAS")[1]
ok("estudia python" in a and "Pensando" in a and "Centrada en «la caché»" in a, "ACTIVAS: la de curso, pensar, el foco")
ok("hazme una app android" in e and "qué es un hash" in e, "EN ESPERA: la cola y tus encargos")
ok("busca la wifi" in h and "hace 2 min" in h and "falló" in h and "la paraste" in h and "grep" in h,
   "TERMINADAS: hechas, fallidas, paradas y encargos investigados, con cuándo")
ok(t.startswith("ACTIVAS (3)") and "EN ESPERA (2)" in t, "con cuántas hay")
t2 = cc.pestana_tareas({"pausada": True}, [], {"tema": "x", "activo": False, "resuelto": False})
ok("EN PAUSA" in t2 and "Aparcado para otro día: «x»" in t2 and "aún nada terminado" in t2, "pausa, aparcado y vacío")
ok("nada ahora mismo" in cc.pestana_tareas(), "sin datos no revienta")

# ---------- el núcleo apunta las terminadas ----------
import nucleo_portatil as npk
tb = npk.Trabajos(lambda o, paso: {"texto": "vale"})
tb.empezar("primera")
tb.empezar("segunda")
lim = time.time() + 5
while time.time() < lim and len(tb.hechas()) < 2:
    time.sleep(0.05)
hh = tb.hechas()
ok([x["orden"] for x in hh] == ["segunda", "primera"] and all(x["fin"] for x in hh), "el núcleo guarda las terminadas")

# ---------- la ventana ----------
import escritorio_kira as ek
json.dump(est, open(os.path.join(T, "pensamientos.json"), "w"))
json.dump(enc, open(os.path.join(T, "preguntas_mias.json"), "w"))


class CliN:
    def estado(self):
        return tr

    def mejoras(self):
        return {"pendiente": {"nombre": "decir_hora"}, "instaladas": []}


esc = ek.EscritorioMixin()
esc.cli = None
esc.nucleo_cli = CliN()
a = esc.app("cuaderno")
ok(len(a.get("pestanas") or []) == 4 and "decir_hora" in a["pestanas"][2]["texto"]
   and "estudia python" in a["pestanas"][3]["texto"], "la ventana del cuaderno trae las cuatro pestañas con todo")

node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(600);
  await pg.click('.icono[data-app="cuaderno"]'); await pg.waitForTimeout(400);
  const pest = await pg.$$eval('[data-pest]', l => l.map(x => x.textContent));
  const t1 = await pg.textContent('#vcuerpo .texto');
  await pg.click('[data-pest="tareas"]'); await pg.waitForTimeout(150);
  const t2 = await pg.textContent('#vcuerpo .texto'); const on = await pg.textContent('.pest.on');
  const fondo = await pg.evaluate(() => getComputedStyle(document.getElementById('ventana')).backgroundColor);
  await pg.screenshot({path: process.argv[3]});
  console.log(JSON.stringify({errs, pest, t1, t2, on, fondo}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    f = os.path.join(T, "c.js")
    open(f, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, f, html, os.path.join(T, "cuaderno.png")], capture_output=True, text=True, timeout=120,
                       env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(len(d["pest"]) == 4 and d["pest"][0].startswith("Pensamiento"), "Chromium: las pestañas arriba")
        ok("PENSANDO" in d["t1"] and "ACTIVAS" in d["t2"] and d["on"] == "Tareas", "Chromium: se cambia de pestaña")
        ok("0.97" in d["fondo"], "Chromium: la ventana casi opaca (no se ven los iconos por detrás): " + d["fondo"])
    else:
        print("  (sin Chromium: no pruebo la pantalla)", out[:200])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
