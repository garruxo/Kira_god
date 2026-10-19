"""Ver la pantalla y siempre activa: apps privadas, la captura se borra, órdenes, pantalla y voz en segundo plano."""
import sys, os, tempfile, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import vista_kira as vk, lector_kira as lk
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

class JavaFalso:
    paquete = "org.kira.kiragod"
    def __init__(s): s.app, s.ver, s.servicio, s.capturas, s.uso = "com.android.chrome", False, False, [], True
    def iniciar(s, pantalla=False): s.servicio = True
    def detener(s): s.servicio = False; s.ver = False
    def activo(s): return s.servicio
    def puede_ver(s): return s.ver
    def pedir_permiso(s, al_resultado): s.ver = s.servicio = True; al_resultado(True)
    def capturar(s, ruta):
        open(ruta, "wb").write(b"png"); s.capturas.append(ruta); return True
    def app_actual(s): return s.app
    def acceso_uso(s): return s.uso
    def abrir_ajustes_uso(s): s.ajustes = True

def tsv_de(lineas):
    filas = ["level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"]
    for i, l in enumerate(lineas):
        x = 10
        for k, w in enumerate(l.split()):
            filas.append(f"5\t1\t1\t1\t{i+1}\t{k+1}\t{x}\t{20 + i * 30}\t{len(w) * 10}\t20\t95\t{w}")
            x += len(w) * 10 + 10
    return "\n".join(filas)
TSV = tsv_de(["Reunión mañana a las nueve", "en la sala grande"])
L = lk.Lector(T, motor=lambda r, td, i: TSV)
os.makedirs(L.tessdata, exist_ok=True)
for i in lk.IDIOMAS:
    open(os.path.join(L.tessdata, i + ".traineddata"), "wb").write(b"t" * 200_000)

# ---------- lógica ----------
J = JavaFalso()
v = vk.Vista(T, J)
ok("com.whatsapp" in v.privadas and not v.siempre_activa, "por defecto: WhatsApp privada, no siempre activa")
try:
    v.mirar(L); ok(False, "sin permiso")
except vk.VistaError as e:
    ok("permiso" in str(e), "sin permiso no mira")
J.pedir_permiso(lambda ok_: None)
texto, app = v.mirar(L)
ok("Reunión mañana" in texto and app == "com.android.chrome", "mira y lee la pantalla")
ok(J.capturas and not os.path.exists(J.capturas[-1]), "la captura se BORRA después de leerla")
J.app = "com.whatsapp"
try:
    v.mirar(L); ok(False, "privada")
except vk.VistaError as e:
    ok("privadas" in str(e), "en una app privada no mira")
ok(len(J.capturas) == 1, "y ni siquiera captura")
J.app = J.paquete; ok(v.mirar(L)[0], "su propia app sí la puede mirar")
ok(v.anadir_privada("com.banco") and not v.anadir_privada("com.banco"), "añadir privada (sin repetir)")
v.poner_siempre_activa(True); ok(J.servicio, "siempre activa arranca el servicio")
v2 = vk.Vista(T, J); ok("com.banco" in v2.privadas and v2.siempre_activa, "se recuerda al reiniciar")
ok(v2.quitar_privada("com.banco") and "com.banco" not in vk.Vista(T, J).privadas, "quitar privada")
J.ver = False; v.poner_siempre_activa(False); ok(not J.servicio, "al quitarla, para el servicio")
open(v.ruta_cfg, "w").write("{roto"); ok(vk.Vista(T, J).privadas == vk.PRIVADAS_DEFECTO, "config rota: valores por defecto")
v.poner_siempre_activa(False)
pc_ = vk.Vista(tempfile.mkdtemp(), None)
ok(not pc_.disponible() and not pc_.puede_ver() and pc_.app_actual() is None, "en el PC no hay vista")

# ---------- órdenes ----------
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
import kira_god
core = kira_god.KiraGodCore()
J = JavaFalso(); core.vista = vk.Vista(T, J); core.lector = L
charlas = []
ok("permiso" in core.procesar_orden("qué ves"), "«qué ves» sin permiso: lo explica")
J.ver = True
r = core.procesar_orden("Kira qué ves" if False else "qué ves")
ok("En tu pantalla pone" in r and "Reunión" in r, "«qué ves»")
ok("Reunión" in core.procesar_orden("lee la pantalla"), "«lee la pantalla»")
ok("Reunión" in core.procesar_orden("mira la pantalla"), "«mira la pantalla»")
core.conversar = lambda t, h=(), al_trozo=None: "Tienes una reunión mañana." if "Reunión" in t else (charlas.append(t), "Son las ocho.")[1]
ok(core.procesar_orden("explícame la pantalla") == "Tienes una reunión mañana.", "«explícame la pantalla» usa el cerebro")
ok("no miraré com.android.chrome" in core.procesar_orden("no mires esta app"), "«no mires esta app»")
ok("[x]" in core.procesar_orden("qué ves") and "privadas" in core.procesar_orden("qué ves"), "después ya no la mira")
ok("com.android.chrome" in core.procesar_orden("apps privadas"), "«apps privadas» la lista")
ok("ya puedo mirar" in core.procesar_orden("puedes mirar esta app"), "«puedes mirar esta app»")
J.app = None; ok("Acceso a datos de uso" in core.procesar_orden("no mires esta app"), "sin saber qué app: lo explica")
J.app = "com.android.chrome"

# ---------- pantalla ----------
class OidoFalso:
    def __init__(s): s.cb, s.pausas, s.estado, s.mensaje = None, [], "apagado", ""
    def disponible(s): return True
    def modelo_instalado(s): return True
    def libreria_disponible(s): return True
    def encender(s, al_frase, al_estado=None): s.cb, s.estado = al_frase, "escuchando"; return True, "ok"
    def pausar(s, si): s.pausas.append(si)
    def apagar(s): s.estado = "apagado"
    def oye(s, texto): threading.Thread(target=s.cb, args=(texto,)).start()
OIDO = OidoFalso(); core.oido = OIDO
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
def correr(seg=2.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.1)
        if cond and cond(): return True
        time.sleep(0.01)
    return bool(cond and cond())
def labels(raiz): return [w.text for w in raiz.walk() if type(w).__name__ == "Label"]
correr(1.0)
sm.ir("cerebro_kira"); pc = sm.get_screen("cerebro_kira"); Clock.correr(3, 0.5)
def boton(txt): return next(w for w in pc.walk() if type(w).__name__ == "Button" and txt in w.text)
ok(boton("Siempre activa: NO"), "botón «Siempre activa»")
ok(boton("Usar oído propio"), "el botón del oído sigue ahí")
boton("Siempre activa").press(); Clock.correr(2, 0.5)
ok(J.servicio and core.vista.siempre_activa and boton("Siempre activa: SÍ"), "se activa desde la pantalla")
ok(boton("Dejar que vea la pantalla").disabled, "ya tiene permiso: botón desactivado")
ok(any("Puede ver la pantalla" in l for l in labels(pc)), "dice que puede ver")
boton("Permiso para saber").press(); ok(getattr(J, "ajustes", False), "abre los ajustes de «datos de uso»")
boton("Apps privadas").press(); Clock.correr(1, 0.5)
ok(any("com.whatsapp" in l for l in labels(pc)), "enseña las apps privadas")
J.ver = False; Clock.correr(3, 0.5)
b = boton("Dejar que vea la pantalla"); ok(not b.disabled, "sin permiso: se puede pedir")
b.press(); ok(correr(2, lambda: J.ver and any("Ya puedo ver" in l for l in labels(pc))), "pedir permiso desde la pantalla")

# ---------- en segundo plano: contesta por voz ----------
sm.ir("inicio"); correr(0.5)
core.en_segundo_plano = True


VOZ.dichos.clear(); antes = sm.current
OIDO.oye("Kira cuéntame algo")
ok(correr(3, lambda: any("ocho" in d for d in VOZ.dichos)), "en otra app: te oye y contesta en voz alta " + repr(VOZ.dichos))
ok(True in OIDO.pausas and OIDO.pausas[-1] is False, "pausa el oído mientras habla y luego lo reanuda")
VOZ.dichos.clear(); OIDO.oye("Kira qué ves")
ok(correr(3, lambda: any("Reunión" in d for d in VOZ.dichos)), "en otra app: «Kira, qué ves» te lee la pantalla")
VOZ.dichos.clear(); OIDO.oye("hablando de otra cosa"); correr(1)
ok(not VOZ.dichos, "sin su nombre no dice nada")
core.en_segundo_plano = False
import main
ok(hasattr(main, "__file__"), "main se importa")
print("VISTA OK", n)
