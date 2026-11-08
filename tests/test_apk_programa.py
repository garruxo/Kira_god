# -*- coding: utf-8 -*-
"""v3.07: app Android DE VERDAD de CUALQUIER programa (no solo juegos): la orden, el proyecto que se sube, el reproductor
de programas de texto (print + input) corrido de verdad, la compilación con un GitHub falso y el camino en KiraOS."""
import importlib.util
import os
import sys
import tempfile
import threading
import time
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tests"))
import apk_juegos_kira as apk

fallos = 0
n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ---------- la orden ----------
P = apk.pedido_apk
ok(P("hazme una app android que calcule propinas") == {"pedido": "que calcule propinas"}, "«hazme una app android que…»")
ok(P("Kira, crea una app para android de notas")["pedido"] == "de notas", "«crea una app para android de…»")
ok(P("hazme un apk de una calculadora")["pedido"] == "de una calculadora", "«hazme un apk de…»")
ok(P("haz una aplicación para el móvil que cuente pasos")["pedido"] == "que cuente pasos", "aplicación para el móvil")
ok(P("conviértelo en una app de verdad") == {"pedido": None}, "«conviértelo en una app de verdad» = el último programa")
ok(P("conviértelo en una app android") == {"pedido": None}, "«conviértelo en una app android»")
ok(P("hazme una app android") == {"pedido": None}, "sin decir qué: el último programa")
ok(P("hazme una app de recetas") is None, "«hazme una app de recetas» (sin android) no es esto: es una maqueta")
ok(P("hola qué tal") is None and P("") is None, "lo demás no")
ok(apk.titulo_de("que calcule propinas") == "Calcule propinas" and apk.titulo_de("de una calculadora") == "Calculadora",
   "título corto de la app")

# ---------- qué es el programa ----------
TEXTO = 'nombre = input("¿Cómo te llamas? ")\nprint("Hola,", nombre)\nfor i in range(3):\n    print(i)\n'
KIVY = "from kivy.app import App\nfrom kivy.uix.label import Label\nclass A(App):\n    def build(self):\n        return Label(text='x')\nA().run()\n"
JUEGO = "from motor_juegos_kira import Juego\nclass Pong(Juego):\n    pass\n"
ok(not apk.es_app_kivy(TEXTO) and apk.es_app_kivy(KIVY), "reconoce una app de Kivy")
ok(apk.es_juego(JUEGO) and not apk.es_juego(TEXTO), "reconoce un juego del motor")
ok(apk.librerias_raras("import math, random\nfrom collections import deque\n") == [], "la biblioteca estándar vale")
ok(apk.librerias_raras("import numpy\nimport requests\n") == ["numpy", "requests"], "las librerías de fuera se ven")

# ---------- el proyecto ----------
jid, arch = apk.proyecto_programa(TEXTO, "Saludador", 3)
b = f"juegos/{jid}/"
ok(jid == "saludador" and set(arch) == {b + "main.py", b + "programa.py", b + "icono.png", b + "buildozer.spec"},
   "programa de texto: reproductor + programa.py + icono + receta")
ok(arch[b + "programa.py"].decode() == TEXTO and b"Reproductor de un programa" in arch[b + "main.py"],
   "el programa va tal cual y lo abre el reproductor")
ok(b"version = 1.3" in arch[b + "buildozer.spec"] and b"android.numeric_version = 3" in arch[b + "buildozer.spec"],
   "la versión sube en cada compilación (se instala encima)")
compile(arch[b + "main.py"].decode(), "main.py", "exec")
ok(True, "el reproductor es Python válido")
jid2, arch2 = apk.proyecto_programa(KIVY, "Mi Kivy")
ok(arch2[f"juegos/{jid2}/main.py"].decode() == KIVY and f"juegos/{jid2}/programa.py" not in arch2,
   "una app de Kivy va TAL CUAL como main.py")
try:
    apk.proyecto_programa("import numpy\nprint(1)\n", "X")
    ok(False, "librerías de fuera deberían avisar")
except apk.ApkError as e:
    ok("numpy" in str(e), "con librerías de fuera lo dice claro (no entrarían en la app)")
try:
    apk.proyecto_programa("def (:\n", "X")
    ok(False, "error de escritura")
except apk.ApkError as e:
    ok("error de escritura" in str(e), "un programa mal escrito no se sube")

# ---------- el reproductor, corrido DE VERDAD (sin Kivy: su parte de ejecutar) ----------
with tempfile.TemporaryDirectory() as d:
    open(os.path.join(d, "programa.py"), "w", encoding="utf-8").write(TEXTO)
    sys.path.insert(0, d)
    mod = types.ModuleType("reproductor_prueba")
    exec(compile(arch[b + "main.py"].decode(), "main.py", "exec"), mod.__dict__)
    ej = mod.Ejecutor()
    ok(ej.arrancar() and not ej.arrancar(), "arranca una vez (no dos a la vez)")
    vistos, fin = [], False
    limite = time.time() + 10
    while time.time() < limite and not fin:
        try:
            tipo, dato = ej.cola.get(timeout=0.2)
        except Exception:
            continue
        if tipo == "texto":
            vistos.append(dato)
        elif tipo == "pide":
            ej.contestar("Ana")
        elif tipo == "fin":
            fin = True
    salida = "".join(vistos)
    ok(fin and "¿Cómo te llamas?" in salida and "Hola, Ana" in salida and "2" in salida,
       "lo que imprime sale en pantalla y input() espera tu respuesta: " + repr(salida[:80]))
    ok(sys.stdout.__class__.__name__ != "_Salida", "al acabar devuelve la salida normal")
    # «Otra vez» con el programa esperando una respuesta: se corta y vuelve a empezar
    ej2 = mod.Ejecutor()
    ej2.arrancar()
    limite = time.time() + 5
    while time.time() < limite and not ej2.esperando:
        time.sleep(0.05)
    ej2.parar()
    limite = time.time() + 5
    while time.time() < limite and ej2.corriendo:
        time.sleep(0.05)
    otra = not ej2.corriendo and ej2.arrancar()
    limite = time.time() + 5
    while time.time() < limite and not ej2.esperando:
        time.sleep(0.05)
    ej2.parar()
    limite = time.time() + 5
    while time.time() < limite and ej2.corriendo:
        time.sleep(0.05)
    ok(otra and not ej2.corriendo, "«Otra vez» corta lo que esperaba y vuelve a empezar")
    sys.path.remove(d)

# ---------- compilar en GitHub (falso) ----------
import base64
TOKEN = "ghp_" + "a1B2" * 9


class GitHubFalso:
    def __init__(self):
        self.repo, self.archivos, self.lanzado, self.consultas = False, {}, None, 0

    def __call__(self, metodo, url, token, cuerpo=None):
        ruta = url.replace(apk.API, "")
        if ruta == "/user":
            return 200, {"login": "garruxo"}
        if ruta == "/repos/garruxo/kira-juegos":
            return (200, {"default_branch": "main", "private": False}) if self.repo else (404, {})
        if ruta == "/user/repos" and metodo == "POST":
            self.repo = True
            return 201, {}
        if "/contents/" in ruta:
            p = ruta.split("/contents/", 1)[1].split("?")[0]
            if metodo == "GET":
                return (200, {"sha": apk.blob_sha(self.archivos[p])}) if p in self.archivos else (404, {})
            self.archivos[p] = base64.b64decode(cuerpo["content"])
            return 201, {}
        if ruta.endswith("/dispatches"):
            self.lanzado = cuerpo
            return 204, {}
        if "/actions/runs?" in ruta:
            return 200, {"workflow_runs": [{"id": 7, "display_title": "x " + self.lanzado["inputs"]["marca"]}]}
        if ruta.endswith("/actions/runs/7"):
            self.consultas += 1
            return 200, ({"status": "in_progress"} if self.consultas < 2 else
                         {"status": "completed", "conclusion": "success"})
        return 404, {"message": "no"}


with tempfile.TemporaryDirectory() as d:
    falso = GitHubFalso()
    gh = apk.GitHub(TOKEN, http=falso, dormir=lambda s: None)
    r = apk.compilar(gh, TEXTO, "Saludador", apk.Registro(os.path.join(d, "r.json")), tipo="programa")
    ok("juegos/saludador/programa.py" in falso.archivos and falso.lanzado["inputs"]["juego"] == "saludador"
       and r["url_apk"].endswith("/saludador.apk"), "un PROGRAMA se sube y se compila por el mismo camino")

    # ---------- el núcleo: app_android ----------
    import kira_god
    core = types.SimpleNamespace(dir=d, es_kiraos=False, cancelado=lambda: False, ultimo_codigo=None,
                                 clave_github=lambda: "")
    sin = kira_god.KiraGodCore.app_android(core, "que salude")
    ok(not sin["ok"] and "config github" in sin["texto"], "sin clave de GitHub: cómo ponerla (y escribirla AQUÍ)")
    core.clave_github = lambda: TOKEN
    pedidos = []

    def programa_acordado(p, al_paso=None):
        pedidos.append(p)
        return {"ok": True, "codigo": TEXTO}
    core.programa_acordado = programa_acordado
    bajados = []
    falso2 = GitHubFalso()
    r = kira_god.KiraGodCore.app_android(core, "que salude", gh=apk.GitHub(TOKEN, http=falso2, dormir=lambda s: None),
                                         bajar=lambda url, ruta: (bajados.append(url), open(ruta, "wb").write(b"PK")))
    ok(r["ok"] and pedidos == ["un programa que salude"] and core.ultimo_codigo == TEXTO,
       "escribe el programa (probado en modo seguro) y lo apunta como el último")
    ok(bajados and os.path.isfile(r["ruta"]) and "Lista la app" in r["texto"] and "caja para contestar" in r["texto"],
       "compila, baja el APK y explica cómo es la app")
    core.ultimo_codigo = JUEGO
    falso3 = GitHubFalso()
    r = kira_god.KiraGodCore.app_android(core, None, gh=apk.GitHub(TOKEN, http=falso3, dormir=lambda s: None),
                                         bajar=lambda url, ruta: open(ruta, "wb").write(b"PK"))
    ok(r["ok"] and any(k.endswith("/juego.py") for k in falso3.archivos), "si el último era un JUEGO, va como juego")
    core.ultimo_codigo = None
    r = kira_god.KiraGodCore.app_android(core, None)
    ok(not r["ok"] and "¿De qué hago la app?" in r["texto"], "sin nada que convertir: lo pregunta")

# ---------- KiraOS: la orden llega a app_android ----------
import nucleo_portatil as npk
llamado = []
fc = types.SimpleNamespace(dir=tempfile.mkdtemp(), registrar_actividad=lambda: None, nueva_tarea=lambda: None,
                           ultimo_codigo="print(1)",
                           app_android=lambda p, al_paso=None: (llamado.append(p), {"texto": "hecho", "ok": True})[1],
                           es_estudia_general=lambda o: None)
r = npk.ejecutar(fc, "hazme una app android que calcule propinas", lambda f, t: None)
ok(r["texto"] == "hecho" and llamado == ["que calcule propinas"], "KiraOS: «hazme una app android…» la hace")
r = npk.ejecutar(fc, "Kira, conviértelo en una app de verdad", lambda f, t: None)
ok(llamado[-1] is None, "KiraOS: «conviértelo en una app de verdad» usa el último programa")

# ---------- desde fuera de casa no ----------
import mando_kira as mk
ok(not mk.permitida_fuera("hazme una app android que calcule")[0], "fuera de casa: la app Android espera a casa")
ok(mk.es_trabajo("hazme una app android que calcule propinas"), "en el móvil es trabajo de KiraOS")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
