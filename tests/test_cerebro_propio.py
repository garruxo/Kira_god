# -*- coding: utf-8 -*-
"""Cerebro propio: descarga del modelo (progreso, espacio, reanudación), elección del motor y arranque/parada."""
import io, os, sys, tempfile, threading, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cerebro_propio_kira as cp
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

T = tempfile.mkdtemp()
cp.MODELOS["prueba"] = {"nombre": "Modelo de prueba", "archivo": "prueba.gguf", "bytes": 5 * 1024 * 1024 + 123,
                        "url": "https://huggingface.co/x/resolve/main/prueba.gguf", "ram_gb": 1}
DATOS = os.urandom(cp.MODELOS["prueba"]["bytes"])

class Resp(io.BytesIO):
    def __init__(s, datos, status=200): super().__init__(datos); s.status = status
    def __enter__(s): return s
    def __exit__(s, *a): return False
pedidos = []
def abrir(req, timeout=30, corta=None):
    pedidos.append(dict(req.headers))
    rng = req.headers.get("Range")
    if rng:
        ini = int(rng.split("=")[1].rstrip("-"))
        return Resp(DATOS[ini:], 206)
    return Resp(DATOS[:corta] if corta else DATOS)

C = cp.CerebroPropio(T, carpeta_binarios=os.path.join(T, "bin"), abrir=abrir)
ok(C.modelo == "ligero" and C.auto, "por defecto: el modelo ligero, encendido automático")
C.elegir("prueba"); ok(cp.CerebroPropio(T).modelo == "prueba", "recuerda el modelo elegido")
try:
    C.elegir("enorme"); ok(False, "modelo desconocido")
except cp.CerebroPropioError:
    ok(True, "modelo desconocido")
ok(not C.modelo_instalado() and "sin descargar" in C.estado_texto(), "sin descargar")

# descarga cortada a medias y reanudada
C._abrir = lambda req, timeout=30: abrir(req, timeout, corta=2 * 1024 * 1024)
try:
    C.descargar(); ok(False, "descarga incompleta")
except cp.CerebroPropioError as e:
    ok("no está completa" in str(e), "detecta la descarga incompleta")
ok(os.path.getsize(C.ruta_modelo() + ".parte") == 2 * 1024 * 1024, "guarda lo bajado")
C._abrir = abrir
progresos = []
C.descargar(progreso=lambda f, b, t: progresos.append(f))
ok(pedidos[-1].get("Range") == f"bytes={2 * 1024 * 1024}-", "reanuda donde se quedó")
ok(C.modelo_instalado() and open(C.ruta_modelo(), "rb").read() == DATOS, "el archivo final es correcto")
ok(progresos and progresos[-1] == 1.0 and progresos == sorted(progresos), "progreso hasta el 100 %")
ok(C.descargar() == C.ruta_modelo(), "si ya está, no descarga otra vez")
ok(C.instalados() == ["prueba"], "lista de instalados")

# espacio en disco
C2 = cp.CerebroPropio(tempfile.mkdtemp(), abrir=abrir)
real = cp.shutil.disk_usage
cp.shutil.disk_usage = lambda p: type("U", (), {"free": 10})()
try:
    C2.descargar("listo"); ok(False, "sin espacio")
except cp.CerebroPropioError as e:
    ok("No hay espacio" in str(e), "comprueba el espacio libre antes")
cp.shutil.disk_usage = real

# cancelar
C3 = cp.CerebroPropio(tempfile.mkdtemp(), abrir=abrir); C3.elegir("prueba")
C3._cancelar.set()
orig_clear = C3._cancelar.clear; C3._cancelar.clear = lambda: None
try:
    C3.descargar(); ok(False, "cancelar")
except cp.CerebroPropioError as e:
    ok("pausada" in str(e), "se puede pausar la descarga")

# ---------- encender: motor rápido si se puede; si no, el genérico ----------
os.makedirs(os.path.join(T, "bin"))
for b in cp.BINARIOS:
    open(os.path.join(T, "bin", b), "w").close()
ok([os.path.basename(b) for b in C.binarios()] == list(cp.BINARIOS), "encuentra los dos motores, el rápido primero")
lanzados, sano = [], {"si": False}
class Proc:
    def __init__(s, args, muere=False): s.args, s.vivo, s.muere = args, True, muere
    def poll(s): return 1 if s.muere or not s.vivo else None
    def terminate(s): s.vivo = False
    def wait(s, timeout=None): return 0
    def kill(s): s.vivo = False
def lanzar(args, **kw):
    lanzados.append(args)
    dp = args[0].endswith("_dp.so")
    p = Proc(args, muere=dp)                          # este «móvil» no soporta el motor rápido
    sano["si"] = not dp
    return p
C._lanzar, C._salud = lanzar, lambda: sano["si"]
ok(C.encender(espera=2) and C.encendido(), "arranca")
ok(lanzados[0][0].endswith("_dp.so") and C.binario_usado.endswith("libkira_cerebro.so"), "si el rápido falla, usa el genérico")
a = lanzados[-1]
ok("--host" in a and a[a.index("--host") + 1] == "127.0.0.1" and a[a.index("-m") + 1] == C.ruta_modelo(), "solo escucha en el propio móvil")
ok("ENCENDIDO" in C.estado_texto(), "estado encendido")
ok(C.encender(espera=2), "encender dos veces no rompe nada")
C.apagar(); ok(not C.encendido() and C.estado == "apagado", "apaga")
# opción --reasoning-budget no soportada: reintenta sin ella
lanzados.clear()
def lanzar2(args, **kw):
    lanzados.append(args); p = Proc(args, muere="--reasoning-budget" in args); sano["si"] = "--reasoning-budget" not in args; return p
C._lanzar = lanzar2
ok(C.encender(espera=2) and "--reasoning-budget" not in lanzados[-1], "si la versión no entiende una opción, arranca sin ella")
C.apagar()
# sin modelo / sin motor
C4 = cp.CerebroPropio(tempfile.mkdtemp(), carpeta_binarios=os.path.join(T, "bin"))
ok(not C4.encender(espera=1) and "descargar" in C4.mensaje, "sin modelo: lo dice")
C5 = cp.CerebroPropio(T, carpeta_binarios=os.path.join(T, "nada")); C5.elegir("prueba")
ok(not C5.encender(espera=1) and "no trae el motor" in C5.mensaje, "sin motor: lo dice")
C.borrar_modelo("prueba"); ok(not C.modelo_instalado(), "borrar el modelo")
print("CEREBRO PROPIO OK", n)
