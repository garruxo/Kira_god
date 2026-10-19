# -*- coding: utf-8 -*-
"""Motor de vídeo REAL: genera MP4 de verdad (ffmpeg + Pillow), servidor del laboratorio por HTTP y cliente del móvil."""
import json, os, struct, subprocess, sys, tempfile, threading, time, urllib.request, urllib.error, wave, math
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import diseno_kira as dk, motor_video_kira as mv, video_cliente_kira as vc
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

def sonda(ruta):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,duration",
                          "-show_entries", "format=duration", "-of", "json", ruta], capture_output=True, text=True).stdout
    d = json.loads(out)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    return v, a, float(d["format"]["duration"])

def brillo(ruta, t):
    from PIL import Image, ImageStat
    png = os.path.join(T, f"f{abs(hash((ruta, t)))}.png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t), "-i", ruta, "-frames:v", "1", png], check=True)
    im = Image.open(png).convert("L"); return ImageStat.Stat(im).mean[0], im.tobytes()

info = mv.info_motor()
ok(info["listo"], "este equipo puede crear vídeo: " + info["motivo"])
corto = dk.normalizar_guion({"titulo": "Prueba", "escenas": [
    {"titulo": "Uno", "plano": "general", "texto": "Una playa de día.", "escena": "dibuja una playa de día", "dur": 2},
    {"titulo": "Dos", "plano": "detalle", "texto": "Un bosque de noche.", "escena": "dibuja un bosque de noche", "dur": 2},
    {"titulo": "Tres", "plano": "", "texto": "El espacio.", "escena": "dibuja el espacio de noche", "dur": 2}]})

# ---------- utilidades puras ----------
for f, c, esperado in (("16:9", "borrador", (640, 360, 15)), ("9:16", "borrador", (360, 640, 15)), ("4:3", "normal", (720, 540, 24)), ("16:9", "alta", (1280, 720, 30))):
    ok(mv.dimensiones(f, c) == esperado, f"dimensiones {f} {c}: {mv.dimensiones(f, c)}")
for malo in (("21:9", "normal"), ("16:9", "ultra")):
    try: mv.dimensiones(*malo); ok(False, f"debería rechazar {malo}")
    except mv.MotorError: ok(True, "rechaza formato/calidad desconocidos")
for i in range(4):
    for k in range(11):
        z, ux, uy = mv.vista(i, k / 10)
        ok(z >= 1.0 and abs(ux) <= 1.0 and abs(uy) <= 1.0, f"cámara {i}@{k}: dentro de la imagen")
ok(mv.vista(0, 0)[0] == 1.0 and mv.vista(0, 1)[0] > 1.1 and mv.vista(1, 0)[0] > mv.vista(1, 1)[0], "zoom in / zoom out")

# ---------- render real ----------
prog = []
r = mv.renderizar(corto, os.path.join(T, "a", "b.mp4"), "4:3", "borrador", progreso=prog.append)
v, a, dur = sonda(r["ruta"])
ok(v["codec_name"] == "h264" and (v["width"], v["height"]) == (480, 360) and abs(dur - 6) < 0.2 and a is None, f"MP4 H.264 480x360, 6 s, sin audio ({v}, {dur})")
ok(r["fotogramas"] == 90 and r["bytes"] > 5000 and not os.path.exists(r["ruta"] + ".part.mp4"), "metadatos correctos y sin restos .part")
ok(prog and prog == sorted(prog) and prog[-1] == 1.0, "el progreso crece hasta 1.0")
b0, px0 = brillo(r["ruta"], 0.0); b1, px1 = brillo(r["ruta"], 1.2); b2, px2 = brillo(r["ruta"], 3.0)
ok(b0 < 12 and b1 > 40, f"empieza a negro y luego se ve ({b0:.0f} -> {b1:.0f})")
ok(px1 != px2, "el contenido cambia entre escenas")
r2 = mv.renderizar(corto, os.path.join(T, "v.mp4"), "9:16", "borrador")
v, a, dur = sonda(r2["ruta"]); ok((v["width"], v["height"]) == (360, 640), "formato vertical 9:16")
ok(sonda(mv.renderizar(corto, os.path.join(T, "w.mp4"), "16:9", "normal")["ruta"])[0]["width"] == 960, "16:9 normal = 960x540")

# ---------- audio ----------
wav = os.path.join(T, "tono.wav")
with wave.open(wav, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
    w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / 22050))) for i in range(22050 * 3)))   # 3 s < 6 s
r3 = mv.renderizar(corto, os.path.join(T, "au.mp4"), "4:3", "borrador", audio=wav)
v, a, dur = sonda(r3["ruta"])
ok(a and a["codec_name"] == "aac" and abs(dur - 6) < 0.3, f"con audio: pista AAC y misma duración ({a}, {dur})")
for malo in (os.path.join(T, "no.wav"), os.path.join(T, "a", "b.mp4"), wav + ".exe"):
    try: mv.renderizar(corto, os.path.join(T, "x.mp4"), audio=malo); ok(False, f"audio inválido {malo}")
    except mv.MotorError: ok(True, "audio inexistente o con extensión no permitida se rechaza")
try: mv.renderizar(corto, os.path.join(T, "x.avi")); ok(False, "salida no mp4")
except mv.MotorError: ok(True, "la salida debe ser .mp4")
try: mv.renderizar({"titulo": "x", "escenas": []}, os.path.join(T, "x.mp4")); ok(False, "guion vacío")
except mv.MotorError: ok(True, "guion inválido -> MotorError")
ev = threading.Event(); ev.set()
try: mv.renderizar(corto, os.path.join(T, "c.mp4"), cancelar=ev); ok(False, "cancelar")
except mv.MotorError as e: ok("Cancelado" in str(e) and not os.path.exists(os.path.join(T, "c.mp4")) and not os.path.exists(os.path.join(T, "c.mp4.part.mp4")), "cancelar no deja archivos")
# ffmpeg que falla: se cuenta la verdad
falso = os.path.join(T, "ffmpeg_falso.sh")
open(falso, "w").write("#!/bin/sh\nif [ \"$2\" = \"-encoders\" ] || [ \"$1\" = \"-hide_banner\" ] && [ \"$2\" = \"-encoders\" ]; then echo ' V....D libx264 x'; exit 0; fi\ncat >/dev/null\necho boom >&2\nexit 1\n")
os.chmod(falso, 0o755); viejo = os.environ.get("KIRA_FFMPEG"); os.environ["KIRA_FFMPEG"] = falso
try: mv.renderizar(corto, os.path.join(T, "f.mp4"), "4:3", "borrador"); ok(False, "ffmpeg roto")
except mv.MotorError as e: ok("ffmpeg falló" in str(e) and "boom" in str(e) and not os.path.exists(os.path.join(T, "f.mp4")), "si ffmpeg falla, lo dice y no deja un MP4 falso: " + str(e))
os.environ["KIRA_FFMPEG"] = "/ruta/que/no/existe"; os.environ["PATH"], pathv = "/nonexistent", os.environ["PATH"]
sin = mv.info_motor(); os.environ["PATH"] = pathv
os.environ.pop("KIRA_FFMPEG")
if viejo: os.environ["KIRA_FFMPEG"] = viejo
ok(sin["ffmpeg"] is None or "imageio" in (sin["ffmpeg"] or ""), "KIRA_FFMPEG inválido se ignora")

# ---------- laboratorio por HTTP ----------
LAB = os.path.join(os.path.dirname(RAIZ), "kira_laboratorio")
if not os.path.isdir(LAB):
    print("VIDEO OK (sin laboratorio al lado: se omiten las pruebas HTTP)", n); sys.exit(0)
os.environ["KIRA_LAB_TOKEN"] = TOKEN = "token-de-prueba-muy-largo-123"
os.environ["KIRA_GOD_DIR"] = RAIZ
sys.path.insert(0, LAB)
import lab_video, servidor_lab
servidor_lab.TRABAJOS = lab_video.Trabajos(os.path.join(T, "lab"))
from http.server import ThreadingHTTPServer
srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor_lab.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}"
def http(ruta, datos=None, token=TOKEN, metodo=None, tipo="application/json"):
    h = {"Content-Type": tipo}
    if token is not None: h["X-Kira-Token"] = token
    req = urllib.request.Request(URL + ruta, data=datos, method=metodo or ("POST" if datos is not None else "GET"), headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()
def jhttp(*a, **k):
    c, b = http(*a, **k); return c, json.loads(b.decode())

ok(jhttp("/salud", token=None)[0] == 200, "/salud sin token")
for ruta in ("/video/capacidad", "/video/estado?id=" + "0" * 16, "/video/archivo?id=" + "0" * 16):
    ok(http(ruta, token=None)[0] == 401 and http(ruta, token="mal")[0] == 401, f"{ruta}: exige token")
for ruta in ("/video", "/audio?nombre=a.mp3", "/probar"):
    ok(http(ruta, b"{}", token=None)[0] == 401, f"POST {ruta}: exige token")
ok(jhttp("/video/capacidad")[1]["ok"], "capacidad: el laboratorio puede crear vídeo")
ok(jhttp("/video", b"no json")[0] == 400, "petición mal formada -> 400")
c, d = jhttp("/video", json.dumps({"guion": {"titulo": "x", "escenas": []}}).encode()); ok(c == 400 and not d["ok"], "guion inválido -> 400")
c, d = jhttp("/video", json.dumps({"guion": corto, "formato": "99:1"}).encode()); ok(c == 400, "formato inválido -> 400")
c, d = jhttp("/video", json.dumps({"guion": corto, "audio_id": "../../etc/passwd"}).encode()); ok(c == 400, "audio_id con ruta -> 400")
c, d = jhttp("/video", json.dumps({"guion": corto, "audio_id": "0" * 16}).encode()); ok(c == 400 and "audio" in d["error"].lower(), "audio_id inexistente -> 400")
ok(http("/audio?nombre=x.exe", b"abc", tipo="application/octet-stream")[0] == 400, "audio con extensión peligrosa -> 400")
ok(http("/audio?nombre=x.mp3", b"", tipo="application/octet-stream")[0] in (400, 413) , "audio vacío rechazado")
c, d = jhttp("/video", json.dumps({"guion": corto, "formato": "4:3", "calidad": "borrador"}).encode()); ok(c == 200 and len(d["id"]) == 16, "acepta el trabajo")
id_ = d["id"]
for _ in range(200):
    e = jhttp("/video/estado?id=" + id_)[1]
    if e["estado"] != "trabajando": break
    time.sleep(0.1)
ok(e["estado"] == "listo" and e["info"]["fotogramas"] == 90, f"el trabajo termina: {e}")
c, cuerpo = http("/video/archivo?id=" + id_)
ok(c == 200 and cuerpo[4:8] == b"ftyp" and len(cuerpo) == e["info"]["bytes"], "descarga un MP4 real (cabecera ftyp, tamaño exacto)")
ok(http("/video/archivo?id=../../etc/passwd")[0] == 404 and http("/video/estado?id=zzz")[0] == 404 and http("/video/archivo?id=" + "1" * 16)[0] == 404, "ids inválidos o ajenos -> 404")
c, d = jhttp("/audio?nombre=musica.wav", open(wav, "rb").read(), tipo="application/octet-stream"); ok(c == 200 and len(d["audio_id"]) == 16, "sube audio")
c, d2 = jhttp("/video", json.dumps({"guion": corto, "formato": "4:3", "calidad": "borrador", "audio_id": d["audio_id"]}).encode()); ok(c == 200, "vídeo con audio aceptado")
for _ in range(200):
    e = jhttp("/video/estado?id=" + d2["id"])[1]
    if e["estado"] != "trabajando": break
    time.sleep(0.1)
dest = os.path.join(T, "desde_lab.mp4"); open(dest, "wb").write(http("/video/archivo?id=" + d2["id"])[1])
ok(e["estado"] == "listo" and sonda(dest)[1] is not None, "el MP4 del laboratorio lleva la música")
# límite de trabajos simultáneos
largo = dk.normalizar_guion({"titulo": "L", "escenas": [{"texto": "a", "escena": "dibuja una ciudad de noche", "dur": 12} for _ in range(4)]})
res = [jhttp("/video", json.dumps({"guion": largo, "formato": "16:9", "calidad": "alta"}).encode())[0] for _ in range(3)]
ok(res == [200, 200, 400], f"máx. 2 vídeos a la vez ({res})")
ok(http("/nada")[0] == 404 and http("/nada", b"{}")[0] == 404, "rutas desconocidas -> 404")

# el cliente espera su turno si el laboratorio está ocupado (aquí: los 2 vídeos largos siguen en marcha)
ocupado = vc.ClienteVideo(URL, TOKEN)
try: ocupado.renderizar(largo, "16:9", "alta"); ok(False, "debería estar ocupado")
except vc.VideoError as e: ok("ocupado" in str(e), "cliente: el laboratorio ocupado se nota")
# ---------- cliente del móvil ----------
vc.motor_local_listo = lambda: (False, "sin ffmpeg local")
(T2 := os.path.join(T, "movil")); cl = vc.ClienteVideo(URL, TOKEN)
ok(cl.capacidad()[0], "cliente: capacidad")
ok(vc.ClienteVideo(URL, "mal").capacidad()[0] is False, "cliente: token incorrecto")
pc_ = vc.pc.PasarelaCliente
vc.ClienteVideo = lambda url=None, token=None, _c=vc.ClienteVideo: _c(URL, TOKEN)
ok(vc.donde_se_renderiza()[0] == "laboratorio", "elige el laboratorio cuando no hay ffmpeg local")
marcas = []
donde, inf = vc.crear_video(corto, os.path.join(T2, "x.mp4"), "4:3", "borrador", audio=wav, progreso=lambda f, t: marcas.append((f, t)), sondeo=0.1)
v, a, dur = sonda(os.path.join(T2, "x.mp4"))
ok(donde == "laboratorio" and v["codec_name"] == "h264" and a is not None and abs(dur - 6) < 0.3, "cliente: vídeo con música creado por el laboratorio y descargado")
ok(marcas[-1][0] == 1.0 and [f for f, _ in marcas] == sorted(f for f, _ in marcas) and any("laboratorio" in t.lower() for _, t in marcas), "cliente: progreso coherente")
try: vc.crear_video(corto, os.path.join(T2, "y.mp4"), "4:3", "borrador", audio=os.path.join(T, "no.mp3")); ok(False, "audio inexistente")
except vc.VideoError: ok(True, "cliente: audio inexistente -> VideoError")
vc.motor_local_listo = lambda: (True, "")
ok(vc.donde_se_renderiza()[0] == "local", "con ffmpeg local se usa el local")
donde, inf = vc.crear_video(corto, os.path.join(T2, "z.mp4"), "9:16", "borrador"); ok(donde == "local" and sonda(os.path.join(T2, "z.mp4"))[0]["height"] == 640, "cliente: render local")
vc.motor_local_listo = lambda: (False, "sin ffmpeg local")
vc.ClienteVideo = lambda url=None, token=None: type(cl)("http://127.0.0.1:1", TOKEN)
try: vc.crear_video(corto, os.path.join(T2, "w.mp4")); ok(False, "sin nada")
except vc.VideoError as e: ok("Aquí:" in str(e) and "Laboratorio:" in str(e) and not os.path.exists(os.path.join(T2, "w.mp4")), "sin motor ni laboratorio: lo explica, no finge")
srv.shutdown()
print("VIDEO OK", n)
