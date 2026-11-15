# -*- coding: utf-8 -*-
"""
taller_programas_kira.py - v3.76: Kira TRABAJA con un programa de órdenes mientras tú lo ves (solo KiraOS).

Lo pidió el dueño: «que ese botón abra una aplicación, programa o herramienta, abra una ventana con ese programa, y
Kira trabaje lo que se puede hacer en ese programa mientras yo veo en esa ventana lo que va haciendo». Eligió los
programas que se manejan con ÓRDENES ESCRITAS (git, python, ffmpeg, convert, nmap, pandoc…), que es lo fiable.

Cómo va:
  1. «trabaja con ffmpeg: convierte video.mp4 a mp3» (o un botón que dé esa orden) → Kira lee la ayuda del programa
     (`prog --help`, sin pantalla y con tiempo) y su cerebro escribe un PLAN de órdenes (como mucho 8).
  2. Se abre la ventana «Taller»: ves el programa, la carpeta de trabajo y cada orden del plan. NO ejecuta nada aún.
  3. Pulsas «Hazlo» (dos toques) → ejecuta las órdenes una a una y ves EN VIVO cada orden y lo que contesta el
     programa. «Parar» la corta al momento.

Candados (nada de esto se salta):
  - cada orden tiene que empezar por ESE programa; nada de tuberías, «;», «&&», redirecciones, «$(…)» ni comillas
    raras; los argumentos en lista (sin shell);
  - programas que nunca: administrador (sudo, su, pkexec…), shells (bash, sh…), borrar/formatear/apagar (rm, dd,
    mkfs, shutdown, systemctl, kill…);
  - rutas: solo dentro de tu carpeta personal o /tmp, nunca «..»;
  - se ejecuta en `~/kira_portatil/taller/<programa>/` con tu usuario, con tiempo máximo y salida acotada;
  - vive en el proceso de la pantalla del portátil (como la Terminal): no se puede pedir desde la red ni el móvil.
"""
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import threading
import time

MAX_ORDENES = 8
MAX_REGISTRO = 400
TIEMPO_ORDEN = 180
MAX_AYUDA = 3500
PROHIBIDOS = {"sudo", "su", "doas", "pkexec", "bash", "sh", "zsh", "dash", "fish", "ksh", "csh", "tcsh", "rm",
              "rmdir", "dd", "shred", "mkfs", "fdisk", "parted", "gdisk", "wipefs", "shutdown", "reboot", "poweroff",
              "halt", "init", "telinit", "systemctl", "service", "passwd", "chpasswd", "useradd", "userdel", "usermod",
              "chown", "chmod", "chgrp", "kill", "killall", "pkill", "mount", "umount", "crontab", "at", "env",
              "nohup", "setsid", "xargs", "eval", "exec", "apt", "apt-get", "dpkg", "snap", "flatpak", "insmod",
              "rmmod", "modprobe", "iptables", "ufw", "nft"}
_RARO = re.compile(r"[|;&<>`\n\r]|\$\(|\$\{")


def base():
    return os.environ.get("KIRA_TALLER") or os.path.expanduser("~/kira_portatil/taller")


def _ruta_sesion():
    return os.path.join(base(), "sesion.json")


def _limpio(t, n=200):
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", str(t or "")).strip()[:n]


def _plano(t):
    import unicodedata
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# ------------------------------------------------------------------ v3.76: también los programas que DESCARGASTE
def dir_datos():
    return os.environ.get("KIRA_DATOS_NUCLEO") or os.path.expanduser("~/kira_portatil/kira_datos")


def descargados(datos=None):
    """Las apps/herramientas que Kira te instaló (GitHub, AppImage, .deb extraído…), con su forma de arrancarlas."""
    try:
        import accesos_kira as ak
        return [a for a in ak.listar(datos or dir_datos()) if a.get("tipo") == "externa" and a.get("lanzar")]
    except Exception:                                     # noqa: BLE001
        return []


def _clave(t):
    return re.sub(r"[^a-z0-9]", "", _plano(t))


def resolver(prog, datos=None):
    """(nombre, lanzar) del programa: uno instalado en el sistema (PATH) o uno que descargaste. None si no lo hay."""
    prog = str(prog or "").strip()
    if not prog:
        return None
    exe = shutil.which(prog)
    if exe:
        return os.path.basename(prog), [exe]
    k = _clave(prog)
    lista = descargados(datos)
    for a in lista:
        if _clave(a.get("titulo")) == k:
            return prog, list(a["lanzar"])
    for a in lista:
        ka = _clave(a.get("titulo"))
        if k and ka and (k in ka or ka in k):
            return prog, list(a["lanzar"])
    return None


# ------------------------------------------------------------------ la ORDEN
_ORDEN = [re.compile(r"^(?:kira[, ]+)?(?:ponte\s+a\s+)?trabaj(?:a|ar|e)\s+con\s+(?:el\s+programa\s+|la\s+herramienta\s+)?"
                     r"(?P<p>[a-z0-9][a-z0-9._+-]{0,40})\s*(?:[:,]|para|y)?\s*(?P<t>.*)$"),
          re.compile(r"^(?:kira[, ]+)?(?:abre\s+)?(?:el\s+)?taller\s+(?:de|con)\s+(?P<p>[a-z0-9][a-z0-9._+-]{0,40})"
                     r"\s*(?:[:,]|para|y)?\s*(?P<t>.*)$"),
          re.compile(r"^(?:kira[, ]+)?usa\s+(?:el\s+programa\s+|la\s+herramienta\s+)?(?P<p>[a-z0-9][a-z0-9._+-]{0,40})"
                     r"\s+para\s+(?P<t>.+)$")]


def orden(texto):
    """(programa, tarea) para «trabaja con X: …», «abre el taller de X», «usa X para …»; si no, None.
    «usa X para …» solo si X es un programa de órdenes que existe (si no, no se lo come a las apps)."""
    t = _plano(re.sub(r"\s+", " ", str(texto or "")).strip().rstrip(" .!?"))
    for i, rx in enumerate(_ORDEN):
        m = rx.match(t)
        if m:
            prog = m.group("p")
            if i == 2 and not resolver(prog):
                return None
            tarea = _limpio(m.group("t").strip(" ,:"), 400)
            orig = re.sub(r"\s+", " ", str(texto or "")).strip().rstrip(" .!?")
            mo = re.search(re.escape(prog) + r"\s*(?:[:,]|para|y)?\s*", orig, re.I)
            if mo and tarea:                               # la tarea con sus mayúsculas y tildes de verdad
                tarea = _limpio(orig[mo.end():], 400) or tarea
            return prog, tarea
    return None


def es_ver(texto):
    return bool(re.match(r"^(?:kira[, ]+)?(?:abre|ensename|muestrame|ver)\s+(?:el\s+)?taller$", _plano(texto).strip(" .!?")))


# ------------------------------------------------------------------ los CANDADOS
def prohibido(prog):
    n = os.path.basename(str(prog or "")).lower()
    return n in PROHIBIDOS or n.startswith("mkfs")


def validar_orden(cmd, prog, carpeta=None, lanzar=None):
    """Lista de argumentos lista para ejecutar, o lanza ValueError con el motivo (en español). Con `lanzar` (un
    programa que descargaste), el nombre del principio se cambia por su forma de arrancarlo."""
    cmd = str(cmd or "").strip()
    if cmd.startswith("$"):
        cmd = cmd[1:].strip()
    if not cmd:
        raise ValueError("orden vacía")
    if _RARO.search(cmd):
        raise ValueError("lleva tuberías, «;», «&», redirecciones o «$(…)»: no se permite")
    try:
        args = shlex.split(cmd)
    except ValueError as e:
        raise ValueError(f"no se entiende: {e}")
    if not args:
        raise ValueError("orden vacía")
    if _clave(os.path.basename(args[0])) != _clave(os.path.basename(prog)):
        raise ValueError(f"tiene que empezar por «{prog}» (empieza por «{args[0]}»)")
    if prohibido(args[0]):
        raise ValueError(f"«{args[0]}» no lo uso nunca desde aquí")
    casa = os.path.expanduser("~")
    for a in args[1:]:
        if ".." in a.replace("\\", "/").split("/"):
            raise ValueError("una ruta con «..» no se permite")
        r = os.path.expanduser(a) if a.startswith("~") else a
        if r.startswith("/") and not (r == casa or r.startswith(casa + "/") or r.startswith("/tmp/") or r == "/tmp"):
            raise ValueError(f"la ruta «{a}» está fuera de tu carpeta personal")
    args = [os.path.expanduser(a) if a.startswith("~") else a for a in args]
    if lanzar:
        return list(lanzar) + args[1:]
    exe = shutil.which(args[0])
    if not exe:
        raise ValueError(f"no tengo instalado «{args[0]}»")
    return [exe] + args[1:]


def ordenes_de(respuesta, prog, lanzar=None):
    """Saca del texto del cerebro las órdenes (líneas «$ prog …» o dentro de un bloque ``` ) y separa las malas."""
    lineas = []
    for l in str(respuesta or "").splitlines():
        s = l.strip()
        if s.startswith("```"):
            continue
        if s.startswith("$ "):
            s = s[2:].strip()
        elif not re.match(re.escape(os.path.basename(prog)) + r"(\s|$)", s, re.I):
            continue
        if s and s not in lineas:
            lineas.append(s)
    buenas, malas = [], []
    for s in lineas[:MAX_ORDENES * 2]:
        try:
            validar_orden(s, prog, lanzar=lanzar)
            buenas.append(s)
        except ValueError as e:
            malas.append((s, str(e)))
    return buenas[:MAX_ORDENES], malas


# ------------------------------------------------------------------ la AYUDA del programa
def ayuda(prog, correr=None, lanzar=None):
    """Lo que el programa dice de sí mismo (--help, o -h). Sin pantalla y con tiempo."""
    correr = correr or _correr
    for arg in ("--help", "-h"):
        try:
            r = correr(list(lanzar or [prog]) + [arg], 8)
        except Exception:                                 # noqa: BLE001
            continue
        if r and len(r.strip()) > 20:
            return r.strip()[:MAX_AYUDA]
    return ""


def _correr(args, tiempo):
    env = dict(os.environ)
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    p = subprocess.run(args, capture_output=True, text=True, timeout=tiempo, env=env, stdin=subprocess.DEVNULL)
    return (p.stdout or "") + (p.stderr or "")


SISTEMA_PLAN = ("Eres Kira y manejas programas de terminal en Linux (Xubuntu). Te doy un programa, su ayuda y una "
                "tarea. Escribe SOLO las órdenes para hacer la tarea, una por línea, empezando cada una por «$ » y por "
                "el nombre del programa. Como mucho 8. Sin tuberías, sin «;», sin «&&», sin redirecciones, sin sudo. "
                "Usa rutas relativas (trabajas en tu carpeta del taller). Si hace falta un archivo que no existe, "
                "dilo en una línea que empiece por «NOTA:». Nada más.")


def pedido_plan(prog, tarea, ayuda_txt, archivos):
    return (f"Programa: {prog}\nTarea: {tarea or 'enseña qué puede hacer este programa con un ejemplo sencillo'}\n"
            f"Archivos en la carpeta del taller: {', '.join(archivos) if archivos else '(ninguno)'}\n"
            f"Ayuda del programa (recortada):\n{ayuda_txt or '(no tiene ayuda)'}")


# ------------------------------------------------------------------ la SESIÓN (en disco: la ve la pantalla)
def carpeta_de(prog):
    c = os.path.join(base(), re.sub(r"[^a-z0-9._+-]", "_", os.path.basename(str(prog)).lower()) or "programa")
    os.makedirs(c, exist_ok=True)
    return c


def archivos(carpeta, maximo=30):
    try:
        return sorted(n for n in os.listdir(carpeta) if not n.startswith("."))[:maximo]
    except OSError:
        return []


def leer():
    try:
        with open(_ruta_sesion(), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar(d):
    os.makedirs(base(), exist_ok=True)
    ruta = _ruta_sesion()
    with open(ruta + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.chmod(ruta + ".tmp", 0o600)
    os.replace(ruta + ".tmp", ruta)


def preparar(prog, tarea, preguntar, correr=None, datos=None):
    """Lee la ayuda, pide el plan al cerebro y deja la sesión ESPERANDO tu «Hazlo». Devuelve (sesion, texto)."""
    if prohibido(prog):
        return None, f"[x] «{prog}» no lo manejo desde el taller (por seguridad: administrador, shells o cosas que borran)."
    r = resolver(prog, datos)
    if not r:
        return None, (f"[x] No tengo «{prog}» (ni en el sistema ni entre lo que me has hecho descargar). Si lo quieres, "
                      f"dime «instala {prog}» (te pido permiso) y luego «trabaja con {prog}: …».")
    nombre, lanzar = r
    descargado = not shutil.which(prog)
    carpeta = carpeta_de(prog)
    ay = ayuda(prog, correr, lanzar)
    resp = preguntar(SISTEMA_PLAN, pedido_plan(prog, tarea, ay, archivos(carpeta)))
    buenas, malas = ordenes_de(resp, prog, lanzar if descargado else None)
    notas = [_limpio(l.split(":", 1)[1], 200) for l in str(resp or "").splitlines() if l.strip().upper().startswith("NOTA:")]
    s = {"programa": os.path.basename(prog), "tarea": tarea, "carpeta": carpeta, "plan": buenas,
         "lanzar": lanzar if descargado else None, "descargado": descargado,
         "rechazadas": [{"orden": o, "por": p} for o, p in malas][:8], "notas": notas[:4],
         "estado": "esperando" if buenas else "sin plan", "registro": [], "cuando": time.time(), "actual": -1}
    guardar(s)
    if not buenas:
        return s, (f"[x] Mi cerebro no me ha dado ninguna orden válida para «{prog}»" +
                   (f" (rechacé {len(malas)} por seguridad)" if malas else "") + ". Dímelo con más detalle.")
    return s, (f"He preparado {len(buenas)} orden(es) de «{prog}» para: {tarea or 'enseñarte qué hace'}. Las tienes en la "
               "ventana Taller: míralas y pulsa «Hazlo» (dos toques) para que las ejecute; verás en vivo lo que va "
               "contestando el programa.")


# ------------------------------------------------------------------ EJECUTAR (en vivo)
class Obrero:
    """Ejecuta el plan de la sesión una orden tras otra y va escribiendo lo que sale en la sesión (la ventana lo lee)."""

    def __init__(self, popen=None):
        self.popen = popen or subprocess.Popen
        self.hilo = None
        self.proc = None
        self.parar_ya = False

    def ocupado(self):
        return self.hilo is not None and self.hilo.is_alive()

    def empezar(self):
        s = leer()
        if not s.get("plan"):
            return "No hay ningún plan preparado. Pídeme «trabaja con <programa>: <lo que quieres>»."
        if s.get("estado") == "trabajando" and self.ocupado():
            return "Ya estoy trabajando con él."
        self.parar_ya = False
        s.update(estado="trabajando", registro=[], actual=0, empezo=time.time())
        guardar(s)
        self.hilo = threading.Thread(target=self._trabajar, daemon=True)
        self.hilo.start()
        return f"Empiezo con «{s['programa']}»: míralo en la ventana."

    def parar(self):
        self.parar_ya = True
        p = self.proc
        if p is not None and p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except Exception:                             # noqa: BLE001
                try:
                    p.terminate()
                except Exception:                         # noqa: BLE001
                    pass
        return "Paro."

    def _apuntar(self, s, linea):
        s["registro"] = (s.get("registro") or []) + [_limpio(linea, 300)]
        s["registro"] = s["registro"][-MAX_REGISTRO:]

    def _trabajar(self):
        s = leer()
        prog, carpeta = s["programa"], s["carpeta"]
        bien = 0
        for i, cmd in enumerate(s["plan"]):
            if self.parar_ya:
                break
            s["actual"] = i
            self._apuntar(s, f"$ {cmd}")
            guardar(s)
            try:
                args = validar_orden(cmd, prog, carpeta, lanzar=s.get("lanzar"))
            except ValueError as e:
                self._apuntar(s, f"[x] No la ejecuto: {e}")
                guardar(s)
                continue
            try:
                env = dict(os.environ)
                env.pop("DISPLAY", None)
                self.proc = self.popen(args, cwd=carpeta, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL, text=True, env=env, start_new_session=True)
                limite = time.time() + TIEMPO_ORDEN
                ultima = 0.0
                for linea in self.proc.stdout:
                    self._apuntar(s, linea.rstrip("\n"))
                    if time.time() - ultima > 0.5:
                        guardar(s)
                        ultima = time.time()
                    if self.parar_ya or time.time() > limite:
                        self.parar()
                        self._apuntar(s, "[x] Cortada (" + ("la paraste" if self.parar_ya else "tardaba demasiado") + ").")
                        break
                codigo = self.proc.wait(timeout=10)
                if codigo == 0:
                    bien += 1
                    self._apuntar(s, "✓ bien")
                else:
                    self._apuntar(s, f"[x] terminó con error ({codigo})")
            except Exception as e:                        # noqa: BLE001
                self._apuntar(s, f"[x] No he podido ejecutarla: {e}")
            guardar(s)
        s["estado"] = "parado" if self.parar_ya else "hecho"
        s["actual"] = -1
        s["resumen"] = (f"{bien} de {len(s['plan'])} órdenes bien." + (" (La paraste.)" if self.parar_ya else ""))
        s["archivos"] = archivos(carpeta)
        self._apuntar(s, "— " + s["resumen"])
        guardar(s)
        self.proc = None


def texto_ventana(s):
    if not s:
        return ("Aquí trabajo con programas de órdenes (git, python, ffmpeg, convert, pandoc, nmap…) mientras tú miras.\n"
                "Pídemelo así: «trabaja con ffmpeg: convierte video.mp4 a mp3» o «usa convert para hacer pequeñas las "
                "fotos». También con los programas que me hayas hecho descargar (por su nombre). Los archivos los pones "
                "en kira_portatil/taller/<programa>/.")
    nombres = {"esperando": "ESPERANDO TU «HAZLO»", "trabajando": "TRABAJANDO…", "hecho": "TERMINADO",
               "parado": "PARADO", "sin plan": "SIN PLAN"}
    lin = [f"PROGRAMA: {s.get('programa')}" + (" (lo descargaste tú)" if s.get("descargado") else "") +
           f"   ·   {nombres.get(s.get('estado'), s.get('estado'))}",
           f"TAREA: {s.get('tarea') or '(enseñar qué hace)'}",
           f"CARPETA: {s.get('carpeta')}", "", "PLAN:"]
    for i, c in enumerate(s.get("plan") or []):
        marca = "▶ " if i == s.get("actual") else "  "
        lin.append(f"{marca}{i + 1}. {c}")
    for r in s.get("rechazadas") or []:
        lin.append(f"   (no la haré: {r['orden']} — {r['por']})")
    for n in s.get("notas") or []:
        lin.append(f"   Nota: {n}")
    if s.get("registro"):
        lin += ["", "LO QUE VA HACIENDO (en vivo):"] + list(s["registro"][-60:])
    if s.get("archivos") and s.get("estado") in ("hecho", "parado"):
        lin += ["", "ARCHIVOS EN LA CARPETA: " + ", ".join(s["archivos"])]
    return "\n".join(lin)
