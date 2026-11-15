"""v3.68: en KiraOS, lo que no es una orden («hola», «¿qué es un compilador?») se CONTESTA con el cerebro, como en el
móvil (antes salía «No reconozco la orden»)."""
import os, sys, tempfile
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [R, os.path.join(R, "kira_portatil")]
import nucleo_portatil as npo

FALLOS = 0
def ok(c, m):
    global FALLOS
    print(("OK   " if c else "FALLA ") + m)
    if not c:
        FALLOS += 1

class Core:
    NO_RECONOCIDA = "[i] No reconozco la orden"
    def __init__(self, falla=False, charla=True):
        self.falla = falla; self.vistos = []
        self.dir = tempfile.mkdtemp()
        if charla:
            npo.poner_charla_aqui(self, True)
        class Rec:
            def __init__(s): s.g = []
            def guardar_charla(s, a, b): s.g.append((a, b))
        self.recuerdos = Rec()
    def conversar(self, texto, historial=(), al_trozo=None, sistema=None):
        self.sistema = sistema
        if self.falla:
            raise RuntimeError("no hay cerebro")
        self.vistos.append(list(historial))
        return "respuesta a " + texto

c = Core()
r = npo.charla_si_no_es_orden(c, "hola", "[i] No reconozco la orden 'hola'.")
ok(r["texto"] == "respuesta a hola", "lo que no es una orden se contesta con el cerebro")
r = npo.charla_si_no_es_orden(c, "¿y tú?", "[i] No reconozco la orden '¿y tú?'.")
ok(c.vistos[-1] == [("tu", "hola"), ("kira", "respuesta a hola")], "recuerda la charla anterior")
ok(c.sistema == npo.SISTEMA_CHARLA and len(c.sistema) < 500, "v3.69: le da instrucciones CORTAS (lee menos, contesta antes)")
ok(c.recuerdos.g[-1] == ("¿y tú?", "respuesta a ¿y tú?"), "guarda la charla en el baúl")
ok(npo.charla_si_no_es_orden(c, "x", "Hecho: tema bosque")["texto"] == "Hecho: tema bosque", "una orden de verdad no cambia")
r = npo.charla_si_no_es_orden(Core(falla=True), "hola", "[i] No reconozco la orden 'hola'.")
ok("No he podido contestarte" in r["texto"] and "no hay cerebro" in r["texto"], "sin cerebro, lo dice claro")
# v3.73: por defecto la charla va en el MÓVIL (el portátil guarda el cerebro para trabajar)
c2 = Core(charla=False)
r = npo.charla_si_no_es_orden(c2, "hola", "[i] No reconozco la orden 'hola'.")
ok(r["texto"] == npo.AVISO_CHARLA and not c2.vistos, "v3.73: por defecto, «háblame en el móvil» al momento (sin cerebro)")
r = npo.charla_si_no_es_orden(c2, "activa la charla aquí", "[i] No reconozco la orden.")
ok("también charlo aquí" in r["texto"] and npo.charla_aqui(c2), "«activa la charla aquí» la vuelve a encender")
ok(npo.charla_si_no_es_orden(c2, "hola", "[i] No reconozco la orden.")["texto"] == "respuesta a hola",
   "…y entonces contesta con el cerebro")
r = npo.charla_si_no_es_orden(c2, "charla solo en el móvil", "[i] No reconozco la orden.")
ok(not npo.charla_aqui(c2) and "en el móvil" in r["texto"], "«charla solo en el móvil» la apaga otra vez")
src = open(os.path.join(R, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("return charla_si_no_es_orden(core, o, r, paso)" in src, "ejecutar lo usa al final")
print("TODO BIEN" if not FALLOS else f"{FALLOS} FALLOS")
sys.exit(1 if FALLOS else 0)
