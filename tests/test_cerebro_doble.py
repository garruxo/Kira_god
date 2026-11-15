# -*- coding: utf-8 -*-
"""v3.70: los dos cerebros del portátil cargados a la vez (2B para charlar, 4B para tareas), con llama-server de mentira."""
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
    os.makedirs(bin_); os.makedirs(mod)
    ruta = os.path.join(bin_, "llama-server")
    with open(ruta, "w") as f:
        f.write("#!" + sys.executable + "\n" + LLAMA_FALSO)
    os.chmod(ruta, 0o755)
    cerebros, pintor_cfg = sp.config(ligero=True, ram=7580)       # el Packard Bell: 7,4 GiB
    open(os.path.join(mod, cerebros["rapido"]["archivo"]), "w").write("x")

    ok(isinstance(sp.cerebro_para_equipo(ruta, mod, cerebros, ram=7580), sp.CerebroDoble),
       "con 7,4 GB: los dos cerebros a la vez")
    ok(type(sp.cerebro_para_equipo(ruta, mod, cerebros, ram=6500)) is sp.Cerebro,
       "con menos de 7 GB: uno cada vez, como siempre")
    cg, _ = sp.config()
    ok(type(sp.cerebro_para_equipo(ruta, mod, cg, ram=32000, doble=False)) is sp.Cerebro,
       "con gráfica (no ligero): uno cada vez (no caben los dos en la gráfica)")
    c4, _ = sp.config(ligero=True, ram=4000)
    ok(type(sp.cerebro_para_equipo(ruta, mod, c4, ram=16000)) is sp.Cerebro,
       "si los dos son el mismo cerebro (2B), uno solo")

    base = libre()
    while True:                                   # dos puertos seguidos libres
        try:
            s2 = socket.socket(); s2.bind(("127.0.0.1", base + 1)); s2.close(); break
        except OSError:
            base = libre()
    cer = sp.cerebro_para_equipo(ruta, mod, cerebros, ram=7580, puerto=base, espera=20, avisar=lambda t: None)
    pin = sp.Pintor("", mod, pintor_cfg, cer)
    puerto = libre()
    srv = sp.crear_servidor("127.0.0.1", puerto, "t" * 32, cer, pin, nombre="doble")
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def charla(quien, txt):
        c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=30)
        c.request("POST", "/v1/chat/completions", body=json.dumps({"kira_cerebro": quien, "messages": [
            {"role": "user", "content": txt}]}), headers={"X-Kira-Token": "t" * 32})
        r = c.getresponse(); b = json.loads(r.read()); c.close()
        return b["choices"][0]["message"]["content"]

    try:
        ok("2B" in charla("grande", "programa"), "sin el 4B bajado, el grande contesta con el 2B")
        open(os.path.join(mod, cerebros["grande"]["archivo"]), "w").write("x")
        ok("4B" in charla("grande", "programa"), "con el 4B bajado, programa con el 4B")
        p_r = cer.subs["rapido"].proceso; p_g = cer.subs["grande"].proceso
        ok("2B" in charla("rapido", "hola"), "y charla con el 2B")
        ok(cer.subs["grande"].proceso is p_g and p_g.poll() is None and cer.subs["rapido"].proceso is p_r,
           "sin quitar ni volver a cargar ninguno (los dos siguen cargados)")
        ok(cer.actual == "rapido+grande" and cer.subs["grande"].puerto == base + 1, "cada uno en su puerto")
        # el grande ocupado no hace esperar al pequeño
        cer.subs["grande"].uso.acquire()
        try:
            t0 = time.monotonic(); r = charla("rapido", "hola otra vez")
            ok("2B" in r and time.monotonic() - t0 < 10, "con el grande ocupado, el pequeño contesta igual")
        finally:
            cer.subs["grande"].uso.release()
        # mientras me habla, el grande (trabajando) se PAUSA y luego sigue
        def estado(pid):
            return open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[0]
        cer.subs["grande"].uso.acquire()          # el grande está trabajando
        try:
            with cer.prioridad("rapido"):
                time.sleep(0.3)
                ok(estado(p_g.pid) == "T" and cer.pausado, "mientras me habla, el grande se PAUSA")
                ok("2B" in charla("rapido", "¿sigues?"), "y el pequeño contesta mientras tanto")
            time.sleep(0.3)
            ok(estado(p_g.pid) != "T" and not cer.pausado, "al acabar, el grande sigue donde estaba")
        finally:
            cer.subs["grande"].uso.release()
        with cer.prioridad("rapido"):
            ok(not cer.pausado, "si el grande está libre, no se pausa nada")
        with cer.uso:                                       # el turno de los dos (pintor) no se queda trabado
            pass
        ok(True, "el turno doble se coge y se suelta")
    finally:
        srv.shutdown(); cer.parar()
    ok(not cer.vivo(), "al acabar se paran los dos")

print("TODO BIEN" if not fallos else f"{fallos} FALLOS")
sys.exit(1 if fallos else 0)
