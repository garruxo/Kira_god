# -*- coding: utf-8 -*-
"""Cableado de la pantalla Taller con un Kivy falso."""
import sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import kira_god, video_cliente_kira as vc
core = kira_god.KiraGodCore(); core._leer_clave = lambda: ""
hechos = {"prefijos": [], "ffmpeg": None, "lab": False, "lab_instalar": False}
core.hechos_capacidades = lambda consultar_laboratorio=True: dict(hechos)
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
def P(nombre): return sm.get_screen(nombre)
def botones(raiz): return [w for w in raiz.walk() if type(w).__name__ == "Button"]
def boton(raiz, empieza): return next(b for b in botones(raiz) if b.text.startswith(empieza))
boton_pre = boton
def textos(raiz): return [w.text for w in raiz.walk() if type(w).__name__ == "Label"]
def esperar(cond, seg=3):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.1)
        if cond(): return True
        time.sleep(0.02)
    return False
import menu_kira as mk
ok(any(a["id"] == "taller" and a["destino"] == ("pantalla", "taller") for a in mk.APARTADOS), "el menú tiene el Taller")
sm.ir("taller"); esperar(lambda: False, 0.4)
Ta = P("taller")
ok(any(b.text.startswith("[!] Mesa de mezcla") for b in botones(Ta)), "sin ffmpeg, la mesa de mezcla aparece con [!]")
ok(any(b.text.startswith("[OK] Videoclips") for b in botones(Ta)), "lo integrado aparece con [OK]")
ok(any("ffmpeg: no disponible" in x for x in textos(Ta)), "resumen del entorno")
boton(Ta, "[!] Mesa de mezcla").press()
ok(boton(Ta, "Abrir").disabled and boton_pre(Ta, "Instalar").disabled, "sin ffmpeg ni permiso: no se puede abrir ni instalar")
ok(any("ffmpeg" in x.lower() for x in textos(Ta)), "explica que necesita ffmpeg")
# el PC permite instalar
hechos.update(lab=True, lab_instalar=True)
boton(Ta, "Actualizar").press(); esperar(lambda: any("permite instalar" in x for x in textos(Ta)))
inst = boton(Ta, "Instalar en el PC"); ok(not inst.disabled, "con permiso del PC se puede pedir instalar")
pedidos = []
vc.ClienteVideo.instalar = lambda self, p: (pedidos.append(list(p)), (True, "Successfully installed imageio-ffmpeg"))[1]
inst.press(); ok(not pedidos and "Seguro" in inst.text, "el primer toque NO instala, pide confirmar")
ok(any("imageio-ffmpeg" in x and "TU PC" in x for x in textos(Ta)), "dice exactamente qué va a instalar y dónde")
inst.press(); esperar(lambda: pedidos)
ok(pedidos == [["imageio-ffmpeg"]], "el segundo toque lo pide al PC")
ok(esperar(lambda: any("[OK] Instalado" in x for x in textos(Ta))), "informa del resultado")
# ya hay ffmpeg: la mesa de mezcla pasa a DISPONIBLE y se puede abrir
hechos.update(ffmpeg="laboratorio")
boton(Ta, "Actualizar").press(); esperar(lambda: any(b.text.startswith("[OK] Mesa") for b in botones(Ta)))
ok(any(b.text.startswith("[OK] Mesa") for b in botones(Ta)), "con ffmpeg la mesa de mezcla aparece como [OK]")
boton_pre(Ta, "[OK] Mesa de mezcla").press()
ab = boton(Ta, "Abrir"); ok(not ab.disabled, "con ffmpeg: se puede Abrir")
ok(any("integrada" in x.lower() for x in textos(Ta)), "dice que ya viene integrada")
ab.press()
ok(sm.current == "mezcla", "«Abrir» lleva a la mesa de mezcla: " + sm.current)
ok(sm.control.pendiente is None, "no se ha generado ni aplicado nada solo por abrir")
# el editor también abre su pantalla
sm.ir("taller"); esperar(lambda: any(b.text.startswith("[OK] Editor") for b in botones(Ta)))
boton_pre(Ta, "[OK] Editor").press(); boton(Ta, "Abrir").press()
ok(sm.current == "editor_video", "«Abrir» del editor lleva a su pantalla: " + sm.current)
print("CABLEADO TALLER OK", n)
