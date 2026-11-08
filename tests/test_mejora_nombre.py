# -*- coding: utf-8 -*-
"""v3.13: visto en el Packard Bell: tras instalar la mejora «disco_fisico», «disco_fisico» daba «No reconozco la
orden». Ahora: el guion bajo vale como espacio en las órdenes de las mejoras, decir el NOMBRE de una mejora la usa (si
tiene una sola orden) o dice sus órdenes, y si no cargó lo dice con el motivo. Y en KiraOS ya no quedan «· En cola…»
ni «· Pensando…» debajo de la respuesta."""
import os
import sys
import tempfile
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp()
os.environ["KIRA_DATA_DIR"] = T
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
os.environ["KIRA_DATOS_NUCLEO"] = T
import kira_god

fallos = 0
n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


K = kira_god.KiraGodCore
os.makedirs(os.path.join(T, "modulos"))
open(os.path.join(T, "modulos", "disco_fisico.py"), "w").write(
    'def registrar():\n    return {"disco fisico": lambda t: "Disco: 224 GB, libres 180 GB"}\n')
open(os.path.join(T, "modulos", "dos_cosas.py"), "w").write(
    'def registrar():\n    return {"suma rapida": lambda t: "s", "resta rapida": lambda t: "r"}\n')
open(os.path.join(T, "modulos", "rota.py"), "w").write('def registrar(:\n')
c = types.SimpleNamespace(dir=T)
for m in ("cargar_modulos", "modulo_para", "es_orden_de_modulo", "_comando_modulo", "_ejecutar_modulo",
          "_por_nombre_de_mejora", "registrar_error"):
    setattr(c, m, types.MethodType(getattr(K, m), c))
c._plano = K._plano
c._acepta_kira = K._acepta_kira
c.RESERVADAS = K.RESERVADAS
c.registrar_error = lambda *a, **k: None
c.cargar_modulos()
ok("disco fisico" in c.comandos_modulos and "rota" in c.errores_modulos, "se cargan las mejoras (y la rota se apunta)")
ok(c.modulo_para("disco_fisico") == ("disco fisico", ""), "«disco_fisico» = «disco fisico» (guion bajo = espacio)")
ok(c._comando_modulo("", "Kira, disco_fisico") == "Disco: 224 GB, libres 180 GB", "y la orden funciona")
ok(c._por_nombre_de_mejora("usa disco físico") == "Disco: 224 GB, libres 180 GB", "por su NOMBRE: la usa")
r = c._por_nombre_de_mejora("dos_cosas")
ok("«resta rapida …»" in r and "«suma rapida …»" in r, "si tiene varias órdenes, las dice")
r = c._por_nombre_de_mejora("rota")
ok(r.startswith("[x] La mejora «rota» está instalada pero NO ha podido cargar") and "Volver atrás" in r,
   "si no cargó, lo dice con el motivo y cómo deshacerla")
ok(c._por_nombre_de_mejora("hola que tal") is None, "lo demás no")
src = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
i = src.index("def procesar_orden")
ok(src.index("_por_nombre_de_mejora(command)", i) < src.index("return f\"{self.NO_RECONOCIDA}", i),
   "se mira ANTES de decir «No reconozco la orden»")

import escritorio_kira as ek
for x in ("· En cola: lo haré en cuanto acabe lo de antes.", "· Pensando...", "Pensando…", "- En cola"):
    ok(ek._TRANSITORIA.match(x), f"«{x}» se quita al contestar")
ok(not ek._TRANSITORIA.match("· prueba: OK"), "lo demás se queda")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
