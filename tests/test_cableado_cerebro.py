"""Cableado: pantalla «Cerebro y oído», oído propio escuchando en todas las pantallas y texto que va apareciendo."""
import sys, os, tempfile, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import inicio_kira as ik
class VozMuda:
    def __init__(s, *a, **k): s.dichos = []; s.error = ""
    def puede_hablar(s): return True
    def puede_escuchar(s): return False
    def hablando(s): return False
    def hablar(s, t): s.dichos.append(t); return True
    def iniciar_escucha(s, idioma="es-ES"): return False, "no"
    def sondear(s): return "error", ""
    def parar_escucha(s): pass
VOZ = VozMuda(); ik.Voz = lambda *a, **k: VOZ
class OidoFalso:
    def __init__(s): s.cb, s.pausas, s.estado, s.encendidos, s.mensaje = None, [], "apagado", 0, ""
    def disponible(s): return True
    def modelo_instalado(s): return True
    def libreria_disponible(s): return True
    def encender(s, al_frase, al_estado=None): s.cb, s.estado = al_frase, "escuchando"; s.encendidos += 1; return True, "ok"
    def pausar(s, si): s.pausas.append(si)
    def apagar(s): s.estado = "apagado"
    def oye(s, texto):                                  # como si llegara desde el hilo de Java
        threading.Thread(target=s.cb, args=(texto,)).start()
import kira_god
core = kira_god.KiraGodCore()
OIDO = OidoFalso(); core.oido = OIDO
charlas = []
def conversar(t, h=(), al_trozo=None):
    charlas.append(t)
    if al_trozo:
        for parcial in ("Claro", "Claro, son", "Claro, son las ocho"):
            al_trozo(parcial); time.sleep(0.15)
    return "Claro, son las ocho."
core.conversar = conversar
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
def labels(raiz=None): return [w.text for w in (raiz or sm).walk() if type(w).__name__ == "Label"]
def boton(txt, raiz):
    return next(w for w in raiz.walk() if type(w).__name__ == "Button" and txt in w.text)
def correr(seg=2.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.1)
        if cond and cond(): return True
        time.sleep(0.01)
    return bool(cond and cond())

correr(1.5)
ok(OIDO.encendidos == 1 and OIDO.cb is not None, "con oído propio, la escucha permanente lo usa")
ok(any("oído propio" in l for l in labels()), "lo dice en la portada")
ok(any("no tengo cerebro" in l and "Cerebro y oído" in l for l in labels()), "sin cerebro: explica dónde conseguirlo")
# texto que va apareciendo
OIDO.oye("Kira cuéntame un cuento")
burbuja = lambda: [l for l in labels(sm.get_screen("inicio")) if "Claro" in l]
ok(correr(3, lambda: any(l.endswith("…") and "Claro" in l for l in burbuja())), "la respuesta aparece mientras piensa")
ok(correr(3, lambda: "Claro, son las ocho." in burbuja()), "y al final queda entera")
ok(charlas == ["cuéntame un cuento"], "la orden llega al cerebro")
ok(correr(2, lambda: any("las ocho" in d for d in VOZ.dichos)), "y la dice en voz alta")
ok(True not in OIDO.pausas, "v2.27: mientras piensa y habla el oído SIGUE (para oír «para» y «cancela»)")
# en cualquier pantalla
sm.ir("juegos"); correr(0.5); OIDO.pausas.clear()
OIDO.oye("hablando de otra cosa"); correr(1)
ok(sm.current == "juegos" and len(charlas) == 1, "sin su nombre no hace nada, aunque esté en otra pantalla")
OIDO.oye("Kira cuéntame algo")
ok(correr(3, lambda: "cuéntame algo" in charlas), "te oye desde otra pantalla y atiende la orden")
ok(sm.current == "juegos", "contesta AHÍ, sin llevarte a su botón (bocadillo flotante)")
sm.ir("jugar"); correr(0.6); ok(OIDO.pausas and OIDO.pausas[-1] is True, "jugando, el oído se pausa")

# pantalla cerebro y oído
sm.ir("menu"); tiles = [w.text for w in sm.walk() if type(w).__name__ == "Button" and "[b]" in w.text]
ok(any("Cerebro y oído" in t for t in tiles), "«Cerebro y oído» en el menú principal")
sm.ir("cerebro_kira"); pc = sm.get_screen("cerebro_kira"); Clock.correr(3, 0.5)
ok(any("Descargar ligero (1.4 GB)" == w.text for w in pc.walk() if type(w).__name__ == "Button"), "botón de descarga del ligero")
ok(any("Descargar listo (3.0 GB)" == w.text for w in pc.walk() if type(w).__name__ == "Button"), "botón del listo")
ok(any("Cerebro propio" in l and "sin descargar" in l for l in labels(pc)), "estado del cerebro")
ok(boton("Encender", pc).disabled and boton("Apagar", pc).disabled, "sin modelo no se puede encender")
ok(any("Oído instalado" in l for l in labels(pc)), "estado del oído")
b = boton("Usar oído propio", pc); antes = b.text; b.press(); Clock.correr(2, 0.5)
ok(b.text != antes and OIDO.estado == "apagado", "se puede volver al reconocedor de Android")
b.press(); Clock.correr(2, 0.5); ok(OIDO.estado == "escuchando", "y otra vez al oído propio")
# descargar (con una descarga falsa e instantánea)
import cerebro_propio_kira as cp
cp.MODELOS["ligero"] = dict(cp.MODELOS["ligero"], bytes=1000)
core.cerebro_propio._abrir = lambda req, timeout=60: type("R", (__import__("io").BytesIO,), {"status": 200, "__enter__": lambda s: s, "__exit__": lambda s, *a: False})(b"x" * 1000)
boton("Descargar ligero", pc).press()
ok(correr(3, lambda: core.cerebro_propio.modelo_instalado("ligero")), "descarga el modelo desde la pantalla")
Clock.correr(3, 0.5)
ok(any("Usando Qwen3.5 2B" in w.text for w in pc.walk() if type(w).__name__ == "Button"), "y lo marca como en uso")
print("CABLEADO CEREBRO OK", n)
