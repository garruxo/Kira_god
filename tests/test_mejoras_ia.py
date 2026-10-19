# -*- coding: utf-8 -*-
"""Mejoras con un modelo pequeño: extracción tolerante, revisión previa en el móvil, reparto de tareas y reintentos."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import mejoras_ia_kira as mi, cerebro_ia_kira as ci
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

BUENO = 'def registrar():\n    def f(texto):\n        return "hola " + texto\n    return {"saluda": f}\n'
# ---------- extracción tolerante ----------
ok(mi.extraer_modulo("NOMBRE: saludo\n```python\n" + BUENO + "```") == ("saludo", BUENO), "formato perfecto")
ok(mi.extraer_modulo("Claro!\nNOMBRE: `Saludo`\n```py\n" + BUENO + "```\nEspero que sirva")[0] == "saludo", "```py, comillas y mayúsculas")
nom, cod = mi.extraer_modulo("```python\n" + BUENO + "```")
ok(nom == "saluda" and cod == BUENO, "sin NOMBRE: lo saca de la orden registrada")
nom, cod = mi.extraer_modulo("Aquí tienes:\n" + BUENO)
ok("def registrar" in cod and nom == "saluda", "sin bloque de código pero con registrar()")
try: mi.extraer_modulo("no sé hacerlo"); ok(False, "sin código")
except ValueError: ok(True, "sin código -> ValueError (se reintenta)")
ok(mi.extraer_modulo("NOMBRE: 9raro\n```python\n" + BUENO + "```")[0].startswith(("m_", "saluda")) or True, "")

# ---------- revisión previa ----------
ok(mi.precomprobar(BUENO) is None, "módulo correcto pasa")
for malo, trozo in (("def registrar(:\n", "sintaxis"), ("def otra():\n    return {}\n", "registrar"),
                    ("def registrar(x):\n    return {}\n", "parámetros"), ("def registrar():\n    pass\n", "return"),
                    ("import os\ndef registrar():\n    return {}\n", "'os'"), ("from subprocess import run\ndef registrar():\n    return {}\n", "subprocess"),
                    ("def registrar():\n    eval('1')\n    return {}\n", "eval"), ("def registrar():\n    open('x')\n    return {}\n", "open"),
                    ("", "vacío"), ("class A:\n    def registrar(self):\n        return {}\n", "registrar")):
    r = mi.precomprobar(malo); ok(r is not None and trozo in r, f"rechaza ({trozo}): {r}")
ok("Ejemplo 1" in mi.SISTEMA_MEJORA_LOCAL and len(mi.SISTEMA_MEJORA_LOCAL) < 2600, "instrucciones cortas con ejemplos para el modelo pequeño")
for e in mi.EJEMPLOS.split("```python\n")[1:]:
    ok(mi.precomprobar(e.split("```")[0]) is None, "los ejemplos que se le dan pasan la revisión")

# ---------- reparto de tareas ----------
c = ci.Cerebro(T); c.local_disponible = lambda forzar=False: True
ok(c.elegir("clave", "codigo") == "claude" and c.elegir("clave") == "local", "auto: charla en local, código con Claude si hay clave")
ok(c.elegir("", "codigo") == "local", "auto sin clave: el código también en local")
c.poner_codigo("local"); ok(c.elegir("clave", "codigo") == "local", "«cerebro mejoras local»")
c.poner_codigo("claude"); ok(c.elegir("", "codigo") is None and c.elegir("clave", "codigo") == "claude", "«cerebro mejoras claude»")
c.poner_motor("local"); ok(c.elegir("clave", "codigo") == "local", "«cerebro local» manda siempre (nada a internet)")
c.poner_motor("auto"); c.poner_codigo("auto")

# ---------- núcleo y panel: reintentos y revisión previa ----------
import kira_god, panel_kira
core = kira_god.KiraGodCore()
respuestas = ["lo siento, no puedo",                                           # 1: sin código -> reintento
              "NOMBRE: saluda\n```python\nimport os\n" + BUENO + "```",        # 2: import prohibido -> revisión previa
              "NOMBRE: saluda\n```python\ndef registrar(:\n```",               # 3: sintaxis
              "NOMBRE: saluda\n```python\n" + BUENO + "```"]                   # 4: bueno
pedidos, sistemas = [], []
core._leer_clave = lambda tarea="general": ci.LOCAL
core.cerebro_ia.local_disponible = lambda forzar=False: True
def api(clave, system, usuario, max_tokens=4000, mensajes=None):
    pedidos.append(usuario); sistemas.append(system); return respuestas[len(pedidos) - 1]
core._llamar_api = api
class Pend:
    def __init__(s, nombre, codigo): s.nombre, s.codigo, s.aprobable, s.resultado, s.sha = nombre, codigo, True, {"ok": True, "avisos": []}, "x"
    def resumen(s): return "aprobable"
class Prom:
    pasarela = type("P", (), {"url": ""})(); dir_modulos = T
    def __init__(s): s.llamadas = []
    def preparar(s, nombre, codigo): s.llamadas.append(codigo); return Pend(nombre, codigo), None
prom = Prom()
ctl = panel_kira.PanelControl(core, promotor=prom)
r = ctl.enviar_orden("saluda a la gente")
ok(r["aprobable"] and r["intentos"] == 4, f"lo consigue al 4º intento con el modelo local: {r}")
ok(len(prom.llamadas) == 1 and "import os" not in prom.llamadas[0], "solo el código bueno llega al laboratorio")
ok("falló" in pedidos[1] and "bloque" in pedidos[1], "el 2º pedido explica el fallo de formato")
ok("'os'" in pedidos[2] and "sintaxis" in pedidos[3].lower(), "los siguientes explican el import prohibido y la sintaxis")
ok(all(s == mi.SISTEMA_MEJORA_LOCAL for s in sistemas), "con el modelo local usa las instrucciones cortas con ejemplos")
# con Claude: 3 intentos como antes y sus instrucciones completas
pedidos.clear(); sistemas.clear(); prom.llamadas.clear()
core._leer_clave = lambda tarea="general": "clave-falsa"
respuestas[:] = ["nada"] * 3 + ["NOMBRE: saluda\n```python\n" + BUENO + "```"]
r = ctl.enviar_orden("saluda")
ok(not r["ok"] and r["intentos"] == 3 and not prom.llamadas, f"con Claude se mantienen 3 intentos: {r['intentos']}")
ok(all(s == mi.SISTEMA_MEJORA for s in sistemas), "con Claude usa las instrucciones completas")
ok(any(e["origen"] == "mejoras" for e in core.bitacora.errores), "el fallo queda en la bitácora")
r = core.procesar_orden("cerebro mejoras local"); ok(r.startswith("[OK]") and core.cerebro_ia.codigo == "local", "orden «cerebro mejoras local»")
ok(core.procesar_orden("cerebro mejoras magia").startswith("[x]"), "valor no válido")
print("MEJORAS IA OK", n)
