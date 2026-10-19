# -*- coding: utf-8 -*-
"""Mejoras más potentes: datos propios, recuerdos, avisos y juegos que añaden los módulos (con sus límites)."""
import os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import api_modulos_kira as am, recuerdos_kira as rk
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- datos propios ----------
A = am.ApiModulo("contador", dir_datos=T)
B = am.ApiModulo("otro", dir_datos=T)
ok(A.leer_dato("x", 7) == 7, "defecto")
A.guardar_dato("x", {"lista": [1, 2], "texto": "ñ"})
ok(A.leer_dato("x") == {"lista": [1, 2], "texto": "ñ"}, "guarda y lee JSON")
ok(B.leer_dato("x") is None, "cada módulo tiene sus propios datos")
ok(am.ApiModulo("contador", dir_datos=T).datos() == {"x": {"lista": [1, 2], "texto": "ñ"}}, "persiste")
for malo, clave in ((object(), "y"), (1, "../fuera"), (1, "")):
    try:
        A.guardar_dato(clave, malo); ok(False, f"rechaza {clave!r}")
    except am.ApiError:
        ok(True, f"rechaza dato/clave no válidos: {clave!r}")
try:
    A.guardar_dato("grande", "x" * (am.MAX_DATOS + 10)); ok(False, "límite")
except am.ApiError:
    ok(True, "límite de 256 KB")
ok(A.borrar_dato("x") and not A.borrar_dato("x") and A.datos() == {}, "borrar dato")
ok(not os.path.exists(os.path.join(T, "fuera.json")), "no escribe fuera de su carpeta")

# ---------- herramientas permitidas y nada más ----------
class H:
    def leer(self, n): return "leído " + n
    def secreto(self): return "no"
ah = am.ApiModulo("m", herramientas=H(), dir_datos=T)
ok(ah.leer("a.txt") == "leído a.txt", "pasa las herramientas de siempre")
try:
    ah.secreto(); ok(False, "oculta lo demás")
except AttributeError:
    ok(True, "no da acceso a otras cosas")

# ---------- recuerdos ----------
R = rk.Recuerdos(os.path.join(T, "baul"))
ar = am.ApiModulo("notas", dir_datos=T, recuerdos=R)
ar.recordar("La reunión del club es el jueves a las 7.")
ok(R.buscar("reunión club")[0]["fuente"] == "módulo notas", "recuerda marcando el módulo")
ok("jueves" in ar.buscar_recuerdos("cuándo es la reunión del club")[0], "busca en el baúl")

# ---------- avisos ----------
reloj = [1000.0]
AV = am.Avisos(reloj=lambda: reloj[0])
aa = am.ApiModulo("cocina", dir_datos=T, avisos=AV)
aa.avisar_en(60, "Saca la pizza")
aa.decir("Ya estoy")
ok(AV.vencidos() == [("cocina", "Ya estoy")], "decir() sale enseguida")
ok(AV.vencidos() == [], "no se repite")
reloj[0] += 61
ok(AV.vencidos() == [("cocina", "Saca la pizza")], "el aviso llega a su hora")
for malo in ((-1, "x"), (8 * 24 * 3600, "x"), ("pronto", "x"), (5, "")):
    try:
        aa.avisar_en(*malo); ok(False, f"rechaza {malo}")
    except am.ApiError:
        ok(True, f"rechaza aviso no válido {malo}")
for i in range(am.MAX_AVISOS_MODULO):
    aa.avisar_en(100, f"a{i}")
try:
    aa.avisar_en(100, "uno más"); ok(False, "límite de avisos")
except am.ApiError:
    ok(True, "máximo de avisos por módulo")
ok(am.ApiModulo.ahora()[:2] == "20", "ahora()")

# ---------- en el núcleo: módulo con comando, datos, avisos y juego ----------
os.makedirs(os.path.join(T, "modulos"))
with open(os.path.join(T, "modulos", "naves.py"), "w", encoding="utf-8") as f:
    f.write('''def registrar():
    def crear(motor):
        class Naves(motor.Juego):
            titulo = "Naves"
            def preparar(self):
                self.nave = self.rect(165, 40, 30, 20, "azul")
            def actualizar(self, dt):
                self.puntos += 1
        return Naves
    def hola(texto, kira):
        kira.guardar_dato("veces", (kira.leer_dato("veces", 0) or 0) + 1)
        kira.avisar_en(0, "aviso desde naves")
        return "hola %d" % kira.leer_dato("veces")
    return {"juego naves": crear, "hola naves": hola}
''')
with open(os.path.join(T, "modulos", "roto.py"), "w", encoding="utf-8") as f:
    f.write('def registrar():\n    return {"juego roto": lambda motor: 42}\n')
import kira_god
core = kira_god.KiraGodCore()
ok("naves" in core.juegos_modulos and core.juegos_modulos["naves"].titulo == "Naves", "el juego del módulo se registra")
ok("hola naves" in core.comandos_modulos and "juego naves" not in core.comandos_modulos, "el juego no es un comando")
ok("roto" in core.errores_modulos, "un juego mal hecho se rechaza con su error")
ok(core.procesar_orden("hola naves") == "hola 1" and core.procesar_orden("hola naves") == "hola 2", "el módulo guarda sus datos")
ok(("naves", "aviso desde naves") in core.avisos.vencidos(), "el módulo programa avisos")
ok(os.path.isfile(os.path.join(T, "datos_modulos", "naves.json")), "datos en su carpeta")
g = core.juegos_modulos["naves"](); g.paso(0.02); ok(g.puntos == 1, "el juego del módulo funciona")
ok("Juegos: naves" in core.procesar_orden("recargar modulos"), "recargar lo enseña")
core.avisos.programar("x", 300, "luego")
ok("luego" in core.procesar_orden("avisos"), "orden avisos")

# ---------- la IA sabe usarlo ----------
import mejoras_ia_kira as mi
ok("guardar_dato" in mi.SISTEMA_MEJORA and "avisar_en" in mi.SISTEMA_MEJORA_LOCAL and "motor.Juego" in mi.SISTEMA_MEJORA,
   "las instrucciones a la IA explican lo nuevo")
nombre, codigo = mi.extraer_modulo(mi.EJEMPLOS.split("Ejemplo 3")[1])
ok(nombre == "recordatorio" and mi.precomprobar(codigo) is None, "el ejemplo 3 pasa la revisión previa")
print("API MODULOS OK", n)
