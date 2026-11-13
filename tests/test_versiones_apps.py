# -*- coding: utf-8 -*-
"""v3.35: (1) cuando hay VARIAS VERSIONES para descargar, Kira las enseña y pregunta cuál; (2) Kira MANEJA las apps
instaladas (abrir, cerrar, ¿está abierta?, herramientas y las órdenes para manejarlas)."""
import os
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATA_DIR"] = T
os.environ["KIRA_VERSIONES"] = os.path.join(T, "versiones.json")
os.environ["KIRA_APPS_PROCESOS"] = os.path.join(T, "procesos.json")
os.environ["KIRA_APPS_HERR"] = os.path.join(T, "herr.json")
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import versiones_kira as vk       # noqa: E402
import manejo_apps_kira as ma     # noqa: E402

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ======================= VERSIONES =======================
V = vk.version_de
ok(V("https://github.com/x/krita/releases/download/v5.2.3/krita-5.2.3-x86_64.AppImage") == "5.2.3", "versión del archivo")
ok(V("https://d.org/app_2.0.1-beta2_amd64.deb") == "2.0.1-beta2", "versión de prueba (beta)")
ok(V("https://d.org/downloads/1.4.10/App-linux-x64.tar.gz") == "1.4.10", "versión de la carpeta")
ok(V("https://x.org/app-latest.AppImage") == "", "sin número → ''")
ok(V("https://x.org/qt5-app-3.1.AppImage") == "3.1" and V("x86_64-tool-1.2.zip") == "1.2", "no confunde qt5/x86_64")
ok(vk.clave_version("2.0") > vk.clave_version("2.0-rc1") > vk.clave_version("1.9.9"), "orden: estable > rc > vieja")

URLS = ["https://d.org/App-2.1.0-x86_64.AppImage", "https://d.org/app_2.1.0_amd64.deb", "https://d.org/App-2.1.0.exe",
        "https://d.org/App-2.2.0-rc1-x86_64.AppImage", "https://d.org/App-2.0.5-x86_64.AppImage",
        "https://d.org/App-2.0.5-arm64.AppImage", "https://d.org/App-1.9.exe"]
ops = vk.opciones_de_urls(URLS)
ok([o["version"] for o in ops] == ["2.2.0-rc1", "2.1.0", "2.0.5"], "agrupa por versión, de la más nueva a la vieja")
ok(all(o["url"].endswith(".AppImage") and "arm64" not in o["url"] for o in ops), "de cada una, el AppImage de 64 bits")
ok(ops[1]["otras"][0]["forma"] == ".deb", "y apunta las otras formas (.deb)")
ok(not ops[0]["estable"] and ops[1]["estable"], "marca la de prueba")
ok(len(vk.opciones_de_urls(["https://d.org/App-1.9.exe"])) == 0, "solo Windows → ninguna")
txt = vk.texto_opciones("App", ops)
ok("3 versiones de App" in txt and "1) 2.2.0-rc1" in txt and "de prueba" in txt and "la estable más nueva" in txt and
   "instala la 1" in txt, "la pregunta para el dueño")
E = vk.eleccion
ok(E("instala la 2", ops)["version"] == "2.1.0" and E("2", ops)["version"] == "2.1.0" and
   E("quiero la 3", ops)["version"] == "2.0.5", "«instala la 2» / «2» / «quiero la 3»")
ok(E("la versión 2.0.5", ops)["version"] == "2.0.5" and E("la segunda", ops)["version"] == "2.1.0", "por número o ordinal")
ok(E("la más nueva", ops)["version"] == "2.2.0-rc1" and E("la estable", ops)["version"] == "2.1.0", "la nueva / la estable")
ok(E("la 2 en .deb", ops)["url"].endswith(".deb"), "«la 2 en .deb» cambia la forma")
ok(E("ninguna", ops) == "cancelar" and E("clónalo", ops) == "clonar", "ninguna / clónalo")
ok(not vk.es_respuesta("qué tal estás", ops) and not vk.es_respuesta("instala firefox", ops) and
   vk.es_respuesta("instala la 2", ops), "solo las respuestas de elegir")
v1410 = vk.opciones_de_urls(["https://d.org/A-1.4.1-x86_64.AppImage", "https://d.org/A-1.4.10-x86_64.AppImage"])
ok(E("la 1.4.1", v1410)["version"] == "1.4.1" and E("la 1.4.10", v1410)["version"] == "1.4.10", "1.4.1 ≠ 1.4.10")

REL = [{"tag_name": "v3.0.0-beta", "prerelease": True, "published_at": "2026-10-01T00:00:00Z",
        "assets": [{"browser_download_url": "https://github.com/o/r/releases/download/v3.0.0-beta/R-3.0.0-beta-x86_64.AppImage"}]},
       {"tag_name": "v2.5.1", "prerelease": False, "published_at": "2026-09-01T00:00:00Z",
        "assets": [{"browser_download_url": "https://github.com/o/r/releases/download/v2.5.1/R-2.5.1-x86_64.AppImage"},
                   {"browser_download_url": "https://github.com/o/r/releases/download/v2.5.1/r_2.5.1_amd64.deb"},
                   {"browser_download_url": "https://github.com/o/r/releases/download/v2.5.1/R-2.5.1-win64.exe"}]},
       {"tag_name": "v2.0", "draft": True, "assets": []},
       {"tag_name": "v1.0", "assets": [{"browser_download_url": "https://github.com/o/r/releases/download/v1.0/R-1.0.exe"}]}]
gh = vk.de_github("https://github.com/o/r", traer_json=lambda u: REL)
ok([o["version"] for o in gh] == ["3.0.0-beta", "2.5.1"] and not gh[0]["estable"] and gh[1]["fecha"] == "2026-09-01",
   "versiones de GitHub (sin borradores ni las solo-Windows)")
ok(vk.de_github("o/r", traer_json=lambda u: (_ for _ in ()).throw(OSError("sin red"))) == [], "sin internet → []")
ok(vk.repo_github("https://github.com/o/r.git") == "o/r" and vk.repo_github("o/r") == "o/r" and
   vk.repo_github("https://d.org/x") is None, "usuario/repo")
vk.guardar_pendiente("App", "https://d.org/descargas", ops)
ok(vk.pendiente()["nombre"] == "App" and oct(os.stat(os.environ["KIRA_VERSIONES"]).st_mode & 0o777) == "0o600",
   "la pregunta queda apuntada (0600)")
ok(vk.pendiente(dura_min=0) is None, "caduca")
ok(vk.nombre_bonito("App 2.1.0 x86 64", "2.1.0") == "App", "nombre del icono sin la versión")

# ---- en el núcleo de KiraOS (instalar de mentira) ----
import nucleo_portatil as np_     # noqa: E402
import apps_externas_kira as aex  # noqa: E402

PAGINA = "".join(f'<a href="{u}">x</a>' for u in URLS)
aex._traer_texto = lambda url, traer=None: PAGINA
vistos = []


def instalar_falso(fuente, al_paso=None, forzar=False, nombre=None, **kw):
    vistos.append((fuente, nombre))
    return {"ok": True, "nombre": nombre or aex._nombre_de(fuente), "lanzar": ["/bin/true"], "carpeta": T,
            "mensaje": f"{nombre} instalada."}


aex.instalar = instalar_falso


class Core:
    dir = os.path.join(T, "core")
    _app_bloqueada = ""

    def procesar_orden(self, o):
        return "charla: " + o


os.makedirs(Core.dir, exist_ok=True)
vk.borrar_pendiente()
paso = lambda fr, t: None
r = np_.ejecutar(Core(), "instala https://d.org/descargas", paso)
ok("3 versiones" in r["texto"] and not vistos, "«instala <página>» con varias versiones → PREGUNTA, no baja nada")
r = np_.ejecutar(Core(), "la 2 en .deb", paso)
ok(vistos and vistos[-1][0].endswith("app_2.1.0_amd64.deb") and vistos[-1][1] == "App" and
   r["texto"].startswith("Versión 2.1.0 (.deb)") and "órdenes de App" in r["texto"],
   "la respuesta instala ESA versión y dice cómo manejarla")
ok(vk.pendiente() is None, "y borra la pregunta")
r = np_.ejecutar(Core(), "la 2", paso)
ok("Versión" not in r.get("texto", ""), "sin pregunta pendiente, «la 2» no instala nada")
vk.guardar_pendiente("App", "https://d.org/descargas", ops)
r = np_.ejecutar(Core(), "ninguna", paso)
ok("no descargo" in r["texto"], "«ninguna» = no baja nada")
import accesos_kira as ak         # noqa: E402
ak.anadir_externa(Core.dir, "Zeta", ["/viejo"], T)
iid, nueva = ak.poner_externa(Core.dir, "Zeta", ["/nuevo"], T)
ok(not nueva and ak.uno(Core.dir, iid)["lanzar"] == ["/nuevo"], "otra versión de la misma app actualiza su icono")

# ======================= MANEJO DE APPS =======================
O = ma.orden
ok(O("abre gimp con ~/foto.png") == ("abrir", "gimp", "~/foto.png") and O("cierra firefox") == ("cerrar", "firefox", "")
   and O("cierra firefox a la fuerza") == ("forzar", "firefox", "") and O("reinicia vlc") == ("reiniciar", "vlc", ""),
   "abrir / cerrar / forzar / reiniciar")
ok(O("¿está abierta gimp?") == ("estado", "gimp", "") and O("gimp está abierta?") == ("estado", "gimp", ""), "¿está abierta?")
ok(O("órdenes de gimp")[0] == O("cómo manejo vlc")[0] == O("qué puedo hacer con krita")[0] == "ordenes", "órdenes de X")
ok(O("en firefox, nueva ventana privada") == ("herramienta", "firefox", "nueva ventana privada") and
   O("usa la herramienta version de ffmpeg") == ("herramienta", "ffmpeg", "version"), "herramientas")
ok(O("qué apps tengo")[0] == "lista" and O("qué apps hay abiertas")[0] == "abiertas", "listas")

DIR_APPS = os.path.join(T, "applications")
os.makedirs(DIR_APPS)
PROG = os.path.join(T, "falsa_app.py")
with open(PROG, "w") as f:
    f.write("import sys, time\n"
            "if '--help' in sys.argv:\n"
            "    print('Uso: falsa [opciones]\\n  -v, --version   Muestra la versión\\n  --list-plugins  Lista los plugins\\n'"
            "'  -o, --output FICHERO  Guarda\\n\\nCommands:\\n  build    Compila el proyecto\\n  help     ayuda')\n"
            "    sys.exit(0)\n"
            "if '--version' in sys.argv:\n    print('falsa 1.2.3'); sys.exit(0)\n"
            "time.sleep(60)\n")
with open(os.path.join(DIR_APPS, "falsa.desktop"), "w") as f:
    f.write(f"[Desktop Entry]\nType=Application\nName=Falsa App\nName[es]=Falsa\nExec={sys.executable} {PROG} %U\n"
            "Actions=nueva;\n\n[Desktop Action nueva]\nName=Nueva ventana\nExec=" + sys.executable + f" {PROG} --nueva\n")
with open(os.path.join(DIR_APPS, "oculta.desktop"), "w") as f:
    f.write("[Desktop Entry]\nType=Application\nName=Oculta\nExec=/bin/true\nNoDisplay=true\n")
with open(os.path.join(DIR_APPS, "mapas.desktop"), "w") as f:
    f.write("[Desktop Entry]\nType=Application\nName=Mapa\nExec=/bin/true\n")

d = ma.leer_desktop(os.path.join(DIR_APPS, "falsa.desktop"))
ok(d["titulo"] == "Falsa" and d["admite_archivo"] and "%U" not in d["lanzar"] and d["acciones"][0]["nombre"] ==
   "Nueva ventana", "lee el .desktop (nombre en español, acciones, sin %U)")
M = ma.Manejo(accesos=[{"tipo": "externa", "titulo": "MiJuego", "lanzar": [sys.executable, PROG], "carpeta": T,
                        "id": "mijuego"}], dirs=[DIR_APPS])
ok(M.buscar("falsa")["titulo"] == "Falsa" and M.buscar("mijuego")["origen"] == "kira", "encuentra apps del sistema y de Kira")
ok(M.buscar("oculta") is None and M.buscar("el mapa") is None and M.buscar("fal") is None,
   "no las ocultas, ni las palabras de Kira («mapa»), ni parecidos sueltos")
ok(ma.hacer(M, "abrir", "la sala hacker") is None, "lo que no es una app → None (sigue el reparto normal)")

app = M.buscar("falsa")
r = ma.hacer(M, "abrir", "falsa")
ok(r["ok"] and r.get("pid"), "abre la app (Popen) y apunta su proceso")
time.sleep(0.3)
ok("Sí, Falsa está abierta" in ma.hacer(M, "estado", "falsa")["texto"], "«¿está abierta?» → sí")
ok("Falsa" in ma.hacer(M, "abiertas")["texto"], "sale en «qué apps hay abiertas»")
r = ma.hacer(M, "cerrar", "falsa")
ok(r["ok"] and "cerrada" in r["texto"], "la cierra")
time.sleep(0.2)
ok("No, Falsa no está abierta" in ma.hacer(M, "estado", "falsa")["texto"], "…y ya no está abierta")
ok("no está abierta" in ma.hacer(M, "cerrar", "falsa")["texto"], "cerrar lo cerrado lo dice")
r = ma.hacer(M, "abrir", "falsa", "/no/existe.png")
ok(not r["ok"] and "No encuentro" in r["texto"], "un archivo que no existe no se pasa")

herr = M.herramientas(app)
nombres = [h["nombre"] for h in herr]
ok("Nueva ventana" in nombres and "--version" in nombres and "--list-plugins" in nombres and "build" in nombres,
   "descubre acciones, opciones y subórdenes")
ok("--output" not in nombres and "--help" not in nombres and "help" not in nombres,
   "no ofrece las que piden un valor ni la ayuda")
r = ma.hacer(M, "herramienta", "falsa", "version")
ok(r["ok"] and "falsa 1.2.3" in r["texto"], "«en Falsa, version» la usa y enseña lo que contesta")
r = ma.hacer(M, "herramienta", "falsa", "volar")
ok(not r["ok"] and "--version" in r["texto"], "una que no tiene → dice las que hay")
txt = ma.hacer(M, "ordenes", "falsa")["texto"]
ok("Órdenes para manejar Falsa" in txt and "«abre Falsa con <archivo o web>»" in txt and "«cierra Falsa»" in txt and
   "«en Falsa, Nueva ventana»" in txt and "«en Falsa, --version» — Muestra la versión" in txt,
   "«órdenes de Falsa» las dice todas")
ok("MiJuego" in ma.hacer(M, "lista")["texto"] and "Falsa" in ma.hacer(M, "lista")["texto"], "«qué apps tengo»")
ok("«órdenes de Zeta»" in ma.breve("Zeta"), "al instalar dice cómo manejarla")

# no cierra procesos que no son de esa app
otro = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
M2 = ma.Manejo(accesos=[], dirs=[DIR_APPS])
ma.hacer(M2, "abrir", "falsa")
time.sleep(0.3)
ma.hacer(M2, "cerrar", "falsa")
ok(otro.poll() is None, "cerrar Falsa NO toca otro python cualquiera")
otro.kill()

# cableado en el núcleo
fuente = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("ma_.orden(o)" in fuente and "vk_.es_respuesta" in fuente, "el núcleo maneja apps y versiones")
html = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html"), encoding="utf-8").read()
ok('data-a="cerrar"' in html and 'hablarCon("órdenes de "+a.titulo)' in html,
   "clic derecho en una app: Cerrar y Órdenes para manejarla")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
