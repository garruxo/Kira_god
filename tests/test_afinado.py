# -*- coding: utf-8 -*-
"""v2.31: Kira aprende de sus mejoras: las aprobadas son ejemplos propios al programar; datos de entrenamiento JSONL;
instalar y quitar un ajuste LoRA (GGUF) que el cerebro del móvil carga con --lora (servidor y motor FALSOS)."""
import http.server, json, os, sys, tempfile, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import afinado_kira as af, saber_mejoras_kira as sm_, cerebro_ia_kira as ci
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# una mejora aprobada por el dueño (instalada + lección «aprobada»)
import kira_god, panel_kira as pk
core = kira_god.KiraGodCore()
ctl = pk.PanelControl(core)
MOD = ("def registrar():\n    def convierte(texto):\n        euros = float(texto.split()[0])\n"
       "        return f'{euros * 1.08:.2f} dólares'\n    return {'convierte euros': convierte}\n")
ctl.probar_codigo(MOD, "euros_dolares", "Mejora para Kira: que convierta euros a dólares")
ok(ctl.aplicar(True)["ok"], "aprobada e instalada")
p = af.recetas_propias()
ok(len(p) == 1 and p[0]["titulo"] == "que convierta euros a dólares" and "convierte euros" in p[0]["codigo"],
   "se convierte en una receta propia, con el pedido con que la aprobaste")
c = sm_.contexto_para("convierte libras a euros y dólares", local=True)
ok("APROBÓ" in c and "convierte euros" in c, "al pedir algo parecido, su cerebro la recibe como ejemplo")
ok("APROBÓ" not in sm_.contexto_para("hazme un juego de naves", local=True), "si no se parece, no")

# datos de entrenamiento
r = core.procesar_orden("prepara datos de entrenamiento")
ruta = os.path.join(core.dir, "entrenamiento", "kira_mejoras.jsonl")
filas = [json.loads(l) for l in open(ruta, encoding="utf-8")]
ok(r.startswith("[OK]") and "1 son mejoras tuyas" in r and len(filas) > 50, "JSONL listo: " + r[:80])
ok(all([m["role"] for m in f["messages"]] == ["system", "user", "assistant"] for f in filas) and
   filas[0]["origen"] == "propia" and "NOMBRE: euros_dolares" in filas[0]["messages"][2]["content"],
   "formato de chat; lo tuyo, primero")
ok("solo funciona en el móvil" in core.procesar_orden("prepara datos de entrenamiento y guárdalos en descargas"),
   "a Descargas: en el móvil")

# instalar y quitar un ajuste
GGUF = b"GGUF" + b"\x00" * 100
class Web(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        d = GGUF if self.path == "/kira_lora.gguf" else b"<html>no</html>"
        self.send_response(200); self.send_header("Content-Length", str(len(d))); self.end_headers(); self.wfile.write(d)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Web)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}"
cer = core.cerebro_propio
ok("sin ajustes" in core.procesar_orden("mi ajuste"), "sin ajuste al principio")
ok(core.procesar_orden(f"instala mi ajuste: {URL}/otra.gguf").startswith("[x] Eso no es un adaptador GGUF"), "comprueba que es GGUF")
r = core.procesar_orden(f"instala mi ajuste: {URL}/kira_lora.gguf")
ok(r.startswith("[OK] Ajuste instalado") and cer.tiene_ajuste(), "instala el ajuste: " + r)
args = cer._argumentos("motor")
ok("--lora" in args and args[args.index("--lora") + 1] == cer.ruta_ajuste(), "el cerebro lo carga con --lora")
ok("Llevo tu ajuste" in core.procesar_orden("mi ajuste"), "«mi ajuste» lo dice")
ok(core.procesar_orden("quita mi ajuste").startswith("[OK]") and "--lora" not in cer._argumentos("motor"), "y se quita")
srv.shutdown()
print("AFINADO OK", n)
