# -*- coding: utf-8 -*-
"""v3.19: el dueño le pide a Kira ventanas, secciones y botones nuevos («crea en la wifi una sección con un botón…»)
y que los cambie cuando quiera. Son MEJORAS (laboratorio + dos toques) que declaran su ventana como DATOS (texto y
botones que le dan órdenes); la pantalla nunca ejecuta código de una mejora."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["KIRA_DATOS_NUCLEO"] = T
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import ventanas_kira as vk
import laboratorio_movil_kira as lm

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ---------- validar (solo datos) ----------
v = vk.validar("mis redes", {"en": "wifi", "titulo": "Mis redes", "texto": "Atajos.",
                             "botones": [{"texto": "Guardadas", "orden": "redes guardadas"}]})
ok(v == {"id": "mis redes", "en": "wifi", "titulo": "Mis redes", "texto": "Atajos.",
         "botones": [{"texto": "Guardadas", "orden": "redes guardadas"}]}, "una ventana buena, limpia")
ok(vk.validar("dia", {"en": "Pantalla principal", "texto": "x"})["en"] == "escritorio", "«pantalla principal» = escritorio")
ok(vk.validar("dia", {"texto": "x"})["en"] == "escritorio" and vk.validar("dia", {"texto": "x"})["titulo"] == "Dia",
   "sin «en» ni título: al escritorio con su nombre")


def falla(ident, d, trozo):
    try:
        vk.validar(ident, d)
        return False
    except vk.VentanaError as e:
        return trozo in str(e)


ok(falla("x", {"en": "el banco", "texto": "a"}, "«en» debe ser"), "un sitio que no existe: no")
ok(falla("x", {"texto": "a", "html": "<b>"}, "sobra: html"), "nada de HTML ni otras claves")
ok(falla("x", {"botones": [{"texto": "a", "orden": str(i)} for i in range(13)]}, "como mucho 12"), "tope de botones")
ok(falla("x", {"botones": [{"texto": "sin orden"}]}, "necesita «texto»"), "un botón sin orden: no")
ok(falla("x", {}, "vacía"), "una ventana vacía: no")
ok(falla("X/../../etc", {"texto": "a"}, "no vale"), "un nombre raro: no")
ok(falla("x", "<script>", "diccionario"), "si no devuelve un diccionario: no")
v = vk.validar("x", {"texto": "<script>alert(1)</script>" + "a" * 5000, "botones": [{"texto": "b" * 80, "orden": "o\nx"}]})
ok(len(v["texto"]) <= vk.MAX_TEXTO and v["texto"].startswith("<script>") and v["botones"][0]["orden"] == "o x"
   and len(v["botones"][0]["texto"]) <= 40, "se recorta lo largo (y lo raro queda como TEXTO, la pantalla lo escapa)")

# ---------- reconocer lo que pides ----------
O = vk.orden
ok(O("crea en la wifi una sección con un botón que diga qué redes tengo guardadas")[0] == "crear", "crear una sección en la wifi")
ok(O("Kira, crea una ventana nueva en el escritorio llamada Mi día con tres botones")[0] == "crear", "crear una ventana en el escritorio")
ok(O("pon un botón en la wifi para arreglar la conexión")[0] == "crear", "poner un botón")
ok(O("cambia la ventana mis redes: que tenga también un botón para apagar") ==
   ("cambiar", "mis redes", "que tenga también un botón para apagar"), "cambiar una ventana")
ok(O("quita la ventana mis redes") == ("quitar", "mis redes"), "quitar una ventana")
ok(O("crea un programa que tenga un botón") is None and O("hazme un juego con botones") is None,
   "un programa o un juego con botones NO es esto")
ok(O("pon la wifi") is None and O("crea una ventana") is None and O("mira la ventana") is None, "ni frases a medias")
ok(vk.pedido_de_ventana("crea un botón") and not vk.pedido_de_ventana("suma dos números"), "cuándo darle al cerebro el ejemplo")
ok("ventana mis redes" in vk.ejemplo_para_cerebro("crea una ventana") and vk.ejemplo_para_cerebro("suma") == "",
   "el ejemplo de ventana solo cuando hace falta (al cerebro pequeño le cuesta leer)")

MODULO = '''def registrar():
    def ventana(texto):
        return {"en": "wifi", "titulo": "Mis redes", "texto": "Atajos para mis redes.",
                "botones": [{"texto": "Redes guardadas", "orden": "redes guardadas"},
                            {"texto": "Saludo", "orden": "saludo de redes"}]}
    def saludo(texto):
        return "Hola desde mis redes."
    return {"ventana mis redes": ventana, "saludo de redes": saludo}
'''
MALO = MODULO.replace('"en": "wifi"', '"en": "el banco"')

# ---------- el laboratorio del móvil (el que corre en KiraOS) ----------
L = lm.LaboratorioMovil()
r = L.probar("mis_redes", MODULO)
ok(r["ok"], "el laboratorio aprueba una mejora con ventana: " + str([e for e in r.get("etapas", []) if not e.get("ok")]))
ok(any(e.get("nombre") == "ventanas" and e.get("ok") for e in r.get("etapas", [])) or "VENTANAS_OK" in json.dumps(r),
   "…y la comprueba en su etapa «ventanas»")
r = L.probar("mal", MALO)
ok(not r["ok"] and "«en» debe ser" in json.dumps(r, ensure_ascii=False), "una ventana mal hecha: el laboratorio la rechaza con el motivo")

# el laboratorio del ordenador (test FIJO, no se toca → no hay que volver a sellar)
f = os.path.join(T, "mis_redes.py")
open(f, "w", encoding="utf-8").write(MODULO)
r = subprocess.run([sys.executable, os.path.join(RAIZ, "kira_laboratorio", "tests_fijos", "test_contrato.py"), f],
                   capture_output=True, text=True, timeout=30)
ok(r.returncode == 0 and "CONTRATO_OK" in r.stdout, "el test fijo del laboratorio del PC también la acepta (sin resellar)")

# ---------- el núcleo la carga ----------
import kira_god
core = kira_god.KiraGodCore.__new__(kira_god.KiraGodCore)
core.dir = T
core.registrar_error = lambda *a: None
os.makedirs(os.path.join(T, "modulos"), exist_ok=True)
open(os.path.join(T, "modulos", "mis_redes.py"), "w", encoding="utf-8").write(MODULO)
open(os.path.join(T, "modulos", "malo.py"), "w", encoding="utf-8").write(MALO)
core.cargar_modulos()
lv = core.ventanas_lista()
ok(len(lv) == 1 and lv[0]["id"] == "mis redes" and lv[0]["modulo"] == "mis_redes", "Kira carga la ventana de su mejora")
ok("saludo de redes" in core.comandos_modulos and "ventana mis redes" not in core.comandos_modulos,
   "la ventana NO es una orden; sus órdenes sí")
ok("malo" in core.errores_modulos and "«en» debe ser" in core.errores_modulos["malo"], "una ventana mala no carga y dice por qué")

# ---------- pedirlas al núcleo: crear, cambiar, quitar ----------
import nucleo_portatil as npk


class PanelFalso:
    def __init__(self):
        self.llamadas = []
        self.pendiente = type("P", (), {"codigo": "nuevo", "nombre": "mis_redes"})()

    def enviar_orden(self, pedido, nombre=None, extra=""):
        self.llamadas.append((pedido, nombre, extra))
        return {"aprobable": True}


pan = PanelFalso()
core._panel = pan
pasos = []
r = npk.ejecutar(core, "crea en la wifi una sección con un botón que diga qué redes tengo guardadas", lambda f, t: pasos.append(t))
ok(r["ok"] and "Cuaderno ▸ Mejoras" in r["texto"] and pan.llamadas[-1][1] is None, "«crea…» = una mejora que espera tus dos toques")
ok("sección" in pan.llamadas[-1][0], "…con lo que pediste")
r = npk.ejecutar(core, "Kira, cambia la ventana mis redes: que tenga también un botón para apagar la wifi", lambda f, t: None)
p, nombre, extra = pan.llamadas[-1]
ok(r["ok"] and nombre == "mis_redes", "«cambia la ventana…»: la versión nueva SUSTITUYE a la misma mejora")
ok("Código actual" in extra and "def registrar" in extra and "apagar la wifi" in extra, "…y el cerebro recibe el código de ahora y tu cambio")
ok("Volver atrás" in r["texto"], "…y se puede volver a la de antes")
r = npk.ejecutar(core, "cambia la ventana del tiempo: más grande", lambda f, t: None)
ok(not r["ok"] and "«Mis redes»" in r["texto"], "si no existe, dice cuáles hay")
r = npk.ejecutar(core, "quita la ventana mis redes", lambda f, t: None)
ok("Quitar" in r["texto"] and "mis_redes" in r["texto"], "quitar: dice cómo (con tus dos toques)")

# ---------- la pantalla (solo pinta texto y botones) ----------
import escritorio_kira as ek


class NucleoFalso:
    def ventanas(self):
        return lv + [{"id": "trampa", "en": "escritorio", "titulo": "<img src=x onerror=alert(1)>", "texto": "hola",
                      "botones": [], "modulo": "x"},
                     {"id": "rota", "en": "el banco", "titulo": "Mal", "texto": "x", "botones": []}]

    def estado(self):
        return {}


esc = ek.EscritorioMixin()
esc.cli = None
esc.nucleo_cli = NucleoFalso()
ex = esc.ventanas_extra()
ok([x["id"] for x in ex] == ["mis redes", "trampa"], "la pantalla vuelve a validar (la rota no sale)")
b = esc.barra()
ok({"id": "mis redes", "en": "wifi", "titulo": "Mis redes"} in b["extras"], "la barra le pasa las ventanas a la pantalla")
a = esc.app("extra:mis redes")
ok(a["titulo"] == "Mis redes" and [x["accion"] for x in a["botones"]] == ["decir:redes guardadas", "decir:saludo de redes"],
   "abrirla: sus botones le dan las órdenes a Kira")
ok("cambia la ventana mis redes" in a["texto"], "…y dice cómo cambiarla")
ok("ya no está" in esc.app("extra:nada")["texto"], "una que ya no está: lo dice")

# ---------- en la pantalla de verdad (Chromium) ----------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e))); let alerta=false; pg.on('dialog', d => { alerta=true; d.dismiss(); });
  await pg.addInitScript(() => { window.__extras=[
     {id:"mi dia",en:"escritorio",titulo:"Mi día",texto:"Lo de hoy.",botones:[{texto:"Qué tengo hoy",orden:"qué tengo hoy"}]},
     {id:"mis redes",en:"wifi",titulo:"Mis redes",texto:"Atajos.",botones:[{texto:"Guardadas",orden:"redes guardadas"}]},
     {id:"trampa",en:"escritorio",titulo:"<img src=x onerror=alert(1)>",texto:"<b>no</b>",botones:[]}]; });
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(300);
  await pg.evaluate(() => { FAKE._extras = window.__extras; refrescaBarra(); }); await pg.waitForTimeout(500);
  const iconos = await pg.$$eval('.icono', l => l.map(x => x.dataset.app));
  await pg.click('.icono[data-app="extra:mi dia"]'); await pg.waitForTimeout(400);
  const t1 = await pg.textContent('#vtitulo'); const bot = await pg.$$eval('#vcuerpo [data-acc]', l => l.map(x => x.dataset.acc));
  await pg.click('#volver'); await pg.waitForTimeout(200);
  await pg.click('.icono[data-app="wifi"]'); await pg.waitForTimeout(500);
  const cab = await pg.$$eval('#vextras button', l => l.map(x => x.textContent));
  await pg.click('#vextras button'); await pg.waitForTimeout(400);
  const t2 = await pg.textContent('#vtitulo');
  await pg.click('#volver'); await pg.waitForTimeout(200);
  await pg.click('.icono[data-app="extra:trampa"]'); await pg.waitForTimeout(400);
  const t3 = await pg.textContent('#vtitulo'); const imgs = await pg.$$eval('img', l => l.length);
  await pg.screenshot({path: process.argv[3]});
  console.log(JSON.stringify({errs, alerta, iconos, t1, bot, cab, t2, t3, imgs}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    fjs = os.path.join(T, "v.js")
    open(fjs, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, fjs, html, os.path.join(T, "ventanas.png")], capture_output=True, text=True, timeout=180, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok("extra:mi dia" in d["iconos"] and len(d["iconos"]) == 13, "Chromium: su ventana nueva sale como icono del escritorio")
        ok(d["t1"] == "Mi día" and d["bot"] == ["decir:qué tengo hoy"], "Chromium: se abre con su botón")
        ok(d["cab"] == ["+ Mis redes"] and d["t2"] == "Mis redes", "Chromium: la sección añadida a la WiFi sale arriba y se abre")
        ok(not d["alerta"] and d["imgs"] == 0 and d["t3"].startswith("<img"), "Chromium: lo que escriba una mejora es solo TEXTO (no ejecuta nada)")
        print("  captura:", os.path.join(T, "ventanas.png"))
    else:
        print("  (sin Chromium)", r.stdout[-800:], r.stderr[-300:])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
