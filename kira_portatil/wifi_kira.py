# -*- coding: utf-8 -*-
"""
wifi_kira.py - KiraOS controla la WiFi del portátil (v2.88). Fuera del APK; usa `nmcli` (NetworkManager, que ya trae
Xubuntu), sin instalar nada.

Lo pidió el dueño: «que KiraOS controle el wifi en el portátil». Como KiraOS va a pantalla completa, la WiFi se maneja
desde Kira (ventana con el botón «WiFi», la consola `kira`, el comando `kira-wifi` o una orden):
  estado · redes (busca) · conectar a una red (guardada o nueva) · desconectar · apagar/encender · redes guardadas ·
  olvidar una · arreglar (reconectar sola a la mejor red conocida).
Y una VIGILANTA suave (`vigilar`): si la WiFi se cae, cada 2 min intenta volver a conectar a una red YA guardada.
No toca nada si la apagaste tú.

Reglas:
  - la CLAVE de una WiFi solo se escribe EN EL PORTÁTIL (ventana: sale con puntitos; consola: sin eco). Kira no la
    guarda en su memoria ni en el historial; la guarda Linux (NetworkManager, solo legible por root).
  - desde el MÓVIL se puede mirar, buscar, conectar a una red guardada y arreglar; APAGAR, DESCONECTAR, OLVIDAR o dar
    una clave, no (te quedarías sin hablar con KiraOS y la clave viajaría): `permitida_remota`.
  - todo con listas de argumentos (sin shell): un nombre de red raro no puede colar órdenes.
"""
import json
import os
import re
import subprocess
import time
import unicodedata

NMCLI = os.environ.get("KIRA_NMCLI", "nmcli")
RUTA = os.environ.get("KIRA_WIFI_ESTADO", os.path.expanduser("~/.kira_wifi.json"))
CADA_VIGILANCIA = 120


class WifiError(Exception):
    pass


# =====================================================================================
#  nmcli
# =====================================================================================
def _correr(args, timeout=40):
    try:
        p = subprocess.run([NMCLI] + list(args), capture_output=True, text=True, timeout=timeout,
                           env=dict(os.environ, LANG="C", LC_ALL="C"))
    except FileNotFoundError:
        raise WifiError("No encuentro «nmcli» (el gestor de red de Linux). En Xubuntu viene de serie: "
                        "instálalo con «sudo apt install network-manager».")
    except subprocess.TimeoutExpired:
        raise WifiError("La WiFi no contesta (tardó demasiado).")
    return p.returncode, p.stdout, p.stderr


def _ok(args, timeout=40):
    code, out, err = _correr(args, timeout)
    if code != 0:
        raise WifiError(_error_bonito(err or out, code))
    return out


def _error_bonito(err, code=1):
    e = str(err or "").strip()
    bajo = e.lower()
    if "secrets were required" in bajo or "no secrets" in bajo or "802-11-wireless-security.psk" in bajo \
            or "invalid passphrase" in bajo or "authentication" in bajo:
        return "La clave no es correcta (o la red no la ha aceptado)."
    if "no network with ssid" in bajo or "not found" in bajo:
        return "No veo esa red ahora mismo. Di «busca redes wifi» para ver cuáles hay."
    if "not authorized" in bajo or "insufficient privileges" in bajo or "permission" in bajo:
        return ("No tengo permiso para tocar la WiFi. Vuelve a ejecutar el instalador de Kira (deja puesto el permiso) "
                "o hazlo desde el icono de red de Xubuntu.")
    if "networkmanager is not running" in bajo or "could not create nmclient" in bajo:
        return "El gestor de red de Linux (NetworkManager) no está en marcha."
    if "no wi-fi device" in bajo or "no suitable device" in bajo:
        return "No encuentro la tarjeta WiFi del portátil (¿le falta el controlador?)."
    return (e.splitlines()[-1] if e else f"La WiFi respondió con un error ({code}).")[:200]


def _partir(linea):
    """Una línea de `nmcli -t` en campos (los «:» de dentro de un nombre vienen como «\\:»)."""
    campos, actual, i = [], [], 0
    while i < len(linea):
        c = linea[i]
        if c == "\\" and i + 1 < len(linea):
            actual.append(linea[i + 1])
            i += 2
            continue
        if c == ":":
            campos.append("".join(actual))
            actual = []
        else:
            actual.append(c)
        i += 1
    campos.append("".join(actual))
    return campos


# =====================================================================================
#  LEER
# =====================================================================================
def interfaz():
    """El nombre de la tarjeta WiFi (p. ej. «wlp2s0») o None."""
    for linea in _ok(["-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"]).splitlines():
        c = _partir(linea)
        if len(c) >= 2 and c[1] == "wifi":
            return c[0]
    return None


def _dispositivo():
    for linea in _ok(["-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"]).splitlines():
        c = _partir(linea) + ["", "", "", ""]
        if c[1] == "wifi":
            return {"interfaz": c[0], "estado": c[2], "conexion": c[3] if c[3] not in ("", "--") else None}
    return None


def radio_encendida():
    return _ok(["radio", "wifi"]).strip().lower() == "enabled"


def guardadas():
    """Nombres de las redes WiFi que Linux recuerda."""
    sal = []
    for linea in _ok(["-t", "-f", "NAME,TYPE", "connection", "show"]).splitlines():
        c = _partir(linea)
        if len(c) >= 2 and c[1] in ("802-11-wireless", "wifi"):
            sal.append(c[0])
    return sal


def redes(rescan=True):
    """Las redes que se ven: [{ssid, senal, seguridad, segura, en_uso, guardada, banda}], la más fuerte primero."""
    args = ["-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY,CHAN", "device", "wifi", "list", "--rescan",
            "yes" if rescan else "no"]
    code, out, err = _correr(args, timeout=45)
    if code != 0 and rescan:                       # algunos equipos no dejan volver a buscar tan seguido
        code, out, err = _correr(args[:-1] + ["no"], timeout=30)
    if code != 0:
        raise WifiError(_error_bonito(err or out, code))
    conocidas = set(guardadas())
    mejor = {}
    for linea in out.splitlines():
        c = _partir(linea) + ["", "", "", "", ""]
        ssid = c[1].strip()
        if not ssid:
            continue                               # redes ocultas: sin nombre no se pueden elegir aquí
        try:
            senal = int(c[2])
        except ValueError:
            senal = 0
        seg = "" if c[3] in ("", "--") else c[3]
        try:
            canal = int(c[4])
        except ValueError:
            canal = 0
        r = {"ssid": ssid, "senal": senal, "seguridad": seg, "segura": bool(seg), "en_uso": c[0].strip() == "*",
             "guardada": ssid in conocidas, "banda": "5 GHz" if canal > 14 else "2,4 GHz"}
        prev = mejor.get(ssid)
        if prev is None or (r["en_uso"] and not prev["en_uso"]) or \
                (r["en_uso"] == prev["en_uso"] and r["senal"] > prev["senal"]):
            mejor[ssid] = r
    return sorted(mejor.values(), key=lambda x: (not x["en_uso"], -x["senal"], x["ssid"].lower()))


def estado():
    """{radio, interfaz, conectada, senal, ip, internet, guardadas, apagada_por_ti}."""
    d = {"radio": False, "interfaz": None, "conectada": None, "senal": None, "ip": None, "internet": "unknown",
         "guardadas": [], "apagada_por_ti": bool(_leer_estado().get("apagada_por_ti"))}
    dev = _dispositivo()
    d["radio"] = radio_encendida()
    d["guardadas"] = guardadas()
    if dev is None:
        return d
    d["interfaz"] = dev["interfaz"]
    if dev["estado"] == "connected" and dev["conexion"]:
        d["conectada"] = dev["conexion"]
        try:
            ip = _ok(["-g", "IP4.ADDRESS", "device", "show", dev["interfaz"]]).strip().splitlines()
            d["ip"] = ip[0].split("/")[0] if ip else None
        except WifiError:
            pass
        try:
            for r in redes(rescan=False):
                if r["en_uso"]:
                    d["senal"] = r["senal"]
                    break
        except WifiError:
            pass
    try:
        d["internet"] = _ok(["networking", "connectivity", "check"], timeout=20).strip() or "unknown"
    except WifiError:
        pass
    return d


_CACHE = {"t": 0.0, "d": None}


def resumen_corto(cada=30):
    """Para el panel del móvil: {ssid, senal, internet} con caché (no se pregunta a Linux cada pocos segundos)."""
    if _CACHE["d"] is not None and time.time() - _CACHE["t"] < cada:
        return _CACHE["d"]
    try:
        e = estado()
        d = {"radio": e["radio"], "ssid": e["conectada"], "senal": e["senal"], "internet": e["internet"]}
    except WifiError as ex:
        d = {"error": str(ex)}
    _CACHE.update(t=time.time(), d=d)
    return d


# =====================================================================================
#  CAMBIAR
# =====================================================================================
def validar_ssid(ssid):
    s = str(ssid or "").strip().strip("«»\"'“”")
    if not s:
        raise WifiError("Dime el nombre de la red.")
    if len(s.encode("utf-8")) > 32 or any(ord(ch) < 32 for ch in s):
        raise WifiError("Ese nombre de red no es válido (máximo 32 letras, sin caracteres raros).")
    return s


def validar_clave(clave):
    c = str(clave or "")
    if re.fullmatch(r"[0-9a-fA-F]{64}", c):
        return c
    if not 8 <= len(c) <= 63 or any(ord(ch) < 32 for ch in c):
        raise WifiError("Las claves WiFi tienen entre 8 y 63 caracteres.")
    return c


def conectar(ssid, clave=None):
    """Conecta a una red: si Linux ya la conoce, sin clave; si es nueva y tiene candado, con `clave`.
    Devuelve el texto para el dueño (nunca lleva la clave)."""
    ssid = validar_ssid(ssid)
    iface = interfaz()
    if iface is None:
        raise WifiError("No encuentro la tarjeta WiFi del portátil (¿le falta el controlador?).")
    if not radio_encendida():
        _ok(["radio", "wifi", "on"])
        time.sleep(2)
    _apuntar(apagada_por_ti=False)
    conocida = ssid in guardadas()
    if conocida and clave is None:
        _ok(["connection", "up", "id", ssid, "ifname", iface], timeout=60)
    elif conocida:
        _ok(["connection", "modify", "id", ssid, "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", validar_clave(clave)])
        _ok(["connection", "up", "id", ssid, "ifname", iface], timeout=60)
    else:
        vistas = {r["ssid"]: r for r in redes()}
        red = vistas.get(ssid)
        if red is None:
            raise WifiError(f"No veo la red «{ssid}» ahora mismo. Di «busca redes wifi» para ver cuáles hay.")
        args = ["device", "wifi", "connect", ssid, "ifname", iface]
        if red["segura"]:
            if clave is None:
                raise WifiError(f"«{ssid}» tiene clave y no la conozco: escríbela en el portátil (botón «WiFi» de mi "
                                f"ventana, o «kira-wifi --conectar \"{ssid}\"»).")
            args += ["password", validar_clave(clave)]
        _ok(args, timeout=60)
        try:
            _ok(["connection", "modify", "id", ssid, "connection.autoconnect", "yes"])
        except WifiError:
            pass
    _evento(f"conectada a «{ssid}»")
    _CACHE["d"] = None
    return f"Conectada a «{ssid}». La recordaré: al encender el portátil se conectará sola."


def desconectar():
    iface = interfaz()
    if iface is None:
        raise WifiError("No encuentro la tarjeta WiFi del portátil.")
    _ok(["device", "disconnect", iface])
    _apuntar(apagada_por_ti=True)                  # que la vigilanta no la vuelva a conectar sola
    _evento("desconectada por ti")
    _CACHE["d"] = None
    return "Desconectada. No me vuelvo a conectar sola hasta que me lo pidas («conéctate a la wifi …» o «arregla la wifi»)."


def radio(encender):
    _ok(["radio", "wifi", "on" if encender else "off"])
    _apuntar(apagada_por_ti=not encender)
    _evento("WiFi encendida" if encender else "WiFi apagada por ti")
    _CACHE["d"] = None
    if encender:
        return "WiFi encendida. Se conectará sola a una red que conozca."
    return "WiFi apagada. No la enciendo sola: dime «enciende la wifi» (o usa el botón «WiFi») cuando quieras."


def olvidar(ssid):
    ssid = validar_ssid(ssid)
    if ssid not in guardadas():
        raise WifiError(f"No tengo guardada ninguna red «{ssid}».")
    _ok(["connection", "delete", "id", ssid])
    _evento(f"olvidada «{ssid}»")
    return f"He olvidado «{ssid}» (y su clave). Para volver a usarla tendrás que darme la clave otra vez."


def reparar():
    """«arregla la wifi»: enciende la radio, busca y se conecta a la MEJOR red ya conocida que se vea."""
    _apuntar(apagada_por_ti=False)
    if not radio_encendida():
        _ok(["radio", "wifi", "on"])
        time.sleep(3)
    e = estado()
    if e["conectada"] and e["internet"] in ("full", "unknown"):
        return f"La WiFi está bien: conectada a «{e['conectada']}»" + (f" ({e['senal']} %)." if e["senal"] else ".")
    conocidas = [r for r in redes() if r["guardada"]]
    if not conocidas:
        return ("No veo ninguna red que conozca. Di «busca redes wifi» y luego «conéctate a la wifi NOMBRE» "
                "(la clave, en el portátil).")
    fallos = []
    for r in conocidas[:3]:
        try:
            _ok(["connection", "up", "id", r["ssid"]], timeout=60)
            _evento(f"arreglada: conectada a «{r['ssid']}»")
            _CACHE["d"] = None
            return f"Arreglado: conectada a «{r['ssid']}» ({r['senal']} %)."
        except WifiError as ex:
            fallos.append(f"«{r['ssid']}»: {ex}")
    return "No he podido conectarme: " + "; ".join(fallos)


# =====================================================================================
#  LA VIGILANTA: si se cae, vuelve a conectar sola (solo a redes guardadas; respeta si la apagaste tú)
# =====================================================================================
def revisar():
    """Una pasada. Devuelve el texto de lo que hizo, o None si no hacía falta nada."""
    if _leer_estado().get("apagada_por_ti"):
        return None
    try:
        if not radio_encendida():
            return None                            # apagada por alguien (o por la tecla de la antena): no la toco
        dev = _dispositivo()
        if dev is None or (dev["estado"] == "connected" and dev["conexion"]):
            return None
        conocidas = [r for r in redes() if r["guardada"]]
    except WifiError:
        return None
    for r in conocidas[:3]:
        try:
            _ok(["connection", "up", "id", r["ssid"]], timeout=60)
            _CACHE["d"] = None
            return _evento(f"se había caído; me he vuelto a conectar a «{r['ssid']}»")
        except WifiError:
            continue
    return None


def vigilar(cada_seg=CADA_VIGILANCIA, parar=None, dormir=time.sleep):
    while not (parar and parar()):
        try:
            revisar()
        except Exception:
            pass
        dormir(cada_seg)


# ---------- lo que recuerda (sin claves) ----------
def _leer_estado():
    try:
        with open(RUTA, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _guardar_estado(d):
    tmp = RUTA + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.chmod(tmp, 0o600)
        os.replace(tmp, RUTA)
    except OSError:
        pass


def _apuntar(**cambios):
    d = _leer_estado()
    d.update(cambios)
    _guardar_estado(d)


def _evento(texto):
    d = _leer_estado()
    d["eventos"] = (d.get("eventos") or [])[-49:] + [{"t": int(time.time()), "texto": str(texto)[:200]}]
    _guardar_estado(d)
    return texto


def eventos(n=10):
    return (_leer_estado().get("eventos") or [])[-n:]


# =====================================================================================
#  TEXTOS
# =====================================================================================
_INTERNET = {"full": "con internet", "limited": "conectada pero SIN internet (el router no da salida)",
             "portal": "pide iniciar sesión en una página (red de hotel/bar)", "none": "sin internet",
             "unknown": ""}


def texto_estado(e):
    if not e.get("interfaz"):
        return "No encuentro la tarjeta WiFi del portátil (¿le falta el controlador?)."
    if not e.get("radio"):
        return "La WiFi está APAGADA" + (" (la apagaste tú)." if e.get("apagada_por_ti") else ".") + \
               " Dime «enciende la wifi»."
    if not e.get("conectada"):
        return ("La WiFi está encendida pero sin conectar." +
                (f" Conozco: {', '.join(e['guardadas'][:5])}." if e.get("guardadas") else "") +
                " Di «arregla la wifi» o «busca redes wifi».")
    t = f"Conectada a «{e['conectada']}»"
    if e.get("senal") is not None:
        t += f", señal {e['senal']} %"
    if e.get("ip"):
        t += f", dirección {e['ip']}"
    extra = _INTERNET.get(e.get("internet") or "unknown", "")
    return t + (f", {extra}." if extra else ".")


def texto_redes(lista):
    if not lista:
        return "No veo ninguna red WiFi."
    filas = []
    for r in lista[:15]:
        marca = "► " if r["en_uso"] else "  "
        filas.append(f"{marca}{r['ssid']} — {r['senal']} %, {r['banda']}"
                     + (", con clave" if r["segura"] else ", ABIERTA (sin clave)")
                     + (", la conozco" if r["guardada"] else ""))
    return "Redes WiFi que veo:\n" + "\n".join(filas) + "\nPara usar una: «conéctate a la wifi NOMBRE»."


# =====================================================================================
#  ÓRDENES (desde la charla, la consola o el móvil)
# =====================================================================================
def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", t)
    return re.sub(r"\s+", " ", t).strip(" .!¡?¿")


_HAY_WIFI = re.compile(r"\b(?:wifi|wi-fi|wi fi|redes? inalambricas?)\b|\b(?:tienes|tiene|tengo|hay) internet\b|"
                       r"^arregla (?:el )?internet\b")
_CLAVE = re.compile(r"\b(?:clave|contrase(?:ñ|n)a|password|pass)\b", re.I)


def trae_clave(texto):
    return bool(_CLAVE.search(str(texto or "")))


def ocultar_clave(texto):
    """Para enseñar en pantalla una frase que traía una clave (sin la clave)."""
    return re.sub(r"(\b(?:clave|contrase(?:ñ|n)a|password|pass)\b\s*(?:es|:|=)?\s*)\S+", r"\1••••",
                  str(texto or ""), flags=re.I)


def _nombre_red(texto):
    """El nombre de la red dentro de la frase original (respeta mayúsculas y comillas)."""
    t = re.sub(r"\b(?:del|de|en el|en)\s+(?:port[aá]til|kira\s?os|ordenador|pc)\b", " ", str(texto or ""), flags=re.I)
    t = re.split(r",?\s+(?:con|y)\s+(?:la\s+)?(?:clave|contrase(?:ñ|n)a|password)\b", t, maxsplit=1, flags=re.I)[0]
    m = re.search(r"(?:wi-?fi|wi fi|red)\s+(?:a\s+|llamada\s+|que se llama\s+|de nombre\s+)?(?:la\s+(?:red\s+)?)?"
                  r"[«\"'“]?(?P<s>[^«»\"“”]+?)[»\"'”]?\s*[.!?]*\s*$", t, flags=re.I)
    if not m:
        return None
    s = m.group("s").strip().strip("«»\"'“”")
    if s.lower() in ("", "wifi", "la wifi", "de casa", "la red", "red", "otra"):
        return None
    return s


def orden_wifi(texto):
    """(accion, nombre_de_red|None) o None. Acciones: estado, redes, guardadas, conectar, desconectar, apagar,
    encender, olvidar, reparar."""
    t = _norm(texto)
    if not t or not _HAY_WIFI.search(t):
        return None
    if re.match(r"^(?:que es|que son|como funciona|para que sirve|explica|explicame|cuentame|historia)\b", t):
        return None                                   # preguntar POR la wifi es charla, no una orden
    if re.match(r"^(?:olvida|borra|elimina|quita)\b", t):
        return "olvidar", _nombre_red(texto)
    if re.match(r"^(?:apaga|desactiva)\b", t):
        return "apagar", None
    if re.match(r"^(?:enciende|activa|prende)\b", t):
        return "encender", None
    if re.match(r"^(?:desconecta|desconectate)\b", t):
        return "desconectar", None
    if re.match(r"^(?:arregla|repara|reconecta|vuelve a conectar|soluciona)\b|\bno (?:va|funciona|tengo|hay)\b", t):
        return "reparar", None
    if re.search(r"\b(?:guardadas|que conoces|conocidas|recuerdas)\b", t):
        return "guardadas", None
    if re.match(r"^(?:busca|escanea|mira|lista|ensename|dime)\b.*\bredes\b|^(?:que|cuales) redes\b|^redes\b|"
                r"^busca (?:la )?wi-?fi|^(?:que|cuales) wi-?fis?\b.*\b(?:hay|ves)\b", t):
        return "redes", None
    if re.match(r"^(?:conectate|conecta(?:te|me)?|usa|cambia(?:te)?|pon(?:te)?|engancha(?:te)?|entra)\b", t):
        return "conectar", _nombre_red(texto)
    return "estado", None


REMOTO_NO = {"apagar": "apagar", "desconectar": "desconectar", "olvidar": "olvidar redes"}


def permitida_remota(texto):
    """¿Se puede hacer esta orden de WiFi desde el MÓVIL? Devuelve (True, "") o (False, por qué)."""
    o = orden_wifi(texto)
    if o is None:
        return True, ""
    if trae_clave(texto):
        return False, ("Por seguridad, la clave de una WiFi no me la digas desde el móvil (viajaría y se quedaría "
                       "escrita). Escríbela en el portátil: botón «WiFi» de mi ventana.")
    if o[0] in REMOTO_NO:
        return False, (f"Por seguridad, {REMOTO_NO[o[0]]} la WiFi del portátil solo se hace en el portátil: si lo hago "
                       "desde el móvil, te quedas sin poder hablar con KiraOS.")
    return True, ""


def hacer(accion, carga=None, clave=None):
    """Hace la orden y devuelve el texto. `clave` solo llega desde el portátil (ventana o consola)."""
    if accion == "estado":
        return texto_estado(estado())
    if accion == "redes":
        return texto_redes(redes())
    if accion == "guardadas":
        g = guardadas()
        return ("Redes que conozco: " + ", ".join(f"«{x}»" for x in g) + ".") if g else "No conozco ninguna red todavía."
    if accion == "conectar":
        if not carga:
            return "¿A qué red? Di «busca redes wifi» y luego «conéctate a la wifi NOMBRE»."
        return conectar(carga, clave)
    if accion == "desconectar":
        return desconectar()
    if accion == "apagar":
        return radio(False)
    if accion == "encender":
        return radio(True)
    if accion == "olvidar":
        if not carga:
            return "¿Qué red olvido? Di «olvida la wifi NOMBRE»."
        return olvidar(carga)
    if accion == "reparar":
        return reparar()
    raise WifiError("No entiendo esa orden de WiFi.")


def responder(texto, clave=None):
    """Orden de WiFi escrita → texto. None si la frase no es de WiFi."""
    o = orden_wifi(texto)
    if o is None:
        return None
    if trae_clave(texto) and clave is None:
        return ("No me escribas la clave en la frase. Pulsa «WiFi» en mi ventana y elige la red: la clave sale con "
                "puntitos y no se queda en mi memoria (o «kira-wifi --conectar NOMBRE» en una terminal).")
    try:
        return hacer(o[0], o[1], clave)
    except WifiError as e:
        return f"[x] {e}"


# =====================================================================================
#  COMANDO: kira-wifi
# =====================================================================================
def main(argv=None):
    import argparse
    import getpass
    ap = argparse.ArgumentParser(description="La WiFi del portátil, desde Kira")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--redes", action="store_true", help="busca las redes que se ven")
    g.add_argument("--conectar", metavar="RED", help="conecta (si tiene clave y no la conozco, te la pido sin eco)")
    g.add_argument("--desconectar", action="store_true")
    g.add_argument("--apagar", action="store_true")
    g.add_argument("--encender", action="store_true")
    g.add_argument("--guardadas", action="store_true")
    g.add_argument("--olvidar", metavar="RED")
    g.add_argument("--arreglar", action="store_true")
    g.add_argument("--vigilar", action="store_true", help="vigila y reconecta sola si se cae (cada 2 min)")
    a = ap.parse_args(argv)
    try:
        if a.redes:
            print(texto_redes(redes()))
        elif a.conectar:
            ssid = validar_ssid(a.conectar)
            clave = None
            vistas = {r["ssid"]: r for r in redes()}
            if ssid not in guardadas() and vistas.get(ssid, {}).get("segura"):
                clave = getpass.getpass(f"Clave de «{ssid}» (no se ve al escribirla): ")
            print(conectar(ssid, clave))
        elif a.desconectar:
            print(desconectar())
        elif a.apagar:
            print(radio(False))
        elif a.encender:
            print(radio(True))
        elif a.guardadas:
            print(hacer("guardadas"))
        elif a.olvidar:
            print(olvidar(a.olvidar))
        elif a.arreglar:
            print(reparar())
        elif a.vigilar:
            vigilar()
        else:
            print(texto_estado(estado()))
    except WifiError as e:
        print(f"[x] {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
