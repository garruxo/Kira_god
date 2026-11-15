# -*- coding: utf-8 -*-
"""v3.76: el TALLER de programas — Kira trabaja con un programa de órdenes (del sistema o uno que DESCARGASTE) y tú
ves en una ventana cada orden y lo que contesta. Prepara el plan, espera tu «Hazlo» (dos toques) y nunca se salta
los candados."""
import os
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_TALLER"] = os.path.join(T, "taller")
os.environ["KIRA_DATOS_NUCLEO"] = os.path.join(T, "datos")
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import taller_programas_kira as tp

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


PY = "python3"
O = tp.orden
ok(O("trabaja con ffmpeg: convierte video.mp4 a mp3") == ("ffmpeg", "convierte video.mp4 a mp3"), "trabaja con X: tarea")
ok(O("Kira, usa python3 para calcular 2 elevado a 100") == ("python3", "calcular 2 elevado a 100"), "usa X para …")
ok(O("abre el taller de git") == ("git", ""), "abre el taller de X")
ok(O("usa firefoxquenoexiste para ver algo") is None, "«usa X para» con algo que no tengo: no se lo come")
ok(O("hola") is None and O("abre firefox") is None, "lo demás no es esto")
ok(tp.es_ver("abre el taller"), "abre el taller = la ventana")

V = tp.validar_orden
ok(V('python3 -c "print(1)"', PY)[1:] == ["-c", "print(1)"], "una orden buena")
for mala, por in [("python3 a.py | grep x", "tuberías"), ("python3 -c x; rm -rf ~", "tuberías"),
                  ("rm -rf /", "empezar por"), ("python3 /etc/passwd", "fuera de tu carpeta"),
                  ("python3 ../x", "«..»"), ("python3 $(whoami)", "tuberías"), ("python3 > out", "tuberías")]:
    try:
        V(mala, PY)
        ok(False, f"rechaza: {mala}")
    except ValueError as e:
        ok(por in str(e), f"rechaza «{mala}»: {e}")
ok(tp.prohibido("sudo") and tp.prohibido("bash") and tp.prohibido("mkfs.ext4") and not tp.prohibido(PY), "lista de nunca")
buenas, malas = tp.ordenes_de("Vale:\n$ python3 -c \"print(7)\"\n$ rm -rf x\nNOTA: nada\n```\npython3 --version\n```", PY)
ok(buenas == ['python3 -c "print(7)"', "python3 --version"] and len(malas) == 1, f"saca las órdenes y aparta las malas: {buenas} {malas}")

# ---------- preparar: lee la ayuda y deja el plan ESPERANDO (no ejecuta nada) ----------
pedidos = []


def cerebro(sistema, usuario):
    pedidos.append(usuario)
    return '$ python3 -c "print(2**100)"\n$ python3 -c "open(\'hecho.txt\',\'w\').write(\'ok\')"\n$ sudo reboot'


s, txt = tp.preparar(PY, "calcula 2 elevado a 100", cerebro)
ok(s["estado"] == "esperando" and len(s["plan"]) == 2 and "Hazlo" in txt, "plan listo, espera tu «Hazlo»: " + txt[:80])
ok("usage" in pedidos[-1].lower() or "python" in pedidos[-1].lower(), "el cerebro recibió la ayuda de verdad del programa")
ok(s["rechazadas"] and "sudo" in s["rechazadas"][0]["orden"], "lo de sudo no entra en el plan (y se dice)")
ok(not s["registro"] and not os.path.exists(os.path.join(s["carpeta"], "hecho.txt")), "y NO ha ejecutado nada")
ok(tp.preparar("sudo", "x", cerebro)[1].startswith("[x]"), "programas prohibidos: no")
ok("No tengo" in tp.preparar("noexisteprograma", "x", cerebro)[1], "si no lo tengo, lo dice (y cómo instalarlo)")

# ---------- «Hazlo»: ejecuta en vivo ----------
ob = tp.Obrero()
ok("Empiezo" in ob.empezar(), "empieza")
for _ in range(100):
    if not ob.ocupado():
        break
    time.sleep(0.05)
s = tp.leer()
reg = "\n".join(s["registro"])
ok("1267650600228229401496703205376" in reg and "✓ bien" in reg, "se ve cada orden y lo que contesta")
ok(s["estado"] == "hecho" and "2 de 2" in s["resumen"], "terminado: " + s.get("resumen", ""))
ok(os.path.exists(os.path.join(s["carpeta"], "hecho.txt")), "trabaja en SU carpeta del taller")
ok("ARCHIVOS EN LA CARPETA: hecho.txt" in tp.texto_ventana(s), "la ventana dice qué archivos quedaron")

# ---------- «Parar» ----------
open(os.path.join(tp.carpeta_de(PY), "contar.py"), "w").write("import time\nfor i in range(200):\n    print(i, flush=True)\n    time.sleep(0.1)\n")
s, _t = tp.preparar(PY, "contar", lambda a, b: "$ python3 -c \"import os; os.system('ls')\"; ls\n$ python3 -u contar.py")
ok(s["plan"] == ["python3 -u contar.py"], "el «;» tampoco cuela desde el cerebro")
ob.empezar()
time.sleep(1.0)
ob.parar()
for _ in range(60):
    if not ob.ocupado():
        break
    time.sleep(0.05)
s = tp.leer()
ok(s["estado"] == "parado" and not ob.ocupado(), "«Parar» la corta al momento: " + str(s["registro"][-3:]))

# ---------- un programa que DESCARGASTE ----------
import accesos_kira as ak
os.makedirs(os.environ["KIRA_DATOS_NUCLEO"], exist_ok=True)
app = os.path.join(T, "kira_portatil", "apps_externas", "mitool")
os.makedirs(app)
open(os.path.join(app, "main.py"), "w").write("import sys\nif '--help' in sys.argv: print('mitool: uso mitool --saluda NOMBRE')\nelse: print('hola', sys.argv[2])\n")
ak.anadir_externa(os.environ["KIRA_DATOS_NUCLEO"], "MiTool", [sys.executable, os.path.join(app, "main.py")], app)
ok(tp.resolver("mitool")[1][-1].endswith("main.py"), "encuentra el programa que descargaste")
ok(O("usa mitool para saludar a Pepe") == ("mitool", "saludar a Pepe"), "«usa X para…» vale con lo descargado")
s, txt = tp.preparar("mitool", "saluda a Pepe", lambda a, b: "$ mitool --saluda Pepe" if "mitool: uso" in b else "")
ok(s["plan"] == ["mitool --saluda Pepe"] and s["descargado"], "lee SU ayuda y prepara el plan: " + txt[:60])
ob.empezar()
for _ in range(100):
    if not ob.ocupado():
        break
    time.sleep(0.05)
ok("hola Pepe" in "\n".join(tp.leer()["registro"]), "y lo maneja: se ve lo que contesta")
ok("lo descargaste tú" in tp.texto_ventana(tp.leer()), "la ventana dice que es uno tuyo")

# ---------- el núcleo y la pantalla ----------
import nucleo_portatil as npo


class Core:
    dir = os.environ["KIRA_DATOS_NUCLEO"]

    def registrar_actividad(self):
        pass

    def nueva_tarea(self):
        pass

    def _clave_para(self, t):
        return "LOCAL_X"

    def _llamar_api(self, clave, system, usuario, **k):
        return '$ python3 -c "print(42)"'


r = npo.ejecutar(Core(), "trabaja con python3: dime 42", lambda *a: None)
ok("Hazlo" in r["texto"] and tp.leer()["plan"] == ['python3 -c "print(42)"'], "el núcleo prepara el plan")
import escritorio_kira as ek
esc = ek.EscritorioMixin()
a = esc.app("taller")
ok(a["titulo"].startswith("Taller") and any(b["accion"] == "hacer:hazlo" and b.get("dos") for b in a["botones"]),
   "la ventana Taller con «Hazlo» (dos toques)")
r = esc.app_hacer("taller", "hazlo")
ok("Empiezo" in r["texto"], "Hazlo desde la ventana")
for _ in range(100):
    if not esc._obrero_taller().ocupado():
        break
    time.sleep(0.05)
ok("42" in esc.app("taller")["texto"], "la ventana enseña lo que va haciendo")
import ventanas_kira as vk
b = vk.construir("crea un botón en el escritorio que trabaje con python3 para calcular primos")[2]["botones"][0]
ok(b["orden"] == "trabaja con python3 para calcular primos" and O(b["orden"])[0] == "python3",
   "un BOTÓN puede abrir el taller de un programa")
html = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html"), encoding="utf-8").read()
ok('taller:"Taller"' in html and 'd.abrir==="taller"' in html, "la pantalla abre la ventana del Taller sola")

print(f"\n{'TODO BIEN' if not fallos else str(fallos) + ' FALLOS'} ({n})")
sys.exit(1 if fallos else 0)
