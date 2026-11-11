# -*- coding: utf-8 -*-
"""v3.21: el dueño le cambia a KiraOS lo que quiera de SU sistema, pidiéndoselo con palabras.

Lo que se cambia aquí (todo con una frase, en la barra «Habla con Kira…», escrito o dicho):
- ASPECTO: «cambia el tema a bosque», «pon kiraos en azul» (los mismos temas que el móvil: noche, bosque, oceano,
  fuego, violeta, claro; también verde, azul, rojo, morado…).
- ICONOS del escritorio: «oculta el icono del mapa», «vuelve a poner el icono del mapa» (Hablar y Ajustes no se
  pueden ocultar: así siempre puedes deshacerlo). Las ventanas/iconos NUEVOS y las funciones nuevas siguen siendo
  MEJORAS (v3.19: laboratorio + tus dos toques).
- SALVAPANTALLAS: «pon el salvapantallas de estrellas», «salvapantallas a los 5 minutos», «quita el salvapantallas»,
  «enséñame el salvapantallas» (estilos: orbe, estrellas, reloj, negro).
- INICIO y APAGADO: «al encender dime: buenos días, jefe», «al apagar di: hasta mañana».
- VOZ: «habla más despacio / más rápido», «voz más grave / más aguda», «voz normal».
- PANTALLA: «sube / baja el brillo», «brillo al 60», «apaga la pantalla», «apaga la pantalla a los 15 minutos».
- SONIDO: «sube / baja el volumen», «volumen al 40», «silencio», «quita el silencio».
- BLUETOOTH: «enciende / apaga el bluetooth», «busca aparatos bluetooth», «mis aparatos bluetooth»,
  «conecta el bluetooth a mis cascos», «desconecta el bluetooth de mis cascos».
- «deshaz el último cambio», «qué puedo cambiar».

Candados (dichos claro):
- solo se usan programas de una LISTA FIJA (brightnessctl/xrandr, pactl/amixer, xset, bluetoothctl/rfkill), con los
  argumentos en lista (sin shell) y los valores comprobados (números acotados, direcciones MAC con su forma).
- nada de esto toca el código de Kira ni archivos del sistema, y no necesita contraseña; lo que la necesite
  (instalar programas, cambiar el logo de arranque) se hace en la ventana Terminal o con `bash solo`.
- fuera de casa (Tailscale) estas órdenes NO se le pasan (mando_kira.permitida_fuera).

Lo de los ajustes vive en ~/.kira_sistema.json (0600; `KIRA_SISTEMA` para pruebas). `correr`/`which` se inyectan.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

TEMAS = {
    "noche": {"fondo": "#05070f", "neon": "#22d3ee", "acento": "#f472d0", "texto": "#e7ecf5"},
    "bosque": {"fondo": "#06110b", "neon": "#4ade80", "acento": "#facc15", "texto": "#e6f4ea"},
    "oceano": {"fondo": "#04101c", "neon": "#38bdf8", "acento": "#818cf8", "texto": "#e3f1fb"},
    "fuego": {"fondo": "#140806", "neon": "#fb923c", "acento": "#f43f5e", "texto": "#fbeee6"},
    "violeta": {"fondo": "#0d0716", "neon": "#a78bfa", "acento": "#f472d0", "texto": "#efe9fb"},
    "claro": {"fondo": "#f4f6fb", "neon": "#0e7490", "acento": "#be185d", "texto": "#111827"},
}
try:                                      # los mismos que el móvil (si está a mano, de ahí; así no se separan)
    import sincronia_kira as _sk
    TEMAS = dict(_sk.TEMAS)
except Exception:                         # noqa: BLE001
    pass
ALIAS_TEMA = {"verde": "bosque", "azul": "oceano", "naranja": "fuego", "rojo": "fuego", "morado": "violeta",
              "lila": "violeta", "blanco": "claro", "oscuro": "noche", "negro": "noche", "mar": "oceano",
              "normal": "noche", "original": "noche", "de siempre": "noche"}
ESTILOS = ("orbe", "estrellas", "reloj", "negro")
# iconos del escritorio que se pueden ocultar (Hablar y Ajustes, nunca: así siempre se puede deshacer)
ICONOS_OCULTABLES = {"buscador": "buscador", "wifi": "wifi", "wi fi": "wifi", "red": "red", "mi red": "red",
                     "mapa": "mapa", "mapa de ataques": "mapa", "maquina": "maquina", "maquina virtual": "maquina",
                     "cuaderno": "cuaderno", "programando": "programando", "movil": "movil", "terminal": "terminal"}
# v3.22: TODOS los iconos de serie (para moverlos, cambiarles el dibujo o el nombre) y los dibujos que se pueden poner
ICONOS_BASE = ("hablar", "buscador", "wifi", "red", "mapa", "maquina", "cuaderno", "programando", "movil", "terminal",
               "ajustes")
NOMBRES_ICONO = dict(ICONOS_OCULTABLES, **{"hablar": "hablar", "hablar con kira": "hablar", "conversacion": "hablar",
                                           "ajustes": "ajustes", "configuracion": "ajustes", "google": "buscador"})
DIBUJOS = ("hablar", "buscador", "wifi", "red", "mapa", "maquina", "cuaderno", "programando", "terminal", "movil",
           "ajustes", "bloquear", "estrella", "corazon", "rayo", "nota", "casa", "sol", "luna", "musica", "camara",
           "libro", "escudo", "reloj", "bluetooth", "altavoz", "brillo", "juego", "mensaje", "carpeta", "extra")
ALIAS_DIBUJO = {"lupa": "buscador", "bocadillo": "hablar", "globo": "mapa", "mundo": "mapa", "bombilla": "cuaderno",
                "idea": "cuaderno", "ordenador": "maquina", "pantalla": "maquina", "telefono": "movil",
                "candado": "bloquear", "engranaje": "ajustes", "rueda": "ajustes", "estrellita": "estrella",
                "corazoncito": "corazon", "relampago": "rayo", "papel": "nota", "hoja": "nota", "nota musical": "musica",
                "cancion": "musica", "foto": "camara", "escudo de seguridad": "escudo", "seguridad": "escudo",
                "hora": "reloj", "sonido": "altavoz", "volumen": "altavoz", "mando": "juego", "videojuego": "juego",
                "sobre": "mensaje", "correo": "mensaje", "carpetas": "carpeta", "red de casa": "red",
                "codigo": "programando", "consola": "terminal", "cuadrados": "extra"}
DEFECTO = {"tema": "noche", "salvapantallas": {"activo": True, "minutos": 10, "estilo": "orbe"},
           "saludo": "", "despedida": "", "voz": {"velocidad": 0, "tono": 0}, "ocultos": [],
           "apagar_pantalla_min": 0, "brillo_xrandr": 1.0, "orden_iconos": [], "dibujos": {}, "nombres": {}}
MAX_FRASE = 140
MAX_HISTORIAL = 30
_MAC = re.compile(r"^[0-9A-F]{2}(?::[0-9A-F]{2}){5}$")


class SistemaError(ValueError):
    pass


# ---------------------------------------------------------------- los AJUSTES (datos)
def ruta_defecto():
    return os.environ.get("KIRA_SISTEMA") or os.path.join(os.path.expanduser("~"), ".kira_sistema.json")


def _copia(d):
    return json.loads(json.dumps(d))


def cargar(ruta=None):
    ruta = ruta or ruta_defecto()
    d = _copia(DEFECTO)
    d["historial"] = []
    try:
        with open(ruta, encoding="utf-8") as f:
            leido = json.load(f)
        if isinstance(leido, dict):
            for k, v in leido.items():
                if k in d and isinstance(d[k], dict) and isinstance(v, dict):
                    d[k].update(v)
                elif k in d or k == "historial":
                    d[k] = v
    except (OSError, ValueError):
        pass
    if d.get("tema") not in TEMAS:
        d["tema"] = "noche"
    return d


def guardar(d, ruta=None):
    ruta = ruta or ruta_defecto()
    carpeta = os.path.dirname(os.path.abspath(ruta))
    os.makedirs(carpeta, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=carpeta, prefix=".kira_sistema.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o600)
    os.replace(tmp, ruta)


def cambiar(clave, valor, ruta=None, que=""):
    """Cambia un ajuste y apunta cómo estaba (para «deshaz el último cambio»)."""
    d = cargar(ruta)
    antes = _copia(d.get(clave))
    d[clave] = valor
    h = list(d.get("historial") or [])
    h.append({"clave": clave, "antes": antes, "que": que, "cuando": time.time()})
    d["historial"] = h[-MAX_HISTORIAL:]
    guardar(d, ruta)
    return d


def deshacer(ruta=None):
    d = cargar(ruta)
    h = list(d.get("historial") or [])
    if not h:
        return None
    ult = h.pop()
    if ult.get("clave") in DEFECTO:
        d[ult["clave"]] = ult.get("antes")
    d["historial"] = h
    guardar(d, ruta)
    return ult


def colores(d):
    return dict(TEMAS.get(d.get("tema"), TEMAS["noche"]))


def para_pantalla(ruta=None):
    """Lo que necesita la pantalla del escritorio para pintarse como tú quieres."""
    d = cargar(ruta)
    s = d.get("salvapantallas") or {}
    return {"tema": d["tema"], "colores": colores(d), "ocultos": [i for i in d.get("ocultos") or []
                                                                    if i in ICONOS_OCULTABLES.values()],
            "salvapantallas": {"activo": bool(s.get("activo", True)),
                               "minutos": max(1, min(120, int(s.get("minutos") or 10))),
                               "estilo": s.get("estilo") if s.get("estilo") in ESTILOS else "orbe"},
            "saludo": str(d.get("saludo") or "")[:MAX_FRASE], "despedida": str(d.get("despedida") or "")[:MAX_FRASE],
            "orden_iconos": [str(i)[:60] for i in (d.get("orden_iconos") or []) if _id_icono_valido(i)][:60],
            "dibujos": {str(k)[:60]: v for k, v in (d.get("dibujos") or {}).items()
                        if _id_icono_valido(k) and v in DIBUJOS},
            "nombres": {str(k)[:60]: _limpia_nombre(v) for k, v in (d.get("nombres") or {}).items()
                        if _id_icono_valido(k) and _limpia_nombre(v)}}


def _id_icono_valido(i):
    i = str(i or "")
    return i in ICONOS_BASE or bool(re.match(r"^extra:[a-z0-9áéíóúñü][a-z0-9áéíóúñü _-]{0,39}$", i))


def _limpia_nombre(t):
    t = re.sub(r"[\x00-\x1f\x7f<>]", "", str(t or "")).strip()
    return t[:30]


def dibujo_de(palabra):
    p = re.sub(r"^(?:un|una|el|la|unos|unas)\s+", "", _plano(palabra).strip())
    p = ALIAS_DIBUJO.get(p, p)
    return p if p in DIBUJOS else None


def resolver_icono(nombre, extras=()):
    """«el mapa» → «mapa»; «mi día» (una ventana que se añadió) → «extra:mi dia». None si no existe."""
    n = re.sub(r"^(?:de\s+la\s+|del\s+|de\s+|el\s+|la\s+|los\s+|las\s+|mi\s+|tu\s+)", "", _plano(nombre).strip())
    n = re.sub(r"\s+(?:del\s+escritorio|de\s+la\s+pantalla(?:\s+principal)?)$", "", n).strip(" «»\"'")
    if n in NOMBRES_ICONO:
        return NOMBRES_ICONO[n]
    for ident, titulo in extras:
        if n in (_plano(ident), _plano(titulo)):
            return "extra:" + ident
    for ident, titulo in extras:
        if n and (n in _plano(titulo) or n in _plano(ident)):
            return "extra:" + ident
    return None


def opciones_voz(ruta=None):
    """(velocidad, tono) entre -100 y 100 (0 = normal)."""
    v = cargar(ruta).get("voz") or {}
    try:
        return (max(-100, min(100, int(v.get("velocidad") or 0))), max(-100, min(100, int(v.get("tono") or 0))))
    except (TypeError, ValueError):
        return (0, 0)


def saludo(ruta=None):
    return para_pantalla(ruta)["saludo"]


def despedida(ruta=None):
    return para_pantalla(ruta)["despedida"]


# ---------------------------------------------------------------- el HARDWARE (lista fija de programas)
def _correr_defecto(args, env=None, timeout=25):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, f"no está «{args[0]}»"
    except subprocess.TimeoutExpired:
        return 124, "tardó demasiado"


def entorno():
    """Para que funcione también desde el servicio del núcleo (que no tiene la pantalla ni el sonido «a mano»)."""
    e = dict(os.environ)
    e.setdefault("DISPLAY", ":0")
    xa = os.path.join(os.path.expanduser("~"), ".Xauthority")
    if "XAUTHORITY" not in e and os.path.exists(xa):
        e["XAUTHORITY"] = xa
    try:
        e.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    except AttributeError:
        pass
    e["LANG"] = "C"
    return e


class Equipo:
    def __init__(self, correr=None, which=None, ruta=None):
        self._correr = correr or (lambda a: _correr_defecto(a, env=entorno()))
        self.which = which or shutil.which
        self.ruta = ruta

    def correr(self, args):
        r = self._correr(list(args))
        return (0, "") if r is None else r

    # ----- brillo -----
    def brillo(self, op, n):
        n = max(0, min(100, int(n)))
        if self.which("brightnessctl"):
            if op == "=":
                arg = f"{max(5, n)}%"                     # nunca a 0: la pantalla se quedaría negra
            else:
                arg = f"{n}%{'+' if op == '+' else '-'}"
            cod, sal = self.correr(["brightnessctl", "-q", "-n", "5%", "set", arg] if op == "-" else
                                   ["brightnessctl", "-q", "set", arg])
            if cod == 0:
                cod2, sal2 = self.correr(["brightnessctl", "-m"])
                m = re.search(r",(\d+)%", sal2 or "")
                return f"Brillo al {m.group(1)} %." if m else "Hecho: he cambiado el brillo."
            fallo = sal
        else:
            fallo = "no está brightnessctl"
        if self.which("xrandr"):                         # reserva: brillo «de mentira» (oscurece la imagen)
            d = cargar(self.ruta)
            actual = float(d.get("brillo_xrandr") or 1.0)
            nuevo = n / 100.0 if op == "=" else actual + (n / 100.0 if op == "+" else -n / 100.0)
            nuevo = round(max(0.2, min(1.0, nuevo)), 2)
            cod, sal = self.correr(["xrandr", "--query"])
            salidas = [l.split()[0] for l in (sal or "").splitlines() if " connected" in l]
            if cod == 0 and salidas:
                cod, sal = self.correr(["xrandr", "--output", salidas[0], "--brightness", str(nuevo)])
                if cod == 0:
                    d["brillo_xrandr"] = nuevo
                    guardar(d, self.ruta)
                    return f"Brillo al {int(nuevo * 100)} % (con xrandr: oscurezco la imagen, la luz de atrás no cambia)."
            fallo = (sal or fallo).strip().splitlines()[-1:] or [fallo]
            fallo = fallo[0]
        raise SistemaError(f"No he podido cambiar el brillo ({str(fallo)[:120]}). Si falta, en la Terminal: "
                           "sudo apt install brightnessctl, y reinicia.")

    # ----- sonido -----
    def volumen(self, op, n):
        n = max(0, min(100, int(n)))
        if self.which("pactl"):
            arg = f"{n}%" if op == "=" else f"{'+' if op == '+' else '-'}{n}%"
            cod, sal = self.correr(["pactl", "set-sink-volume", "@DEFAULT_SINK@", arg])
            if cod == 0:
                self.correr(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"])
                cod2, sal2 = self.correr(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
                m = re.search(r"(\d+)%", sal2 or "")
                if m and int(m.group(1)) > 100:          # que no pase del 100 % (se oiría mal)
                    self.correr(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "100%"])
                    return "Volumen al 100 % (el máximo)."
                return f"Volumen al {m.group(1)} %." if m else "Hecho: he cambiado el volumen."
            fallo = sal
        else:
            fallo = "no está pactl"
        if self.which("amixer"):
            arg = f"{n}%" if op == "=" else f"{n}%{'+' if op == '+' else '-'}"
            cod, sal = self.correr(["amixer", "-q", "sset", "Master", arg, "unmute"])
            if cod == 0:
                cod2, sal2 = self.correr(["amixer", "get", "Master"])
                m = re.search(r"\[(\d+)%\]", sal2 or "")
                return f"Volumen al {m.group(1)} %." if m else "Hecho: he cambiado el volumen."
            fallo = sal
        raise SistemaError(f"No he podido cambiar el volumen ({str(fallo).strip()[:120]}).")

    def silencio(self, si):
        if self.which("pactl"):
            cod, sal = self.correr(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if si else "0"])
            if cod == 0:
                return "Silencio: no sonará nada." if si else "Sonido puesto otra vez."
        if self.which("amixer"):
            cod, sal = self.correr(["amixer", "-q", "sset", "Master", "mute" if si else "unmute"])
            if cod == 0:
                return "Silencio: no sonará nada." if si else "Sonido puesto otra vez."
        raise SistemaError("No he podido cambiar el sonido (no encuentro pactl ni amixer).")

    # ----- pantalla -----
    def pantalla_apagar(self):
        if not self.which("xset"):
            raise SistemaError("No encuentro «xset» para apagar la pantalla.")
        cod, sal = self.correr(["xset", "dpms", "force", "off"])
        if cod != 0:
            raise SistemaError(f"No he podido apagar la pantalla ({sal.strip()[:120]}).")
        return "Pantalla apagada. Mueve el ratón o pulsa una tecla para encenderla."

    def pantalla_minutos(self, n):
        n = max(0, min(240, int(n)))
        if not self.which("xset"):
            raise SistemaError("No encuentro «xset» para cambiar cuándo se apaga la pantalla.")
        seg = str(n * 60)
        cod, sal = (self.correr(["xset", "-dpms"]) if n == 0 else self.correr(["xset", "dpms", seg, seg, seg]))
        if cod != 0:
            raise SistemaError(f"No he podido cambiarlo ({sal.strip()[:120]}).")
        return ("La pantalla ya no se apagará sola." if n == 0 else
                f"La pantalla se apagará sola tras {n} min sin tocar nada.")

    # ----- bluetooth -----
    def _bt(self):
        if not self.which("bluetoothctl"):
            raise SistemaError("No encuentro el bluetooth (bluetoothctl). En la Terminal: sudo apt install bluez, "
                               "y reinicia. Si el portátil no tiene bluetooth, no se puede.")

    def bt_poder(self, si):
        self._bt()
        if si and self.which("rfkill"):
            self.correr(["rfkill", "unblock", "bluetooth"])
        cod, sal = self.correr(["bluetoothctl", "power", "on" if si else "off"])
        if cod != 0 or re.search(r"no default controller|not available|failed", sal or "", re.I):
            raise SistemaError("No he podido " + ("encender" if si else "apagar") + " el bluetooth ("
                               + ((sal or "").strip().splitlines() or ["sin motivo"])[-1][:120] + "). ¿Tiene "
                               "bluetooth este portátil? Algunos lo traen apagado con una tecla (Fn).")
        return "Bluetooth encendido." if si else "Bluetooth apagado."

    def _aparatos(self, filtro=None):
        args = ["bluetoothctl", "devices"] + ([filtro] if filtro else [])
        cod, sal = self.correr(args)
        if cod != 0 and filtro == "Paired":
            cod, sal = self.correr(["bluetoothctl", "paired-devices"])
        if cod != 0:
            return [] if filtro else None
        out = []
        for l in (sal or "").splitlines():
            m = re.match(r"^\s*Device\s+([0-9A-Fa-f:]{17})\s*(.*)$", l)
            if m:
                out.append((m.group(1).upper(), m.group(2).strip() or m.group(1).upper()))
        return out

    def bt_lista(self, buscar=False):
        self._bt()
        if buscar:
            self.correr(["bluetoothctl", "power", "on"])
            self.correr(["bluetoothctl", "--timeout", "12", "scan", "on"])
        todos = self._aparatos()
        if todos is None:
            raise SistemaError("No he podido mirar el bluetooth (¿está encendido? Dime «enciende el bluetooth»).")
        empar = {m for m, _ in self._aparatos("Paired")}
        con = {m for m, _ in self._aparatos("Connected")}
        if not todos:
            return ("No veo ningún aparato bluetooth. Pon el aparato en modo de emparejar y dime «busca aparatos "
                    "bluetooth».")
        lin = []
        for mac, nombre in todos[:30]:
            est = "conectado" if mac in con else ("emparejado" if mac in empar else "visto")
            lin.append(f"· {nombre} — {est}")
        return ("Aparatos bluetooth:\n" + "\n".join(lin) + "\n\nPara usar uno: «conecta el bluetooth a "
                + todos[0][1] + "».")

    def _buscar_aparato(self, nombre):
        n = _plano(nombre).strip()
        todos = self._aparatos() or []
        for mac, nom in todos:
            if _plano(nom) == n:
                return mac, nom
        for mac, nom in todos:
            if n and (n in _plano(nom) or _plano(nom) in n):
                return mac, nom
        # por palabras: «mis cascos jbl» ↔ «JBL Tune 510BT» (la palabra que se repite manda)
        vacias = {"mi", "mis", "el", "la", "los", "las", "de", "del", "tu", "tus", "un", "una", "que", "con"}
        pal = [p for p in re.findall(r"[a-z0-9]+", n) if p not in vacias and len(p) >= 2]
        mejor, puntos = None, 0
        for mac, nom in todos:
            pn = set(re.findall(r"[a-z0-9]+", _plano(nom)))
            p = sum(1 for x in pal if x in pn)
            if p > puntos:
                mejor, puntos = (mac, nom), p
        return mejor

    def bt_conectar(self, nombre):
        self._bt()
        self.correr(["bluetoothctl", "power", "on"])
        a = self._buscar_aparato(nombre)
        if a is None:
            self.correr(["bluetoothctl", "--timeout", "10", "scan", "on"])
            a = self._buscar_aparato(nombre)
        if a is None:
            raise SistemaError(f"No encuentro «{nombre}». Ponlo en modo de emparejar (casi siempre, mantener pulsado "
                               "su botón) y vuelve a pedírmelo.")
        mac, nom = a
        if not _MAC.match(mac):
            raise SistemaError("Ese aparato tiene una dirección rara; no lo toco.")
        if mac not in {m for m, _ in self._aparatos("Paired")}:
            self.correr(["bluetoothctl", "pair", mac])
            self.correr(["bluetoothctl", "trust", mac])
        cod, sal = self.correr(["bluetoothctl", "connect", mac])
        if cod == 0 and not re.search(r"failed|not available", sal or "", re.I):
            return f"Conectada a «{nom}» por bluetooth."
        raise SistemaError(f"No he podido conectarme a «{nom}» ("
                           + ((sal or "").strip().splitlines() or ["sin motivo"])[-1][:120]
                           + "). Ponlo en modo de emparejar y prueba otra vez.")

    def bt_desconectar(self, nombre):
        self._bt()
        a = self._buscar_aparato(nombre)
        if a is None:
            raise SistemaError(f"No encuentro «{nombre}» entre mis aparatos bluetooth.")
        mac, nom = a
        if not _MAC.match(mac):
            raise SistemaError("Ese aparato tiene una dirección rara; no lo toco.")
        self.correr(["bluetoothctl", "disconnect", mac])
        return f"Desconectada de «{nom}»."


# ---------------------------------------------------------------- reconocer la ORDEN (puro)
_TILDES = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def _plano(t):
    """Minúsculas y sin tildes (misma longitud: sirve para cortar el texto original por las mismas posiciones)."""
    return str(t or "").translate(_TILDES).lower()


def tema_de(palabra):
    p = _plano(palabra).strip()
    p = re.sub(r"^(?:el\s+|tema\s+|color\s+|modo\s+)", "", p)
    p = ALIAS_TEMA.get(p, p)
    return p if p in TEMAS else None


def _nivel(t):
    """(op, n): «al 50» → ('=',50); «sube» → ('+',15); «baja» → ('-',15); «al máximo» → ('=',100)."""
    m = re.search(r"\b(?:al?|en|hasta(?:\s+el)?)\s+(\d{1,3})\s*(?:%|por\s*ciento)?", t) or re.search(r"\b(\d{1,3})\s*%", t)
    if m:
        return "=", min(100, int(m.group(1)))
    if re.search(r"\b(?:maximo|tope|todo)\b", t):
        return "=", 100
    if re.search(r"\bminimo\b", t):
        return "=", 0
    if re.search(r"\b(?:mitad|medio)\b", t):
        return "=", 50
    poco = bool(re.search(r"\b(?:un\s+poco|poquito|algo)\b", t))
    if re.search(r"\b(?:baja\w*|menos|reduce\w*|disminuye\w*|bajito|oscurece\w*)\b", t):
        return "-", 10 if poco else 20
    if re.search(r"\b(?:sube\w*|mas|aumenta\w*|alto|subelo|subela)\b", t):
        return "+", 10 if poco else 20
    return None


_V_CAMBIA = r"(?:cambia(?:me)?|pon(?:me)?|ponle|cambiale|deja(?:me)?)"
_DE_KIRAOS = r"(?:\s+(?:de\s+kiraos|de\s+kira|del\s+portatil|del\s+ordenador|del\s+escritorio|de\s+tu\s+pantalla|del\s+sistema|tuyo))?"
_RE_TEMA = [re.compile(r"^" + _V_CAMBIA + r"\s+(?:el\s+|tu\s+|los\s+|la\s+)?(?:tema|aspecto|colou?r(?:es)?|diseno|estilo|"
                       r"estetica|apariencia)" + _DE_KIRAOS + r"\s+(?:a|en|al|por|de)\s+(?:color\s+|tema\s+|modo\s+)?"
                       r"(?P<t>[a-z ]{3,15})$"),
            re.compile(r"^(?:pon(?:te)?|vistete|cambiate)\s+(?:kiraos\s+|kira\s+|el\s+escritorio\s+|la\s+pantalla\s+)?"
                       r"(?:en|de)\s+(?:color\s+|tema\s+|modo\s+)?(?P<t>[a-z ]{3,15})$"),
            re.compile(r"^(?:pon|usa)\s+(?:el\s+)?(?:tema|modo)\s+(?P<t>[a-z ]{3,15})$")]
_BT = re.compile(r"\b(?:bluetooth|bluetooh|bluetuz|blutu\w*|bluetoot|bt)\b")


def orden(texto):
    """(accion, valor) o None. Solo reconoce; `hacer` lo hace."""
    orig = re.sub(r"\s+", " ", str(texto or "")).strip().strip(" .!?¡¿")
    orig = re.sub(r"^(?:oye\s+|hola\s+)?kira\b[\s,:;]*", "", orig, flags=re.I)
    orig = re.sub(r"^por\s+favor\s*,?\s*", "", orig, flags=re.I)
    t = _plano(orig)
    if not t or "movil" in t:                     # el aspecto del MÓVIL es otra orden (v2.87)
        return None
    # --- deshacer / qué puedo cambiar ---
    if re.match(r"^(?:deshaz|deshacer|anula)\s+(?:el\s+)?(?:ultimo\s+)?cambio(?:\s+del\s+sistema)?$", t) or \
            re.match(r"^(?:vuelve|dejalo|ponlo)\s+(?:a\s+)?como\s+estaba$", t):
        return ("deshacer", None)
    if re.match(r"^(?:que\s+(?:puedo|te\s+puedo)\s+cambiar(?:\s+de\s+ti|\s+del\s+sistema)?|como\s+tienes\s+(?:el\s+sistema|"
                r"tus\s+ajustes|configurado\s+el\s+sistema)|(?:tus\s+)?ajustes\s+del\s+sistema)$", t):
        return ("estado", None)
    # --- saludo de inicio y despedida (el texto, tal cual lo dijiste) ---
    for clave, pat in (("saludo", r"^(?:al\s+(?:encender(?:te)?|arrancar|iniciar(?:te)?|empezar|entrar)|cuando\s+(?:enciendas|arranques|"
                                  r"te\s+enciendas|inicies|entre|entres))\s*,?\s*(?:di(?:me)?|saluda(?:me)?(?:\s+(?:con|diciendo))?)\s*:?\s*"),
                       ("saludo", r"^" + _V_CAMBIA + r"\s+(?:el\s+|tu\s+)?saludo(?:\s+de\s+(?:inicio|arranque|entrada|bienvenida))?"
                                  r"\s*(?:a|por|en)?\s*:?\s*"),
                       ("despedida", r"^(?:al\s+(?:apagar(?:te)?|apagarte|cerrar|salir)|cuando\s+(?:te\s+apagues|apagues|me\s+vaya))\s*,?\s*"
                                     r"(?:di(?:me)?|despidete(?:\s+(?:con|diciendo))?)\s*:?\s*"),
                       ("despedida", r"^" + _V_CAMBIA + r"\s+(?:la\s+|tu\s+)?despedida\s*(?:a|por|en)?\s*:?\s*")):
        m = re.match(pat, t)
        if m:
            frase = orig[m.end():].strip().strip("«»\"'").strip()
            if re.match(r"^(?:nada|lo\s+de\s+siempre|lo\s+normal)$", _plano(frase)):
                frase = ""
            return (clave, frase[:MAX_FRASE]) if frase or re.match(r".*(?:nada|siempre|normal)$", t) else None
    # --- tema / aspecto ---
    for r in _RE_TEMA:
        m = r.match(t)
        if m:
            nombre = tema_de(m.group("t"))
            if nombre:
                return ("tema", nombre)
    # --- iconos del escritorio ---
    m = re.match(r"^(?:oculta|esconde|quita)(?:me)?\s+(?:el\s+)?icono\s+(?:de\s+la\s+|del\s+|de\s+)?(?P<n>[a-z ]+?)"
                 r"(?:\s+del\s+escritorio|\s+de\s+la\s+pantalla(?:\s+principal)?)?$", t)
    if m and m.group("n").strip() in ICONOS_OCULTABLES:
        return ("ocultar", ICONOS_OCULTABLES[m.group("n").strip()])
    m = re.match(r"^(?:muestra|ensena|vuelve\s+a\s+poner|recupera|devuelve)(?:me)?\s+(?:el\s+)?icono\s+(?:de\s+la\s+|del\s+|de\s+)?"
                 r"(?P<n>[a-z ]+?)(?:\s+en\s+el\s+escritorio)?$", t)
    if m and m.group("n").strip() in ICONOS_OCULTABLES:
        return ("mostrar", ICONOS_OCULTABLES[m.group("n").strip()])
    if re.match(r"^(?:muestra|ensena|vuelve\s+a\s+poner)(?:me)?\s+todos\s+los\s+iconos$", t):
        return ("mostrar", "todos")
    # --- v3.22: mover iconos, cambiarles el dibujo o el nombre ---
    if re.match(r"^(?:deja|pon|vuelve\s+a\s+poner)\s+(?:todos\s+)?los\s+iconos\s+(?:como\s+(?:estaban|al\s+principio|de\s+serie)|"
                r"en\s+su\s+sitio|en\s+orden)$", t) or re.match(r"^ordena\s+los\s+iconos\s+como\s+estaban$", t):
        return ("iconos_serie", None)
    m = re.match(r"^(?:mueve|pon|coloca|lleva|pasa)(?:me)?\s+(?:el\s+)?icono\s+(?P<n>.+?)\s+(?P<d>(?:al|a\s+la|el|en\s+el|en\s+la|"
                 r"antes\s+de(?:l)?|delante\s+de(?:l)?|despues\s+de(?:l)?|detras\s+de(?:l)?|junto\s+a(?:l)?)\s+.+)$", t)
    if m:
        d = m.group("d")
        dm = re.match(r"^(?:al|el|en\s+el)\s+(?:principio|primero|inicio|primer\s+lugar)$", d)
        if dm:
            donde = ("inicio", None)
        elif re.match(r"^(?:al|el|en\s+el)\s+(?:final|ultimo|fin|ultimo\s+lugar)$", d):
            donde = ("final", None)
        elif re.match(r"^(?:a\s+la|en\s+la)\s+posicion\s+(\d{1,2})$", d):
            donde = ("posicion", int(re.search(r"\d+", d).group()))
        else:
            dm = re.match(r"^(antes\s+de(?:l)?|delante\s+de(?:l)?|despues\s+de(?:l)?|detras\s+de(?:l)?|junto\s+a(?:l)?)\s+(?P<o>.+)$", d)
            if not dm:
                dm = None
            if dm:
                antes = dm.group(1).startswith(("antes", "delante"))
                otro = orig[len(orig) - len(dm.group("o")):].strip()
                donde = ("antes" if antes else "despues", otro)
            else:
                donde = None
        if donde:
            nom = orig[m.start("n"):m.end("n")]
            return ("mover_icono", (nom, donde))
    m = re.match(r"^(?:cambia|cambiale|pon(?:le)?)\s+(?:el\s+)?(?:icono|dibujo)\s+(?:de\s+la\s+|del\s+|de\s+)?(?P<n>.+?)\s+"
                 r"(?:por|a|en)\s+(?:un\s+|una\s+|el\s+|la\s+)?(?:dibujo\s+de\s+(?:un\s+|una\s+)?)?(?P<d>[a-z ]{2,25})$", t) or \
        re.match(r"^pon(?:le)?\s+(?:un\s+|una\s+)?(?P<d>[a-z ]{2,25}?)\s+(?:al|en\s+el)\s+icono\s+(?:de\s+la\s+|del\s+|de\s+)?(?P<n>.+)$", t)
    if m and dibujo_de(m.group("d")):
        return ("dibujo_icono", (orig[m.start("n"):m.end("n")], dibujo_de(m.group("d"))))
    m = re.match(r"^(?:cambia|cambiale|pon(?:le)?)\s+(?:el\s+)?nombre\s+(?:al\s+|del\s+)?icono\s+(?:de\s+la\s+|del\s+|de\s+)?(?P<n>.+?)\s+"
                 r"(?:a|por|en)\s+(?P<x>.+)$", t) or \
        re.match(r"^(?:renombra|llama)\s+(?:al\s+|el\s+)?icono\s+(?:de\s+la\s+|del\s+|de\s+)?(?P<n>.+?)\s+(?:a|como|por)\s+(?P<x>.+)$", t)
    if m:
        nuevo = _limpia_nombre(orig[m.start("x"):m.end("x")].strip("«»\"' "))
        if nuevo:
            return ("nombre_icono", (orig[m.start("n"):m.end("n")], nuevo))
    # --- salvapantallas ---
    if re.search(r"\b(?:salvapantallas|salva\s+pantallas|protector\s+de\s+pantalla)\b", t):
        if re.match(r"^(?:quita|apaga|desactiva|sin|no\s+quiero)\b", t):
            return ("salva_activo", False)
        if re.match(r"^(?:ensename|ensena|muestrame|muestra|pon\s+ya|prueba|ver)\b", t) and not re.search(r"\b(?:de|a\s+los)\b", t):
            return ("salva_ver", None)
        m = re.search(r"(\d{1,3})\s*min", t)
        if m:
            return ("salva_minutos", max(1, min(120, int(m.group(1)))))
        for e in ESTILOS:
            if re.search(r"\b" + e + r"\b", t):
                return ("salva_estilo", e)
        if re.match(r"^(?:pon|activa|enciende)\b", t):
            return ("salva_activo", True)
        return None
    # --- voz ---
    if re.search(r"\b(?:habla(?:me)?|voz|hables)\b", t):
        if re.search(r"\bvoz\s+(?:normal|de\s+siempre)\b|\bhabla\s+normal\b", t):
            return ("voz", (0, 0))
        if re.search(r"\b(?:despacio|lento|mas\s+lenta|pausad\w+)\b", t):
            return ("voz_velocidad", -20)
        if re.search(r"\b(?:rapido|deprisa|mas\s+rapida|ligero)\b", t):
            return ("voz_velocidad", 20)
        if re.search(r"\b(?:grave|baja|profunda)\b", t) and "voz" in t:
            return ("voz_tono", -20)
        if re.search(r"\b(?:aguda|alta|fina)\b", t) and "voz" in t:
            return ("voz_tono", 20)
    # --- bluetooth ---
    if _BT.search(t):
        if re.match(r"^(?:enciende|activa|pon|conecta)\s+(?:el\s+)?(?:bluetooth|bluetooh|bluetuz|blutu\w*|bluetoot|bt)$", t):
            return ("bt_poder", True)
        if re.match(r"^(?:apaga|desactiva|quita|desconecta)\s+(?:el\s+)?(?:bluetooth|bluetooh|bluetuz|blutu\w*|bluetoot|bt)$", t):
            return ("bt_poder", False)
        if re.match(r"^(?:busca|buscar|escanea|empareja)\b", t):
            return ("bt_buscar", None)
        m = re.match(r"^(?:desconecta(?:me)?|desconectate)\s+(?:el\s+\S+\s+)?(?:de\s+|del\s+|de\s+la\s+|de\s+los\s+)?(?P<n>.+?)"
                     r"(?:\s+(?:por|del|de)\s+(?:el\s+)?\S+)?$", t)
        if m:
            nombre = _BT.sub("", orig[m.start("n"):m.end("n")]).strip(" ,")
            nombre = re.sub(r"^(?:de|del|de la|de los|a|al)\s+", "", nombre, flags=re.I).strip()
            return ("bt_desconectar", nombre) if nombre else None
        m = re.match(r"^(?:conecta(?:me)?|conectate|empareja(?:me)?)\s+(?:el\s+\S+\s+)?(?:a\s+|al\s+|con\s+|a\s+la\s+|a\s+los\s+)?"
                     r"(?P<n>.+?)(?:\s+(?:por|con)\s+(?:el\s+)?\S+)?$", t)
        if m:
            nombre = _BT.sub("", orig[m.start("n"):m.end("n")]).strip(" ,")
            nombre = re.sub(r"^(?:a|al|con|a la|a los)\s+", "", nombre, flags=re.I).strip()
            return ("bt_conectar", nombre) if nombre else None
        if re.search(r"\b(?:aparatos|dispositivos|que\s+\S+\s+tengo|mis|lista)\b", t) or re.match(r"^(?:el\s+)?bluetooth$", t):
            return ("bt_lista", None)
    # --- pantalla (apagar) ---
    m = re.match(r"^(?:apaga|que\s+se\s+apague|apagame)\s+(?:la\s+)?pantalla\s+(?:a\s+los|tras|despues\s+de|en)\s+(\d{1,3})\s*min", t) or \
        re.match(r"^(?:que\s+)?la\s+pantalla\s+se\s+apague\s+(?:a\s+los|tras|en|despues\s+de)\s+(\d{1,3})\s*min", t)
    if m:
        return ("pantalla_minutos", int(m.group(1)))
    if re.match(r"^(?:que\s+)?(?:la\s+pantalla\s+)?no\s+se\s+apague\s+(?:nunca\s+)?(?:la\s+pantalla)?(?:\s+nunca)?$", t) and "pantalla" in t:
        return ("pantalla_minutos", 0)
    if re.match(r"^(?:apaga|oscurece|duerme|desconecta)(?:me)?\s+(?:la\s+)?pantalla(?:\s+(?:ya|ahora))?$", t):
        return ("pantalla_apagar", None)
    # --- brillo ---
    if re.search(r"\bbrillo\b", t) and re.match(r"^(?:sube|baja|pon|cambia|ajusta|aumenta|disminuye|reduce|mas|menos|"
                                                 r"el\s+brillo|brillo|subeme|bajame|ponme|dame|quita|un\s+poco)\b", t):
        n = _nivel(t)
        return ("brillo", n) if n else None
    if re.match(r"^(?:mas|menos)\s+luz(?:\s+en\s+la\s+pantalla)?$", t):
        return ("brillo", ("+", 20) if t.startswith("mas") else ("-", 20))
    # --- volumen / silencio ---
    if re.match(r"^(?:silencio|silenciate|callate\s+el\s+sonido|quita\s+(?:el\s+)?(?:sonido|volumen)|mutea\w*|sin\s+sonido)$", t):
        return ("silencio", True)
    if re.match(r"^(?:quita\s+(?:el\s+)?silencio|pon\s+(?:el\s+)?sonido|devuelve\s+el\s+sonido|activa\s+el\s+sonido)$", t):
        return ("silencio", False)
    if re.search(r"\b(?:volumen|sonido)\b", t) and re.match(r"^(?:sube|baja|pon|cambia|ajusta|aumenta|disminuye|reduce|"
                                                             r"mas|menos|el\s+volumen|volumen|subeme|bajame|ponme|un\s+poco)\b", t):
        n = _nivel(t)
        return ("volumen", n) if n else None
    return None


# ---------------------------------------------------------------- HACERLO
QUE_PUEDO = (
    "Puedes cambiarme, con una frase:\n"
    "· el aspecto: «cambia el tema a bosque» (" + ", ".join(TEMAS) + "; o verde, azul, rojo…)\n"
    "· los iconos: «oculta el icono del mapa» / «vuelve a poner el icono del mapa», «mueve el icono del mapa al "
    "principio» (o al final, a la posición 3, antes del wifi…), «cambia el icono del mapa por una estrella», "
    "«cambia el nombre del icono del mapa a Ataques», «deja los iconos como estaban»\n"
    "· el salvapantallas: «pon el salvapantallas de estrellas» (orbe, estrellas, reloj, negro), "
    "«salvapantallas a los 5 minutos», «quita el salvapantallas», «enséñame el salvapantallas»\n"
    "· al encender y al apagar: «al encender dime: buenos días», «al apagar di: hasta mañana»\n"
    "· la voz: «habla más despacio / más rápido», «voz más grave / más aguda», «voz normal»\n"
    "· la pantalla: «sube el brillo», «brillo al 60», «apaga la pantalla», «apaga la pantalla a los 15 minutos»\n"
    "· el sonido: «sube el volumen», «volumen al 40», «silencio», «quita el silencio»\n"
    "· el bluetooth: «enciende el bluetooth», «busca aparatos bluetooth», «conecta el bluetooth a mis cascos»\n"
    "· «deshaz el último cambio».\n"
    "Ventanas, iconos y funciones NUEVAS: pídemelas («crea en el escritorio una ventana…», «mejórate: …»); las "
    "escribo, las pruebo en mi laboratorio y se instalan con tus dos toques (Cuaderno ▸ Mejoras).")


def texto_estado(ruta=None):
    p = para_pantalla(ruta)
    vel, tono = opciones_voz(ruta)
    s = p["salvapantallas"]
    lin = [f"Tema: {p['tema']}.",
           "Salvapantallas: " + (f"{s['estilo']}, a los {s['minutos']} min." if s["activo"] else "quitado."),
           "Al encender digo: " + (f"«{p['saludo']}»." if p["saludo"] else "lo de siempre."),
           "Al apagar digo: " + (f"«{p['despedida']}»." if p["despedida"] else "lo de siempre."),
           f"Voz: velocidad {vel:+d}, tono {tono:+d} (0 = normal).",
           "Iconos ocultos: " + (", ".join(p["ocultos"]) if p["ocultos"] else "ninguno.")]
    return "\n".join(lin) + "\n\n" + QUE_PUEDO


def _orden_actual(d, extras):
    """El orden de los iconos tal como se ven ahora (los de serie + las ventanas nuevas del escritorio)."""
    todos = list(ICONOS_BASE) + ["extra:" + i for i, _ in extras]
    guardado = [i for i in (d.get("orden_iconos") or []) if i in todos]
    return guardado + [i for i in todos if i not in guardado]


def _nombre_visible(ident, d, extras):
    n = (d.get("nombres") or {}).get(ident)
    if n:
        return n
    if ident.startswith("extra:"):
        return dict(extras).get(ident[6:], ident[6:])
    return ident


def hacer(accion, valor, ruta=None, equipo=None, extras=()):
    """Hace la orden. Devuelve el texto para decírtelo. Nunca lanza: un fallo se cuenta.
    `extras`: [(id, título)] de las ventanas que Kira se añadió (para moverlas o cambiarlas también)."""
    eq = equipo or Equipo(ruta=ruta)
    extras = [(str(a), str(b)) for a, b in (extras or [])]
    try:
        if accion == "iconos_serie":
            d = cargar(ruta)
            d2 = {"orden_iconos": [], "dibujos": {}, "nombres": {}}
            for k, v in d2.items():
                cambiar(k, v, ruta, que="iconos como estaban")
            return "Iconos como estaban: su sitio, su dibujo y su nombre de siempre."
        if accion in ("mover_icono", "dibujo_icono", "nombre_icono"):
            nombre = valor[0]
            ident = resolver_icono(nombre, extras)
            if ident is None:
                return f"[x] No encuentro el icono «{nombre}». Los que hay: " + ", ".join(
                    [i for i in ICONOS_BASE] + [t for _, t in extras]) + "."
            d = cargar(ruta)
            if accion == "dibujo_icono":
                dib = dict(d.get("dibujos") or {})
                dib[ident] = valor[1]
                cambiar("dibujos", dib, ruta, que=f"dibujo del icono {ident}")
                return (f"Hecho: el icono «{_nombre_visible(ident, d, extras)}» lleva ahora el dibujo de «{valor[1]}». "
                        "Dibujos que hay: " + ", ".join(d_ for d_ in DIBUJOS if d_ != "extra") + ".")
            if accion == "nombre_icono":
                nom = dict(d.get("nombres") or {})
                nom[ident] = valor[1]
                cambiar("nombres", nom, ruta, que=f"nombre del icono {ident}")
                return f"Hecho: el icono ahora se llama «{valor[1]}»."
            orden_ = _orden_actual(d, extras)
            orden_.remove(ident)
            tipo, ref = valor[1]
            if tipo == "inicio":
                orden_.insert(0, ident)
            elif tipo == "final":
                orden_.append(ident)
            elif tipo == "posicion":
                orden_.insert(max(0, min(len(orden_), int(ref) - 1)), ident)
            else:
                otro = resolver_icono(ref, extras)
                if otro is None or otro == ident:
                    return f"[x] No encuentro el icono «{ref}» para ponerlo al lado."
                k = orden_.index(otro)
                orden_.insert(k if tipo == "antes" else k + 1, ident)
            cambiar("orden_iconos", orden_, ruta, que=f"mover el icono {ident}")
            pos = orden_.index(ident) + 1
            return f"Hecho: el icono «{_nombre_visible(ident, d, extras)}» está ahora en el puesto {pos}."
        if accion == "estado":
            return texto_estado(ruta)
        if accion == "deshacer":
            u = deshacer(ruta)
            return ("No hay ningún cambio que deshacer." if u is None else
                    f"Hecho: he deshecho el último cambio ({u.get('que') or u.get('clave')}).")
        if accion == "tema":
            cambiar("tema", valor, ruta, que=f"tema {valor}")
            return f"Listo: ahora visto el tema «{valor}». (Para volver: «cambia el tema a noche» o «deshaz el último cambio».)"
        if accion in ("ocultar", "mostrar"):
            d = cargar(ruta)
            oc = [i for i in d.get("ocultos") or [] if i in ICONOS_OCULTABLES.values()]
            if accion == "mostrar" and valor == "todos":
                oc = []
            elif accion == "ocultar":
                oc = sorted(set(oc) | {valor})
            else:
                oc = [i for i in oc if i != valor]
            cambiar("ocultos", oc, ruta, que=f"{accion} icono {valor}")
            return ("He quitado ese icono del escritorio (lo sigues teniendo en el menú K). Para traerlo: «vuelve a "
                    f"poner el icono de {valor}»." if accion == "ocultar" else "Icono otra vez en el escritorio.")
        if accion.startswith("salva_"):
            d = cargar(ruta)
            s = dict(d.get("salvapantallas") or {})
            if accion == "salva_ver":
                return "Ahí va el salvapantallas. Mueve el ratón o pulsa una tecla para quitarlo."
            if accion == "salva_activo":
                s["activo"] = bool(valor)
            elif accion == "salva_minutos":
                s["minutos"], s["activo"] = int(valor), True
            elif accion == "salva_estilo":
                s["estilo"], s["activo"] = valor, True
            cambiar("salvapantallas", s, ruta, que="salvapantallas")
            if not s.get("activo", True):
                return "Salvapantallas quitado."
            return (f"Salvapantallas: {s.get('estilo', 'orbe')}, cuando lleves {s.get('minutos', 10)} min sin tocar nada. "
                    "Para verlo ya: «enséñame el salvapantallas».")
        if accion in ("saludo", "despedida"):
            cambiar(accion, valor, ruta, que=accion)
            if not valor:
                return "Vale: vuelvo a decir lo de siempre."
            return (f"Hecho: al encender te diré «{valor}»." if accion == "saludo" else
                    f"Hecho: al apagar te diré «{valor}».")
        if accion.startswith("voz"):
            vel, tono = opciones_voz(ruta)
            if accion == "voz":
                vel, tono = valor
            elif accion == "voz_velocidad":
                vel = max(-80, min(80, vel + int(valor)))
            else:
                tono = max(-80, min(80, tono + int(valor)))
            cambiar("voz", {"velocidad": vel, "tono": tono}, ruta, que="voz")
            return ("Así hablo ahora." if (vel, tono) != (0, 0) else "Vuelvo a mi voz normal.")
        if accion == "brillo":
            return eq.brillo(*valor)
        if accion == "volumen":
            return eq.volumen(*valor)
        if accion == "silencio":
            return eq.silencio(valor)
        if accion == "pantalla_apagar":
            return eq.pantalla_apagar()
        if accion == "pantalla_minutos":
            r = eq.pantalla_minutos(valor)
            cambiar("apagar_pantalla_min", int(valor), ruta, que="apagar la pantalla")
            return r
        if accion == "bt_poder":
            return eq.bt_poder(valor)
        if accion == "bt_buscar":
            return eq.bt_lista(buscar=True)
        if accion == "bt_lista":
            return eq.bt_lista()
        if accion == "bt_conectar":
            return eq.bt_conectar(valor)
        if accion == "bt_desconectar":
            return eq.bt_desconectar(valor)
    except SistemaError as e:
        return f"[x] {e}"
    except Exception as e:                        # noqa: BLE001
        return f"[x] No he podido: {e}"
    return "No conozco ese cambio."


def responder(texto, ruta=None, equipo=None, extras=()):
    o = orden(texto)
    if o is None:
        return None
    return hacer(o[0], o[1], ruta=ruta, equipo=equipo, extras=extras)


def reaplicar(ruta=None, equipo=None):
    """Al arrancar la pantalla: vuelve a poner lo que no se guarda solo (cuándo se apaga la pantalla)."""
    d = cargar(ruta)
    n = int(d.get("apagar_pantalla_min") or 0)
    if n:
        try:
            (equipo or Equipo(ruta=ruta)).pantalla_minutos(n)
        except Exception:                         # noqa: BLE001
            pass
