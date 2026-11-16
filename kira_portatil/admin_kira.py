#!/usr/bin/env python3
"""admin_kira.py — v3.93 (SOLO KiraOS, el portátil): Kira SUPERADMINISTRADORA, pero CON TU CONTRASEÑA.

El dueño eligió «contraseña en ventana»: Kira puede hacer cualquier cosa de administrador en Xubuntu, PERO antes de
cada una el propio Xubuntu (polkit, con `pkexec`) enseña una ventana con la orden EXACTA que va a ejecutar y pide TU
contraseña. La recuerda unos minutos (`auth_admin_keep`), así no te la pide cinco veces seguidas para lo mismo.

Por qué así (y no «root sin preguntar»): la contraseña la escribes TÚ en una ventana del sistema, que ningún programa
puede rellenar por ti. Ni un programa malo bajado de internet ni un fallo del cerebro de Kira pueden hacerse
administradores a escondidas.

Reglas (no cambian):
  · SOLO cuando tú se lo pides (una orden tuya en la barra del portátil). Mientras piensa/estudia/experimenta sola,
    NUNCA: el pensar no llega aquí.
  · SOLO en la pantalla del portátil (necesita tu sesión para enseñar la ventana): ni desde el móvil, ni por la red,
    ni por Tailscale.
  · Argumentos en lista, sin shell. No vale lanzar intérpretes (bash, python…) ni «envoltorios» (env, xargs…) como
    administrador: la ventana tiene que enseñar lo que de verdad se hace.
  · Kira NUNCA escribe discos (dd, mkfs, fdisk, parted, wipefs…), ni borra carpetas del sistema enteras, ni cambia
    contraseñas ni borra tu usuario.
  · Todo queda apuntado en ~/kira_portatil/admin.log (0600) y, con el ayudante instalado, en /var/log/kira-admin.log.

Para que la ventana diga «Kira quiere ejecutar como administrador: …» y recuerde la contraseña unos minutos, hay que
activar UNA vez el ayudante (`kira-admin-activar` o «bash modo_admin»). Sin él, funciona igual con el pkexec de
Xubuntu, pero pide la contraseña cada vez.
"""
import os
import re
import shlex
import shutil
import subprocess
import time
import unicodedata

AYUDANTE = os.environ.get("KIRA_ADMIN_AYUDANTE", "/usr/local/bin/kira-admin")
POLITICA = os.environ.get("KIRA_ADMIN_POLITICA", "/usr/share/polkit-1/actions/org.kira.admin.policy")
REGISTRO = os.environ.get("KIRA_ADMIN_LOG", os.path.expanduser("~/kira_portatil/admin.log"))
ACCION = "org.kira.admin"

# lo que NUNCA se ejecuta como administrador (también lo comprueba el ayudante, por si acaso)
INTERPRETES = {"bash", "sh", "dash", "zsh", "fish", "ksh", "csh", "tcsh", "su", "sudo", "pkexec", "doas", "env",
               "xargs", "nohup", "setsid", "nice", "ionice", "chroot", "script", "busybox", "python", "python2",
               "python3", "perl", "ruby", "node", "nodejs", "php", "lua", "tclsh", "expect", "screen", "tmux",
               "find", "awk", "gawk", "mawk", "sed", "vim", "vi", "nano", "less", "more", "man", "watch", "timeout"}
DISCOS = {"dd", "mkfs", "wipefs", "fdisk", "sfdisk", "cfdisk", "parted", "gparted", "gdisk", "sgdisk", "cgdisk",
          "shred", "blkdiscard", "mkswap", "badblocks", "hdparm", "sdparm", "cryptsetup", "mke2fs", "tune2fs",
          "e2fsck", "fsck", "losetup", "mdadm", "pvcreate", "vgcreate", "lvcreate", "lvremove", "vgremove",
          "pvremove", "dmsetup", "zpool", "zfs", "btrfs", "nvme", "flashrom", "efibootmgr", "grub-install"}
CUENTAS = {"passwd", "chpasswd", "userdel", "deluser", "usermod", "chage", "vipw", "vigr", "visudo"}
SISTEMA = {"/", "/etc", "/usr", "/home", "/boot", "/bin", "/sbin", "/lib", "/lib32", "/lib64", "/libx32", "/var",
           "/opt", "/root", "/srv", "/proc", "/sys", "/dev", "/run", "/snap", "/media", "/mnt"}
_RARO = re.compile(r"[;&|<>`]|\$\(|\$\{")


class AdminError(Exception):
    pass


def _sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t or "")) if unicodedata.category(c) != "Mn").lower()


def _base(prog):
    b = os.path.basename(str(prog or ""))
    return "mkfs" if b.startswith("mkfs.") else b


def validar(args):
    """Comprueba UNA orden (lista). Devuelve la lista limpia o lanza AdminError con el motivo en español."""
    if not isinstance(args, (list, tuple)) or not args:
        raise AdminError("no hay ninguna orden")
    args = [str(a) for a in args]
    if any("\n" in a or "\x00" in a for a in args):
        raise AdminError("la orden trae saltos de línea raros")
    if any(_RARO.search(a) for a in args):
        raise AdminError("la orden trae signos de shell (| ; & > < $( `): aquí cada cosa va por separado, sin shell")
    b = _base(args[0])
    if b in INTERPRETES or re.match(r"^(python|perl|ruby|php|lua)\d", b):
        raise AdminError(f"no ejecuto «{b}» como administrador: con eso la ventana no enseñaría lo que de verdad se hace")
    if b in DISCOS:
        raise AdminError(f"«{b}» escribe o formatea discos y eso no lo hago nunca (si hace falta, hazlo tú a mano)")
    if b in CUENTAS:
        raise AdminError(f"«{b}» cambia contraseñas o cuentas de usuario y eso no lo hago")
    if b == "rm":
        recursivo = any(a.startswith("-") and not a.startswith("--") and ("r" in a or "R" in a) for a in args[1:]) \
            or "--recursive" in args or "--no-preserve-root" in args
        for a in args[1:]:
            if a.startswith("-"):
                continue
            ruta = os.path.normpath(a) if a.startswith("/") else a
            if ruta in SISTEMA or ruta.rstrip("/") == "" or (recursivo and ruta.startswith("/") and ruta.count("/") <= 2):
                raise AdminError(f"no borro «{a}»: es una carpeta del sistema")
    if b in ("chmod", "chown", "chgrp") and any(a in ("-R", "--recursive") or (a.startswith("-") and "R" in a)
                                                for a in args[1:]):
        for a in args[1:]:
            if not a.startswith("-") and os.path.normpath(a) in SISTEMA:
                raise AdminError(f"no cambio los permisos de «{a}» entero: rompería el sistema")
    return args


# ---------------- entender la orden del dueño ----------------
_ADMIN = r"(?:administrador|administradora|admin|root|superusuario|super\s*admin\w*|sudo)"
_ORDEN = re.compile(
    rf"^\s*(?:kira[\s,]+)?(?:(?:ejecuta|ejecutame|haz|hazme|lanza|corre|pon)\s+)?"
    rf"(?:como|con\s+permisos?\s+de|en\s+modo)\s+{_ADMIN}\s*[:,]?\s+(?P<cmd>.+)$")
_ORDEN_SUDO = re.compile(r"^\s*(?:kira[\s,]+)?sudo\s+(?P<cmd>[a-z0-9].+)$")
_ORDEN_FIN = re.compile(rf"^\s*(?:kira[\s,]+)?(?P<cmd>.+?)\s*,?\s+(?:como|con\s+permisos?\s+de)\s+{_ADMIN}\s*\.?\s*$")
_VER = re.compile(rf"(que|lo que)\s+(has\s+hecho|hiciste)\s+(como\s+{_ADMIN}|de\s+{_ADMIN})|registro\s+de(l)?\s+{_ADMIN}"
                  rf"|tus\s+ordenes\s+de\s+{_ADMIN}")
_ESTADO = re.compile(rf"(estado|como\s+va|esta\s+activ\w+)\s+(el\s+|del\s+|de\s+)?(modo\s+)?{_ADMIN}"
                     rf"|activa(r)?\s+(el\s+)?modo\s+{_ADMIN}|modo\s+{_ADMIN}\s*\??$")


def traducir(frase):
    """Frases normales → órdenes de verdad. Devuelve una LISTA de órdenes (cada una, lista) o None."""
    f = _sin_tildes(frase).strip().rstrip(".?!")
    f = re.sub(r"^(por\s+favor\s+|porfa\s+)", "", f)
    paquetes = r"(?:el\s+|la\s+|los\s+|las\s+)?(?:programas?\s+|paquetes?\s+|aplicacion(?:es)?\s+|app\s+)?"
    m = re.match(rf"^(?:instala(?:me)?|instalar)\s+{paquetes}(?P<p>[a-z0-9][a-z0-9+.\- ]*)$", f)
    if m:
        ps = [p for p in re.split(r"[\s,]+|\by\b", m.group("p")) if p and p != "y"]
        if ps and all(re.match(r"^[a-z0-9][a-z0-9+.\-]{0,80}$", p) for p in ps):
            return [["apt-get", "install", "-y"] + ps]
    m = re.match(rf"^(?:desinstala(?:me)?|quita|borra|elimina)\s+{paquetes}(?P<p>[a-z0-9][a-z0-9+.\-]*)$", f)
    if m:
        return [["apt-get", "remove", "-y", m.group("p")]]
    if re.match(r"^(actualiza(?:me)?|pon\s+al\s+dia)\s+(el\s+sistema|xubuntu|ubuntu|linux|todo|los\s+programas)$", f):
        return [["apt-get", "update"], ["apt-get", "upgrade", "-y"]]
    if re.match(r"^(actualiza|refresca)\s+(la\s+)?lista\s+de\s+(programas|paquetes)$", f):
        return [["apt-get", "update"]]
    if re.match(r"^(limpia|arregla)\s+(los\s+)?(programas|paquetes)(\s+rotos)?$", f):
        return [["apt-get", "-f", "install", "-y"], ["apt-get", "autoremove", "-y"]]
    m = re.match(r"^(reinicia|enciende|arranca|para|apaga|deten)\s+el\s+servicio\s+(?P<s>[a-z0-9@._\-]+)$", f)
    if m:
        v = {"reinicia": "restart", "enciende": "start", "arranca": "start", "para": "stop", "apaga": "stop",
             "deten": "stop"}[m.group(1)]
        return [["systemctl", v, m.group("s")]]
    return None


def _partir(cmd):
    try:
        partes = shlex.split(cmd)
    except ValueError:
        return None
    return partes or None


def orden(texto):
    """¿Es una orden de administrador? Devuelve ("ejecutar", [ordenes]) / ("ver", None) / ("estado", None) / None.
    PURO (salvo mirar qué programas existen, con `which`)."""
    t = str(texto or "").strip()
    if not t:
        return None
    s = _sin_tildes(t)
    if _VER.search(s):
        return ("ver", None)
    if _ESTADO.search(s):
        return ("estado", None)
    cmd, al_final = None, False
    for rx in (_ORDEN, _ORDEN_SUDO, _ORDEN_FIN):
        m = rx.match(s)
        if m:
            # la orden con su forma original (mayúsculas, rutas), si el texto conserva las mismas posiciones
            cmd = t[m.start("cmd"):m.end("cmd")] if len(s) == len(t) else m.group("cmd")
            al_final = rx is _ORDEN_FIN
            break
    if not cmd:
        return None
    cmd = cmd.strip().rstrip(".")
    tr = traducir(cmd)
    if tr:
        return ("ejecutar", tr)
    partes = _partir(cmd)
    if not partes:
        return None
    if not re.match(r"^[A-Za-z0-9/][A-Za-z0-9._+/\-]*$", partes[0]):
        return None
    if not partes[0].startswith("/") and shutil.which(partes[0]) is None:
        # «… como administrador» al final de una frase normal («estudia linux como administrador») no es una orden
        return None if al_final else ("desconocida", [partes])
    return ("ejecutar", [partes])


# ---------------- ejecutar ----------------
def _correr_defecto(args, timeout=1800):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    return p.returncode, p.stdout or ""


def ayudante_activo():
    """¿Está el ayudante de Kira (ventana con «Kira quiere…» y contraseña recordada unos minutos)?"""
    return os.access(AYUDANTE, os.X_OK) and os.path.isfile(POLITICA)


def puede_preguntar():
    """¿Puedo enseñarte la ventana de la contraseña? Solo en la pantalla del portátil, con pkexec y con tu sesión."""
    return bool(os.environ.get("KIRA_ADMIN_PANTALLA") == "1" and os.environ.get("DISPLAY")
                and shutil.which(os.environ.get("KIRA_PKEXEC", "pkexec")))


def _permiso_paquetes(args, correr):
    """El permiso de la v3.33 (apt/dpkg sin contraseña): para instalar paquetes no hace falta la ventana."""
    if _base(args[0]) not in ("apt-get", "apt", "dpkg", "aptitude"):
        return False
    try:
        rc, _s = correr(["sudo", "-n", "true"], timeout=10)
        return rc == 0
    except Exception:                                 # noqa: BLE001
        return False


def linea_de_orden(args, correr=None):
    """La línea que se ejecuta de verdad (con pkexec y el ayudante, o con el permiso de paquetes)."""
    correr = correr or _correr_defecto
    if _permiso_paquetes(args, correr):
        return ["sudo", "-n"] + list(args), "permiso"
    prog = args[0] if args[0].startswith("/") else (shutil.which(args[0]) or args[0])
    pk = os.environ.get("KIRA_PKEXEC", "pkexec")
    if ayudante_activo():
        return [pk, AYUDANTE, prog] + list(args[1:]), "ventana"
    return [pk, prog] + list(args[1:]), "ventana"


def _tapar(t):
    try:
        import ordenes_kira
        return ordenes_kira.ocultar_claves(t)
    except Exception:                                 # noqa: BLE001
        return t


def apuntar(args, rc, salida, ruta=None):
    ruta = ruta or REGISTRO
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        nuevo = not os.path.exists(ruta)
        with open(ruta, "a", encoding="utf-8") as f:
            ult = " | ".join(x.strip() for x in str(salida or "").strip().splitlines()[-2:])[:200]
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  rc={rc}  {_tapar(' '.join(shlex.quote(a) for a in args))}"
                    f"{('  → ' + _tapar(ult)) if ult else ''}\n")
        if nuevo:
            os.chmod(ruta, 0o600)
    except OSError:
        pass


def ejecutar(ordenes, correr=None, al_paso=None, ruta=None):
    """Ejecuta las órdenes UNA tras otra, cada una con tu contraseña en la ventana de Xubuntu (o con el permiso de
    paquetes ya dado). Para en cuanto una falla o la cancelas. Devuelve {ok, texto, hechas, cancelada}."""
    correr = correr or _correr_defecto
    paso = al_paso or (lambda _t: None)
    limpias = []
    for o in ordenes or []:
        try:
            limpias.append(validar(o))
        except AdminError as e:
            return {"ok": False, "cancelada": False, "hechas": 0,
                    "texto": f"No lo hago como administrador: {e}. (Orden: {' '.join(map(str, o))})"}
    if not limpias:
        return {"ok": False, "cancelada": False, "hechas": 0, "texto": "No hay ninguna orden que hacer."}
    hechas, trozos = 0, []
    for o in limpias:
        linea, como = linea_de_orden(o, correr)
        paso(("Xubuntu te pide la contraseña para: " if como == "ventana" else "Haciendo (con tu permiso de "
              "paquetes): ") + " ".join(o))
        try:
            rc, salida = correr(linea, timeout=1800)
        except subprocess.TimeoutExpired:
            rc, salida = 124, "tardó demasiado (30 min)"
        except FileNotFoundError:
            rc, salida = 127, "no encuentro pkexec"
        except Exception as e:                        # noqa: BLE001
            rc, salida = 1, str(e)
        apuntar(o, rc, salida, ruta)
        if como == "ventana" and rc == 126:
            trozos.append(f"«{' '.join(o)}»: NO lo he hecho (cancelaste la ventana o la contraseña no era la buena).")
            return {"ok": False, "cancelada": True, "hechas": hechas, "texto": "\n".join(trozos)}
        if como == "ventana" and rc == 127 and ("authentication agent" in salida.lower() or "pkexec" in salida.lower()
                                                or not salida.strip()):
            trozos.append("No he podido enseñarte la ventana de la contraseña (falta el «agente» de polkit de Xubuntu "
                          "en esta sesión). Activa el modo administrador una vez: «kira-admin-activar» en la Terminal.")
            return {"ok": False, "cancelada": False, "hechas": hechas, "texto": "\n".join(trozos)}
        ult = "\n".join(salida.strip().splitlines()[-6:])
        if rc != 0:
            trozos.append(f"«{' '.join(o)}» falló (código {rc}). Dijo:\n{_tapar(ult)}")
            return {"ok": False, "cancelada": False, "hechas": hechas, "texto": "\n".join(trozos)}
        hechas += 1
        trozos.append(f"Hecho como administrador: {' '.join(o)}" + (f"\n{_tapar(ult)}" if ult else ""))
    return {"ok": True, "cancelada": False, "hechas": hechas, "texto": "\n".join(trozos)}


def leer_registro(n=25, ruta=None):
    ruta = ruta or REGISTRO
    try:
        with open(ruta, encoding="utf-8") as f:
            lineas = f.read().splitlines()
    except OSError:
        return "Todavía no he hecho nada como administrador."
    if not lineas:
        return "Todavía no he hecho nada como administrador."
    return "Lo último que he hecho como administrador (con tu contraseña):\n" + "\n".join(lineas[-n:])


def texto_estado():
    t = []
    if ayudante_activo():
        t.append("Modo administrador ACTIVADO: antes de cada cosa de administrador, Xubuntu te enseña la orden en una "
                 "ventana y te pide la contraseña; la recuerda unos minutos.")
    else:
        t.append("El modo administrador funciona con el pkexec de Xubuntu (te pedirá la contraseña CADA vez). Para que "
                 "la ventana diga qué quiere hacer Kira y la recuerde unos minutos, actívalo una vez: escribe "
                 "kira-admin-activar en la Terminal (o el botón «Activar el modo administrador» de Ajustes).")
    if not shutil.which(os.environ.get("KIRA_PKEXEC", "pkexec")):
        t.append("Ojo: no encuentro pkexec en este sistema (paquete «pkexec» o «policykit-1»).")
    t.append("Pídemelo así: «ejecuta como administrador apt update», «instala vlc como administrador», «reinicia el "
             "servicio ssh como administrador». Lo que he hecho: «qué has hecho como administrador».")
    return "\n".join(t)


def hacer(o, correr=None, al_paso=None, ruta=None):
    """Atiende la orden ya reconocida (desde la PANTALLA). Devuelve el texto para el dueño."""
    tipo, ords = o
    if tipo == "ver":
        return leer_registro(ruta=ruta)
    if tipo == "estado":
        return texto_estado()
    if tipo == "desconocida":
        return (f"No encuentro el programa «{ords[0][0]}» en este portátil, así que no puedo ejecutarlo como "
                "administrador. Si es un paquete, dime «instala " + ords[0][0] + " como administrador».")
    if not puede_preguntar():
        return ("Para hacer algo como administrador necesito enseñarte la ventana de la contraseña de Xubuntu, y eso "
                "solo se puede en la pantalla del portátil (no desde el móvil ni por la red). Pídemelo en la barra de "
                "KiraOS.")
    r = ejecutar(ords, correr=correr, al_paso=al_paso, ruta=ruta)
    return r["texto"]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--registro":
        print(leer_registro())
    else:
        print(texto_estado())
