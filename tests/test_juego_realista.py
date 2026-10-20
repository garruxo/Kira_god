# -*- coding: utf-8 -*-
"""Juegos realistas (v2.22): el pintor dibuja los personajes (recortados, sin fondo) y Kira programa el juego que
los usa. PNG en Python puro, quitar el fondo, «dibujos» del programa, motor con imágenes y la voz (motor de pintar
FALSO; el de verdad se prueba en GitHub)."""
import base64, os, stat, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import sprites_kira as spk, juego_realista_kira as jr, pintor_kira as pk, motor_juegos_kira as mj
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- PNG y fondo ----------
W = H = 128
px = bytearray()
for y in range(H):
    for x in range(W):
        dentro = (x - 64) ** 2 + (y - 64) ** 2 < 30 ** 2
        px += bytes((200, 40, 40, 255) if dentro else (248, 248, 246, 255))
png = spk.escribir_png(W, H, px)
w, h, leido = spk.leer_png(png)
ok((w, h) == (W, H) and leido == px, "escribir y leer PNG (Python puro)")
sin, frac = spk.quitar_fondo(w, h, leido)
ok(sin[3] == 0 and sin[(64 * W + 64) * 4 + 3] == 255 and 0.7 < frac < 0.9, f"quita el fondo liso y deja el personaje ({frac:.2f})")
ok(spk.reducir(w, h, leido, 64)[:2] == (64, 64), "reduce")
o = os.path.join(T, "o.png"); open(o, "wb").write(png)
ok("fondo quitado" in spk.preparar_sprite(o, os.path.join(T, "s", "p.png")), "prepara un personaje")
ok(spk.preparar_sprite(o, os.path.join(T, "s", "f.png"), fondo=True) == "escenario", "el escenario no se recorta")

# ---------- qué se pide y el plan ----------
ok(jr.es_realista("juego realista de un caballero que esquiva dragones") == "un caballero que esquiva dragones", "detecta «juego realista de…»")
ok(jr.es_realista("juego de naves realista") == "naves" and jr.es_realista("juego de naves") is None, "también al final; si no, no")
pl = jr.plan_simple("un caballero que esquiva dragones y recoge monedas en un castillo", pk.traducir_simple)
ok(pl["protagonista"] == "un caballero" and pl["enemigo"] == "dragones" and pl["premio"] == "monedas"
   and pl["escenario"] == "un castillo" and pl["enemigo_en"] == "dragons", "plan sacado de la frase: " + repr(pl))
ok(jr.plan_desde_ia('Aquí va: {"titulo": "Caballero", "protagonista": "caballero", "enemigo_en": "a red dragon"}')["enemigo_en"]
   == "a red dragon", "plan de la IA (con valores por defecto si falta algo)")
d = jr.dibujos(pl)
ok(set(d) == {"fondo", "jugador", "enemigo", "premio"} and "white background" in d["jugador"] and "no characters" in d["fondo"],
   "personajes sobre fondo blanco (para recortarlos) y escenario sin personajes")
programa = jr.codigo(pl)
ok(spk.dibujos_de(programa) == (pl["carpeta"], {k: v for k, v in d.items()}), "el programa dice qué dibujos necesita")

# ---------- el juego funciona (en modo seguro) ----------
import juegos_kira as jk
juego, error = jk.cargar(programa, semilla=1)
ok(juego is not None, f"el programa se carga en modo seguro: {error}")
for i in range(60 * 8):
    if i % 20 == 0:
        juego.tocar(40 + (i * 7) % 280, 60)
    juego.paso(1 / 60)
    if juego.estado == "fin":
        juego.tocar(10, 10)
formas = {x[0] for x in juego.dibujo()}
ok("imagen" in formas and all(f in mj.FORMAS for f in formas), "dibuja con imágenes (el motor las conoce)")
import laboratorio_movil_kira as lm
modulo = ("def registrar():\n    def crear(motor):\n" + "\n".join("        " + l for l in
          programa.replace("from motor_juegos_kira import Juego", "Juego = motor.Juego").splitlines()) +
          "\n        return JuegoRealista\n    return {'juego caballero': crear}\n")
r = lm.LaboratorioMovil().probar("caballero", modulo)
ok(r["ok"], "y pasa el laboratorio del móvil como juego instalable: " + str([e for e in r["etapas"] if not e["ok"]]))

# ---------- pintar los dibujos (motor de pintar FALSO) ----------
PNG64 = base64.b64encode(png).decode()
MOTOR = f'''#!{sys.executable}
import base64, sys
a = sys.argv[1:]
out = a[a.index("-o") + 1]
print("[INFO ] loading model from 'x'", flush=True)
print("\\r|====| 1/1 - 1.00s/it", flush=True)
open(out, "wb").write(base64.b64decode("{PNG64}"))
print("[INFO ] save result image", flush=True)
'''
BIN = os.path.join(T, "bin"); os.makedirs(BIN)
r_ = os.path.join(BIN, "libkira_pintor.so"); open(r_, "w").write(MOTOR); os.chmod(r_, os.stat(r_).st_mode | stat.S_IEXEC)
import kira_god
core = kira_god.KiraGodCore()
core.pintor = pk.Pintor(os.path.join(T, "datos"), carpeta_binarios=BIN, memoria=lambda: 8000)
r = core.crear_juego_realista("un caballero que esquiva dragones y recoge monedas en un castillo")
ok("recuadros" in r["aviso"] and not r["pintados"], "sin pincel: el juego sale igual (con recuadros) y lo dice")
os.makedirs(core.pintor.carpeta_modelos, exist_ok=True)
with open(core.pintor.ruta_modelo("rapido"), "wb") as f:
    f.truncate(pk.MODELOS["rapido"]["bytes"])
pasos = []
r = core.crear_juego_realista("un caballero que esquiva dragones y recoge monedas en un castillo",
                              al_progreso=lambda f, t: pasos.append((round(f, 2), t)))
ok(not r["aviso"] and [x[0] for x in r["pintados"]] == ["fondo", "jugador", "enemigo", "premio"], "pinta los 4 dibujos")
for nombre in ("fondo", "jugador", "enemigo", "premio"):
    ok(os.path.isfile(spk.ruta(r["nombre"], nombre)), f"«{nombre}» guardado en la carpeta del juego")
w2, h2, px2 = spk.leer_png(open(spk.ruta(r["nombre"], "jugador"), "rb").read())
ok(px2[3] == 0, "el personaje queda recortado (fondo transparente)")
ok(not core.pintor.imagenes(), "los dibujos del juego no llenan «Mis imágenes»")
ok(any("Pintando «jugador» (2 de 4)" in t for _, t in pasos), "va diciendo qué pinta")
# «pinta los dibujos del juego» para un juego cualquiera
cod2 = 'from motor_juegos_kira import Juego\nclass J(Juego):\n    sprites = "mi_nave"\n    dibujos = {"nave": "a spaceship"}\n'
carpeta, dib = spk.dibujos_de(cod2)
ok(core.pintar_dibujos(carpeta, dib) == [("nave", "fondo quitado (78 %)")] or os.path.isfile(spk.ruta("mi_nave", "nave")),
   "pinta los dibujos que pide cualquier juego")

# ---------- la voz y las pantallas (Kivy simulado) ----------
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
core2.pintor = core.pintor
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core2)
def correr(seg=3.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.3)
        if cond and cond(): return True
        time.sleep(0.01)
    return bool(cond and cond())
correr(0.8)
campo = next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "TextInput")
campo.text = "Kira, hazme un juego realista de un surfista que esquiva tiburones en el mar"
next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
ok(correr(15, lambda: sm.current == "jugar"), "pinta, programa y lo pone a jugar: " + sm.current)
ok(any("¡Listo!" in d for d in VOZ.dichos), "y lo dice")
ok(os.path.isfile(spk.ruta("un_surfista", "jugador")), "con sus dibujos realistas")
textos = [getattr(w, "text", "") for w in sm.get_screen("editor_codigo").walk()]
ok(any("class JuegoRealista" in t for t in textos), "el programa queda en el editor para cambiarlo")
print("JUEGO REALISTA OK", n)
