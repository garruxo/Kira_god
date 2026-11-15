# -*- coding: utf-8 -*-
"""v3.79 (KiraOS):
  1) «instala X de github» solo con el nombre → busca en GitHub, enseña los proyectos y TÚ eliges (nunca el primero);
  2) en el Buscador: «Abrir en el navegador» (el de verdad) y la lista de DESCARGAS de la página para elegir tú;
  3) «instala lo que he descargado» → el último programa de tu carpeta Descargas.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATOS_NUCLEO"] = os.path.join(T, "kira_datos")
os.environ["KIRA_GITHUB_BUSCA"] = os.path.join(T, "gb.json")
os.makedirs(os.environ["KIRA_DATOS_NUCLEO"], exist_ok=True)
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import github_buscar_kira as gb
import apps_externas_kira as aex
import internet_kira as ik

n = fallos = 0


def ok(c, m):
    global n, fallos
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ---------------- la orden ----------------
E = gb.es_orden
ok(E("instala obsidian de github") == "obsidian", "«instala X de github»")
ok(E("Kira, descárgame el programa krita desde github") == "krita", "«descárgame el programa X desde github»")
ok(E("instala desde github yt-dlp") == "yt-dlp", "«instala desde github X»")
ok(E("busca lazygit en github y instálalo") == "lazygit", "«busca X en github y instálalo»")
ok(E("instala https://github.com/a/b de github") is None and E("instala dueno/proyecto de github") is None,
   "un enlace o «dueño/proyecto» van directos (como antes)")
ok(E("instala vlc") is None and E("busca obsidian en github") is None, "lo demás no (buscar solo = el Buscador)")

# ---------------- buscar ----------------
pedidas = []


def api(url):
    pedidas.append(url)
    return {"items": [
        {"full_name": "otro/obsidian-tema", "name": "obsidian-tema", "stargazers_count": 90000, "description": "un tema",
         "language": "CSS", "pushed_at": "2025-01-01T00:00:00Z", "html_url": "https://github.com/otro/obsidian-tema"},
        {"full_name": "obsidianmd/obsidian-releases", "name": "obsidian-releases", "stargazers_count": 12000,
         "description": "Obsidian", "pushed_at": "2026-10-01T00:00:00Z"},
        {"full_name": "viejo/obsidian", "name": "obsidian", "stargazers_count": 50, "archived": True},
        {"full_name": "copia/obsidian", "name": "obsidian", "stargazers_count": 999999, "fork": True},
        {"full_name": "bueno/obsidian", "name": "Obsidian", "stargazers_count": 3000, "description": "El de verdad"},
    ]}


ops = gb.buscar("obsidian", traer_json=api)
ok("search/repositories" in pedidas[0] and "sort=stars" in pedidas[0], "pregunta a la API de búsqueda de GitHub")
ok(ops[0]["repo"] == "bueno/obsidian", "el que se llama EXACTAMENTE así va primero")
ok(ops[-1]["repo"] == "viejo/obsidian" and ops[-1]["archivado"], "los abandonados al final")
ok(not any(o["repo"] == "copia/obsidian" for o in ops), "las copias (forks) fuera")
t = gb.texto_opciones("obsidian", ops)
ok("1. bueno/obsidian" in t and "★ 90 mil" in t and "ABANDONADO" in t and "«el 1»" in t, "te los enseña y pregunta")
ok("Buscador" in gb.texto_no_encontrado("xyz") and "instala lo que he descargado" in gb.texto_no_encontrado("xyz"),
   "si no lo encuentra, te dice cómo buscarlo y descargarlo tú")
ok(gb.eleccion("el 2", ops) == 1 and gb.eleccion("la tercera", ops) == 2 and gb.eleccion("ninguno", ops) == "cancelar",
   "entiende «el 2», «la tercera», «ninguno»")
ok(gb.eleccion("el 9", ops) is None and gb.eleccion("hola", ops) is None, "lo que no es respuesta, no")
ok(gb.eleccion("bueno/obsidian", ops) == 0, "también por su nombre")

# ---------------- el núcleo ----------------
import nucleo_portatil as npo


class Core:
    dir = os.environ["KIRA_DATOS_NUCLEO"]


r = npo._buscar_github("obsidian", lambda *a: None, traer_json=api)
ok("¿Cuál quieres?" in r["texto"] and gb.pendiente(), "el núcleo pregunta y se queda esperando la respuesta")
instaladas = []
_inst = npo._instalar_app
npo._instalar_app = lambda core, f, paso, **k: (instaladas.append((f, k.get("nombre"))) or {"texto": "Instalada."})
try:
    r = npo.ejecutar(Core(), "el 1", lambda *a: None)
    ok(instaladas == [("https://github.com/bueno/obsidian", "obsidian")] and "Has elegido bueno/obsidian" in r["texto"],
       "«el 1» → instala ESE proyecto (por el camino de siempre: versiones, análisis, icono)")
    ok(gb.pendiente() is None, "y ya no queda nada esperando")
    npo._buscar_github("obsidian", lambda *a: None, traer_json=api)
    instaladas.clear()
    r = npo.ejecutar(Core(), "ninguno", lambda *a: None)
    ok(not instaladas and "no instalo" in r["texto"], "«ninguno» → no instala nada")
    r = npo._buscar_github("nada", lambda *a: None, traer_json=lambda u: {"items": []})
    ok("No he encontrado" in r["texto"], "sin resultados lo dice")
    r = npo._buscar_github("nada", lambda *a: None, traer_json=lambda u: (_ for _ in ()).throw(OSError("límite")))
    ok("no me ha contestado" in r["texto"], "si GitHub no contesta, lo dice (y cómo hacerlo tú)")

    # ---------------- lo que descargaste tú ----------------
    ok(gb.es_orden_descargado("instala lo que he descargado") and gb.es_orden_descargado("instala lo último que descargué")
       and gb.es_orden_descargado("instala el archivo que bajé") and gb.es_orden_descargado("instala lo de descargas"),
       "«instala lo que he descargado»")
    ok(not gb.es_orden_descargado("instala vlc"), "lo demás no")
    desc = os.path.join(T, "Descargas")
    os.makedirs(desc)
    viejo = os.path.join(desc, "viejo.deb")
    open(viejo, "wb").write(b"x")
    os.utime(viejo, (time.time() - 100, time.time() - 100))
    open(os.path.join(desc, "Programa-1.0-x86_64.AppImage"), "wb").write(b"\x7fELF")
    open(os.path.join(desc, "foto.jpg"), "wb").write(b"x")
    open(os.path.join(desc, "otro.zip.part"), "wb").write(b"x")
    ok(gb.ultimo_descargado().endswith("Programa-1.0-x86_64.AppImage"),
       "el último PROGRAMA de Descargas (ni fotos ni lo que aún se baja)")
    instaladas.clear()
    r = npo.ejecutar(Core(), "instala lo que he descargado", lambda *a: None)
    ok(instaladas and instaladas[0][0].endswith(".AppImage") and "lo descargaste" not in r["texto"]
       and "El último que descargaste" in r["texto"], "el núcleo lo instala")
finally:
    npo._instalar_app = _inst

# un archivo local se instala DE VERDAD (copiándolo, sin internet)
ok(aex.metodo(os.path.join(desc, "Programa-1.0-x86_64.AppImage")) == "appimage" and aex.metodo(viejo) == "descarga",
   "un archivo de tu portátil se instala como una descarga")
r = aex.instalar(os.path.join(desc, "Programa-1.0-x86_64.AppImage"), base=os.path.join(T, "apps"))
ok(r["ok"] and os.path.isfile(r["lanzar"][0]) and os.access(r["lanzar"][0], os.X_OK),
   "instalar un AppImage que bajaste tú: se copia y se puede abrir")
exe = os.path.join(desc, "Juego-setup.exe")
open(exe, "wb").write(b"MZ")
r = npo._instalar_app(Core(), exe, lambda *a: None, sin_versiones=True)
ok("Windows" in r["texto"] and "[x]" not in r["texto"], "si lo que bajaste es de Windows, lo dice y busca la de Linux")

# ---------------- el navegador ----------------
html = ('<html><body><main><h1>Prog</h1><p>Descarga el programa para tu sistema.</p>'
        '<a href="/d/Prog-2.0-x86_64.AppImage">Linux</a> <a href="/d/Prog-2.0.exe">Windows</a>'
        '<a href="https://otra.org/Prog.dmg">Mac</a><a href="/doc">Documentación</a></main></body></html>')
partes = ik._html_partes(html)
d = ik.descargas_de(partes.enlaces, "https://prog.org/")
ok([x["archivo"] for x in d] == ["Prog-2.0-x86_64.AppImage", "Prog-2.0.exe", "Prog.dmg"],
   "el lector saca las DESCARGAS de la página (y no las páginas normales)")

import escritorio_kira as ek

esc = ek.EscritorioMixin()


class Internet:
    def leer(self, url):
        return {"url": url, "titulo": "Prog", "texto": "Descarga el programa.", "codigos": [], "tipo": "web",
                "enlaces": [], "descargas": d}


esc._internet = lambda: Internet()
esc._via = lambda: "desde mi máquina"
p = esc.leer_web("https://prog.org/")
ok([x["sistema"] for x in p["descargas"]] == ["Linux", "Windows", "Mac"], "leer_web dice de qué sistema es cada descarga")
lanzados = []
r = esc.abrir_navegador("https://prog.org/", popen=lambda a, **k: lanzados.append(a),
                        which=lambda c: "/usr/bin/" + c if c == "firefox" else None)
ok(r["ok"] and lanzados == [["/usr/bin/firefox", "https://prog.org/"]] and "Descargas" in r["texto"],
   "«Abrir en el navegador»: el navegador de verdad, y te dice dónde va lo que descargues")
ok(not esc.abrir_navegador("file:///etc/passwd")["ok"] and not esc.abrir_navegador("javascript:alert(1)")["ok"],
   "solo abre páginas web (http/https)")
ok(not esc.abrir_navegador("https://a.org", which=lambda c: None)["ok"], "sin navegador lo dice")

# ---------------- la pantalla (Chromium) ----------------
node = shutil.which("node")
htmlf = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(300);
  await pg.evaluate(() => { FAKE._descargas=[{url:"https://p.org/P.AppImage",archivo:"P.AppImage",sistema:"Linux"},
                                             {url:"https://p.org/P.exe",archivo:"P.exe",sistema:"Windows"}];
    window._inst=[]; var f=FAKE.instalar_web; FAKE.instalar_web=function(u){ window._inst.push(u); return Promise.resolve("Instalada."); }; });
  await pg.evaluate(() => { abrir("buscador"); }); await pg.waitForTimeout(300);
  await pg.evaluate(() => { leerUrl("https://p.org/", "p.org"); }); await pg.waitForTimeout(400);
  const descargas = await pg.$$eval('.descargas .desc', bs => bs.map(b => b.textContent));
  const nav = await pg.$('#busNavegador') ? true : false;
  await pg.click('#busNavegador'); await pg.waitForTimeout(200);
  const navegador = await pg.evaluate(() => FAKE._navegador);
  await pg.click('.descargas .desc[data-d="0"]'); await pg.waitForTimeout(300);
  const inst = await pg.evaluate(() => window._inst);
  const msg = await pg.$eval('#busInstResult', e => e.textContent);
  console.log(JSON.stringify({errs, descargas, nav, navegador, inst, msg}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    fjs = os.path.join(T, "a.js")
    open(fjs, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, fjs, htmlf], capture_output=True, text=True, timeout=180, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d2 = json.loads(out)
        ok(not d2["errs"], "Chromium: sin errores " + str(d2["errs"]))
        ok(len(d2["descargas"]) == 2 and "Windows" in d2["descargas"][1], "Chromium: el lector enseña sus descargas")
        ok(d2["nav"] and d2["navegador"] == "https://p.org/", "Chromium: «Abrir en el navegador» abre ESA página")
        ok(d2["inst"] == ["https://p.org/P.AppImage"] and "Instalada" in d2["msg"],
           "Chromium: pulsar una descarga la instala")
    else:
        print("  (sin Chromium)", r.stdout[-500:], r.stderr[-300:])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
