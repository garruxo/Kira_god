# -*- coding: utf-8 -*-
"""v2.85: la MÁQUINA VIRTUAL de Kira (kira_portatil/maquina_kira.py). Aquí no hay QEMU ni KVM: se prueba la parte pura
de verdad (órdenes, semilla, guion que se ejecuta DENTRO —corrido con bash de verdad—, fotos) y la máquina con un QEMU
de mentira (procesos, SSH y la conversación QMP por un socket de verdad)."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import maquina_kira as mq

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


T = tempfile.mkdtemp(prefix="maq")

# ---------- la semilla y la orden de QEMU (los candados) ----------
ud = mq.user_data("ssh-ed25519 AAAAC3Nza kira-maquina")
ok(ud.startswith("#cloud-config") and "name: kira" in ud and "ssh-ed25519 AAAAC3Nza" in ud, "semilla con su llave")
ok("ssh_pwauth: false" in ud and "lock_passwd: true" in ud, "sin contraseñas: solo entra con su llave")
o = mq.orden_qemu(T, kvm=True)
t = " ".join(o)
ok("-enable-kvm" in o and "restrict=on" in t, "con KVM y la red de QEMU AISLADA")
ok(f"guestfwd=tcp:{mq.PUERTA_IP}:{mq.PUERTA_PUERTO}-cmd:" in t and "proxy_maquina.py" in t,
   "v2.91: por defecto, su única salida es la puerta (proxy fuera de la máquina)")
ok("hostfwd=tcp:127.0.0.1:2223-:22" in t and "127.0.0.1:1" in o, "SSH y pantalla solo en el propio portátil")
ok(not any(x in t for x in ("-virtfs", "9p", "smb=", "-fsdev")), "no comparte ninguna carpeta tuya")
ok("-daemonize" in o and "-pidfile" in o and "-m" in o and o[o.index("-m") + 1] == "1024", "1 GB y en segundo plano")
t2 = " ".join(mq.orden_qemu(T, kvm=False, red=False))
ok("tcg" in t2 and "restrict=on" in t2 and "guestfwd" not in t2, "sin KVM va con tcg; «sin internet»: ni puerta")
ok("restrict=off" not in t and "restrict=off" not in t2, "NUNCA con la red abierta (vería tu casa)")
ok("BatchMode=yes" in mq.orden_ssh(T) and "kira@127.0.0.1" in mq.orden_ssh(T), "entra por SSH con su llave")

# ---------- el guion que corre DENTRO: lo ejecuto con bash de verdad ----------
pantalla = os.path.join(T, "pantalla_tty1.txt")


def correr_guion(g):
    g = g.replace("/dev/tty1", pantalla)
    r = subprocess.run(["bash", "-s"], input=g, capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout


c, s = correr_guion(mq.guion_remoto("echo hola desde dentro; echo 'con comillas \"raras\"'"))
ok(c == 0 and "hola desde dentro" in s and 'con comillas "raras"' in s, "el comando se ejecuta tal cual")
ok("kira@maquina$" in s, "se ve qué ejecuta Kira")
ok(os.path.isfile(pantalla) and "hola desde dentro" in open(pantalla).read(),
   "y TAMBIÉN sale en la pantalla de la máquina (la ves trabajar)")
c, s = correr_guion(mq.guion_remoto("echo antes; exit 3"))
ok(c == 3 and "antes" in s, "si falla, devuelve su código de error")
c, s = correr_guion(mq.guion_remoto("print(sum(range(10)))\nprint('KIRA_FIN')", python=True, delim="KIRA_FIN"))
ok(c == 0 and "45" in s and "KIRA_FIN" in s, "ejecuta programas Python (aunque contengan la marca del guion)")
c, s = correr_guion(mq.guion_remoto("echo calladito", mostrar=False))
ok(c == 0 and "calladito" in s and "kira@maquina$" not in s, "y también sin enseñarlo")

# ---------- fotos ----------
ok(mq.nombre_foto("antes de probar") == "antes_de_probar", "nombre de foto limpio")
ok(mq.nombre_foto(None, ahora=0).startswith("foto-"), "sin nombre: foto con fecha")
try:
    mq.nombre_foto("../../etc")
    ok(False, "nombre raro")
except mq.MaquinaError:
    ok(True, "un nombre de foto raro no vale")
info = json.dumps({"snapshots": [{"name": "nueva", "date-sec": 0}, {"name": "antes_de_probar", "date-sec": 60}]})
ok([f["nombre"] for f in mq.fotos_de_info(info)] == ["nueva", "antes_de_probar"], "lee las fotos del disco")
ok(mq.fotos_de_info("basura") == [], "si no entiende, no inventa")

# ---------- las órdenes ----------
for frase, esp in (("Kira, prepara tu máquina", ("preparar", "")), ("arranca tu máquina", ("encender", "red")),
                   ("enciende tu máquina con internet", ("encender", "red")), ("apaga tu máquina", ("apagar", "")),
                   ("arranca tu máquina sin internet", ("encender", "sin")),
                   ("enséñame tu máquina", ("ver", "")), ("abre tu máquina", ("encender", "red")),
                   ("ejecuta en tu máquina: ls -la /Etc", ("ejecutar", "ls -la /Etc")),
                   ("lee en tu máquina /etc/hostname", ("leer", "/etc/hostname")),
                   ("prueba el programa en tu máquina", ("probar", "")), ("estudia tu máquina", ("estudiar", "")),
                   ("estudia linux en tu máquina", ("estudiar", "")),
                   ("haz una foto de tu máquina", ("foto", "")),
                   ("haz una foto de tu máquina llamada Antes", ("foto", "Antes")),
                   ("vuelve a la foto nueva", ("volver", "nueva")), ("fotos de tu máquina", ("fotos", "")),
                   ("estado de tu máquina", ("estado", "")), ("deja tu máquina como nueva", ("nueva", ""))):
    ok(mq.orden_maquina(frase) == esp, f"«{frase}» -> {esp} (salió {mq.orden_maquina(frase)})")
for frase in ("estudia Python", "la máquina de café", "qué es una máquina virtual"):
    ok(mq.orden_maquina(frase) is None, f"«{frase}» no es para su máquina")

# ---------- la máquina con un QEMU de mentira ----------
B = os.path.join(T, "m")
llamadas = []
INFO = {"snapshots": []}


def correr(orden, input=None, capture_output=True, text=True, timeout=None):
    llamadas.append((orden, input))
    p = orden[0]
    j = lambda x: os.path.join(B, x)  # noqa: E731
    if p == "curl":
        open(orden[orden.index("-o") + 1], "wb").write(b"qcow2 de mentira")
    elif p == "ssh-keygen":
        f = orden[orden.index("-f") + 1]
        open(f, "w").write("privada"); open(f + ".pub", "w").write("ssh-ed25519 AAAA kira-maquina")
    elif p == "cloud-localds":
        open(orden[1], "wb").write(b"iso")
    elif p == "qemu-img" and orden[1] == "create":
        open(orden[-2], "wb").write(b"disco")
    elif p == "qemu-img" and orden[1] == "snapshot" and orden[2] == "-c":
        INFO["snapshots"].append({"name": orden[3], "date-sec": 1})
    elif p == "qemu-img" and orden[1] == "info":
        return subprocess.CompletedProcess(orden, 0, json.dumps(INFO), "")
    elif p == "qemu-system-x86_64":
        open(j("maquina.pid"), "w").write(str(os.getpid()))
        threading.Thread(target=qmp_falso, args=(j("qmp.sock"),), daemon=True).start()
        import time as _t
        _t.sleep(0.2)
    elif p == "ssh":
        if input and "echo hola" in input:
            return subprocess.CompletedProcess(orden, 0, "kira@maquina$ echo hola\nhola\n", "")
        return subprocess.CompletedProcess(orden, 0, "salida de " + (input or "").split("\n")[2][:30] if input
                                           else "", "")
    return subprocess.CompletedProcess(orden, 0, "", "")


qmp_vistos = []


def qmp_falso(ruta):
    try:
        os.remove(ruta)
    except OSError:
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(ruta)
    srv.listen(5)
    while True:
        try:
            c, _ = srv.accept()
        except OSError:
            return
        f = c.makefile("rwb")
        f.write(b'{"QMP": {"version": {}}}\n'); f.flush()
        for linea in f:
            d = json.loads(linea)
            qmp_vistos.append(d)
            if d["execute"] == "human-monitor-command":
                cl = d["arguments"]["command-line"]
                if cl.startswith("savevm "):
                    INFO["snapshots"].append({"name": cl.split()[1], "date-sec": 2})
            if d["execute"] in ("system_powerdown", "quit"):
                try:
                    os.remove(os.path.join(B, "maquina.pid"))
                except OSError:
                    pass
            f.write(b'{"event": "ALGO"}\n{"return": ""}\n' if d["execute"] != "qmp_capabilities"
                    else b'{"return": {}}\n')
            f.flush()
        c.close()


m = mq.Maquina(base=B, correr=correr, which=lambda p: "/usr/bin/" + p, dormir=lambda s: None, kvm=True)
ok("Todavía no tengo máquina" in m.estado(), "antes de preparar lo dice")
txt = m.preparar()
ok("preparada" in txt and m.preparada(), "se prepara: imagen, llave, semilla y disco")
ok(oct(os.stat(B).st_mode & 0o777) == "0o700", "su carpeta es solo tuya")
ok(any(o[0] == "qemu-img" and "-b" in o for o, _ in llamadas), "su disco va encima de la imagen original")
txt = m.encender()
ok(m.encendida() and "solo por mi puerta" in txt and m.modo_red() == "puerta",
   "se enciende con internet solo por su puerta (v2.91)")
aj = [i for o, i in llamadas if o[0] == "ssh" and i and "useradd" in i]
ok(aj and "date -u -s @" in aj[-1] and "prueba" in aj[-1] and "95kira-puerta" in aj[-1],
   "al arrancar: pone la hora, crea el usuario «prueba» sin permisos y la puerta")
ok("nueva" in [f["nombre"] for f in m.fotos()], "en el primer arranque hace la foto «nueva»")
c, s = m.ejecutar("echo hola")
ok(c == 0 and "hola" in s, "ejecuta dentro y devuelve lo que sale")
ok("kira@maquina$ echo hola" in open(os.path.join(B, "maquina.log")).read(), "y lo apunta en su registro")
ok(m.foto("antes de probar") == "antes_de_probar" and
   any(d.get("arguments", {}).get("command-line") == "savevm antes_de_probar" for d in qmp_vistos),
   "foto con la máquina encendida (por QMP)")
ok(m.volver("antes de probar") == "antes_de_probar" and
   any(d.get("arguments", {}).get("command-line") == "loadvm antes_de_probar" for d in qmp_vistos),
   "y vuelve a ella")
try:
    m.volver("no_existe")
    ok(False, "foto que no existe")
except mq.MaquinaError:
    ok(True, "a una foto que no existe no vuelve")
fichas = []
r = mq.hacer(m, "estudiar", guardar_ficha=lambda tema, texto: fichas.append((tema, texto)))
ok(len(fichas) == len(mq.ESTUDIO) and fichas[0][0].startswith("mi máquina:"), "estudia Linux y lo guarda en su baúl")
ok(all(not any(x in cmd.replace("2>/dev/null", "").replace("->", "").replace(">=", "") for x in ("rm ", ">", "apt", "dd ", "tee", "mv "))
       for _t, cmd, _e in mq.ESTUDIO),
   "estudiar solo LEE (no cambia nada dentro)")
ok("No tengo ningún programa" in mq.hacer(m, "probar")["texto"], "sin programa reciente lo dice")
m.ultimo_codigo = "print(1)"
ok("probado en mi máquina" in mq.hacer(m, "probar")["texto"], "prueba su último programa dentro")
abiertos = []
m.ver(entorno={}, popen=lambda orden, **kw: abiertos.append((orden, kw.get("env", {}).get("DISPLAY"))))
ok(any("vncviewer" in o[0] for o, _d in abiertos) and abiertos[0][1] == ":0",
   "te abre su pantalla en el portátil (aunque lo pidas desde el móvil)")
ok(any("tail" in " ".join(o) for o, _d in abiertos), "y la ventana de lo que va haciendo")
ok("Mi máquina está apagada" in m.apagar() and not m.encendida(), "se apaga")
try:
    m.ejecutar("ls")
    ok(False, "apagada")
except mq.MaquinaError as e:
    ok("arranca tu máquina" in str(e), "apagada no ejecuta y dice cómo encenderla")

# ---------- enganchada en la Kira completa del portátil ----------
import nucleo_portatil as npo


class MaqFalsa:
    def __init__(self):
        self.ultimo_codigo, self.probados = None, []
    def probar_python(self, codigo, **k):
        self.probados.append(codigo); return 0, "45"
    def estudiar(self, al_paso=None):
        return [("el sistema", "qué Linux es", "Debian 13")]


class Rec:
    def __init__(self):
        self.g = []
    def guardar(self, texto, tema="", fuente=""):
        self.g.append((tema, fuente))


class CoreFalso:
    recuerdos = Rec()
    def registrar_actividad(self): pass
    def nueva_tarea(self): pass
    def es_estudia_general(self, o): return "algo" if o.startswith("estudia") else None
    def estudiar_a_fondo(self, tema, al_paso=None): raise AssertionError("no debe estudiar en internet")
    def programa_acordado(self, pedido, al_paso=None):
        self.pedido = pedido; return {"ok": True, "codigo": "print(45)", "nombre": "suma"}
    def procesar_orden(self, o): return "charla"


mf = MaqFalsa()
npo._MAQUINA["m"] = mf
core = CoreFalso()
r = npo.ejecutar(core, "estudia tu máquina", lambda *a: None)
ok("estudiado cómo funciona Linux" in r["texto"] and core.recuerdos.g[0][1] == "mi máquina virtual",
   "«estudia tu máquina» va a la máquina (no a internet) y guarda en el baúl")
r = npo.ejecutar(core, "escríbeme un programa que sume del 0 al 9 y pruébalo en tu máquina", lambda *a: None)
ok("pruébalo" not in core.pedido and mf.probados == ["print(45)"] and "en mi máquina funciona" in r["texto"],
   "«…y pruébalo en tu máquina»: escribe el programa y lo prueba dentro")
ok(mf.ultimo_codigo == "print(45)", "se acuerda del último programa («prueba el programa en tu máquina»)")

# ---------- el móvil se lo pasa al portátil ----------
import mando_kira as mdk
ok(mdk.es_de_maquina("abre tu máquina") and not mdk.es_local("abre tu máquina"),
   "«abre tu máquina» no se queda en el móvil")
ok(mdk.es_local("abre la sala hacker"), "lo demás de «abre…» sigue en el móvil")
src_i = open(os.path.join(RAIZ, "interfaz_kira.py"), encoding="utf-8").read()
ok("mdk_.es_de_maquina(orden)" in src_i, "sin portátil, el móvil explica que la máquina vive allí")
sh = open(os.path.join(RAIZ, "kira_portatil", "instalar_portatil.sh"), encoding="utf-8").read()
ok("qemu-system-x86" in sh and "kira-maquina" in sh and "usermod -aG kvm" in sh and "Intel Virtualization" in sh,
   "el instalador pone QEMU, su orden, KVM y avisa de la BIOS")

print("\nTODO BIEN", n)
