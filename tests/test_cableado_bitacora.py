# -*- coding: utf-8 -*-
"""Cableado de la pantalla Bitácora y del consejo automático al fallar (Kivy falso)."""
import sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import kira_god
core = kira_god.KiraGodCore(); core._leer_clave = lambda: ""
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
def P(x): return sm.get_screen(x)
def botones(r): return [w for w in r.walk() if type(w).__name__ == "Button"]
def boton(r, t): return next(b for b in botones(r) if b.text == t)
def textos(r): return [w.text for w in r.walk() if type(w).__name__ == "Label"]
import menu_kira as mk
ok(any(a["id"] == "bitacora" and a["destino"] == ("pantalla", "bitacora") for a in mk.APARTADOS), "el menú tiene la Bitácora")
sm.ir("bitacora"); B = P("bitacora")
ok(any("Lo que hemos construido" in x for x in textos(B)), "abre con el resumen")
boton(B, "FALLOS").press()
ok(any("No tengo fallos" in x for x in textos(B)) and boton(B, "Ya está arreglado").disabled, "sin fallos, nada que cerrar")
core.registrar_error("vídeo", "No se encontró ffmpeg")
boton(B, "FALLOS").press()
ok(any("imageio-ffmpeg" in x for x in textos(B)) and not boton(B, "Ya está arreglado").disabled, "el fallo aparece con su arreglo")
boton(B, "Ya está arreglado").press()
ok(core.bitacora.pendientes() == [] and any("resueltos" in x for x in textos(B)), "se cierran los fallos")
boton(B, "GUÍAS").press()
g = next(b for b in botones(B) if b.text.startswith("Compilar el APK en la nube")); g.press()
ok(any("Artifacts" in x for x in textos(B)), "abre la guía de compilar en la nube")
campo = next(w for w in B.walk() if type(w).__name__ == "TextInput")
campo.text = "IP del PC: 192.168.1.40"; boton(B, "Apuntar").press()
ok(any("192.168.1.40" in x["texto"] for x in core.bitacora.notas) and any("Apuntado" in x for x in textos(B)), "apunta una nota")
# consejo automático en la mesa de mezcla: sin ffmpeg ni laboratorio, el error trae el arreglo
import herramientas_kira as hk, motor_video_kira as mv
mv.ffmpeg_ruta = lambda: None
sm.ir("editor_video"); E = P("editor_video")
import diseno_kira as dk
D = os.path.join(T, "o"); os.makedirs(D); open(os.path.join(D, "v.mp4"), "wb").write(b"x")
dk.Mediateca(os.path.join(T, "mediateca.json")).anadir("Clip", os.path.join(D, "v.mp4"))
sm.ir("editor_video")
next(b for b in botones(E) if b.text == "Elegir vídeo…").press()
ok(any(b.text.startswith("Vídeo: Clip") for b in botones(E)), "elige el vídeo")
cortar = next(b for b in botones(E) if b.text == "Cortar"); cortar.press()
t0 = time.time()
while time.time() - t0 < 20 and not any(x.startswith("[x]") for x in textos(E)):
    Clock.correr(1, 0.1); time.sleep(0.05)
errs = [x for x in textos(E) if x.startswith("[x]")]
ok(errs, "el editor informa del error: " + str(textos(E)[-3:]))
ok(any("Cómo arreglarlo" in x for x in errs) or any(e["origen"] == "mezcla/editor" for e in core.bitacora.errores), "el fallo queda apuntado y, si lo conoce, sale el arreglo: " + str(errs))
print("CABLEADO BITÁCORA OK", n)
