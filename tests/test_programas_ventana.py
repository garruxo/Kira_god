# -*- coding: utf-8 -*-
"""v3.77: programas DE VENTANA en el Taller.
  1) RECETAS probadas para usarlos por órdenes (LibreOffice, GIMP, Inkscape, ImageMagick, ffmpeg, pandoc): el plan
     sale de la receta tal cual, sin que el cerebro lo invente; se ejecutan DE VERDAD los que hay en esta máquina.
  2) EXPERIMENTAL: manejarlos POR DENTRO con la accesibilidad (AT-SPI), pulsando menús y botones por su nombre, con
     un programa de mentira: plan, «Hazlo», candados (borrar/enviar/contraseñas/terminales), se para si no encuentra.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_TALLER"] = os.path.join(T, "taller")
os.environ["KIRA_DATOS_NUCLEO"] = os.path.join(T, "datos")
os.makedirs(os.environ["KIRA_DATOS_NUCLEO"], exist_ok=True)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import recetas_programas_kira as rp
import taller_programas_kira as tp
import accesibilidad_kira as acc

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ======================================================================= 1) RECETAS
W = {"soffice", "gimp", "convert", "inkscape", "ffmpeg", "pandoc"}
ok(rp.canonico("libreoffice", which=lambda c: c in W) == "soffice", "«libreoffice» → soffice")
ok(rp.canonico("imagemagick", which=lambda c: c in W) == "convert", "«imagemagick» → convert (si no hay magick)")
ok(rp.canonico("imagemagick", which=lambda c: c in W | {"magick"}) == "magick", "«imagemagick» → magick si lo hay")
ok(rp.canonico("git", which=lambda c: True) == "git", "lo que no tiene alias, igual")

P = rp.plan
o = P("soffice", "convierte informe.docx a pdf")[0]
ok(len(o) == 1 and "--headless --convert-to pdf" in o[0] and o[0].endswith("informe.docx"), "LibreOffice: docx → pdf")
ok("--convert-to csv" in P("soffice", "pasa datos.xlsx a csv")[0][0], "LibreOffice: xlsx → csv")
ok("UserInstallation=file:///tmp/kira_lo" in o[0], "LibreOffice con su propio perfil (no choca con el tuyo)")
g = P("gimp", "haz foto.jpg más pequeña al 50%")[0][0]
ok(g.startswith("gimp -i -b '(let*") and "gimp-image-scale" in g and "0.5" in g and '"foto_peq.jpg"' in g,
   "GIMP por lotes: al 50%")
ok("gimp-image-convert-grayscale" in P("gimp", "pon foto.png en blanco y negro")[0][0], "GIMP: blanco y negro")
ok("ROTATE-270" in P("gimp", "gira foto.png a la izquierda")[0][0], "GIMP: girar a la izquierda")
ok(" 800 " in P("gimp", "haz foto.jpg de 800 px")[0][0], "GIMP: a 800 px de ancho")
ok(P("convert", "gira foto.jpg 90")[0] == ["convert foto.jpg -rotate 90 foto_girada.jpg"], "ImageMagick: girar")
ok(P("convert", "haz foto.jpg de 640 px")[0] == ["convert foto.jpg -resize 640x foto_peq.jpg"], "ImageMagick: tamaño")
ok(P("convert", "pon foto.jpg en escala de grises")[0] == ["convert foto.jpg -colorspace Gray foto_gris.jpg"],
   "ImageMagick: grises")
ok(P("ffmpeg", "saca el audio de video.mp4")[0] == ["ffmpeg -nostdin -y -i video.mp4 -vn video.mp3"], "ffmpeg: audio")
ok("fps=10,scale=480:-1" in P("ffmpeg", "haz un gif de video.mp4")[0][0], "ffmpeg: gif")
ok(P("inkscape", "exporta logo.svg a png de 512 px")[0] ==
   ["inkscape logo.svg --export-type=png --export-filename=logo.png -w 512"], "Inkscape: svg → png")
ok(P("pandoc", "convierte notas.md a html")[0] == ["pandoc notas.md -o notas.html"], "pandoc: md → html")
ok(P("gimp", "pinta un gato precioso") is None, "lo que no tiene receta: None (va al cerebro)")
ok(P("git", "convierte algo a pdf") is None, "un programa sin recetas: None")
v = P("convert", "haz pequeñas todas las fotos", ["a.jpg", "b.png", "notas.txt"])[0]
ok(len(v) == 2 and "a.jpg" in v[0] and "b.png" in v[1], "«todas las fotos»: las de la carpeta del taller")
ok(len(P("convert", "haz pequeña la foto", ["a.jpg", "b.png"])[0]) == 1, "sin «todas»: solo una")
f = P("convert", "haz pequeña la foto", [])
ok(f[0] == [] and "carpeta" in f[1][0], "sin archivo: dice dónde ponerlo")
ok(P("convert", "gira la foto 90", ["mal'nombre.jpg"])[0] == [], "nombres con comillas: no entran en una receta")
ok("Ejemplos que funcionan" in rp.ejemplos("gimp") and "$ gimp -i -b" in rp.ejemplos("gimp"), "ejemplos para el cerebro")

# ---------- candados ----------
V = tp.validar_orden
gimp_receta = P("gimp", "haz foto.jpg de 800 px")[0][0]
ok(V(gimp_receta, "gimp", lanzar=["g"], de_receta=True)[:3] == ["g", "-i", "-b"], "un guion de GIMP de la receta: sí")
for mala, por in [("gimp -i -b '(gimp-quit 0)'", "guiones"),
                  ("soffice --headless macro:///Standard.Module1.Main", "guiones"),
                  ("inkscape a.svg --actions=export-do", "guiones"),
                  ("convert file:///etc/passwd x.png", "fuera"),
                  ("convert -font /etc/shadow a.png b.png", "fuera"),
                  ("ffmpeg -i x.mp4 -f mp3 -vn salida=/etc/x.mp3", "fuera"),
                  ("convert ../secreto.jpg x.png", ".."),
                  ("convert a.jpg x.png", None)]:
    try:
        V(mala, mala.split()[0], lanzar=["x"])
        ok(por is None, f"válida: {mala}")
    except ValueError as e:
        ok(por is not None and (por in str(e) or (por == "fuera" and "fuera" in str(e))), f"rechazada ({por}): {mala}")
try:
    V(gimp_receta.replace('"foto.jpg"', '"../foto.jpg"', 1), "gimp", lanzar=["g"], de_receta=True)
    ok(False, "«..» dentro de un guion")
except ValueError:
    ok(True, "«..» dentro de un guion: no, ni de receta")
ok(V("soffice -env:UserInstallation=file:///tmp/kira_lo --headless --convert-to pdf --outdir . a.docx", "soffice",
     lanzar=["s"])[1].startswith("-env"), "el perfil en /tmp sí vale")


def cerebro_nunca(sistema, usuario):
    raise AssertionError("con receta no se pregunta al cerebro")


# ---------- de verdad, con lo que hay instalado aquí ----------
if shutil.which("convert"):
    carp = tp.carpeta_de("convert")
    subprocess.run(["convert", "-size", "120x80", "xc:red", os.path.join(carp, "foto.png")], check=True)
    s, txt = tp.preparar("convert", "haz foto.png de 60 px", cerebro_nunca)
    ok(s["de_receta"] and "recetas probadas" in txt and s["plan"] == ["convert foto.png -resize 60x foto_peq.png"],
       "preparar con receta (sin cerebro)")
    ok("de mis recetas probadas" in tp.texto_ventana(tp.leer()), "la ventana dice que es de receta")
    ob = tp.Obrero()
    ob.empezar()
    ob.hilo.join(30)
    sal = os.path.join(carp, "foto_peq.png")
    dims = subprocess.run(["identify", "-format", "%wx%h", sal], capture_output=True, text=True).stdout
    ok(os.path.exists(sal) and dims == "60x40", f"ImageMagick DE VERDAD: 120x80 → {dims}")
    s, txt = tp.preparar("imagemagick", "pon foto.png en blanco y negro", cerebro_nunca)
    ok(s and s["programa"] == "convert", "«imagemagick» se resuelve a convert")
else:
    print("  (sin ImageMagick aquí: no lo pruebo de verdad)")

if shutil.which("pandoc"):
    carp = tp.carpeta_de("pandoc")
    open(os.path.join(carp, "notas.md"), "w").write("# Hola\n\nKira **trabaja**.\n")
    tp.preparar("pandoc", "convierte notas.md a html", cerebro_nunca)
    ob = tp.Obrero()
    ob.empezar()
    ob.hilo.join(30)
    h = os.path.join(carp, "notas.html")
    ok(os.path.exists(h) and "<strong>trabaja</strong>" in open(h).read(), "pandoc DE VERDAD: md → html")

if shutil.which("ffmpeg"):
    carp = tp.carpeta_de("ffmpeg")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=duration=1:size=160x120:rate=10",
                    "-f", "lavfi", "-i", "sine=duration=1", "-shortest", os.path.join(carp, "video.mp4")], check=True)
    tp.preparar("ffmpeg", "saca el audio de video.mp4", cerebro_nunca)
    ob = tp.Obrero()
    ob.empezar()
    ob.hilo.join(60)
    ok(os.path.getsize(os.path.join(carp, "video.mp3")) > 1000, "ffmpeg DE VERDAD: saca el audio")

if shutil.which("soffice") and os.environ.get("KIRA_SIN_SOFFICE") != "1":
    carp = tp.carpeta_de("soffice")
    open(os.path.join(carp, "carta.txt"), "w").write("Hola, soy Kira.\n")
    s, _t = tp.preparar("libreoffice", "convierte carta.txt a pdf", cerebro_nunca)
    ob = tp.Obrero()
    ob.empezar()
    ob.hilo.join(170)
    pdf = os.path.join(carp, "carta.pdf")
    ok(s["programa"] in ("soffice", "libreoffice") and os.path.exists(pdf) and open(pdf, "rb").read(4) == b"%PDF",
       "LibreOffice DE VERDAD (sin ventana): txt → pdf")

for _prog in ("gimp", "inkscape"):
    if not shutil.which(_prog):
        print(f"  (sin {_prog} aquí: su receta se prueba en GitHub con probar_programas_ventana.yml)")
if shutil.which("gimp") and shutil.which("convert"):
    carp = tp.carpeta_de("gimp")
    subprocess.run(["convert", "-size", "200x100", "gradient:red-blue", os.path.join(carp, "foto.jpg")], check=True)
    for tarea, sal, dims in [("haz foto.jpg más pequeña al 50%", "foto_peq.jpg", "100x50"),
                             ("gira foto.jpg 90", "foto_girada.jpg", "100x200"),
                             ("pon foto.jpg en blanco y negro", "foto_gris.jpg", "200x100")]:
        tp.preparar("gimp", tarea, cerebro_nunca)
        ob = tp.Obrero()
        ob.empezar()
        ob.hilo.join(170)
        d = subprocess.run(["identify", "-format", "%wx%h", os.path.join(carp, sal)], capture_output=True, text=True).stdout
        ok(d == dims, f"GIMP DE VERDAD: {tarea} → {d or 'nada'}  " + " | ".join(tp.leer()["registro"][-3:]))
if shutil.which("inkscape"):
    carp = tp.carpeta_de("inkscape")
    open(os.path.join(carp, "logo.svg"), "w").write('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">'
                                                     '<rect width="100" height="50" fill="teal"/></svg>')
    tp.preparar("inkscape", "exporta logo.svg a png de 300 px", cerebro_nunca)
    ob = tp.Obrero()
    ob.empezar()
    ob.hilo.join(170)
    png = os.path.join(carp, "logo.png")
    ok(os.path.exists(png) and open(png, "rb").read(4) == b"\x89PNG", "Inkscape DE VERDAD: svg → png")

# ---------- sin receta: el cerebro, con ejemplos, y sus guiones no valen ----------
visto = {}


def cerebro_gimp(sistema, usuario):
    visto["u"] = usuario
    return "$ gimp -i -b '(gimp-quit 0)'\n$ gimp --version"


tp.resolver = (lambda real: (lambda p, d=None: ("gimp", ["/usr/bin/gimp"]) if p in ("gimp",) else real(p, d)))(tp.resolver)
_which = tp.shutil.which
tp.shutil.which = lambda c: "/usr/bin/gimp" if c == "gimp" else _which(c)
try:
    s, txt = tp.preparar("gimp", "pinta un gato", cerebro_gimp, correr=lambda a, t: "GIMP ayuda " * 5)
finally:
    tp.shutil.which = _which
ok("Ejemplos que funcionan" in visto["u"], "sin receta: el cerebro recibe ejemplos de recetas")
ok(s["plan"] == ["gimp --version"] and any("guiones" in r["por"] for r in s["rechazadas"]),
   "el guion que escribe el cerebro se rechaza; lo demás sí")

# ======================================================================= 2) ACCESIBILIDAD (experimental)
E = acc.es_orden
ok(E("maneja gimp por dentro: exporta la imagen como png") == ("gimp", "exporta la imagen como png"), "maneja X por dentro")
ok(E("Kira, usa libreoffice desde su ventana para poner el título en negrita")[0] == "libreoffice", "desde su ventana")
ok(E("trabaja dentro de gimp: recorta") == ("gimp", "recorta"), "trabaja dentro de X")
ok(E("trabaja con gimp: haz foto.jpg pequeña") is None and E("hola") is None, "lo demás no es esto")
ok(tp.orden("trabaja con gimp por dentro: exporta") is None, "el Taller de órdenes no se lo come")

VP = acc.validar_paso
ok(VP("PULSA: Archivo > Exportar como…") == ("PULSA", ["Archivo", "Exportar como…"]), "PULSA con camino de menú")
ok(VP("escribe: Nombre = foto.png") == ("ESCRIBE", ("Nombre", "foto.png")), "ESCRIBE campo = texto")
ok(VP("ESPERA: 99") == ("ESPERA", 10), "ESPERA como mucho 10 s")
for malo in ["PULSA: Archivo > Eliminar", "PULSA: No guardar", "PULSA: Enviar", "PULSA: Vaciar papelera",
             "ESCRIBE: Contraseña = 1234", "ESCRIBE: Nombre =", "BORRA: todo", "PULSA: Reemplazar"]:
    try:
        VP(malo)
        ok(False, f"rechaza «{malo}»")
    except ValueError:
        ok(True, f"rechaza «{malo}»")
ok(acc.app_bloqueada("xfce4-terminal") and acc.app_bloqueada("Firefox") and acc.app_bloqueada("kiraos")
   and not acc.app_bloqueada("gimp"), "programas que no se manejan por dentro")


class Nodo:
    def __init__(self, nombre, rol, hijos=(), visible=True):
        self.nombre, self.rol, self.hijos, self.visible = nombre, rol, list(hijos), visible
        self.texto = ""


class Back:
    def __init__(self, apps):
        self._apps = apps
        self.pulsados, self.escritos = [], []
        self.al_pulsar = {}

    def apps(self):
        return list(self._apps)

    def hijos(self, n):
        return n.hijos

    def nombre(self, n):
        return n.nombre

    def rol(self, n):
        return n.rol

    def visible(self, n):
        return n.visible

    def pulsar(self, n):
        self.pulsados.append(n.nombre)
        f = self.al_pulsar.get(n.nombre)
        if f:
            f()
        return True

    def escribir(self, n, t):
        n.texto = t
        self.escritos.append((n.nombre, t))
        return True


exp_como = Nodo("Exportar como…", "menu item", visible=False)
borrar = Nodo("Eliminar", "menu item")
archivo = Nodo("Archivo", "menu", [exp_como, borrar, Nodo("Abrir…", "menu item")])
ventana = Nodo("GNU Image Manipulation Program", "frame", [Nodo("", "menu bar", [archivo]), Nodo("Filtros", "menu")])
gimp = Nodo("GNU Image Manipulation Program", "application", [ventana])
term = Nodo("xfce4-terminal", "application", [Nodo("Ejecutar", "push button")])
back = Back([term])
dialogo = Nodo("Exportar imagen", "dialog", [Nodo("Nombre", "text"), Nodo("Exportar", "push button"),
                                              Nodo("Contraseña", "password text")])


def abre_dialogo():
    ventana.hijos.append(dialogo)


back.al_pulsar["Exportar como…"] = abre_dialogo
back.al_pulsar["Archivo"] = lambda: setattr(exp_como, "visible", True)
lanzados = []


def popen_falso(args, **k):
    lanzados.append(args)
    back._apps.append(gimp)
    gimp.nombre = "gimp"


plan_cerebro = {}


def cerebro_pasos(sistema, usuario):
    plan_cerebro["u"] = usuario
    return ("PULSA: Archivo > Exportar como…\nESCRIBE: Nombre = foto.png\nPULSA: Exportar\nESPERA: 1\n"
            "PULSA: Archivo > Eliminar\nNOTA: si sale «Reemplazar», pregúntale al dueño")


s, txt = acc.preparar("gimp", "exporta la imagen como png", cerebro_pasos, back=back, popen=popen_falso,
                      which=lambda c: "/usr/bin/gimp" if c == "gimp" else None, dormir=lambda x: None, esperar_app=1)
ok(lanzados and lanzados[0] == ["/usr/bin/gimp"], "abre el programa si no estaba abierto")
ok("menú «Archivo»" in plan_cerebro["u"] and "menú «Exportar como…»" in plan_cerebro["u"]
   and "Contraseña" not in plan_cerebro["u"], "el cerebro recibe los menús y botones (sin los de contraseña)")
ok(s["modo"] == "ventana" and s["estado"] == "esperando" and len(s["plan"]) == 4 and not back.pulsados,
   "plan de 4 pasos ESPERANDO tu «Hazlo» (no ha pulsado nada)")
ok(any("Eliminar" in r["orden"] for r in s["rechazadas"]), "el paso de «Eliminar» se rechaza")
ok("POR DENTRO DE SU VENTANA" in tp.texto_ventana(tp.leer()) and "EXPERIMENTAL" in txt, "la ventana dice que es experimental")
ob = tp.Obrero(back=back, dormir=lambda x: None)
ob.empezar()
ob.hilo.join(10)
fin = tp.leer()
ok(back.pulsados == ["Archivo", "Exportar como…", "Exportar"], f"pulsa por su nombre, en orden: {back.pulsados}")
ok(back.escritos == [("Nombre", "foto.png")], "escribe en el campo")
ok(fin["estado"] == "hecho" and "4 de 4 pasos" in fin["resumen"] and any("✓ pulsé «Archivo > Exportar como…»" in r
                                                                         for r in fin["registro"]), "registro en vivo")

# si algo no aparece, se para (no improvisa); campos de contraseña nunca
s2 = dict(fin, plan=["PULSA: Herramientas", "PULSA: Exportar"], estado="esperando", registro=[])
tp.guardar(s2)
back.pulsados.clear()
_e = acc.ESPERA_ELEMENTO
acc.ESPERA_ELEMENTO = 0.01
ob = tp.Obrero(back=back, dormir=lambda x: None)
ob.empezar()
ob.hilo.join(10)
acc.ESPERA_ELEMENTO = _e
fin = tp.leer()
ok(back.pulsados == [] and "0 de 2" in fin["resumen"] and any("Me paro aquí" in r for r in fin["registro"]),
   "no encuentra un botón: se para")
try:
    acc.hacer_paso(back, "gimp", "ESCRIBE: Contrasena del archivo = x", dormir=lambda x: None, esperar=0.01)
    ok(False, "contraseña")
except ValueError:
    ok(True, "nunca escribe en un campo de contraseña")
ok(acc.buscar_app(back, "xfce4-terminal") is not None, "")
r, _t = acc.preparar("xfce4-terminal", "ejecuta algo", cerebro_pasos, back=back)
ok(r is None and "no lo manejo" in _t, "una terminal no se maneja por dentro")
r, _t = acc.preparar("programaquenoexiste", "algo", cerebro_pasos, back=Back([]), which=lambda c: None)
ok(r is None and "no tengo" in _t, "un programa que no tengo: lo dice")

# ---------- la pantalla, el núcleo y el instalador ----------
import escritorio_kira as ek
esc = ek.EscritorioMixin()
esc.back_acc = back
esc.preguntar_por_dentro = cerebro_pasos
esc.voz_activa = False
esc.cli = None
t = {"estado": "pensando", "respuesta": "", "lineas": [], "pedir_clave": None}
esc._contestar(t, "maneja gimp por dentro: exporta la imagen como png")
ok(t.get("abrir") == "taller" and "EXPERIMENTAL" in t["respuesta"], "la barra de KiraOS lo prepara y abre el Taller")
import nucleo_portatil as npo


class Core:
    dir = os.environ["KIRA_DATOS_NUCLEO"]


r = npo.ejecutar(Core(), "maneja gimp por dentro: exporta", lambda *a: None)
ok("pantalla del portátil" in r["texto"], "desde el móvil/la red: dice que es de la pantalla del portátil")
ins = open(os.path.join(RAIZ, "kira_portatil", "instalar_portatil.sh"), encoding="utf-8").read()
ok("python3-pyatspi" in ins and "toolkit-accessibility true" in ins and "imagemagick" in ins,
   "el instalador pone la accesibilidad e ImageMagick")
ok("maneja gimp por dentro" in tp.texto_ventana({}), "la ventana vacía explica las dos formas")

print(f"\n{'TODO BIEN' if not fallos else str(fallos) + ' FALLOS'} ({n})")
sys.exit(1 if fallos else 0)
