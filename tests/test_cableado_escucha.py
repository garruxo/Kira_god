"""Cableado de la portada: botón de neón, escucha permanente con «Kira» (micrófono simulado), menú claro."""
import sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T

import inicio_kira as ik
class MicroFalso:
    """Simula el reconocimiento de voz del móvil: cada escucha devuelve la siguiente frase de la cola."""
    def __init__(self, *a, **k):
        self.cola, self.dichos, self.arranques, self.paradas = [], [], 0, 0
        self.hablando_hasta = 0.0; self._activa = False; self.error = ""
    def puede_hablar(self): return True
    def puede_escuchar(self): return True
    def hablando(self): return False
    def hablar(self, t): self.dichos.append(t); return True
    def iniciar_escucha(self, idioma="es-ES"): self.arranques += 1; self._activa = True; return True, "Te escucho…"
    def sondear(self):
        if not self._activa: return "error", "no"
        self._activa = False
        return ("listo", self.cola.pop(0)) if self.cola else ("error", "silencio")
    def parar_escucha(self): self.paradas += 1; self._activa = False
MICRO = MicroFalso()
ik.Voz = lambda *a, **k: MICRO

import kira_god
core = kira_god.KiraGodCore()
charlas = []
core.conversar = lambda t, h=(): (charlas.append(t), f"Te respondo sobre {t} con mucho gusto.")[1]
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
def labels(): return [w.text for w in sm.walk() if type(w).__name__ == "Label"]
def boton(txt): return next(w for w in sm.walk() if type(w).__name__ == "Button" and txt in w.text)
def correr(seg=2.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.4)
        if cond and cond(): return True
        time.sleep(0.01)
    return bool(cond and cond())

portada = next(w for w in sm.walk() if type(w).__name__ == "PortadaKira")
correr(1.5)
ok(any("di «Kira»" in l for l in labels()), "el saludo explica cómo llamarla")
ok(boton("Escucha:").text == "Escucha: SÍ", "la escucha permanente arranca sola")
ok(MICRO.arranques >= 1, "el micrófono se pone a escuchar")
ok(portada.modelo.estado in ("escuchando", "hablando"), "neón en modo escucha")

# sin el nombre: nada
MICRO.cola.append("estamos hablando de fútbol en el salón")
correr(1.5)
ok(not charlas, "sin «Kira» no contesta")
# con el nombre y la orden en la misma frase
MICRO.cola.append("Kira cuéntame un chiste de gatos")
ok(correr(4, lambda: charlas), "con «Kira» atiende")
ok(charlas == ["cuéntame un chiste de gatos"], "la orden es lo que va después del nombre: " + repr(charlas))
ok(correr(3, lambda: any("chiste de gatos con mucho" in l for l in labels())), "responde en la burbuja")
ok(any("chiste de gatos" in d for d in MICRO.dichos), "y lo dice en voz alta")
# solo el nombre: atenta, y la siguiente frase es la orden
MICRO.cola.append("Kira")
ok(correr(3, lambda: portada.modelo.estado == "atenta"), "solo «Kira»: se queda atenta y el neón brilla más")
ok(any("Dime" in d for d in MICRO.dichos), "pregunta «¿Sí? Dime.»")
MICRO.cola.append("qué tal el día")
ok(correr(4, lambda: "qué tal el día" in charlas), "la siguiente frase es la orden")
# conversación nueva guardada en el baúl; repetida, no
correr(1.0)
ok(core.recuerdos.respuesta_directa("qué tal el día") is not None or core.recuerdos.buscar("chiste gatos"), "guarda la conversación nueva")
total = core.recuerdos.estado()["total"]
MICRO.cola.append("Kira cuéntame un chiste de gatos")
correr(3)
ok(core.recuerdos.estado()["total"] == total, "la ya reconocida no se duplica")

# fuera de la portada no escucha
sm.ir("menu"); antes = MICRO.arranques; MICRO.cola.append("Kira hola"); correr(1.5)
ok(MICRO.arranques == antes and MICRO.cola, "en el menú no escucha")
sm.ir("inicio"); correr(1.0)
ok(MICRO.arranques > antes, "al volver a la portada, vuelve a escuchar")
MICRO.cola.clear()

# apagar y encender la escucha
boton("Escucha:").press(); correr(0.5)
ok(boton("Escucha:").text == "Escucha: NO" and any("Escucha apagada" in l for l in labels()), "se apaga")
antes = MICRO.arranques; MICRO.cola.append("Kira hola"); correr(1.5)
ok(MICRO.arranques == antes, "apagada no escucha")
ok("escucha_permanente\": false" in open(os.path.join(T, "interfaz_ajustes.json")).read(), "recuerda que la apagaste")
MICRO.cola.clear(); boton("Escucha:").press(); correr(0.6)
ok(boton("Escucha:").text == "Escucha: SÍ", "se vuelve a encender")
sm.ir("config"); ok(any("Escucha permanente" in w.text for w in sm.walk() if type(w).__name__ == "Button"), "también en Configuración")

# botón de neón -> menú (con animación)
sm.ir("inicio"); portada.al_tocar(); ok(sm.current == "menu", "el botón de neón entra al menú")
class Toque: x, y = 50, 60
portada.zoom = 1.0; sm.ir("inicio"); portada.on_touch_down(Toque()); ok(sm.current == "menu", "un toque en el centro también")

# ---------- pedir una mejora con la voz ----------
sm.ir("inicio"); correr(0.5); MICRO.dichos.clear(); charlas.clear()
core.cerebro_para_codigo = lambda: None
MICRO.cola.append("Kira, aprende a convertir euros a dólares")
ok(correr(3, lambda: any("necesito un cerebro" in d for d in MICRO.dichos)), "sin cerebro: lo dice claro")
ok(not charlas, "no lo trata como charla")
core.cerebro_para_codigo = lambda: "claude"
ctl = sm.control; ctl.pasarela.url = ""
MICRO.cola.append("Kira, aprende a convertir euros a dólares")
ok(correr(3, lambda: any("laboratorio conectado" in d for d in MICRO.dichos)), "sin laboratorio: lo dice claro")
ctl.pasarela.url = "http://127.0.0.1:8765"; ctl.pasarela.token = "token-de-prueba-largo-123"   # conectado (url y token)
pedidos, aplicadas = [], []
class Pend:
    nombre = "euros_dolares"; resultado = {"avisos": []}
def enviar_orden(p): pedidos.append(p); ctl.pendiente = Pend(); return {"ok": True, "aprobable": True, "intentos": 1, "texto": "Resumen: superó las pruebas."}
ctl.enviar_orden = enviar_orden
ctl.aplicar = lambda confirmado=False: (aplicadas.append(confirmado), {"ok": True, "texto": "[OK] aplicado"})[1]
MICRO.cola.append("Kira, aprende a convertir euros a dólares")
ok(correr(3, lambda: any("me pongo a programar" in d for d in MICRO.dichos)), "confirma que se pone a programar")
ok(correr(6, lambda: pedidos), "envía el pedido al laboratorio")
ok("convertir euros a dólares" in pedidos[0] and sm.current == "terminal", "abre la terminal de mejoras con el pedido: " + repr(pedidos))
ok(correr(3, lambda: any("ha pasado las pruebas" in d for d in MICRO.dichos)), "lee el resultado en voz alta")
ok(not aplicadas, "la voz NO aplica nada: hay que tocar Aplicar dos veces")
ok(not buscar_btn("Aplicar").disabled if (buscar_btn := (lambda t: next(w for w in sm.get_screen("terminal").walk() if type(w).__name__ == "Button" and w.text == t))) else False, "Aplicar queda listo para tus dos toques")
print("CABLEADO ESCUCHA OK", n)
