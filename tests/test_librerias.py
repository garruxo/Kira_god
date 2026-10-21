# -*- coding: utf-8 -*-
"""v2.31: librerías de Python desde PyPI (servidor FALSO): solo las de Python puro, con sus dependencias, huella sha256,
sin rutas peligrosas, instalar SOLO con tus dos toques; luego el editor, el laboratorio y las mejoras las pueden importar."""
import hashlib, http.server, io, json, os, sys, tempfile, threading, time, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import librerias_kira as lk
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

def rueda(nombre, archivos, top=None):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for ruta, texto in archivos.items():
            z.writestr(ruta, texto)
        z.writestr(f"{nombre}-1.0.dist-info/METADATA", f"Name: {nombre}\nVersion: 1.0\n")
        if top:
            z.writestr(f"{nombre}-1.0.dist-info/top_level.txt", top + "\n")
    return b.getvalue()
RUEDAS = {
    "holamundo-1.0-py3-none-any.whl": rueda("holamundo", {"holamundo/__init__.py": "from ayudante import doble\n"
                                                         "def saluda(x):\n    return 'hola ' + doble(x)\n"}, "holamundo"),
    "ayudante-1.0-py3-none-any.whl": rueda("ayudante", {"ayudante.py": "def doble(x):\n    return x * 2\n"}),
    "malvada-1.0-py3-none-any.whl": rueda("malvada", {"../../fuera.py": "x = 1\n"}),
    "trucada-1.0-py3-none-any.whl": rueda("trucada", {"trucada.py": "x = 1\n"}),
}
def ficha(nombre, deps=(), sin_rueda=False, sha_mala=False, req_py=">=3.8"):
    f = f"{nombre}-1.0-py3-none-any.whl"
    urls = [{"packagetype": "sdist", "filename": f"{nombre}-1.0.tar.gz", "url": "x", "size": 10}]
    if sin_rueda:
        urls.append({"packagetype": "bdist_wheel", "filename": f"{nombre}-1.0-cp311-cp311-manylinux_x86_64.whl",
                     "url": "x", "size": 10})
    else:
        datos = RUEDAS[f]
        urls.append({"packagetype": "bdist_wheel", "filename": f, "url": f"{URL}/ruedas/{f}", "size": len(datos),
                     "digests": {"sha256": "0" * 64 if sha_mala else hashlib.sha256(datos).hexdigest()}})
    return {"info": {"name": nombre, "version": "1.0", "summary": f"La librería {nombre}", "license": "MIT",
                     "requires_python": req_py, "requires_dist": list(deps)}, "urls": urls}
class PyPI(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        fichas = {"holamundo": ficha("holamundo", ["ayudante>=1", "pytest; extra == 'test'", "tomli; python_version < '3.11'"]),
                  "ayudante": ficha("ayudante"), "compilada": ficha("compilada", sin_rueda=True),
                  "malvada": ficha("malvada"), "trucada": ficha("trucada", sha_mala=True),
                  "moderna": ficha("ayudante", req_py=">=3.13"), "usa-compilada": ficha("holamundo", ["compilada"])}
        if self.path.startswith("/ruedas/"):
            datos = RUEDAS[self.path[8:]]
            self.send_response(200); self.send_header("Content-Length", str(len(datos))); self.end_headers()
            self.wfile.write(datos); return
        nombre = self.path.strip("/").split("/")[1] if self.path.count("/") >= 2 else ""
        if nombre not in fichas:
            self.send_response(404); self.end_headers(); return
        d = json.dumps(fichas[nombre]).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(d)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), PyPI)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}"

# ---------- frases ----------
ok(lk.interpretar("Kira, instala la librería kivymd") == {"accion": "preparar", "nombre": "kivymd"}, "«instala la librería X»")
ok(lk.interpretar("quita la librería rich")["accion"] == "quitar" and lk.interpretar("mis librerías")["accion"] == "lista", "quitar y lista")
ok(lk.interpretar("instala whatsapp") is None, "instalar una app no es esto")
ok(lk.dependencias(["a>=1", "b; extra == 'dev'", "c; python_version < '3.11'", "d; sys_platform == 'win32'", "e"]) == ["a", "e"],
   "dependencias que hacen falta en el móvil")

# ---------- preparar e instalar ----------
L = lk.Librerias(os.path.join(T, "librerias"))
L.pypi = URL + "/pypi/{}/json"
p = L.preparar("holamundo")
ok([x["nombre"] for x in p["plan"]] == ["holamundo", "ayudante"] and "ayudante" in L.texto_plan(), "plan con su dependencia")
try:
    L.instalar_pendiente(); ok(False, "sin confirmación")
except lk.LibreriaError as e:
    ok("confirmación" in str(e) and L.pendiente is not None, "sin tus dos toques no instala nada")
ok(L.instalar_pendiente(True) == ["ayudante 1.0", "holamundo 1.0"], "instala (primero la dependencia)")
L.activar()
import holamundo
ok(holamundo.saluda("ja") == "hola jaja", "y se puede importar")
ok({"holamundo", "ayudante"} <= set(L.importables()), "sabe qué nombres se importan")
for nombre, frase in (("compilada", "compiladas"), ("usa-compilada", "dependencia"), ("moderna", "3.11"),
                      ("noexiste", "No existe"), ("holamundo", "ya está instalada")):
    try:
        L.preparar(nombre); ok(False, nombre)
    except lk.LibreriaError as e:
        ok(frase in str(e), f"{nombre}: lo explica ({e})")
for nombre, frase in (("malvada", "ruta peligrosa"), ("trucada", "huella")):
    L.preparar(nombre)
    try:
        L.instalar_pendiente(True); ok(False, nombre)
    except lk.LibreriaError as e:
        ok(frase in str(e), f"{nombre}: no la instala ({e})")
ok(not os.path.exists(os.path.join(T, "fuera.py")), "nada fuera de su carpeta")

# ---------- el editor, el laboratorio y las mejoras las aceptan ----------
os.environ["KIRA_DATA_DIR"] = T                  # el índice está en KIRA_DATA_DIR/librerias
import ejecutor_kira as ej, laboratorio_movil_kira as lm
r = ej.ejecutar("import holamundo\nprint(holamundo.saluda('ab'))")
ok(r["ok"] and "hola abab" in r["salida"], "en el editor: " + str(r["error"]))
ok(ej.revisar("import requests") is not None, "lo no instalado sigue sin poderse")
MOD = "import holamundo\ndef registrar():\n    return {'saluda doble': lambda t: holamundo.saluda(t)}\n"
v = lm.LaboratorioMovil().probar("saluda_doble", MOD)
ok(v["ok"], "una mejora que la usa pasa el laboratorio del móvil: " + str([e for e in v["etapas"] if not e["ok"]]))
ok("numpy" in lk.extra_permitidos() and ej.ejecutar("import numpy\nprint(numpy.arange(3).sum())")["ok"], "numpy, si está")

# ---------- el núcleo y la interfaz ----------
import kira_god
core = kira_god.KiraGodCore()
core.librerias.pypi = L.pypi
ok("holamundo" in core.orden_librerias("mis librerías"), "«mis librerías»")
ok("holamundo" in core.texto_librerias_para_programar(), "el cerebro sabe que puede usarlas al programar")
r = core.procesar_orden("instala la librería holamundo")
ok("ya está instalada" in r, "si ya está, lo dice")
ok(core.procesar_orden("quita la librería ayudante").startswith("[OK]") and "ayudante" not in core.librerias.indice, "quitar")
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
import inicio_kira as ik
class VozMuda:
    def __init__(s): s.dichos = []
    def puede_hablar(s): return True
    def puede_escuchar(s): return False
    def hablando(s): return False
    def hablar(s, t): s.dichos.append(t); return True
    def callar(s): pass
    def iniciar_escucha(s, idioma="es-ES"): return False, "no"
    def sondear(s): return "error", "no"
    def parar_escucha(s): pass
VOZ = VozMuda(); ik.Voz = lambda *a, **k: VOZ
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
def correr(seg=3.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.3)
        if cond and cond(): return True
        time.sleep(0.02)
    return bool(cond and cond())
def textos(nombre): return [w.text for w in sm.get_screen(nombre).walk() if hasattr(w, "text") and isinstance(w.text, str)]
correr(0.8)
campo = next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "TextInput")
campo.text = "Kira, instala la librería ayudante"
next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
ok(correr(4, lambda: sm.current == "librerias" and any("La librería ayudante" in t for t in textos("librerias"))),
   "por voz: te enseña qué es en «Librerías»")
ok(correr(2, lambda: any("Toca Instalar dos veces" in d for d in VOZ.dichos)) and "ayudante" not in core.librerias.indice,
   "y NO la instala sola")
b = next(w for w in sm.get_screen("librerias").walk() if type(w).__name__ == "Button" and w.text == "Instalar")
b.press(); correr(0.3)
ok("ayudante" not in core.librerias.indice and "Seguro" in b.text, "primer toque: pide confirmar")
b.press()
ok(correr(4, lambda: "ayudante" in core.librerias.indice), "segundo toque: instalada")
print("LIBRERÍAS OK", n)
srv.shutdown()
