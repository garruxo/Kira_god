# -*- coding: utf-8 -*-
"""El pintor de Kira (v2.18): pedidos, prompt en inglés, progreso del motor, pintar con un motor FALSO (el de verdad,
stable-diffusion.cpp, va en el APK y se prueba con modelos reales en GitHub: .github/workflows/probar_pintor.yml),
descargas con reanudación, memoria y la pantalla «Pintor» (Kivy simulado)."""
import base64, io, os, stat, struct, sys, tempfile, time, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import pintor_kira as pk, descargas_kira as dsc
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- pedidos ----------
P = pk.pedido_imagen
ok(P("pinta un faro en una isla al atardecer") == "un faro en una isla al atardecer", "pinta…")
ok(P("hazme una foto de un gato astronauta") == "foto de un gato astronauta", "hazme una foto de…")
ok(P("créame una imagen de una ciudad futurista de noche") == "una ciudad futurista de noche", "crea una imagen de…")
ok(P("dibújame un dragón") == "un dragón", "dibuja (con pincel)")
ok(P("dibuja una playa al atardecer", siempre_dibuja=False) is None, "sin pincel, «dibuja» sigue siendo el lienzo de siempre")
ok(P("dibuja una imagen de una playa", siempre_dibuja=False) == "una playa", "pero «dibuja una imagen…» es del pintor")
ok(P("hazme un juego de naves") is None and P("hazme una web para mi bar") is None and P("crea una función") is None,
   "juegos, webs y mejoras no son imágenes")
ok(P("pinta") is None and P("hola") is None, "lo demás no")

# ---------- estilo, formato y prompt ----------
ok(pk.estilo_de("una acuarela de un velero") == "acuarela" and pk.estilo_de("un gato estilo anime") == "anime", "estilos")
ok(pk.estilo_de("un faro al atardecer") == "foto", "por defecto, foto realista")
ok(pk.formato_de("un fondo de pantalla de montañas") == "vertical" and pk.formato_de("un paisaje horizontal") == "horizontal"
   and pk.formato_de("un perro") == "cuadrada", "formatos")
ok(pk.traducir_simple("un gato negro durmiendo en la playa") == "cat black sleeping in beach", "diccionario de emergencia")
pr = pk.preparar("un faro en una isla al atardecer", lambda t: "Prompt: a lighthouse on an island at sunset, golden light")
ok(pr["prompt"].startswith("a lighthouse on an island at sunset, golden light, realistic photo") and pr["ingles_por"] == "cerebro",
   "prompt en inglés con el cerebro + estilo: " + pr["prompt"])
pr = pk.preparar("una acuarela de un velero", lambda t: (_ for _ in ()).throw(RuntimeError("sin red")))
ok(pr["ingles_por"] == "diccionario" and "watercolor" in pr["prompt"] and pr["estilo"] == "acuarela", "si el cerebro falla, diccionario")
pr = pk.preparar("un perro", lambda t: "un perro bonito")
ok(pr["ingles_por"] == "diccionario" or "dog" in pr["prompt"], "si el cerebro contesta en español, no se fía")

# ---------- progreso del motor ----------
pg = pk.Progreso(4)
pg.leer("[INFO ] stable-diffusion.cpp:725 - loading model from 'm.gguf'\n")
f1 = pg.fraccion
pg.leer("\r|=====>    | 3/6 - 120.00MB/s\033[K")
pg.leer("\n[INFO ] get_learned_condition completed, taking 0.10s\n")
pg.leer("\r|==>       | 1/4 - 2.50s/it\033[K")
f2, t2 = pg.leer("\r|=====>    | 2/4 - 2.40s/it\033[K")
ok(f1 < f2 and "paso 2 de 4" in t2, f"pasos ({f2:.2f}, {t2})")
pg.leer("\r|==========| 4/4 - 2.40s/it\033[K\n[INFO ] sampling completed, taking 9.6s\n")
f3, t3 = pg.leer("[INFO ] decoding 1 latents\n")
ok(f3 > 0.85 and "Revelando" in t3, "revelar")
f4, _ = pg.leer("[INFO ] decode_first_stage completed, taking 1.2s\n")
ok(f4 >= f3 and f4 < 1.0, "nunca retrocede y no llega al 100 % hasta acabar")

# ---------- motor FALSO ----------
def png(w=40, h=40):
    filas = b"".join(b"\x00" + bytes((x * 7 + y * 3) % 256 for x in range(w * 3)) for y in range(h))
    def trozo(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + \
        trozo(b"IDAT", zlib.compress(filas)) + trozo(b"IEND", b"")
PNG64 = base64.b64encode(png()).decode()
MOTOR = f'''#!{sys.executable}
import base64, os, sys, time, signal
a = sys.argv[1:]
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ultimos_args.txt"), "w").write("\\n".join(a))
def arg(k, d=None): return a[a.index(k) + 1] if k in a else d
if os.environ.get("PINTOR_FALSO") == "memoria":
    print("[ERROR] ggml.c - failed to allocate buffer: out of memory", flush=True); sys.exit(1)
if os.environ.get("PINTOR_FALSO") == "lento":
    time.sleep(30)
PNG = base64.b64decode("{PNG64}")
out = arg("-o")
if arg("-M") == "upscale":
    print("[INFO ] upscaling from (40 x 40) to (160 x 160)", flush=True)
    open(out, "wb").write(PNG); sys.exit(0)
print("[INFO ] stable-diffusion.cpp:725 - loading model from '%s'" % arg("-m"), flush=True)
for i in range(1, 4):
    sys.stdout.write("\\r|=====| %d/3 - 120.00MB/s\\033[K" % i); sys.stdout.flush()
print("\\n[INFO ] get_learned_condition completed, taking 0.10s", flush=True)
pasos = int(arg("--steps", "1"))
for i in range(1, pasos + 1):
    sys.stdout.write("\\r|====| %d/%d - 1.50s/it\\033[K" % (i, pasos)); sys.stdout.flush()
    if arg("--preview-path"): open(arg("--preview-path"), "wb").write(PNG)
    time.sleep(0.05)
print("\\n[INFO ] sampling completed, taking 0.3s", flush=True)
print("[INFO ] decode_first_stage completed, taking 0.1s", flush=True)
open(out, "wb").write(PNG)
print("[INFO ] save result image to '%s'" % out, flush=True)
'''
MALO_DP = f'''#!{sys.executable}
import os, signal
os.kill(os.getpid(), signal.SIGILL)
'''
BIN = os.path.join(T, "bin"); os.makedirs(BIN)
def poner(nombre, texto):
    r = os.path.join(BIN, nombre); open(r, "w").write(texto); os.chmod(r, os.stat(r).st_mode | stat.S_IEXEC); return r
poner("libkira_pintor_dp.so", MALO_DP)
poner("libkira_pintor.so", MOTOR)

pin = pk.Pintor(os.path.join(T, "datos"), carpeta_binarios=BIN, memoria=lambda: 8000)
ok(pin.tiene_motor() and not pin.instalados(), "motor sí, pinceles no")
try: pin.pintar("a cat"); ok(False, "sin pincel")
except pk.PintorError as e: ok("descárgalo" in str(e), "sin pincel lo dice: " + str(e))
os.makedirs(pin.carpeta_modelos, exist_ok=True)
for k, m in pk.MODELOS.items():                         # pinceles «descargados» (archivos dispersos del tamaño exacto)
    with open(pin.ruta_modelo(k), "wb") as f: f.truncate(m["bytes"])
ok(not pin.instalado("realista"), "el realista necesita también su revelador (TAESD)")
open(pin.ruta_taesd("realista"), "wb").write(b"t" * 1000)
ok(pin.instalados() == ["rapido", "realista"], "pinceles listos")
progresos = []
r = pin.pintar("a lighthouse, realistic photo", "realista", "vertical", semilla=1234,
               al_progreso=lambda f, t: progresos.append((round(f, 2), t)), vista=os.path.join(T, "vista.png"))
ok(os.path.isfile(r["ruta"]) and r["semilla"] == 1234 and r["modelo"] == "realista", "pinta (con el genérico: el _dp no arranca)")
ok(os.path.join(BIN, "libkira_pintor_dp.so") in pin.binario_malo, "aparta el motor rápido si el móvil no lo soporta")
args = open(os.path.join(BIN, "ultimos_args.txt")).read().split("\n")
ok(args[args.index("-W") + 1] == "448" and args[args.index("-H") + 1] == "640" and args[args.index("--steps") + 1] == "4",
   "formato vertical y 4 pasos (realista)")
ok(args[args.index("--taesd") + 1].endswith("taesd.safetensors"), "el realista lleva su revelador")
ok("--mmap" in args and "--preview" in args and args[args.index("-s") + 1] == "1234" and "-n" not in args,
   "memoria mapeada, vista previa y semilla (sin negativo con cfg 1)")
fr = [f for f, _ in progresos]
ok(fr == sorted(fr) and fr[-1] == 1.0 and any("paso 4 de 4" in t for _, t in progresos), "el progreso avanza hasta el final")
r2 = pin.pintar("a cat", "rapido")
args = open(os.path.join(BIN, "ultimos_args.txt")).read().split("\n")
ok(args[args.index("--steps") + 1] == "1" and "--preview" not in args, "pincel rápido: 1 paso, sin vista previa")
ok(pin.imagenes()[0] == r2["ruta"] and len(pin.imagenes()) == 2, "sus imágenes, la última primero")
os.environ["PINTOR_FALSO"] = "memoria"
try: pin.pintar("a cat", "rapido"); ok(False, "memoria")
except pk.PintorError as e: ok("faltó memoria" in str(e), "sin memoria: lo dice y aconseja: " + str(e))
os.environ["PINTOR_FALSO"] = "lento"
t0 = time.time()
threading = __import__("threading")
threading.Timer(0.6, pin.cancelar).start()
try: pin.pintar("a cat", "rapido"); ok(False, "cancelar")
except pk.PintorError as e: ok("Cancelado" in str(e) and time.time() - t0 < 5, "se puede parar")
os.environ.pop("PINTOR_FALSO")
# ampliar
try: pin.ampliar(r2["ruta"]); ok(False, "sin ampliador")
except pk.PintorError as e: ok("ampliador" in str(e), "ampliar sin el ampliador lo dice")
open(pin.ruta_ampliador(), "wb").write(b"x" * 2_000_000)
ok(pin.ampliar(r2["ruta"]).endswith("_x4.png"), "amplía ×4")
# borrar
pin.borrar_imagen(r2["ruta"]); ok(not os.path.isfile(r2["ruta"]), "borra sus imágenes")
try: pin.borrar_imagen(os.path.join(T, "vista.png")); ok(False, "solo las suyas")
except pk.PintorError: ok(True, "solo borra imágenes pintadas por Kira")
ok("descargado" in pin.estado_texto() and "incluido" in pin.estado_texto(), "estado")

# ---------- descargas con reanudación ----------
DATOS = bytes(range(256)) * 400
class Resp:
    def __init__(s, b, status=200): s.f, s.status = io.BytesIO(b), status; s.headers = {"Content-Length": str(len(b))}
    def read(s, n=-1): return s.f.read(n)
    def __enter__(s): return s
    def __exit__(s, *a): return False
vistos = []
def red(req, timeout=0):
    rango = req.headers.get("Range")
    vistos.append(rango)
    if rango:
        desde = int(rango.split("=")[1].rstrip("-"))
        return Resp(DATOS[desde:], 206)
    return Resp(DATOS)
dest = os.path.join(T, "d", "m.bin")
os.makedirs(os.path.dirname(dest)); open(dest + ".parte", "wb").write(DATOS[:5000])
ok(dsc.bajar("https://x/m", dest, len(DATOS), abrir=red) == dest and open(dest, "rb").read() == DATOS, "reanuda donde se quedó")
ok(vistos[-1] == "bytes=5000-", "pide solo lo que falta")
dest2 = os.path.join(T, "d", "sin_tam.bin")
ok(dsc.bajar("https://x/m", dest2, None, abrir=red) and os.path.getsize(dest2) == len(DATOS), "sin tamaño conocido: el del servidor")
try: dsc.bajar("https://x/m", os.path.join(T, "d", "corto.bin"), len(DATOS) + 10, abrir=red); ok(False, "incompleta")
except dsc.DescargaError as e: ok("no está completa" in str(e), "descarga incompleta: lo dice")
viejo = dict(pk.MODELOS["rapido"])
pk.MODELOS["rapido"].update(bytes=len(DATOS), archivo="pequeno.gguf")
pin2 = pk.Pintor(os.path.join(T, "datos2"), carpeta_binarios=BIN, abrir=red)
ok(pin2.descargar("rapido") and pin2.instalado("rapido") and pin2.estado == "listo", "el pintor descarga su pincel")
pk.MODELOS["rapido"].update(viejo)

# ---------- en el núcleo: prompt con el cerebro y memoria ----------
import kira_god, cerebro_ia_kira as ci
core = kira_god.KiraGodCore()
core.pintor = pk.Pintor(os.path.join(T, "datos"), carpeta_binarios=BIN, memoria=lambda: 900)
pedidos = []
core._leer_clave = lambda *a: ci.LOCAL
core._llamar_api = lambda clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None: (
    pedidos.append((system, usuario)), "a lighthouse on a rocky island at sunset, warm light")[1]
class CerebroFalso:
    def __init__(s): s.on, s.vueltas = True, 0
    def encendido(s): return s.on
    def apagar(s): s.on = False
    def encender_en_segundo_plano(s, cb=None): s.vueltas += 1; s.on = True
core.cerebro_propio = CerebroFalso()
r = core.pintar_imagen("un faro en una isla al atardecer", modelo="realista")
ok(os.path.isfile(r["ruta"]) and r["prompt"].startswith("a lighthouse on a rocky island"), "el núcleo pinta con el prompt de su cerebro")
ok(pedidos[0][0] == pk.SISTEMA_PROMPT and "faro" in pedidos[0][1], "le pide el prompt en inglés")
ok(core.cerebro_propio.vueltas == 1 and "apartado mi cerebro" in r["aviso"], "si no cabe en la memoria, aparta el cerebro y lo vuelve a encender")
core._leer_clave = lambda *a: ""
r = core.pintar_imagen("un gato negro durmiendo", modelo="rapido")
ok("cat black sleeping" in r["prompt"] and "palabra a palabra" in r["aviso"], "sin cerebro: diccionario y lo dice")
ok(core.procesar_orden("usa el pincel realista").startswith("[OK] Pinto con el pincel realista"), "elegir pincel por orden")
ok("Pincel elegido" in core.procesar_orden("pintor"), "estado del pintor")

# ---------- la pantalla «Pintor» y la voz (Kivy simulado) ----------
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
import inicio_kira as ik
class VozMuda:
    def __init__(s): s.dichos = []
    def puede_hablar(s): return True
    def puede_escuchar(s): return False
    def hablando(s): return False
    def hablar(s, t): s.dichos.append(t); return True
    def iniciar_escucha(s, idioma="es-ES"): return False, "no"
    def sondear(s): return "error", "no"
    def parar_escucha(s): pass
VOZ = VozMuda(); ik.Voz = lambda *a, **k: VOZ
core2 = kira_god.KiraGodCore()
core2.pintor = pk.Pintor(os.path.join(T, "datos"), carpeta_binarios=BIN, memoria=lambda: 8000)
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core2)
def correr(seg=3.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.3)
        if cond and cond(): return True
        time.sleep(0.01)
    return bool(cond and cond())
def textos(nombre): return [w.text for w in sm.get_screen(nombre).walk() if isinstance(getattr(w, "text", None), str)]
correr(0.8)
campo = next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "TextInput")
campo.text = "Kira, pinta un faro en una isla al atardecer"
next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
ok(correr(3, lambda: sm.current == "pintor"), "la voz lleva al pintor")
ok(correr(8, lambda: any(t.startswith("Pintada en") for t in textos("pintor"))), "pinta y lo dice en pantalla: " + str(textos("pintor")[-6:]))
img = next(w for w in sm.get_screen("pintor").walk() if type(w).__name__ == "Image")
ok(str(img.source).endswith(".png") and os.path.isfile(img.source), "enseña la imagen")
ok(correr(2, lambda: any("Ya está" in d for d in VOZ.dichos)), "y lo dice en voz alta")
ok(any("«un faro en una isla al atardecer»" in t for t in textos("pintor")), "con lo que pediste")
boton = lambda t: next(w for w in sm.get_screen("pintor").walk() if type(w).__name__ == "Button" and w.text.startswith(t))
ok(not boton("A la galería").disabled and not boton("Otra versión").disabled, "acciones listas")
boton("A la galería").press()
ok(any("galería" in t for t in textos("pintor")), "galería: en el PC lo dice honestamente")
print("PINTOR OK", n)
