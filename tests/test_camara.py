"""Cámara y ojos: foto sin guardar, leer un papel, describir con los ojos, permisos, segundo plano, --mmproj."""
import sys, os, tempfile, time, json, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import camara_kira as ck, lector_kira as lk, cerebro_ia_kira as ci, cerebro_propio_kira as cp
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

class CamFalsa:
    def __init__(s): s.permiso, s.fotos, s.pedido, s.fallo = False, [], 0, ""
    def tiene_permiso(s): return s.permiso
    def pedir_permiso(s, al=None): s.pedido += 1
    def hay_camara(s, trasera=True): return True
    def foto(s, ruta, trasera=True, max_lado=1600):
        if s.fallo: return s.fallo
        open(ruta, "wb").write(b"\xff\xd8" + b"j" * 500); s.fotos.append((ruta, trasera)); return ""
def tsv_de(lineas):
    filas = ["level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"]
    for i, l in enumerate(lineas):
        x = 10
        for k, w in enumerate(l.split()):
            filas.append(f"5\t1\t1\t1\t{i+1}\t{k+1}\t{x}\t{20 + i * 30}\t{len(w) * 10}\t20\t95\t{w}"); x += len(w) * 10 + 10
    return "\n".join(filas)
L = lk.Lector(T, motor=lambda r, td, i: tsv_de(["Leche huevos pan", "y tomates"]))
os.makedirs(L.tessdata, exist_ok=True)
for i in lk.IDIOMAS:
    open(os.path.join(L.tessdata, i + ".traineddata"), "wb").write(b"t" * 200_000)

# ---------- lógica ----------
J = CamFalsa(); C = ck.Camara(T, J)
try:
    C.leer(L); ok(False, "sin permiso")
except ck.CamaraError as e:
    ok("permiso" in str(e), "sin permiso no hace foto")
J.permiso = True
ok("Leche huevos pan" in C.leer(L), "lee lo que enfoca la cámara")
ok(J.fotos and not os.path.exists(J.fotos[-1][0]) and J.fotos[-1][1] is True, "usa la de atrás y BORRA la foto")
ok(C.describir(lambda r, p: "Una mesa con una taza." if os.path.isfile(r) else "?", trasera=False) == "Una mesa con una taza.",
   "describe con los ojos (mientras la foto existe)")
ok(J.fotos[-1][1] is False and not os.path.exists(J.fotos[-1][0]), "con la de delante, y también la borra")
ok(ck.quiere_delantera("qué tengo delante con la cámara frontal") and not ck.quiere_delantera("lee este papel"),
   "entiende «frontal»")
J.fallo = "otra app está usando la cámara"
try:
    C.leer(L); ok(False, "fallo")
except ck.CamaraError as e:
    ok("otra app" in str(e), "explica por qué falló la foto")
J.fallo = ""
C.primer_plano = lambda: False
try:
    C.leer(L); ok(False, "segundo plano")
except ck.CamaraError as e:
    ok("abre Kira" in str(e), "en segundo plano no usa la cámara (Android no deja)")
C.primer_plano = lambda: True
ok(not ck.Camara(T, None).disponible(), "en el PC no hay cámara")

# ---------- ojos: la imagen va al modelo local ----------
enviado = {}
class Resp(io.BytesIO):
    status = 200
    def __enter__(s): return s
    def __exit__(s, *a): return False
def abrir(req, timeout=60):
    enviado["cuerpo"] = json.loads(req.data.decode())
    return Resp(json.dumps({"choices": [{"message": {"content": "Veo un papel con una lista."}}]}).encode())
ia = ci.Cerebro(T, abrir=abrir)
img = os.path.join(T, "x.jpg"); open(img, "wb").write(b"\xff\xd8" + b"z" * 50)
ok(ia.ver_imagen(img, "¿Qué es?") == "Veo un papel con una lista.", "ver_imagen devuelve lo que ve")
cont = enviado["cuerpo"]["messages"][-1]["content"]
ok(cont[0]["type"] == "image_url" and cont[0]["image_url"]["url"].startswith("data:image/jpeg;base64,"), "manda la foto")
ok(cont[1]["text"] == "¿Qué es?", "y la pregunta")

# ---------- --mmproj ----------
d = tempfile.mkdtemp(); P = cp.CerebroPropio(d, salud=lambda: True)
ok(not P.ojos_instalados() and "--mmproj" not in P._argumentos("motor"), "sin ojos no se cargan")
os.makedirs(P.carpeta_modelos, exist_ok=True)
cp.MODELOS[P.modelo] = dict(cp.MODELOS[P.modelo], ojos=dict(cp.MODELOS[P.modelo]["ojos"], bytes=10))
open(P.ruta_ojos(), "wb").write(b"o" * 10)
a = P._argumentos("motor")
ok(P.ojos_instalados() and a[a.index("--mmproj") + 1] == P.ruta_ojos(), "con ojos, el motor arranca con --mmproj")
ok("--mmproj" not in P._argumentos("motor", ojos=False), "y se puede arrancar sin ellos (si no caben)")
# si con ojos no arranca, prueba sin ellos
cp.MODELOS[P.modelo] = dict(cp.MODELOS[P.modelo], bytes=5)
open(P.ruta_modelo(), "wb").write(b"m" * 5)
class Proc:
    def __init__(s, args): s.args, s.pid = args, None; s.muerto = "--mmproj" in args
    def poll(s): return 1 if s.muerto else None
    def terminate(s): s.muerto = True
    def wait(s, timeout=None): return 0
    def kill(s): s.muerto = True
lanzados = []
P2 = cp.CerebroPropio(d, carpeta_binarios=d, lanzar=lambda a, **k: (lanzados.append(a), Proc(a))[1], salud=lambda: True)
open(os.path.join(d, cp.BINARIOS[0]), "wb").write(b"#")
ok(P2.encender(espera=1) and not P2.ojos_cargados and any("--mmproj" in a for a in lanzados),
   "si con ojos no cabe en memoria, arranca sin ellos")
P2.apagar()

# ---------- órdenes ----------
import kira_god
core = kira_god.KiraGodCore()
J2 = CamFalsa(); core.camara = ck.Camara(T, J2); core.lector = L
r = core.procesar_orden("lee este papel")
ok("permiso" in r and J2.pedido == 1, "sin permiso: te lo pide")
J2.permiso = True
r = core.procesar_orden("lee este papel")
ok("Con la cámara leo" in r and "tomates" in r, "«lee este papel»")
r = core.procesar_orden("qué tengo delante")
ok("tomates" in r and "descarga tus ojos" in r, "sin ojos: lee las letras y dice cómo conseguir los ojos")
core.cerebro_propio.con_ojos = lambda: True
core.cerebro_ia.ver_imagen = lambda ruta, p: "Tienes una lista de la compra." if os.path.isfile(ruta) else "?"
ok(core.procesar_orden("qué tengo delante") == "Tienes una lista de la compra.", "con ojos: describe lo que tienes delante")
ok(core.procesar_orden("describe lo que ves con la cámara frontal") == "Tienes una lista de la compra."
   and J2.fotos[-1][1] is False, "con la frontal")
ok(all(not os.path.exists(f) for f, _ in J2.fotos), "ninguna foto queda guardada")
core.en_segundo_plano = True
ok("abre Kira" in core.procesar_orden("lee este papel"), "en segundo plano lo explica")
core.en_segundo_plano = False
core.cerebro_propio.con_ojos = lambda: False
ok("ojos" in core.procesar_orden("ojos").lower(), "«ojos» dice si los tiene")
ok("cerebro" in core.procesar_orden("descarga tus ojos").lower(), "sin cerebro, los ojos no se pueden descargar")
print("CAMARA OK", n)
