# -*- coding: utf-8 -*-
"""La guardiana de la red (vigilancia_kira): aprende los aparatos y el tráfico normal, avisa de lo NUEVO/anormal una
sola vez, y el umbral de tráfico evoluciona. Con una defensa de mentira (sin red real)."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import vigilancia_kira as vg

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


class DefensaFalsa:
    def __init__(self):
        self.aparatos = [{"ip": "192.168.1.1", "mac": "AA:AA:AA:AA:AA:01", "nombre": "router", "fabricante": "Movistar"}]
        self.paq = 100
    def inventario(self):
        return list(self.aparatos)
    def trafico(self, segundos=20):
        return {"conversaciones": [{"a": "192.168.1.5", "b": "8.8.8.8", "paquetes": self.paq}], "protocolos": []}


d = DefensaFalsa()
est = vg._vacio()

# primera pasada: el router es nuevo -> avisa una vez
avisos = vg.revisar(est, defensa=d, ahora=1000)
ok(any(a["tipo"] == "aparato_nuevo" for a in avisos), "la 1.ª vez avisa del aparato nuevo (el router)")
# segunda pasada: ya lo conoce -> NO vuelve a avisar del mismo
avisos = vg.revisar(est, defensa=d, ahora=1100)
ok(not any(a["tipo"] == "aparato_nuevo" for a in avisos), "no repite el aviso de un aparato que ya conoce")
ok(est["aparatos"]["AA:AA:AA:AA:AA:01"]["veces"] == 2, "cuenta las veces que ve cada aparato")

# aparece un aparato DESCONOCIDO -> avisa
d.aparatos.append({"ip": "192.168.1.77", "mac": "BB:BB:BB:BB:BB:02", "nombre": "", "fabricante": "¿?"})
avisos = vg.revisar(est, defensa=d, ahora=1200)
ok(any(a["tipo"] == "aparato_nuevo" and "192.168.1.77" in a["detalle"] for a in avisos),
   "avisa cuando aparece un aparato desconocido")

# tráfico: durante el aprendizaje no avisa de «mucho»; después, un pico sí
for t in range(vg.APRENDIENDO):
    vg.revisar(est, defensa=d, ahora=1300 + t)         # tráfico normal (100 paq)
d.paq = 50000                                           # pico enorme
avisos = vg.revisar(est, defensa=d, ahora=2000)
ok(any(a["tipo"] == "trafico_alto" for a in avisos), "tras aprender lo normal, un pico de tráfico sí avisa")
ok(est["trafico"]["muestras"] > vg.APRENDIENDO and est["trafico"]["media"] > 0,
   "el tráfico normal se va aprendiendo (media/muestras), umbral adaptativo")

# confirmar un aparato de confianza (tú mandas)
ok(vg.confirmar(est, "192.168.1.77") and est["aparatos"]["BB:BB:BB:BB:BB:02"]["confirmado"] is True,
   "puedo confirmar un aparato como de confianza")
ok(vg.olvidar(est, "192.168.1.77") and "BB:BB:BB:BB:BB:02" not in est["aparatos"], "puedo olvidar un aparato")

# avisos pendientes / vistos
ok(len(vg.pendientes(est)) > 0, "hay avisos pendientes de ver")
vg.marcar_vistos(est)
ok(len(vg.pendientes(est)) == 0, "al marcarlos vistos, ya no quedan pendientes")

# el mapa resume lo que sabe
m = vg.mapa(est)
ok("aparatos" in m and "trafico_normal" in m and "ultimos" in m, "el mapa resume aparatos, tráfico y eventos")

# guardar/cargar (archivo temporal, 0600)
R = os.path.join(tempfile.mkdtemp(), "vig.json")
vg.guardar(est, R)
ok(os.path.isfile(R) and (os.stat(R).st_mode & 0o777) == 0o600, "guarda el estado en un archivo solo del dueño (0600)")
est2 = vg.cargar(R)
ok(est2["aparatos"].get("AA:AA:AA:AA:AA:01") is not None, "lo guardado se vuelve a cargar bien")

# si la red falla, no rompe
class DefensaRota:
    def inventario(self):
        raise RuntimeError("sin WiFi")
    def trafico(self, segundos=20):
        return None
av = vg.revisar(vg._vacio(), defensa=DefensaRota())
ok(av and av[0]["tipo"] == "sin_red", "si no puede mirar la red, lo dice (no rompe)")

# vigilar: da una vuelta y para (no se queda colgado)
chequeos = {"n": 0}
def parar():
    chequeos["n"] += 1
    return chequeos["n"] > 2          # deja pasar una vuelta y para
vg.vigilar(cada_min=1, ruta=R, defensa=DefensaFalsa(), avisar=lambda a: None,
           parar=parar, dormir=lambda s: None)
ok(chequeos["n"] >= 1, "vigilar() da una vuelta, respeta la parada y no se cuelga")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
