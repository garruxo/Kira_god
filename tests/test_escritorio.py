# -*- coding: utf-8 -*-
"""La lógica de la ventana de Kira del portátil (`manejar`): charla, cambiar de cerebro y órdenes de red, sin abrir
ninguna ventana. Con un cliente de mentira."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import kira_escritorio as ke
import kira_consola as kc

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


class CliFalso:
    def __init__(self):
        self.grande = True
        self.dicho = []
        self.falla = False

    def charla(self, texto, al_trozo=None):
        if self.falla:
            raise kc.ConsolaError("no hay cerebro")
        r = f"[{'grande' if self.grande else 'rapido'}] {texto}"
        if al_trozo:
            for p in r.split(" "):
                al_trozo(p + " ")
        self.dicho.append(("charla", texto))
        return r

    def defensa(self, accion, **extra):
        self.dicho.append(("defensa", accion, extra))
        if accion == "inventario":
            return {"ok": True, "aparatos": [{"ip": "192.168.1.1", "nombre": "router", "fabricante": "Movistar"}]}
        if accion == "puertos":
            return {"ok": True, "host": extra["host"], "abiertos": [{"puerto": 22, "servicio": "ssh"}]}
        if accion == "trafico":
            return {"ok": True, "conversaciones": [{"a": "192.168.1.5", "b": "8.8.8.8", "paquetes": 3}], "protocolos": []}
        return {"ok": False, "error": "?"}


def corre(cli, texto):
    lineas, trozos = [], []
    etiqueta = ke.manejar(cli, texto, lambda x: lineas.append(x), lambda t: trozos.append(t))
    return etiqueta, lineas, "".join(trozos)


cli = CliFalso()
et, li, tr = corre(cli, "hola qué tal")
ok(et == "charla" and tr.strip() == "[grande] hola qué tal", "una frase normal va a la charla (cerebro grande), a trozos")

et, li, tr = corre(cli, "/rapido")
ok(et == "cerebro" and cli.grande is False and "rápido" in li[0], "«/rapido» cambia de cerebro")
et, li, tr = corre(cli, "/grande")
ok(et == "cerebro" and cli.grande is True, "«/grande» vuelve al grande")

et, li, tr = corre(cli, "/red")
ok(et == "defensa" and cli.dicho[-1][1] == "inventario" and "router" in li[0] and "Movistar" in li[0],
   "«/red» pide el inventario y lo muestra")
et, li, tr = corre(cli, "/puertos 192.168.1.1")
ok(et == "defensa" and cli.dicho[-1][1] == "puertos" and cli.dicho[-1][2]["host"] == "192.168.1.1" and "22" in li[0],
   "«/puertos IP» mira ese aparato")
et, li, tr = corre(cli, "/puertos")
ok(et == "defensa" and "qué aparato" in li[0], "«/puertos» sin IP: pide la IP")
et, li, tr = corre(cli, "/trafico 10")
ok(et == "defensa" and cli.dicho[-1][2]["segundos"] == 10, "«/trafico 10» mira el tráfico 10 s")

et, li, tr = corre(cli, "   ")
ok(et == "vacio", "una línea vacía no hace nada")

cli.falla = True
et, li, tr = corre(cli, "hola")
ok(et == "error" and "[x]" in li[0], "si el cerebro no está, lo dice (no rompe la ventana)")

# la bienvenida usa hola()
class CliHola:
    def hola(self):
        return {"nombre": "mi-portatil", "cargado": "grande", "cerebros": {"grande": "Qwen 35B"}}
ok("mi-portatil" in ke.bienvenida(CliHola()) and "Qwen 35B" in ke.bienvenida(CliHola()), "la bienvenida dice el portátil y el cerebro")

class CliSin:
    def hola(self):
        raise kc.ConsolaError("conexión rechazada")
ok("No encuentro" in ke.bienvenida(CliSin()), "sin cerebro, la bienvenida avisa en vez de romper")

ok("import tkinter" in open(os.path.join(RAIZ, "kira_portatil", "kira_escritorio.py")).read(),
   "la ventana usa Tkinter (viene con Python, no hay que instalar nada)")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
