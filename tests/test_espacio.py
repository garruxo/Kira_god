# -*- coding: utf-8 -*-
"""El espacio aislado de Kira (espacio_kira): ejecutar código con límites dentro de su carpeta, el candado de que no
salga de ahí, el nivel de aislamiento según las herramientas, el tope de tamaño y limpiar. Ejecuta Python de verdad
(sencillo) y usa herramientas de mentira para el resto."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import espacio_kira as es

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


B = tempfile.mkdtemp()

# ejecuta código de verdad y recoge la salida
r = es.ejecutar(codigo="print('hola desde el espacio'); print(2+2)", base=B)
ok(r["ok"] and "hola desde el espacio" in r["salida"] and "4" in r["salida"], "ejecuta un programa y devuelve su salida")

# lo que escribe, lo escribe DENTRO del espacio (no fuera)
r = es.ejecutar(codigo="open('prueba.txt','w').write('x'*10)", base=B)
ok(r["ok"] and os.path.isfile(os.path.join(B, "prueba.txt")), "lo que crea el programa queda dentro del espacio")

# un error del programa se recoge, no rompe
r = es.ejecutar(codigo="raise ValueError('ups')", base=B)
ok(not r["ok"] and "ValueError" in r["error"], "un error del programa se recoge (no rompe Kira)")

# candado: no se puede ejecutar un archivo de FUERA del espacio
fuera = os.path.join(tempfile.mkdtemp(), "malo.py")
open(fuera, "w").write("print('no deberia')")
r = es.ejecutar(archivo=fuera, base=B)
ok(not r["ok"] and "dentro del espacio" in r["error"], "no deja ejecutar archivos de fuera del espacio (candado)")

# nivel de aislamiento según las herramientas
o, niv = es.orden_aislada(B, os.path.join(B, "x.py"), which=lambda p: "/usr/bin/firejail" if p == "firejail" else None)
ok(o[0] == "firejail" and "--net=none" in o and "caja fuerte" in niv, "con firejail: caja fuerte sin red")
o, niv = es.orden_aislada(B, os.path.join(B, "x.py"), red=True, which=lambda p: "/usr/bin/firejail" if p == "firejail" else None)
ok("--net=none" not in o, "con --con-red, firejail deja la red")
o, niv = es.orden_aislada(B, os.path.join(B, "x.py"), which=lambda p: "/usr/bin/bwrap" if p == "bwrap" else None)
ok(o[0] == "bwrap" and "--unshare-net" in o, "con bubblewrap: también sin red")
o, niv = es.orden_aislada(B, os.path.join(B, "x.py"), which=lambda p: None)
ok(o[0] == "python3" and "NO" in niv, "sin herramientas: básico y lo dice claro (la red no se bloquea)")

# tope de tamaño: si el espacio está lleno, no ejecuta
import espacio_kira
_tope = espacio_kira.MAX_MB
try:
    espacio_kira.MAX_MB = 0
    r = es.ejecutar(codigo="print('x')", base=B)
    ok(not r["ok"] and "MB" in r["error"], "si el espacio está lleno, avisa y no ejecuta")
finally:
    espacio_kira.MAX_MB = _tope

# estado y limpiar
st = es.estado(B)
ok("carpeta" in st and "aislamiento" in st and st["tope_mb"] == _tope, "el estado dice carpeta, ocupación y aislamiento")
es.limpiar(B)
ok(es.listar(B) == [], "limpiar deja el espacio vacío")

# timeout (programa que no acaba) — con un correr de mentira que simula que se pasa de tiempo
import subprocess
def correr_lento(*a, **k):
    raise subprocess.TimeoutExpired(cmd="x", timeout=es.TOPE_SEG)
r = es.ejecutar(codigo="while True: pass", base=B, correr=correr_lento)
ok(not r["ok"] and r["cortado"] and "tiempo" in r["error"], "si un programa no acaba, lo corta por tiempo")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
