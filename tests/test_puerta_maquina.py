# -*- coding: utf-8 -*-
"""v2.91: KiraOS investiga, busca y experimenta DESDE SU MÁQUINA VIRTUAL, con internet solo por su PUERTA
(proxy_maquina.py, fuera de la máquina) que nunca deja ir a tu casa. Aquí no hay QEMU: la puerta se prueba de verdad
con sockets, y los guiones que corren dentro se ejecutan con bash de verdad (con un «sudo» de mentira)."""
import email.message
import http.server
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import proxy_maquina as px  # noqa: E402
import maquina_kira as mq  # noqa: E402
import red_kira  # noqa: E402

n = 0


def ok(c, m):
    global n
    n += 1
    print(("[OK] " if c else "[X] ") + m)
    if not c:
        sys.exit(1)


T = tempfile.mkdtemp(prefix="kira_puerta_")

# =====================================================================================
#  1. LA PUERTA: qué deja pasar y qué no
# =====================================================================================
for ip in ("93.184.216.34", "1.1.1.1", "2606:4700:4700::1111"):
    ok(px.permitido(ip), f"{ip} es internet: pasa")
for ip in ("192.168.1.1", "10.0.2.2", "127.0.0.1", "172.20.0.5", "169.254.1.1", "100.64.0.1", "0.0.0.0", "::1",
           "fe80::1", "fd00::5", "::ffff:192.168.1.7", "224.0.0.1", "basura"):
    ok(not px.permitido(ip), f"{ip} es de casa o especial: NO pasa")

p = px.analizar(b"CONNECT es.wikipedia.org:443 HTTP/1.1\r\nHost: es.wikipedia.org:443")
ok(p["tipo"] == "CONNECT" and p["host"] == "es.wikipedia.org" and p["puerto"] == 443, "entiende CONNECT (https)")
p = px.analizar(b"GET http://ejemplo.org/a?b=1 HTTP/1.1\r\nHost: ejemplo.org\r\nProxy-Connection: keep-alive")
ok(p["tipo"] == "HTTP" and p["puerto"] == 80 and p["linea"] == "GET /a?b=1 HTTP/1.1", "entiende http normal")
cab = px.cabecera_http(p).decode()
ok("Proxy-Connection" not in cab and cab.endswith("Connection: close\r\n\r\n") and "Host: ejemplo.org" in cab,
   "al sitio le llega la petición limpia (sin cabeceras del proxy)")
for mala, cod in ((b"CONNECT 10.0.2.2:22 HTTP/1.1", 403), (b"CONNECT smtp.gmail.com:25 HTTP/1.1", 403),
                  (b"GET http://ejemplo.org:8080/ HTTP/1.1", 403), (b"GET /sin/host HTTP/1.1", 400),
                  (b"hola que tal", 400), (b"CONNECT a b:443 HTTP/1.1", 400)):
    try:
        px.analizar(mala)
        ok(False, f"{mala!r} no debía pasar")
    except px.PuertaError as e:
        ok(e.codigo == cod, f"{mala[:34]!r} → {e.codigo} (solo webs: 443 y 80)")


def resolver(mapa):
    def g(host, puerto, *_a):
        if host not in mapa:
            raise socket.gaierror("no existe")
        return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, puerto))
                for ip in mapa[host]]
    return g


MAPA = {"ejemplo.kira": ["93.184.216.34"], "router.casa": ["192.168.1.1"], "mixto.kira": ["10.0.0.5", "8.8.8.8"],
        "rebote.kira": ["127.0.0.1"]}
fam, dire = px.elegir_direccion("mixto.kira", 443, resolver(MAPA))
ok(dire[0] == "8.8.8.8", "si un sitio tiene varias direcciones, usa solo la pública")
for host in ("router.casa", "rebote.kira"):
    try:
        px.elegir_direccion(host, 443, resolver(MAPA))
        ok(False, host)
    except px.PuertaError as e:
        ok(e.codigo == 403 and "tu casa" in e.motivo, f"«{host}» apunta a tu casa/al portátil: 403")
try:
    px.elegir_direccion("no.existe", 443, resolver(MAPA))
    ok(False, "no existe")
except px.PuertaError as e:
    ok(e.codigo == 502, "un sitio que no existe: 502")


# =====================================================================================
#  2. LA PUERTA DE VERDAD: una conexión como las que lanza QEMU (entrada/salida = la conexión)
# =====================================================================================
class Web(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        cuerpo = ("<html><head><title>Página de prueba</title></head><body><p>Hola desde internet: " + self.path +
                  "</p></body></html>").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *_a):
        pass


web = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Web)
threading.Thread(target=web.serve_forever, daemon=True).start()
PWEB = web.server_address[1]
eco = socket.socket()
eco.bind(("127.0.0.1", 0))
eco.listen(5)
PECO = eco.getsockname()[1]


def servir_eco():
    while True:
        c, _ = eco.accept()
        d = c.recv(100)
        c.sendall(b"ECO:" + d)
        c.close()


threading.Thread(target=servir_eco, daemon=True).start()
visitas = []


def conectar_falso(_familia, dire):
    """Lo público de mentira (93.184.216.34) va a nuestros servidores locales (puerto 443 = eco, 80 = web)."""
    assert px.permitido(dire[0]), "la puerta intentó conectar a algo de casa"
    visitas.append(dire)
    return socket.create_connection(("127.0.0.1", PECO if dire[1] == 443 else PWEB), timeout=5)


puerta = socket.socket()
puerta.bind(("127.0.0.1", 0))
puerta.listen(20)
PPUERTA = puerta.getsockname()[1]
registro = []


def servir_puerta():
    while True:
        c, _ = puerta.accept()
        fd = c.fileno()
        threading.Thread(target=lambda c=c, fd=fd: (px.atender(fd, fd, getaddrinfo=resolver(MAPA),
                                                               conectar=conectar_falso, registrar=registro.append),
                                                    c.close()), daemon=True).start()


threading.Thread(target=servir_puerta, daemon=True).start()


def hablar_puerta(datos):
    s = socket.create_connection(("127.0.0.1", PPUERTA), timeout=10)
    s.sendall(datos)
    sal = b""
    while True:
        d = s.recv(4096)
        if not d:
            break
        sal += d
    s.close()
    return sal


r = hablar_puerta(b"CONNECT ejemplo.kira:443 HTTP/1.1\r\nHost: ejemplo.kira:443\r\n\r\nhola-tls")
ok(r.startswith(b"HTTP/1.1 200 Connection established\r\n\r\n") and r.endswith(b"ECO:hola-tls"),
   "CONNECT a internet: abre el túnel y pasa los datos en las dos direcciones")
r = hablar_puerta(b"CONNECT router.casa:443 HTTP/1.1\r\n\r\n")
ok(r.startswith(b"HTTP/1.1 403") and "no deja ir a tu casa" in r.decode(), "CONNECT a tu router: 403, no conecta")
r = hablar_puerta(b"CONNECT 192.168.1.20:443 HTTP/1.1\r\n\r\n")
ok(r.startswith(b"HTTP/1.1 403"), "CONNECT a una IP de casa escrita a mano: 403")
r = hablar_puerta(b"GET http://ejemplo.kira/hola HTTP/1.1\r\nHost: ejemplo.kira\r\n\r\n")
ok(b"200 OK" in r.split(b"\r\n")[0] and b"Hola desde internet: /hola" in r, "http normal a internet: pasa")
ok(all(px.permitido(d[0]) for d in visitas), "la puerta solo llegó a conectar con direcciones públicas")
ok(any("ejemplo.kira:443 ok" in x for x in registro) and any("denegado (403)" in x for x in registro),
   "apunta a qué sitios fue y qué paró")


# =====================================================================================
#  3. LO QUE CORRE DENTRO (con bash de verdad y un «sudo» de mentira)
# =====================================================================================
BIN = os.path.join(T, "bin")
os.makedirs(BIN)
with open(os.path.join(BIN, "sudo"), "w") as f:
    f.write("#!/bin/bash\n"
            "while [ $# -gt 0 ]; do case \"$1\" in -n) shift;; -u) shift 2;; --) shift; break;; *) break;; esac; done\n"
            "if [ \"$1\" = tee ] && [ \"$2\" = /dev/tty1 ]; then exit 1; fi\n"   # sin pantalla tty1 aquí
            "if [ \"$1\" = pkill ]; then echo PKILL \"$@\" >> \"" + os.path.join(T, "pkill.txt") + "\"; exit 0; fi\n"
            "exec \"$@\"\n")
os.chmod(os.path.join(BIN, "sudo"), 0o755)
ENV = dict(os.environ, PATH=BIN + ":" + os.environ.get("PATH", ""))


def bash(guion):
    r = subprocess.run(["bash", "-s"], input=guion, capture_output=True, text=True, timeout=120, env=ENV)
    return r.returncode, r.stdout + r.stderr


g = mq.guion_experimento("import sys\nprint('resultado', sum(range(10)))\nprint('python', sys.flags.isolated)")
c, s = bash(g)
ok(c == 0 and "resultado 45" in s and "python 1" in s, "un experimento corre (Python aislado, -I) y devuelve lo que imprime")
ok("PKILL pkill -9 -u prueba" in open(os.path.join(T, "pkill.txt")).read(),
   "al acabar mata lo que el experimento dejara corriendo (del usuario prueba)")
ok("sudo -n -u prueba" in g and "ulimit -t" in g and "timeout -k 5" in g, "como «prueba», con tope de tiempo y memoria")
ok("\ncd /tmp\n" in g and "\ncd /tmp\n" in mq.guion_web("https://a.org/"),
   "v2.92: trabaja desde /tmp («prueba» no puede entrar en la carpeta de kira)")
ok(mq.MAX_WEB >= 8_000_000, "v2.92: trae páginas grandes (la de un vídeo) enteras")
c, s = bash(mq.guion_experimento("raise ValueError('no cuadra')"))
ok(c != 0 and mq.resumen_error(s, c) == "ValueError: no cuadra", "si falla, saca la línea del error de verdad")
c, s = bash(mq.guion_experimento("import modulo_que_no_existe_kira"))
ok("No module named" in mq.resumen_error(s, c), "y si falta una librería, lo dice tal cual")
ok(not [x for x in os.listdir("/tmp") if x.startswith("kira_exp.")], "borra su carpeta de pruebas al acabar")
ok(mq.resumen_error("", 124).startswith("tardó demasiado"), "si se pasa de tiempo, lo dice")

# la visita a una web, DESDE DENTRO, por la puerta (aquí la puerta es la de verdad, en un puerto local)
g = mq.guion_web("http://ejemplo.kira/desde-la-maquina", cabeceras={"User-Agent": "Kira"}).replace(
    mq.PUERTA, f"http://127.0.0.1:{PPUERTA}")
c, s = bash(g)
d = mq.leer_respuesta_web(s)
ok(d and d["status"] == 200 and b"Hola desde internet: /desde-la-maquina" in d["cuerpo"],
   "visita una web desde dentro, pasando por la puerta")
ok(any(k.lower() == "content-type" and "text/html" in v for k, v in d["cabeceras"]), "y trae las cabeceras")
g = mq.guion_web("http://router.casa/admin").replace(mq.PUERTA, f"http://127.0.0.1:{PPUERTA}")
d = mq.leer_respuesta_web(bash(g)[1])
ok(d and d["status"] == 403 and b"no deja ir a tu casa" in d["cuerpo"], "desde dentro NO llega a tu router: 403")
ok(mq.leer_respuesta_web("basura sin línea") is None, "si no vuelve nada, no se inventa una página")
aj = mq.guion_ajustes(1_800_000_000)
ok("date -u -s @1800000000" in aj and "useradd" in aj and mq.PUERTA in aj, "ajustes de cada arranque")


# =====================================================================================
#  4. RedMaquina: lo de investigar sale por la máquina; las claves y lo de casa, nunca
# =====================================================================================
class MaqWeb:
    def __init__(self):
        self.prep, self.k, self.enc, self.modo = True, True, True, "puerta"
        self.pedidas, self.recuperada, self.encendidas, self.falla = [], 0, 0, False
        self.respuesta = {"status": 200, "url": "", "cabeceras": [["Content-Type", "text/html; charset=utf-8"]],
                          "cuerpo": b"<html><head><title>Sobre Python</title></head><body><p>Python es un lenguaje de "
                                    b"programacion muy legible y facil de aprender.</p></body></html>"}

    def preparada(self): return self.prep
    def kvm(self): return self.k
    def encendida(self): return self.enc
    def modo_red(self): return self.modo if self.enc else None

    def encender(self, red=True):
        self.encendidas += 1
        self.enc, self.modo = True, "puerta" if red else "sin"

    def recuperar(self):
        self.recuperada += 1

    def pedir_web(self, url, datos=None, cabeceras=None, metodo=None, timeout=25):
        if self.falla:
            raise mq.MaquinaError("no contesta")
        self.pedidas.append((url, dict(cabeceras or {}), datos))
        d = dict(self.respuesta)
        d["url"] = url
        return d


directas = []


def directo(req, timeout=30):
    directas.append(req.full_url)
    return mq.RespuestaWeb({"status": 200, "cabeceras": [["Content-Type", "text/plain"]], "cuerpo": b"directo"},
                           req.full_url)


mw = MaqWeb()
red = mq.RedMaquina(mw, directo=directo, reloj=lambda: 1000.0)
import internet_kira as ik  # noqa: E402
net = ik.Internet(T, abrir=red.abrir)
pag = net.leer("https://es.wikipedia.org/wiki/Python")
ok(pag["titulo"] == "Sobre Python" and "lenguaje" in pag["texto"] and mw.pedidas and not directas,
   "leer una página: la visita la hace la máquina y Kira recibe el TEXTO")
ok(red.via == "maquina" and "máquina virtual" in red.estado(), "y dice que salió desde la máquina")
ok(mw.pedidas[0][1].get("User-agent"), "lleva las cabeceras normales (navegador)")
# claves y cosas de casa: SIEMPRE directo (una clave nunca entra en la máquina)
for url, cab in (("https://api.anthropic.com/v1/messages", {"x-api-key": "sk-secreta"}),
                 ("https://api.github.com/user", {"Authorization": "token ghp_secreto"}),
                 ("http://127.0.0.1:8770/hola", {}), ("http://192.168.1.40:8771/hola", {}),
                 ("http://localhost:8081/completion", {}), ("http://kira-portatil.local/", {})):
    antes = len(mw.pedidas)
    red.abrir(urllib.request.Request(url, headers=cab), timeout=5)
    ok(len(mw.pedidas) == antes and directas[-1] == url, f"{url[:40]}… va directo (clave o casa), nunca por la máquina")
ok(not any("secret" in json.dumps(p[1]) for p in mw.pedidas), "ninguna clave ha entrado en la máquina")
# 404 de la web → error normal de urllib (Internet lo entiende)
mw.respuesta = {"status": 404, "cabeceras": [], "cuerpo": b"no"}
try:
    red.abrir(urllib.request.Request("https://ejemplo.org/no"), timeout=5)
    ok(False, "404")
except urllib.error.HTTPError as e:
    ok(e.code == 404, "una web que responde 404 da el error de siempre")
mw.respuesta = {"error": "URLError: Tunnel connection failed: 403 Forbidden"}
try:
    red.abrir(urllib.request.Request("https://ejemplo.org/x"), timeout=5)
    ok(False, "error")
except urllib.error.URLError:
    ok(True, "si la puerta lo para, sale como error de conexión")
# la máquina apagada: la enciende con la puerta
mw.enc, mw.respuesta = False, {"status": 200, "cabeceras": [], "cuerpo": b"ok"}
red.abrir(urllib.request.Request("https://ejemplo.org/y"), timeout=5)
ok(mw.encendidas == 1 and mw.modo == "puerta", "si la máquina está apagada, la enciende (con la puerta) y visita")
# la máquina no contesta: lo hace el portátil, y a la segunda vuelve a su foto limpia
mw.falla = True
red.abrir(urllib.request.Request("https://ejemplo.org/z1"), timeout=5)
ok(directas[-1].endswith("/z1") and red.via == "portatil" and "no contestó" in red.estado(),
   "si la máquina no contesta, lo busca el portátil y lo dice")
red.abrir(urllib.request.Request("https://ejemplo.org/z2"), timeout=5)
ok(mw.recuperada == 1, "a la segunda sin contestar, la máquina vuelve sola a su foto limpia")
mw.falla = False
# sin KVM o sin preparar: desde el portátil, diciendo por qué
for attr, palabra in (("k", "KVM"), ("prep", "preparada")):
    m2 = MaqWeb()
    setattr(m2, attr, False)
    r2 = mq.RedMaquina(m2, directo=directo)
    r2.abrir(urllib.request.Request("https://ejemplo.org/w"), timeout=5)
    ok(not m2.pedidas and palabra in r2.estado(), f"sin {palabra}: lo hace el portátil y lo dice")
m3 = MaqWeb()
m3.modo = "sin"
r3 = mq.RedMaquina(m3, directo=directo)
r3.abrir(urllib.request.Request("https://ejemplo.org/w"), timeout=5)
ok(not m3.pedidas and "sin internet" in r3.estado(), "si la encendiste «sin internet», no la usa para navegar")

# el gancho de red_kira: en el móvil no hay nada puesto (igual que siempre)
ok(red_kira._INVESTIGAR["abrir"] is None, "en el móvil, investigar sale como siempre")
vistos = []
red_kira.poner_investigar(lambda req, timeout=30: vistos.append(req.full_url) or "resp")
ok(red_kira.abrir_investigar(urllib.request.Request("https://x.org/"), timeout=3) == "resp" and vistos,
   "en KiraOS, investigar sale por su máquina")
red_kira.poner_investigar(None)
for mod, fun in (("internet_kira", "red_kira.abrir_investigar"), ("video_kira", "red_kira.abrir_investigar"),
                 ("estudio_kira", "red_kira.abrir_investigar")):
    ok(fun in open(os.path.join(RAIZ, mod + ".py"), encoding="utf-8").read(), f"{mod} investiga por el gancho")
ok("red_kira.abrir(" in open(os.path.join(RAIZ, "descargas_kira.py"), encoding="utf-8").read(),
   "las descargas de Kira (modelos) siguen directas, no por la máquina")


# =====================================================================================
#  5. LOS EXPERIMENTOS AL PENSAR: dentro de la máquina (y si no puede, el modo seguro de siempre)
# =====================================================================================
class MaqExp:
    def __init__(self, c, s, enc=True):
        self.c, self.s, self.enc, self.vistos = c, s, enc, []

    def encendida(self): return self.enc

    def experimentar(self, codigo):
        self.vistos.append(codigo)
        return self.c, self.s


r = mq.probar_en_maquina(MaqExp(0, "resultado 45\n"), "print(45)")
ok(r[0] is True and r[2]["salida"].startswith("resultado 45") and r[2]["donde"] == "maquina",
   "un experimento que funciona en la máquina")
r = mq.probar_en_maquina(MaqExp(1, "Traceback…\nZeroDivisionError: division by zero\n"), "1/0")
ok(r[0] is False and r[1] == "ZeroDivisionError: division by zero", "uno que falla, con su error de verdad")
ok(mq.probar_en_maquina(MaqExp(1, "ModuleNotFoundError: No module named 'numpy'"), "import numpy") is None,
   "si le falta una librería, sigue el camino de siempre (te pregunta antes de instalar)")
ok(mq.probar_en_maquina(MaqExp(0, "", enc=False), "print(1)") is None, "con la máquina apagada, no la usa")

import kira_god  # noqa: E402
import programar_kira as pk  # noqa: E402


class CoreMini:
    pass


cm = CoreMini()
cm.probar_experimento = lambda codigo: (True, "", {"ok": True, "salida": "desde la máquina", "donde": "maquina"})
r = kira_god.KiraGodCore._probar_experimento(cm, "print(1)")
ok(r[2]["donde"] == "maquina", "KiraOS: los experimentos al pensar van a su máquina")
juego = "def crear():\n    pass\n\ndef actualizar(j, dt):\n    pass\n\ndef dibujar(j, p):\n    pass\n"
if pk.es_juego(juego):
    r = kira_god.KiraGodCore._probar_experimento(cm, juego)
    ok(r[2].get("donde") != "maquina", "los juegos se prueban aquí (necesitan su motor)")
cm.probar_experimento = lambda codigo: None
r = kira_god.KiraGodCore._probar_experimento(cm, "print(2)")
ok(r[0] is True and "donde" not in r[2], "si la máquina no puede, modo seguro de siempre")
cm2 = CoreMini()
r = kira_god.KiraGodCore._probar_experimento(cm2, "print(3)")
ok(r[0] is True, "en el móvil (sin máquina) todo sigue igual")

# el núcleo del portátil lo engancha todo
import nucleo_portatil as npo  # noqa: E402
npo._MAQUINA["m"] = MaqWeb()
npo._MAQUINA["red"] = None
cn = CoreMini()
rd = npo.enganchar_maquina(cn)
ok(red_kira._INVESTIGAR["abrir"] == rd.abrir and callable(cn.probar_experimento),
   "el núcleo de KiraOS pone su máquina para investigar y para experimentar")
ok("internet" in npo.actividad(type("C", (), {"dir": T})()), "el panel sabe por dónde sale a internet")
red_kira.poner_investigar(None)
src = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("con_maquina=not a.sin_maquina" in src and "encender_maquina_al_arrancar" in src,
   "al arrancar KiraOS, su máquina se enciende con ella")

shutil.rmtree(T, ignore_errors=True)
web.shutdown()
print("\nTODO BIEN", n)
