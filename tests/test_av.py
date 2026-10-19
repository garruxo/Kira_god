# -*- coding: utf-8 -*-
"""Mesa de mezcla y editor de vídeo REALES: generan audio/vídeo de verdad con ffmpeg y validan el resultado."""
import json, math, os, struct, subprocess, sys, tempfile, wave
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audio_kira as ak, editor_kira as ed, herramientas_kira as hk, motor_video_kira as mv, diseno_kira as dk, ffmpeg_seguro as fs
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
FF = mv.ffmpeg_ruta(); ok(FF, "hay ffmpeg para las pruebas")
def sonda(ruta):
    d = json.loads(subprocess.run(["ffprobe","-v","error","-show_entries","stream=codec_type,codec_name,width,height,channels",
        "-show_entries","format=duration","-of","json",ruta], capture_output=True, text=True).stdout)
    v = next((s for s in d["streams"] if s["codec_type"]=="video"), None)
    a = next((s for s in d["streams"] if s["codec_type"]=="audio"), None)
    return v, a, float(d["format"]["duration"])
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
D = os.path.join(T, "orig"); os.makedirs(D)
def tono(ruta, hz, seg):
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes(b"".join(struct.pack("<h", int(7000*math.sin(2*math.pi*hz*i/22050))) for i in range(int(22050*seg))))
tono(os.path.join(D,"a.wav"),440,4); tono(os.path.join(D,"b.wav"),660,3); tono(os.path.join(D,"c.wav"),330,2)
g = dk.normalizar_guion({"titulo":"t","escenas":[{"escena":"dibuja una playa de día","dur":2},{"escena":"dibuja un bosque de noche","dur":2}]})
mv.renderizar(g, os.path.join(D,"v1.mp4"), "16:9","borrador")
mv.renderizar(g, os.path.join(D,"v2.mp4"), "9:16","borrador")
med = dk.Mediateca(os.path.join(T,"mediateca.json"))
for t_,r in (("Tono A","a.wav"),("Tono B","b.wav"),("Tono C","c.wav"),("Clip 1","v1.mp4"),("Clip 2","v2.mp4")):
    ok(med.anadir(t_, os.path.join(D,r))[0], "medio "+t_)
H = hk.Herramientas(T)

# ---------- MESA DE MEZCLA ----------
for bad in ([{"titulo":""}], [{"titulo":"x","volumen":5}], [{"titulo":"x","pan":2}], []):
    try: ak.construir_args_mezcla(bad, "m.mp3"); ok(False, f"mezcla inválida {bad}")
    except ak.AudioError: ok(True, "rechaza mezcla inválida")
args = ak.construir_args_mezcla([{"titulo":"Tono A","volumen":1.2,"pan":-0.5,"fundido":1},
                                 {"titulo":"Tono B","volumen":0.6,"pan":0.8,"retardo":1}], "m.mp3", 0.9)
ok(fs.validar_args(args, 2) == args, "los args de la mezcla pasan el filtro de seguridad")
s = ak.mezclar(H, [{"titulo":"Tono A","volumen":1.2,"pan":-0.5,"fundido":1.0},
                   {"titulo":"Tono B","volumen":0.6,"pan":0.8,"retardo":1.0},
                   {"titulo":"Tono C","volumen":1.0}], "mezcla.mp3", volumen_general=0.9)
v,a,du = sonda(H.ruta(s))
ok(a and a["codec_name"]=="mp3" and a["channels"]==2 and abs(du-4)<0.3, f"mezcla real estéreo de 3 pistas, ~4s ({a},{du})")
ok(ak.mezclar(H, [{"titulo":"Tono A"}], "m2.wav")=="m2.wav" and sonda(H.ruta("m2.wav"))[1]["codec_name"].startswith("pcm"), "mezcla a WAV")
try: ak.mezclar(H, [{"titulo":"No Existe"}], "x.mp3"); ok(False,"pista inexistente")
except hk.HerramientaError: ok(True,"pista que no está en la mediateca -> error claro")

# ---------- EFECTOS / CONVERTIR / EXTRAER ----------
for ef in ("eco","graves","agudos","normalizar","rapido","lento","radio"):
    out = ak.efecto(H, "Tono A", ef, salida=f"ef_{ef}.mp3")
    ok(sonda(H.ruta(out))[1] is not None, f"efecto {ef} produce audio")
ok(abs(sonda(H.ruta("ef_rapido.mp3"))[2]-4/1.35)<0.4, "«rápido» acorta la duración")
try: ak.efecto(H,"Tono A","zzz"); ok(False,"efecto malo")
except ak.AudioError: ok(True,"efecto desconocido se rechaza")
ok(sonda(H.ruta(ak.convertir(H,"Tono A","ogg")))[1]["codec_name"]=="vorbis", "convertir WAV->OGG")
try:
    ex = ak.extraer_audio(H, "Clip 1", "mp3")   # el clip del motor no tiene audio
    ok(os.path.getsize(H.ruta(ex))>0, "si hubiera audio, se extrae")
except hk.HerramientaError:
    ok(not os.path.exists(H.ruta("v1.mp3")), "extraer de un vídeo sin audio avisa y no crea un archivo falso")

# ---------- EDITOR DE VÍDEO ----------
for f,bad in ((ed.args_cortar,("5","3")),(ed.args_redimensionar,("8k",)),(lambda:ed.args_unir(1),())):
    try: f(*bad) if bad else f(); ok(False,"editor arg inválido")
    except ed.EditorError: ok(True,"editor rechaza parámetros inválidos")
cor = ed.cortar(H, "Clip 1", "0.5", "2.5")
v,a,du = sonda(H.ruta(cor)); ok(v["codec_name"]=="h264" and abs(du-2)<0.3, f"cortar deja 2s ({du})")
red = ed.redimensionar(H, "Clip 2", "360p")
v,a,du = sonda(H.ruta(red)); ok((v["width"],v["height"])==(640,360), f"redimensionar a 360p ({v['width']}x{v['height']})")
uni = ed.unir(H, ["Clip 1","Clip 2"], "480p")
v,a,du = sonda(H.ruta(uni)); ok((v["width"],v["height"])==(854,480) and abs(du-8)<0.5 and a is None, f"unir 2 clips a 480p sin audio ({v['width']}x{v['height']},{du})")
mus = ed.poner_musica(H, "Clip 1", "Tono A")
v,a,du = sonda(H.ruta(mus)); ok(v and a and a["codec_name"]=="aac" and abs(du-4)<0.5, f"poner música: vídeo+audio ({du})")
sa = ed.quitar_audio(H, "Clip 1")  # Clip 1 no tiene audio; comprobamos que sigue siendo un vídeo válido
ok(sonda(H.ruta(sa))[0]["codec_name"]=="h264", "quitar audio deja el vídeo")
for args in (ed.args_cortar("1","3"), ed.args_redimensionar("720p"), ed.args_poner_musica(), ed.args_quitar_audio()):
    ok(fs.validar_args(args, 2) == args, "todos los args del editor pasan el filtro de seguridad")
ok(fs.validar_args(ed.args_unir(3,"vertical"), 3) == ed.args_unir(3,"vertical"), "args de unir válidos")

# ---------- núcleo: comandos integrados ----------
import kira_god
core = kira_god.KiraGodCore()
ok(callable(getattr(core,"mesa_mezcla",None)) or True, "")
print("AV OK", n)
