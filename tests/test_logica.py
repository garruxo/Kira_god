import sys, os, tempfile, math, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import inicio_kira as ik, menu_kira as mk
n = 0
def ok(c, m):
    global n; n += 1
    assert c, "FALLA: " + m
# orbe
o = ik.OrbeModelo(semilla=1)
for est in ik.ESTADOS:
    o.poner_estado(est)
    for _ in range(200): o.paso(1/30)
    f = o.fotograma()
    ok(0.5 < f["nucleo"] < 0.9, f"nucleo {est} {f['nucleo']}")
    ok(all(0 <= a <= 1 for _, a in f["anillos"]), "alfa anillos "+est)
    ok(all(0 <= p[3] <= 1 for p in f["particulas"]), "alfa part")
    ok(all(abs(c - t) < 0.05 for c, t in zip(f["color"], ik.COLORES[est])), "color converge "+est)
o.poner_estado("inventado"); ok(o.estado == "hablando", "estado invalido ignorado")
o.paso(99); ok(o.t < 7000, "dt acotado")
ok(ik.dentro_del_orbe(100, 100, 100, 100, 50) and not ik.dentro_del_orbe(300, 100, 100, 100, 50), "toque circular")
ok(len(ik.OrbeModelo(particulas=0).particulas()) == 0, "0 particulas")
# máquina
m = ik.Maquina("hola mundo", cps=10)
ok(m.visible() == "" and not m.terminada, "maquina inicio")
m.paso(0.5); ok(m.visible() == "hola " , "maquina medio "+repr(m.visible()))
m.paso(5); ok(m.terminada and m.visible() == "hola mundo", "maquina fin")
# saludo
ok("Buenos días" in ik.saludo(8, True) and "Buenas tardes" in ik.saludo(15, True) and "Buenas noches" in ik.saludo(2, True), "saludos")
ok("clave" in ik.saludo(10, False) and "no puedo hablar" in ik.saludo(10, True, False), "saludo honesto")
# conversación
ordenes = []
def orden(t):
    ordenes.append(t)
    return "[OK] hecho" if t == "estado" else "[i] No reconozco la orden 'x'. Usa..."
def charla(t, h):
    if t == "falla": raise RuntimeError("Falta la clave de la API.")
    if t == "boom": raise ValueError("red")
    return "Hola, soy Kira"
c = ik.Conversacion(os.path.join(T, "c.json"), orden, charla)
ok(c.preguntar("estado") == ("[OK] hecho", "orden"), "orden")
ok(c.preguntar("hola\x00 qué tal") == ("Hola, soy Kira", "charla"), "charla")
ok(c.preguntar("falla")[1] == "error" and c.preguntar("boom")[1] == "error", "errores")
ok(c.preguntar("   ")[1] == "error", "vacio")
ok(len(c.preguntar("x"*5000)[0]) > 0 and all(len(h["texto"]) <= 1200 for h in c.historial), "acotado")
c2 = ik.Conversacion(os.path.join(T, "c.json"), orden, charla)
ok(len(c2.historial) == len(c.historial) > 5, "persistencia")
c2.borrar(); ok(ik.Conversacion(os.path.join(T, "c.json"), orden, charla).historial == [], "borrar")
open(os.path.join(T, "mal.json"), "w").write("{no json")
ok(ik.Conversacion(os.path.join(T, "mal.json"), orden, charla).historial == [], "json corrupto")
def orden_rota(t): raise OSError("x")
ok(ik.Conversacion(os.path.join(T, "d.json"), orden_rota, charla).preguntar("a")[1] == "error", "orden rota")
# voz
class FakeSTT:
    listening = True; results = []; errors = []; language = ""
    def start(self): pass
    def stop(self): pass
class FakeTTS:
    dicho = []
    def speak(self, t): FakeTTS.dicho.append(t)
class P: tts = FakeTTS(); stt = FakeSTT()
v = ik.Voz(P())
ok(v.puede_hablar() and v.puede_escuchar(), "voz disponible")
ok(v.hablar("hola") is True, "habla"); import time; time.sleep(0.2); ok(FakeTTS.dicho == ["hola"], "tts recibido")
ok(v.iniciar_escucha()[0] and v.sondear()[0] == "escuchando", "escucha")
FakeSTT.listening = False; FakeSTT.results = ["  hola\x01 kira "]; ok(v.sondear() == ("listo", "hola kira"), "resultado")
FakeSTT.results = []; FakeSTT.errors = ["no audio"]; ok(v.sondear() == ("error", "no audio"), "error stt")
class Nada: pass
v2 = ik.Voz(Nada()); ok(not v2.puede_hablar() and not v2.iniciar_escucha()[0] and v2.hablar("x") is False, "sin voz es honesto")
vi = ik.Voz(); vi._plyer = None
import builtins; real = builtins.__import__
def imp(name, *a, **k):
    if name == "plyer": raise ImportError("no")
    return real(name, *a, **k)
builtins.__import__ = imp; ok(not ik.Voz().puede_hablar(), "sin plyer"); builtins.__import__ = real
# menú
ids = [a["id"] for a in mk.APARTADOS]; ok(len(ids) == len(set(ids)) == 24, "apartados únicos")
ok(all(a["destino"][0] in ("panel", "pantalla") for a in mk.APARTADOS), "destinos")
f = {"notas": ["Comprar PILAS", "idea: módulo de hora"], "módulos": ["hora (hora, reloj)"]}
ok(mk.buscar_local("pilas", f) == [("notas", "Comprar PILAS")], "busca")
ok(mk.buscar_local("MODULO hora", f) == [("notas", "idea: módulo de hora")], "sin tildes y todas las palabras")
ok(mk.buscar_local("(.*", f) == [] and mk.buscar_local("   ", f) == [], "regex literal/vacío")
ok(len(mk.buscar_local("a", {"x": ["a"] * 100}, maximo=5)) == 5, "máximo")
nt = mk.Notas(os.path.join(T, "n.json"))
ok(nt.anadir("  hola ")[0] and not nt.anadir("  ")[0], "notas añadir")
nt.anadir("dos"); ok(nt.textos() == ["dos", "hola"], "orden reciente primero")
idb = nt.listar()[0]["id"]; ok(nt.borrar(idb) and not nt.borrar(idb), "borrar nota")
ok(mk.Notas(os.path.join(T, "n.json")).textos() == ["hola"], "notas persisten")
nt.anadir("z"*900); ok(len(nt.textos()[0]) == 500, "recorta nota")
for i in range(300): nt.anadir(f"n{i}")
ok(len(nt.items) == 200, "máx notas")
a = mk.AjustesInterfaz(os.path.join(T, "a.json")); ok(a.voz_hablar and a.velocidad == 45, "defecto")
a.alternar_voz(); a.cambiar_velocidad(1000); b = mk.AjustesInterfaz(os.path.join(T, "a.json"))
ok(b.voz_hablar is False and b.velocidad == 120, "ajustes persisten y acotan")
json.dump({"velocidad": "rapido", "voz_hablar": 5}, open(os.path.join(T, "a2.json"), "w"))
ok(mk.AjustesInterfaz(os.path.join(T, "a2.json")).velocidad == 45, "ajuste corrupto")
class Ctl:
    def estado(self): return {"clave": False, "lab": "sin configurar", "modulos": 2, "pendiente": False}
l = mk.estado_sistema(Ctl(), T); ok(any("FALTA" in x for x in l) and any("Espacio" in x for x in l), "estado real")
# núcleo: armar_mensajes
import kira_god
K = kira_god.KiraGodCore
m1 = K.armar_mensajes([("kira", "a"), ("tu", "b"), ("tu", "c"), ("kira", "d")], "e")
ok([x["role"] for x in m1] == ["user", "assistant", "user"] and m1[0]["content"] == "b\nc", "alterna "+str(m1))
ok(K.armar_mensajes([], "hola") == [{"role": "user", "content": "hola"}], "sin historial")
m2 = K.armar_mensajes([("tu", "x")], "y"); ok(len(m2) == 1 and m2[0]["content"] == "x\ny", "user final fusiona")
k = K()
try: k.conversar("hola"); ok(False, "debía pedir clave")
except RuntimeError as e: ok("clave" in str(e), "pide clave")
print("OK", n, "comprobaciones")
# secretos fuera del historial
cc = ik.Conversacion(os.path.join(T, "s.json"), lambda t: "[OK] clave guardada sk-ant-abcdefgh12345", charla)
cc.preguntar("config clave: sk-ant-api03-SECRETO123456")
cc.preguntar("mi clave es sk-ant-api03-OTRASECRETA99 ok")
raw = open(os.path.join(T, "s.json")).read()
ok("SECRETO" not in raw and "OTRASECRETA" not in raw and "abcdefgh12345" not in raw, "secretos no se guardan: " + raw)
ok(ik.ocultar_secretos("config pasarela http://x tokenabc") == "config pasarela: (oculto)", "config pasarela oculta")
print("OK final", n)
