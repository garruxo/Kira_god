# -*- coding: utf-8 -*-
"""v3.72: cuando le hablas a KiraOS, lo que Kira está pensando SOLA suelta el cerebro (se corta) para contestarte antes."""
import inspect
import os
import sys
import tempfile
import threading

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
os.environ["HOME"] = tempfile.mkdtemp()
import kira_god
import pensador_kira as pn
import cerebro_ia_kira as ci
import nucleo_portatil as npo

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


core = kira_god.KiraGodCore()
res = {}


def fondo(clave):
    kira_god._HILO.fondo = True
    res[clave] = core.cancelado()


def en_hilo(fn, *a):
    t = threading.Thread(target=fn, args=a)
    t.start()
    t.join()


en_hilo(fondo, "sin_dueno")
ok(res["sin_dueno"] is False, "pensando sola y sin nadie esperando: sigue")
with core.dueno_atendido():
    en_hilo(fondo, "con_dueno")
    ok(core.cancelado() is False, "tu propia orden NO se corta")
ok(res["con_dueno"] is True, "si TÚ esperas, lo que piensa sola suelta el cerebro")
en_hilo(fondo, "despues")
ok(res["despues"] is False, "al acabar tu orden, vuelve a poder pensar")

# el pensador no apunta «no pude pensar» si lo cortaron para atenderte: deja pasar la Cancelada
est = pn._vacio() if hasattr(pn, "_vacio") else {"notas": [], "vistas": []}


def corta(_p):
    raise ci.Cancelada("Cancelado: lo has parado tú.")


try:
    pn.pensar_una(est, corta, semillas=["listas"])
    ok(False, "la Cancelada debía pasar hacia arriba")
except ci.Cancelada:
    ok(True, "pensador: cortar para atenderte no deja una nota de error")
ok(not est.get("notas"), "…y el cuaderno no se ensucia")

src = inspect.getsource(kira_god.KiraGodCore.pensar_sola)
ok("_HILO.fondo = True" in src and '"Cancelada"' in src, "el hilo de pensar se marca y no cuenta el corte como fallo")
ok("dueno_atendido" in inspect.getsource(npo.Nucleo._hacer), "cada orden en KiraOS hace que el pensar ceda el cerebro")

print("TODO BIEN" if not fallos else f"{fallos} FALLOS")
sys.exit(1 if fallos else 0)
