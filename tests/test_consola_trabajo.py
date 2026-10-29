# -*- coding: utf-8 -*-
"""La consola de trabajo en vivo (consola_kira): líneas, código letra a letra, intentos con su resultado, detener,
y que `version()` suba cuando hay algo nuevo. Lógica pura, sin Kivy."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import consola_kira as ck

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


c = ck.Consola()
v0 = c.version()
c.empezar("escribir un programa que ordene una lista", pedido="ordena una lista")
ok(c.activa and c.version() > v0, "empezar activa la consola y sube la versión")
ok(c.titulo.startswith("escribir") and c.pedido == "ordena una lista", "guarda título y pedido")

c.linea("Pensando el programa…")
c.linea("Pensando el programa…")            # repetida seguida: no se duplica
ok(sum(1 for _, t in c.lineas if t == "Pensando el programa…") == 1, "no repite la misma línea seguida")

# código letra a letra
c.codigo_vivo("def ordena(x):\n    retu")
ok(c.ultimo_codigo().endswith("retu"), "el código en vivo es lo último que se está escribiendo")
t = c.texto()
ok("escribiendo" in t and "▌" in t, "mientras escribe, lo marca como «escribiendo…»")

# un intento probado (pasa)
c.intento("def ordena(x):\n    return sorted(x)", ok=True)
ok(c.intentos[-1]["ok"] and c.intentos[-1]["n"] == 1, "registra el intento 1 como pasado")
ok(c.codigo_vivo_txt == "", "al cerrar el intento, deja de estar «escribiendo»")
ok(any("Intento 1: ✓" in t for _, t in c.lineas), "escribe en el registro que el intento 1 pasó")

# explicación bajo el código terminado
t2 = c.texto(explicacion="La función devuelve la lista ordenada.")
ok("CÓMO FUNCIONA" in t2 and "devuelve la lista ordenada" in t2, "muestra la explicación técnica bajo el código")

# un segundo intento que falla con motivo
c.intento("def ordena(x): return x", ok=False, motivo="no ordena")
ok(c.intentos[-1]["n"] == 2 and not c.intentos[-1]["ok"], "registra el intento 2 como fallado")
ok(any("Intento 2: ✗" in t and "no ordena" in t for _, t in c.lineas), "escribe el motivo del fallo")

# detener
va = c.version()
c.pedir_detener()
ok(c.detener_pedido and c.version() > va, "pedir detener marca la señal y sube la versión")

# terminar
c.terminar("Programa listo y probado.")
ok(not c.activa and "listo" in c.fin.lower(), "terminar apaga la consola y guarda el final")
ok(any("■" in t for _, t in c.lineas), "el final queda en el registro")

# tope de líneas
c2 = ck.Consola()
c2.empezar("muchas", pedido="x")
for i in range(ck.MAX_LINEAS + 50):
    c2.linea(f"linea {i}")
ok(len(c2.lineas) <= ck.MAX_LINEAS, "no crece sin fin: respeta el tope de líneas")

# empezar de nuevo limpia lo anterior
c.empezar("otra cosa", pedido="otra")
ok(c.intentos == [] and c.fin == "" and not c.detener_pedido, "empezar de nuevo limpia intentos/fin/detener")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
