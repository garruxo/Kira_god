# -*- coding: utf-8 -*-
"""Oído propio (Vosk): resultados, descarga y descompresión segura del modelo, y nombre por cómo suena."""
import io, os, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import oido_kira as ok_mod, escucha_kira as ek
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

ok(ok_mod.texto_de_resultado('{"text": "kira qué hora es"}') == "kira qué hora es", "lee el resultado de Vosk")
ok(ok_mod.texto_de_resultado('{"text": ""}') == "" and ok_mod.texto_de_resultado("basura") == "", "resultados vacíos o raros")

def zip_modelo(nombre=ok_mod.MODELO["nombre"], malo=False):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(f"{nombre}/am/final.mdl", b"x" * 100)
        z.writestr(f"{nombre}/conf/model.conf", b"--sample-frequency=16000")
        if malo:
            z.writestr("../../fuera.txt", b"peligro")
    return b.getvalue()
class Resp(io.BytesIO):
    status = 200
    def __init__(s, d): super().__init__(d); s.headers = {"Content-Length": str(len(d))}
    def __enter__(s): return s
    def __exit__(s, *a): return False
T = tempfile.mkdtemp()
O = ok_mod.Oido(T, abrir=lambda req, timeout=60: Resp(zip_modelo()))
ok(not O.modelo_instalado() and not O.disponible(), "sin modelo")
prog = []
O.descargar_modelo(progreso=lambda f, b, t: prog.append(f))
ok(O.modelo_instalado() and prog and prog[-1] == 1.0, "descarga y descomprime con progreso")
ok(not os.path.exists(os.path.join(T, "voz", ok_mod.MODELO["nombre"] + ".zip")), "borra el zip después")
ok(not O.libreria_disponible() and not O.disponible(), "en el PC no hay librería de Android: no se usa")
ok(O.encender(lambda t: None)[0] is False, "encender sin librería: no se rompe")
O.pausar(True); O.apagar(); ok(O.estado == "apagado", "pausar y apagar sin servicio no fallan")

T2 = tempfile.mkdtemp()
O2 = ok_mod.Oido(T2, abrir=lambda req, timeout=60: Resp(zip_modelo(malo=True)))
try:
    O2.descargar_modelo(); ok(False, "zip con rutas peligrosas")
except ok_mod.OidoError:
    ok(True, "rechaza un zip que intenta salirse de su carpeta")
ok(not os.path.exists(os.path.join(T2, "fuera.txt")) and not os.path.exists(os.path.join(os.path.dirname(T2), "fuera.txt")), "no escribió fuera")
O3 = ok_mod.Oido(tempfile.mkdtemp(), abrir=lambda req, timeout=60: Resp(zip_modelo(nombre="otra_cosa")))
O3.descargar_modelo(); ok(O3.modelo_instalado(), "acepta el modelo aunque la carpeta interior tenga otro nombre")
def caido(req, timeout=60): raise OSError("sin red")
try:
    ok_mod.Oido(tempfile.mkdtemp(), abrir=caido).descargar_modelo(); ok(False, "sin red")
except ok_mod.OidoError as e:
    ok("No se pudo descargar" in str(e), "sin red: mensaje claro")

# el nombre por cómo suena (el reconocedor sin conexión puede no conocer «Kira»)
for f, si in (("quiera qué hora es", True), ("kiara pon música", True), ("quira", True), ("Kira hola", True),
              ("quiero que vengas", False), ("mira esto", False), ("oye quiera", False), ("cirro", False), ("que hora es", False)):
    ok(ek.contiene_nombre(f)[0] == si, f"«{f}» -> {si}")
ok(ek.contiene_nombre("quiera qué hora es")[1] == "qué hora es", "la orden es lo que sigue")
print("OIDO OK", n)
