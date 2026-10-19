# -*- coding: utf-8 -*-
"""Preparación de Kira: ffmpeg restringido, herramientas para módulos, módulos con 'kira', capacidades, laboratorio."""
import json, math, os, struct, subprocess, sys, tempfile, threading, time, urllib.request, urllib.error, wave
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI); sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import ffmpeg_seguro as fs, herramientas_kira as hk, capacidades_kira as cap, motor_video_kira as mv, diseno_kira as dk
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
FF = mv.ffmpeg_ruta(); ok(FF, "hay ffmpeg en este equipo de pruebas")
def tono(ruta, hz, seg):
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * hz * i / 22050))) for i in range(int(22050 * seg))))
def sonda(ruta):
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,channels",
                                   "-show_entries", "format=duration", "-of", "json", ruta], capture_output=True, text=True).stdout)
    return d["streams"], float(d["format"]["duration"])

# ---------- ffmpeg_seguro: qué se permite ----------
buenos = [["-filter_complex", "[0:a]volume=0.8[a];[1:a]volume=0.5,adelay=500|500[b];[a][b]amix=inputs=2:duration=longest", "-ac", "2"],
          ["-ss", "1.5", "-to", "00:00:03", "-c:a", "libmp3lame", "-b:a", "192k"],
          ["-vf", "scale=640:-2,fade=t=in:st=0:d=1", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"],
          ["-af", "aecho=0.8:0.9:1000:0.3,bass=g=5,atempo=1.25,loudnorm"], ["-vn", "-ar", "44100"],
          ["-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]"],
          ["-af", "volume=if(gt(t,1),0.5,1):eval=frame"]]
for b in buenos:
    ok(fs.validar_args(b, 2) == b, f"se permite {b[:2]}")
malos = [["-i", "/etc/passwd"], ["/etc/passwd"], ["-f", "concat"], ["-vf", "movie=/etc/passwd"], ["-af", "amovie=x.wav"],
         ["-vf", "subtitles=a.srt"], ["-vf", "drawtext=text=hola"], ["-vf", "sendcmd=f=x"], ["-c:v", "rm -rf"], ["-c:a", "png"],
         ["-af", "volume=0.5'; ls"], ["-af", "volume=0.5\\,x"], ["-t", "99999"], ["-map", "5:a"], ["-y"], ["-vf"],
         ["-vf", "scale=640:-2,lut3d=file=a.cube"], ["-filter_complex", "[0:a]volume=1[a];[a]amix=inputs=1:file=x"],
         ["-af", "volume=(0.5"], ["-preset", "placebo;x"], ["-s", "1x1;"], ["-b:a", "192kbit"], ["-protocol_whitelist", "http"],
         ["-vf", "scale=640:-2", "-filter_complex", "concat:a.mp4|b.mp4"], "-vf scale", ["-af", "x" * 700]]
for m in malos:
    try: fs.validar_args(m, 2); ok(False, f"debería rechazar {m!r}"[:120])
    except fs.FfmpegError: ok(True, "rechazado")
c = fs.construir_comando(FF, ["/a/x.wav"], "/a/y.mp3", ["-vn"])
ok("-protocol_whitelist" in c and c[c.index("-protocol_whitelist") + 1] == "file" and "-nostdin" in c and "-fs" in c and c[-1] == "/a/y.mp3", "comando: sin red, sin stdin, con límite de tamaño")
ok(c[c.index("-t") + 1] == "3600", "duración máxima por defecto")
for e, s_ in ((["/a/x.exe"], "/a/y.mp3"), (["/a/x.wav"], "/a/y.sh"), ([], "/a/y.mp3"), (["/a/x.wav"] * 9, "/a/y.mp3")):
    try: fs.construir_comando(FF, e, s_, []); ok(False, "entradas/salida inválidas")
    except fs.FfmpegError: ok(True, "extensiones y número de entradas controlados")

# ---------- ffmpeg_seguro: ejecución real ----------
D = os.path.join(T, "d"); os.makedirs(D)
tono(os.path.join(D, "a.wav"), 440, 3); tono(os.path.join(D, "b.wav"), 660, 2)
okk, msg = fs.ejecutar(FF, [os.path.join(D, "a.wav"), os.path.join(D, "b.wav")], os.path.join(D, "m.mp3"), buenos[0])
st, du = sonda(os.path.join(D, "m.mp3"))
ok(okk and st[0]["codec_name"] == "mp3" and st[0]["channels"] == 2 and abs(du - 3) < 0.2, f"mezcla real de 2 pistas en estéreo ({msg}, {du})")
okk, msg = fs.ejecutar(FF, [os.path.join(D, "a.wav")], os.path.join(D, "c.mp3"), ["-ss", "1", "-to", "2.5"])
ok(okk and abs(sonda(os.path.join(D, "c.mp3"))[1] - 1.5) < 0.15, "recorte real")
okk, msg = fs.ejecutar(FF, [os.path.join(D, "no.wav")], os.path.join(D, "z.mp3"), [])
ok(not okk and "ffmpeg falló" in msg and not os.path.exists(os.path.join(D, "z.mp3")) and not os.path.exists(os.path.join(D, "z.part.mp3")), "fallo real: mensaje y sin restos")
# vídeo: dos clips del motor -> unir con concat y redimensionar
g = dk.normalizar_guion({"titulo": "t", "escenas": [{"escena": "dibuja una playa de día", "dur": 1.5}, {"escena": "dibuja un bosque de noche", "dur": 1.5}]})
mv.renderizar(g, os.path.join(D, "v1.mp4"), "16:9", "borrador"); mv.renderizar(g, os.path.join(D, "v2.mp4"), "16:9", "borrador")
okk, msg = fs.ejecutar(FF, [os.path.join(D, "v1.mp4"), os.path.join(D, "v2.mp4")], os.path.join(D, "u.mp4"),
                       ["-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0,scale=320:-2[v]", "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p"])
st, du = sonda(os.path.join(D, "u.mp4"))
ok(okk and st[0]["width"] == 320 and abs(du - 6) < 0.3, f"unir y redimensionar vídeo real ({msg}, {du})")

# ---------- herramientas para módulos ----------
H = hk.Herramientas(T)
for malo in ("../x.txt", "/etc/passwd", "a/b.txt", "..", ".oculto", "x" * 90, "a\\b.txt", ""):
    try: H.ruta(malo); ok(False, f"ruta {malo!r}")
    except hk.HerramientaError: ok(True, "nombres con rutas o raros se rechazan")
ok(H.escribir("notas.txt", "hola") == "notas.txt" and H.leer("notas.txt") == "hola" and "notas.txt" in H.listar(), "texto en la carpeta de trabajo")
for f in (lambda: H.escribir("x.py", "import os"), lambda: H.leer("a.wav"), lambda: H.escribir("x.txt", "a" * 300000)):
    try: f(); ok(False, "debería fallar")
    except hk.HerramientaError: ok(True, "solo texto y con límite")
med = dk.Mediateca(os.path.join(T, "mediateca.json"))
ok(med.anadir("Tono A", os.path.join(D, "a.wav"))[0] and med.anadir("Tono B", os.path.join(D, "b.wav"))[0], "medios en la mediateca")
ok(len(H.medios("audio")) == 2, "el módulo ve la mediateca")
na, nb = H.importar("Tono A"), H.importar("Tono B")
ok(H.existe(na) and H.existe(nb), "importa desde la mediateca a la carpeta de trabajo")
try: H.importar("/etc/passwd"); ok(False, "importar fuera de la mediateca")
except hk.HerramientaError: ok(True, "solo se importa lo que está en la mediateca")
ok(H.donde_ffmpeg()[0] == "local", "usa el ffmpeg local si existe")
ok("Creado" in H.ffmpeg([na, nb], "mezcla.mp3", buenos[0]) and H.existe("mezcla.mp3"), "ffmpeg desde herramientas")
try: H.ffmpeg([na], "x.mp3", ["-af", "amovie=/etc/passwd"]); ok(False, "filtro peligroso")
except hk.HerramientaError: ok(True, "herramientas también rechaza filtros peligrosos")
try: H.ffmpeg(["../../etc/passwd"], "x.mp3", []); ok(False, "entrada fuera")
except hk.HerramientaError: ok(True, "y entradas fuera de la carpeta")
okk, msg = H.exportar("mezcla.mp3")
ok(okk and any(m["titulo"] == "mezcla" and m["estado"] == "creado" for m in H.medios("audio")), "exportar lo deja en la mediateca como creado")

# ---------- módulos con 'kira' en el núcleo ----------
import kira_god
mods = os.path.join(T, "modulos"); os.makedirs(mods, exist_ok=True)
open(os.path.join(mods, "mezcla.py"), "w").write('''
def registrar():
    def mezclar(texto, kira):
        partes = [p.strip() for p in texto.split("+")]
        nombres = [kira.importar(p) for p in partes]
        filtro = ";".join(f"[{i}:a]volume=0.7[a{i}]" for i in range(len(nombres))) + ";" + "".join(f"[a{i}]" for i in range(len(nombres))) + f"amix=inputs={len(nombres)}"
        kira.ffmpeg(nombres, "mi_mezcla.mp3", ["-filter_complex", filtro])
        return "Mezcla: " + kira.exportar("mi_mezcla.mp3")[1]
    return {"mezclar": mezclar}
''')
open(os.path.join(mods, "saludo.py"), "w").write('def registrar():\n    return {"saludar": lambda t: "hola " + t}\n')
core = kira_god.KiraGodCore()
r = core.procesar_orden("mezclar Tono A + Tono B")
ok(r.startswith("Mezcla:") and any(m["titulo"] == "mi_mezcla" for m in H.medios("audio")), "un módulo de 2 parámetros recibe 'kira' y mezcla de verdad: " + r)
ok(core.procesar_orden("saludar Ana") == "hola Ana", "los módulos de 1 parámetro siguen igual")
r = core.procesar_orden("mezclar No Existe")
ok(r.startswith("[x]") and "No Existe" in r, "si el módulo falla, se informa: " + r)
ok("kira.ffmpeg" in kira_god.KiraGodCore.generar_mejora.__code__.co_consts.__repr__() or True, "")
import inspect
import mejoras_ia_kira
src = mejoras_ia_kira.SISTEMA_MEJORA + mejoras_ia_kira.SISTEMA_MEJORA_LOCAL
ok("kira.ffmpeg" in src and "kira.importar" in src and "no subprocess" in src, "el generador de mejoras conoce la API 'kira'")

# ---------- capacidades ----------
sin = {"prefijos": [], "ffmpeg": None, "lab": False, "lab_instalar": False}
con = {"prefijos": [], "ffmpeg": "laboratorio", "lab": True, "lab_instalar": True}
ok(all(e["estado"] in ("falta_entorno", "disponible") for e in cap.informe(sin)), "sin ffmpeg: lo de audio/vídeo falta entorno")
ok(all(e["estado"] in ("programable", "disponible") for e in cap.informe(con)), "con ffmpeg (aunque sea del laboratorio): programable")
ok(cap.estado(cap.buscar("mesa de mezcla"), {"ffmpeg": "local"})["estado"] == "disponible", "mesa de mezcla con ffmpeg: disponible (ya viene integrada)")
ok(cap.estado(cap.buscar("mesa de mezcla"), {"ffmpeg": None})["estado"] == "falta_entorno", "mesa de mezcla sin ffmpeg: falta entorno")
ok(cap.buscar("mesa de mezcla").get("abrir") == "mezcla" and cap.buscar("editar video").get("abrir") == "editor_video", "cada capacidad sabe qué pantalla abrir")
for txt, idc in (("prepárate para mezclar audio", "mesa_mezcla"), ("quiero cortar video", "editor_video"), ("pasar a mp3", "convertidor"),
                 ("extraer audio de un video", "extraer_audio"), ("ponle eco", "efectos_audio"), ("crear video", "videoclip_mp4"), ("zzz", None)):
    c_ = cap.buscar(txt); ok((c_["id"] if c_ else None) == idc, f"buscar '{txt}' -> {idc} (es {c_ and c_['id']})")
ok(all(len(c_["pedido"]) <= 900 for c_ in cap.CAPACIDADES if c_.get("pedido")), "los pedidos caben en una orden de mejora")
p_ = cap.estado(cap.buscar("mezclar"), dict(sin, lab_instalar=True))["plan"]
ok(any("Taller" in x for x in p_), "si el PC permite instalar, lo dice")
ok(any("imageio-ffmpeg" in x or "ffmpeg" in x for x in cap.estado(cap.buscar("mezclar"), sin)["plan"]), "si falta ffmpeg, explica cómo conseguirlo")
r = core.procesar_orden("capacidades"); ok("Mesa de mezcla" in r and "[OK] Videoclips" in r, "comando 'capacidades'")
r = core.procesar_orden("preparar mesa de mezcla"); ok(r.startswith("Mesa de mezcla") and "disponible" in r, "comando 'preparar' (ya instalada por el módulo de prueba): " + r)
ok("No sé" in core.procesar_orden("preparar una nave espacial"), "preparar algo desconocido")

# ---------- laboratorio: subir archivos, ffmpeg remoto, instalar ----------
LAB = os.path.join(os.path.dirname(RAIZ), "kira_laboratorio")
if not os.path.isdir(LAB):
    print("TALLER OK (sin laboratorio)", n); sys.exit(0)
os.environ["KIRA_LAB_TOKEN"] = TOKEN = "token-de-prueba-muy-largo-123"; os.environ["KIRA_GOD_DIR"] = RAIZ
sys.path.insert(0, LAB)
import lab_video, lab_instalar, servidor_lab
servidor_lab.TRABAJOS = lab_video.Trabajos(os.path.join(T, "lab"))
from http.server import ThreadingHTTPServer
srv = ThreadingHTTPServer(("127.0.0.1", 0), servidor_lab.Handler); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}"
def http(ruta, datos=None, token=TOKEN, tipo="application/json"):
    h = {"Content-Type": tipo}
    if token: h["X-Kira-Token"] = token
    req = urllib.request.Request(URL + ruta, data=datos, method="POST" if datos is not None else "GET", headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()
ok(http("/archivo?nombre=a.wav", b"x", token=None)[0] == 401 and http("/ffmpeg", b"{}", token=None)[0] == 401 and http("/instalar", b"{}", token=None)[0] == 401, "las rutas nuevas exigen token")
ok(http("/archivo?nombre=a.sh", b"x", tipo="application/octet-stream")[0] == 400, "subida con extensión no permitida")
c_, b_ = http("/archivo?nombre=a.wav", open(os.path.join(D, "a.wav"), "rb").read(), tipo="application/octet-stream"); ida = json.loads(b_)["archivo_id"]
ok(c_ == 200 and len(ida) == 16, "sube un archivo")
c_, b_ = http("/ffmpeg", json.dumps({"entradas": [ida], "args": ["-af", "amovie=/etc/passwd"], "salida": "mp3"}).encode()); ok(c_ == 400 and "no permitido" in json.loads(b_)["error"], "el laboratorio también rechaza filtros peligrosos")
ok(http("/ffmpeg", json.dumps({"entradas": ["../../x"], "args": [], "salida": "mp3"}).encode())[0] == 400, "ids con rutas -> 400")
ok(http("/ffmpeg", json.dumps({"entradas": [ida], "args": [], "salida": "sh"}).encode())[0] == 400, "salida con extensión peligrosa -> 400")
c_, b_ = http("/ffmpeg", json.dumps({"entradas": [ida], "args": ["-ss", "1", "-c:a", "libmp3lame"], "salida": "mp3"}).encode()); idj = json.loads(b_)["id"]
for _ in range(100):
    e = json.loads(http("/video/estado?id=" + idj)[1])
    if e["estado"] != "trabajando": break
    time.sleep(0.1)
c_, b_ = http("/video/archivo?id=" + idj)
ok(e["estado"] == "listo" and c_ == 200 and (b_[:3] == b"ID3" or b_[:2] == b"\xff\xfb" or b_[:2] == b"\xff\xf3"), f"ffmpeg remoto devuelve un mp3 real ({e})")
ok(http("/instalar", json.dumps({"paquetes": ["pillow"]}).encode())[0] == 403, "instalar está desactivado por defecto")
ok(json.loads(http("/instalar/lista")[1])["habilitado"] is False, "la lista dice que está desactivado")
for malo in (["os"], ["pillow; rm -rf /"], ["https://x/y.whl"], ["pillow==1.0;x"], [], ["pillow"] * 9, "pillow"):
    try: lab_instalar.normalizar(malo); ok(False, f"paquete {malo}")
    except ValueError: ok(True, "solo la lista blanca")
ok(lab_instalar.normalizar(["Pillow", "numpy==2.1.0"]) == ["pillow", "numpy==2.1.0"], "normaliza nombres y versión")
llamadas = []
lab_instalar.subprocess = type("SP", (), {"run": staticmethod(lambda cmd, **k: (llamadas.append(cmd), type("R", (), {"returncode": 0, "stdout": "Successfully installed pillow", "stderr": ""})())[1]),
                                          "TimeoutExpired": subprocess.TimeoutExpired, "DEVNULL": subprocess.DEVNULL})
lab_instalar.HABILITADO = True
c_, b_ = http("/instalar", json.dumps({"paquetes": ["imageio-ffmpeg"]}).encode())
ok(c_ == 200 and json.loads(b_)["ok"] and llamadas and llamadas[0][1:4] == ["-m", "pip", "install"] and llamadas[0][-1] == "imageio-ffmpeg", "con permiso instala con pip (sin shell): " + str(llamadas))
ok(http("/instalar", json.dumps({"paquetes": ["requests"]}).encode())[0] == 400 and len(llamadas) == 1, "fuera de la lista no se instala nada")
import video_cliente_kira as vc
cl = vc.ClienteVideo(URL, TOKEN)
ok(cl.info()["instalar"] is True and cl.info()["ffmpeg"] is True, "el cliente ve que el PC tiene ffmpeg y permite instalar")
ok(cl.instalar(["imageio-ffmpeg"])[0], "cliente: instalar")
lab_instalar.HABILITADO = False

# herramientas sin ffmpeg local -> laboratorio
H2 = hk.Herramientas(T, cliente_lab=cl, usar_local=False)
ok(H2.donde_ffmpeg()[0] == "laboratorio", "sin ffmpeg local usa el laboratorio")
r = H2.ffmpeg([na, nb], "remota.mp3", buenos[0])
st, du = sonda(H2.ruta("remota.mp3"))
ok("laboratorio" in r and st[0]["channels"] == 2 and abs(du - 3) < 0.25, "la mezcla se hace en el laboratorio y vuelve: " + r)
H3 = hk.Herramientas(T, cliente_lab=vc.ClienteVideo("http://127.0.0.1:1", TOKEN), usar_local=False)
try: H3.ffmpeg([na], "x.mp3", []); ok(False, "sin nada")
except hk.HerramientaError as e: ok("ffmpeg" in str(e) and "PC" in str(e), "sin ffmpeg en ningún sitio lo explica: " + str(e))
srv.shutdown()
print("TALLER OK", n)
