# -*- coding: utf-8 -*-
"""Respuestas que aparecen mientras Kira piensa (streaming) con el modelo local y con Claude."""
import io, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import cerebro_ia_kira as ci
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

ok(ci.visible_parcial("<think>pienso") == "", "no enseña el razonamiento a medias")
ok(ci.visible_parcial("<think>a</think>Hola") == "Hola", "quita el razonamiento cerrado")
ok(ci.visible_parcial("Hola <think>x") == "Hola ", "corta donde empieza a razonar")

class Resp(io.BytesIO):
    status = 200
    def __enter__(s): return s
    def __exit__(s, *a): return False
def flujo_openai(trozos):
    lineas = [b"data: " + json.dumps({"choices": [{"delta": {"content": t}}]}).encode() + b"\n\n" for t in trozos]
    return Resp(b"".join(lineas) + b"data: [DONE]\n\n")
enviado = []
def abrir(req, timeout=0):
    if req.full_url.endswith("/health"):
        return Resp(b'{"status":"ok"}')
    enviado.append(json.loads(req.data))
    return flujo_openai(["<think>", "hmm", "</think>", "Hola", ", soy", " Kira", "."])
c = ci.Cerebro(T, abrir=abrir)
vistos = []
r = c.chat_local("sys", [{"role": "user", "content": "hola"}], al_trozo=vistos.append)
ok(enviado[-1]["stream"] is True, "pide la respuesta a trozos")
ok(r == "Hola, soy Kira.", "texto final limpio")
ok(vistos == ["Hola", "Hola, soy", "Hola, soy Kira", "Hola, soy Kira."], "va apareciendo poco a poco: " + repr(vistos))
ok(not any("hmm" in v for v in vistos), "nunca enseña el razonamiento")
def abrir_normal(req, timeout=0):
    return Resp(json.dumps({"choices": [{"message": {"content": "Respuesta entera"}}]}).encode())
ok(ci.Cerebro(T, abrir=abrir_normal).chat_local("s", [{"role": "user", "content": "x"}]) == "Respuesta entera", "sin trozos sigue igual")

# Claude por trozos (eventos SSE de la API)
import kira_god, red_kira
core = kira_god.KiraGodCore()
open(os.path.join(T, "api_key.txt"), "w").write("clave-de-prueba-1234567890")
core.cerebro_ia.poner_motor("claude")
eventos = [{"type": "message_start"}, {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Buenas"}},
           {"type": "content_block_delta", "delta": {"type": "text_delta", "text": " noches"}}, {"type": "message_stop"}]
cuerpo = b"".join(b"event: x\ndata: " + json.dumps(e).encode() + b"\n\n" for e in eventos)
pedido = {}
red_kira.abrir = lambda req, timeout=30: (pedido.update(json.loads(req.data)), Resp(cuerpo))[1]
vistos = []
r = core.conversar("hola", al_trozo=vistos.append)
ok(pedido.get("stream") is True and r == "Buenas noches" and vistos == ["Buenas", "Buenas noches"], "Claude también va apareciendo")

# la conversación pasa los trozos a la pantalla
import inicio_kira as ik
trozos = []
cv = ik.Conversacion(os.path.join(T, "c.json"), lambda t: "[i] No reconozco la orden", lambda t, h, al_trozo=None: (al_trozo("Ho"), al_trozo("Hola"), "Hola")[2])
ok(cv.preguntar("qué tal", al_trozo=trozos.append) == ("Hola", "charla") and trozos == ["Ho", "Hola"], "Conversacion reenvía los trozos")
cv2 = ik.Conversacion(os.path.join(T, "c2.json"), lambda t: "[i] No reconozco la orden", lambda t, h: "vieja")
ok(cv2.preguntar("qué tal", al_trozo=trozos.append) == ("vieja", "charla"), "funciones antiguas sin trozos siguen valiendo")
print("FLUJO OK", n)
