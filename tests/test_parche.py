# -*- coding: utf-8 -*-
"""v3.30: parchear en vez de reescribir todo.

Cuando Kira CAMBIA un módulo que ya existe, no reescribe el código entero: dice solo las líneas que cambia, añade o
quita (formato CAMBIA/POR, AÑADE DESPUÉS DE/NUEVO, AÑADE AL FINAL, QUITA) y se aplican sobre el código de ahora. Si el
parche no encaja, se reescribe entero. Siempre con la red de seguridad de siempre (laboratorio + dos toques)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp()
os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)

import parche_kira as pk

n = fallos = 0


def ok(c, m):
    global n, fallos
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


BASE = '''def registrar():
    def ventana(texto):
        botones = [
            {"texto": "Redes guardadas", "orden": "redes guardadas"},
            {"texto": "Arregla la wifi", "orden": "arregla la wifi"},
        ]
        return {"en": "wifi", "titulo": "Mis redes", "texto": "Atajos.", "botones": botones}
    return {"ventana mis redes": ventana}
'''

# ---------------- CAMBIA … POR … ----------------
r = pk.aplicar(BASE, 'CAMBIA:\n'
                     '        return {"en": "wifi", "titulo": "Mis redes", "texto": "Atajos.", "botones": botones}\n'
                     'POR:\n'
                     '        return {"en": "wifi", "titulo": "Redes de casa", "texto": "Atajos.", "botones": botones}\n')
ok('"titulo": "Redes de casa"' in r and '"titulo": "Mis redes"' not in r, "CAMBIA/POR cambia solo esa línea")
ok("Arregla la wifi" in r and "def registrar" in r, "el resto del módulo queda intacto")
compile(r, "<parche>", "exec")  # sigue siendo Python válido

# ---------------- AÑADE DESPUÉS DE … NUEVO … ----------------
r = pk.aplicar(BASE, 'AÑADE DESPUÉS DE:\n'
                     '            {"texto": "Redes guardadas", "orden": "redes guardadas"},\n'
                     'NUEVO:\n'
                     '            {"texto": "Apaga la wifi", "orden": "apaga la wifi"},\n')
ok("Apaga la wifi" in r, "AÑADE DESPUÉS DE mete la línea nueva")
ok(r.index("Apaga la wifi") > r.index("Redes guardadas") and r.index("Apaga la wifi") < r.index("Arregla la wifi"),
   "la mete JUSTO después de la línea de referencia")
compile(r, "<parche>", "exec")

# ---------------- AÑADE AL FINAL ----------------
r = pk.aplicar(BASE, "AÑADE AL FINAL:\n# un comentario al final\n")
ok(r.rstrip().endswith("# un comentario al final"), "AÑADE AL FINAL lo pone al final")

# ---------------- QUITA ----------------
r = pk.aplicar(BASE, 'QUITA:\n            {"texto": "Arregla la wifi", "orden": "arregla la wifi"},\n')
ok("Arregla la wifi" not in r and "Redes guardadas" in r, "QUITA borra esa línea y deja el resto")
compile(r, "<parche>", "exec")

# ---------------- varios bloques a la vez ----------------
r = pk.aplicar(BASE, 'CAMBIA:\n'
                     '        return {"en": "wifi", "titulo": "Mis redes", "texto": "Atajos.", "botones": botones}\n'
                     'POR:\n'
                     '        return {"en": "wifi", "titulo": "Casa", "texto": "Atajos.", "botones": botones}\n'
                     'QUITA:\n'
                     '            {"texto": "Arregla la wifi", "orden": "arregla la wifi"},\n')
ok('"titulo": "Casa"' in r and "Arregla la wifi" not in r, "varios bloques en una respuesta")

# ---------------- envuelto en ```python ----------------
r = pk.aplicar("x = 1\n", "```python\nCAMBIA:\nx = 1\nPOR:\nx = 2\n```")
ok(r == "x = 2\n", "quita las vallas ``` y aplica igual")

# ---------------- variantes y acentos ----------------
ok(pk.aplicar("x = 1\n", "REEMPLAZA:\nx = 1\nPOR:\nx = 2\n") == "x = 2\n", "REEMPLAZA vale como CAMBIA")
ok(pk.aplicar("x = 1\n", "SUSTITUYE:\nx = 1\nESTO:\nx = 9\n") == "x = 9\n", "SUSTITUYE…ESTO vale")
ok(pk.aplicar("a = 1\nb = 2\nc = 3\n", "QUITA:\nb = 2\n") == "a = 1\nc = 3\n", "QUITA en código simple")

# ---------------- lo que NO debe pasar ----------------
ok(pk.aplicar_seguro("x = 1\n", "CAMBIA:\nno existe\nPOR:\ny = 2\n") is None, "si la línea de ahora no está: None")
ok(pk.aplicar_seguro("x = 1\n", "no hay ningún cambio aquí") is None, "sin formato de parche: None")
ok(pk.aplicar_seguro("x\nx\n", "CAMBIA:\nx\nPOR:\ny\n") is None, "una línea corta ambigua (aparece 2 veces): None")
try:
    pk.aplicar("x = 1\n", "CAMBIA:\nno existe\nPOR:\ny = 2\n")
    ok(False, "aplicar lanza ParcheError si no encaja")
except pk.ParcheError:
    ok(True, "aplicar lanza ParcheError si no encaja")

# ---------------- detectar un CAMBIO con «Código actual» ----------------
import ventanas_kira as vk

ped = vk.pedido_cambio({"id": "mis_redes", "modulo": "mis_redes", "titulo": "Mis redes"}, BASE,
                       "cambia el título a Redes de casa")
pc = pk.codigo_de_pedido(ped)
ok(pc is not None and pc[0] == "mis_redes" and "def registrar" in pc[1], "codigo_de_pedido saca (nombre, código) del cambio")
ok(pk.codigo_de_pedido("Convierte este código en una mejora:\n```python\ndef registrar():\n    return {}\n```") is None,
   "NO se dispara con «convierte este código» (ahí el código es un programa, no el módulo de ahora)")
ok(pk.codigo_de_pedido("Crea una mejora que salude a la gente") is None, "un pedido normal (sin código) → None")

ok(pk.nombre_de(BASE) == "ventana_mis_redes", "nombre_de saca el nombre de la primera orden")
ok(pk.nombre_de("def registrar():\n    return {}\n") == "mejora", "sin orden clara → «mejora»")

# ---------------- de punta a punta con el núcleo ----------------
import kira_god
import cerebro_ia_kira as ci

core = kira_god.KiraGodCore()
core.cerebro_ia.local_disponible = lambda forzar=False: True  # cerebro del móvil listo → clave LOCAL

BASE_CAMBIADO = BASE.replace("Mis redes", "Redes de casa")
PARCHE = ('CAMBIA:\n'
          '        return {"en": "wifi", "titulo": "Mis redes", "texto": "Atajos.", "botones": botones}\n'
          'POR:\n'
          '        return {"en": "wifi", "titulo": "Redes de casa", "texto": "Atajos.", "botones": botones}\n')


def api_parche(clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None, codigo=False):
    if "CAMBIAR un módulo" in system:          # modo parche
        return PARCHE
    raise AssertionError("no debería reescribir entero: el parche ya encajó")


core._llamar_api = api_parche
nombre, nuevo = core.generar_mejora(ped)
ok(nombre == "mis_redes" and '"titulo": "Redes de casa"' in nuevo and "Arregla la wifi" in nuevo,
   "generar_mejora PARCHEA (una sola llamada) y conserva lo demás")


def api_falla(clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None, codigo=False):
    if "CAMBIAR un módulo" in system:          # el cerebro no sabe parchear
        return "lo siento, no sé cómo hacer ese parche"
    return "NOMBRE: mis_redes\n```python\n" + BASE_CAMBIADO + "```"   # reescribe entero


core._llamar_api = api_falla
nombre, nuevo = core.generar_mejora(ped)
ok("Redes de casa" in nuevo and "def registrar" in nuevo, "si el parche no encaja, reescribe el módulo entero")


def api_entero(clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None, codigo=False):
    if "CAMBIAR un módulo" in system:          # el cerebro ignora el formato y escribe el módulo entero
        return "NOMBRE: mis_redes\n```python\n" + BASE_CAMBIADO + "```"
    raise AssertionError("no hace falta otra llamada: el módulo entero ya vino")


core._llamar_api = api_entero
nombre, nuevo = core.generar_mejora(ped)
ok("Redes de casa" in nuevo, "si en modo parche el cerebro escribe el módulo entero, se usa (sin otra llamada)")

# una mejora NUEVA (sin «Código actual») sigue reescribiéndose como siempre
vistos = []


def api_nueva(clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None, codigo=False):
    vistos.append(system)
    return "NOMBRE: saluda\n```python\ndef registrar():\n    def f(t):\n        return 'hola ' + t\n    return {'saluda': f}\n```"


core._llamar_api = api_nueva
nombre, nuevo = core.generar_mejora("Crea una mejora que salude a la gente")
ok(nombre == "saluda" and all("CAMBIAR un módulo" not in s for s in vistos), "una mejora nueva NO entra en modo parche")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
