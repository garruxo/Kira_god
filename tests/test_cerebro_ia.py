# -*- coding: utf-8 -*-
"""Cerebro de IA: modelo local (servidor tipo llama-server, simulado por HTTP) o Claude; elección automática."""
import json, os, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import cerebro_ia_kira as ci
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

recibido = []
class Falso(BaseHTTPRequestHandler):
    respuesta = "<think>razono…</think>¡Hola! Soy Kira, en local."
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/health":
            b = b'{"status":"ok"}'; self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        else:
            self.send_response(404); self.end_headers()
    def do_POST(self):
        d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        recibido.append(d)
        b = json.dumps({"choices": [{"message": {"role": "assistant", "content": Falso.respuesta}}]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
srv = ThreadingHTTPServer(("127.0.0.1", 0), Falso); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}"

# ---------- limpieza de respuestas ----------
ok(ci.limpiar_respuesta("<think>a\nb</think>\nHola") == "Hola", "quita el razonamiento <think>")
ok(ci.limpiar_respuesta("<think>sin cerrar…") == "", "razonamiento cortado -> vacío")
ok(ci.limpiar_respuesta("Normal") == "Normal", "texto normal intacto")

# ---------- configuración ----------
c = ci.Cerebro(T)
ok(c.motor == "auto" and c.url == ci.URL_DEFECTO, "por defecto: auto y 127.0.0.1:8080")
for malo in ("ftp://x", "http://a b", "javascript:alert(1)", "http://x/ruta/rara?q=1"):
    try: c.poner_url(malo); ok(False, f"url {malo}")
    except ci.CerebroError: ok(True, "url inválida rechazada")
try: c.poner_motor("magia"); ok(False, "motor raro")
except ci.CerebroError: ok(True, "motor desconocido rechazado")
c.poner_url("http://127.0.0.1:1")          # nada escuchando
ok(c.local_disponible(forzar=True) is False, "sin servidor: apagado")
ok(c.elegir("") is None and c.elegir("clave") == "claude", "auto sin local: Claude si hay clave")
c.poner_url(URL)
ok(c.local_disponible(forzar=True) is True, "con servidor: encendido")
ok(c.elegir("") == "local" and c.elegir("clave") == "local", "auto con local: prefiere el local")
c.poner_motor("claude"); ok(c.elegir("clave") == "claude" and c.elegir("") is None, "modo claude: solo Claude")
c.poner_motor("local"); ok(c.elegir("clave") == "local", "modo local con servidor")
c2 = ci.Cerebro(T); ok(c2.motor == "local" and c2.url == URL, "la configuración persiste")
open(os.path.join(T, "cerebro.json"), "w").write("{roto"); ok(ci.Cerebro(T).motor == "auto", "archivo roto -> auto")
c.poner_motor("local"); c.poner_url(URL)

# ---------- chat con el modelo local ----------
r = c.chat_local("Eres Kira.", [{"role": "user", "content": "hola"}], max_tokens=5000)
ok(r == "¡Hola! Soy Kira, en local.", "responde y quita el razonamiento: " + r)
d = recibido[-1]
ok(d["messages"][0] == {"role": "system", "content": "Eres Kira."} and d["messages"][1]["content"] == "hola", "envía system + mensajes en formato OpenAI")
ok(d["max_tokens"] == ci.MAX_TOKENS_LOCAL, "limita la longitud para un modelo de móvil")
Falso.respuesta = "<think>solo pienso"
try: c.chat_local("", [{"role": "user", "content": "x"}]); ok(False, "vacía")
except ci.CerebroError: ok(True, "respuesta vacía -> error claro")
Falso.respuesta = "Hola, en local."
ok("ENCENDIDO" in c.estado_texto("") and "modelo local" in c.estado_texto(""), "estado legible")

# ---------- núcleo: Kira habla con el modelo local sin clave de Claude ----------
import kira_god
core = kira_god.KiraGodCore()
core.cerebro_ia.poner_url(URL); core.cerebro_ia.poner_motor("auto")
ok(core.cerebro_activo() == "local" and core.tiene_clave(), "sin clave pero con modelo local: tiene cerebro")
ok(core.conversar("hola") == "Hola, en local.", "la charla va al modelo local")
ok(not any("anthropic" in json.dumps(x) for x in recibido), "no se manda nada a Anthropic")
r = core.procesar_orden("cerebro"); ok("ENCENDIDO" in r and "auto" in r, "orden «cerebro»")
ok(core.procesar_orden("cerebro claude").startswith("[OK]") and core.cerebro_activo() is None, "modo claude sin clave: ningún cerebro")
try: core.conversar("hola"); ok(False, "sin cerebro")
except RuntimeError as e: ok("clave" in str(e).lower(), "sin cerebro: mensaje claro: " + str(e))
ok(core.procesar_orden("cerebro url: ftp://x").startswith("[x]"), "url mala por orden")
ok(core.procesar_orden("cerebro local").startswith("[OK]") and core.cerebro_activo() == "local", "modo local por orden")
srv.shutdown(); srv.server_close()
core.cerebro_ia._cache = (0.0, None)
try: core.conversar("hola"); ok(False, "local apagado")
except RuntimeError as e: ok("apagado" in str(e) and "Cerebro y oído" in str(e) and "Termux" not in str(e), "local apagado en modo local: lo dice (sin mandar a Termux): " + str(e))
ok(core.registrar_error("charla", "El cerebro local no responde en http://127.0.0.1:8080").startswith("Cómo arreglarlo"), "la bitácora sabe arreglarlo")
# con Claude como respaldo en auto
core.procesar_orden("cerebro auto"); core._leer_clave_api = lambda: "clave-falsa"
core.cerebro_ia._cache = (0.0, None)
llam = []
core._llamar_api.__func__  # existe
orig = kira_god.KiraGodCore._llamar_api
def falso_api(self, clave, system, usuario, max_tokens=4000, mensajes=None):
    llam.append(clave); return "Respuesta de Claude."
kira_god.KiraGodCore._llamar_api = falso_api
ok(core.conversar("hola") == "Respuesta de Claude." and llam == ["clave-falsa"], "auto con el local apagado: usa Claude")
kira_god.KiraGodCore._llamar_api = orig
print("CEREBRO IA OK", n)
