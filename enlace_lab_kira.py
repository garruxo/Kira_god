# -*- coding: utf-8 -*-
"""
enlace_lab_kira.py - Kira se CONECTA SOLA al laboratorio del ordenador (VA EN EL APK; solo librería estándar).

Antes había que copiar a mano la dirección del PC y un token larguísimo. Ahora:
  1. En el PC: doble clic en «Arrancar laboratorio.bat» (carpeta kira_laboratorio). En su ventana sale un código.
  2. En el móvil: «Kira, conéctate al ordenador». Kira lo busca en la WiFi (pregunta al faro del laboratorio y, si
     el router no deja, recorre la red) y te pide el código de 6 cifras: díselo de palabra o escrito.
  3. Listo para siempre: guarda la conexión en pasarela.json. Si un día el PC cambia de dirección, Kira lo vuelve a
     encontrar sola con el mismo token (pasarela_cliente.reubicar) cuando lo necesite.
Seguridad: el faro nunca da el token; solo lo da el laboratorio a quien dice el código que sale en SU pantalla.
"""
import concurrent.futures
import json
import re
import socket
import threading
import time
import unicodedata
import urllib.error
import urllib.request

import pasarela_cliente as pc

PUERTO_HTTP = 8765
PUERTO_FARO = 8766
PREGUNTA = b"KIRA_BUSCA_LAB 1"
CIFRAS = 6
ESPERA_CODIGO = 10 * 60        # segundos que Kira espera a que le digas el código


# =====================================================================================
#  BUSCAR EL LABORATORIO EN LA WIFI
# =====================================================================================
def ip_local():
    """La dirección de este móvil en la WiFi (o None)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))           # no envía nada: solo elige la interfaz de salida
            ip = s.getsockname()[0]
        finally:
            s.close()
        return None if ip.startswith(("127.", "0.")) else ip
    except OSError:
        return None


def destinos_faro(ip=None):
    """A dónde preguntar «¿hay un laboratorio?»: difusión general, la de la red de casa y este mismo aparato (Termux)."""
    ip = ip or ip_local()
    d = ["255.255.255.255"]
    if ip:
        d.append(".".join(ip.split(".")[:3]) + ".255")
    d.append("127.0.0.1")
    return d


def _preguntar_faro(destinos, puerto, espera):
    hallados = {}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except OSError:
        return []
    with s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except OSError:
            pass
        for d in destinos:
            try:
                s.sendto(PREGUNTA, (d, puerto))
            except OSError:
                continue
        fin = time.monotonic() + espera
        while True:
            queda = fin - time.monotonic()
            if queda <= 0:
                break
            s.settimeout(queda)
            try:
                datos, (ip, _p) = s.recvfrom(1024)
            except (socket.timeout, OSError):
                break
            try:
                r = json.loads(datos.decode("utf-8"))
                puerto_http = int(r.get("puerto", PUERTO_HTTP))
            except (ValueError, TypeError, AttributeError):
                continue
            if r.get("kira_lab") != 1 or not 0 < puerto_http < 65536:
                continue
            nombre = str(r.get("nombre") or ip)[:40]
            clave = (nombre, puerto_http)                 # el mismo laboratorio contesta por cada red: uno solo
            if clave in hallados and not ip.startswith("127."):
                continue                                  # si es este mismo aparato (Termux), mejor 127.0.0.1
            url = f"http://{ip}:{puerto_http}"
            hallados[clave] = {"url": url, "ip": ip, "nombre": nombre}
    return list(hallados.values())


def _salud(url, timeout=0.6):
    try:
        with urllib.request.urlopen(url + "/salud", timeout=timeout) as r:
            return json.loads(r.read(200).decode("utf-8")).get("ok") is True
    except Exception:
        return False


def _recorrer_red(ip, puerto=PUERTO_HTTP, hilos=48):
    """Si el router no deja pasar la pregunta del faro: prueba /salud en las 254 direcciones de la red de casa."""
    if not ip or not re.match(r"^(?:10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)", ip):
        return []                                     # solo redes de casa (con datos móviles no tiene sentido)
    base = ".".join(ip.split(".")[:3])
    urls = [f"http://{base}.{n}:{puerto}" for n in range(1, 255)]
    with concurrent.futures.ThreadPoolExecutor(hilos) as ex:
        vivos = [u for u, ok in zip(urls, ex.map(_salud, urls)) if ok]
    return [{"url": u, "ip": u.split("//")[1].split(":")[0], "nombre": u.split("//")[1].split(":")[0]} for u in vivos]


def buscar(espera=1.5, destinos=None, puerto_faro=PUERTO_FARO, recorrer=True):
    """Laboratorios que hay en la WiFi: [{'url', 'ip', 'nombre'}]."""
    ip = ip_local()
    hallados = _preguntar_faro(destinos or destinos_faro(ip), puerto_faro, espera)
    if not hallados and _salud(f"http://127.0.0.1:{PUERTO_HTTP}", 0.4):
        hallados = [{"url": f"http://127.0.0.1:{PUERTO_HTTP}", "ip": "127.0.0.1", "nombre": "este móvil"}]
    if not hallados and recorrer:
        hallados = _recorrer_red(ip)
    return hallados


# =====================================================================================
#  HABLAR CON EL LABORATORIO
# =====================================================================================
def _pedir(url, ruta, datos=None, token=None, timeout=8):
    """(código HTTP, dict). Código 0 si no se pudo conectar."""
    cab = {"Content-Type": "application/json"}
    if token:
        cab["X-Kira-Token"] = token
    cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
    req = urllib.request.Request(url + ruta, data=cuerpo, method="POST" if cuerpo is not None else "GET", headers=cab)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read(20_000).decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read(5000).decode("utf-8"))
        except Exception:
            return e.code, {"ok": False, "error": f"respondió {e.code}"}
    except Exception as e:
        return 0, {"ok": False, "error": str(e)}


def hola(url, token, timeout=4):
    """{'id', 'nombre'} si ese laboratorio acepta este token; None si no."""
    codigo, r = _pedir(url, "/hola", token=token, timeout=timeout)
    return r if codigo == 200 and r.get("ok") else None


def reubicar(token, evitar="", buscar_fn=None):
    """Busca en la WiFi un laboratorio que acepte este token. {'url', 'nombre', 'id'} o None."""
    for lab in (buscar_fn or buscar)():
        if lab["url"] == evitar:
            continue
        h = hola(lab["url"], token)
        if h:
            return {"url": lab["url"], "nombre": h.get("nombre") or lab["nombre"], "id": h.get("id")}
    return None


# =====================================================================================
#  EL CÓDIGO DICHO EN VOZ ALTA («cuatro ocho dos…», «cuarenta y ocho veintiuno…», «482 197»)
# =====================================================================================
_UNIDADES = {"cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
             "siete": 7, "ocho": 8, "nueve": 9}
_ESPECIALES = {"diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
               "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintiun": 21,
               "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26,
               "veintisiete": 27, "veintiocho": 28, "veintinueve": 29, "cien": 100}
_DECENAS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90}
_CENTENAS = {"ciento": 100, "doscientos": 200, "trescientos": 300, "cuatrocientos": 400, "quinientos": 500,
             "seiscientos": 600, "setecientos": 700, "ochocientos": 800, "novecientos": 900}


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def cifras_dichas(texto):
    """Las cifras de la frase, en orden: «48 21 97», «cuatro ocho dos uno nueve siete» o «cuarenta y ocho…»."""
    fichas = re.findall(r"\d+|[a-z]+", _norm(texto))
    salida, i = [], 0
    while i < len(fichas):
        f = fichas[i]
        if f.isdigit():
            salida.append(f)
            i += 1
            continue
        valor, usado = None, 1
        if f in _CENTENAS:
            valor = _CENTENAS[f]
            resto = fichas[i + 1:i + 4]
            if resto and resto[0] in _DECENAS:
                valor += _DECENAS[resto[0]]
                usado += 1
                if len(resto) >= 3 and resto[1] == "y" and resto[2] in _UNIDADES:
                    valor += _UNIDADES[resto[2]]
                    usado += 2
            elif resto and resto[0] in _ESPECIALES and _ESPECIALES[resto[0]] < 100:
                valor += _ESPECIALES[resto[0]]
                usado += 1
            elif resto and resto[0] in _UNIDADES:
                valor += _UNIDADES[resto[0]]
                usado += 1
        elif f in _DECENAS:
            valor = _DECENAS[f]
            if i + 2 < len(fichas) and fichas[i + 1] == "y" and fichas[i + 2] in _UNIDADES:
                valor += _UNIDADES[fichas[i + 2]]
                usado = 3
        elif f in _ESPECIALES:
            valor = _ESPECIALES[f]
        elif f in _UNIDADES:
            valor = _UNIDADES[f]
        if valor is not None:
            salida.append(str(valor))
        i += usado
    return "".join(salida)


def codigo_de(texto, cifras=CIFRAS):
    """El código de 'cifras' cifras si la frase lo trae (y no trae otra cosa larga); si no, None."""
    c = cifras_dichas(texto)
    return c if len(c) == cifras else None


# =====================================================================================
#  LA CONVERSACIÓN PARA CONECTARSE
# =====================================================================================
class Enlace:
    """conectar() -> lo que Kira dice; si hace falta el código, queda esperándolo y con_codigo(frase) lo canjea."""

    def __init__(self, buscar_fn=None, reloj=time.monotonic, dispositivo="Kira"):
        self._buscar = buscar_fn or buscar
        self._reloj = reloj
        self.dispositivo = dispositivo
        self.pendiente = None              # {'url', 'nombre', 'hasta'} mientras espera el código
        self._lock = threading.Lock()

    # ---------- estado ----------
    def esperando_codigo(self):
        p = self.pendiente
        return p is not None and self._reloj() < p["hasta"]

    def estado(self):
        """(conectada, texto) comprobándolo de verdad."""
        cfg = pc.leer_config()
        url, token = str(cfg.get("url") or ""), str(cfg.get("token") or "")
        if not token:
            return False, "No estoy conectada a ningún laboratorio. Dime «Kira, conéctate al ordenador»."
        nombre = cfg.get("nombre") or url
        if url and hola(url, token):
            return True, f"[OK] Estoy conectada al laboratorio de {nombre} ({url})."
        return False, (f"Tengo guardado el laboratorio de {nombre}, pero ahora no contesta. ¿Está encendido? "
                       "Dime «Kira, conéctate al ordenador» y lo busco.")

    # ---------- conectar ----------
    def conectar(self):
        with self._lock:
            cfg = pc.leer_config()
            url, token = str(cfg.get("url") or ""), str(cfg.get("token") or "")
            if url and token:
                h = hola(url, token)
                if h:
                    self.pendiente = None
                    return f"[OK] Ya estoy conectada al laboratorio de {h.get('nombre') or url}. Cuando lo necesite, lo uso."
            labs = self._buscar()
            if token:                                       # ya emparejada: solo hay que encontrarlo
                for lab in labs:
                    h = hola(lab["url"], token)
                    if h:
                        pc.guardar_config(lab["url"], token, nombre=h.get("nombre") or lab["nombre"], id=h.get("id"))
                        self.pendiente = None
                        return (f"[OK] Conectada al laboratorio de {h.get('nombre') or lab['nombre']}"
                                f"{' (estaba en otra dirección: ya la he cambiado)' if url and lab['url'] != url else ''}.")
            if not labs:
                return ("[x] No encuentro el laboratorio en tu WiFi. En el ordenador, haz doble clic en «Arrancar "
                        "laboratorio» (carpeta kira_laboratorio) y, si Windows lo pregunta, pulsa «Permitir». El móvil "
                        "y el ordenador tienen que estar en la misma WiFi. Luego dímelo otra vez.")
            preferido = cfg.get("nombre")
            lab = next((l for l in labs if l["nombre"] == preferido), labs[0])
            codigo, r = _pedir(lab["url"], "/emparejar/pedir", {"dispositivo": self.dispositivo})
            if codigo != 200 or not r.get("ok"):
                return f"[x] El laboratorio de {lab['nombre']} no me deja conectarme: {r.get('error') or 'no contesta'}"
            nombre = r.get("nombre") or lab["nombre"]
            self.pendiente = {"url": lab["url"], "nombre": nombre, "hasta": self._reloj() + ESPERA_CODIGO}
            otros = f" (hay {len(labs)}: uso el de {nombre})" if len(labs) > 1 else ""
            return (f"He encontrado el laboratorio en «{nombre}»{otros}. Dime el código de {CIFRAS} cifras que sale en "
                    "la pantalla del ordenador.")

    def con_codigo(self, texto):
        """Si estaba esperando el código y la frase lo trae, empareja. Devuelve lo que dice Kira, o None si la frase
        no era un código (así sigue a lo suyo)."""
        if not self.esperando_codigo():
            return None
        codigo = codigo_de(texto)
        if codigo is None:
            if re.search(r"\bc[oó]digo\b", str(texto or ""), re.I) or len(cifras_dichas(texto)) >= 3:
                return f"[x] Necesito las {CIFRAS} cifras del código que sale en el ordenador, por ejemplo «4 8 2 1 9 7»."
            return None
        p = self.pendiente
        estado, r = _pedir(p["url"], "/emparejar", {"codigo": codigo, "dispositivo": self.dispositivo})
        if estado == 200 and r.get("ok") and r.get("token"):
            pc.guardar_config(p["url"], r["token"], nombre=r.get("nombre") or p["nombre"], id=r.get("id"))
            self.pendiente = None
            return (f"[OK] ¡Conectada al laboratorio de {r.get('nombre') or p['nombre']}! Ya no hace falta nada más: "
                    "a partir de ahora me conecto sola cuando lo necesite, aunque cambie la dirección del ordenador.")
        if estado == 0:
            return f"[x] El laboratorio ha dejado de contestar ({r.get('error')}). ¿Sigue encendido?"
        error = r.get("error") or "no me ha aceptado"
        if "caduc" in error or "no quedan" in error or "cerrado" in error:
            self.pendiente = None
        return "[x] " + error

    def cancelar(self):
        self.pendiente = None

    def olvidar(self):
        self.pendiente = None
        pc.olvidar_config()
        return ("[OK] He olvidado el laboratorio. Para volver a conectarme, dime «Kira, conéctate al ordenador» y el "
                "código que salga en su pantalla.")


# frases de la conversación (las usa el núcleo de Kira)
_LAB = r"(?:el |al |la |a la |con el |con la |del |de la |en el |en la |mi |tu )?(?:laboratorio|lab|ordenador|pc|port[aá]til|computadora|pasarela)\b"
CONECTAR = re.compile(r"^(?:kira[, ]+)?(?:por favor[, ]+)?(?:con[eé]ctate|conecta(?:te|me)?|enl[aá]zate|enlaza(?:te)?|"
                      r"vinc[uú]late|vincula(?:te)?|empar[eé]jate|empareja(?:te)?|entra|accede)\s+" + _LAB, re.I)
DESCONECTAR = re.compile(r"^(?:kira[, ]+)?(?:descon[eé]ctate|desconecta(?:te)?|olvida|desvinc[uú]late|desvincula(?:te)?)\s+"
                         + _LAB, re.I)
ESTADO = re.compile(r"^(?:¿\s*)?(?:est[aá]s conectada(?: al| a la)?(?: laboratorio| ordenador| pc| pasarela)?|"
                    r"estado del (?:laboratorio|ordenador|pc)|(?:hay |tienes )?laboratorio\s*\??)\s*\??$", re.I)
