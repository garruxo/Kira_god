# -*- coding: utf-8 -*-
"""v2.84: pasar la MEMORIA de Kira del móvil al portátil (memoria_kira): qué viaja, qué no, y que importar es seguro."""
import json
import os
import sys
import tempfile
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import memoria_kira as mk
import recuerdos_kira as rk

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


T = tempfile.mkdtemp()
MOVIL = os.path.join(T, "movil")
os.makedirs(os.path.join(MOVIL, "modulos"))
os.makedirs(os.path.join(MOVIL, "modelos"))
B = rk.Recuerdos(os.path.join(MOVIL, "recuerdos"))
B.guardar("Python es un lenguaje de programación interpretado.", tema="python", fuente="estudio")
B.guardar("El perceptrón es la red neuronal más sencilla.", tema="perceptrón", fuente="estudio")
for nombre, cont in (("pensamientos.json", {"notas": [1], "soluciones": {"x": {}}}), ("foco.json", {"tema": "y"}),
                     ("api_key.txt", "sk-secreta"), ("github_token.txt", "ghp_secreto"),
                     ("pasarela.json", {"token": "t"}), ("kira_audit.log", "log")):
    with open(os.path.join(MOVIL, nombre), "w") as f:
        f.write(cont if isinstance(cont, str) else json.dumps(cont))
open(os.path.join(MOVIL, "modulos", "saludo.py"), "w").write("def registrar():\n    return {}\n")
open(os.path.join(MOVIL, "modulos", "api_key.txt"), "w").write("tampoco")
open(os.path.join(MOVIL, "modelos", "cerebro.gguf"), "wb").write(b"x" * 1000)

# ---------- empaquetar ----------
Z = os.path.join(T, "memoria.zip")
r = mk.empaquetar(MOVIL, Z)
nombres = set(zipfile.ZipFile(Z).namelist())
ok("pensamientos.json" in nombres and "foco.json" in nombres, "viajan el cuaderno y el foco")
ok(any(x.startswith("recuerdos/") for x in nombres), "viaja el baúl de recuerdos")
ok("modulos/saludo.py" in nombres, "viajan las mejoras aprobadas")
for malo in ("api_key.txt", "github_token.txt", "pasarela.json", "kira_audit.log", "modulos/api_key.txt",
             "modelos/cerebro.gguf"):
    ok(malo not in nombres, f"NO viaja {malo}")
ok(mk.MARCA in nombres and r["archivos"] >= 4, "lleva su marca y cuenta los archivos")
r2 = mk.empaquetar(MOVIL, os.path.join(T, "m2.zip"), max_archivo=10)
ok(r2["saltados"] and r2["archivos"] < r["archivos"], "un archivo demasiado grande se salta y se avisa")
ok("Me dejé" in mk.texto_resumen(r2), "y lo dice")

# ---------- importar (en el portátil) ----------
PORT = os.path.join(T, "portatil")
os.makedirs(os.path.join(PORT, "recuerdos"))
open(os.path.join(PORT, "foco.json"), "w").write('{"tema": "lo de antes"}')
open(os.path.join(PORT, "api_key.txt"), "w").write("la-del-portatil")
ri = mk.importar(Z, PORT)
ok(ri["archivos"] >= 4 and ri["origen"] == "móvil", "importa la memoria")
ok(json.load(open(os.path.join(PORT, "foco.json")))["tema"] == "y", "el foco ahora es el del móvil")
ok(open(os.path.join(PORT, "api_key.txt")).read() == "la-del-portatil", "no toca la clave del portátil")
ok(ri["respaldo"] and json.load(open(os.path.join(ri["respaldo"], "foco.json")))["tema"] == "lo de antes",
   "lo que había quedó guardado aparte")
B2 = rk.Recuerdos(os.path.join(PORT, "recuerdos"))
ok(B2.total() == 2 and B2.respuesta_directa("qué es el perceptrón"), "el baúl llega entero y se puede leer")
ok(oct(os.stat(os.path.join(PORT, "foco.json")).st_mode & 0o777) == "0o600", "lo importado solo para ti (0600)")

# ---------- paquetes malos ----------
MALO = os.path.join(T, "malo.zip")
with zipfile.ZipFile(MALO, "w") as z:
    z.writestr("../fuera.txt", "x")
    z.writestr("/etc/passwd", "x")
    z.writestr("api_key.txt", "robada")
    z.writestr("modulos/../../escapa.py", "x")
    z.writestr("cosas_raras/x.py", "x")
    z.writestr("notas.json", "{}")
rm = mk.importar(MALO, PORT, respaldo=False)
ok(rm["archivos"] == 1 and len(rm["rechazados"]) == 5, "de un paquete malo solo entra lo permitido")
ok(not os.path.exists(os.path.join(T, "fuera.txt")) and not os.path.exists(os.path.join(T, "escapa.py")),
   "nada se escapa de la carpeta")
ok(open(os.path.join(PORT, "api_key.txt")).read() == "la-del-portatil", "una clave dentro del paquete no entra")
open(os.path.join(T, "no.zip"), "w").write("hola")
try:
    mk.importar(os.path.join(T, "no.zip"), PORT)
    ok(False, "no zip")
except mk.MemoriaError:
    ok(True, "algo que no es un zip se rechaza")

print("\nTODO BIEN", n)
