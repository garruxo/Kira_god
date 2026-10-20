# -*- coding: utf-8 -*-
"""
Test FIJO del laboratorio: si una mejora añade JUEGOS ({"juego <nombre>": crear(motor)}), se JUEGAN aquí unos
segundos simulados (con toques y deslizamientos) para comprobar que no fallan ni se cuelgan.
Recibe la ruta del módulo en sys.argv[1]. Salida 0 = pasa.
"""
import importlib.util
import inspect
import os
import sys
import time

s = importlib.util.spec_from_file_location("mejora", sys.argv[1])
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
tabla = m.registrar() if callable(getattr(m, "registrar", None)) else {}
juegos = {k: v for k, v in (tabla or {}).items() if isinstance(k, str) and k.startswith("juego ")}
if not juegos:
    print("JUEGOS_OK (sin juegos)")
    sys.exit(0)

# el motor de juegos de Kira (Kira_god al lado del laboratorio, o el laboratorio dentro de Kira_god)
lab = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
motor = None
for carpeta in (os.path.join(os.path.dirname(lab), "Kira_god"), os.path.dirname(lab)):
    ruta = os.path.join(carpeta, "motor_juegos_kira.py")
    if os.path.isfile(ruta):
        sm = importlib.util.spec_from_file_location("motor_juegos_kira", ruta)
        motor = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(motor)
        break
assert motor is not None, "no encuentro motor_juegos_kira.py (deja Kira_god junto al laboratorio)"

for nombre, crear in juegos.items():
    assert callable(crear) and len(inspect.signature(crear).parameters) == 1, \
        f"'{nombre}' debe ser una función crear(motor) que devuelve la clase del juego"
    clase = crear(motor)
    assert isinstance(clase, type) and issubclass(clase, motor.Juego), f"'{nombre}' no devuelve una clase de Juego"
    j = clase(semilla=1)
    inicio = time.time()
    for i in range(60 * 20):                       # 20 segundos de juego simulado
        if i % 25 == 0:
            j.tocar(40 + (i * 7) % 280, 60 + (i * 11) % 500)
        if i % 40 == 0:
            j.mover_dedo(180, 300, 30 if i % 80 else 0, 0 if i % 80 else 30)
        t0 = time.time()
        j.paso(1 / 60)
        assert time.time() - t0 < 0.25, f"'{nombre}': un fotograma tardó demasiado"
        if j.estado in ("fin", "ganado"):
            j.tocar(10, 10)                         # reinicia y sigue probando
        assert len(j.piezas) <= motor.MAX_PIEZAS
    assert time.time() - inicio < 10, f"'{nombre}' va demasiado lento"
    for d in j.dibujo():
        forma, col = d[0], d[5]
        assert forma in ("rect", "circulo", "texto", "linea", "poligono") and len(col) == 4
print("JUEGOS_OK", ", ".join(juegos))
