# -*- coding: utf-8 -*-
"""
maquina_kira.py - La MÁQUINA VIRTUAL de Kira en el portátil (v2.85).

Pedido del dueño: «que Kira pueda crear una máquina virtual que yo pueda ver y que Kira pueda leer, ejecutar o
estudiar». Eligió: Linux LIGERO dentro (Debian «genericcloud», ~350 MB), y que sirva para PROBAR sus programas,
APRENDER sistemas, VERLA TRABAJAR y VOLVER ATRÁS (fotos del estado).

Cómo es:
  - un ordenador de mentira (QEMU; con KVM si el procesador y la BIOS lo dejan) con 1 GB de memoria y 2 núcleos;
  - el disco de Kira es una capa encima de la imagen original (kira.qcow2 sobre base.qcow2): la original no se toca,
    así que siempre se puede volver a empezar de cero;
  - Kira entra por SSH con su propia llave (solo en 127.0.0.1:2223) y lo que ejecuta SALE TAMBIÉN EN LA PANTALLA de la
    máquina (tty1), para que lo veas trabajar en la ventana (VNC en 127.0.0.1:5901) y en el registro maquina.log;
  - fotos del estado (instantáneas del qcow2): con la máquina encendida o apagada; «vuelve a la foto X».

Candados (por qué no toca lo tuyo):
  - SIN INTERNET por defecto (red de QEMU «restrict=on»: dentro no se llega ni a internet ni a tu portátil; solo entra
    el SSH de Kira por el puerto reenviado). Con red solo si lo pides («arranca tu máquina con internet»);
  - no comparte ninguna carpeta con el portátil; la pantalla y el SSH solo escuchan en 127.0.0.1;
  - lo que pasa dentro se queda dentro: nada de la máquina vuelve solo al código de Kira (las mejoras siguen por el
    laboratorio + tus dos toques / la auto-mejora con su interruptor).

Órdenes (las reconoce `orden_maquina`; el móvil se las pasa al portátil):
  «prepara tu máquina», «arranca tu máquina [con internet]», «apaga tu máquina», «enséñame tu máquina»,
  «ejecuta en tu máquina: <comando>», «lee en tu máquina <ruta>», «prueba el programa en tu máquina»,
  «estudia tu máquina», «haz una foto de tu máquina [llamada X]», «vuelve a la foto X», «fotos de tu máquina»,
  «estado de tu máquina», «deja tu máquina como nueva».
"""
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("KIRA_MAQUINA") or os.path.expanduser("~/kira_portatil/maquina")
IMAGENES = (   # Linux ligero: Debian para la nube (con cloud-init), ~350 MB
    ("debian-13-genericcloud-amd64.qcow2",
     "https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2"),
    ("debian-12-genericcloud-amd64.qcow2",
     "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2"),
)
MEMORIA_MB = 1024
NUCLEOS = 2
DISCO_GB = 8
PUERTO_SSH = 2223
PANTALLA_VNC = 1                     # 127.0.0.1:5901
USUARIO = "kira"
MAX_SALIDA = 20000
FOTO_NUEVA = "nueva"                 # la foto del primer arranque: «deja tu máquina como nueva»


class MaquinaError(RuntimeError):
    """Algo de la máquina no se puede hacer (se le dice al dueño tal cual)."""


# =====================================================================================
#  PARTE PURA (se prueba sin QEMU)
# =====================================================================================
def user_data(clave_pub, usuario=USUARIO, nombre="kira-maquina"):
    """cloud-init: crea el usuario de Kira con su llave (sin contraseña) y le deja escribir en la pantalla (tty1)."""
    clave_pub = " ".join(str(clave_pub).split())
    return "\n".join([
        "#cloud-config",
        f"hostname: {nombre}",
        "ssh_pwauth: false",
        "users:",
        f"  - name: {usuario}",
        "    gecos: Kira",
        "    shell: /bin/bash",
        "    groups: [tty]",
        "    sudo: ALL=(ALL) NOPASSWD:ALL",
        "    lock_passwd: true",
        "    ssh_authorized_keys:",
        f"      - {clave_pub}",
        "write_files:",
        "  - path: /etc/motd",
        "    content: |",
        "      Máquina de Kira: aquí prueba sus programas y aprende cómo funciona Linux por dentro.",
        "",
    ])


def meta_data(nombre="kira-maquina"):
    return f"instance-id: {nombre}-1\nlocal-hostname: {nombre}\n"


def orden_qemu(base, kvm=True, memoria=MEMORIA_MB, nucleos=NUCLEOS, red=False, pantalla=PANTALLA_VNC,
               puerto_ssh=PUERTO_SSH, qemu="qemu-system-x86_64"):
    """La orden para encender la máquina en segundo plano (se queda viva aunque Kira se reinicie)."""
    j = lambda n: os.path.join(base, n)  # noqa: E731
    o = [qemu, "-name", "kira-maquina", "-m", str(int(memoria)), "-smp", str(int(nucleos))]
    o += (["-enable-kvm", "-cpu", "host"] if kvm else ["-accel", "tcg"])
    o += ["-drive", f"file={j('kira.qcow2')},if=virtio,format=qcow2",
          "-drive", f"file={j('semilla.iso')},if=virtio,format=raw,readonly=on",
          "-netdev", f"user,id=n0,restrict={'off' if red else 'on'},hostfwd=tcp:127.0.0.1:{int(puerto_ssh)}-:22",
          "-device", "virtio-net-pci,netdev=n0",
          "-display", "none", "-vnc", f"127.0.0.1:{int(pantalla)}",
          "-qmp", f"unix:{j('qmp.sock')},server=on,wait=off",
          "-pidfile", j("maquina.pid"), "-daemonize"]
    return o


def orden_ssh(base, puerto=PUERTO_SSH, usuario=USUARIO, espera=8):
    return ["ssh", "-i", os.path.join(base, "clave"), "-p", str(int(puerto)),
            "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR",
            "-o", "BatchMode=yes", "-o", f"ConnectTimeout={int(espera)}", f"{usuario}@127.0.0.1"]


def guion_remoto(comando, mostrar=True, python=False, delim=None):
    """El guion que se manda por SSH (por la entrada, sin líos de comillas). Si `mostrar`, lo que hace Kira y lo que
    sale se ve TAMBIÉN en la pantalla de la máquina (tty1). Con `python`, `comando` es un programa Python."""
    delim = delim or ("KIRA_" + secrets.token_hex(6).upper())
    while delim in comando:
        delim += "X"
    lineas = ["set -o pipefail"]
    if python:
        lineas += [f"cat > /tmp/kira_programa.py <<'{delim}'", comando, delim]
        orden, titulo = "python3 /tmp/kira_programa.py", "python3 programa.py"
    else:
        lineas += [f"cat > /tmp/kira_orden.sh <<'{delim}'", comando, delim]
        orden, titulo = "bash /tmp/kira_orden.sh", comando.strip().splitlines()[0][:120] if comando.strip() else ""
    if mostrar:
        t = titulo.replace("'", "'\\''")
        lineas.append("{ printf '\\n\\033[1;36mkira@maquina$\\033[0m %s\\n' '" + t + "'; " + orden + "; } 2>&1 | "
                      "(sudo -n tee /dev/tty1 2>/dev/null || cat)")
    else:
        lineas.append(orden + " 2>&1")
    return "\n".join(lineas) + "\n"


_FOTO = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def nombre_foto(nombre=None, ahora=None):
    """Un nombre de foto válido (letras, números, - y _; en minúsculas). Sin nombre: foto-AAAAMMDD-HHMM."""
    if not nombre:
        return time.strftime("foto-%Y%m%d-%H%M", time.localtime(ahora or time.time()))
    n = re.sub(r"\s+", "_", _sin_tildes(str(nombre)).strip().lower())
    if not _FOTO.match(n):
        raise MaquinaError("El nombre de la foto solo puede llevar letras, números, - y _ (hasta 32).")
    return n


def fotos_de_info(info_json):
    """De `qemu-img info --output=json` saca las fotos: [{'nombre','fecha'}]."""
    try:
        d = json.loads(info_json) if isinstance(info_json, str) else (info_json or {})
    except ValueError:
        return []
    sal = []
    for s in d.get("snapshots") or []:
        ts = s.get("date-sec")
        sal.append({"nombre": s.get("name", "?"),
                    "fecha": time.strftime("%d/%m %H:%M", time.localtime(ts)) if ts else ""})
    return sal


def recortar(t, maximo=MAX_SALIDA):
    t = str(t or "")
    t = re.sub(r"\x1b\[[0-9;]*m", "", t)
    return t if len(t) <= maximo else t[:maximo] + f"\n… (recorté {len(t) - maximo} letras)"


# Lo que mira Kira para APRENDER cómo funciona un Linux por dentro (solo LEER: nada cambia la máquina)
ESTUDIO = (
    ("el sistema", "cat /etc/os-release | head -4; uname -srm",
     "qué Linux es, su núcleo (kernel) y la arquitectura del procesador"),
    ("los discos", "lsblk -o NAME,SIZE,TYPE,MOUNTPOINT; df -h / | tail -1",
     "cómo se reparte el disco en particiones y cuánto está ocupado"),
    ("la memoria", "free -m", "la RAM total, usada y la de intercambio"),
    ("el árbol de carpetas", "ls /", "las carpetas raíz: /etc (ajustes), /usr (programas), /var (datos que cambian)…"),
    ("los procesos", "ps -eo pid,ppid,user,comm --sort=pid | head -20",
     "los programas en marcha: cada uno con su número (PID) y su padre (PPID); el 1 es systemd"),
    ("los servicios", "systemctl list-units --type=service --state=running --no-pager --no-legend | head -15",
     "los servicios que systemd mantiene encendidos"),
    ("la red", "ip -brief addr; ip route | head -3", "las tarjetas de red, sus direcciones y por dónde sale"),
    ("los usuarios", "getent passwd | awk -F: '$3>=1000 || $3==0 {print $1\": uid \"$3\" -> \"$7}'",
     "quién puede entrar: root (uid 0) y los usuarios normales (uid 1000+)"),
    ("los permisos", "ls -l /etc/passwd /etc/shadow /tmp -d",
     "lectura/escritura/ejecución para dueño, grupo y resto; /etc/shadow solo lo lee root"),
    ("el arranque", "systemd-analyze 2>/dev/null | head -2; systemctl get-default",
     "cuánto tarda en arrancar y a qué «objetivo» llega"),
)


def ficha_estudio(resultados):
    """Del estudio (titulo, explicacion, salida) hace las fichas que guarda en su baúl."""
    fichas = []
    for titulo, expl, salida in resultados:
        s = recortar(salida, 1500).strip() or "(no salió nada)"
        fichas.append((f"mi máquina: {titulo}", f"En mi máquina virtual miré {titulo} ({expl}). Salió:\n{s}"))
    return fichas


def _sin_tildes(t):
    t = unicodedata.normalize("NFD", str(t or ""))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


_MAQ = r"(?:tu|la|mi)\s+maquina(?:\s+virtual)?"


def orden_maquina(texto):
    """¿Es una orden para la máquina virtual? Devuelve (accion, carga) o None. Respeta mayúsculas/minúsculas de la
    carga (el comando o la ruta)."""
    original = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", str(texto or ""), flags=re.I).strip()
    t = _sin_tildes(original.lower()).strip(" .!¡?¿")
    if "maquina" not in t and not re.match(r"^(?:vuelve|volver|regresa)\s+a\s+la\s+foto\s", t):
        return None

    def carga_tras(patron):
        m = re.search(patron, _sin_tildes(original), flags=re.I)
        return original[m.end():].strip(" :") if m else ""

    if re.match(r"^(?:prepara|crea|instala|hazte|montate)\s+" + _MAQ + r"$", t):
        return ("preparar", "")
    if re.match(r"^(?:arranca|enciende|inicia|despierta|abre)\s+" + _MAQ + r"(?:\s+con\s+(?:internet|red))?$", t):
        return ("encender", "red" if re.search(r"con\s+(?:internet|red)$", t) else "")
    if re.match(r"^(?:apaga|para|cierra|duerme)\s+" + _MAQ + r"$", t):
        return ("apagar", "")
    if re.match(r"^(?:ensename|muestrame|enseña|ver|veo|mira)\s*(?:me\s+)?" + _MAQ + r"$", t) or \
            re.match(r"^quiero ver " + _MAQ + r"$", t):
        return ("ver", "")
    if re.match(r"^(?:ejecuta|lanza|corre|haz)\s+en\s+" + _MAQ + r"\b", t):
        c = carga_tras(r"^(?:ejecuta|lanza|corre|haz)\s+en\s+(?:tu|la|mi)\s+maquina(?:\s+virtual)?")
        return ("ejecutar", c) if c else None
    if re.match(r"^(?:lee|leeme|abre el archivo|ensename el archivo)\s+(?:en|de)\s+" + _MAQ + r"\b", t):
        c = carga_tras(r"^(?:lee|leeme|abre el archivo|ensename el archivo)\s+(?:en|de)\s+(?:tu|la|mi)\s+maquina"
                       r"(?:\s+virtual)?")
        return ("leer", c) if c else None
    if re.match(r"^prueba\s+(?:el|ese|este|tu|mi)\s+(?:programa|codigo|juego)\s+en\s+" + _MAQ + r"$", t):
        return ("probar", "")
    if re.match(r"^(?:estudia|aprende|explora|investiga)\s+(?:como funciona\s+)?" + _MAQ + r"$", t) or \
            re.match(r"^(?:estudia|aprende)\s+linux\s+en\s+" + _MAQ + r"$", t):
        return ("estudiar", "")
    m = re.match(r"^(?:haz|hazle|saca|guarda)\s+una\s+foto\s+(?:de|a)\s+" + _MAQ + r"(?:\s+(?:llamada|que se llame|con el nombre)\s+(.+))?$", t)
    if m:
        return ("foto", carga_tras(r"(?:llamada|que se llame|con el nombre)") if m.group(1) else "")
    m = re.match(r"^(?:vuelve|volver|regresa)\s+(?:a\s+)?(?:la\s+foto)\s+(.+?)(?:\s+de\s+" + _MAQ + r")?$", t)
    if m:
        return ("volver", m.group(1).strip())
    if re.match(r"^(?:fotos|que fotos tiene|lista las fotos)\s+(?:de\s+)?" + _MAQ + r"$", t):
        return ("fotos", "")
    if re.match(r"^(?:estado de|como esta)\s+" + _MAQ + r"$", t):
        return ("estado", "")
    if re.match(r"^(?:deja|pon|vuelve a dejar)\s+" + _MAQ + r"\s+como\s+nueva$", t) or \
            re.match(r"^(?:borra|limpia|reinicia de cero)\s+" + _MAQ + r"$", t):
        return ("nueva", "")
    return None


# =====================================================================================
#  LA MÁQUINA (QEMU de verdad; todo lo de fuera se inyecta para poder probarlo)
# =====================================================================================
class Maquina:
    def __init__(self, base=None, correr=subprocess.run, which=shutil.which, dormir=time.sleep,
                 reloj=time.time, kvm=None, memoria=MEMORIA_MB):
        self.base = base or BASE
        self._correr, self._which, self._dormir, self._reloj = correr, which, dormir, reloj
        self._kvm = kvm
        self.memoria = memoria
        self.ultimo_codigo = None

    # ---------- utilidades ----------
    def _j(self, n):
        return os.path.join(self.base, n)

    def _run(self, orden, entrada=None, timeout=120):
        try:
            r = self._correr(orden, input=entrada, capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            raise MaquinaError(f"Falta el programa «{orden[0]}» en el portátil (lo pone el instalador).")
        except subprocess.TimeoutExpired:
            raise MaquinaError(f"Tardó más de {timeout} s y lo corté.")
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    def _log(self, texto):
        try:
            os.makedirs(self.base, exist_ok=True)
            with open(self._j("maquina.log"), "a", encoding="utf-8") as f:
                f.write(texto.rstrip("\n") + "\n")
        except OSError:
            pass

    def kvm(self):
        if self._kvm is not None:
            return self._kvm
        return os.access("/dev/kvm", os.R_OK | os.W_OK)

    def imagen(self):
        for nombre, _url in IMAGENES:
            if os.path.isfile(self._j(nombre)):
                return self._j(nombre)
        return None

    def preparada(self):
        return all(os.path.isfile(self._j(n)) for n in ("kira.qcow2", "semilla.iso", "clave"))

    def pid(self):
        try:
            with open(self._j("maquina.pid")) as f:
                p = int(f.read().strip())
            os.kill(p, 0)
            return p
        except (OSError, ValueError):
            return None

    def encendida(self):
        return self.pid() is not None

    # ---------- preparar (una vez) ----------
    def preparar(self, al_paso=None):
        """Baja el Linux ligero (si no está), crea la llave de Kira, la semilla y su disco. Deja la foto «nueva»."""
        paso = al_paso or (lambda *_a: None)
        os.makedirs(self.base, exist_ok=True)
        os.chmod(self.base, 0o700)
        for prog in ("qemu-img", "qemu-system-x86_64", "ssh", "ssh-keygen"):
            if not self._which(prog):
                raise MaquinaError(f"Falta «{prog}». Vuelve a pasar el instalador de Kira del portátil.")
        img = self.imagen()
        if not img:
            for nombre, url in IMAGENES:
                paso(0.1, f"Bajo el Linux ligero ({nombre}, ~350 MB)…")
                c, s = self._run(["curl", "-fL", "--retry", "3", "-C", "-", "-o", self._j(nombre + ".parte"), url],
                                 timeout=3600)
                if c == 0 and os.path.isfile(self._j(nombre + ".parte")):
                    os.replace(self._j(nombre + ".parte"), self._j(nombre))
                    img = self._j(nombre)
                    break
            if not img:
                raise MaquinaError("No pude bajar el Linux de la máquina. ¿Hay internet en el portátil?")
        if not os.path.isfile(self._j("clave")):
            paso(0.5, "Creo la llave de Kira para entrar en su máquina…")
            c, s = self._run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "kira-maquina",
                              "-f", self._j("clave")])
            if c != 0:
                raise MaquinaError("No pude crear la llave: " + s[-200:])
        with open(self._j("clave.pub"), encoding="utf-8") as f:
            pub = f.read().strip()
        paso(0.6, "Preparo su semilla (usuario y llave)…")
        with open(self._j("user-data"), "w", encoding="utf-8") as f:
            f.write(user_data(pub))
        with open(self._j("meta-data"), "w", encoding="utf-8") as f:
            f.write(meta_data())
        if self._which("cloud-localds"):
            c, s = self._run(["cloud-localds", self._j("semilla.iso"), self._j("user-data"), self._j("meta-data")])
        else:
            c, s = self._run(["genisoimage", "-quiet", "-output", self._j("semilla.iso"), "-volid", "cidata",
                              "-joliet", "-rock", self._j("user-data"), self._j("meta-data")])
        if c != 0:
            raise MaquinaError("No pude crear la semilla de la máquina: " + s[-200:])
        if not os.path.isfile(self._j("kira.qcow2")):
            paso(0.8, "Creo su disco (la imagen original no se toca)…")
            c, s = self._run(["qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", img, self._j("kira.qcow2"),
                              f"{DISCO_GB}G"])
            if c != 0:
                raise MaquinaError("No pude crear su disco: " + s[-200:])
        paso(1.0, "Lista.")
        return ("Mi máquina virtual está preparada: un Linux ligero (Debian) con 1 GB de memoria, sin internet y sin "
                "acceso a tus archivos. Dime «arranca tu máquina».")

    # ---------- encender / apagar ----------
    def encender(self, red=False, al_paso=None, espera=240):
        paso = al_paso or (lambda *_a: None)
        if not self.preparada():
            self.preparar(al_paso)
        if self.encendida():
            return "Mi máquina ya está encendida."
        kvm = self.kvm()
        paso(0.1, "Enciendo mi máquina" + ("" if kvm else " (sin aceleración: irá lenta)") + "…")
        c, s = self._run(orden_qemu(self.base, kvm=kvm, memoria=self.memoria, red=red))
        if c != 0:
            raise MaquinaError("QEMU no arrancó: " + s.strip()[-300:])
        primera = not os.path.isfile(self._j("arrancada.ok"))
        fin = self._reloj() + espera
        while self._reloj() < fin:
            c, _ = self._run(orden_ssh(self.base, espera=5) + ["true"], timeout=20)
            if c == 0:
                break
            paso(0.4, "Esperando a que arranque…")
            self._dormir(4)
        else:
            raise MaquinaError("Encendió, pero no me deja entrar todavía. Prueba «estado de tu máquina» en un rato.")
        if primera:
            open(self._j("arrancada.ok"), "w").close()
            try:
                self.foto(FOTO_NUEVA)            # para «deja tu máquina como nueva»
            except MaquinaError:
                pass
        self._log(f"\n=== máquina encendida {time.strftime('%d/%m %H:%M')} ({'con' if red else 'sin'} internet) ===")
        aviso = "" if kvm else (" Ojo: va sin aceleración (KVM). Activa «Intel VT» / «Virtualization» en la BIOS (F2) "
                                "y irá mucho más rápida.")
        return ("Mi máquina está encendida " + ("CON internet" if red else "sin internet") + ". Dime «enséñame tu "
                "máquina» para verla." + aviso)

    def apagar(self, espera=60):
        if not self.encendida():
            return "Mi máquina ya estaba apagada."
        try:
            self.qmp("system_powerdown")
        except MaquinaError:
            pass
        fin = self._reloj() + espera
        while self._reloj() < fin and self.encendida():
            self._dormir(2)
        if self.encendida():
            try:
                self.qmp("quit")
            except MaquinaError:
                p = self.pid()
                if p:
                    try:
                        os.kill(p, 15)
                    except OSError:
                        pass
        self._log(f"=== máquina apagada {time.strftime('%d/%m %H:%M')} ===")
        return "Mi máquina está apagada."

    # ---------- QMP: hablar con QEMU mientras está encendida ----------
    def qmp(self, comando, argumentos=None, timeout=30):
        ruta = self._j("qmp.sock")
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect(ruta)
        except OSError as e:
            raise MaquinaError(f"No puedo hablar con la máquina: {e}")
        f = s.makefile("rwb")
        try:
            def leer():
                while True:
                    linea = f.readline()
                    if not linea:
                        raise MaquinaError("La máquina cortó la conversación.")
                    d = json.loads(linea.decode("utf-8"))
                    if "return" in d or "error" in d:
                        return d
            f.readline()                                        # saludo
            f.write(json.dumps({"execute": "qmp_capabilities"}).encode() + b"\n"); f.flush()
            leer()
            pet = {"execute": comando}
            if argumentos:
                pet["arguments"] = argumentos
            f.write(json.dumps(pet).encode() + b"\n"); f.flush()
            d = leer()
            if "error" in d:
                raise MaquinaError(d["error"].get("desc", "error de la máquina"))
            return d["return"]
        finally:
            try:
                f.close(); s.close()
            except OSError:
                pass

    def _monitor(self, linea):
        r = self.qmp("human-monitor-command", {"command-line": linea}, timeout=300)
        if isinstance(r, str) and re.search(r"error|could not|failed", r, re.I):
            raise MaquinaError(r.strip())
        return r

    # ---------- trabajar dentro ----------
    def ejecutar(self, comando, timeout=120, mostrar=True):
        """Ejecuta un comando de Linux dentro (como el usuario kira). Se ve en su pantalla. Devuelve (codigo, salida)."""
        if not self.encendida():
            raise MaquinaError("Mi máquina está apagada: dime «arranca tu máquina».")
        self._log(f"kira@maquina$ {comando}")
        c, s = self._run(orden_ssh(self.base) + ["bash", "-s"], entrada=guion_remoto(comando, mostrar), timeout=timeout)
        s = recortar(s)
        self._log(s + (f"[salió con código {c}]" if c else ""))
        return c, s

    def probar_python(self, codigo, timeout=120, mostrar=True):
        if not self.encendida():
            raise MaquinaError("Mi máquina está apagada: dime «arranca tu máquina».")
        self._log("kira@maquina$ python3 programa.py   # (mi programa)")
        c, s = self._run(orden_ssh(self.base) + ["bash", "-s"],
                         entrada=guion_remoto(codigo, mostrar, python=True), timeout=timeout)
        s = recortar(s)
        self._log(s + (f"[salió con código {c}]" if c else ""))
        return c, s

    def leer(self, ruta):
        ruta = str(ruta or "").strip()
        if not ruta or "\n" in ruta:
            raise MaquinaError("Dime qué archivo leer (por ejemplo /etc/hostname).")
        q = "'" + ruta.replace("'", "'\\''") + "'"
        return self.ejecutar(f"head -c 20000 -- {q}", mostrar=True)

    def estudiar(self, al_paso=None):
        """Mira (solo LEER) cómo es Linux por dentro. Devuelve [(titulo, explicacion, salida)]."""
        paso = al_paso or (lambda *_a: None)
        sal = []
        for i, (titulo, cmd, expl) in enumerate(ESTUDIO):
            paso(i / len(ESTUDIO), f"Miro {titulo}…")
            try:
                _c, s = self.ejecutar(cmd, timeout=60)
            except MaquinaError as e:
                s = f"(no pude: {e})"
            sal.append((titulo, expl, s))
        paso(1.0, "Estudiado.")
        return sal

    # ---------- fotos (volver atrás) ----------
    def foto(self, nombre=None):
        n = nombre_foto(nombre)
        if self.encendida():
            self._monitor(f"savevm {n}")
        else:
            c, s = self._run(["qemu-img", "snapshot", "-c", n, self._j("kira.qcow2")])
            if c != 0:
                raise MaquinaError("No pude hacer la foto: " + s[-200:])
        self._log(f"=== foto «{n}» ===")
        return n

    def volver(self, nombre):
        n = nombre_foto(nombre)
        if n not in [f["nombre"] for f in self.fotos()]:
            raise MaquinaError(f"No tengo ninguna foto llamada «{n}». Di «fotos de tu máquina».")
        if self.encendida():
            self._monitor(f"loadvm {n}")
        else:
            c, s = self._run(["qemu-img", "snapshot", "-a", n, self._j("kira.qcow2")])
            if c != 0:
                raise MaquinaError("No pude volver a esa foto: " + s[-200:])
        self._log(f"=== vuelta a la foto «{n}» ===")
        return n

    def fotos(self):
        if not os.path.isfile(self._j("kira.qcow2")):
            return []
        c, s = self._run(["qemu-img", "info", "-U", "--output=json", self._j("kira.qcow2")])
        return fotos_de_info(s) if c == 0 else []

    def como_nueva(self):
        """Vuelve a la foto «nueva» (el primer arranque). Si no existe, rehace su disco desde la imagen original."""
        if FOTO_NUEVA in [f["nombre"] for f in self.fotos()]:
            self.volver(FOTO_NUEVA)
            return "Mi máquina vuelve a estar como el primer día."
        if self.encendida():
            self.apagar()
        img = self.imagen()
        if not img:
            raise MaquinaError("Todavía no está preparada: «prepara tu máquina».")
        try:
            os.remove(self._j("kira.qcow2"))
        except OSError:
            pass
        for n in ("arrancada.ok",):
            try:
                os.remove(self._j(n))
            except OSError:
                pass
        c, s = self._run(["qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", img, self._j("kira.qcow2"),
                          f"{DISCO_GB}G"])
        if c != 0:
            raise MaquinaError("No pude rehacer su disco: " + s[-200:])
        return "Su disco está como recién hecho. Dime «arranca tu máquina»."

    # ---------- verla ----------
    def ver(self, entorno=None, popen=subprocess.Popen):
        """Abre en la pantalla del portátil la ventana de la máquina (VNC) y el registro de lo que hace Kira."""
        if not self.encendida():
            raise MaquinaError("Mi máquina está apagada: dime «arranca tu máquina».")
        env = dict(entorno if entorno is not None else os.environ)
        if not env.get("DISPLAY"):                   # desde el servicio: la pantalla del portátil es la :0
            env["DISPLAY"] = ":0"
            env.setdefault("XAUTHORITY", os.path.expanduser("~/.Xauthority"))
        abiertos = []
        visor = next((v for v in ("vncviewer", "gvncviewer", "remmina") if self._which(v)), None)
        if visor:
            arg = {"vncviewer": f"127.0.0.1::{5900 + PANTALLA_VNC}", "gvncviewer": f"127.0.0.1:{PANTALLA_VNC}",
                   "remmina": f"vnc://127.0.0.1:{5900 + PANTALLA_VNC}"}[visor]
            try:
                popen([visor, arg], env=env, start_new_session=True,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                abiertos.append("su pantalla")
            except OSError:
                pass
        term = next((t for t in ("xfce4-terminal", "x-terminal-emulator", "gnome-terminal") if self._which(t)), None)
        if term:
            log = self._j("maquina.log")
            open(log, "a").close()
            try:
                popen([term, "-T", "Kira trabajando en su máquina", "-e", f"tail -n 40 -F {log}"], env=env,
                      start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                abiertos.append("lo que voy haciendo")
            except OSError:
                pass
        if not abiertos:
            raise MaquinaError(f"No encuentro un visor. En el portátil: «vncviewer 127.0.0.1::{5900 + PANTALLA_VNC}».")
        return "En la pantalla del portátil te abro " + " y ".join(abiertos) + "."

    def estado(self):
        enc = self.encendida()
        f = self.fotos()
        t = ("Mi máquina está ENCENDIDA" if enc else ("Mi máquina está apagada" if self.preparada()
                                                     else "Todavía no tengo máquina: «prepara tu máquina»"))
        if self.preparada():
            t += f" · Linux ligero, {self.memoria} MB · " + ("con KVM (rápida)" if self.kvm() else "sin KVM (lenta)")
            t += f" · {len(f)} foto(s)" + (": " + ", ".join(x["nombre"] for x in f[-5:]) if f else "")
        return t + "."


# =====================================================================================
#  LAS ÓRDENES (las usa nucleo_portatil y la línea de órdenes)
# =====================================================================================
def hacer(maquina, accion, carga="", al_paso=None, guardar_ficha=None):
    """Hace la orden y devuelve {texto, …}. `guardar_ficha(tema, texto)` guarda lo estudiado en el baúl."""
    m = maquina
    if accion == "preparar":
        return {"texto": m.preparar(al_paso)}
    if accion == "encender":
        return {"texto": m.encender(red=(carga == "red"), al_paso=al_paso)}
    if accion == "apagar":
        return {"texto": m.apagar()}
    if accion == "ver":
        return {"texto": m.ver()}
    if accion == "ejecutar":
        c, s = m.ejecutar(carga)
        return {"texto": f"En mi máquina, «{carga}»" + (" salió bien" if c == 0 else f" salió con código {c}") +
                         ":\n" + (s.strip() or "(sin salida)")}
    if accion == "leer":
        c, s = m.leer(carga)
        return {"texto": (s.strip() or "(vacío)") if c == 0 else f"No pude leer «{carga}»: {s.strip()[-300:]}"}
    if accion == "probar":
        if not m.ultimo_codigo:
            return {"texto": "No tengo ningún programa reciente. Pídeme uno («escríbeme un programa que…») y luego "
                             "«prueba el programa en tu máquina»."}
        c, s = m.probar_python(m.ultimo_codigo)
        return {"texto": ("Lo he probado en mi máquina y funciona" if c == 0 else
                          f"Lo he probado en mi máquina y falló (código {c})") + ":\n" + (s.strip() or "(sin salida)")}
    if accion == "estudiar":
        r = m.estudiar(al_paso)
        guardadas = 0
        for tema, texto in ficha_estudio(r):
            if guardar_ficha:
                try:
                    guardar_ficha(tema, texto)
                    guardadas += 1
                except Exception:
                    pass
        resumen = "\n".join(f"· {t}: {e}" for t, e, _s in r)
        return {"texto": f"He estudiado cómo funciona Linux por dentro en mi máquina ({len(r)} cosas"
                         + (f", {guardadas} fichas en mi baúl" if guardadas else "") + "):\n" + resumen +
                         "\nCuando piense, me preguntaré por ellas."}
    if accion == "foto":
        return {"texto": f"Foto hecha: «{m.foto(carga or None)}». Para volver: «vuelve a la foto …»."}
    if accion == "volver":
        return {"texto": f"Mi máquina ha vuelto a la foto «{m.volver(carga)}»."}
    if accion == "fotos":
        f = m.fotos()
        return {"texto": ("Fotos de mi máquina:\n" + "\n".join(f"· {x['nombre']} ({x['fecha']})" for x in f))
                if f else "Mi máquina aún no tiene fotos."}
    if accion == "estado":
        return {"texto": m.estado()}
    if accion == "nueva":
        return {"texto": m.como_nueva()}
    raise MaquinaError("No sé hacer eso con mi máquina.")


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="La máquina virtual de Kira (Linux ligero)")
    ap.add_argument("--preparar", action="store_true")
    ap.add_argument("--encender", action="store_true")
    ap.add_argument("--con-internet", action="store_true")
    ap.add_argument("--apagar", action="store_true")
    ap.add_argument("--ver", action="store_true")
    ap.add_argument("--estado", action="store_true")
    ap.add_argument("--ejecutar", metavar="COMANDO")
    a = ap.parse_args(argv)
    m = Maquina()
    try:
        if a.preparar:
            print(m.preparar(lambda _f, t: print("·", t)))
        if a.encender:
            print(m.encender(red=a.con_internet, al_paso=lambda _f, t: print("·", t)))
        if a.ejecutar:
            print(m.ejecutar(a.ejecutar)[1])
        if a.ver:
            if not m.encendida():
                print(m.encender(al_paso=lambda _f, t: print("·", t)))
            print(m.ver())
        if a.apagar:
            print(m.apagar())
        if a.estado or not any((a.preparar, a.encender, a.apagar, a.ver, a.ejecutar)):
            print(m.estado())
    except MaquinaError as e:
        sys.exit(f"[x] {e}")


if __name__ == "__main__":
    main()
