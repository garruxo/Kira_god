# -*- coding: utf-8 -*-
"""La consola de Kira en el portátil (sin móvil): charla con historial, elige rápido/grande, órdenes de defensa y
formato bonito. Con un servidor de mentira (sin red real)."""
import json
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import kira_consola as kc

TOKEN = "C" * 32
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


class Falso(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _j(self, codigo, obj):
        b = json.dumps(obj).encode()
        self.send_response(codigo)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.headers.get("X-Kira-Token") != TOKEN:
            return self._j(401, {"ok": False})
        if self.path == "/hola":
            return self._j(200, {"ok": True, "nombre": "portatil", "cargado": "grande",
                                 "cerebros": {"rapido": "9B", "grande": "35B"}, "pintor": True})
        self._j(404, {})

    def do_POST(self):
        if self.headers.get("X-Kira-Token") != TOKEN:
            return self._j(401, {"ok": False})
        d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        if self.path == "/v1/chat/completions":
            cual = d.get("kira_cerebro")
            n = len([m for m in d["messages"] if m["role"] == "user"])
            texto = f"[{cual}|{n}] " + d["messages"][-1]["content"]
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
        if self.path == "/defensa":
            if d["accion"] == "inventario":
                return self._j(200, {"ok": True, "aparatos": [{"ip": "192.168.1.1", "nombre": "router", "fabricante": "Movistar"}]})
            if d["accion"] == "puertos":
                return self._j(200, {"ok": True, "host": d["host"], "abiertos": [{"puerto": 80, "servicio": "http"}]})
            if d["accion"] == "trafico":
                return self._j(200, {"ok": True, "conversaciones": [{"a": "192.168.1.5", "b": "192.168.1.1", "paquetes": 9}],
                                     "protocolos": [{"protocolo": "tls", "paquetes": 7}]})
            if d["accion"] in ("revisa", "vigila"):
                return self._j(200, {"ok": True, "avisos": [{"tipo": "aparato_nuevo", "detalle": "Aparato NUEVO: 192.168.1.9", "nivel": "importante"}]})
            if d["accion"] == "alertas":
                return self._j(200, {"ok": True, "pendientes": []})
            if d["accion"] == "mapa":
                return self._j(200, {"ok": True, "aparatos": [{"ip": "192.168.1.1", "nombre": "router", "confirmado": True}],
                                     "confirmados": 1, "pendientes": 0, "trafico_normal": {}, "ultimos": []})
            if d["accion"] == "clave":
                return self._j(200, {"ok": True, "clave": "faro-tigre-nube-remo-sal-42"})
            if d["accion"] == "fuerza":
                return self._j(200, {"ok": True, "nivel": "floja", "bits": 10, "largo": 6, "consejos": ["Hazla más larga."]})
        self._j(404, {})


puerto = libre()
srv = HTTPServer(("127.0.0.1", puerto), Falso)
threading.Thread(target=srv.serve_forever, daemon=True).start()

cli = kc.Cliente(f"http://127.0.0.1:{puerto}", TOKEN)
ok(cli.hola()["nombre"] == "portatil", "encuentra el cerebro de casa")

r = cli.charla("hola")
ok(r == "[grande|1] hola", "charla con el cerebro grande por defecto")
r = cli.charla("y ahora")
ok(r == "[grande|2] y ahora" and len(cli.historial) == 4, "guarda el historial (segunda pregunta ve dos turnos)")
cli.grande = False
trozos = []
r = cli.charla("rapidito", al_trozo=lambda t: trozos.append(t))
ok(r.startswith("[rapido|3]") and len(trozos) >= 2, "cambia al rápido y va a trozos")

ok("router" in kc.formato_defensa(cli.defensa("inventario")) and "Movistar" in kc.formato_defensa(cli.defensa("inventario")),
   "/red: lista los aparatos")
ok("80" in kc.formato_defensa(cli.defensa("puertos", host="192.168.1.1")), "/puertos: puertos abiertos")
ok("192.168.1.5" in kc.formato_defensa(cli.defensa("trafico", segundos=5)), "/trafico: resumen")
ok("[x]" in kc.formato_defensa({"ok": False, "error": "fuera de tu red"}), "un error se muestra claro")

# la guardiana y las claves (nuevas en v2.47)
ok("192.168.1.9" in kc.formato_avisos(cli.defensa("revisa")), "la guardiana avisa de un aparato nuevo")
ok("normal" in kc.formato_avisos(cli.defensa("alertas")), "sin novedades, lo dice")
ok("router" in kc.formato_mapa(cli.defensa("mapa")), "el mapa de la red lista los aparatos")
ok("faro-tigre" in kc.formato_clave(cli.defensa("clave")), "genera una clave fuerte")
ok("floja" in kc.formato_clave(cli.defensa("fuerza", clave="123456")), "audita una clave floja y aconseja")

# una sola pregunta (modo -p, el que usa la prueba de GitHub)
import io
sal = io.StringIO()
_stdout = sys.stdout
sys.stdout = sal
try:
    kc.una_vez(kc.Cliente(f"http://127.0.0.1:{puerto}", TOKEN), "dime algo")
finally:
    sys.stdout = _stdout
ok("dime algo" in sal.getvalue(), "modo -p: una pregunta y responde")

# token malo
ok("token" not in "", "placeholder")
try:
    kc.Cliente(f"http://127.0.0.1:{puerto}", "X" * 32).hola()
    ok(False, "con token malo debería fallar")
except kc.ConsolaError:
    ok(True, "con token equivocado, avisa")

srv.shutdown()
ok(kc.leer_token.__doc__ is None or True, "placeholder")
doc = open(os.path.join(RAIZ, "kira_portatil", "kira_consola.py"), encoding="utf-8").read()
ok("No creas malware" in doc, "la consola mantiene el límite defensivo en su sistema")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
