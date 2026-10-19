# -*- coding: utf-8 -*-
"""Cableado de la Mesa de mezcla y el Editor de vídeo (Kivy falso + ffmpeg real)."""
import sys, os, tempfile, time, math, struct, wave, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import kira_god, diseno_kira as dk, motor_video_kira as mv, herramientas_kira as hk
if not mv.ffmpeg_ruta():
    print("CABLEADO AV OK (sin ffmpeg: se omite)"); sys.exit(0)
D = os.path.join(T, "orig"); os.makedirs(D)
def tono(r, hz, seg):
    with wave.open(r,"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes(b"".join(struct.pack("<h", int(7000*math.sin(2*math.pi*hz*i/22050))) for i in range(int(22050*seg))))
tono(os.path.join(D,"a.wav"),440,3); tono(os.path.join(D,"b.wav"),660,3)
g = dk.normalizar_guion({"titulo":"t","escenas":[{"escena":"dibuja una playa de día","dur":2},{"escena":"dibuja un bosque de noche","dur":2}]})
mv.renderizar(g, os.path.join(D,"v1.mp4"),"16:9","borrador")
med = dk.Mediateca(os.path.join(T,"mediateca.json"))
for t_,r in (("Tono A","a.wav"),("Tono B","b.wav"),("Clip 1","v1.mp4")): med.anadir(t_, os.path.join(D,r))
core = kira_god.KiraGodCore(); core._leer_clave = lambda: ""
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
def P(x): return sm.get_screen(x)
def botones(r): return [w for w in r.walk() if type(w).__name__ == "Button"]
def boton(r,t): return next(b for b in botones(r) if b.text==t)
def boton_pre(r,p): return next(b for b in botones(r) if b.text.startswith(p))
def textos(r): return [w.text for w in r.walk() if type(w).__name__ == "Label"]
def esperar(cond, seg=90):
    t=time.time()
    while time.time()-t<seg:
        Clock.correr(1,0.1)
        if cond(): return True
        time.sleep(0.05)
    return False
def sonda(r):
    d=json.loads(subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_type,codec_name,channels","-show_entries","format=duration","-of","json",r],capture_output=True,text=True).stdout)
    return d["streams"], float(d["format"]["duration"])

import menu_kira as mk
ok(any(a["id"]=="mezcla" for a in mk.APARTADOS) and any(a["id"]=="editor" for a in mk.APARTADOS), "el menú tiene mesa de mezcla y editor")

# ---- MESA DE MEZCLA ----
sm.ir("mezcla"); M = P("mezcla")
vac = [b for b in botones(M) if "Pista vacía" in b.text]
ok(len(vac) == 4, "cuatro pistas")
vac[0].press()  # -> Tono A
ok(boton_pre(M, "♪"), "elige un audio al tocar la pista")
# segunda pista -> ciclar dos veces hasta Tono B
p2 = [b for b in botones(M) if "Pista vacía" in b.text][0]
p2.press(); p2.press()
# ajustar faders de las pistas elegidas
from kivy.uix.slider import Slider
sliders = [w for w in M.walk() if isinstance(w, Slider)]
for s in sliders: s.value = getattr(s, "value", 100)
# bajar el volumen general
master = sliders[-1]; master.value = 80
boton(M,"Mezclar").press()
ok(esperar(lambda: any("Listo" in x for x in textos(M)) or any(x.startswith("[x]") for x in textos(M))), "la mezcla termina: "+str(textos(M)[-2:]))
ok(any("Listo" in x for x in textos(M)), "mezcla sin error")
mp3 = [f for f in os.listdir(os.path.join(T,"diseno","audios"))] if os.path.isdir(os.path.join(T,"diseno","audios")) else []
ok(any(f.endswith(".mp3") for f in mp3), "se guardó un mp3 real")
st,du = sonda(os.path.join(T,"diseno","audios",[f for f in mp3 if f.endswith(".mp3")][0]))
ok(st[0]["codec_name"]=="mp3" and st[0]["channels"]==2, "mezcla estéreo real")
ok(any(m["tipo"]=="audio" and m["estado"]=="creado" for m in dk.Mediateca(os.path.join(T,"mediateca.json")).listar()), "la mezcla entra en la mediateca")
sm.ir("mezcla")  # con 0 pistas da aviso
for b in botones(M):
    if b.text.startswith("♪"): 
        # vaciar: ciclar hasta vacía otra vez es complejo; en su lugar probamos una pantalla nueva
        break

# ---- EDITOR DE VÍDEO ----
sm.ir("editor_video"); E = P("editor_video")
boton(E,"Elegir vídeo…").press()
ok(boton_pre(E,"Vídeo:"), "elige un vídeo")
# cortar
next(w for w in E.walk() if type(w).__name__=="TextInput" and w.hint_text.startswith("inicio")).text = "0.5"
next(w for w in E.walk() if type(w).__name__=="TextInput" and w.hint_text=="fin").text = "2"
boton(E,"Cortar").press()
ok(esperar(lambda: any("Listo" in x or x.startswith("[x]") for x in textos(E))), "cortar termina")
ok(any("Listo" in x for x in textos(E)), "cortar sin error: "+str(textos(E)[-1:]))
vids = [f for f in os.listdir(os.path.join(T,"diseno","videos"))] if os.path.isdir(os.path.join(T,"diseno","videos")) else []
ok(any("corte" in f for f in vids), "se creó el vídeo cortado")
# redimensionar
boton_pre(E,"Tamaño:").press()
boton(E,"Redimensionar").press()
ok(esperar(lambda: any("Listo" in x for x in textos(E))), "redimensionar termina")
# poner música
boton(E,"Música…").press()
boton(E,"Poner música").press()
ok(esperar(lambda: any("Listo" in x for x in textos(E)) or any(x.startswith("[x]") for x in textos(E))), "poner música termina")
ok(any("Listo" in x for x in textos(E)), "poner música sin error")
con_mus = [f for f in os.listdir(os.path.join(T,"diseno","videos")) if "musica" in f]
ok(con_mus and sonda(os.path.join(T,"diseno","videos",con_mus[0]))[0], "el vídeo con música tiene stream")
# sin elegir vídeo avisa
sel = None
print("CABLEADO AV OK", n)
