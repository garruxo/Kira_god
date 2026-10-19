"""Sin oído descargado: Kira NO usa el reconocedor de Android (pitidos); se descarga su oído sola y luego escucha."""
import sys, os, tempfile, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import inicio_kira as ik
class VozAndroid:
    def __init__(s, *a, **k): s.dichos = []; s.error = ""; s.escuchas = 0
    def puede_hablar(s): return True
    def puede_escuchar(s): return True
    def hablando(s): return False
    def hablar(s, t): s.dichos.append(t); return True
    def iniciar_escucha(s, idioma="es-ES"): s.escuchas += 1; return True, "ok"
    def sondear(s): return "escuchando", ""
    def parar_escucha(s): pass
VOZ = VozAndroid(); ik.Voz = lambda *a, **k: VOZ
class OidoSinModelo:
    def __init__(s): s.cb, s.pausas, s.estado, s.mensaje, s.bajado, s.descargas = None, [], "apagado", "", False, 0
    def libreria_disponible(s): return True
    def modelo_instalado(s): return s.bajado
    def disponible(s): return s.bajado
    def descargar_modelo(s, progreso=None):
        s.estado = "descargando"; s.descargas += 1; time.sleep(0.3); s.bajado = True; s.estado = "apagado"
    def encender(s, al_frase, al_estado=None): s.cb, s.estado = al_frase, "escuchando"; return True, "ok"
    def pausar(s, si): s.pausas.append(si)
    def apagar(s): s.estado = "apagado"
import kira_god
core = kira_god.KiraGodCore()
OIDO = OidoSinModelo(); core.oido = OIDO
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
def correr(seg, cond):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.1)
        if cond(): return True
        time.sleep(0.01)
    return cond()
correr(0.5, lambda: False)
labels = lambda: [w.text for w in sm.walk() if type(w).__name__ == "Label"]
ok(any("descargando mi oído" in l for l in labels()) or OIDO.descargas == 1, "avisa de que se descarga el oído " + repr([l for l in labels() if "oí" in l or "scuch" in l]))
ok(correr(4, lambda: OIDO.estado == "escuchando"), "al terminar, escucha con su oído propio")
correr(1, lambda: False)
ok(VOZ.escuchas == 0, "nunca ha usado el reconocedor de Android (sin pitidos)")
ok(OIDO.descargas == 1, "lo descarga una sola vez")
print("OIDO AUTO OK", n)
