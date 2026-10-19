# -*- coding: utf-8 -*-
"""Cableado de la Sala de Diseño, Sala de Cine, estudio, mediateca y reproductor con un Kivy falso."""
import sys, os, tempfile, time, json, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import kira_god, diseno_kira as dk, salas_kira as sk, habitacion_kira as hk
core = kira_god.KiraGodCore(); core._leer_clave = lambda: ""
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
from kivy.core.window import Window as W2
tecla = W2._b["on_keyboard"][0]
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
def buscar(tipo, raiz=None, **atr):
    for w in (raiz or sm).walk():
        if type(w).__name__ == tipo and all(getattr(w, k, None) == v for k, v in atr.items() if k != "texto_en") and \
           ("texto_en" not in atr or atr["texto_en"] in getattr(w, "text", "")):
            return w
    raise AssertionError(f"no hay {tipo} {atr}")
def textos(raiz=None):
    return [w.text for w in (raiz or sm).walk() if type(w).__name__ == "Label"]
def esperar(cond, seg=3):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.1)
        if cond(): return True
        time.sleep(0.02)
    return False
def pantalla(nombre): return sm.get_screen(nombre)
def decir(sala, frase, hint):
    buscar("TextInput", raiz=pantalla(sala), hint_text=hint).text = frase
    buscar("Button", raiz=pantalla(sala), text="Ir").press()

# ---------- menú ----------
import menu_kira as mk
ids = {a["id"]: a["destino"][1] for a in mk.APARTADOS}
ok(ids["diseno"] == "sala_diseno" and ids["cine"] == "sala_cine" and ids["mediateca"] == "mediateca", "el menú tiene diseño, cine y mediateca")
ok(all(any(s.name == d for s in sm.children) for d in ("sala_diseno", "estudio", "mediateca", "sala_cine", "reproductor")), "las 5 pantallas existen")

# ---------- sala de diseño ----------
HD, HIN = "Di o escribe: diseñar, mediateca, cine, salir…", "Di o escribe: ver, pantalla, diseño, salir…"
sm.ir("sala_diseno")
hd = buscar("HabitacionWidget", raiz=pantalla("sala_diseno"))
ok(hd.rec.cfg is sk.CFG_DISENO and hd.rec.estado == "caminando", "entra caminando en la sala de diseño")
Clock.correr(120, 0.05); ok(hd.rec.estado == "libre", "llega a la mesa")
ok({b.text for b in pantalla("sala_diseno").walk() if type(b).__name__ == "Button"} >= {"Salir", "< Mediateca", "Diseñar", "Cine >"}, "botones de la sala (incluye Salir)")
# arrastrar, tocar el ordenador
class Toque:
    def __init__(s, x, y): s.x, s.y, s.pos, s.dx, s.dy, s.grab_current = x, y, (x, y), 0, 0, None
    def grab(s, w): s.grab_current = w
    def ungrab(s, w): s.grab_current = None
t = Toque(50, 50); hd.on_touch_down(t); t.x += 40; t.dx = 40; hd.on_touch_move(t); hd.on_touch_up(t)
ok(hd.rec.pose[3] != 0, "arrastrar gira la vista")
hd.rec.pose = sk.POSE_D_MESA
mx, my = hk.proyectar(hk.a_camara((0, 1.3, 6.89), sk.POSE_D_MESA), 100, 100, 90)
t = Toque(mx, my); hd.on_touch_down(t); hd.on_touch_up(t); ok(hd.rec.estado == "yendo", "tocar el ordenador te acerca")
Clock.correr(60, 0.05); Clock.correr(20, 0.05); ok(sm.current == "estudio", "llega y abre el estudio: " + sm.current)

# ---------- estudio: WEB ----------
buscar("Button", raiz=pantalla("estudio"), text="WEB").press()
buscar("TextInput", raiz=pantalla("estudio"), hint_text="Describe lo que quieres crear…").text = "web de una cafetería junto a la playa"
buscar("Button", raiz=pantalla("estudio"), text="Crear").press()
ok(esperar(lambda: any("<!DOCTYPE html>" in x for x in textos(pantalla("estudio")))), "genera el HTML: " + str(textos(pantalla("estudio"))[-3:]))
ok(any("plantillas locales" in x for x in textos(pantalla("estudio"))), "dice que usó plantillas (sin clave), no la IA")
ok(any("<script" in x.lower() for x in textos(pantalla("estudio"))) is False, "el HTML mostrado no tiene scripts")
buscar("Button", raiz=pantalla("estudio"), text="Guardar").press()
ok(any(f.endswith(".html") for f in os.listdir(os.path.join(T, "diseno"))), "guarda el .html")
ok(any("Guardado dentro de Kira" in x for x in textos(pantalla("estudio"))), "avisa de dónde queda")

# ---------- estudio: APP ----------
buscar("Button", raiz=pantalla("estudio"), text="APP").press()
buscar("TextInput", raiz=pantalla("estudio"), hint_text="Describe lo que quieres crear…").text = "app de notas y tareas"
buscar("Button", raiz=pantalla("estudio"), text="Crear").press()
ok(esperar(lambda: any("Pantalla 1" in x for x in textos(pantalla("estudio")))), "genera la maqueta")
buscar("Button", raiz=pantalla("estudio"), text="Guardar").press()
ok(any(f.endswith(".app.json") for f in os.listdir(os.path.join(T, "diseno"))), "guarda la maqueta")

# ---------- estudio: VIDEOCLIP ----------
buscar("Button", raiz=pantalla("estudio"), text="VIDEOCLIP").press()
ok(buscar("Button", raiz=pantalla("estudio"), texto_en="en desarrollo").disabled, "no se puede guardar antes de crear")
buscar("TextInput", raiz=pantalla("estudio"), hint_text="Describe lo que quieres crear…").text = "videoclip de una playa del amanecer a la noche"
buscar("Button", raiz=pantalla("estudio"), text="Crear").press()
ok(esperar(lambda: any("VIDEOCLIP:" in x for x in textos(pantalla("estudio")))), "genera el guion")
buscar("Button", raiz=pantalla("estudio"), texto_en="en desarrollo").press()
bib = json.load(open(os.path.join(T, "mediateca.json"), encoding="utf-8"))
ok(len(bib) == 1 and bib[0]["tipo"] == "clip" and bib[0]["estado"] == "desarrollo", "el videoclip entra en la mediateca como 'en desarrollo'")
buscar("Button", raiz=pantalla("estudio"), text="Ver en el cine").press()
ok(sm.current == "reproductor", "ver en el cine abre el reproductor")
ok(any("Escena 1" in x for x in textos(pantalla("reproductor"))), "muestra la primera escena sin empezar")
buscar("Button", raiz=pantalla("reproductor"), text="Play").press()
Clock.correr(80, 0.1)
ok(any("Escena" in x and "[" in x for x in textos(pantalla("reproductor"))), "el storyboard avanza con el reloj")
b_play = buscar("Button", raiz=pantalla("reproductor"), text="Pausa"); b_play.press()
ok(buscar("Button", raiz=pantalla("reproductor"), text="Play"), "pausa")
buscar("Button", raiz=pantalla("reproductor"), text="Parar").press()
Clock.correr(300, 0.1)
ok(tecla(W2, 27) is True and sm.current == "sala_cine", "Esc en el reproductor vuelve al cine")
ok(buscar("HabitacionWidget", raiz=pantalla("sala_diseno")).rec.estado in ("libre", "dentro", "volviendo", "yendo", "caminando"), "sala de diseño sigue válida")

# ---------- sala de cine ----------
hc = buscar("HabitacionWidget", raiz=pantalla("sala_cine"))
ok(hc.rec.cfg is sk.CFG_CINE, "la sala de cine usa su configuración")
Clock.correr(120, 0.05)
ok({b.text for b in pantalla("sala_cine").walk() if type(b).__name__ == "Button"} >= {"Salir", "< Diseño", "Pantalla", "Salir >"}, "botones del cine (incluye Salir)")
decir("sala_cine", "quiero ver la peli", HIN); Clock.correr(80, 0.05)
ok(sm.current == "reproductor", "por voz/texto a la pantalla del cine: " + sm.current)
ok(any("Elige" in x for x in textos(pantalla("reproductor"))), "al entrar desde el cine se ofrece la lista")
ok(any(b.text.startswith("[C]") for b in pantalla("reproductor").walk() if type(b).__name__ == "Button"), "la lista incluye el videoclip creado")
tecla(W2, 27); hc.rec.pose = sk.POSE_C_MESA; hc.rec.estado = "libre"
ok(tecla(W2, 27) is True and sm.current == "sala_diseno", "Esc en el cine vuelve a la sala de diseño")
Clock.correr(120, 0.05)

# ---------- puerta del cine desde la sala de diseño ----------
hd.rec.pose = sk.POSE_D_MESA; hd.rec.estado = "libre"
decir("sala_diseno", "vamos al cine", HD); Clock.correr(80, 0.05)
ok(sm.current == "sala_cine", "la puerta de la derecha lleva al cine: " + sm.current)
# regreso del cine (puerta izquierda) y salir
hc.rec.pose = sk.POSE_C_MESA; hc.rec.estado = "libre"
decir("sala_cine", "volver al estudio", HIN); Clock.correr(80, 0.05)
ok(sm.current == "sala_diseno", "la puerta izquierda del cine vuelve a diseño: " + sm.current)
Clock.correr(120, 0.05)
hd.rec.pose = sk.POSE_D_MESA; hd.rec.estado = "libre"
decir("sala_diseno", "salir", HD); Clock.correr(80, 0.05)
ok(sm.current == "menu", "la puerta de regreso (izquierda) sale al menú: " + sm.current)
sm.ir("sala_cine"); Clock.correr(120, 0.05)
buscar("Button", raiz=pantalla("sala_cine"), text="Salir").press()
ok(sm.current == "menu", "el botón Salir del cine va al menú")

# ---------- mediateca ----------
sm.ir("sala_diseno"); Clock.correr(120, 0.05)
buscar("Button", raiz=pantalla("sala_diseno"), text="< Mediateca").press(); Clock.correr(80, 0.05)
ok(sm.current == "mediateca", "biblioteca de la izquierda abre la mediateca: " + sm.current)
buscar("Button", raiz=pantalla("mediateca"), text="En desarrollo").press()
bt = [b for b in pantalla("mediateca").walk() if type(b).__name__ == "Button" and b.text.startswith("[C]")]
ok(len(bt) == 1, "el clip aparece en 'En desarrollo'")
bt[0].press(); buscar("Button", raiz=pantalla("mediateca"), text="Cambiar estado").press()
ok(json.load(open(os.path.join(T, "mediateca.json"), encoding="utf-8"))[0]["estado"] == "creado", "cambia a 'creado'")
buscar("Button", raiz=pantalla("mediateca"), text="Creados").press()
bt = [b for b in pantalla("mediateca").walk() if type(b).__name__ == "Button" and b.text.startswith("[C]")]; bt[0].press()
buscar("Button", raiz=pantalla("mediateca"), text="Reproducir").press()
ok(sm.current == "reproductor" and any("Escena 1" in x for x in textos(pantalla("reproductor"))), "reproducir abre el clip elegido sin reiniciar la pantalla")
tecla(W2, 27); tecla(W2, 27); tecla(W2, 27)
sm.ir("mediateca")
# escanear el móvil (simulado)
M = os.path.join(T, "movil"); os.makedirs(M)
open(os.path.join(M, "cancion.mp3"), "wb").write(b"x"); open(os.path.join(M, "peli.mp4"), "wb").write(b"x")
dk.carpetas_medios = lambda: [M]
buscar("Button", raiz=pantalla("mediateca"), texto_en="Buscar vídeos").press()
ok(esperar(lambda: any("Encontrados 2" in x for x in textos(pantalla("mediateca")))), "escanea el móvil: " + str(textos(pantalla("mediateca"))[-3:]))
buscar("Button", raiz=pantalla("mediateca"), text="Música").press()
cancion = [b for b in pantalla("mediateca").walk() if type(b).__name__ == "Button" and b.text.startswith("[M]")]
ok(len(cancion) == 1, "aparece la música encontrada")
# audio con un SoundLoader falso
class Sonido:
    def __init__(s): s.t = []
    def play(s): s.t.append("play")
    def stop(s): s.t.append("stop")
    def unload(s): s.t.append("unload")
    def get_pos(s): return 3.0
    def seek(s, p): s.t.append(("seek", p))
snd = Sonido(); a = types.ModuleType("kivy.core.audio"); a.SoundLoader = type("SL", (), {"load": staticmethod(lambda r: snd)}); sys.modules["kivy.core.audio"] = a
cancion[0].press(); buscar("Button", raiz=pantalla("mediateca"), text="Reproducir").press()
buscar("Button", raiz=pantalla("reproductor"), text="Play").press(); ok(snd.t == ["play"], "la música suena")
buscar("Button", raiz=pantalla("reproductor"), text="Pausa").press(); buscar("Button", raiz=pantalla("reproductor"), text="Play").press()
ok(snd.t[-2:] == ["play", ("seek", 3.0)], "pausa y sigue donde se quedó: " + str(snd.t))
sm.ir("menu"); ok("stop" in snd.t and "unload" in snd.t, "al salir de la pantalla se para la música")
# vídeo real: este entorno no tiene proveedor -> mensaje honesto
sm.ir("mediateca"); buscar("Button", raiz=pantalla("mediateca"), text="Vídeos").press()
peli = [b for b in pantalla("mediateca").walk() if type(b).__name__ == "Button" and b.text.startswith("[V]")]
peli[0].press(); buscar("Button", raiz=pantalla("mediateca"), text="Reproducir").press()
ok(any("no incluye un reproductor de vídeo" in x for x in textos(pantalla("reproductor"))), "sin proveedor de vídeo lo dice, no finge")
# quitar con doble toque; el archivo no se borra
sm.ir("mediateca"); buscar("Button", raiz=pantalla("mediateca"), text="Vídeos").press()
peli = [b for b in pantalla("mediateca").walk() if type(b).__name__ == "Button" and b.text.startswith("[V]")]; peli[0].press()
q = buscar("Button", raiz=pantalla("mediateca"), text="Quitar de la lista"); q.press()
ok(os.path.exists(os.path.join(M, "peli.mp4")) and "Seguro" in q.text and len(dk.Mediateca(os.path.join(T, "mediateca.json")).listar(tipo="video")) == 1, "el primer toque pide confirmar")
q.press(); ok(len(dk.Mediateca(os.path.join(T, "mediateca.json")).listar(tipo="video")) == 0 and os.path.exists(os.path.join(M, "peli.mp4")), "el segundo quita de la lista sin borrar el archivo")
# Hacker intacto
sm.ir("sala_hacker"); hh = buscar("HabitacionWidget", raiz=pantalla("sala_hacker")); ok(hh.rec.cfg is hk.CFG_HACKER and hh.rec.estado == "caminando", "la Sala Hacker sigue funcionando")
ok(hd._reloj is None and hc._reloj is None, "al salir se paran los relojes de las otras salas")
# ---------- crear el MP4 real desde el estudio ----------
sm.ir("estudio"); E = pantalla("estudio")
buscar("Button", raiz=E, text="VIDEOCLIP").press()
ok(buscar("Button", raiz=E, text="Crear vídeo MP4").disabled, "no se puede crear el MP4 sin guion")
buscar("TextInput", raiz=E, hint_text="Describe lo que quieres crear…").text = "videoclip de un bosque"
buscar("Button", raiz=E, text="Crear").press(); ok(esperar(lambda: any("VIDEOCLIP:" in x for x in textos(E))), "guion listo")
buscar("Button", raiz=E, text="16:9").press(); ok(buscar("Button", raiz=E, text="9:16"), "el botón de formato rota")
buscar("Button", raiz=E, text="normal").press(); buscar("Button", raiz=E, text="alta").press(); ok(buscar("Button", raiz=E, text="borrador"), "el botón de calidad rota")
buscar("Button", raiz=E, text="Sin música").press(); ok(any(b.text.startswith("Música:") for b in E.walk() if type(b).__name__ == "Button"), "elige música de la mediateca")
buscar("Button", raiz=E, text="Crear vídeo MP4").press()
ok(esperar(lambda: any(x.startswith("[x]") and "ffmpeg" in x for x in textos(E)), 60), "una música rota (archivo falso) da un error claro, no un vídeo falso")
ok(not os.path.exists(os.path.join(T, "diseno", "videos")) or not [f for f in os.listdir(os.path.join(T, "diseno", "videos")) if f.endswith(".mp4")], "y no deja un MP4")
next(b for b in E.walk() if type(b).__name__ == "Button" and b.text.startswith("Música:")).press()
ok(buscar("Button", raiz=E, text="Sin música"), "vuelve a sin música")
buscar("Button", raiz=E, text="Crear vídeo MP4").press()
ok(esperar(lambda: any("Vídeo creado" in x for x in textos(E)), 60), "crea el vídeo: " + str(textos(E)[-3:]))
mp4 = [f for f in os.listdir(os.path.join(T, "diseno", "videos")) if f.endswith(".mp4")]
ok(len(mp4) == 1, "hay un MP4 real en diseno/videos")
import subprocess
sonda = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height", "-of", "csv=p=0", os.path.join(T, "diseno", "videos", mp4[0])], capture_output=True, text=True).stdout
ok("h264" in sonda and "360,640" in sonda or "h264,360,640" in sonda.replace("\n", ""), "es H.264 vertical (9:16 borrador): " + sonda)
ok(any(i["tipo"] == "video" and i["estado"] == "creado" and i["titulo"].endswith("(MP4)") for i in json.load(open(os.path.join(T, "mediateca.json"), encoding="utf-8"))), "el MP4 entra en la mediateca")
ok(buscar("Button", raiz=E, text="Crear vídeo MP4") is not None, "el botón vuelve a su texto")
print("CABLEADO DISEÑO OK", n)
