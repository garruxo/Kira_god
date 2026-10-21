# -*- coding: utf-8 -*-
"""v2.27: «para» y «cancela» valen aunque Kira esté hablando o trabajando; lo que estaba haciendo y la mejora
pendiente sobreviven a un cierre de Android; por qué la cerró Android, explicado (Kivy y cerebro simulados)."""
import io, json, os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import escucha_kira as esk, cerebro_ia_kira as ci, cierres_kira as ck
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- qué es «para» y qué es «cancela» ----------
for f in ("para", "Kira, para", "para de hablar", "Cállate", "silencio por favor", "basta ya kira", "deja de hablar"):
    ok(esk.orden_control(f) == "callar", f"«{f}» es callar")
for f in ("Kira cancela", "cancela lo que estás haciendo", "déjalo", "para todo", "detente", "olvídalo", "cancela eso"):
    ok(esk.orden_control(f) == "cancelar", f"«{f}» es cancelar")
for f in ("te lo dejo para mañana", "para qué sirve esto", "cancela mi cita de mañana", "Kira, abre WhatsApp",
          "hola", "Kira para qué sirve git"):
    ok(esk.orden_control(f) is None, f"«{f}» NO es una orden de control (su propia voz no la corta)")

# ---------- cortar al cerebro a mitad ----------
class Flujo:
    def __init__(s, n): s.l = [b'data: {"choices":[{"delta":{"content":"hola "}}]}\n'] * n
    def readline(s): return s.l.pop(0) if s.l else b""
vistos = []
try:
    ci.leer_sse(Flujo(50), lambda d: d["choices"][0]["delta"]["content"], vistos.append, parar=lambda: len(vistos) >= 3)
    ok(False, "debía cortarse")
except ci.Cancelada:
    ok(len(vistos) == 3, "«cancela» corta al cerebro mientras escribe")
ok(ci.leer_sse(Flujo(2), lambda d: d["choices"][0]["delta"]["content"], lambda t: None) == "hola hola ", "sin parar, igual que antes")

import kira_god
core = kira_god.KiraGodCore()
core.cerebro_ia.chat_local = lambda system, mensajes, max_tokens=512, al_trozo=None, parar=None: (
    (_ for _ in ()).throw(ci.Cancelada("Cancelado.")) if parar and parar() else "respuesta")
ok(core._llamar_api(ci.LOCAL, "s", "u") == "respuesta", "sin cancelar, responde")
ok("cancelo" in core.cancelar().lower() and core.cancelado(), "«cancela» marca lo que está en marcha")
try:
    core._llamar_api(ci.LOCAL, "s", "u"); ok(False, "debía cancelarse")
except ci.Cancelada:
    ok(True, "lo que pide al cerebro se corta")
core.nueva_tarea()
ok(not core.cancelado() and core._llamar_api(ci.LOCAL, "s", "u") == "respuesta", "algo nuevo: el «cancela» de antes no cuenta")
core.cancelar(); core.__dict__["_cancelar_t"] -= 60
ok(not core.cancelado(), "y pasado un rato tampoco (no se queda cancelando todo para siempre)")
pintados = []
class PintorFalso:
    def cancelar(s): pintados.append("cortado")
core.pintor = PintorFalso(); core.cancelar(); core.nueva_tarea()
ok(pintados == ["cortado"], "también corta el pintor")

# ---------- lo que estaba haciendo sobrevive a un cierre ----------
ruta = os.path.join(T, "trabajo.json")
t1 = ck.Trabajo(ruta)
t1.empezar("programa", "programa que calcule mi media")
t2 = ck.Trabajo(ruta)                              # Android la cerró a mitad y vuelve a arrancar
ok(t2.interrumpido and t2.interrumpido["pedido"] == "programa que calcule mi media", "sabe qué estaba haciendo")
ok("sigue con lo que hacías" in t2.aviso() and "escribir un programa" in t2.aviso(), "y lo dice al arrancar")
ok(t2.retomar()["tipo"] == "programa" and t2.retomar() is None, "lo retoma una sola vez")
t3 = ck.Trabajo(ruta); t3.empezar("mejora", "x"); t3.terminar()
ok(ck.Trabajo(ruta).interrumpido is None, "si terminó bien, no hay nada que retomar")
for f in ("sigue con lo que hacías", "Kira, continúa con lo que estabas haciendo", "retoma el trabajo", "sigue"):
    ok(ck.pide_seguir(f), f"«{f}» retoma")
ok(not ck.pide_seguir("sigue la serie de fibonacci"), "otra cosa no")
# el núcleo lo apunta mientras programa (y lo borra al acabar)
vio = {}
def api(clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None):
    vio["fichero"] = os.path.isfile(os.path.join(core.dir, "trabajo_en_curso.json"))
    return "NOMBRE: media\n```python\nprint(7)\n```"
core._leer_clave = lambda *a: ci.LOCAL
core._llamar_api = api
core.reparto = lambda tarea: ("local", None)
core.cancelar()
r = core.programa_acordado("programa que diga 7")
ok(r["ok"] and vio["fichero"], "mientras programa, está apuntado (y un «cancela» viejo no lo corta)")
ok(not os.path.isfile(os.path.join(core.dir, "trabajo_en_curso.json")), "al acabar, se borra")

# ---------- por qué la cerró Android ----------
ahora = int(time.time() * 1000)
txt, ms = ck.motivo_android(f"3|lmk|{ahora}|2621440|125", 0)
ok("MEMORIA" in txt and "2.5 GB" in txt and "cerebro ligero" in txt and ms == ahora, "falta de memoria: lo explica")
ok(ck.motivo_android(f"3|lmk|{ahora}|0|125", ahora)[0] is None, "el mismo cierre no se repite")
ok(ck.motivo_android(f"10||{ahora + 5}|0|100", ahora)[0] is None, "si la cerraste tú, no avisa")
txt, _ = ck.motivo_android(f"2|signal 9|{ahora + 9}|0|125", ahora)
ok("Sin restricciones" in txt, "cerrada por el sistema (ahorro del fabricante): dice qué tocar")
ok(ck.motivo_android("", 0) == (None, 0) and ck.motivo_android("basura", 7) == (None, 7), "sin dato, nada")
V = ck.Visto(os.path.join(T, "visto.txt")); V.guardar(ahora)
ok(ck.Visto(os.path.join(T, "visto.txt")).ms == ahora, "recuerda hasta dónde avisó")

# ---------- la mejora pendiente sobrevive a un cierre ----------
import panel_kira as pk
MOD = "def registrar():\n    return {'saluda': lambda t: 'hola ' + t}\n"
ctl = pk.PanelControl(core)
r = ctl.probar_codigo(MOD, "saluda", "que salude")
ok(r["aprobable"] and os.path.isfile(ctl.ruta_pendiente), "probada y esperando tus dos toques: guardada en disco")
ctl2 = pk.PanelControl(core)                      # Kira se cerró y vuelve
ok(ctl2.pendiente is not None and ctl2.pendiente.aprobable and ctl2.recuperada and ctl2.pedido_actual == "que salude",
   "al volver, la mejora sigue ahí")
ok(not ctl2.aplicar()["ok"], "y aplicar sigue pidiendo tu confirmación")
d = json.load(open(ctl.ruta_pendiente)); d["codigo"] += "# cambiado\n"; json.dump(d, open(ctl.ruta_pendiente, "w"))
ok(pk.PanelControl(core).pendiente is None, "si el código cambió en el disco, NO vale (no lo aprobó el laboratorio)")
ctl.probar_codigo(MOD, "saluda", "que salude")
ctl.rechazar("no")
ok(not os.path.isfile(ctl.ruta_pendiente) and pk.PanelControl(core).pendiente is None, "rechazada: se borra")

# ---------- la interfaz: «para» mientras habla, «cancela» mientras trabaja ----------
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
import inicio_kira as ik
class VozFalsa:
    def __init__(s): s.dichos, s.calladas, s.habla = [], 0, False
    def puede_hablar(s): return True
    def puede_escuchar(s): return False
    def hablando(s): return s.habla
    def hablar(s, t): s.dichos.append(t); return True
    def callar(s): s.calladas += 1; s.habla = False
    def iniciar_escucha(s, idioma="es-ES"): return False, "no"
    def sondear(s): return "error", "no"
    def parar_escucha(s): pass
VOZ = VozFalsa(); ik.Voz = lambda *a, **k: VOZ
class OidoFalso:
    estado, mensaje = "escuchando", ""
    def __init__(s): s.cb, s.pausas = None, []
    def disponible(s): return True
    def libreria_disponible(s): return True
    def modelo_instalado(s): return True
    def encender(s, al_frase, al_estado=None): s.cb = al_frase; return True, "ok"
    def pausar(s, si): s.pausas.append(si)
    def apagar(s): pass
core2 = kira_god.KiraGodCore()
core2.oido = OIDO = OidoFalso()
cancelados = []
core2.cancelar = lambda: (cancelados.append(1), "Vale, lo cancelo.")[1]
preguntas = []
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core2)
def correr(seg=1.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.3)
        if cond and cond(): return True
        time.sleep(0.01)
    return bool(cond and cond())
correr(1.5)
ok(OIDO.cb is not None, "el oído propio está escuchando")
VOZ.habla = True
correr(0.6)
ok(OIDO.pausas and OIDO.pausas[-1] is False, "MIENTRAS HABLA, el oído sigue escuchando (antes se pausaba)")
antes = len(VOZ.dichos)
OIDO.cb("Kira, cuéntame un chiste")                # su propia voz o algo que no es «para»: no se atiende
correr(0.5)
ok(len(VOZ.dichos) == antes, "lo que oye mientras habla no lo atiende (podría ser su propia voz)")
OIDO.cb("para")
correr(0.3)
ok(VOZ.calladas == 1 and not VOZ.habla, "«para» la calla en el acto")
OIDO.cb("Kira, cancela")
correr(0.6)
ok(cancelados and VOZ.calladas == 2 and any("cancelo" in d.lower() for d in VOZ.dichos), "«cancela» corta lo que hace y lo dice")
campo = next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "TextInput")
cancelados.clear()
campo.text = "cancela"
next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
correr(0.5)
ok(cancelados, "también escrito")
print("CONTROL POR VOZ OK", n)
