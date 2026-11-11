# -*- coding: utf-8 -*-
"""v3.23: el dueño cambia las salas POR DENTRO con una frase: letra, color, tamaño de la ventana, quitar/renombrar
botones y pestañas, con qué pestaña se abre, una nota fija; y las mejoras de Kira pueden poner TARJETAS dentro de
una sala (lugar «arriba»/«abajo»). Todo son DATOS: la pantalla los aplica; nada de código de pantalla."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
RUTA = os.path.join(T, "sistema.json")
os.environ["KIRA_SISTEMA"] = RUTA
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import sistema_kira as sk
import ventanas_kira as vk

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


casos = {
    "en el cuaderno, letra más grande": ("sala_letra", ("cuaderno", "+")),
    "pon la letra grande en la terminal": ("sala_letra", ("terminal", "grande")),
    "pon el cuaderno en verde": ("sala_color", ("cuaderno", "bosque")),
    "cambia el color de la sala programando a fuego": ("sala_color", ("programando", "fuego")),
    "haz la ventana del mapa a pantalla completa": ("sala_tamano", ("mapa", "completa")),
    "haz el cuaderno más pequeño": ("sala_tamano", ("cuaderno", "pequena")),
    "que el cuaderno se abra en Tareas": ("sala_pestana", ("cuaderno", "Tareas")),
    "quita el botón Cerebro grande de ajustes": ("sala_ocultar", ("ajustes", "Cerebro grande")),
    "en ajustes, oculta el botón Sin voz": ("sala_ocultar", ("ajustes", "Sin voz")),
    "oculta la pestaña Conocimiento del cuaderno": ("sala_ocultar", ("cuaderno", "Conocimiento")),
    "vuelve a poner el botón Cerebro grande en ajustes": ("sala_mostrar", ("ajustes", "Cerebro grande")),
    "cambia el botón Sin voz de ajustes por Callada": ("sala_renombrar", ("ajustes", "Sin voz", "Callada")),
    "en la wifi cambia el botón Buscar por Escanear": ("sala_renombrar", ("wifi", "Buscar", "Escanear")),
    "pon una nota en programando: recuerda guardar": ("sala_nota", ("programando", "recuerda guardar")),
    "quita la nota del cuaderno": ("sala_nota", ("cuaderno", "")),
    "deja la sala cuaderno como estaba": ("sala_serie", ("cuaderno",)),
    "deja todas las salas como estaban": ("sala_serie", ("todas",)),
}
mal = [(f, sk.orden(f)) for f, e in casos.items() if sk.orden(f) != e]
ok(not mal, f"reconoce las {len(casos)} órdenes de las salas " + str(mal[:2]))
ok(sk.orden("pon kiraos en azul") == ("tema", "oceano") and sk.orden("quita el botón mis redes") is None
   and sk.orden("crea en programando una sección con un botón") is None,
   "no se come el tema general ni crear/quitar ventanas de mejoras")
ok(sk.orden("pon la nevera en verde") is None, "una sala que no existe: no es esta orden")

sk.responder("en el cuaderno, letra más grande")
sk.responder("en el cuaderno, letra más grande")
ok(sk.para_pantalla()["salas"]["cuaderno"]["letra"] == "enorme", "«más grande» dos veces: grande → enorme")
sk.responder("pon el cuaderno en verde")
ok(sk.para_pantalla()["salas"]["cuaderno"]["colores"]["neon"] == "#4ade80", "color de UNA sala")
r = sk.responder("quita el botón Cerebro grande de ajustes")
ok(sk.para_pantalla()["salas"]["ajustes"]["ocultar"] == ["Cerebro grande"] and "vuelve a poner" in r, "quitar un botón (y cómo traerlo)")
sk.responder("vuelve a poner el botón cerebro GRANDE en ajustes")
ok("ocultar" not in sk.para_pantalla()["salas"].get("ajustes", {}), "volver a ponerlo (sin importar mayúsculas)")
sk.responder("cambia el botón Sin voz de ajustes por Callada")
ok(sk.para_pantalla()["salas"]["ajustes"]["renombrar"] == {"Sin voz": "Callada"}, "renombrar un botón")
sk.responder("que el cuaderno se abra en Tareas")
sk.responder("pon una nota en programando: recuerda guardar")
p = sk.para_pantalla()["salas"]
ok(p["cuaderno"]["pestana"] == "Tareas" and p["programando"]["nota"] == "recuerda guardar", "pestaña de inicio y nota")
sk.responder("deja la sala cuaderno como estaba")
ok("cuaderno" not in sk.para_pantalla()["salas"], "dejar UNA sala como estaba")
sk.responder("deja todas las salas como estaban")
ok(sk.para_pantalla()["salas"] == {}, "todas como estaban")
open(RUTA, "w").write(json.dumps({"salas": {"ajustes": {"letra": "<x>", "color": "rojo-raro", "ocultar": ["a" * 99, ""],
                                                         "nota": "n" * 5000, "renombrar": {"x": "<b>" * 30}},
                                             "../../etc": {"letra": "grande"}, "mapa": "basura"}}))
p = sk.para_pantalla()["salas"]
ok(list(p) == ["ajustes"] and "letra" not in p["ajustes"] and "color" not in p["ajustes"]
   and len(p["ajustes"]["ocultar"][0]) == 40 and len(p["ajustes"]["nota"]) == sk.MAX_NOTA
   and len(p["ajustes"]["renombrar"]["x"]) == 40, "un archivo tocado a mano se limpia")
os.remove(RUTA)
ok("las salas POR DENTRO" in sk.QUE_PUEDO, "«qué puedo cambiar» lo explica")

# tarjetas de Kira DENTRO de una sala (mejora): «lugar»
v = vk.validar("mi atajo", {"en": "cuaderno", "texto": "x", "lugar": "arriba", "botones": [{"texto": "a", "orden": "piensa"}]})
ok(v["lugar"] == "arriba", "una ventana de mejora puede ir DENTRO de una sala")
ok("lugar" not in vk.validar("y", {"en": "wifi", "texto": "x"}), "sin lugar: un botón arriba, como antes")
ok("lugar" not in vk.validar("z", {"en": "escritorio", "texto": "x", "lugar": "arriba"}), "en el escritorio siempre es un icono")
try:
    vk.validar("w", {"texto": "x", "lugar": "<script>"})
    ok(False, "lugar raro")
except vk.VentanaError as e:
    ok("«lugar» debe ser" in str(e), "lugar raro: no vale")
ok('"lugar"' in vk.EJEMPLO_VENTANA, "el cerebro sabe que puede ponerlas dentro")

# ---------- en la pantalla de verdad (Chromium) ----------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e))); let alerta=false; pg.on('dialog', d => { alerta=true; d.dismiss(); });
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(300);
  await pg.evaluate(() => {
    FAKE._extras=[{id:"atajo",en:"ajustes",titulo:"Mi atajo",lugar:"arriba",texto:"<img src=x onerror=alert(1)>",botones:[{texto:"Piensa",orden:"piensa"}]}];
    FAKE._aspecto={tema:"noche",colores:{fondo:"#05070f",neon:"#22d3ee",acento:"#f472d0",texto:"#e7ecf5"},ocultos:[],
      salvapantallas:{activo:false,minutos:10,estilo:"orbe"},orden_iconos:[],dibujos:{},nombres:{},
      salas:{ajustes:{letra:"grande",tamano:"completa",ocultar:["Cerebro grande"],renombrar:{"Sin voz":"Callada"},
                      nota:"Hola <b>papi</b>",color:"bosque",colores:{fondo:"#06110b",neon:"#4ade80",acento:"#facc15",texto:"#e6f4ea"}},
             cuaderno:{pestana:"Tareas",ocultar:["Conocimiento (1)"]}}}; refrescaBarra(); });
  await pg.waitForTimeout(500);
  await pg.click('.icono[data-app="ajustes"]'); await pg.waitForTimeout(500);
  const r = await pg.evaluate(() => { const c=document.getElementById('vcuerpo'), v=document.getElementById('ventana');
    const bs=[...c.querySelectorAll('.botones > button')].filter(x=>x.closest('.tarjeta-extra')===null);
    return {cls:c.className, vcls:v.className, cian:getComputedStyle(v).getPropertyValue('--cian').trim(),
      visibles:bs.filter(x=>x.style.display!=='none').map(x=>x.textContent),
      nota:(c.querySelector('.nota-sala')||{}).textContent, notaHtml:(c.querySelector('.nota-sala')||{}).innerHTML,
      tarjeta:!!c.querySelector('.tarjeta-extra'), tarjTxt:(c.querySelector('.tarjeta-extra div')||{}).textContent,
      imgs:c.querySelectorAll('img').length, cab:[...document.querySelectorAll('#vextras button')].length}; });
  // vuelve a pintarse sola (como las ventanas en vivo) y lo aplica otra vez
  await pg.evaluate(() => { llama("app","ajustes").then(function(d){ pintaApp("ajustes", d); }); }); await pg.waitForTimeout(400);
  const r2 = await pg.evaluate(() => [...document.querySelectorAll('#vcuerpo .botones > button')].filter(x=>x.style.display!=='none' && !x.closest('.tarjeta-extra')).map(x=>x.textContent));
  await pg.screenshot({path: process.argv[3]});
  await pg.click('#volver'); await pg.waitForTimeout(200);
  await pg.click('.icono[data-app="cuaderno"]'); await pg.waitForTimeout(500);
  const r3 = await pg.evaluate(() => ({on:(document.querySelector('.pest.on')||{}).textContent,
     ocultas:[...document.querySelectorAll('.pest')].filter(x=>x.style.display==='none').map(x=>x.textContent),
     vcls:document.getElementById('ventana').className, cls:document.getElementById('vcuerpo').className}));
  console.log(JSON.stringify({errs, alerta, r, r2, r3}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    fjs = os.path.join(T, "s.js")
    open(fjs, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, fjs, html, os.path.join(T, "sala.png")], capture_output=True, text=True, timeout=180, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        x = d["r"]
        ok(not d["errs"] and not d["alerta"], "Chromium: sin errores ni nada ejecutado " + str(d["errs"]))
        ok("l-grande" in x["cls"] and "t-completa" in x["vcls"], "Chromium: letra grande y a pantalla completa")
        ok(x["cian"] == "#4ade80", "Chromium: el color de ESA sala")
        ok("Cerebro grande" not in x["visibles"] and "Callada" in x["visibles"] and "Sin voz" not in x["visibles"],
           "Chromium: botón quitado y otro renombrado " + str(x["visibles"]))
        ok(x["nota"] == "Hola <b>papi</b>" and "<b>" not in x["notaHtml"], "Chromium: la nota sale como TEXTO")
        ok(x["tarjeta"] and x["tarjTxt"].startswith("<img") and x["imgs"] == 0 and x["cab"] == 0,
           "Chromium: la tarjeta de la mejora sale DENTRO, como texto")
        ok("Cerebro grande" not in d["r2"] and "Callada" in d["r2"], "Chromium: al volver a pintarse, lo mantiene")
        ok(d["r3"]["on"] == "Tareas" and d["r3"]["ocultas"] == ["Conocimiento (1)"], "Chromium: el cuaderno se abre en Tareas y sin la pestaña oculta")
        ok("t-completa" not in d["r3"]["vcls"] and "l-grande" not in d["r3"]["cls"], "Chromium: cada sala con lo suyo")
        print("  captura:", os.path.join(T, "sala.png"))
    else:
        print("  (sin Chromium)", r.stdout[-800:], r.stderr[-300:])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
