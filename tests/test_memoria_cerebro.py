# -*- coding: utf-8 -*-
"""v2.30: «no se pudo hablar con el modelo local: timed out». Lo que se le da al cerebro del móvil cabe en su memoria
de trabajo (2048 fichas con lo que escribe), las mejoras para él llevan instrucciones cortas, los pedidos esperan su
turno (no se pisan) y, si tarda demasiado, lo dice claro."""
import os, socket, sys, tempfile, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import cerebro_ia_kira as ci, mejoras_ia_kira as mi
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

def cabe(msgs, mt): return sum(ci.fichas_aprox(m["content"]) for m in msgs) + mt + 64 <= ci.CTX_LOCAL
m, t = ci.ajustar_a_contexto([{"role": "system", "content": "s" * 2000}, {"role": "user", "content": "INICIO " + "x" * 9000 + " FINAL"}], 1024)
ok(cabe(m, t) and t >= 400, f"un pedido larguísimo se recorta para que quepa ({t} fichas para escribir)")
ok(m[0]["content"] == "s" * 2000 and m[1]["content"].startswith("INICIO") and m[1]["content"].endswith("FINAL") and "[…]" in m[1]["content"],
   "se recorta por el medio el mensaje largo; las instrucciones no se tocan")
m2, t2 = ci.ajustar_a_contexto([{"role": "user", "content": "hola"}], 512)
ok(m2[0]["content"] == "hola" and t2 == 512, "lo corto, tal cual")

# instrucciones cortas para el cerebro del móvil
ok(mi.sistema_local("que convierta euros a dólares") == mi.SISTEMA_MEJORA_LOCAL_CORTO and
   len(mi.SISTEMA_MEJORA_LOCAL_CORTO) < 900, "una mejora sencilla: instrucciones cortas")
ok(mi.sistema_local("un juego de naves") == mi.SISTEMA_MEJORA_LOCAL and
   mi.sistema_local("que suba el volumen de una canción") == mi.SISTEMA_MEJORA_LOCAL, "juegos y audio: las completas")

# lo que de verdad recibe el cerebro del móvil al programar una mejora cabe (sin el mapa del proyecto)
import kira_god, panel_kira as pk
core = kira_god.KiraGodCore()
core.procesar_orden("estudia ingeniería")
vio = []
core._leer_clave = lambda *a: ci.LOCAL
def api(clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None):
    vio.append((system, usuario))
    return "NOMBRE: x\n```python\ndef registrar():\n    return {'xx': lambda t: t}\n```"
core._llamar_api = api
ctl = pk.PanelControl(core)
for pedido in ("Mejora para Kira: que convierta euros a dólares", "Mejora para Kira: que calcule el camino más corto entre ciudades"):
    vio.clear(); ctl.enviar_orden(pedido)
    s, u = vio[0]
    ok("<bitacora>" not in u, "al cerebro del móvil no le llega el mapa del proyecto (no le cabe)")
    ok(ci.fichas_aprox(s) + ci.fichas_aprox(u) + 600 < ci.CTX_LOCAL, f"cabe con sitio para escribir: {len(s) + len(u)} letras")

# un pedido cada vez: el segundo espera su turno (antes se pisaban y uno daba «timed out»)
import http.server, json
dentro, max_dentro = [0], [0]
class Lento(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        dentro[0] += 1; max_dentro[0] = max(max_dentro[0], dentro[0])
        time.sleep(0.4)
        dentro[0] -= 1
        cuerpo = b'data: {"choices":[{"delta":{"content":"vale"}}]}\n\ndata: [DONE]\n\n'
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
        self.wfile.write(cuerpo)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Lento)
threading.Thread(target=srv.serve_forever, daemon=True).start()
C = ci.CerebroIA(os.path.join(T, "c.json")) if hasattr(ci, "CerebroIA") else ci.Cerebro(os.path.join(T, "c.json"))
C.url = f"http://127.0.0.1:{srv.server_address[1]}"
res = []
hilos = [threading.Thread(target=lambda: res.append(C.chat_local("s", [{"role": "user", "content": "hola"}], 100,
                                                                    al_trozo=lambda t: None))) for _ in range(3)]
for h in hilos: h.start()
for h in hilos: h.join(10)
ok(res == ["vale"] * 3 and max_dentro[0] == 1, f"tres pedidos a la vez: de uno en uno ({max_dentro[0]} a la vez)")
srv.shutdown()

# si tarda demasiado, lo dice claro
mudo = socket.socket(); mudo.bind(("127.0.0.1", 0)); mudo.listen(1)
C.url = f"http://127.0.0.1:{mudo.getsockname()[1]}"
try:
    C.chat_local("s", [{"role": "user", "content": "hola"}], 50, timeout=1); ok(False, "debía tardar")
except ci.CerebroError as e:
    ok("tardado demasiado" in str(e) and "cerebro ligero" in str(e), "«timed out» explicado: " + str(e))
print("MEMORIA CEREBRO OK", n)
