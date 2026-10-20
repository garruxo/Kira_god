"""«Preparando a Kira»: oído, cerebro, lector y pantalla listos antes de empezar; cerebro reutilizado si ya estaba."""
import sys, os, tempfile, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import arranque_kira as ak
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

class Ajustes: oido_propio = True; escucha_permanente = True
class Oido:
    def __init__(s): s.estado, s.mensaje, s.progreso = "apagado", "", 0.0
    def libreria_disponible(s): return True
class Cerebro:
    def __init__(s, instalado=True): s.estado, s.progreso, s.mensaje, s.inst, s.on, s.encendidas, s.bajadas = "apagado", 0, "", instalado, False, 0, 0
    def tiene_motor(s): return True
    def encendido(s): return s.on
    def modelo_instalado(s): return s.inst
    def encender_en_segundo_plano(s, fin=None):
        s.estado = "arrancando"; s.encendidas += 1
    def descargar(s): s.bajadas += 1; s.estado = "descargando"; time.sleep(0.2); s.inst = True; s.estado = "apagado"
    def encender(s): s.on = True; s.estado = "encendido"
class Lector:
    def __init__(s): s.estado, s.inst, s.bajadas = "listo", False, 0
    def libreria_disponible(s): return True
    def idiomas_instalados(s): return s.inst
    def descargar_idiomas(s): s.bajadas += 1; s.inst = True
class Vista:
    def __init__(s): s.quiere_ver, s.siempre_activa, s.ver, s.pedidas = True, False, False, 0; s.java = object()
    def disponible(s): return True
    def puede_ver(s): return s.ver
    def pedir_ver(s, fin): s.pedidas += 1; s.ver = True; fin(True)
class IA:
    def local_disponible(s, forzar=False): return True
class Core: pass

def core_con(cerebro):
    c = Core(); c.cerebro_propio, c.lector, c.vista, c.cerebro_ia = cerebro, Lector(), Vista(), IA(); return c

# ---------- lógica ----------
O = Oido(); encendidos = []
C = core_con(Cerebro())
P = ak.Preparacion(C, O, Ajustes(), encender_oido=lambda: (encendidos.append(1), setattr(O, "estado", "escuchando")), red=lambda: True)
ok(P.hace_falta(), "hay cosas que preparar")
P.piezas(); P.piezas()
ok(len(encendidos) == 1 and C.cerebro_propio.encendidas == 1, "enciende oído y cerebro UNA vez")
ok(C.vista.pedidas == 1, "pide ya el permiso de pantalla (lo diste otra vez)")
time.sleep(0.1)
ok(C.lector.bajadas == 1, "con WiFi descarga los idiomas del lector")
ok(not P.todo_listo(), "el cerebro aún carga: no está todo listo")
ok(any(n_ == "Cerebro" and "memoria" in t for n_, t, _ in P.piezas()), "dice que está cargando el cerebro")
C.cerebro_propio.on = True
ok(P.todo_listo(), "con todo cargado, listo")
# sin WiFi: no descarga el cerebro (1,4 GB) y no bloquea
C2 = core_con(Cerebro(instalado=False)); O2 = Oido(); O2.estado = "escuchando"
P2 = ak.Preparacion(C2, O2, Ajustes(), encender_oido=lambda: None, red=lambda: False)
pz = {n_: (t, l) for n_, t, l in P2.piezas()}
ok("WiFi" in pz["Cerebro"][0] and pz["Cerebro"][1] and C2.cerebro_propio.bajadas == 0, "sin WiFi no descarga el cerebro ni espera")
ok(C2.lector.bajadas == 0, "sin WiFi no descarga los idiomas")
# con WiFi y sin cerebro: lo descarga y lo enciende
C3 = core_con(Cerebro(instalado=False))
P3 = ak.Preparacion(C3, O2, Ajustes(), encender_oido=lambda: None, red=lambda: True)
P3.piezas(); time.sleep(0.5)
ok(C3.cerebro_propio.bajadas == 1 and C3.cerebro_propio.on, "con WiFi descarga el cerebro y lo enciende")
# en el PC no hay nada que preparar
class Nada:
    def libreria_disponible(s): return False
    def tiene_motor(s): return False
    def disponible(s): return False
C4 = Core(); C4.cerebro_propio, C4.lector, C4.vista = Nada(), Nada(), Nada()
ok(not ak.Preparacion(C4, Nada(), Ajustes(), encender_oido=lambda: None).hace_falta(), "en el PC no se enseña")

# ---------- cerebro reutilizado ----------
import cerebro_propio_kira as cp, subprocess
d = tempfile.mkdtemp()
cp_ = cp.CerebroPropio(d, salud=lambda: True)
os.makedirs(os.path.dirname(cp_.ruta_modelo()), exist_ok=True); open(cp_.ruta_modelo(), "wb").write(b"x")
cp.MODELOS[cp_.modelo] = dict(cp.MODELOS[cp_.modelo], bytes=1)
vivo = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
open(cp_.ruta_pid, "w").write(f"{vivo.pid} {cp_.modelo}")
cp_.binarios = lambda: []                       # si intentara lanzar el motor, fallaría
ok(cp_.encender() and cp_.encendido(), "si el cerebro seguía cargado, lo usa al momento")
cp_.apagar(); vivo.wait(timeout=5)
ok(vivo.poll() is not None and not os.path.exists(cp_.ruta_pid), "apagarlo para el motor que seguía vivo")
open(cp_.ruta_pid, "w").write(f"999999 {cp_.modelo}")
ok(not cp_.encender() and not os.path.exists(cp_.ruta_pid), "un registro viejo (motor muerto) no se usa")

# ---------- pantalla ----------
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
    def __init__(s): s.cb, s.estado, s.mensaje, s.progreso = None, "apagado", "", 0
    def disponible(s): return True
    def modelo_instalado(s): return True
    def libreria_disponible(s): return True
    def encender(s, al_frase, al_estado=None): s.cb, s.estado = al_frase, "escuchando"; return True, "ok"
    def pausar(s, si): pass
    def apagar(s): s.estado = "apagado"
import kira_god
core = kira_god.KiraGodCore()
CER = Cerebro(); core.cerebro_propio = CER; core.oido = OidoFalso()
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
def correr(seg, cond):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.1)
        if cond(): return True
        time.sleep(0.01)
    return cond()
labels = lambda: [w.text for w in sm.walk() if type(w).__name__ == "Label"]
ok(sm.current == "arranque", "al abrir, sale «Preparando a Kira»")
correr(1, lambda: False)
ok(any("Cerebro: cargándolo" in l for l in labels()) and any("Oído: listo" in l for l in labels()), "enseña cómo va cada cosa")
ok(sm.current == "arranque" and not VOZ.dichos, "espera al cerebro antes de empezar")
CER.on = True
ok(correr(3, lambda: sm.current == "inicio"), "con todo listo, entra sola")
ok(correr(2, lambda: any("Soy Kira" in d for d in VOZ.dichos)), "y entonces saluda")
# «Entrar ya»
core2 = kira_god.KiraGodCore(); core2.cerebro_propio = Cerebro(); core2.oido = OidoFalso()
sm2 = construir_interfaz(core2)
ok(sm2.current == "arranque", "otra vez preparando")
next(w for w in sm2.walk() if type(w).__name__ == "Button" and w.text == "Entrar ya").press()
ok(correr(1, lambda: sm2.current == "inicio"), "«Entrar ya» entra sin esperar")
print("ARRANQUE OK", n)
