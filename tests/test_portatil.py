# -*- coding: utf-8 -*-
"""El cerebro de casa (portátil): token, cambio de cerebro, charla normal y a trozos, pintor (aparta el cerebro) y
faro. Con un llama-server y un sd-cli de mentira (scripts de Python), así se prueba sin gráfica ni modelos."""
import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import servidor_portatil as sp

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


LLAMA_FALSO = r'''
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
args = sys.argv[1:]
modelo = args[args.index("-m") + 1].split("/")[-1]
puerto = int(args[args.index("--port") + 1])
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"ok")
    def do_POST(self):
        d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        texto = "Soy " + modelo + " y me dices: " + d["messages"][-1]["content"]
        if d.get("stream"):
            self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
            for p in texto.split(" "):
                self.wfile.write(("data: " + json.dumps({"choices": [{"delta": {"content": p + " "}}]}) + "\n\n").encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
        else:
            b = json.dumps({"choices": [{"message": {"content": texto}}], "args": args}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
HTTPServer(("127.0.0.1", puerto), H).serve_forever()
'''

SD_FALSO = r'''
import sys
a = sys.argv[1:]
open(a[a.index("-o") + 1], "wb").write(b"\x89PNG\r\n\x1a\n" + " ".join(a).encode())
'''


def libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


with tempfile.TemporaryDirectory() as d:
    bin_, mod = os.path.join(d, "bin"), os.path.join(d, "modelos")
    os.makedirs(bin_)
    os.makedirs(mod)
    for nombre, codigo in (("llama-server", LLAMA_FALSO), ("sd-cli", SD_FALSO)):
        ruta = os.path.join(bin_, nombre)
        with open(ruta, "w") as f:
            f.write("#!" + sys.executable + "\n" + codigo)
        os.chmod(ruta, 0o755)
    cerebros, pintor_cfg = sp.config(False)
    for c in cerebros.values():
        open(os.path.join(mod, c["archivo"]), "w").write("x")
    open(os.path.join(mod, cerebros["rapido"]["ojos"]["archivo"]), "w").write("x")
    open(os.path.join(mod, pintor_cfg["archivo"]), "w").write("x")
    open(os.path.join(mod, pintor_cfg["vae"]["archivo"]), "w").write("x")

    TOKEN = "t" * 32
    cer = sp.Cerebro(os.path.join(bin_, "llama-server"), mod, cerebros, puerto=libre(), espera=20, avisar=lambda t: None)
    pin = sp.Pintor(os.path.join(bin_, "sd-cli"), mod, pintor_cfg, cer)
    puerto = libre()
    srv = sp.crear_servidor("127.0.0.1", puerto, TOKEN, cer, pin, nombre="portatil-prueba")
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def pedir(metodo, ruta, cuerpo=None, token=TOKEN):
        c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=30)
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        c.request(metodo, ruta, body=datos, headers={"X-Kira-Token": token, "Content-Type": "application/json"})
        r = c.getresponse()
        b = r.read()
        c.close()
        return r.status, b

    try:
        ok(pedir("GET", "/salud", token="")[0] == 200, "/salud sin token")
        ok(pedir("GET", "/hola", token="malo")[0] == 401 and pedir("POST", "/pintar", {"prompt": "x"}, token="")[0] == 401,
           "sin el token no se entra")
        st, b = pedir("GET", "/hola")
        h = json.loads(b)
        ok(st == 200 and h["tipo"] == "portatil" and set(h["instalados"]) == {"rapido", "grande"} and h["pintor"],
           "/hola dice qué cerebros y pintor tiene")
        st, b = pedir("POST", "/v1/chat/completions", {"messages": [{"role": "user", "content": "hola"}]})
        r = json.loads(b)
        ok(st == 200 and "9B" in r["choices"][0]["message"]["content"] and "hola" in r["choices"][0]["message"]["content"],
           "charla con el cerebro rápido (por defecto)")
        ok("--mmproj" in r["args"] and "--reasoning-budget" in r["args"], "con ojos y sin «pensar en voz alta»")
        st, b = pedir("POST", "/v1/chat/completions", {"kira_cerebro": "grande",
                                                       "messages": [{"role": "user", "content": "programa"}]})
        r = json.loads(b)
        ok(st == 200 and "35B" in r["choices"][0]["message"]["content"] and "--n-cpu-moe" in r["args"]
           and "kira_cerebro" not in json.dumps(r), "cambia al cerebro grande (expertos en la RAM)")
        c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=30)
        c.request("POST", "/v1/chat/completions", body=json.dumps({"stream": True, "messages": [
            {"role": "user", "content": "a trozos"}]}), headers={"X-Kira-Token": TOKEN})
        r = c.getresponse()
        texto = r.read().decode()
        ok(r.status == 200 and texto.count("data:") > 5 and "[DONE]" in texto and "9B" in texto,
           "la respuesta llega a trozos (stream) y vuelve al rápido")
        c.close()
        st, png = pedir("POST", "/pintar", {"prompt": "un gato", "ancho": 700, "alto": 2000, "semilla": 7})
        ok(st == 200 and png.startswith(b"\x89PNG") and b"-W 640" in png and b"-H 1024" in png and b"--vae" in png
           and b"-s 7" in png, "pinta (tamaño ajustado a múltiplos de 64 y con el VAE)")
        ok(cer.actual is None and not cer.vivo(), "mientras pinta, el cerebro deja la gráfica libre")
        st, b = pedir("POST", "/v1/chat/completions", {"messages": [{"role": "user", "content": "otra vez"}]})
        ok(st == 200 and cer.actual == "rapido", "tras pintar, el cerebro vuelve solo")
        os.remove(os.path.join(mod, cerebros["grande"]["archivo"]))
        st, b = pedir("POST", "/cerebro", {"usar": "grande"})
        ok(st == 200 and json.loads(b)["cargado"] == "rapido", "si falta el grande, usa el que hay")
        ok(pedir("POST", "/v1/chat/completions", None)[0] == 400, "una petición vacía no rompe nada")
    finally:
        cer.parar()
        srv.shutdown()

    # faro
    faro = sp.Faro(1234, "portatil-prueba", host="127.0.0.1", puerto=0)
    faro.start()
    faro.listo.wait(2)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2)
    s.sendto(sp.PREGUNTA, ("127.0.0.1", faro.puerto))
    r = json.loads(s.recvfrom(256)[0])
    ok(r == {"kira_portatil": 1, "puerto": 1234, "nombre": "portatil-prueba"}, "el faro contesta (sin el token)")
    faro.parar()

lista = sp.descargas()
ok(len(lista) == 6 and sum(b for _, _, b in lista) > 35e9 and all(u.startswith("https://huggingface.co/") for _, u, _ in lista),
   "descargas: 2 cerebros con ojos + pintor con VAE (~37 GB)")
ok(len(sp.descargas(sin_grande=True)) == 4 and len(sp.descargas(prueba=True)) == 2, "sin el grande / modo prueba")
# v2.82: modo LIGERO (portátil viejo sin gráfica): solo el 2B, poca memoria, sin pintor
lig = sp.descargas(ligero=True, ram=4000)
ok(len(lig) == 1 and lig[0][0].startswith("Qwen_Qwen3.5-2B"), "modo ligero con 4 GB: solo baja el cerebro 2B")
lig8 = sp.descargas(ligero=True, ram=7600)       # v3.45: con 8 GB, el grande es el 4B
ok([a for a, _, _ in lig8] == ["Qwen_Qwen3.5-2B-Q4_K_M.gguf", "Qwen_Qwen3.5-4B-Q4_K_M.gguf"],
   "modo ligero con 8 GB: 2B (charla) + 4B (pensar y programar)")
cf, _ = sp.config(ligero=True, ram=7600)
ok(cf["grande"]["archivo"].startswith("Qwen_Qwen3.5-4B") and "8192" in cf["grande"]["args"], "el grande ligero es el 4B")
ok(sp.ram_mb("/no/existe") == 0, "sin /proc/meminfo no inventa la RAM")
cl, pl = sp.config(ligero=True)
ok("-c" in cl["rapido"]["args"] and cl["rapido"]["args"][cl["rapido"]["args"].index("-c") + 1] == "4096",
   "modo ligero: poca memoria de conversación")
ok(not sp.Pintor("", "/tmp", pl, None).listo(), "modo ligero: sin pintor (y no peta)")
sh = open(os.path.join(RAIZ, "kira_portatil", "instalar_portatil.sh"), encoding="utf-8").read()
ok("--ligero) LIGERO=1" in sh and "/kira_swap" in sh and 'TRABAJOS=2' in sh, "el instalador tiene --ligero con intercambio")
ok('[ "$LIGERO" = "1" ] && OPC_SRV="--ligero"' in sh, "el servicio arranca en modo ligero")
r = subprocess.run(["bash", "-n", os.path.join(RAIZ, "kira_portatil", "instalar_portatil.sh")], capture_output=True)
ok(r.returncode == 0, "instalar_portatil.sh está bien escrito")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
