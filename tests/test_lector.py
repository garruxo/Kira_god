# -*- coding: utf-8 -*-
"""Lector de capturas: maquetación (sangría del código, líneas en blanco), descarga de idiomas, órdenes y pantalla."""
import io, os, shutil, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import lector_kira as lk, ejecutor_kira as ej
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

CODIGO = '''def buscar(lista, x):
    izq, der = 0, len(lista) - 1
    while izq <= der:
        mitad = (izq + der) // 2
        if lista[mitad] == x:
            return mitad
        if lista[mitad] < x:
            izq = mitad + 1
        else:
            der = mitad - 1
    return -1

print(buscar([1, 3, 5, 7], 5))'''
TEXTO = "Kira, recuerda que el jueves tengo cita\ncon el médico a las 10:30 en la calle Mayor."

def captura(ruta, lineas, oscuro=True, x=60, titulo=True):
    from PIL import Image, ImageDraw, ImageFont
    mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 30)
    im = Image.new("RGB", (1080, 120 + 52 * len(lineas)), (30, 32, 40) if oscuro else (250, 250, 252))
    d = ImageDraw.Draw(im)
    if titulo:
        d.text((24, 18), "buscar.py - Editor", font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26),
               fill=(200, 200, 210) if oscuro else (60, 60, 70))
    for i, l in enumerate(lineas):
        d.text((x, 90 + i * 52), l, font=mono, fill=(220, 225, 235) if oscuro else (20, 20, 25))
    im.save(ruta)
def tesseract(ruta, tessdata=None, idiomas=None):
    return subprocess.run(["tesseract", ruta, "stdout", "-l", "eng", "tsv"], capture_output=True, text=True).stdout

# ---------- maquetación con TSV sintético ----------
def palabra(b, p, l, x, w, t, top, h=22, conf=95):
    return "\t".join(map(str, (5, 1, b, p, l, 1, x, top, w, h, conf, t)))
tsv = "\n".join([palabra(1, 1, 1, 24, 200, "Título", 10),
                 palabra(2, 1, 1, 60, 54, "def", 62), palabra(2, 1, 1, 132, 90, "f():", 62),
                 palabra(3, 1, 1, 132, 108, "return", 114), palabra(3, 1, 1, 258, 18, "1", 114),
                 palabra(4, 1, 1, 60, 108, "print(f())", 218)])
t = lk.maquetar(lk.leer_tsv(tsv))
ok(t.splitlines() == ["Título", "def f():", "    return 1", "", "print(f())"], "sangría y línea en blanco: " + repr(t))
ok(lk.maquetar([]) == "", "nada que maquetar")
ok(lk.limpiar_codigo("print(“hola”) — ‘x’") == "print(\"hola\") - 'x'", "arregla comillas y guiones")
ok(lk.parece_codigo(["def f():", "    return x[0]", "print(f())"]) and not lk.parece_codigo(["Hola, ¿qué tal?", "Bien."]), "distingue código de texto")

# ---------- con Tesseract de verdad (si está instalado) ----------
if shutil.which("tesseract"):
    D = tempfile.mkdtemp()
    captura(os.path.join(D, "c1.png"), CODIGO.splitlines())
    r = lk.maquetar([p for p in lk.leer_tsv(tesseract(os.path.join(D, "c1.png"))) if p[5] >= 20])
    ok(r.split("\n", 1)[1].strip() == CODIGO.strip(), "captura de un editor oscuro: el código sale idéntico")
    ok(ej.ejecutar(r.split("\n", 1)[1])["salida"].strip() == "2", "y se puede ejecutar")
    captura(os.path.join(D, "c2.png"), CODIGO.splitlines(), oscuro=False, x=140, titulo=False)
    r = lk.maquetar([p for p in lk.leer_tsv(tesseract(os.path.join(D, "c2.png"))) if p[5] >= 20])
    ok(r.strip() == CODIGO.strip(), "fondo claro y otro margen: también idéntico")
    captura(os.path.join(D, "t.png"), TEXTO.splitlines(), oscuro=False, titulo=False)
    r = lk.maquetar([p for p in lk.leer_tsv(tesseract(os.path.join(D, "t.png"))) if p[5] >= 20])
    ok("recuerda que el jueves" in r and "10:30" in r and len(r.splitlines()) == 2, "lee texto normal")
else:
    print("   (sin tesseract en este equipo: se omiten las capturas reales)")

# ---------- última captura ----------
C = tempfile.mkdtemp()
for i, nombre in enumerate(("a.png", "b.jpg", "notas.txt")):
    open(os.path.join(C, nombre), "w").close(); os.utime(os.path.join(C, nombre), (1000 + i, 1000 + i))
ok(lk.ultima_captura([C, "/no/existe"]) == os.path.join(C, "b.jpg"), "encuentra la captura más reciente")
ok(lk.ultima_captura(["/no/existe"]) is None, "sin capturas")

# ---------- descarga de idiomas ----------
class Resp(io.BytesIO):
    status = 200
    def __enter__(s): return s
    def __exit__(s, *a): return False
L = lk.Lector(T, abrir=lambda req, timeout=60: Resp(b"t" * 200_000), motor=lambda r, td, i: tsv)
ok(not L.idiomas_instalados(), "sin idiomas")
L.descargar_idiomas(); ok(L.idiomas_instalados() and L.disponible(), "descarga español e inglés")
try:
    lk.Lector(tempfile.mkdtemp(), abrir=lambda req, timeout=60: Resp(b"<html>error</html>")).descargar_idiomas(); ok(False, "archivo malo")
except lk.LectorError:
    ok(True, "rechaza un idioma que no es válido")
img = os.path.join(C, "b.jpg")
ok(L.leer(img).startswith("Título") and L.ultimo.startswith("Título"), "lee y recuerda lo último leído")
try:
    L.leer("/no/existe.png"); ok(False, "imagen inexistente")
except lk.LectorError:
    ok(True, "imagen inexistente")
vacio = lk.Lector(T, motor=lambda r, td, i: "")
try:
    vacio.leer(img); ok(False, "sin texto")
except lk.LectorError as e:
    ok("No veo texto" in str(e), "imagen sin texto")

# ---------- órdenes ----------
import kira_god
core = kira_god.KiraGodCore()
core.lector = lk.Lector(T, motor=lambda r, td, i: tsv)
lk.ultima_captura = lambda carpetas=None: img
r = core.procesar_orden("lee la última captura")
ok("He leído tu última captura" in r and "print(f())" in r, "«lee la última captura»")
ok("Guardado en mi baúl" in core.procesar_orden("guarda lo leído") and core.recuerdos.buscar("print")[0]["fuente"] == "captura", "«guarda lo leído»")
ok("cerebro" in core.procesar_orden("explícame lo leído").lower() or "[x]" in core.procesar_orden("explícame lo leído"), "sin cerebro, lo dice")
core.conversar = lambda t, h=(), al_trozo=None: "Es una función que devuelve 1." if "def f()" in t else "?"
ok(core.procesar_orden("explícame lo leído") == "Es una función que devuelve 1.", "«explícame lo leído» usa el cerebro")
ok("listo" in core.procesar_orden("lector"), "estado del lector")

# ---------- pantalla ----------
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
sm.ir("menu"); ok(any("Lector" in w.text for w in sm.walk() if type(w).__name__ == "Button" and "[b]" in w.text), "Lector en el menú")
sm.ir("lector"); pl = sm.get_screen("lector")
def boton(t): return next(w for w in pl.walk() if type(w).__name__ == "Button" and w.text == t)
def esperar(c, s=4):
    t0 = time.time()
    while time.time() - t0 < s:
        Clock.correr(1, 0.1)
        if c(): return True
        time.sleep(0.01)
    return False
ok(boton("Descargar el lector (6 MB)").disabled, "ya descargado: botón desactivado")
boton("Leer la última captura").press()
ok(esperar(lambda: any("print(f())" in w.text for w in pl.walk() if type(w).__name__ == "Label")), "lee desde la pantalla")
boton("Abrir en el editor").press()
area = next(w for w in sm.get_screen("editor_codigo").walk() if type(w).__name__ == "TextInput" and getattr(w, "multiline", False))
ok(sm.current == "editor_codigo" and "    return 1" in area.text, "abre lo leído en el editor, con su sangría")
sm.ir("inicio"); campo = next(w for w in sm.walk() if type(w).__name__ == "TextInput" and "Escríbele" in getattr(w, "hint_text", ""))
campo.text = "abre lo leído en el editor"; next(w for w in sm.walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
ok(sm.current == "editor_codigo", "también por voz o texto: «abre lo leído en el editor»")
print("LECTOR OK", n)
