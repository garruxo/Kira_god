# -*- coding: utf-8 -*-
"""v3.07: KiraOS se MEJORA A SÍ MISMA con la misma red de seguridad que el móvil: la orden, el laboratorio de verdad,
la mejora ESPERANDO, instalar SOLO con confirmación y SOLO desde el propio portátil (403 desde el móvil), volver atrás
y quitar con copia; la ventana «Mejoras» del escritorio con DOS toques (Chromium)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["KIRA_DATA_DIR"] = T
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import nucleo_portatil as npk

fallos = 0
n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ---------- la orden ----------
P = npk.pedido_mejora_kiraos
ok(P("mejórate: que me digas la hora") == "que me digas la hora", "«mejórate: …»")
ok(P("mejora KiraOS: añade una orden de chistes") == "añade una orden de chistes", "«mejora KiraOS: …»")
ok(P("mejora tu sistema para que recuerde mi cumpleaños") == "para que recuerde mi cumpleaños", "«mejora tu sistema para que…»")
ok(P("prepara una mejora para ti: contar palabras") == "contar palabras", "«prepara una mejora para ti: …»")
ok(P("añádete una función que cuente vocales") == "que cuente vocales", "«añádete una función que…»")
ok(P("mejórate sola") is None and P("mejórate sin parar") is None, "«mejórate sola» es el interruptor de la auto-mejora")
ok(P("mejórate") is None and P("prepara una mejora para el móvil: x") is None, "lo demás no")

# ---------- con el panel DE VERDAD (laboratorio del móvil real) ----------
BUENO = 'def registrar():\n    def f(texto):\n        return "hola " + texto\n    return {"saluda": f}\n'
BUENO2 = 'def registrar():\n    def f(texto):\n        return "hola de nuevo " + texto\n    return {"saluda": f}\n'
cargas = []
core = types.SimpleNamespace(dir=T, comandos_modulos={}, errores_modulos={},
                             cargar_modulos=lambda: (cargas.append(1), 1)[1], recuerdos=None)
pan = npk.panel_de(core)
ok(core._panel is pan and npk.panel_de(core) is pan, "el panel de KiraOS se crea una vez y se queda")
r = pan.probar_modulo(BUENO, "saludar", "que salude")
ok(r["aprobable"], "el laboratorio de verdad aprueba un módulo bueno: " + r["texto"][:80])
e = npk.mejoras_estado(core)
ok(e["pendiente"] and e["pendiente"]["nombre"] == "saludar" and "def registrar" in e["pendiente"]["codigo"],
   "la mejora ESPERA, con su código para que lo veas")
ok(not os.path.exists(os.path.join(pan.promotor.dir_modulos, "saludar.py")), "y NO está instalada todavía")
r = npk.mejora_hacer(core, "aplicar", confirmado=False)
ok(not r["ok"] and "confirmación" in r["texto"], "sin tu confirmación no instala nada")
r = npk.mejora_hacer(core, "aplicar", confirmado=True)
ruta = os.path.join(pan.promotor.dir_modulos, "saludar.py")
ok(r["ok"] and os.path.isfile(ruta) and cargas, "con tu confirmación la instala y se carga: " + r["texto"][:60])
ok(npk.mejoras_estado(core)["pendiente"] is None and
   [m["nombre"] for m in npk.mejoras_estado(core)["instaladas"]] == ["saludar"], "sale entre las instaladas")
pan.probar_modulo(BUENO2, "saludar", "otra versión")
npk.mejora_hacer(core, "aplicar", confirmado=True)
ok("de nuevo" in open(ruta).read(), "una versión nueva encima")
r = npk.mejora_hacer(core, "revertir", "saludar")
ok(r["ok"] and "de nuevo" not in open(ruta).read(), "«Volver atrás» deja la versión anterior")
ok(not npk.mejora_hacer(core, "quitar", "saludar")["ok"], "quitar también pide confirmación")
r = npk.mejora_hacer(core, "quitar", "saludar", confirmado=True)
ok(r["ok"] and not os.path.exists(ruta), "quitar la saca (con copia en respaldos)")
pan.probar_modulo(BUENO, "otra", "x")
ok(npk.mejora_hacer(core, "rechazar")["ok"] and npk.mejoras_estado(core)["pendiente"] is None, "descartar")
ok(not npk.mejora_hacer(core, "borrar_todo")["ok"], "acciones raras no")
malo = 'def registrar():\n    import os\n    os.system("rm -rf /")\n    return {}\n'
r = pan.probar_modulo(malo, "malo", "x")
ok(not r["aprobable"] and npk.mejoras_estado(core)["pendiente"] is None, "lo peligroso no pasa el laboratorio")

# ---------- la orden en el núcleo ----------
pend_falso = types.SimpleNamespace(nombre="decir_hora", codigo="def registrar(): ...")
fake_pan = types.SimpleNamespace(enviar_orden=lambda p: {"aprobable": True, "nombre": "decir_hora"}, pendiente=pend_falso)
fc = types.SimpleNamespace(dir=T, registrar_actividad=lambda: None, nueva_tarea=lambda: None, _panel=fake_pan,
                           es_estudia_general=lambda o: None)
r = npk.ejecutar(fc, "Kira, mejórate: que me digas la hora", lambda f, t: None)
ok(r["ok"] and "NO la he instalado" in r["texto"] and "«Mejoras»" in r["texto"] and "DOS veces" in r["texto"],
   "«mejórate: …» la deja esperando y dice dónde instalarla")
fake_pan.enviar_orden = lambda p: {"aprobable": False, "texto": "no pasó: falta registrar"}
r = npk.ejecutar(fc, "mejórate: algo raro", lambda f, t: None)
ok(not r["ok"] and "No la instalo" in r["texto"], "si no pasa el laboratorio, lo dice")

# ---------- el servidor: SOLO desde el propio portátil ----------
nuc = npk.Nucleo(T, crear=lambda: core)
srv = npk.crear_servidor("127.0.0.1", 0, "tok", nuc)
threading.Thread(target=srv.serve_forever, daemon=True).start()
cli = npk.ClienteNucleo(f"http://127.0.0.1:{srv.server_address[1]}", "tok")
core._panel.probar_modulo(BUENO, "saludar", "que salude")
d = cli.mejoras()
ok(d["pendiente"]["nombre"] == "saludar", "la ventana pide sus mejoras al núcleo")
ok(not cli.mejora("aplicar")["ok"], "por la red tampoco instala sin confirmación")
ok(cli.mejora("aplicar", confirmado=True)["ok"] and os.path.isfile(ruta), "desde el portátil, con confirmación, sí")
import urllib.error
viejo = npk.es_local
npk.es_local = lambda ip: False                   # como si llegara desde el móvil
try:
    for f in (lambda: cli.mejoras(), lambda: cli.mejora("quitar", "saludar", confirmado=True)):
        try:
            f()
            ok(False, "desde fuera del portátil debería negarse")
        except urllib.error.HTTPError as e:
            ok(e.code == 403, "desde el móvil: 403 (las mejoras de KiraOS solo en el portátil)")
finally:
    npk.es_local = viejo
ok(os.path.isfile(ruta), "y no ha quitado nada")
srv.shutdown()

# ---------- el móvil: «mejora KiraOS: …» se le pasa tal cual; fuera de casa, no ----------
import mando_kira as mk
ok(mk.mejora_es_de_kiraos("mejora KiraOS: chistes") and not mk.mejora_es_de_kiraos("mejora tu voz"),
   "el móvil distingue una mejora para KiraOS")
ok(not mk.permitida_fuera("mejórate: chistes")[0] and not mk.permitida_fuera("añádete una función x")[0],
   "fuera de casa no se piden mejoras")
src = open(os.path.join(RAIZ, "interfaz_kira.py"), encoding="utf-8").read()
ok(src.index("mejora_es_de_kiraos(orden)") < src.index("trabajo_a_kiraos(mdk_.orden_de_mejora(pedido))"),
   "la app la mira ANTES de convertirla en mejora para el móvil")

# ---------- la ventana del escritorio ----------
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
os.environ["KIRA_DATOS_NUCLEO"] = T
import escritorio_kira as ek


class CliN:
    def __init__(self):
        self.hechas = []
        self.d = {"pendiente": {"nombre": "decir_hora", "pedido": "la hora", "codigo": "def registrar():\n    ...",
                                "aprobable": True}, "instaladas": [{"nombre": "saludar", "comandos": ["saluda"]}]}

    def mejoras(self):
        return self.d

    def mejora(self, que, nombre="", confirmado=False):
        self.hechas.append((que, nombre, confirmado))
        return {"ok": True, "texto": "[OK] hecho"}


esc = ek.EscritorioMixin()
esc.cli = None
esc.nucleo_cli = CliN()
a = esc.app("mejoras")
ok("ESPERANDO TU PERMISO" in a["texto"] and "def registrar" in a["texto"] and "saludar" in a["texto"],
   "la ventana enseña la mejora pendiente con su código y las instaladas")
acc = {b["accion"]: b for b in a["botones"]}
ok(acc["hacer:aplicar"].get("dos") and acc["hacer:revertir:saludar"].get("dos") and acc["hacer:quitar:saludar"].get("dos"),
   "Instalar, Volver atrás y Quitar piden DOS toques")
r = esc.app_hacer("mejoras", "aplicar")
ok(r["refrescar"] and esc.nucleo_cli.hechas[-1] == ("aplicar", "", True), "Instalar llama al núcleo con confirmación")
esc.app_hacer("mejoras", "revertir:saludar")
ok(esc.nucleo_cli.hechas[-1] == ("revertir", "saludar", False), "Volver atrás «saludar»")
ok(esc.app_hacer("mejoras", "formatear")["texto"] == "No conozco ese botón.", "botones raros no")
ok("mejoras" in [i["id"] for i in ek.ICONOS], "icono «Mejoras» en el escritorio")

# ---------- Chromium: dos toques de verdad ----------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(600);
  await pg.click('.icono[data-app="mejoras"]'); await pg.waitForTimeout(400);
  const texto = await pg.textContent('#vcuerpo .texto');
  await pg.click('[data-acc="hacer:aplicar"]'); await pg.waitForTimeout(150);
  const tras1 = await pg.textContent('[data-acc="hacer:aplicar"]');
  const res1 = await pg.evaluate(() => (document.getElementById('resultado')||{}).textContent || '');
  await pg.click('[data-acc="hacer:aplicar"]'); await pg.waitForTimeout(400);
  const res2 = await pg.evaluate(() => (document.getElementById('resultado')||{}).textContent || '');
  console.log(JSON.stringify({errs, texto, tras1, res1, res2}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
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
        ok("ESPERANDO" in d["texto"], "Chromium: la ventana «Mejoras» se abre")
        ok("Seguro" in d["tras1"] and d["res1"] == "", "Chromium: el PRIMER toque solo avisa (no instala)")
        ok("aplicar" in d["res2"], "Chromium: el SEGUNDO toque instala")
    else:
        print("  (sin Chromium/playwright: no pruebo la pantalla)", out[:200])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
