# -*- coding: utf-8 -*-
"""v2.84: la KIRA COMPLETA en el portátil (nucleo_portatil) y el MÓVIL COMO MANDO (casa_kira + mando_kira + núcleo del
móvil). Con el núcleo de verdad (sin cerebro) en una carpeta temporal y servidores de verdad en 127.0.0.1."""
import ast
import json
import os
import socket
import sys
import tempfile
import threading
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp()
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
os.environ.pop("KIRA_API_KEY", None)
import nucleo_portatil as npo

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


def libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


TOKEN = "t" * 32

# ---------- el reparto de órdenes (con un núcleo de mentira) ----------
class Falso:
    def __init__(self):
        self.hecho = []

    def registrar_actividad(self): pass
    def nueva_tarea(self): pass
    def es_estudia_general(self, o):
        return o[8:] if o.lower().startswith("estudia ") else None
    def estudiar_a_fondo(self, tema, al_paso=None):
        al_paso(0.5, "a mitad"); self.hecho.append(("estudia", tema)); return f"Estudiado {tema}"
    def experimentar(self, tema, al_progreso=None, mejorar=False):
        self.hecho.append(("exp", tema)); return {"ok": True, "texto": "exp", "codigo": "print(1)", "nombre": "e"}
    def programa_acordado(self, pedido, al_paso=None, al_codigo=None):
        al_paso("escribiendo"); self.hecho.append(("prog", pedido)); return {"ok": True, "codigo": "print(2)", "nombre": "p"}
    def aprender_codigo(self, c, al_paso=None):
        self.hecho.append(("cod", c)); return "aprendido"
    def procesar_orden(self, o):
        self.hecho.append(("orden", o)); return "hola desde el núcleo"


f = Falso()
pasos = []
paso = lambda fr, t: pasos.append((fr, t))
ok(npo.ejecutar(f, "Kira, estudia Python", paso)["texto"] == "Estudiado Python", "«estudia X» → estudiar a fondo")
ok((0.5, "a mitad") in pasos, "el estudio cuenta sus pasos (barra)")
r = npo.ejecutar(f, "escríbeme un programa que sume dos números", paso)
ok(r["codigo"] == "print(2)" and f.hecho[-1][0] == "prog", "«escríbeme un programa…» → programa probado con código")
ok(npo.ejecutar(f, "experimenta con algoritmos de ordenación", paso)["codigo"] == "print(1)", "experimentar")
ok(npo.ejecutar(f, "piensa", paso)["texto"] == "hola desde el núcleo" and f.hecho[-1] == ("orden", "piensa"),
   "lo demás (pensar, foco, charla…) → procesar_orden")

# ---------- tareas EN COLA (v2.95): varias esperan; las TUYAS, delante ----------
puertas = {}
hechas = []


def _hacer(o, p):
    p(0.3, "uno:" + o)
    puertas.setdefault(o, threading.Event()).wait(5)
    hechas.append(o)
    return {"texto": "fin " + o}


tr = npo.Trabajos(_hacer)
a = tr.empezar("A")
for _ in range(60):
    if tr.ocupado():
        break
    time.sleep(0.02)
ok(a and tr.ocupado(), "la primera arranca sola")
b = tr.empezar("B")                                  # tuya, en cola (ya NO devuelve None)
ok(b and tr.ver(b)["estado"] == "en cola" and tr.en_cola() == 1, "la segunda no da error: se pone en cola")
fondo = tr.empezar("fondo", tuya=False)              # de fondo (pensar/encargo): al final
c = tr.empezar("C")                                  # tuya: delante de la de fondo
ok(tr.cola == [b, c, fondo], "tus órdenes van delante de las de fondo")
for ev in ("A", "B", "fondo", "C"):
    puertas.setdefault(ev, threading.Event()).set()
for _ in range(100):
    if len(hechas) == 4 and not tr.ocupado():
        break
    time.sleep(0.05)
ok(hechas == ["A", "B", "C", "fondo"], "se hacen en orden: la de curso, luego las tuyas, y al final la de fondo")
v = tr.ver(a)
ok(v["estado"] == "hecho" and v["respuesta"] == "fin A" and v["avance"] == ["uno:A"], "cada tarea acaba con su respuesta")

# pausar: no empieza nuevas; al seguir, sí
tr2 = npo.Trabajos(lambda o, p: (p(0.5, "x"), {"texto": "fin " + o})[1])
tr2.pausar(True)
x = tr2.empezar("X")
time.sleep(0.2)
ok(tr2.ver(x)["estado"] == "en cola" and tr2.en_cola() == 1, "pausada: la tarea espera, no empieza")
tr2.pausar(False)
for _ in range(60):
    if tr2.ver(x)["estado"] == "hecho":
        break
    time.sleep(0.05)
ok(tr2.ver(x)["estado"] == "hecho", "al seguir, la hace")

# ---------- el núcleo DE VERDAD en el portátil, con su servidor ----------
DATOS = os.path.join(T, "kira_datos")
npo.preparar_datos(DATOS, TOKEN, cerebro_url="http://127.0.0.1:9")    # sin cerebro de verdad
pas = json.load(open(os.path.join(DATOS, "pasarela.json")))
ok(pas["token"] == TOKEN and pas["portatil_url"] == "http://127.0.0.1:9", "su cerebro es el del portátil")
ok(os.environ["KIRA_DATA_DIR"] == DATOS, "sus datos van a su carpeta")
nucleo = npo.Nucleo(DATOS)
ok(type(nucleo.core).__name__ == "KiraGodCore", "corre el MISMO núcleo de Kira que el móvil")
P = libre()
srv = npo.crear_servidor("127.0.0.1", P, TOKEN, nucleo)
threading.Thread(target=srv.serve_forever, daemon=True).start()
cli = npo.ClienteNucleo(f"http://127.0.0.1:{P}", TOKEN)
ok(cli.disponible(), "el portátil responde con el token")
ok(not npo.ClienteNucleo(f"http://127.0.0.1:{P}", "malo" * 8).disponible(), "con otro token, no")
t = cli.orden("tus preguntas", cada=0.1)
ok(t["estado"] == "hecho" and isinstance(t["respuesta"], str) and t["respuesta"], "una orden de verdad se hace allí")

# v2.94: si está ocupada (409), lo dice con buenas palabras (no «HTTP Error 409. Conflict»)
import urllib.error, io  # noqa: E402
def _ocupada(req, timeout=10):
    raise urllib.error.HTTPError(req.full_url, 409, "Conflict", {}, io.BytesIO(b'{"actividad": {"pensando": true}}'))
cli_ocup = npo.ClienteNucleo(f"http://127.0.0.1:{P}", TOKEN, abrir=_ocupada)
r = cli_ocup.orden("estudia python")
ok(r["estado"] == "ocupada" and "HTTP" not in r["respuesta"] and "ocupada" in r["respuesta"].lower()
   and "pensando" in r["respuesta"], "ocupada (409): mensaje amable, no el error crudo")
def _otro(req, timeout=10):
    raise urllib.error.HTTPError(req.full_url, 500, "Boom", {}, io.BytesIO(b""))
try:
    npo.ClienteNucleo(f"http://127.0.0.1:{P}", TOKEN, abrir=_otro).orden("x")
    ok(False, "un 500 sí debe propagarse")
except urllib.error.HTTPError as e:
    ok(e.code == 500, "otros errores (500) siguen saliendo como antes")
# v2.95: estado ligero, pausar y seguir por el servidor
est = cli.estado()
ok(all(k in est for k in ("ocupada", "en_cola", "pausada", "cola", "actividad")), "/estado da el estado del trabajo")
ok(cli.pausar(True).get("pausada") is True and cli.estado()["pausada"] is True, "se puede pausar")
ok(cli.seguir().get("pausada") is False, "y seguir")
ok("en_cola" in cli._pedir("/hola"), "/hola también dice cuántas esperan")
ok(cli.cancelar().get("ok") is True, "el botón de parar llega al núcleo")
ok("WEBKIT_DISABLE_COMPOSITING_MODE" in open(os.path.join(RAIZ, "kira_portatil", "kiraos.py"), encoding="utf-8").read(),
   "kiraos desactiva la aceleración gráfica (efecto agua en gráficas viejas)")

# ---------- el MÓVIL: su memoria viaja al portátil ----------
import memoria_kira as mk
import recuerdos_kira as rk
MOVIL = os.path.join(T, "movil")
rk.Recuerdos(os.path.join(MOVIL, "recuerdos")).guardar("Mi persona juega al ajedrez.", tema="aficiones",
                                                        fuente="usuario")
open(os.path.join(MOVIL, "foco.json"), "w").write('{"tema": "un buscador", "activo": false}')
Z = os.path.join(T, "m.zip")
mk.empaquetar(MOVIL, Z)

import casa_kira as ck
import pasarela_cliente as pcl
casa = ck.Casa()
casa.disponible = lambda forzar=False: True
ck.PUERTO_NUCLEO = P
pcl.guardar_config("http://127.0.0.1:8765", TOKEN, portatil_url="http://127.0.0.1:9")   # en la carpeta del portátil
ok(casa.nucleo_url == f"http://127.0.0.1:{P}", "el móvil sabe dónde está la Kira completa (puerto 8771)")
ok(casa.nucleo_disponible(), "y la encuentra")
txt = casa.enviar_memoria(Z)
ok("recibido" in txt, "le pasa su memoria")
ok(any("ajedrez" in (nucleo.core.recuerdos.leer(i) or {}).get("texto", "")
       for i in range(1, nucleo.core.recuerdos.total() + 1)), "el portátil ya recuerda lo del móvil (núcleo reiniciado)")
ok(json.load(open(os.path.join(DATOS, "foco.json")))["tema"] == "un buscador", "y su foco")
lineas = []
t = casa.orden("tus preguntas", al_paso=lambda fr, l: lineas.append(l), dormir=lambda s: time.sleep(0.05))
ok(t["estado"] == "hecho", "el móvil manda una orden y recibe la respuesta")
ok(casa.cancelar_nucleo(), "y puede pararla («para»)")
casa.token  # noqa
mal = ck.Casa()
mal.disponible = lambda forzar=False: True
try:
    pcl.guardar_config("http://127.0.0.1:8765", "otro" * 8, portatil_url="http://127.0.0.1:9")
    mal._nucleo("/hola")
    ok(False, "token malo")
except ck.CasaError:
    ok(True, "con otro token, el portátil no obedece")
finally:
    pcl.guardar_config("http://127.0.0.1:8765", TOKEN, portatil_url="http://127.0.0.1:9")
srv.shutdown()

# ---------- el núcleo del MÓVIL: modo mando y pasar la memoria ----------
import kira_god
os.environ["KIRA_DATA_DIR"] = MOVIL
core = kira_god.KiraGodCore()
ok(core.modo_mando() is True, "el modo mando viene encendido")
ok(core.modo_mando(False) is False and core.modo_mando() is False and core.mando_listo() is False, "se apaga")
core.modo_mando(True)


class CasaFalsa:
    def __init__(self):
        self.zip = None
    def nucleo_disponible(self): return True
    def nucleo_hola(self): return {"version": "2.84", "recuerdos": 3, "ocupada": True, "haciendo": "estudiar Python"}
    def enviar_memoria(self, ruta):
        self.zip = set(__import__("zipfile").ZipFile(ruta).namelist())
        return "He recibido 5 archivos de memoria."


cf = CasaFalsa()
core._casa = lambda: cf
ok(core.mando_listo(esperar=True) is True, "con el portátil en casa, el mando está listo")
ok("estudiar Python" in core.mando_estado(), "«estado del portátil» dice qué hace")
r = core.pasar_memoria()
ok(r.startswith("Listo") and cf.zip and any(x.startswith("recuerdos/") for x in cf.zip), "pasa su memoria")
ok(not os.path.exists(os.path.join(MOVIL, "memoria_para_portatil.zip")), "y borra el paquete al acabar")

# ---------- qué se queda en el móvil ----------
import mando_kira as mdk
for frase, esp in (("modo mando", "on"), ("Kira, trabaja en el portátil", "on"), ("trabaja en el móvil", "off"),
                   ("pasa tu memoria al portátil", "memoria"), ("estado del portátil", "estado"),
                   ("estudia Python", None)):
    ok(mdk.orden_control(frase) == esp, f"control: «{frase}»")
for frase in ("abre la sala hacker", "hazme una foto", "qué ves", "para", "pinta un gato", "implementa este código",
              "sube el volumen", "mejora tu oído"):
    ok(mdk.es_local(frase), f"«{frase}» se hace en el móvil")
for frase in ("estudia Python", "piensa", "para qué sirve un trie", "escríbeme un programa que ordene",
              "investiga qué es un compilador", "mejora sin parar los buscadores", "tu cuaderno"):
    ok(not mdk.es_local(frase), f"«{frase}» se lo paso al portátil")

# ---------- cableado en la pantalla del móvil y en el portátil ----------
src_i = open(os.path.join(RAIZ, "interfaz_kira.py"), encoding="utf-8").read()
ok("def mando_por_voz" in src_i and "def mando_control" in src_i, "la pantalla tiene el mando")
i_hook = src_i.find("mdk_.orden_control(orden)")
ok(0 < i_hook < src_i.find("exp = ex_.pedido_experimento(orden)"), "el mando va antes de programar/estudiar aquí")
ok("core.mando_listo(esperar=True)" in src_i, "al abrir, mira si está el portátil (en segundo plano)")
sh = open(os.path.join(RAIZ, "kira_portatil", "instalar_portatil.sh"), encoding="utf-8").read()
ok("kira-nucleo.service" in sh and "nucleo_portatil.py" in sh and "8771/tcp" in sh, "el instalador la deja arrancando")
src_e = open(os.path.join(RAIZ, "kira_portatil", "kira_escritorio.py"), encoding="utf-8").read()
ok("nucleo.orden(" in src_e, "la ventana del portátil también usa la Kira completa")
ast.parse(src_i)

print("\nTODO BIEN", n)
