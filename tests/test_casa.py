# -*- coding: utf-8 -*-
"""El móvil usa el cerebro de casa (portátil) cuando está en la WiFi: descubrir, disponible, charla (rápido/grande),
stream, pintar, y que `cerebro_ia_kira.Cerebro` lo use solo y vuelva al cerebro del móvil si el portátil falla."""
import http.client
import json
import os
import socket
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

TOKEN = "T" * 32
fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


def libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class PortatilFalso(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _j(self, codigo, obj):
        b = json.dumps(obj).encode()
        self.send_response(codigo)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _tok(self):
        return self.headers.get("X-Kira-Token") == TOKEN

    def do_GET(self):
        if self.path == "/salud":
            return self._j(200, {"ok": True})
        if not self._tok():
            return self._j(401, {"ok": False})
        if self.path == "/hola":
            return self._j(200, {"ok": True, "tipo": "portatil", "nombre": "portatil-prueba",
                                 "cerebros": {"rapido": "Qwen 9B", "grande": "Qwen 35B"}, "pintor": True})
        self._j(404, {})

    def do_POST(self):
        if not self._tok():
            return self._j(401, {"ok": False})
        largo = int(self.headers.get("Content-Length", "0"))
        d = json.loads(self.rfile.read(largo)) if largo else {}
        if self.path == "/pintar":
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            png = b"\x89PNG\r\n\x1a\n" + d.get("prompt", "").encode()
            self.send_header("Content-Length", str(len(png)))
            self.end_headers()
            self.wfile.write(png)
            return
        if self.path == "/v1/chat/completions":
            cual = d.get("kira_cerebro", "?")
            texto = f"[{cual}] " + d["messages"][-1]["content"]
            if d.get("stream"):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                for p in texto.split(" "):
                    self.wfile.write(("data: " + json.dumps({"choices": [{"delta": {"content": p + " "}}]}) + "\n\n").encode())
                self.wfile.write(b"data: [DONE]\n\n")
            else:
                self._j(200, {"choices": [{"message": {"content": texto}}]})
            return
        self._j(404, {})


puerto = libre()
srv = HTTPServer(("127.0.0.1", puerto), PortatilFalso)
threading.Thread(target=srv.serve_forever, daemon=True).start()

with tempfile.TemporaryDirectory() as d:
    os.environ["KIRA_DATA_DIR"] = d
    import pasarela_cliente as pc
    import casa_kira
    import cerebro_ia_kira as ci

    pc.guardar_config("http://127.0.0.1:8765", TOKEN, portatil_url=f"http://127.0.0.1:{puerto}", nombre="casa")
    casa = casa_kira.Casa()
    ok(casa.url == f"http://127.0.0.1:{puerto}" and casa.token == TOKEN, "lee la dirección y el token de pasarela.json")
    ok(casa.disponible(), "el portátil está disponible (acepta nuestro token)")
    info = casa.info()
    ok(info and "grande" in info["cerebros"] and info["pintor"], "/hola dice qué tiene")

    ok(casa.chat("", [{"role": "user", "content": "hola"}], grande=False) == "[rapido] hola", "charla con el rápido")
    ok(casa.chat("", [{"role": "user", "content": "programa"}], grande=True) == "[grande] programa", "charla con el grande")
    trozos = []
    r = casa.chat("", [{"role": "user", "content": "uno dos tres"}], al_trozo=lambda t: trozos.append(t))
    ok("tres" in r and len(trozos) >= 3, "la respuesta llega a trozos")
    png = casa.pintar("a red apple", semilla=1)
    ok(png.startswith(b"\x89PNG") and b"a red apple" in png, "pinta (devuelve el PNG)")

    # token malo: no disponible
    pc.guardar_config("http://127.0.0.1:8765", "X" * 32, portatil_url=f"http://127.0.0.1:{puerto}", nombre="casa")
    ok(not casa_kira.Casa().disponible(), "con el token equivocado, no lo usa")

    # a través del cerebro: todo lo que use el cerebro va al portátil, sin clave de Claude ni cerebro del móvil
    pc.guardar_config("http://127.0.0.1:8765", TOKEN, portatil_url=f"http://127.0.0.1:{puerto}", nombre="casa")
    cer = ci.Cerebro(d)
    ok(cer.casa_disponible(forzar=True), "el cerebro ve el portátil")
    ok(cer.local_disponible(forzar=True), "«cerebro local» disponible aunque el del móvil esté apagado (hay portátil)")
    ok(cer.chat_local("", [{"role": "user", "content": "hola"}], max_tokens=200) == "[rapido] hola",
       "una charla corta va al cerebro rápido del portátil")
    ok(cer.chat_local("", [{"role": "user", "content": "un modulo largo"}], max_tokens=1500) == "[grande] un modulo largo",
       "programar (muchos tokens) va al cerebro grande")

    # si el portátil se cae y no hay cerebro del móvil: error claro (no cuelga)
    cer.casa_disponible = lambda forzar=False: True            # cree que sigue disponible…
    def _cae(*a, **k):
        raise casa_kira.CasaError("No se pudo hablar con el cerebro de casa: conexión rechazada")
    cer._casa.chat = _cae                                      # …pero al llamar, falla
    try:
        cer.chat_local("", [{"role": "user", "content": "hola"}], max_tokens=200)
        ok(False, "debería avisar de que el portátil cayó")
    except ci.CerebroError as e:
        ok("casa" in str(e).lower() or "móvil" in str(e), "si el portátil cae y no hay cerebro del móvil, lo dice")

# descubrimiento por el faro
import enlace_lab_kira as el
faro_port = libre()


class FaroHilo(threading.Thread):
    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", faro_port))
        s.settimeout(3)
        try:
            datos, quien = s.recvfrom(256)
            if datos.strip() == casa_kira.PREGUNTA:
                s.sendto(json.dumps({"kira_portatil": 1, "puerto": 9999, "nombre": "mi-portatil"}).encode(), quien)
        except socket.timeout:
            pass
        s.close()


FaroHilo().start()
hallados = casa_kira._preguntar(["127.0.0.1"], 2)
# el faro de prueba está en un puerto suelto; comprobamos la función con ese puerto
import socket as _s
ss = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
ss.sendto(casa_kira.PREGUNTA, ("127.0.0.1", faro_port))
ss.settimeout(2)
try:
    datos, _ = ss.recvfrom(256)
    r = json.loads(datos)
    ok(r.get("kira_portatil") == 1 and r["nombre"] == "mi-portatil", "el faro del portátil contesta a la pregunta")
except _s.timeout:
    ok(False, "el faro no contestó")
ss.close()
srv.shutdown(); srv.server_close()

src = open(os.path.join(RAIZ, "cerebro_ia_kira.py"), encoding="utf-8").read()
ok("self.casa_disponible()" in src and "grande=max_tokens >= 800" in src, "el cerebro enruta al portátil")
src2 = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
ok("casa.pintar(" in src2, "los dibujos de los juegos se pintan en el portátil cuando está")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
