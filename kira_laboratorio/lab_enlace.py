# -*- coding: utf-8 -*-
"""
lab_enlace.py - Que Kira ENCUENTRE el laboratorio y se CONECTE sola, sin copiar direcciones ni tokens.

1. FARO (UDP 8766): cuando Kira pregunta por la WiFi «¿hay un laboratorio?», el faro contesta con su puerto y el
   nombre del equipo (NUNCA con el token). Así Kira sabe la dirección del PC aunque el router se la cambie.
2. EMPAREJAR (una sola vez por móvil): el laboratorio enseña en su ventana un código de 6 cifras. Le dices a Kira
   «Kira, conéctate al ordenador» y luego el código; si coincide, el laboratorio le da su token y Kira lo guarda.
   A partir de ahí se conecta sola.
   Contra quien quiera adivinarlo desde la misma WiFi: 5 intentos por código, el código caduca a los 10 minutos y,
   tras 3 códigos fallados, el emparejamiento se cierra hasta que vuelvas a arrancar el laboratorio.
   Para echar a todos los móviles: borra token_lab.txt y vuelve a arrancar (tendrán que emparejarse otra vez).
Solo librería estándar (vale en Windows, Linux y Termux).
"""
import hashlib
import hmac
import json
import os
import secrets
import socket
import threading
import time

PUERTO_FARO = 8766
PREGUNTA = b"KIRA_BUSCA_LAB 1"
CIFRAS = 6
CADUCA = 10 * 60          # segundos que vale un código
INTENTOS = 5              # fallos permitidos con un mismo código
CODIGOS_MAX = 3           # códigos fallados antes de cerrar el emparejamiento


def id_lab(token):
    """Identificador estable del laboratorio (cambia si cambia el token). No revela el token."""
    return hashlib.sha256(("kira-lab:" + str(token)).encode("utf-8")).hexdigest()[:12]


def nombre_equipo():
    try:
        return (socket.gethostname() or "ordenador")[:40]
    except OSError:
        return "ordenador"


def ips_locales():
    """Direcciones de este equipo en la red local (para enseñarlas en la ventana)."""
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))           # no envía nada: solo elige la interfaz de salida
            ips.add(s.getsockname()[0])
        finally:
            s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127.") and not ip.startswith("169.254."))


def _bonito(codigo):
    return codigo[:3] + " " + codigo[3:]


class Emparejador:
    """El código de 6 cifras que se enseña en la ventana del laboratorio y sus límites."""

    def __init__(self, token, reloj=time.monotonic, avisar=print, nombre=None):
        self.token = token
        self._reloj = reloj
        self._avisar = avisar
        self.nombre = nombre or nombre_equipo()
        self._lock = threading.Lock()
        self.codigo = None
        self.hasta = 0.0
        self.fallos = 0
        self.codigos_fallados = 0
        self.cerrado = False
        self.emparejados = 0

    def _nuevo(self):
        self.codigo = "".join(secrets.choice("0123456789") for _ in range(CIFRAS))
        self.hasta = self._reloj() + CADUCA
        self.fallos = 0

    def codigo_actual(self):
        """El código vigente (crea uno nuevo si caducó). None si el emparejamiento está cerrado."""
        with self._lock:
            if self.cerrado:
                return None
            if self.codigo is None or self._reloj() >= self.hasta:
                self._nuevo()
            return self.codigo

    def mostrar(self, quien=""):
        """Enseña el código en la ventana del laboratorio. Devuelve False si el emparejamiento está cerrado."""
        c = self.codigo_actual()
        if c is None:
            self._avisar("[lab] Alguien ha pedido conectarse, pero el emparejamiento está CERRADO por demasiados "
                         "códigos fallados. Vuelve a arrancar el laboratorio si eras tú.")
            return False
        minutos = max(1, int(-(-(self.hasta - self._reloj()) // 60)))     # redondeo hacia arriba
        linea = "=" * 60
        self._avisar(f"\n{linea}\n  CÓDIGO PARA CONECTAR A KIRA:   {_bonito(c)}\n"
                     f"  {'Lo pide: ' + quien if quien else 'Dile a Kira: «Kira, conéctate al ordenador»'}"
                     f"\n  Díselo a Kira (de palabra o escrito). Caduca en {minutos} min.\n{linea}\n")
        return True

    def probar(self, codigo, quien=""):
        """(True, token) si el código es el bueno; (False, motivo) si no."""
        codigo = "".join(ch for ch in str(codigo or "") if ch.isdigit())
        with self._lock:
            if self.cerrado:
                return False, "El emparejamiento está cerrado por demasiados intentos. Vuelve a arrancar el laboratorio."
            if self.codigo is None or self._reloj() >= self.hasta:
                return False, "Ese código ya caducó. Pídemelo otra vez y saldrá uno nuevo en el ordenador."
            if len(codigo) == CIFRAS and hmac.compare_digest(codigo, self.codigo):
                self.codigo = None                       # un solo uso
                self.emparejados += 1
                self._avisar(f"[lab] Kira conectada{' (' + quien + ')' if quien else ''}. Ya no hace falta el código: "
                             "a partir de ahora se conecta sola.")
                return True, self.token
            self.fallos += 1
            if self.fallos >= INTENTOS:
                self.codigo = None
                self.codigos_fallados += 1
                if self.codigos_fallados >= CODIGOS_MAX:
                    self.cerrado = True
                    self._avisar("[lab] AVISO: demasiados códigos fallados. Cierro el emparejamiento hasta que "
                                 "vuelvas a arrancar el laboratorio (¿alguien intenta adivinarlo?).")
                    return False, "Demasiados intentos: el emparejamiento se ha cerrado. Vuelve a arrancar el laboratorio."
                return False, "Ese código no es y ya no quedan intentos con él. Pídemelo otra vez: saldrá otro."
            quedan = INTENTOS - self.fallos
            return False, f"Ese código no es. Quedan {quedan} intento{'s' if quedan != 1 else ''}."


class Faro(threading.Thread):
    """Contesta por UDP a «¿hay un laboratorio?» con {kira_lab, puerto, nombre}. Nunca envía el token."""

    def __init__(self, puerto_http, nombre=None, host="0.0.0.0", puerto=PUERTO_FARO):
        super().__init__(daemon=True, name="kira-faro")
        self.puerto_http, self.host, self.puerto = int(puerto_http), host, int(puerto)
        self.nombre = nombre or nombre_equipo()
        self._parar = threading.Event()
        self.listo = threading.Event()
        self.error = ""
        self.respuestas = 0

    def parar(self):
        self._parar.set()

    def run(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if os.name != "nt":                         # en Windows SO_REUSEADDR deja «robar» el puerto: no
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.puerto))
            self.puerto = s.getsockname()[1]               # por si se pidió el 0 (uno libre)
            s.settimeout(0.5)
        except OSError as e:
            self.error = f"no pude abrir el faro en el puerto {self.puerto}: {e}"
            self.listo.set()
            return
        self.listo.set()
        respuesta = json.dumps({"kira_lab": 1, "puerto": self.puerto_http, "nombre": self.nombre}).encode("utf-8")
        with s:
            while not self._parar.is_set():
                try:
                    datos, quien = s.recvfrom(256)
                except socket.timeout:
                    continue
                except OSError:
                    if self._parar.is_set():
                        break
                    continue
                if datos.strip() == PREGUNTA:
                    try:
                        s.sendto(respuesta, quien)
                        self.respuestas += 1
                    except OSError:
                        pass
