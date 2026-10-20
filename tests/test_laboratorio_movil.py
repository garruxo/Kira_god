# -*- coding: utf-8 -*-
"""Laboratorio de bolsillo (v2.17): Kira prueba sus mejoras dentro del móvil, sin ordenador; si el ordenador está
conectado, también allí. Mismo veredicto que el laboratorio del PC, así que «Aplicar» (dos toques) no cambia."""
import os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import laboratorio_movil_kira as lm
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

L = lm.LaboratorioMovil()
BUENO = 'def registrar():\n    def f(texto):\n        return "hola " + texto\n    return {"saluda": f}\n'
r = L.probar("saluda", BUENO)
ok(r["ok"] and r["sha256"] == lm.sha256(BUENO) and r["donde"] == "móvil", "un módulo correcto pasa (con el sha de ESTE código)")
ok([e["nombre"] for e in r["etapas"]] == ["sintaxis", "revision_patrones", "seguridad_movil", "carga_aislada", "contrato",
                                           "prueba_de_uso"], "las etapas de siempre y la prueba de uso")

def falla(codigo, etapa, trozo=""):
    r = L.probar("m", codigo)
    mal = next((e for e in r["etapas"] if not e["ok"]), None)
    return not r["ok"] and mal is not None and mal["nombre"] == etapa and trozo in mal["detalle"]

ok(falla("def registrar(:\n", "sintaxis"), "sintaxis")
ok(falla("import os\n" + BUENO, "seguridad_movil", "'os'"), "nada de os")
ok(falla("import platform\n" + BUENO, "seguridad_movil", "platform"), "solo módulos de la lista segura")
ok(falla('def registrar():\n    def f(t):\n        return getattr(f, "__glo" "bals__")\n    return {"x": f}\n',
         "seguridad_movil", "__globals__"), "ni trucos con textos internos")
ok(falla('import time\ndef registrar():\n    def f(t):\n        time.sleep(9)\n        return ""\n    return {"x": f}\n',
         "seguridad_movil", "avisar_en"), "sin sleep (bloquearía a Kira): le dice qué usar")
ok(falla("from time import sleep\n" + BUENO, "seguridad_movil", "sleep"), "ni importando sleep")
t0 = time.time()
ok(falla("while True:\n    pass\n" + BUENO, "carga_aislada", "bucle"), "un bucle infinito al cargar se corta")
ok(time.time() - t0 < lm.TOPE_CARGA + 2, "y no se queda esperando")
ok(falla('def registrar():\n    raise RuntimeError("roto")\n    return {}\n', "carga_aislada", "roto"), "error al cargar")
ok(falla('def registrar():\n    return {"Saluda": lambda t: t}\n', "contrato", "Saluda"), "prefijos en minúsculas")
ok(falla('def registrar():\n    return {"x": lambda a, b, c: a}\n', "contrato", "(texto)"), "la orden recibe (texto) o (texto, kira)")
ok(falla('def registrar():\n    def f(t):\n        while True:\n            pass\n    return {"x": f}\n', "prueba_de_uso", "colgada"),
   "una orden que se cuelga no pasa")
ok(falla('def registrar():\n    def f(t, kira):\n        return kira.volar(t)\n    return {"vuela": f}\n', "prueba_de_uso", "kira.volar"),
   "usar una función de 'kira' que no existe no pasa")
r = L.probar("m", 'def registrar():\n    def f(t):\n        return t.split()[5]\n    return {"quinta": f}\n')
ok(r["ok"] and any("IndexError" in a for a in r["avisos"]), "un error raro con una frase de ejemplo queda como AVISO")
r = L.probar("m", 'def registrar():\n    def f(t, kira):\n        kira.guardar_dato("a", t)\n        kira.avisar_en(60, "hola")\n'
                  '        return "ok " + str(kira.leer_dato("a"))\n    return {"anota": f}\n')
ok(r["ok"] and not r["avisos"], "las funciones de 'kira' funcionan en la prueba (sin tocar nada real)")
r = L.probar("m", 'def registrar():\n    def f(t):\n        if not t:\n            raise ValueError("dime algo")\n        return t\n'
                  '    return {"eco": f}\n')
ok(r["ok"] and not r["avisos"], "ValueError con frases que no entiende es lo esperado")

# el kira de prueba tiene EXACTAMENTE las funciones del de verdad
import api_modulos_kira as am
real = {x for x in dir(am.ApiModulo) if not x.startswith("_")} | set(am.PERMITIDAS)
ok(real == {x for x in dir(lm.KiraDePrueba) if not x.startswith("_")}, "kira de prueba = kira de verdad")

# juegos
JUEGO = '''def registrar():
    def crear(motor):
        class J(motor.Juego):
            def preparar(self):
                self.b = self.circulo(100, 100, 10, "rojo")
            def actualizar(self, dt):
                self.b.x += 60 * dt
                if self.b.x > 360:
                    self.b.x = 0
        return J
    return {"juego bolita": crear}
'''
r = L.probar("bolita", JUEGO)
ok(r["ok"] and any(e["nombre"] == "juegos" and e["ok"] for e in r["etapas"]), "un juego se juega 20 s simulados")
ok(falla(JUEGO.replace("self.b.x += 60 * dt", "self.b.x += 1 / 0"), "juegos", "ZeroDivisionError"), "un juego que falla no pasa")
ok(falla(JUEGO.replace("return J", "return 5"), "juegos", "clase"), "crear() debe devolver la clase del juego")

# todas las recetas probadas (módulos de gráficos, juegos e ingeniería) pasan también en el móvil
import recetas_graficos_kira as rg, recetas_ingenieria_kira as ri
mods = [x for x in rg.RECETAS + ri.RECETAS if "def registrar" in x["codigo"]]
malos = [x["id"] for x in mods if not L.probar(x["id"].replace(" ", "_")[:30], x["codigo"])["ok"]]
ok(len(mods) > 50 and not malos, f"las {len(mods)} recetas pasan el laboratorio del móvil: {malos}")

# ---------- doble: móvil siempre, ordenador si responde ----------
class PC:
    def __init__(s, url="http://pc:8765", token="t" * 20, resp=None):
        s.url, s.token, s.nombre, s.llamadas, s.resp = url, token, "PC", [], resp
    def probar(s, nombre, codigo):
        s.llamadas.append(nombre)
        return s.resp if s.resp is not None else {"ok": True, "sha256": lm.sha256(codigo), "etapas": [{"nombre": "tests", "ok": True}], "avisos": ["importa 'x'"]}
d = lm.LaboratorioDoble(None)
ok(d.probar("s", BUENO)["ok"] and d.url == "" and d.token == "", "sin ordenador: solo el móvil (y basta)")
pc = PC(); d = lm.LaboratorioDoble(pc, salud=lambda: True)
r = d.probar("s", BUENO)
ok(r["ok"] and pc.llamadas == ["s"] and r["donde"] == "móvil y ordenador", "con el ordenador conectado: prueba en los dos")
ok(any(e["nombre"] == "ordenador: tests" for e in r["etapas"]) and "importa 'x'" in r["avisos"], "junta etapas y avisos")
ok(d.url == "http://pc:8765" and d.nombre == "PC", "se puede consultar la pasarela a través del doble")
pc = PC(); d = lm.LaboratorioDoble(pc, salud=lambda: False)
r = d.probar("s", BUENO)
ok(r["ok"] and not pc.llamadas and "no responde" in r["etapas"][-1]["detalle"], "ordenador apagado: no espera, vale el móvil")
pc = PC(resp={"ok": False, "sha256": "", "etapas": [{"nombre": "tests_fijos", "ok": False, "detalle": "x"}], "avisos": []})
_r = lm.LaboratorioDoble(pc, salud=lambda: True).probar("s", BUENO)
ok(not _r["ok"], "si el ordenador lo rechaza, no pasa")
ok(_r.get("rechazo") == "ordenador" and any("ORDENADOR no la aprueba" in str(e.get("detalle")) and "desconéctate" in
   str(e.get("detalle")) for e in _r["etapas"]), "y dice claro que fue el ordenador y cómo arreglarlo")
pc = PC(resp={"ok": False, "error": "Laboratorio no alcanzable"})
ok(lm.LaboratorioDoble(pc, salud=lambda: True).probar("s", BUENO)["ok"], "si el ordenador se cae a mitad, vale el móvil")
pc = PC(); d = lm.LaboratorioDoble(pc, salud=lambda: True)
ok(not d.probar("s", "import os\n" + BUENO)["ok"] and not pc.llamadas, "lo que no pasa en el móvil ni se envía al ordenador")

# el Promotor de siempre funciona con el laboratorio del móvil (mismo veredicto → «Aplicar» igual que antes)
import pasarela_cliente as pcl
prom = pcl.Promotor(lm.LaboratorioDoble(None))
pend, err = prom.preparar("saluda", BUENO)
ok(err is None and pend.aprobable, "el Promotor acepta el veredicto del móvil")
ok(not prom.aplicar(pend, "APLICAR mal")[0], "aplicar sigue exigiendo tu confirmación")
ok(prom.aplicar(pend, pend.frase_confirmacion())[0] and os.path.isfile(os.path.join(prom.dir_modulos, "saluda.py")),
   "con tu confirmación se instala")
print("LABORATORIO MÓVIL OK", n)
