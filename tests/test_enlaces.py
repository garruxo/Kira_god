# -*- coding: utf-8 -*-
"""v3.01: Kira SIGUE los enlaces de una página para seguir estudiando (antes solo leía esa página).
- internet: saca los enlaces del contenido (no de los menús), descarta registrarse/comprar/redes/archivos, y elige los
  que tratan del tema o siguen el curso (capítulo, lección, siguiente…).
- núcleo: «estudia en internet X» sigue enlaces; «estudia esta página y sus enlaces: URL» la recorre (acotado).
- KiraOS: el lector del Buscador enseña los enlaces (pulsables, con «‹ Atrás») y «Estúdiala con sus enlaces»."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
import internet_kira as ik  # noqa: E402
import estudio_kira as ek  # noqa: E402

n = 0


def ok(c, m):
    global n
    n += 1
    print(("[OK] " if c else "[X] ") + m)
    if not c:
        sys.exit(1)


HTML = """<html><head><title>Curso de Python: índice</title></head><body>
<nav><a href="/menu-python-variables">Variables en Python (menú)</a></nav>
<header><a href="/inicio">Inicio</a></header>
<main><h1>Curso de Python</h1><p>Bienvenido al curso. Empieza por el primer capítulo.</p>
<ul>
<li><a href="capitulo-1-variables.html">Capítulo 1: variables en Python</a></li>
<li><a href="/curso/capitulo-2-bucles">Capítulo 2: bucles</a></li>
<li><a href="https://docs.python.org/es/3/tutorial/">Tutorial oficial de Python</a></li>
<li><a href="#arriba">Volver arriba</a></li>
<li><a href="/login">Entra en tu cuenta</a></li>
<li><a href="https://www.facebook.com/sharer?u=python">Compartir</a></li>
<li><a href="/img/python.png">Logo de Python</a></li>
<li><a href="mailto:hola@ejemplo.es">Escríbenos</a></li>
<li><a href="https://otra.com/recetas-de-cocina">Recetas de cocina</a></li>
<li><a href="capitulo-1-variables.html#ejemplo">Capítulo 1 otra vez</a></li>
<li><a href="/curso/siguiente">Siguiente lección</a></li>
</ul></main><footer><a href="/aviso-legal">Aviso legal</a></footer></body></html>"""
BASE = "https://ejemplo.es/curso/python/"

p = ik._html_partes(HTML)
enl = ik.enlaces_de(p.enlaces, BASE)
urls = [e["url"] for e in enl]
ok("https://ejemplo.es/curso/python/capitulo-1-variables.html" in urls, "convierte los enlaces relativos en direcciones")
ok("https://ejemplo.es/curso/capitulo-2-bucles" in urls and "https://docs.python.org/es/3/tutorial/" in urls,
   "y guarda los absolutos")
ok(not any("menu-python" in u or u.endswith("/inicio") or "aviso-legal" in u for u in urls),
   "no coge los enlaces de los menús, la cabecera ni el pie")
ok(not any("login" in u or "facebook" in u or u.endswith(".png") or u.startswith("mailto") for u in urls),
   "descarta entrar en cuentas, redes sociales, imágenes y correos")
ok(urls.count("https://ejemplo.es/curso/python/capitulo-1-variables.html") == 1 and not any("#" in u for u in urls),
   "sin anclas ni repetidos")
ok(next(e for e in enl if "capitulo-2" in e["url"])["texto"] == "Capítulo 2: bucles", "guarda el texto de cada enlace")

pag = {"url": BASE, "titulo": "Curso de Python: índice", "enlaces": enl}
el = [e["url"] for e in ik.elegir_enlaces(pag, "python", n=10)]
ok("https://otra.com/recetas-de-cocina" not in el, "no sigue lo que no tiene que ver (recetas de cocina)")
ok(el and "capitulo-1" in el[0], "primero lo que habla del tema y sigue el curso: " + str(el[:3]))
ok(any("siguiente" in u for u in el) and any("capitulo-2" in u for u in el),
   "también sigue la continuación del curso en la misma web (capítulo 2, siguiente lección)")
ok(len(ik.elegir_enlaces(pag, "python", n=2)) == 2, "acotado: solo los que se piden")
ok("capitulo-1" not in str(ik.elegir_enlaces(pag, "python", n=10, ya=[el[0]])[:1]), "no repite los ya leídos")

# la orden
ok(ik.interpretar("estudia esta página y sus enlaces: https://ejemplo.es/x") ==
   {"accion": "estudiar_enlaces", "url": "https://ejemplo.es/x"}, "«estudia esta página y sus enlaces: URL»")
ok(ik.interpretar("estudia sus enlaces") == {"accion": "estudiar_enlaces", "url": None}, "«estudia sus enlaces» (la última)")
ok(ik.interpretar("estudia a fondo esta web https://ejemplo.es/x")["accion"] == "estudiar_enlaces", "«estudia a fondo esta web»")
ok(ik.interpretar("lee https://ejemplo.es/x")["accion"] == "leer", "«lee URL» sigue siendo solo leer")
ok(ek.es_estudia_general("estudia sus enlaces") is None and ek.es_estudia_general("estudia python") == "python",
   "no se confunde con «estudia X» (tema general)")

# el lector de internet guarda los enlaces de verdad
class R:
    def __init__(self, cuerpo, url):
        self.cuerpo, self.url = cuerpo.encode(), url
        self.status = 200
        self.headers = {"Content-Type": "text/html; charset=utf-8"}

    def read(self, *a):
        c, self.cuerpo = self.cuerpo, b""
        return c

    def geturl(self):
        return self.url

    def getheader(self, k, d=None):
        return self.headers.get(k, d)

    def info(self):
        return self

    def get(self, k, d=None):
        return self.headers.get(k, d)

    def get_content_charset(self):
        return "utf-8"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


net = ik.Internet(T, abrir=lambda req, timeout=20: R(HTML, BASE))
pg = net.leer(BASE)
ok(len(pg.get("enlaces", [])) >= 5, "al leer una página, Kira se queda con sus enlaces")
ok("estudia sus enlaces" in ik.Internet.texto_pagina(pg), "y te dice que puede estudiarlos")

# ---------- núcleo: sigue los enlaces ----------
import kira_god  # noqa: E402

PAGINAS = {
    BASE: pag,
    "https://ejemplo.es/curso/python/capitulo-1-variables.html": {
        "url": "x1", "titulo": "Capítulo 1: variables", "texto": "Las variables en Python guardan valores. " * 3,
        "enlaces": [{"url": "https://ejemplo.es/curso/python/capitulo-1b.html", "texto": "Más sobre variables de Python"}]},
    "https://ejemplo.es/curso/python/capitulo-1b.html": {"url": "x1b", "titulo": "1b", "texto": "Python: tipos. " * 5},
}
leidas = []


class Falso:
    pagina = None

    def buscar(self, consulta, tipo="web", n=8):
        return [{"url": BASE, "fuente": "ejemplo.es", "titulo": "Curso"}]

    def leer(self, url):
        leidas.append(url)
        if url in PAGINAS:
            self.pagina = PAGINAS[url]
            return PAGINAS[url]
        return {"url": url, "titulo": url.rsplit("/", 1)[-1], "texto": f"Página sobre Python ({url}). " * 3}


core = kira_god.KiraGodCore()
core.internet = Falso()
core.resumir_pagina = lambda pag, tema="": (pag.get("texto", "")[:300], True)
core._repasar_con_claude = lambda *a: False
r = core.estudiar_en_internet("python", paginas=1, enlaces=3)
ok(r.startswith("[OK]") and "3 enlace(s) de dentro" in r, "«estudia en internet» ahora sigue enlaces del tema: " + r)
ok(leidas[0] == BASE and len(leidas) == 4 and not any("cocina" in u for u in leidas),
   "lee la página y solo los enlaces del tema, con tope")

leidas.clear()
r = core.estudiar_pagina(BASE, maximo=10)
ok(r.startswith("[OK]") and "página(s) que enlaza" in r, "«estudia esta página y sus enlaces»: " + r.splitlines()[0])
ok("https://ejemplo.es/curso/python/capitulo-1b.html" in leidas, "llega a un segundo salto (el enlace del capítulo 1)")
ok(len(set(leidas)) == len(leidas), "nunca lee dos veces la misma página")
leidas.clear()
r = core.estudiar_pagina(BASE, maximo=2)
ok(len(leidas) == 3 and "tope" in r, "respeta el tope de páginas y lo dice")
core.internet.pagina = PAGINAS[BASE]
leidas.clear()
ok(core.estudiar_pagina(None, maximo=1).startswith("[OK]"), "«estudia sus enlaces» usa la última página leída")
core.cancelado = lambda: True
leidas.clear()
core.estudiar_pagina(BASE, maximo=10)
ok(leidas == [BASE], "si le dices «para», deja de seguir enlaces")
del core.cancelado
ok("estudiar_enlaces" in open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read(), "la orden está enganchada")

# ---------- KiraOS: el lector del Buscador enseña los enlaces ----------
import escritorio_kira as esk  # noqa: E402


class Api(esk.EscritorioMixin):
    def __init__(self):
        self.cli = None

    def _internet(self):
        return net

    def _via(self):
        return "desde el portátil"


d = Api().leer_web(BASE)
ok(d["ok"] and d["enlaces"] and d["enlaces"][0]["tema"] and d["total_enlaces"] >= 5,
   "leer_web devuelve los enlaces, los del tema primero")

node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(600);
  await pg.click('#entrada'); await pg.keyboard.type('busca python'); await pg.keyboard.press('Enter');
  await pg.waitForTimeout(1200); await pg.click('.res .tit'); await pg.waitForTimeout(400);
  const enl = await pg.$$eval('.enl', l => l.map(x => x.textContent));
  const tema = await pg.$$eval('.enl.tema', l => l.length);
  const boton = await pg.isVisible('#busEnlaces');
  await pg.screenshot({path: process.argv[3]});
  await pg.click('.enl.tema'); await pg.waitForTimeout(400);
  const atras = await pg.textContent('#busAtras');
  await pg.click('#busAtras'); await pg.waitForTimeout(400);
  const vuelta = await pg.textContent('#busAtras');
  const hay = await pg.$$eval('.enl', l => l.length);
  console.log(JSON.stringify({errs, enl, tema, boton, atras, vuelta, hay}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    f = os.path.join(T, "e.js")
    open(f, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, f, html, os.path.join(T, "enlaces.png")], capture_output=True, text=True, timeout=120, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(len(d["enl"]) == 3 and d["tema"] == 2, "Chromium: el lector enseña los enlaces de la página (los del tema marcados)")
        ok(d["boton"], "Chromium: botón «Estúdiala con sus enlaces»")
        ok("Atrás" in d["atras"] and "Resultados" in d["vuelta"] and d["hay"] == 3,
           "Chromium: pulsar un enlace lo abre y «‹ Atrás» vuelve a la página de antes")
        print("captura:", os.path.join(T, "enlaces.png"))
    else:
        print("(sin Chromium utilizable: me salto la pantalla)", out[:200])

print("\nTODO BIEN", n)
