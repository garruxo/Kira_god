# -*- coding: utf-8 -*-
"""v3.20: «implementa la receta X» y «usa la solución X en Kira» (foto del dueño: las dos daban «No reconozco la
orden»). Se prueban en el laboratorio de verdad y quedan esperando los dos toques; nunca se instalan solas."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["KIRA_DATA_DIR"] = T
os.environ["HOME"] = T
sys.path.insert(0, RAIZ)
import implementar_kira as ik

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


O = ik.orden
ok(O("implementa receta fuerza de contraseña") == ("receta", "fuerza de contrasena"), "lo de la foto: «implementa receta …»")
ok(O("usa la solucin fuerza de contrasena en kira") == ("solucion", "fuerza de contrasena"),
   "lo de la foto: «usa la solucin … en kira» (sin tildes y con la falta)")
ok(O("Kira, instala la receta de dijkstra") == ("receta", "dijkstra") and O("pon la receta del cifrado césar")[0] == "receta",
   "otras formas de decirlo")
ok(O("usa la solución cifrado en Kira") == ("solucion", "cifrado"), "solución con tilde")
for t in ("implementa este código", "implementa las mejoras", "usa la receta", "dime una receta de cocina"):
    ok(O(t) is None, f"«{t}» NO es esto")
S = {"fuerza de contraseña": {"codigo": "x"}, "cifrado césar": {}}
ok(ik.buscar_solucion(S, "fuerza de contrasena")[0] == "fuerza de contraseña", "encuentra la solución sin tildes")
ok(ik.buscar_solucion(S, "cesar")[0] == "cifrado césar" and ik.buscar_solucion(S, "volcanes")[0] is None, "por parecido; si no, nada")

# ---------- con el núcleo y el laboratorio de verdad ----------
import kira_god
import pensador_kira as pn
core = kira_god.KiraGodCore()
core.es_kiraos = True
r = core.procesar_orden("implementa receta fuerza de contraseña")
ok("ha pasado mi laboratorio" in r and "NO la he instalado" in r and "Cuaderno ▸ Mejoras" in r, "la receta pasa el laboratorio y ESPERA tus dos toques: " + r[:120])
pend = core._panel.pendiente
ok(pend is not None and pend.nombre == "fuerza_contrasena" and pend.aprobable, "queda pendiente con su nombre")
ok(not os.path.exists(os.path.join(core.dir, "modulos", "fuerza_contrasena.py")), "y NO se ha instalado sola")
r = core.procesar_orden("implementa la receta de volcanes submarinos")
ok("No tengo una receta" in r and "parecidas" in r, "una receta que no existe: lo dice con las parecidas")

ruta = core._ruta_pensar()
est = pn.cargar(ruta)
mod = ('def registrar():\n    def saludo(texto):\n        return "hola desde la solucion"\n'
       '    return {"saludo de solucion": saludo}\n')
est.setdefault("soluciones", {})["saludo amable"] = {"tema": "saludo amable", "respuesta": "r", "codigo": mod}
est["soluciones"]["fuerza de contraseña"] = {"tema": "fuerza de contraseña", "respuesta": "solo texto", "codigo": ""}
pn.guardar(est, ruta)
r = core.procesar_orden("usa la solución saludo amable en Kira")
ok("solución «saludo amable»" in r and "ha pasado mi laboratorio" in r, "una solución con código: al laboratorio y esperando")
ok(core._panel.pendiente.nombre.startswith("saludo"), "…pendiente con su nombre")
r = core.procesar_orden("usa la solucin fuerza de contrasena en kira")
ok("receta probada" in r and "ha pasado mi laboratorio" in r, "la solución sin código pero con receta: usa la receta (lo de la foto)")
r = core.procesar_orden("usa la solución de los volcanes en kira")
ok("No encuentro la solución" in r and "saludo amable" in r, "una solución que no está: dice cuáles hay")
core.es_kiraos = False
ok("el panel" in core._donde_instalar(), "en el móvil dice dónde instalar allí")
ok("usa la solución x en Kira" in core.usar_solucion("x", "kira") or "No encuentro" in core.usar_solucion("x", "kira"),
   "el botón «En Kira» ya explica la orden que funciona")
est = pn.cargar(ruta)
ok("usa la solución saludo amable en Kira" in core.usar_solucion("saludo amable", "kira"), "…con el nombre de la solución")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
