# -*- coding: utf-8 -*-
"""v2.29: UNA tarea larga cada vez con su barra (tiempo y %); si le pides otra cosa mientras trabaja, pregunta si la
deja; «sí»: la aparca, hace lo tuyo y vuelve a ella; «no»: sigue y lo tuyo va después. Y las MEJORAS INSTALADAS se
usan de verdad: su orden va primero y se entiende aunque no la digas exacta (Kivy y cerebro simulados)."""
import os, sys, tempfile, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import tareas_kira as tk
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- el gestor (reloj falso) ----------
ahora = [100.0]
G = tk.Gestor(os.path.join(T, "tareas.json"), reloj=lambda: ahora[0])
ok(not G.ocupado() and G.estimacion() is None and G.texto_barra() == "", "sin tarea, sin barra")
G.empezar("programa", "programa que calcule mi media")
ahora[0] += 45
f, falta = G.estimacion()
ok(0.4 < f < 0.5 and abs(falta - 45) < 1, f"sin datos de la tarea: por lo que suele tardar (90 s): {f:.2f} {falta:.0f}")
G.progreso(0.75, "probando en modo seguro")
f, falta = G.estimacion()
ok(f == 0.75 and 20 < falta < 40, f"con su progreso: 75 % y lo que falta ({falta:.0f} s)")
G.progreso(0.5)
ok(G.estimacion()[0] == 0.75, "el % nunca va hacia atrás")
b = G.texto_barra()
ok("Escribir un programa" in b and "75 %" in b and "quedan ~" in b and "probando" in b, "texto de la barra: " + b)
ahora[0] += 15
G.terminar(True)
ok(G.duracion_tipica("programa") == 60.0, "aprende cuánto tarda de verdad (60 s)")
ok(tk.Gestor(os.path.join(T, "tareas.json")).duracion_tipica("programa") == 60.0, "y lo recuerda")
G.empezar("mejora", "x"); ahora[0] += 500
f, falta = G.estimacion()
ok(f < 1 and falta >= 5, "si tarda más de lo normal, no dice 100 % ni «0 s»")
G.terminar(True)
ok(tk.tiempo(75) == "1 min 15 s" and tk.tiempo(9) == "9 s" and tk.tiempo(4000) == "1 h 06 min", "tiempos legibles")
# interrumpir y retomar
relanzadas = []
G.empezar("experimento", "colores", relanzar=lambda: relanzadas.append(1), datos={"pedido": "colores"})
t = G.interrumpir()
ok(t.interrumpida and G.terminar(True).interrumpida, "aparcada: al terminar, se sabe que la dejaste")
G.cola.insert(0, "hazme un juego")
ok(G.siguiente() == ("orden", "hazme un juego"), "primero lo que pediste")
q, tarea = G.siguiente()
ok(q == "retomar" and tarea.descripcion == "colores" and G.siguiente() is None, "después, vuelve a la aparcada")
G.empezar("pdf", "descargar"); G.interrumpir()
ok(tk.Gestor(os.path.join(T, "tareas.json")).de_antes[0]["tipo"] == "pdf", "las aparcadas sobreviven a un cierre")

# ---------- las mejoras instaladas se usan de verdad ----------
import kira_god, cerebro_ia_kira as ci
os.makedirs(os.path.join(T, "modulos"), exist_ok=True)
open(os.path.join(T, "modulos", "euros.py"), "w").write(
    "def registrar():\n    return {'convierte euros': lambda t: 'EUROS:' + t, 'busca': lambda t: 'MODULO:' + t}\n")
core = kira_god.KiraGodCore()
core.cargar_modulos()
ok(core.procesar_orden("Kira, convierte euros: 10 a Dólares") == "EUROS:10 a Dólares", "su orden exacta (lo de después, tal cual)")
ok(core.procesar_orden("convierte 10 euros a dólares") == "EUROS:10 a dólares", "y dicha de otra forma")
ok(core.es_orden_de_modulo("convierte euros 3") and not core.es_orden_de_modulo("busca en internet gatos"),
   "una orden de una palabra del núcleo («busca») no le quita el sitio a Kira")
import panel_kira as pk
ctl = pk.PanelControl(core)
MOD = "def registrar():\n    return {'di hola': lambda t: 'hola ' + t}\n"
ctl.probar_codigo(MOD, "saludo", "que salude")
r = ctl.aplicar(True)
ok(r["ok"] and "Úsala diciendo: «Kira, di hola …»" in r["texto"], "al instalarla, dice cómo se usa: " + r["texto"][-120:])
ok(core.procesar_orden("di hola Ana") == "hola Ana", "y ya funciona")

# ---------- la interfaz: preguntar, aparcar, volver ----------
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock, Window
import inicio_kira as ik
class VozMuda:
    def __init__(s): s.dichos = []
    def puede_hablar(s): return True
    def puede_escuchar(s): return False
    def hablando(s): return False
    def hablar(s, t): s.dichos.append(t); return True
    def callar(s): pass
    def iniciar_escucha(s, idioma="es-ES"): return False, "no"
    def sondear(s): return "error", "no"
    def parar_escucha(s): pass
VOZ = VozMuda(); ik.Voz = lambda *a, **k: VOZ
core2 = kira_god.KiraGodCore()
core2.cerebro_para_codigo = lambda: "local"
core2.reparto = lambda tarea: ("local", None)
core2._leer_clave = lambda *a: ci.LOCAL
espera = {"lento": True}
pedidos = []
def api(clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None):
    pedidos.append(usuario)
    if "LENTO" in usuario:
        t0 = time.time()
        while espera["lento"] and time.time() - t0 < 20:      # trabaja… hasta que la cancelan
            if core2.cancelado():
                raise ci.Cancelada("Cancelado.")
            time.sleep(0.05)
        return "NOMBRE: lento\n```python\nprint('soy el LENTO')\n```"
    return "NOMBRE: rapido\n```python\nprint('soy el RAPIDO')\n```"
core2._llamar_api = api
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core2)
def correr(seg=3.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.3)
        if cond and cond(): return True
        time.sleep(0.02)
    return bool(cond and cond())
def textos(nombre): return [w.text for w in sm.get_screen(nombre).walk() if hasattr(w, "text") and isinstance(w.text, str)]
def escribir(frase):
    campo = next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "TextInput")
    campo.text = frase
    next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
def barra(): return " ".join(getattr(w, "text", "") for w in getattr(Window, "children", []))
correr(0.8)
escribir("Kira, escríbeme un programa que sea LENTO")
ok(correr(3, lambda: core2.tareas.ocupado() and "%" in barra() and "quedan" in barra()), "una tarea larga: barra con % y tiempo: " + barra())
sm.ir("inicio"); correr(0.3)
escribir("escríbeme un programa que sea rápido")
ok(correr(2, lambda: any("¿Lo dejo guardado" in d for d in VOZ.dichos)), "si le pides otra cosa, pregunta si la deja")
ok(any("Estoy con escribir un programa" in d and "%" in d for d in VOZ.dichos), "y dice por dónde va")
escribir("sí")
ok(correr(8, lambda: any("soy el RAPIDO" in t for t in textos("editor_codigo"))), "«sí»: deja la suya y hace lo tuyo")
ok(any("Vuelvo con lo que estaba haciendo" in d for d in VOZ.dichos) or correr(6, lambda: any(
    "Vuelvo con lo que estaba haciendo" in d for d in VOZ.dichos)), "y al terminar vuelve a la que dejó")
espera["lento"] = False
ok(correr(10, lambda: any("soy el LENTO" in t for t in textos("editor_codigo"))), "y la termina")
ok(correr(3, lambda: not core2.tareas.ocupado() and "quedan" not in barra()), "sin tareas, la barra se va")
# «no»: sigue con lo suyo y lo tuyo va después
espera["lento"] = True
sm.ir("inicio"); correr(0.3)
VOZ.dichos.clear()
escribir("escríbeme un programa que sea LENTO otra vez")
correr(1.5)
sm.ir("inicio"); correr(0.3)
escribir("escríbeme un programa que sea rápido")
correr(1.0)
escribir("no, sigue")
ok(correr(2, lambda: any("lo hago en cuanto termine" in d for d in VOZ.dichos)), "«no»: sigue")
correr(1.0)
ok(core2.tareas.actual is not None and "LENTO" in core2.tareas.actual.descripcion, "con la suya")
espera["lento"] = False
ok(correr(12, lambda: sum("soy el" in t for t in textos("editor_codigo")) and any("RAPIDO" in t for t in textos("editor_codigo"))
          and not core2.tareas.ocupado()), "y después hace lo tuyo")
# una mejora instalada se usa aunque otra pantalla la quisiera interceptar
os.makedirs(os.path.join(core2.dir, "modulos"), exist_ok=True)
open(os.path.join(core2.dir, "modulos", "pinta.py"), "w").write(
    "def registrar():\n    return {'pinta estrellas': lambda t: 'ESTRELLAS ' + t}\n")
core2.cargar_modulos()
sm.ir("inicio"); correr(0.3)
escribir("Kira, pinta estrellas 5")
ok(correr(3, lambda: any("ESTRELLAS 5" in t for t in textos("inicio"))), "«pinta estrellas» va a SU mejora, no al pintor")
print("TAREAS OK", n)
