import sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import kira_god
core = kira_god.KiraGodCore()
llamadas = []
core.conversar = lambda t, h=(): (llamadas.append((t, list(h))), "Hola, estoy aquí contigo.")[1]
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
def buscar(tipo, raiz=None, **atr):
    for w in (raiz or sm).walk():
        if type(w).__name__ == tipo and all(getattr(w, k, None) == v or (k == "texto_en" and v in getattr(w, "text", "")) for k, v in atr.items() if k != "texto_en") and \
           ("texto_en" not in atr or atr["texto_en"] in getattr(w, "text", "")):
            return w
    raise AssertionError(f"no hay {tipo} {atr}")
def esperar(cond, seg=3):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.1)
        if cond(): return True
        time.sleep(0.02)
    return False
ok(sm.current == "inicio", "arranca en el orbe")
campo = buscar("TextInput", hint_text="Escríbele a Kira…")
burbuja = [w for w in sm.walk() if type(w).__name__ == "Label"]
Clock.correr(40, 0.1)
sal = [w.text for w in burbuja if "Soy Kira" in w.text]
ok(sal and "no tengo cerebro" in sal[0], "saludo honesto sin cerebro: " + str([w.text for w in burbuja][:6]))
# charla
campo.text = "hola kira"; buscar("Button", text="Enviar").press()
B = next(w for w in burbuja if "Soy Kira" in w.text or w.text == "…")
ok(esperar(lambda: "contigo" in B.text), "respuesta de charla en la burbuja: " + B.text)
ok(llamadas and llamadas[0][0] == "hola kira", "pasó por conversar: " + repr(llamadas) + str([w.text for w in burbuja]))
# orden real del núcleo (no debe ir a charla)
llamadas.clear(); campo.text = "recargar modulos"; buscar("Button", text="Enviar").press()
Clock.correr(60, 0.1); time.sleep(0.3); Clock.correr(60, 0.1)
ok(not llamadas, "una orden conocida no llama a la IA: " + str(llamadas))
# entrar con el orbe
orbe = next(w for w in sm.walk() if type(w).__name__ == "PortadaKira")
orbe.al_tocar(); ok(sm.current == "menu", "tocar el botón de neón entra al menú")
# menú sencillo: primero los principales; «Más apartados» enseña el resto
tiles = [w for w in sm.walk() if type(w).__name__ == "Button" and "[b]" in w.text]
import menu_kira as _mk
ok(len(tiles) == len(_mk.PRINCIPALES) == 12, f"12 apartados principales (con Pintor e Internet), hay {len(tiles)}")
mas = buscar("Button", texto_en="Más apartados"); mas.press()
tiles = [w for w in sm.walk() if type(w).__name__ == "Button" and "[b]" in w.text]
import menu_kira as _mk
ok(len(tiles) == len(_mk.APARTADOS) and "Menos" in mas.text, f"con «Más» salen todos ({len(_mk.APARTADOS)}), hay {len(tiles)}")
# todos los apartados navegan sin error
vistos = set()
for t in tiles:
    sm.ir("menu"); t.press(); Clock.correr(3, 0.1); time.sleep(0.15); Clock.correr(3, 0.1); vistos.add(sm.current)
ok(vistos == {"inicio", "panel", "pasarela", "busqueda", "notas", "memoria", "estado", "config", "ayuda", "lienzo", "conocimiento", "sala_hacker", "sala_diseno", "sala_cine", "mediateca", "taller", "sala_ciber", "mezcla", "editor_video", "bitacora", "juegos", "editor_codigo", "cerebro_kira", "lector", "pintor", "internet"}, "destinos: " + str(vistos))
# notas
sm.ir("notas"); cn = buscar("TextInput", hint_text="Nueva nota…"); cn.text = "comprar pilas"
buscar("Button", text="Añadir nota").press(); ok("comprar pilas" in open(os.path.join(T, "notas.json"), encoding="utf-8").read(), "nota guardada")
# búsqueda
sm.ir("busqueda"); cb = buscar("TextInput", hint_text="Busca en notas, lecciones, módulos y conversaciones…"); cb.text = "pilas"
buscar("Button", text="Buscar").press()
ok(any("[nota] comprar pilas" in w.text for w in sm.walk() if type(w).__name__ == "Label"), "búsqueda encuentra la nota")
# memoria con borrado en dos toques
sm.ir("memoria"); b = buscar("Button", text="Borrar conversación"); b.press(); ok("Seguro" in b.text, "pide confirmar")
b.press(); ok(b.text == "Borrar conversación", "borra al segundo toque")
ok(open(os.path.join(T, "conversacion.json")).read().strip() == "[]", "historial vacío")
# lienzo: pedirlo por el orbe abre la pantalla y dibuja
sm.ir("inicio"); campo.text = "dibuja un paisaje de una playa al atardecer"; buscar("Button", text="Enviar").press()
ok(esperar(lambda: sm.current == "lienzo"), "pedir un dibujo abre el lienzo")
ew = next(w for w in sm.walk() if type(w).__name__ == "EscenaWidget"); ok(len(ew.formas) > 50, "el lienzo tiene formas")
ok(any("playa de atardecer" in w.text for w in sm.walk() if type(w).__name__ == "Label"), "leyenda del lienzo")
buscar("Button", text="Otra variante").press(); ok(len(ew.formas) > 50, "variante")
cl_ = buscar("TextInput", hint_text="Describe la escena: playa al atardecer con palmeras…"); cl_.text = "dragon volando"; buscar("Button", text="Dibujar").press()
ok(any("Solo sé dibujar" in w.text for w in sm.walk() if type(w).__name__ == "Label"), "honesto con lo que no sabe dibujar")
cl_.text = "montañas de noche"; buscar("Button", text="Dibujar").press(); ok(len(ew.formas) > 20, "dibuja desde el campo")
# aprender por el orbe y verlo en Conocimiento
sm.ir("inicio"); campo.text = "aprende que mi gato se llama Miko"; buscar("Button", text="Enviar").press()
esperar(lambda: os.path.exists(os.path.join(T, "conocimiento.json"))); Clock.correr(5, 0.1)
sm.ir("conocimiento"); ok(any("Miko" in w.text for w in sm.walk() if type(w).__name__ == "Label"), "aparece en Conocimiento")
buscar("Button", text="Olvidar").press(); ok(not any("Miko" in w.text for w in sm.walk() if type(w).__name__ == "Label" and w.text.startswith("[")), "olvidar")
# configuración
sm.ir("config"); bv = buscar("Button", texto_en="Kira habla"); antes = bv.text; bv.press(); ok(bv.text != antes, "alterna voz")
# atrás
sm.ir("menu")
from kivy.core.window import Window as W
f = [f for f in W._b["on_keyboard"]][0]; ok(f(W, 27) is True and sm.current == "inicio", "Esc: menú -> portada")
ok(f(W, 27) is False, "Esc en la portada deja salir")
# clave nunca en disco de historial
campo.text = "config clave: sk-ant-api03-ZZZZZZZZZZZZ"; buscar("Button", text="Enviar").press(); esperar(lambda: False, 0.6)
ok("ZZZZZZ" not in open(os.path.join(T, "conversacion.json")).read(), "la clave no queda en el historial")

# ---------- SALA HACKER ----------
import habitacion_kira as hk
sm.ir("sala_hacker")
hab = next(w for w in sm.walk() if type(w).__name__ == "HabitacionWidget")
ok(hab.rec.estado == "caminando", "entra caminando")
Clock.correr(120, 0.05); ok(hab.rec.estado == "libre", "llega a la mesa y queda libre")
class Toque:
    def __init__(s, x, y): s.x, s.y, s.pos, s.dx, s.dy, s.grab_current = x, y, (x, y), 0, 0, None
    def grab(s, w): s.grab_current = w
    def ungrab(s, w): s.grab_current = None
t = Toque(50, 50); hab.on_touch_down(t); t.x += 40; t.dx = 40; hab.on_touch_move(t); hab.on_touch_up(t)
ok(hab.rec.pose[3] != 0, "arrastrar gira la vista")
hab.rec.pose = hk.POSE_MESA
mx, my = hk.proyectar(hk.a_camara((0, 1.28, 6.88), hk.POSE_MESA), 100, 100, 90)
t = Toque(mx, my); hab.on_touch_down(t); hab.on_touch_up(t); ok(hab.rec.estado == "yendo", "tocar el ordenador te acerca")
Clock.correr(60, 0.05); Clock.correr(20, 0.05); ok(sm.current == "terminal", "llega y se conecta a la terminal: " + sm.current)
# aprender
buscar("Button", text="Bucles (for y while)").press()
ok(any("Ejemplo:" in w.text and "range(3)" in w.text for w in sm.walk() if type(w).__name__ == "Label"), "muestra la lección")
buscar("Button", text="Comprobar sintaxis").press(); ok(any("Sintaxis correcta" in w.text for w in sm.walk() if type(w).__name__ == "Label"), "comprueba sintaxis")
buscar("Button", text="Guardar en biblioteca").press(); ok("Bucles" in open(os.path.join(T, "biblioteca.json"), encoding="utf-8").read(), "guarda en la biblioteca")
ok("programación Bucles" in open(os.path.join(T, "conocimiento.json"), encoding="utf-8").read(), "Kira lo recuerda")
core.generar_leccion = lambda tema: ("Recursión", "Una función que se llama a sí misma.", "def f(n):\n    return n")
buscar("TextInput", hint_text="Pídele a Kira una lección sobre…").text = "recursión"
buscar("Button", texto_en="Pedir lección").press(); esperar(lambda: any("Recursión" in w.text for w in sm.walk() if type(w).__name__ == "Label" and "Ejemplo" in w.text))
ok(any("Recursión" in w.text and "Ejemplo:" in w.text for w in sm.walk() if type(w).__name__ == "Label"), "lección pedida a Kira")
# mejorar (con el flujo de mejoras simulado)
buscar("Button", text="MEJORAR").press()
class Pend:
    nombre = "hora_rapida"; resultado = {"avisos": ["importa 'subprocess'"]}
ctl = sm.control; pedidos = []
def enviar_orden(p): pedidos.append(p); ctl.pendiente = Pend(); return {"ok": True, "aprobable": True, "intentos": 1, "texto": "Resumen del laboratorio: superó las pruebas."}
aplicadas = []
ctl.enviar_orden = enviar_orden; ctl.aplicar = lambda confirmado=False: (aplicadas.append(confirmado), {"ok": True, "texto": "[OK] Módulo aplicado."})[1]
buscar("Button", text="Sistema").press()
buscar("TextInput", hint_text="Qué quieres que Kira aprenda a hacer…").text = "muestra la batería"
buscar("Button", text="Pedir mejora").press(); esperar(lambda: pedidos)
ok(pedidos and "solo lectura" in pedidos[0] and "muestra la batería" in pedidos[0], "el alcance viaja en la orden: " + repr(pedidos) + " tema=" + repr(buscar("TextInput", hint_text="Qué quieres que Kira aprenda a hacer…").text))
ok(esperar(lambda: not buscar("Button", raiz=sm.get_screen("terminal"), text="Aplicar").disabled), "se activa Aplicar")
ok(any("Resumen del laboratorio" in w.text for w in sm.walk() if type(w).__name__ == "Label"), "muestra el resultado")
ap = buscar("Button", raiz=sm.get_screen("terminal"), text="Aplicar"); ap.press()
ok(not aplicadas and "Seguro" in ap.text, "el primer toque NO aplica, pide confirmar")
ok(any("subprocess" in w.text for w in sm.walk() if type(w).__name__ == "Label"), "enseña los avisos antes de confirmar")
ap.press(); esperar(lambda: aplicadas); ok(aplicadas == [True], "el segundo toque aplica con confirmación")
# biblioteca
kivy_falso.Window.fire("noop") if False else None
from kivy.core.window import Window as W2
tecla = W2._b["on_keyboard"][0]
ok(tecla(W2, 27) is True and sm.current == "sala_hacker", "Esc en la terminal vuelve a la habitación")
ok(hab.rec.estado in ("volviendo", "libre"), "la cámara vuelve a la mesa")
hab.rec.pose = hk.POSE_MESA; hab.rec.estado = "libre"
buscar("TextInput", hint_text="Di o escribe: hackear, programar, biblioteca, salir…").text = "llévame a la biblioteca"
buscar("Button", text="Ir").press(); Clock.correr(80, 0.05); ok(sm.current == "biblioteca", "por voz/texto a la biblioteca: " + sm.current)
buscar("Button", text="Apuntes").press()
buscar("TextInput", hint_text="Título del apunte").text = "Truco"; buscar("TextInput", hint_text="Texto o código").text = "usa enumerate"
buscar("Button", text="Guardar apunte").press(); ok("enumerate" in open(os.path.join(T, "biblioteca.json"), encoding="utf-8").read(), "apunte guardado")
buscar("Button", text="Lecciones").press(); ok(any(w.text.startswith("Bucles") for w in sm.walk() if type(w).__name__ == "Button"), "estante de lecciones")
buscar("Button", text="Módulos").press(); buscar("Button", text="Aprendido").press()
ok(any("programación Bucles" in w.text for w in sm.walk() if type(w).__name__ == "Button"), "estante de lo aprendido")
tecla(W2, 27); hab.rec.pose = hk.POSE_MESA; hab.rec.estado = "libre"
buscar("TextInput", hint_text="Di o escribe: hackear, programar, biblioteca, salir…").text = "salir"
buscar("Button", text="Ir").press(); Clock.correr(80, 0.05); ok(sm.current == "menu", "salir vuelve al menú: " + sm.current)
sm.ir("sala_hacker"); ok(hab.rec.estado == "caminando", "al volver a entrar, otra vez el paseo")
print("CABLEADO OK", n)
