# -*- coding: utf-8 -*-
"""v3.22: «mueve el icono del mapa al principio», «cambia el icono del mapa por una estrella», «cambia el nombre del
icono del mapa a Ataques», también con las ventanas que Kira se añadió; «deja los iconos como estaban»."""
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

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


EX = [("mi dia", "Mi día")]
casos = {
    "mueve el icono del mapa al principio": ("mover_icono", ("del mapa", ("inicio", None))),
    "mueve el icono de la terminal al final": ("mover_icono", ("de la terminal", ("final", None))),
    "pon el icono del cuaderno a la posición 2": ("mover_icono", ("del cuaderno", ("posicion", 2))),
    "mueve el icono del wifi después del mapa": ("mover_icono", ("del wifi", ("despues", "mapa"))),
    "cambia el icono del mapa por una estrella": ("dibujo_icono", ("mapa", "estrella")),
    "ponle una estrella al icono del mapa": ("dibujo_icono", ("mapa", "estrella")),
    "cambia el nombre del icono del mapa a Ataques": ("nombre_icono", ("mapa", "Ataques")),
    "renombra el icono de la terminal como Consola": ("nombre_icono", ("terminal", "Consola")),
    "deja los iconos como estaban": ("iconos_serie", None),
}
mal = [(f, sk.orden(f)) for f, e in casos.items() if sk.orden(f) != e]
ok(not mal, "reconoce mover / dibujo / nombre / como estaban " + str(mal[:2]))
ok(sk.orden("cambia el icono mis redes: que tenga otro botón") is None, "cambiar una VENTANA sigue siendo una mejora (v3.19)")
ok(sk.orden("pon el icono del mapa") is None and sk.orden("crea un icono nuevo con un botón") is None,
   "crear iconos nuevos sigue siendo una mejora")
ok(sk.resolver_icono("del mapa") == "mapa" and sk.resolver_icono("de mi día", EX) == "extra:mi dia"
   and sk.resolver_icono("nada raro", EX) is None, "encuentra el icono (de serie o una ventana añadida)")

sk.responder("mueve el icono del mapa al principio", extras=EX)
p = sk.para_pantalla()
ok(p["orden_iconos"][0] == "mapa", "mover al principio")
sk.responder("mueve el icono de mi día antes del buscador", extras=EX)
o = sk.para_pantalla()["orden_iconos"]
ok(o.index("extra:mi dia") == o.index("buscador") - 1, "mover una ventana añadida, delante de otro icono")
r = sk.responder("pon el icono del cuaderno a la posición 2", extras=EX)
ok(sk.para_pantalla()["orden_iconos"][1] == "cuaderno" and "puesto 2" in r, "a una posición")
r = sk.responder("cambia el icono del mapa por una lupa", extras=EX)
ok(sk.para_pantalla()["dibujos"]["mapa"] == "buscador", "«una lupa» = el dibujo del buscador")
sk.responder("cambia el icono de mi día por un corazón", extras=EX)
ok(sk.para_pantalla()["dibujos"]["extra:mi dia"] == "corazon", "dibujo nuevo para una ventana añadida")
sk.responder("cambia el nombre del icono del mapa a Ataques", extras=EX)
ok(sk.para_pantalla()["nombres"]["mapa"] == "Ataques", "nombre nuevo")
sk.responder("renombra el icono de la terminal como <b>X</b>", extras=EX)
ok("<" not in sk.para_pantalla()["nombres"]["terminal"], "un nombre con < > se limpia")
ok(sk.responder("mueve el icono de la nevera al final", extras=EX).startswith("[x]"), "un icono que no existe: lo dice")
open(RUTA, "w").write(json.dumps({"orden_iconos": ["mapa", "../../x", "extra:<script>"], "dibujos": {"mapa": "<svg>"},
                                  "nombres": {"wifi": "a" * 200}}))
p = sk.para_pantalla()
ok(p["orden_iconos"] == ["mapa"] and p["dibujos"] == {} and len(p["nombres"]["wifi"]) == 30, "tocado a mano: se limpia")
sk.responder("cambia el icono del mapa por una estrella")
sk.responder("deja los iconos como estaban")
p = sk.para_pantalla()
ok(p["orden_iconos"] == [] and p["dibujos"] == {} and p["nombres"] == {}, "«deja los iconos como estaban»")
ok("mueve el icono" in sk.QUE_PUEDO, "«qué puedo cambiar» lo explica")

# la pantalla y el núcleo le pasan las ventanas añadidas
src = open(os.path.join(RAIZ, "kira_portatil", "escritorio_kira.py"), encoding="utf-8").read()
ok("extras=ex" in src, "la pantalla le pasa sus ventanas añadidas")
src = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("extras=ex_" in src, "el núcleo también")

# ---------- en la pantalla de verdad (Chromium) ----------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(300);
  await pg.evaluate(() => { FAKE._extras=[{id:"mi dia",en:"escritorio",titulo:"Mi día"}];
    FAKE._aspecto={tema:"noche",colores:{fondo:"#05070f",neon:"#22d3ee",acento:"#f472d0",texto:"#e7ecf5"},ocultos:[],
      salvapantallas:{activo:false,minutos:10,estilo:"orbe"},orden_iconos:["mapa","extra:mi dia"],
      dibujos:{"mapa":"estrella","extra:mi dia":"corazon"},nombres:{"mapa":"Ataques <i>"}}; refrescaBarra(); });
  await pg.waitForTimeout(500);
  const ids = await pg.$$eval('.icono', l => l.map(x => x.dataset.app));
  const nom = await pg.$eval('.icono[data-app="mapa"] span', x => x.childNodes[0].textContent);
  const d1 = await pg.$eval('.icono[data-app="mapa"] svg', x => x.innerHTML);
  const d2 = await pg.$eval('.icono[data-app="extra:mi dia"] svg', x => x.innerHTML);
  await pg.click('.icono[data-app="mapa"]'); await pg.waitForTimeout(300);
  const tit = await pg.textContent('#vtitulo');
  console.log(JSON.stringify({errs, ids, nom, d1, d2, tit}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    fjs = os.path.join(T, "i.js")
    open(fjs, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, fjs, html], capture_output=True, text=True, timeout=180, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(d["ids"][:2] == ["mapa", "extra:mi dia"] and len(d["ids"]) == 12, "Chromium: los iconos en tu orden")
        ok(d["nom"] == "Ataques <i>", "Chromium: con tu nombre (como texto, sin ejecutar nada)")
        ok("M12 3l2.6" in d["d1"] and "M12 20s" in d["d2"], "Chromium: con los dibujos que elegiste")
        ok(d["tit"] == "Ataques <i>", "Chromium: la ventana también lleva tu nombre")
    else:
        print("  (sin Chromium)", r.stdout[-800:], r.stderr[-300:])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
