# -*- coding: utf-8 -*-
"""v2.89: arreglos vistos en las CAPTURAS de verdad (Kivy y Tk en GitHub): botones claros con letra oscura, números a
la española, «…» al recortar, la orden a KiraOS guarda su número (cerrar la app no la pierde) y la ventana de la WiFi
con los botones en dos filas."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import casa_kira as ck
import ordenes_kira as okr
import tablero_kira as tbk

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


ok(tbk._num(91.8) == "91,8" and tbk._num("1.35", 2) == "1,35" and tbk._num(8192 / 1024) == "8", "números a la española")
ok(tbk._corta("x" * 300, 50).endswith("…") and len(tbk._corta("x" * 300, 50)) == 50, "al recortar, «…»")
ok(tbk._corta("corto", 50) == "corto", "lo corto no se toca")
tx = tbk.tarjeta_kiraos({"kiraos": {"version": "2.89", "equipo": {"procesador": "Intel Core i5 M430", "ram_mb": 7900,
                                                                   "disco_libre_gb": 181, "carga": "1.35",
                                                                   "encendido_h": 5.2}}})["texto"]
ok("7,7 GB de RAM" in tx and "carga 1,35" in tx and "encendido 5,2 h" in tx, "el portátil, bien escrito: " + tx)
T = tempfile.mkdtemp()
oid = okr.apuntar(T, "o", "kiraos")
okr.actualizar(T, oid, respuesta="r" * 400, estado="hecha")
ok("…" in tbk.tarjeta_ordenes({"ordenes": okr.ultimas(T)})["texto"], "una respuesta larga se corta con «…»")

# la orden a KiraOS apunta su número nada más empezar
c = ck.Casa.__new__(ck.Casa)
llamadas = []


def nucleo(ruta, datos=None, **k):
    llamadas.append(ruta)
    return {"id": "t42"} if ruta == "/orden" else {"estado": "hecho", "respuesta": "listo", "avance": []}


c._nucleo, c._reloj = nucleo, lambda: 0
vistos = []
r = c.orden("hazme un juego", al_id=vistos.append, dormir=lambda s: None)
ok(vistos == ["t42"] and r["estado"] == "hecho", "casa.orden avisa del número de la tarea")
oid2 = okr.apuntar(T, "hazme un juego", "kiraos")
okr.actualizar(T, oid2, tarea="t42")
oid3 = okr.apuntar(T, "hola", "movil")
okr.cerrar_huerfanas(T)
est = {o["id"]: o["estado"] for o in okr.ultimas(T, 50)}
ok(est[oid2] == "en curso" and est[oid3] == "cancelada", "al reabrir, la que tiene número de KiraOS se sigue")
ok([o["id"] for o in okr.en_kiraos(T)] == [oid2], "y se le pregunta a KiraOS cómo acabó")

src = open(os.path.join(RAIZ, "interfaz_kira.py"), encoding="utf-8").read()
ok("al_id=lambda tid: oid and ordk_.actualizar(core.dir, oid, tarea=tid)" in src, "la interfaz apunta el número")
ok('oscuro if _luminosidad(color) > 0.6' in src, "sobre un botón claro, letra oscura")
src_e = open(os.path.join(RAIZ, "kira_portatil", "kira_escritorio.py"), encoding="utf-8").read()
ok("filas_botones" in src_e and '("Cerrar", win.destroy)' in src_e, "la ventana de la WiFi, en dos filas")
print("\nTODO BIEN", n)
