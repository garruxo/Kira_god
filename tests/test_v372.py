# -*- coding: utf-8 -*-
"""v3.72: la máquina virtual de KiraOS se enciende SOLO cuando hace falta, se apaga sola si lleva 10 min sin usarse
(si la encendí yo) y se PAUSA mientras Kira te contesta."""
import os
import signal
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import maquina_kira as mq
import nucleo_portatil as npo

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class MaquinaFalsa:
    def __init__(self, proc=None):
        self.on, self.apagadas, self.proc = False, 0, proc

    def preparada(self):
        return True

    def kvm(self):
        return True

    def encendida(self):
        return self.on

    def encender(self, red=True):
        self.on = True

    def apagar(self, espera=60):
        self.on, self.apagadas = False, self.apagadas + 1

    def modo_red(self):
        return "puerta"

    def pid(self):
        return self.proc.pid if (self.on and self.proc) else None

    def pedir_web(self, url, **k):
        return {"status": 200, "cuerpo": b"hola", "cabeceras": []}

    def experimentar(self, codigo):
        return 0, "ok"


reloj = Reloj()
m = MaquinaFalsa()
red = mq.RedMaquina(m, reloj=reloj)
ok(not m.on, "al empezar la máquina está apagada (ya no se enciende al arrancar)")
red.abrir("https://example.org/")
ok(m.on and red.encendida_por_mi, "se enciende sola cuando hace falta (una visita)")
reloj.t += 5 * 60
ok(not red.apagar_si_inactiva(10) and m.on, "a los 5 min sin usarse sigue encendida")
reloj.t += 6 * 60
ok(red.apagar_si_inactiva(10) and not m.on and m.apagadas == 1, "a los 11 min sin usarse se apaga sola")

# trabajando no se apaga
red.abrir("https://example.org/")
with red.usando():
    reloj.t += 60 * 60
    ok(not red.apagar_si_inactiva(10) and m.on, "mientras trabaja no se apaga aunque pase el tiempo")

# si la encendió el dueño, no se toca
m2 = MaquinaFalsa()
m2.on = True
red2 = mq.RedMaquina(m2, reloj=reloj)
red2.abrir("https://example.org/")
reloj.t += 60 * 60
ok(not red2.apagar_si_inactiva(10) and m2.on, "si ya estaba encendida (la encendiste tú), no la apago")

# pausa mientras te contesto: con un proceso de verdad
proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
try:
    m3 = MaquinaFalsa(proc)
    m3.on = True
    red3 = mq.RedMaquina(m3, reloj=reloj)

    def estado(pid):
        return open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[0]

    with red3.pausa_charla() as cong:
        time.sleep(0.3)
        ok(cong and estado(proc.pid) == "T", "mientras te contesta, la máquina se CONGELA")
        ok(not red3.lista()[0], "congelada no se usa para visitas (lo hace el portátil)")
    time.sleep(0.3)
    ok(estado(proc.pid) != "T" and not red3.pausada, "al acabar de contestar, la máquina sigue donde estaba")
    with red3.usando():
        with red3.pausa_charla() as cong:
            ok(not cong and estado(proc.pid) != "T", "si está trabajando (visita/experimento) no se congela")
    m3.on = False
    with red3.pausa_charla() as cong:
        ok(not cong, "apagada no hay nada que congelar")
finally:
    proc.kill()

# el núcleo la usa en la charla
import inspect
src = inspect.getsource(npo.charla_si_no_es_orden)
ok("pausa_maquina()" in src, "la charla de KiraOS congela la máquina mientras contesta")
main_src = inspect.getsource(npo.main)
ok("maquina_al_arrancar" in main_src and "vigilar_maquina" in main_src,
   "ya no se enciende al arrancar (salvo --maquina-al-arrancar) y se vigila para apagarla")
with npo.pausa_maquina() as x:
    ok(True, "sin máquina enganchada, la pausa no hace nada")

print("TODO BIEN" if not fallos else f"{fallos} FALLOS")
sys.exit(1 if fallos else 0)
