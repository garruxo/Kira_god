# -*- coding: utf-8 -*-
"""v3.45: todas las aplicaciones de Xubuntu en KiraOS, fondos e iconos con imagen (también pintados en el móvil),
cerebro 4B para pensar/programar, y el estudio a fondo («ingeniería inversa») del portátil y sus drivers."""
import base64
import io
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
TMP = tempfile.mkdtemp()
os.environ["KIRA_SISTEMA"] = os.path.join(TMP, "sistema.json")
os.environ["KIRA_AVISOS"] = os.path.join(TMP, "avisos.json")
os.environ["KIRA_HARDWARE"] = os.path.join(TMP, "hardware.json")
os.environ["KIRA_DATOS_NUCLEO"] = os.path.join(TMP, "datos")
os.environ["HOME"] = os.path.join(TMP, "casa")
os.makedirs(os.environ["HOME"], exist_ok=True)

import fondos_kira as fk            # noqa: E402
import menu_apps_kira as mak        # noqa: E402
import sistema_kira as sk           # noqa: E402
import sincronia_kira as sc         # noqa: E402
import cerebro_grande_kira as cg    # noqa: E402
import servidor_portatil as sp      # noqa: E402
import hardware_kira as hw          # noqa: E402
import mando_kira as mk             # noqa: E402
import estudio_kira as ek           # noqa: E402

N = 0


def ok(c, msg):
    global N
    if not c:
        print("FALLA:", msg)
        sys.exit(1)
    N += 1


PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def escribe(ruta, datos=PNG):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "wb") as f:
        f.write(datos)
    return ruta


# ======================= FONDOS e ICONOS con imagen =======================
movil = os.path.join(TMP, "datos", "imagenes_movil")
escribe(os.path.join(movil, "atardecer_kira.png"))
escribe(os.path.join(TMP, "casa", "Imágenes", "playa.jpg"), b"\xff\xd8\xff\xe0" + b"0" * 100)
escribe(os.path.join(TMP, "casa", "Imágenes", "notas.txt"), b"no soy imagen")
os.utime(os.path.join(movil, "atardecer_kira.png"), (1000, 1000))
lista = fk.listar()
ok([x["nombre"] for x in lista] == ["atardecer_kira", "playa"], "lista solo imágenes, las del móvil primero")
ok(lista[0]["origen"] == "pintado en el móvil", "dice de dónde viene")
ok(fk.buscar("la última del móvil", lista)["nombre"] == "atardecer_kira", "«la última del móvil»")
ok(fk.buscar("playa", lista)["nombre"] == "playa", "por el nombre")
ok(fk.buscar("montaña", lista) is None, "no inventa")
ok(fk.por_id(lista[1]["id"], lista)["nombre"] == "playa", "por su id")
ok(fk.miniatura(lista[0]["ruta"]).startswith("data:image/"), "miniatura como data:")
ok(fk.fondo(lista[0]["ruta"]).startswith("data:image/"), "fondo como data:")
ok(fk.fondo("/etc/passwd") == "", "nunca un archivo que no es imagen")
g = fk.galeria(lista)
ok(len(g) == 2 and "ruta" not in g[0], "la galería no enseña rutas")

# órdenes del sistema
for f, esperado in (("pon de fondo la última del móvil", ("fondo", "la ultima del movil")),
                    ("cambia el fondo de pantalla a playa", ("fondo", "playa")),
                    ("pon la playa de fondo", ("fondo", "la playa")),
                    ("quita el fondo", ("fondo_quitar", None)),
                    ("cambia el fondo", ("fondo_galeria", None)),
                    ("abre todas las aplicaciones", ("abrir", "aplicaciones")),
                    ("abre el menú de aplicaciones", ("abrir", "aplicaciones")),
                    ("quita la imagen del icono del mapa", ("icono_img_quitar", "mapa"))):
    ok(sk.orden(f) == esperado, f"orden: {f} → {sk.orden(f)}")
ok(sk.orden("pon la última del móvil como icono del mapa") == ("icono_img", ("la ultima del movil", "mapa")),
   "imagen como icono")
ok(sk.orden("cambia el aspecto del móvil a bosque") is None, "el aspecto del móvil sigue siendo otra orden")
ok(sk.orden("cambia el icono del mapa por una estrella")[0] == "dibujo_icono", "cambiar el dibujo sigue igual")
ok(sk.orden("abre firefox") is None, "«abre firefox» no es esto (lo hace el manejo de apps)")

r = sk.hacer("fondo", "la última del móvil")
ok("atardecer_kira" in r and sk.ruta_fondo().endswith("atardecer_kira.png"), "pone el fondo")
pp = sk.para_pantalla()
ok(pp["fondo"] and pp["fondo"]["id"] == fk.por_id(lista[0]["id"], lista)["id"] and "ruta" not in pp["fondo"],
   "la pantalla recibe el id, no la ruta")
ok("[x]" in sk.hacer("fondo", "montaña"), "imagen que no existe: lo dice")
r = sk.hacer("icono_img", ("playa", "mapa"))
ok("playa" in r and sk.ruta_icono_img("mapa").endswith("playa.jpg"), "icono con imagen")
ok(sk.para_pantalla()["iconos_img"].get("mapa"), "la pantalla sabe que el mapa lleva imagen")
ok("[x]" in sk.hacer("icono_img", ("playa", "nada")), "icono que no existe")
sk.hacer("icono_img_quitar", "mapa")
ok(not sk.para_pantalla()["iconos_img"], "quitar la imagen del icono")
sk.hacer("fondo_quitar", None)
ok(sk.para_pantalla()["fondo"] is None, "quitar el fondo")
ok("tengo 2 imágenes" in sk.hacer("fondo_galeria", None), "galería: cuántas hay")
os.remove(os.path.join(TMP, "casa", "Imágenes", "playa.jpg"))
d = sk.cargar()
d["fondo"] = os.path.join(TMP, "casa", "Imágenes", "playa.jpg")
sk.guardar(d)
ok(sk.para_pantalla()["fondo"] is None, "un fondo borrado no rompe nada")

# ======================= TODAS LAS APLICACIONES =======================
apps_dir = os.path.join(TMP, "apps")
iconos = os.path.join(TMP, "share")
escribe(os.path.join(apps_dir, "firefox.desktop"),
        b"[Desktop Entry]\nType=Application\nName=Firefox\nName[es]=Navegador Firefox\nGenericName[es]=Navegador web\n"
        b"Exec=firefox %u\nIcon=firefox\nCategories=Network;WebBrowser;\n")
escribe(os.path.join(apps_dir, "xfce4-settings-manager.desktop"),
        b"[Desktop Entry]\nType=Application\nName=Gestor de configuracion\nExec=xfce4-settings-manager\n"
        b"Icon=org.xfce.settings.manager\nCategories=XFCE;GTK;Settings;DesktopSettings;\n")
escribe(os.path.join(apps_dir, "calc.desktop"),
        b"[Desktop Entry]\nType=Application\nName=Calculadora\nExec=galculator\nIcon=accessories-calculator\n"
        b"Categories=Utility;Calculator;\n")
escribe(os.path.join(apps_dir, "oculta.desktop"), b"[Desktop Entry]\nType=Application\nName=X\nExec=x\nNoDisplay=true\n")
escribe(os.path.join(iconos, "icons", "hicolor", "48x48", "apps", "firefox.png"))
escribe(os.path.join(iconos, "icons", "elementary-xfce", "apps", "48", "accessories-calculator.svg"),
        b"<svg xmlns='http://www.w3.org/2000/svg'/>")
m = mak.menu([apps_dir], iconos)
ok([a["titulo"] for a in m["apps"]] == ["Calculadora", "Gestor de configuracion", "Navegador Firefox"], "apps ordenadas")
cat = {a["titulo"]: a["categoria"] for a in m["apps"]}
ok(cat == {"Calculadora": "Accesorios", "Gestor de configuracion": "Configuración", "Navegador Firefox": "Internet"},
   "categorías como el menú de Xubuntu")
ok(m["categorias"] == ["Configuración", "Internet", "Accesorios"], "solo las categorías que hay, en su orden")
ico = {a["titulo"]: a["icono"] for a in m["apps"]}
ok(ico["Navegador Firefox"].startswith("data:image/png") and ico["Calculadora"].startswith("data:image/svg+xml"),
   "iconos de verdad del tema (png y svg, también el formato de elementary)")
ok(ico["Gestor de configuracion"] == "", "sin icono, vacío (la pantalla pone el suyo)")
lanzados = []


class P:
    pid = 4242


man = mak.ma.Manejo(dirs=[apps_dir], popen=lambda *a, **k: (lanzados.append(a[0]), P())[1],
                    ruta_procesos=os.path.join(TMP, "proc.json"))
r = mak.abrir("calc.desktop", [apps_dir], man)
ok(r["ok"] and lanzados == [["galculator"]], "abre la app de la lista, con su orden en lista")
ok(not mak.abrir("../../etc/passwd", [apps_dir], man)["ok"], "nunca algo fuera de la lista")
ok(not mak.abrir("oculta.desktop", [apps_dir], man)["ok"], "ni las ocultas")

# ======================= los dibujos del móvil viajan a KiraOS =======================
dm, dk = os.path.join(TMP, "m"), os.path.join(TMP, "k")
for i in range(3):
    escribe(os.path.join(dm, "imagenes", f"dibujo{i}.png"))
    os.utime(os.path.join(dm, "imagenes", f"dibujo{i}.png"), (2000 + i, 2000 + i))
escribe(os.path.join(dm, "imagenes", "falsa.png"), b"esto no es png")
imgs, claves, quedan = sc._imagenes_nuevas(dm, [])
ok(len(imgs) == 2 and quedan, "dos por viaje y avisa de que quedan")
ok(sc.guardar_imagenes_recibidas(dk, imgs) == 2, "KiraOS las guarda")
ok(sorted(os.listdir(os.path.join(dk, "imagenes_movil"))) == ["dibujo0.png", "dibujo1.png"], "en imagenes_movil")
imgs2, claves2, quedan2 = sc._imagenes_nuevas(dm, claves)
ok([i["nombre"] for i in imgs2] == ["dibujo2.png", "falsa.png"] and not quedan2, "el siguiente viaje sigue")
ok(sc.guardar_imagenes_recibidas(dk, imgs2) == 1, "una falsa (no es PNG de verdad) no se guarda")
ok(sc.guardar_imagenes_recibidas(dk, [{"nombre": "../../x.png", "datos": base64.b64encode(PNG).decode()}]) == 1 and
   os.path.isfile(os.path.join(dk, "imagenes_movil", "x.png")) and not os.path.exists(os.path.join(TMP, "x.png")),
   "un nombre con «..» no sale de su carpeta")
ok(sc.guardar_imagenes_recibidas(dk, [{"nombre": "a.exe", "datos": base64.b64encode(PNG).decode()}]) == 0, "solo imágenes")
src = open(os.path.join(RAIZ, "sincronia_kira.py"), encoding="utf-8").read()
ok('"imagenes": imgs' in src and "guardar_imagenes_recibidas(dir_, paquete.get(\"imagenes\"))" in src and
   'est["img_enviadas"]' in src, "cableado en la sincronía (solo se marcan enviadas si llegó la respuesta)")

# ======================= cerebro 4B =======================
for f in ("aumenta tu cerebro", "Kira, mejora tu cerebro", "descarga tu cerebro grande", "ponte el cerebro de 4B",
          "usa un cerebro más listo"):
    ok(cg.es_orden(f) == "bajar", "reconoce: " + f)
ok(cg.es_orden("qué cerebro tienes") == "estado", "estado")
ok(cg.es_orden("mejora tu sistema: algo") is None and cg.es_orden("estudia python") is None, "no se come otras")
mods = os.path.join(TMP, "modelos")
ok("2B para todo" in cg.estado(ram=4000, modelos=mods), "con 4 GB lo dice")
ok("Cabe el 4B" in cg.estado(ram=7600, modelos=mods), "con 8 GB ofrece el 4B")
g4, _ = cg.objetivo(7600)
contenido = b"K" * 3000


class Resp:
    def __init__(self, datos, status=200):
        self.b = io.BytesIO(datos)
        self.status = status

    def read(self, n=-1):
        return self.b.read(n)


cortes = {"n": 0}


def abrir_falso(req):
    rango = req.get_header("Range")
    if rango:
        ini = int(rango.split("=")[1].rstrip("-"))
        return Resp(contenido[ini:], 206)
    return Resp(contenido[:1000])                     # la primera vez se corta a los 1000


cg.sp.LIGERO_GRANDE["bytes"] = 3000
r = cg.descargar(abrir=abrir_falso, ram=7600, modelos=mods, trozo=256)
ok("se cortó" in r and os.path.getsize(os.path.join(mods, g4["archivo"] + ".part")) == 1000, "corte: guarda lo bajado")
ok("llevo 1 MB" in cg.estado(ram=7600, modelos=mods) or "llevo 0 MB" in cg.estado(ram=7600, modelos=mods),
   "estado: cuánto lleva")
pasos = []
r = cg.descargar(abrir=abrir_falso, ram=7600, modelos=mods, trozo=256, al_paso=lambda f, t: pasos.append(f))
ok("Listo" in r and open(os.path.join(mods, g4["archivo"]), "rb").read() == contenido, "reanuda y termina")
ok(pasos and pasos[-1] == 1.0, "barra hasta el final")
ok("Ya tengo" in cg.descargar(abrir=abrir_falso, ram=7600, modelos=mods), "no lo baja dos veces")
ok("dos cerebros" in cg.estado(ram=7600, modelos=mods), "estado con los dos")
os.remove(os.path.join(mods, g4["archivo"]))
ok("Paro" in cg.descargar(abrir=lambda q: Resp(contenido), ram=7600, modelos=mods, parar=lambda: True), "«para» la corta")

# ======================= estudio a fondo del portátil =======================
syspci = os.path.join(TMP, "sys", "pci")
os.makedirs(os.path.join(syspci, "0000:02:00.0"))
with open(os.path.join(syspci, "0000:02:00.0", "resource"), "w") as f:
    f.write("0x00000000f0000000 0x00000000f000ffff 0x0000000000140204\n"
            "0x0000000000000000 0x0000000000000000 0x0000000000000000\n"
            "0x000000000000e000 0x000000000000e0ff 0x0000000000040101\n")
with open(os.path.join(syspci, "0000:02:00.0", "irq"), "w") as f:
    f.write("17\n")
rp = hw.recursos_pci("0000:02:00.0", syspci)
ok(rp["irq"] == "17" and rp["zonas"][0] == {"bar": 0, "inicio": "0xf0000000", "tam": 65536, "tipo": "memoria"} and
   rp["zonas"][1]["tipo"] == "puertos", "zonas de memoria y puertos de la pieza")
sysmod = os.path.join(TMP, "sys", "mod")
os.makedirs(os.path.join(sysmod, "tg3", "parameters"))
with open(os.path.join(sysmod, "tg3", "parameters", "tg3_debug"), "w") as f:
    f.write("-1\n")
ok(hw.parametros_modulo("tg3", sysmod) == {"tg3_debug": "-1"}, "ajustes del driver")
ok(hw.registro_kernel("tg3", correr=lambda a: (0, "[1.0] tg3 0000:02:00.0 eth0: Tigon3 [partno(BCM57780)]\n[1.1] otra\n"))
   == ["[1.0] tg3 0000:02:00.0 eth0: Tigon3 [partno(BCM57780)]"], "lo que Linux apuntó del driver")
ok(hw.version_linux("6.8.0-48-generic") == "v6.8" and hw.version_linux("") == "master", "versión de Linux")
rs = hw.resumen_fuente("#define TG3PCI_DEVICE 0x00000002\n#define MAC_MODE 0x00000400\nint x;\n")
ok(rs["registros"] == 2 and "MAC_MODE = 0x00000400" in rs["ejemplos"], "saca los registros del chip")
pedidas = []


def abrir_linux(req, timeout=60):
    pedidas.append(req.full_url)
    return Resp(b"#define MAC_MODE 0x00000400\n#define RX_MODE 0x00000468\n")


r = hw.estudiar_codigo("tg3", "6.8.0-48-generic", abrir=abrir_linux, carpeta=os.path.join(TMP, "estudio"))
ok(r["ok"] and pedidas[0] == "https://raw.githubusercontent.com/torvalds/linux/v6.8/drivers/net/ethernet/broadcom/tg3.h",
   "baja el código abierto de Linux de SU versión")
ok(os.path.isfile(os.path.join(TMP, "estudio", "tg3", "tg3.h")) and
   os.path.isfile(os.path.join(TMP, "estudio", "tg3", "resumen.txt")), "lo guarda con su resumen")
ok("2 registros" in r["texto"], "cuenta los registros")
ok("drivers/net/wireless/ath/ath9k/ar9287_initvals.h" in hw.FUENTES_LINUX["ath9k"] and
   "drivers/net/wireless/ath/ath9k/eeprom_9287.c" in hw.FUENTES_LINUX["ath9k"], "v3.46: lo de la WiFi AR9287 del Packard Bell")
ok(not hw.estudiar_codigo("desconocido", abrir=abrir_linux)["ok"], "driver que no conoce: lo dice")
for f, esperado in (("haz ingeniería inversa del portátil", ("fondo", "")), ("estudia el código del driver tg3", ("fondo", "tg3")),
                    ("estudia el driver de tu red por cable", ("fondo", "red")), ("estudia a fondo tu hardware", ("fondo", ""))):
    ok(hw.es_orden_fondo(f) == esperado, "a fondo: " + f)
    ok(mk.es_trabajo(f), "desde el móvil va a KiraOS: " + f)
    ok(ek.es_estudia_general(f) is None, "no es el estudio por internet: " + f)
ok(hw.es_orden_fondo("estudia tu hardware") is None, "el estudio normal sigue siendo el normal")
nucleo = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok(nucleo.index("cg_.es_orden(o)") < nucleo.index("hw_.es_orden_fondo(o)") < nucleo.index("hw_.es_orden(o)"),
   "el núcleo atiende: cerebro, a fondo, normal")
ok("\"ingenieria\"" not in nucleo, "sanidad")

# ======================= el puente del escritorio =======================
import escritorio_kira as esk       # noqa: E402


class Api(esk.EscritorioMixin):
    cli = None


api = Api()
d = api.fondos()
ok(d["imagenes"] and "ruta" not in d["imagenes"][0] and "Tengo" in d["texto"], "puente: galería")
r = api.fondo_poner(d["imagenes"][0]["id"])
ok(r["ok"] and api.fondo_datos().startswith("data:image/"), "puente: poner y dar el fondo")
ok(not api.fondo_poner("noexiste")["ok"], "puente: id que no existe")
api.fondo_quitar()
ok(api.fondo_datos() == "", "puente: quitar")
mak.ma.DIRS_DESKTOP = (apps_dir,)
ok(any(a["titulo"] == "Calculadora" for a in api.apps_menu()["apps"]), "puente: menú de aplicaciones")
api._ini_escritorio()
aj = api._app_ajustes()
ok(aj["botones"][0]["accion"] == "app:aplicaciones" and aj["botones"][1]["accion"] == "app:fondos",
   "Ajustes: Todas las aplicaciones y Fondo de pantalla")
t = {"estado": "hecho", "respuesta": "x", "lineas": [], "pedir_clave": False, "abrir": "fondos"}
api._ini_escritorio()
api._charlas["z"] = t
ok(api.tarea_hablar("z").get("abrir") == "fondos", "la respuesta abre la ventana de fondos")
t["abrir"] = "terminal"
ok("abrir" not in api.tarea_hablar("z"), "solo esas dos ventanas")

# ======================= en Chromium =======================
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
if sync_playwright:
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        pg.goto("file://" + os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html") + "#quedarse")
        pg.wait_for_timeout(500)
        pg.evaluate("abrir('aplicaciones')")
        pg.wait_for_timeout(300)
        ok(pg.evaluate("window.KIRA_APPS.vistas") == 2 and "Firefox" in pg.inner_text("#appsLista"), "Chromium: apps")
        pg.click("[data-cat='Sistema']")
        pg.wait_for_timeout(100)
        ok(pg.evaluate("window.KIRA_APPS.vistas") == 1 and "Gestor de tareas" in pg.inner_text("#appsLista"), "Chromium: categoría")
        pg.fill("#appsBuscar", "zzz")
        pg.wait_for_timeout(100)
        ok("No hay ninguna" in pg.inner_text("#appsLista"), "Chromium: buscar")
        pg.evaluate("abrir('fondos')")
        pg.wait_for_timeout(300)
        ok("atardecer" in pg.inner_text("#vcuerpo"), "Chromium: galería de fondos")
        pg.click(".fondo-i")
        pg.wait_for_timeout(700)
        ok(pg.evaluate("window.KIRA_FONDO && window.KIRA_FONDO.puesto"), "Chromium: el fondo se pone")
        ok("data:image" in pg.evaluate("document.getElementById('fondo').style.background"), "Chromium: con la imagen")
        pg.evaluate("ponAspecto(Object.assign({}, ASPECTO, {iconos_img:{mapa:'abc'}}))")
        pg.wait_for_timeout(400)
        ok(pg.evaluate("!!document.querySelector('.icono[data-app=mapa] img.icoimg') && "
                       "document.querySelector('.icono[data-app=mapa] img.icoimg').src.indexOf('data:image')===0"),
           "Chromium: icono con imagen")
        pg.evaluate("volver()")
        pg.click("#btnKira")
        ok("Todas las aplicaciones" in pg.inner_text("#menu"), "Chromium: en el menú K")
        b.close()

print(f"TODO BIEN ({N})")
