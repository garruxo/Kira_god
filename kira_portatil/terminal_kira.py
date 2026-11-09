# -*- coding: utf-8 -*-
"""v3.17: la TERMINAL dentro de KiraOS — el dueño maneja Linux sin salir de Kira.

Es una terminal DE VERDAD (bash en un pseudo-terminal), con TU usuario, como la de Xubuntu:
- lo que escribes en la ventana «Terminal» del escritorio va a bash; lo que bash contesta sale en la ventana;
- `sudo` funciona: cuando pide la contraseña, la ventana cambia a puntitos (la contraseña no se guarda ni se enseña);
- «Ctrl+C» para cortar un programa, «Ctrl+D», limpiar y empezar de nuevo;
- solo vive en ESTE portátil: la abre la pantalla de Kira (pywebview, en el mismo programa). NO está en el
  servidor del núcleo ni se puede usar desde el móvil ni desde internet.
- Kira NO escribe aquí sola: lo que se ejecuta es lo que escribes tú.

Lo que NO hace (dicho claro): programas a pantalla completa como `nano`, `top` o `htop` necesitan una terminal
gráfica completa y aquí se verán mal (para eso: `cat`, `less` no, mejor `head`/`tail`, o la terminal de Xubuntu).
"""
import codecs
import os
import re
import signal
import threading
import time

MAX_BUFFER = 300_000                     # lo que se guarda para enseñar (caracteres); lo viejo se tira
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][A-Za-z0-9]|\x1b[=>78]")
_CLAVE = re.compile(r"(contrase[ñn]a|password|passphrase|clave)[^\n]{0,60}:\s*$", re.I)


def limpiar(texto):
    """(puro) Quita los códigos de color/cursor y los «\\r» que la ventana no sabe pintar. Un «\\b» borra la letra."""
    t = _ANSI.sub("", str(texto or ""))
    t = t.replace("\r\n", "\n")
    t = re.sub(r"[^\n]*\r(?!\n)", "", t)          # «\r» suelto = vuelve al principio de la línea: se queda lo último
    while "\b" in t:
        n = re.sub(r"[^\b\n]\x08", "", t, count=0)
        if n == t:
            t = t.replace("\b", "")
            break
        t = n
    return "".join(c for c in t if c in "\n\t" or ord(c) >= 32)


def pide_clave(texto):
    """(puro) ¿La última línea es una pregunta de contraseña (sudo, ssh…)? Entonces la ventana usa puntitos."""
    ultima = str(texto or "").rsplit("\n", 1)[-1]
    return bool(_CLAVE.search(ultima))


class Terminal:
    """Un bash en un pseudo-terminal. `escribir` manda una línea; `leer(desde)` da lo nuevo."""

    def __init__(self, shell=None, cwd=None, env=None):
        self.shell = shell or os.environ.get("SHELL") or "/bin/bash"
        if not os.path.exists(self.shell):
            self.shell = "/bin/bash" if os.path.exists("/bin/bash") else "/bin/sh"
        self.cwd = cwd or os.path.expanduser("~")
        self.env = env
        self.pid = None
        self.fd = None
        self._buf = ""
        self._base = 0                           # cuántos caracteres se han tirado por delante (para «desde»)
        self._lock = threading.Lock()
        self._hilo = None
        self.vivo = False

    def _entorno(self):
        e = dict(os.environ if self.env is None else self.env)
        e.update(TERM="dumb", PAGER="cat", GIT_PAGER="cat", SYSTEMD_PAGER="cat", LESS="-FRX", NO_COLOR="1",
                 PS1=r"\u@kiraos:\w$ ", PROMPT_COMMAND="", LANG=e.get("LANG") or "es_ES.UTF-8")
        e.pop("KIRA_TOKEN", None)
        return e

    def iniciar(self):
        if self.vivo:
            return True
        import pty
        import termios
        pid, fd = pty.fork()
        if pid == 0:                             # el hijo: bash
            try:
                os.chdir(self.cwd)
            except OSError:
                pass
            args = [self.shell, "--noediting", "--norc", "-i"] if self.shell.endswith("bash") else [self.shell, "-i"]
            try:
                os.execvpe(self.shell, args, self._entorno())
            finally:
                os._exit(127)
        self.pid, self.fd = pid, fd
        try:                                     # sin eco: la ventana ya enseña lo que escribes
            at = termios.tcgetattr(fd)
            at[3] &= ~termios.ECHO
            termios.tcsetattr(fd, termios.TCSANOW, at)
        except Exception:
            pass
        self.vivo = True
        self._hilo = threading.Thread(target=self._leer_siempre, daemon=True)
        self._hilo.start()
        return True

    def _leer_siempre(self):
        dec = codecs.getincrementaldecoder("utf-8")("replace")
        while True:
            try:
                datos = os.read(self.fd, 4096)
            except OSError:
                datos = b""
            if not datos:
                break
            self._poner(dec.decode(datos))
        self.vivo = False
        try:
            os.waitpid(self.pid, 0)
        except Exception:
            pass
        self._poner("\n[la terminal se ha cerrado — pulsa «Nueva» para abrir otra]\n")

    def _poner(self, texto):
        with self._lock:
            self._buf += limpiar(texto)
            if len(self._buf) > MAX_BUFFER:
                quitar = len(self._buf) - MAX_BUFFER
                self._buf = self._buf[quitar:]
                self._base += quitar

    def escribir(self, linea, clave=False):
        """Manda una línea a bash (como pulsar Intro). Con `clave`, la línea es una contraseña: no se apunta."""
        if not self.vivo:
            self.iniciar()
        linea = str(linea or "").replace("\r", "")
        if not clave:
            self._poner(linea + "\n")              # se ve lo que escribiste (bash va sin eco)
        else:
            self._poner("\n")
        os.write(self.fd, (linea + "\n").encode("utf-8"))
        return True

    def tecla(self, nombre):
        """ctrl_c (corta el programa), ctrl_d (fin), ctrl_z."""
        cod = {"ctrl_c": b"\x03", "ctrl_d": b"\x04", "ctrl_z": b"\x1a"}.get(str(nombre))
        if cod is None or not self.vivo:
            return False
        os.write(self.fd, cod)
        if nombre == "ctrl_c":
            self._poner("^C\n")
        return True

    def leer(self, desde=0):
        """Lo nuevo desde la posición `desde`: {"texto", "pos", "vivo", "clave", "reinicio"}. Si `desde` se quedó
        atrás (se tiró lo viejo), se manda todo lo que hay con `reinicio`."""
        with self._lock:
            fin = self._base + len(self._buf)
            desde = int(desde or 0)
            reinicio = desde < self._base or desde > fin
            texto = self._buf if reinicio else self._buf[desde - self._base:]
            return {"texto": texto, "pos": fin, "vivo": self.vivo, "clave": pide_clave(self._buf[-200:]),
                    "reinicio": reinicio}

    def directorio(self):
        """La carpeta donde está ahora la terminal (si has hecho «cd»)."""
        try:
            return os.readlink(f"/proc/{self.pid}/cwd")
        except (OSError, TypeError):
            return self.cwd

    def completar(self, linea):
        """Tab: completa la última palabra (una orden si es la primera, si no un archivo/carpeta) con «compgen».
        Devuelve {"linea": la línea completada, "opciones": [...]}."""
        import subprocess
        linea = str(linea or "")
        partes = linea.split(" ")
        palabra = partes[-1]
        tipo = "-c" if len(partes) == 1 else "-f"
        try:
            r = subprocess.run(["bash", "-c", f'compgen {tipo} -- "$1" | sort -u | head -200', "_", palabra],
                               capture_output=True, text=True, timeout=3, cwd=self.directorio())
            opciones = [o for o in r.stdout.splitlines() if o]
        except Exception:
            opciones = []
        if not opciones:
            return {"linea": linea, "opciones": []}
        comun = os.path.commonprefix(opciones)
        if len(opciones) == 1:
            ruta = os.path.join(self.directorio(), os.path.expanduser(comun))
            comun += "/" if tipo == "-f" and os.path.isdir(ruta) else " "
        partes[-1] = comun if len(comun) >= len(palabra) else palabra
        return {"linea": " ".join(partes), "opciones": opciones if len(opciones) > 1 else []}

    def limpiar_pantalla(self):
        with self._lock:
            self._base += len(self._buf)
            self._buf = ""
        return True

    def cerrar(self):
        if self.pid and self.vivo:
            try:
                os.kill(self.pid, signal.SIGHUP)
            except OSError:
                pass
            time.sleep(0.1)
            try:
                os.kill(self.pid, signal.SIGKILL)
            except OSError:
                pass
        try:
            if self.fd is not None:
                os.close(self.fd)
        except OSError:
            pass
        self.vivo = False
        return True
