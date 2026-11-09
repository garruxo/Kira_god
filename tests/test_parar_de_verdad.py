# -*- coding: utf-8 -*-
"""v3.18: «Parar» y «Borrar» en KiraOS paran DE VERDAD, aunque el cerebro del Packard Bell esté varios minutos
leyendo el pedido sin decir nada. Antes: el «cancela» caducaba a los 25 s, la espera del cerebro no miraba el
«parar» hasta que llegaba la primera palabra, «Borrar» no paraba la que se hacía, y el servidor del cerebro seguía
trabajando aunque nadie esperara la respuesta (y no dejaba pasar la siguiente)."""
import http.client
import os
import socket
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["KIRA_DATOS_NUCLEO"] = T
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import casa_kira
import kira_god
import nucleo_portatil as npk
import servidor_portatil as sp

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


def espera(cond, s=6):
    lim = time.time() + s
    while time.time() < lim:
        if cond():
            return True
        time.sleep(0.05)
    return False


# ---------- 1) el «Parar» de la tarea no caduca ----------
core = kira_god.KiraGodCore.__new__(kira_god.KiraGodCore)
core.CANCELAR_DURA = 0.2
core.cancelar = lambda: (core.__dict__.__setitem__("_cancelar_t", time.monotonic()), core._evento_cancelar().set())
core.cancelar()
time.sleep(0.4)
ok(not core.cancelado(), "(antes) el «cancela» solo caducaba enseguida…")
core.parar_extra = lambda: True
ok(core.cancelado(), "…ahora el «Parar» de la tarea sigue valiendo hasta que acabe")
core.parar_extra = lambda: False
ok(not core.cancelado(), "sin «Parar», sigue trabajando")

# una tarea «larga» que, como el núcleo de verdad, solo mira cancelado() de vez en cuando
nucleo = npk.Nucleo.__new__(npk.Nucleo)
nucleo.core = kira_god.KiraGodCore.__new__(kira_god.KiraGodCore)
nucleo.core.CANCELAR_DURA = 0.2
nucleo.con_maquina = False
vio = {}


def hacer(orden, paso):
    c = nucleo.core
    t0 = time.time()
    while time.time() - t0 < 20:
        time.sleep(0.5)                           # el cerebro «leyendo»: mucho rato sin poder mirar
        if c.cancelado():
            vio[orden] = time.time() - t0
            raise kira_god.__dict__.get("Cancelada", RuntimeError)("Cancelado.")
    return {"texto": "acabé sin que me pararan"}


nucleo._hacer = hacer
nucleo._enganchar()
nucleo.trabajos = npk.Trabajos(nucleo._hacer)
a = nucleo.trabajos.empezar("larga uno")
ok(espera(nucleo.trabajos.ocupado), "empieza la tarea larga")
time.sleep(0.6)                                   # ya pasado el rato en que caducaba el «cancela»
r = nucleo.tarea_accion(a, "parar")
ok(r["ok"], "pulsar «Parar»")
ok(espera(lambda: nucleo.trabajos.tareas[a]["estado"] == "cancelado", 4), "la tarea se PARA de verdad")
ok(nucleo.trabajos.tareas[a]["resultado"] == "Parada", "y sale en Terminadas como «Parada»")
b = nucleo.trabajos.empezar("larga dos")
ok(espera(lambda: nucleo.trabajos.tareas[b]["estado"] == "en curso"), "la siguiente empieza (el «Parar» de antes no la corta)")
time.sleep(1.2)
ok(nucleo.trabajos.tareas[b]["estado"] == "en curso", "…y sigue mientras no la pares")
r = nucleo.tarea_accion(b, "borrar")
ok(r["ok"] and "paro" in r["texto"], "«Borrar» la que se está haciendo: la para")
ok(espera(lambda: b not in nucleo.trabajos.tareas, 4), "…y la quita de la lista")
c_ = nucleo.trabajos.empezar("larga tres")
ok(espera(lambda: nucleo.trabajos.tareas[c_]["estado"] == "en curso"), "otra más")
nucleo.trabajos.parar_actual()                    # lo que hace el «Parar» de la barra (/cancelar)
ok(espera(lambda: nucleo.trabajos.tareas[c_]["estado"] == "cancelado", 4), "el «Parar» de la barra también la para")

# ---------- 2) el cliente corta aunque el cerebro aún no haya dicho nada ----------
estado = {"cerrado": None, "llegaron": 0}


class Lento(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        estado["llegaron"] += 1
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        t0 = time.time()
        while time.time() - t0 < 15:              # «leyendo el pedido»: no manda NADA
            if sp.cliente_se_fue(self.connection):
                estado["cerrado"] = time.time() - t0
                return
            time.sleep(0.1)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'data: {"choices":[{"delta":{"content":"tarde"}}]}\n\ndata: [DONE]\n\n')


srv = ThreadingHTTPServer(("127.0.0.1", 0), Lento)
threading.Thread(target=srv.serve_forever, daemon=True).start()


class CasaPrueba(casa_kira.Casa):
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    token = "tok"


casa = CasaPrueba()
pulsado = {"t": None}


def parar():
    return pulsado["t"] is not None and time.time() >= pulsado["t"]


pulsado["t"] = time.time() + 1.0
t0 = time.time()
try:
    casa.chat("sys", [{"role": "user", "content": "hola"}], al_trozo=lambda t: None, parar=parar, timeout=60)
    ok(False, "debería cortarse")
except casa_kira.Cancelada:
    ok(time.time() - t0 < 3, f"«Parar» corta en {time.time() - t0:.1f} s aunque el cerebro aún no haya escrito nada")
except Exception as e:                            # noqa: BLE001
    ok(False, f"se cortó con otro error: {e!r}")
ok(espera(lambda: estado["cerrado"] is not None, 3), "y el cerebro se entera de que nadie espera (deja de trabajar)")


class Rapido(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'data: {"choices":[{"delta":{"content":"hola "}}]}\n\n'
                         b'data: {"choices":[{"delta":{"content":"jefe"}}]}\n\ndata: [DONE]\n\n')


srv2 = ThreadingHTTPServer(("127.0.0.1", 0), Rapido)
threading.Thread(target=srv2.serve_forever, daemon=True).start()
CasaPrueba.url = f"http://127.0.0.1:{srv2.server_address[1]}"
trozos = []
r = casa.chat("sys", [{"role": "user", "content": "hola"}], al_trozo=trozos.append, parar=lambda: False)
ok(r == "hola jefe" and trozos, "sin «Parar», la respuesta llega igual que siempre (a trozos)")

# ---------- 3) el servidor del cerebro suelta a llama-server si quien preguntó se fue ----------
x, y = socket.socketpair()
ok(not sp.cliente_se_fue(x), "con el cliente ahí: sigue")
y.close()
ok(sp.cliente_se_fue(x), "el cliente colgó: se nota")
x.close()


class ConFalsa:
    def __init__(self):
        self.a, self.b = socket.socketpair()
        self.sock = self.a


cli_a, cli_b = socket.socketpair()
cf = ConFalsa()
fin = threading.Event()
h = threading.Thread(target=sp.vigilar_cliente, args=(cli_a, cf, fin, 0.05), daemon=True)
h.start()
time.sleep(0.2)
ok(h.is_alive(), "mientras el cliente espera, no toca nada")
cli_b.close()
h.join(2)
cf.b.settimeout(1)
ok(not h.is_alive() and cf.b.recv(1) == b"", "cuando el cliente se va, corta la conexión con llama-server")
fin.set()

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
