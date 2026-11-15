# -*- coding: utf-8 -*-
"""v3.78 (KiraOS):
  1) al INSTALAR un programa, Kira prepara sus ÓRDENES antes de abrirlo, y al pulsar su icono sale su ventanita con
     todas las órdenes (pulsables); con clic derecho ▸ Órdenes, la ventanita sin abrir la app;
  2) si lo que hay para descargar es de OTRO sistema (.exe, .dmg…) o la página no tiene el archivo, busca la versión
     para Linux: en la página, en su GitHub, en su página de descargas y, si no, en apt y Flathub (y lo dice claro).
"""
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATOS_NUCLEO"] = os.path.join(T, "kira_datos")
os.makedirs(os.environ["KIRA_DATOS_NUCLEO"], exist_ok=True)
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import buscar_linux_kira as bl
import apps_externas_kira as aex
import manejo_apps_kira as ma

n = fallos = 0


def ok(c, m):
    global n, fallos
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ======================================================================= 2) BUSCAR LA VERSIÓN PARA LINUX
P = bl.plataforma
ok(P("https://x.org/d/VLC-3.0-win64.exe") == "windows" and P("https://x.org/a.msi") == "windows", ".exe / .msi = Windows")
ok(P("https://x.org/App-1.2.dmg") == "mac" and P("https://x.org/app.apk") == "android", ".dmg = Mac, .apk = Android")
ok(P("https://x.org/App-1.2-x86_64.AppImage") == "linux" and P("https://x.org/app_1.0_amd64.deb") == "linux",
   "AppImage / .deb = Linux")
ok(P("https://x.org/descargas") == "", "una página no es un archivo")
ok(bl.texto_plataformas(bl.plataformas(["https://a/x.exe", "https://a/y.dmg"])) == "Windows (.exe) y Mac (.dmg)",
   "dice qué sistemas hay")
ok(bl.nombre_de("https://x.org/d/VLC-3.0.20-win64.exe") == "vlc", "el nombre sale del archivo, sin versión ni sistema")
ok(bl.nombre_de("https://editor.org/", "<title>Kritix - Descargar</title>") == "Kritix", "o del título de la página")

PAGINAS = {
    "https://prog.org/": '<title>Prog</title><a href="/files/Prog-2.0-setup.exe">Windows</a>'
                         '<a href="/files/Prog-2.0.dmg">Mac</a><a href="/descargas/todas">Todas las descargas</a>',
    "https://prog.org/descargas/todas": '<a href="https://cdn.prog.org/Prog-2.0-x86_64.AppImage">Linux</a>',
    "https://solo.org/": '<title>Solo</title><a href="/Solo-1.0-win64.exe">Bajar</a>',
    "https://gh.org/": '<a href="/Gh.exe">win</a> código en <a href="https://github.com/dueno/gh">GitHub</a>',
}


def traer(u):
    if u not in PAGINAS:
        raise OSError("404")
    return PAGINAS[u]


def de_github(url):
    return [{"version": "1.0", "url": url + "/releases/download/v1/gh.AppImage"}] if "dueno/gh" in url else []


b = bl.buscar("https://prog.org/", traer=traer, de_github=de_github, which=lambda c: None)
ok(b["ok"] and b["como"] == "subpagina" and b["fuente"].endswith(".AppImage"),
   "la página solo tenía .exe y .dmg: la encuentra en su página de descargas")
b = bl.buscar("https://gh.org/", traer=traer, de_github=de_github, which=lambda c: None)
ok(b["ok"] and b["como"] == "github" and b["fuente"] == "https://github.com/dueno/gh", "o en el GitHub que enlaza")
b = bl.buscar("https://github.com/dueno/gh/releases/download/v1/gh-setup.exe", traer=traer, de_github=de_github,
              which=lambda c: None)
ok(b["ok"] and b["como"] == "github", "un .exe de las versiones de un GitHub → las versiones de ese GitHub")


def correr_sis(args, timeout=30):
    if args[:2] == ["apt-cache", "policy"]:
        return (0, "solo:\n  Instalados: (ninguno)\n  Candidato: 1.0-1\n") if args[2] == "solo" else (0, "")
    if args[:2] == ["flatpak", "search"]:
        return 0, "org.solo.Solo\tSolo\ncom.otra.Cosa\tCosa\n"
    return 1, ""


b = bl.buscar("https://solo.org/", traer=traer, de_github=de_github, correr=correr_sis, which=lambda c: "/usr/bin/" + c)
ok(not b["ok"] and "Windows" in b["texto"] and b["apt"] == "solo" and b["flatpak"] == "org.solo.Solo",
   "solo hay para Windows: lo dice y la encuentra en apt y Flathub")
ok("«instala solo»" in b["texto"] and "«instala flatpak org.solo.Solo»" in b["texto"],
   "y te da la orden exacta (no la instala de otra fuente sin preguntarte)")
b = bl.buscar("https://solo.org/", traer=traer, de_github=de_github, correr=lambda a, timeout=0: (1, ""),
              which=lambda c: "/usr/bin/" + c)
ok(not b["ok"] and "Wine" in b["texto"] and "Tampoco" in b["texto"], "si no está en ningún sitio, lo dice (y lo de Wine)")
b = bl.buscar("https://noexiste.org/x.exe", traer=traer, de_github=de_github, correr=correr_sis,
              which=lambda c: None)
ok(not b["ok"] and "Windows" in b["texto"], "un .exe suelto sin página: dice que es de Windows")

# ---------- Flathub ----------
ok(bl.es_flatpak("flatpak org.videolan.VLC") == "org.videolan.VLC" and bl.es_flatpak("flatpak:org.a.B") == "org.a.B",
   "«flatpak org.x.App» se reconoce")
ok(bl.es_flatpak("vlc") is None and bl.es_flatpak("flatpak vlc") is None, "lo demás no")
ok(aex.es_orden_instalar("instala flatpak org.videolan.VLC") == "flatpak org.videolan.VLC", "«instala flatpak …» llega")
hechas = []


def correr_fp(args, timeout=0, **k):
    hechas.append(args)
    return 0, "ok"


r = bl.instalar_flatpak("org.videolan.VLC", correr=correr_fp, which=lambda c: "/usr/bin/flatpak")
ok(r["ok"] and r["lanzar"] == ["flatpak", "run", "org.videolan.VLC"], "instala de Flathub y sabe abrirla")
ok(any("--user" in a and "install" in a for a in hechas) and not any("sudo" in a for a in hechas),
   "para tu usuario, sin administrador")
r = bl.instalar_flatpak("org.videolan.VLC", correr=correr_fp, which=lambda c: None)
ok(not r["ok"] and "sudo apt install flatpak" in r["mensaje"], "sin Flatpak: dice cómo ponerlo")
_w = bl.shutil.which
bl.shutil.which = lambda c: "/usr/bin/flatpak" if c == "flatpak" else _w(c)
try:
    r = aex.instalar("flatpak org.videolan.VLC", correr=correr_fp)
finally:
    bl.shutil.which = _w
ok(r["ok"] and r["lanzar"][0] == "flatpak", "apps_externas_kira.instalar entiende «flatpak …»")

# ---------- el núcleo ----------
import nucleo_portatil as npo

llamadas = []
_bus, _inst = bl.buscar, aex.instalar


class Core:
    dir = os.environ["KIRA_DATOS_NUCLEO"]


aex.instalar = lambda f, **k: (llamadas.append(f) or {"ok": True, "nombre": "Prog", "lanzar": ["true"], "carpeta": ""})
bl.buscar = lambda f, **k: {"ok": True, "fuente": "https://cdn.prog.org/Prog-2.0-x86_64.AppImage", "como": "subpagina",
                            "texto": "La encontré en su página de descargas."}
try:
    r = npo._instalar_app(Core(), "https://prog.org/files/Prog-2.0-setup.exe", lambda *a: None, sin_versiones=True)
    ok(llamadas == ["https://cdn.prog.org/Prog-2.0-x86_64.AppImage"] and "página de descargas" in r["texto"],
       "el núcleo: con un .exe busca la de Linux y la instala")
    bl.buscar = lambda f, **k: {"ok": False, "texto": "No hay versión para Linux: lo que encontré es para Windows."}
    llamadas.clear()
    r = npo._instalar_app(Core(), "https://solo.org/Solo.exe", lambda *a: None, sin_versiones=True)
    ok(not llamadas and "Windows" in r["texto"] and "[x]" not in r["texto"], "y si no la hay, lo explica (sin «error»)")
finally:
    bl.buscar, aex.instalar = _bus, _inst

# ======================================================================= 1) LAS ÓRDENES DEL PROGRAMA
herr = os.path.join(T, "herr.py")
open(herr, "w").write('import sys\nif "--help" in sys.argv:\n    print("Uso: herr [opciones]\\n\\nOptions:\\n'
                      '  --version      Muestra la version\\n  --rapido       Va muy rapido\\n")\n')
app = {"titulo": "Herr", "lanzar": [sys.executable, herr], "carpeta": T}
m = ma.Manejo(accesos=[])
nprep = ma.preparar_ordenes(m, app)
ok(nprep == 2, f"al instalar le pregunta qué sabe hacer: {nprep} herramientas")
lo = ma.lista_ordenes(m, app)
ok([o["texto"] for o in lo[:4]] == ["Abrir", "Cerrar", "Reiniciar", "¿Está abierta?"], "lo básico: abrir, cerrar…")
ok(any(o["orden"] == "en Herr, --version" and "version" in o["desc"] for o in lo), "y sus herramientas, con su orden")
ok(ma.preparar_ordenes(m, {"titulo": "Inst", "lanzar": ["bash", "/tmp/instalador.sh"]}) == 0,
   "a un instalador .sh NO le pregunta (lo ejecutaría)")
ok("2 herramienta" in ma.texto_preparadas(2, "Herr") and "ventanita" in ma.texto_preparadas(0, "X"),
   "lo dice al instalar")

import accesos_kira as ak
import escritorio_kira as ek

DN = os.environ["KIRA_DATOS_NUCLEO"]
iid, _nueva = ak.poner_externa(DN, "Herr", [sys.executable, herr], T)
esc = ek.EscritorioMixin()
abiertos = []
_abrir = ma.Manejo.abrir
ma.Manejo.abrir = lambda self, a, archivo="": (abiertos.append(a["titulo"]) or {"ok": True, "texto": "Abriendo Herr…"})
import arreglar_app_kira as _arr   # v3.81: abierta VIGILADA
_arr.abrir_vigilando = lambda a, d, **k: (abiertos.append(a["titulo"]) or {"ok": True, "texto": "Abriendo Herr…"})
try:
    d = esc.abrir_acceso(iid)
    ok(d["externa"] and abiertos == ["Herr"] and any(o["orden"] == "en Herr, --rapido" for o in d["ordenes"]),
       "al pulsar su icono: la abre Y trae su ventanita de órdenes")
    abiertos.clear()
    d = esc.abrir_acceso(iid, False)
    ok(not abiertos and len(d["ordenes"]) >= 6, "clic derecho ▸ Órdenes: la ventanita sin abrir la app")
finally:
    ma.Manejo.abrir = _abrir

# instalar_web: página sin Linux → la busca, instala y prepara sus órdenes
_tt, _inst = aex._traer_texto, aex.instalar
aex._traer_texto = lambda u, traer=None: traer_web(u)


def traer_web(u):
    return {"https://prog.org/": PAGINAS["https://prog.org/"],
            "https://prog.org/descargas/todas": PAGINAS["https://prog.org/descargas/todas"]}[u]


aex.instalar = lambda f, **k: {"ok": True, "nombre": "Prog", "lanzar": [sys.executable, herr], "carpeta": T,
                               "mensaje": "Prog descargada."}
try:
    txt = esc.instalar_web(url="https://prog.org/", sin_versiones=True)
finally:
    aex._traer_texto, aex.instalar = _tt, _inst
ok("página de descargas" in txt and "Prog descargada" in txt and "He preparado sus órdenes" in txt,
   "Buscador: la página solo tenía .exe/.dmg → la encuentra, la instala y prepara sus órdenes")
ok(any(a["titulo"] == "Prog" for a in ak.listar(DN)), "y deja su icono")

# ---------- la pantalla (Chromium) ----------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(300);
  await pg.evaluate(() => { FAKE._accesos=[{id:"vlc",titulo:"VLC",icono:"programa",tipo:"externa"}]; refrescaBarra();
    window._dicho=[]; var h=FAKE.hablar; FAKE.hablar=function(t){ window._dicho.push(t); return h(t); }; });
  await pg.waitForTimeout(400);
  await pg.click('.icono[data-app="acceso:vlc"]'); await pg.waitForTimeout(400);
  const botones = await pg.$$eval('#vcuerpo .ordbtn', bs => bs.map(b => b.textContent));
  const tit = await pg.$eval('#vcuerpo .ordtit', e => e.textContent).catch(()=>'');
  await pg.click('#vcuerpo .ordbtn[data-o="2"]'); await pg.waitForTimeout(300);
  const dicho = await pg.evaluate(() => window._dicho);
  console.log(JSON.stringify({errs, botones, tit, dicho}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    fjs = os.path.join(T, "a.js")
    open(fjs, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, fjs, html], capture_output=True, text=True, timeout=180, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        import json as _j
        d = _j.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(len(d["botones"]) == 3 and "Órdenes de VLC" in d["tit"], "Chromium: al abrir la app sale su ventanita de órdenes")
        ok(d["dicho"] == ["en VLC, --version"], "Chromium: pulsar una orden se la dice a Kira")
    else:
        print("  (sin Chromium)", r.stdout[-500:], r.stderr[-300:])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
