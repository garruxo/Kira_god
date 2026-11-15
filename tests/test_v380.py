"""v3.80 (revisión de KiraOS y Kira app):
- KiraOS contesta AL MOMENTO (sin cerebro) la ayuda, la hora, la fecha y cómo apagar (antes: «háblame en el móvil»);
- «estudia la wifi» es estudiar, no mirar la WiFi;
- «abre youtube» en la pantalla de KiraOS abre esa web en el navegador; en el núcleo ya no dice «solo en el móvil»;
- desde el móvil, las órdenes que solo entiende KiraOS (instalar programas, el taller, su cerebro, sus ventanas…)
  se le pasan a KiraOS (antes se quedaban en el móvil y salía «no te entiendo»)."""
import os, sys, time, tempfile
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [R, os.path.join(R, "kira_portatil")]
os.environ["HOME"] = tempfile.mkdtemp()

FALLOS = 0
def ok(c, m):
    global FALLOS
    print(("OK   " if c else "FALLA ") + m)
    if not c:
        FALLOS += 1

import nucleo_portatil as npo
t0 = time.struct_time((2026, 11, 15, 19, 5, 0, 6, 319, 0))
ok(npo.respuesta_rapida("¿Qué hora es?", t0) == "Son las 19:05.", "la hora, al momento")
ok(npo.respuesta_rapida("kira, qué día es hoy", t0) == "Hoy es domingo, 15 de noviembre de 2026.", "la fecha")
ok(npo.respuesta_rapida("ayuda") == npo.AYUDA_KIRAOS and "«estudia python»" in npo.AYUDA_KIRAOS, "la ayuda")
ok(npo.respuesta_rapida("¿qué puedes hacer?") == npo.AYUDA_KIRAOS, "«qué puedes hacer» = la ayuda")
ok("menú K" in npo.respuesta_rapida("apaga el portátil") and "menú K" in npo.respuesta_rapida("reinicia"),
   "apagar/reiniciar: con el menú K (dos toques), nunca por una frase")
for o in ("hola", "apaga el bluetooth", "reinicia firefox", "qué hora es en Tokio"):
    ok(npo.respuesta_rapida(o) is None, f"«{o}» no es una respuesta rápida")


class Core:
    NO_RECONOCIDA = "[i] No reconozco la orden"
    def __init__(self):
        self.dir = tempfile.mkdtemp(); self.usado = False
    def conversar(self, *a, **k):
        self.usado = True
        return "x"
c = Core()
r = npo.charla_si_no_es_orden(c, "ayuda", "[i] No reconozco la orden 'ayuda'.")
ok(r["texto"] == npo.AYUDA_KIRAOS and not c.usado, "en el núcleo, «ayuda» sale sin gastar el cerebro")
npo.poner_charla_aqui(c, True)
npo.charla_si_no_es_orden(c, "qué hora es", "[i] No reconozco la orden.")
ok(not c.usado, "aunque la charla esté encendida, la hora no pasa por el cerebro")

import wifi_kira as wk
ok(wk.orden_wifi("estudia la wifi") is None and wk.orden_wifi("aprende cómo funciona la wifi") is None,
   "«estudia la wifi» no es una orden de la WiFi")
ok(wk.orden_wifi("busca redes wifi") == ("redes", None), "…y las órdenes de la WiFi siguen igual")

import escritorio_kira as esk
ok(esk.web_de_frase("abre youtube") == "https://www.youtube.com", "«abre youtube» → su web")
ok(esk.web_de_frase("abre github.com") == "https://github.com", "«abre github.com» → esa web")
ok(esk.web_de_frase("busca en google gatos").startswith("https://www.google.com/search?q="), "«busca en google X»")
ok(esk.web_de_frase("abre firefox") is None and esk.web_de_frase("abre el mapa") is None
   and esk.web_de_frase("hola") is None, "un programa, una sala o una charla no son una web")


class Mix(esk.EscritorioMixin):
    def __init__(self):
        self.cli = None; self.abierta = None; self.voz_activa = False
    def abrir_navegador(self, url, popen=None, which=None):
        self.abierta = url
        return {"ok": True, "texto": "Te la abro en el navegador."}
m = Mix()
t = {"respuesta": "", "lineas": [], "estado": ""}
m._contestar(t, "abre youtube")
ok(m.abierta == "https://www.youtube.com" and "navegador" in t["respuesta"], "la pantalla de KiraOS la abre en el navegador")

src = open(os.path.join(R, "kira_god.py"), encoding="utf-8").read()
ok("Llamar por teléfono solo lo hago desde el móvil" in src and "es_kiraos" in src.split("def _orden_fuera")[1][:900],
   "en KiraOS, el núcleo dice qué SÍ vale (no «solo funciona en el móvil»)")

import mando_kira as mk
for o in ("instala obsidian de github", "instala lo que he descargado", "descarga las dependencias de obsidian",
          "trabaja con ffmpeg: convierte a.mp4 a mp3", "abre el taller de ffmpeg", "maneja gimp por dentro: abre",
          "aumenta tu cerebro", "conoce tu entorno", "crea un botón en la wifi que diga hola",
          "pon un botón en el cuaderno que diga hola"):
    ok(mk.es_trabajo(o), f"desde el móvil, «{o}» va a KiraOS")
for o in ("hola", "trabaja con cuidado", "qué cerebro tienes", "abre youtube", "qué hora es"):
    ok(not mk.es_trabajo(o), f"«{o}» se queda en el móvil")
ok(not mk.permitida_fuera("instala obsidian de github")[0], "instalar programas, fuera de casa no")
print("TODO BIEN" if not FALLOS else f"{FALLOS} FALLOS")
sys.exit(1 if FALLOS else 0)
