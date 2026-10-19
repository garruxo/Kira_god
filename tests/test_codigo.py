# -*- coding: utf-8 -*-
"""Programación avanzada: curso, códigos, ejecutor seguro, programas guardados, motor de juegos y juegos."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import curso_avanzado_kira as ca, ejecutor_kira as ej, juegos_kira as jk, motor_juegos_kira as mj, programacion_kira as pk
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- curso avanzado y códigos: todos se ejecutan bien en modo seguro ----------
ok(len(ca.CURSO_AVANZADO) >= 16 and len(ca.CODIGOS) >= 10, "16 lecciones avanzadas y 10 códigos")
ids = [l["id"] for l in ca.todas()]
ok(len(ids) == len(set(ids)) and not set(ids) & {l["id"] for l in pk.CURSO}, "ids únicos")
for l in ca.todas():
    r = ej.ejecutar(l["codigo"], limite=10)
    ok(r["ok"] and r["salida"].strip(), f"{l['id']} se ejecuta y muestra algo: {r['error']}")
    ok(len(l["texto"]) > 60, f"{l['id']} tiene explicación")
esperado = {"grafos": "['casa', 'tienda', 'cine']", "huffman": "True", "vigenere": "nos vemos en la sala hacker",
            "perceptron": "acierta 200 de 200", "hilos": "suma 5050", "sqlite": "(2, 'compilar kira')", "pruebas": "fallos: 0"}
for k, v in esperado.items():
    ok(v in ej.ejecutar(ca.buscar(k)["codigo"], limite=10)["salida"], f"{k} da el resultado correcto")
for l in pk.CURSO:
    if l["id"] not in ("archivos", "modulos_kira"):
        ok(ej.ejecutar(l["codigo"])["ok"], f"básico {l['id']} en modo seguro")
ok(ca.buscar("nada") is None, "buscar algo que no existe")

# ---------- modo seguro ----------
def err(c, **kw): return ej.ejecutar(c, **kw)["error"]
ok("bucle infinito" in err("while True:\n    pass", limite=0.5), "corta bucles infinitos")
ok("bucle infinito" in err("import threading\ndef g():\n    while True: pass\nt=threading.Thread(target=g); t.start(); t.join()", limite=0.5), "también en hilos")
for malo in ("import os", "import subprocess", "from socket import socket", "import sys", "import shutil",
             "open('x.txt','w')", "eval('1')", "exec('x=1')", "__import__('os')",
             "().__class__.__bases__[0].__subclasses__()", "getattr(print, '__self__')", "from . import x"):
    ok("modo seguro" in err(malo), f"bloquea: {malo}")
ok("ZeroDivisionError" in err("x = 1\ny = x / 0") and "línea 2" in err("x = 1\ny = x / 0"), "error con su línea")
ok("sintaxis" in err("def f(:\n  pass"), "error de sintaxis")
r = ej.ejecutar("a = input('a? ')\nb = input('b? ')\nprint(int(a) + int(b))", entrada="2\n40")
ok(r["ok"] and "42" in r["salida"], "input() lee la caja de entrada")
ok("EOFError" in err("input()"), "input sin entrada: error claro")
r = ej.ejecutar("for i in range(100000): print('linea', i)", limite=10)
ok(len(r["salida"]) < ej.MAX_SALIDA + 100 and "recortada" in r["salida"], "salida enorme recortada")
ok(ej.ejecutar("import math\nprint(math.sqrt(16))")["salida"].strip() == "4.0", "módulos de la lista segura")
ok(ej.ejecutar("raise SystemExit")["ok"], "SystemExit termina sin error")
ok(err("") == "No hay código.", "vacío")
import sys as _s, threading as _t
ok(_s.gettrace() is None, "deja el rastreo como estaba")

# ---------- programas guardados ----------
P = ej.Programas(os.path.join(tempfile.mkdtemp(), "programas"))
ok(P.guardar("Mi Programa!", "print(1)") == "mi_programa", "guarda con nombre limpio")
ok(P.abrir("mi_programa") == "print(1)" and P.listar() == ["mi_programa"], "abre y lista")
ok(P.abrir("../../etc/passwd") is None, "no sale de su carpeta")
try:
    P.guardar("   ", "x"); ok(False, "nombre vacío")
except ValueError:
    ok(True, "nombre vacío")
ok(P.borrar("mi_programa") and P.listar() == [] and not P.borrar("mi_programa"), "borra")

# ---------- motor de juegos ----------
class Prueba(mj.Juego):
    def preparar(self):
        self.a = self.rect(0, 0, 10, 10, "rojo")
        self.b = self.circulo(30, 5, 5, (0, 1, 0))
        self.a.vx = 100
g = Prueba(semilla=1)
ok(not mj.chocan(g.a, g.b), "separados no chocan")
for _ in range(10): g.paso(0.02)
ok(abs(g.a.x - 20) < 0.01 and mj.chocan(g.a, g.b), "se mueve con su velocidad y choca")
ok(mj.color("rojo")[3] == 1 and mj.color((0.5, 0.5, 0.5)) == (0.5, 0.5, 0.5, 1.0), "colores")
g.fin("x"); g.paso(1); ok(abs(g.a.x - 20) < 0.01, "en 'fin' no se mueve")
g.tocar(1, 1); ok(g.estado == "jugando" and g.a.x == 0, "tocar tras el fin reinicia")
g.pausar(); g.paso(0.5); ok(g.estado == "pausa" and g.a.x == 0, "pausa")
ok(mj.buscar_juego({"Prueba": Prueba, "x": 1}) is Prueba and mj.buscar_juego({}) is None, "encuentra la clase del juego")
ok(len(g.dibujo()) == 2 and g.dibujo()[0][0] == "rect", "lista de dibujo")
try:
    for _ in range(mj.MAX_PIEZAS + 1): g.rect(0, 0, 1, 1)
    ok(False, "límite de piezas")
except RuntimeError:
    ok(True, "límite de piezas")

# ---------- los juegos: se cargan desde su código y se pueden ganar puntos ----------
def jugar(id_, bot, segundos=60):
    j, e = jk.cargar(jk.buscar(id_)["codigo"], semilla=3)
    ok(e is None, f"{id_} carga: {e}")
    for i in range(int(segundos * 60)):
        bot(j, i)
        ej.con_limite(j.paso, 0.2, 1 / 60)
        if j.estado != "jugando":
            break
    return j
def sigue_bola(j, i):
    j.dedo = (j.bola.x, 40)
r = jugar("rompeladrillos", sigue_bola)
ok(r.puntos >= 150, f"rompeladrillos: un buen jugador rompe ladrillos ({r.puntos})")
def esquiva(j, i):
    peligro = [m for m in j.con_etiqueta("meteorito") if m.y < 300 and abs(m.x - (j.nave.x + 15)) < 60]
    if peligro:
        j.dedo = ((j.nave.x + 15 + (90 if peligro[0].x < j.nave.x + 15 else -90)) % 330, 60)
r = jugar("esquiva", esquiva, 30)
ok(r.puntos >= 20, f"esquiva: esquivando se suman puntos ({r.puntos})")
def salta(j, i):
    cols = [c for c in j.con_etiqueta("columna") if c.x + c.w > 70 and c.y > 0]
    objetivo = (cols[0].y - 75) if cols else 320
    if j.pajaro.y < objetivo - 20 and j.pajaro.vy < 0:
        j.tocar(0, 0)
r = jugar("saltarin", salta, 40)
ok(r.puntos >= 3, f"saltarín: pasando huecos se suman puntos ({r.puntos})")
def pong(j, i):
    j.dedo = (j.bola.x, 30)
r = jugar("pong", pong, 120)
ok(r.puntos >= 1, f"pong: se le puede marcar a Kira ({r.puntos})")
def serpiente(j, i):
    if i % 5: return
    (cx, cy), (mx, my) = j.cuerpo[0], j.manzana
    opciones = [d for d, si in (((1, 0), mx > cx), ((-1, 0), mx < cx), ((0, 1), my > cy), ((0, -1), my < cy)) if si]
    for d in opciones + [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        nx, ny = cx + d[0], cy + d[1]
        if (d[0] + j.direccion[0], d[1] + j.direccion[1]) != (0, 0) and 0 <= nx < j.columnas and 0 <= ny < j.filas \
                and (nx, ny) not in j.cuerpo:
            j.al_deslizar(d[0] * 40, d[1] * 40)
            break
r = jugar("serpiente", serpiente, 40)
ok(r.puntos >= 3, f"serpiente: yendo a por las manzanas crece ({r.puntos})")
j, e = jk.cargar(jk.PLANTILLA); ok(e is None and j.titulo == "Mi juego", "la plantilla funciona")
ok(jk.cargar("print('hola')")[1].startswith("El programa no define"), "un programa sin juego")
ok("modo seguro" in jk.cargar("import os")[1], "un juego también pasa el modo seguro")
mal, e = jk.cargar("from motor_juegos_kira import Juego\nclass J(Juego):\n    def actualizar(self, dt):\n        while True: pass")
try:
    ej.con_limite(mal.paso, 0.2, 0.016); ok(False, "fotograma colgado")
except ej.TiempoAgotado:
    ok(True, "un fotograma colgado se corta")
print("CODIGO OK", n)
