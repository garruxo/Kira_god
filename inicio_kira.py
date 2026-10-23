# -*- coding: utf-8 -*-
"""
inicio_kira.py - Pantalla de inicio inmersiva: el ORBE de Kira (Kivy, móvil y PC)

Qué es:  un orbe animado que "respira" y reacciona al estado de Kira (reposo, escuchando, pensando,
         hablando). Tocarlo entra al menú. Debajo puedes hablarle (micrófono) o escribirle.
Qué NO es: no es 3D real, y la "amplitud" al hablar es simulada (no mide el audio).

Dos capas, igual que el resto del proyecto:
  - Lógica PURA (sin Kivy): OrbeModelo, Maquina (texto que se escribe), Conversacion, Voz, saludo().
  - Widgets Kivy: crear_widgets() devuelve la clase OrbeKira.

Voz (opcional): usa 'plyer' si está instalado (texto->voz y voz->texto). Si no está, o el dispositivo no lo
soporta, Kira lo dice y se sigue escribiendo. La voz->texto de Android NO está probada en todos los móviles.
"""
import json
import math
import os
import re
import threading
import time

ESTADOS = ("reposo", "escuchando", "pensando", "hablando")
COLORES = {  # RGB por estado
    "reposo": (0.10, 0.90, 0.55),
    "escuchando": (0.30, 0.65, 1.00),
    "pensando": (0.75, 0.45, 1.00),
    "hablando": (0.20, 1.00, 0.60),
}
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MAX_ENTRADA = 1000
MAX_HISTORIAL = 60


# =====================================================================================
#  ORBE (lógica pura)
# =====================================================================================
class OrbeModelo:
    """Calcula, para cada instante, qué dibujar. Coordenadas en unidades del radio del orbe (R=1)."""

    def __init__(self, particulas=26, semilla=None):
        import random
        rnd = random.Random(semilla)
        self.estado = "reposo"
        self.t = 0.0
        self.fase_color = 0.0
        self.color = COLORES["reposo"]
        self._p = [{"ang": rnd.uniform(0, 2 * math.pi), "radio": rnd.uniform(1.12, 1.55),
                    "vel": rnd.uniform(0.25, 0.9) * rnd.choice((-1, 1)),
                    "tam": rnd.uniform(0.018, 0.045), "fase": rnd.uniform(0, 6.28)} for _ in range(max(0, int(particulas)))]

    def poner_estado(self, estado):
        if estado in ESTADOS:
            self.estado = estado

    def paso(self, dt):
        dt = max(0.0, min(float(dt), 0.25))      # un tirón de pantalla no debe dar un salto enorme
        self.t += dt
        objetivo = COLORES[self.estado]
        k = min(1.0, dt * 4.0)                   # el color cambia suavemente
        self.color = tuple(c + (o - c) * k for c, o in zip(self.color, objetivo))
        vel = {"reposo": 1.0, "escuchando": 1.6, "pensando": 4.0, "hablando": 2.2}[self.estado]
        for p in self._p:
            p["ang"] = (p["ang"] + p["vel"] * vel * dt) % (2 * math.pi)

    def nucleo(self):
        """Radio del núcleo (0.55..0.85)."""
        t = self.t
        if self.estado == "hablando":     # latido irregular que imita el habla
            a = 0.5 + 0.5 * math.sin(t * 11.0) * (0.6 + 0.4 * math.sin(t * 3.1 + 1.0))
            return 0.62 + 0.18 * a
        if self.estado == "pensando":
            return 0.60 + 0.05 * math.sin(t * 7.0)
        if self.estado == "escuchando":
            return 0.66 + 0.06 * math.sin(t * 5.0)
        return 0.64 + 0.05 * math.sin(t * 1.6)     # respiración lenta

    def anillos(self):
        """[(radio, alfa)] - ondas que se alejan (hablando) o se acercan (escuchando)."""
        if self.estado == "reposo":
            return [(0.95 + 0.03 * math.sin(self.t * 1.2), 0.25)]
        sentido = -1.0 if self.estado == "escuchando" else 1.0
        velocidad = 0.55 if self.estado != "pensando" else 0.25
        res = []
        for i in range(3):
            f = (self.t * velocidad + i / 3.0) % 1.0
            f = f if sentido > 0 else 1.0 - f
            res.append((0.8 + 0.75 * f, round(0.45 * (1.0 - abs(2 * f - 1.0) ** 2), 4)))
        return res

    def particulas(self):
        """[(x, y, tamaño, alfa)]"""
        sal = []
        for p in self._p:
            r = p["radio"] + 0.04 * math.sin(self.t * 1.5 + p["fase"])
            sal.append((math.cos(p["ang"]) * r, math.sin(p["ang"]) * r, p["tam"],
                        0.35 + 0.35 * (0.5 + 0.5 * math.sin(self.t * 2.0 + p["fase"]))))
        return sal

    def fotograma(self):
        return {"color": self.color, "nucleo": self.nucleo(), "anillos": self.anillos(), "particulas": self.particulas()}


def dentro_del_orbe(px, py, cx, cy, radio_px, margen=1.15):
    """¿El toque (px,py) cae sobre el orbe? (para que el botón sea redondo, no un rectángulo)."""
    return (px - cx) ** 2 + (py - cy) ** 2 <= (radio_px * margen) ** 2


# =====================================================================================
#  TEXTO QUE SE ESCRIBE MIENTRAS KIRA "HABLA"
# =====================================================================================
class Maquina:
    """Texto que se escribe letra a letra. Nunca tarda más de 'tope' segundos: con respuestas largas acelera
    (antes, 300 letras a 45 por segundo eran casi 7 s mirando cómo se escribía)."""

    def __init__(self, texto, cps=45.0, tope=2.0):
        self.texto = str(texto)
        self.cps = max(5.0, min(float(cps), 400.0), len(self.texto) / max(0.3, float(tope)))
        self.t = 0.0

    def paso(self, dt):
        self.t += max(0.0, dt)
        return self.visible()

    def visible(self):
        return self.texto[: min(len(self.texto), int(self.t * self.cps))]

    @property
    def terminada(self):
        return int(self.t * self.cps) >= len(self.texto)


# =====================================================================================
#  SALUDO (con datos reales, sin fingir)
# =====================================================================================
def saludo(hora, tiene_clave, voz_hablar_ok=False, voz_escuchar_ok=False):
    parte = "Buenos días" if 6 <= hora < 13 else ("Buenas tardes" if 13 <= hora < 21 else "Buenas noches")
    frases = [f"{parte}. Soy Kira."]
    if tiene_clave:
        frases.append("Dime lo que necesites.")
    else:
        frases.append("Aún no tengo cerebro para charlar: descárgalo en «Cerebro y oído» (luego va sin internet "
                      "ni clave).")
    if not voz_hablar_ok:
        frases.append("En este dispositivo no puedo hablar en voz alta: te escribo.")
    elif not voz_escuchar_ok:
        frases.append("No puedo escucharte aquí: escríbeme.")
    return " ".join(frases)


# =====================================================================================
#  CONVERSACIÓN
# =====================================================================================
_SECRETO = re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}|ghp_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,}")
_CONFIG = re.compile(r"^\s*config\w*\s+(clave|token|pasarela|github)\b.*$", re.I | re.S)


def ocultar_secretos(texto):
    """Lo que se guarda en el historial no debe contener claves ni tokens (ni 'config clave: ...')."""
    t = str(texto)
    m = _CONFIG.match(t)
    if m:
        return f"config {m.group(1).lower()}: (oculto)"
    return _SECRETO.sub(lambda m_: m_.group(0)[:7] + "****", t)


_MEJORA = re.compile(
    r"^(?:por\s+favor\s+)?(?P<verbo>mej[oó]rate|mejora(?:r)?|mejora\s+tu|mejora\s+tus|aprende\s+a|ap[ré]ndete\s+a|a[ñn][aá]dete|a[ñn]ade|"
    r"implementa(?:r|te)?|incorpora|int[eé]grate|"
    r"progr[aá]mate|programa|cr[eé]ate|crea\s+una\s+funci[oó]n|quiero\s+que\s+(?:sepas|aprendas\s+a|puedas))\b[\s,:]*(?P<pedido>.+)$",
    re.I | re.S)


_CON_CODIGO = re.compile(
    r"^(?:por\s+favor\s+)?(?:implementa(?:r|me)?|instala(?:r|me)?|integra(?:r)?|incorpora(?:r)?|a[ñn]ade|mete|"
    r"convierte|haz\s+una\s+mejora\s+con)\s+(?:este|ese|el|mi)\s+(?:c[oó]digo|programa|m[oó]dulo|script)"
    r"(?:\s+(?:del?\s+editor|que\s+(?:tengo|he\s+escrito|has\s+le[ií]do)|le[ií]do))?"
    r"(?:\s+(?:en|a|como|entre)\s+(?:las?\s+|una\s+)?(?:mejoras?|kira|ti|tus\s+mejoras|m[oó]dulos?|orden(?:es)?))?$",
    re.I)


def pedido_con_codigo(texto):
    """«implementa este código en las mejoras», «instala este programa», «convierte el código del editor en una
    mejora» -> True (la mejora sale del código que tienes abierto en el editor o de lo último leído)."""
    return bool(_CON_CODIGO.match(limpiar_entrada(texto).rstrip(" .!?¡¿")))


def pedido_mejora(texto):
    """Si la frase pide una MEJORA de Kira («mejora…», «aprende a…», «añade…», «prográmate…»), devuelve lo que pide.
    Si no, None. («aprende que…» es para recordar un dato, no para programar.)"""
    t = limpiar_entrada(texto).rstrip(" .!?¡¿")
    m = _MEJORA.match(t)
    if not m:
        return None
    pedido = m.group("pedido").strip(" ,.:")
    if len(pedido) < 4 or re.match(r"^(?:sola|sobre)\b", pedido, re.I):
        return None
    if m.group("verbo").lower().startswith("ap") and re.match(r"^que\b", pedido, re.I):
        return None                                     # «aprende que…» = recordar un dato
    limpio = _quitar_proceso(pedido)
    return limpio if len(limpio) >= 4 else pedido


# Lo que el dueño añade sobre CÓMO hacerlo («pero primero escribe el código en tu laboratorio y espera mis órdenes»)
# no es parte de la mejora: Kira ya lo hace siempre (laboratorio del móvil + dos toques). Si llegara al cerebro, este
# intentaría programar «esperar órdenes» y la mejora saldría rara.
_PROCESO = [
    re.compile(r"[,;.]?\s*(?:pero\s+|y\s+)?(?:antes|primero)(?:\s+de\s+nada)?[\s,]+(?:escr[ií]bel[oa]|escribe|"
               r"pru[eé]bal[oa]|prueba|hazl[oa]|haz|ens[aá]yal[oa]|ensaya|m[eé]tel[oa]|ponl[oa])\b.*$", re.I | re.S),
    re.compile(r"[,;.]?\s*(?:pero\s+|y\s+)?(?:escr[ií]bel[oa]|escribe(?:\s+el\s+c[oó]digo)?|pru[eé]bal[oa]|prueba(?:lo)?|"
               r"ens[aá]yal[oa])\s+(?:\S+\s+){0,3}?(?:en\s+)?(?:tu|el|mi)\s+laboratorio\b.*$", re.I | re.S),
    re.compile(r"[,;.]?\s*(?:y\s+)?(?:luego\s+|despu[eé]s\s+)?espera\s+(?:a\s+)?(?:mis|las|tus|la|mi|a\s+que|que)\s+"
               r"(?:[oó]rden(?:es)?|instrucciones|aprobaci[oó]n|permiso|te\s+diga|diga|yo)\b.*$", re.I | re.S),
    re.compile(r"[,;.]?\s*(?:pero\s+|y\s+)?(?:no\s+(?:la|lo|me\s+la|me\s+lo)\s+instales|sin\s+instalar(?:la|lo)?)\b.*$",
               re.I | re.S),
]
_VERBO_MEJORA = re.compile(r"^(?:a\s+)?(?:programar|hacer|crear|escribir|preparar)(?:te|me)?\s+"
                           r"(?=(?:una|la|un|el)\s+(?:mejora|m[oó]dulo|habilidad|funci[oó]n)\b)", re.I)


def _quitar_proceso(pedido):
    corte = len(pedido)
    for rx in _PROCESO:
        m = rx.search(pedido)
        if m and m.start() > 0:
            corte = min(corte, m.start())
    return _VERBO_MEJORA.sub("", pedido[:corte]).strip(" ,.:;")


def pide_esperar(texto):
    """¿El dueño pidió expresamente que la pruebe primero y espere su orden? (Ya es así siempre: se le confirma.)"""
    t = limpiar_entrada(texto)
    return any(rx.search(t) for rx in _PROCESO)


def limpiar_entrada(texto):
    return re.sub(r"\s+", " ", _CONTROL.sub(" ", str(texto))).strip()[:MAX_ENTRADA]


class Conversacion:
    """Reparte lo que escribes: ¿es una orden del núcleo o charla? Guarda el historial en disco.

    responder_orden(texto)->str     (core.procesar_orden)
    conversar(texto, historial)->str (core.conversar; puede lanzar RuntimeError)
    """

    def __init__(self, ruta, responder_orden, conversar, no_reconocida="[i] No reconozco la orden", cerebro=None,
                 al_turno=None):
        self.ruta, self.responder_orden, self.conversar = ruta, responder_orden, conversar
        self.al_turno = al_turno    # al_turno(tu, kira): guarda en el baúl las conversaciones NUEVAS
        self.cerebro = cerebro      # cerebro_local.CerebroLocal (opcional): memoria que aprende, búsqueda, dibujo
        self.no_reconocida = no_reconocida
        self._lock = threading.Lock()
        self.historial = self._leer()

    def _leer(self):
        try:
            with open(self.ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            return [{"rol": h["rol"], "texto": str(h["texto"])[:1200], "t": float(h.get("t", 0))}
                    for h in datos if isinstance(h, dict) and h.get("rol") in ("tu", "kira")][-MAX_HISTORIAL:]
        except (OSError, ValueError, KeyError, TypeError):
            return []

    def _guardar(self):
        try:
            tmp = self.ruta + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.historial, f, ensure_ascii=False)
            os.replace(tmp, self.ruta)
        except OSError:
            pass

    def _anotar(self, rol, texto):
        with self._lock:
            self.historial.append({"rol": rol, "texto": ocultar_secretos(texto)[:1200], "t": time.time()})
            del self.historial[:-MAX_HISTORIAL]
            self._guardar()

    def turnos(self, n=8):
        with self._lock:
            return [(h["rol"], h["texto"]) for h in self.historial[-n:]]

    def borrar(self):
        with self._lock:
            self.historial = []
            self._guardar()

    def preguntar(self, texto, al_trozo=None):
        """Bloqueante (llámalo en un hilo). Devuelve (respuesta, via): 'orden' | 'local' | 'aprender' | 'escena' | 'charla' | 'error'."""
        texto = limpiar_entrada(texto)
        if not texto:
            return "No he oído nada. Dime algo.", "error"
        previo = self.turnos()
        self._anotar("tu", texto)
        if self.cerebro is not None:                      # ¿está esperando un "sí/no" para aprender algo?
            try:
                pend = self.cerebro.responder_pendiente(texto)
            except Exception:
                pend = None
            if pend:
                self._anotar("kira", pend[0])
                return pend
        try:
            r = str(self.responder_orden(texto))
        except Exception as e:
            r = f"[x] La orden falló: {e}"
            self._anotar("kira", r)
            return r, "error"
        if not r.startswith(self.no_reconocida):
            self._anotar("kira", r)
            return r, "orden"
        if self.cerebro is not None:                      # pensamiento local antes de gastar la API
            try:
                loc = self.cerebro.intentar(texto)
            except Exception:
                loc = None
            if loc:
                self._anotar("kira", loc[0])
                return loc
        try:
            if al_trozo is not None:
                try:
                    r = self.conversar(texto, previo, al_trozo=al_trozo)   # la respuesta va apareciendo
                except TypeError:
                    r = self.conversar(texto, previo)
            else:
                r = self.conversar(texto, previo)
            self._anotar("kira", r)
            if self.al_turno is not None:
                try:
                    self.al_turno(texto, r)
                except Exception:
                    pass
            return r, "charla"
        except RuntimeError as e:
            r = f"[x] {e}"
        except Exception as e:
            r = f"[x] No pude responder: {e}"
        self._anotar("kira", r)
        return r, "error"


# =====================================================================================
#  VOZ: la propia de Kira en Android (VozKira.java: un motor, en español, frase a frase); plyer si no está
# =====================================================================================
_FIN_FRASE = re.compile(r"[.!?…;:](?=\s)|\n+")
_MARCAS = re.compile(r"\[(?:OK|x|i|!)\]|[*#`_]{1,3}")


def limpiar_para_voz(texto):
    """Lo que se lee en voz alta: sin marcas [OK]/[x], asteriscos ni almohadillas de formato."""
    return re.sub(r"\s+", " ", _MARCAS.sub("", str(texto or ""))).strip()


def frases_listas(texto, desde, minimo=28, maximo=180):
    """Trozo de 'texto' a partir de 'desde' que ya se puede decir (acaba en fin de frase), o ('', desde).
    Junta frases cortas hasta 'minimo' letras para que no suene a golpes; si una frase es muy larga, corta en una
    coma o un espacio. Devuelve (trozo, nuevo_desde)."""
    resto = texto[desde:]
    fin = None
    for m in _FIN_FRASE.finditer(resto):
        if m.end() >= minimo:
            fin = m.end()
            break
    if fin is None and len(resto) > maximo:
        corte = max(resto.rfind(", ", 0, maximo), resto.rfind(" ", 0, maximo))
        fin = corte + 1 if corte > minimo else None
    if fin is None:
        return "", desde
    return resto[:fin].strip(), desde + fin


class HablaEnVivo:
    """Kira dice la respuesta FRASE A FRASE mientras el cerebro la va escribiendo, en vez de esperar a tenerla entera
    (así empieza a hablar en uno o dos segundos). Si no hay voz propia (o está apagada), no hace nada y la respuesta
    se lee entera al final, como antes."""

    def __init__(self, voz, activa=True):
        self.voz = voz
        self.activa = bool(activa) and callable(getattr(voz, "encolar", None))
        self.desde = 0            # hasta dónde del texto parcial ya se ha dicho
        self.dicho = []           # frases ya dichas (sin espacios de más)
        self.empezo = False

    def trozo(self, parcial):
        if not self.activa:
            return
        while True:
            frase, desde = frases_listas(parcial, self.desde)
            if not frase:
                return
            self.desde = desde
            frase = " ".join(frase.split())
            if not self.voz.encolar(frase, primero=not self.empezo):
                self.activa = False              # sin voz propia: lo que falte se dirá al final
                return
            self.empezo = True
            self.dicho.append(frase)

    def callar(self):
        """«Para» / «cállate»: lo que falte de esta respuesta ya no se dice."""
        self.activa = False
        self.callada = True

    def final(self, texto):
        """Dice lo que faltaba de la respuesta final. True si la voz ya está resuelta (no hay que leerla entera)."""
        if getattr(self, "callada", False):
            return True
        if not self.empezo:
            return False
        fin = " ".join(str(texto or "").split())
        hecho = " ".join(self.dicho)
        if fin.startswith(hecho):
            resto = fin[len(hecho):]
        else:                                    # la respuesta final se retocó: sigue tras la última frase dicha
            i = fin.find(self.dicho[-1])
            resto = fin[i + len(self.dicho[-1]):] if i >= 0 else ""
        resto = resto.strip()
        if resto:
            self.voz.encolar(resto)
        return True


class _VozJava:
    """Puente con org.kira.servicio.VozKira (solo Android). Se crea en el hilo principal."""

    def __init__(self):
        from jnius import autoclass
        self.V = autoclass("org.kira.servicio.VozKira")
        self.V.iniciar(autoclass("org.kivy.android.PythonActivity").mActivity)

    def lista(self):
        return bool(self.V.lista())

    def hablar(self, texto, encolar):
        return bool(self.V.hablar(texto, bool(encolar)))

    def hablando(self):
        return bool(self.V.hablando())

    def callar(self):
        self.V.callar()

    def aviso(self):
        return str(self.V.error() or "")


def voz_java():
    try:
        return _VozJava()
    except Exception:
        return None


class Voz:
    def __init__(self, plyer_modulo=None, java=None):
        self._plyer = plyer_modulo
        self.java = java if java is not None else (voz_java() if plyer_modulo is None else None)
        self.error = ""
        self._stt = None
        self.hablando_hasta = 0.0

    def hablando(self):
        if self.java is not None:
            try:
                return self.java.hablando()
            except Exception:
                pass
        return time.monotonic() < self.hablando_hasta

    def _cargar(self):
        if self._plyer is None:
            try:
                import plyer
                self._plyer = plyer
            except Exception as e:
                self.error = f"plyer no está instalado ({type(e).__name__})"
                return None
        return self._plyer

    def puede_hablar(self):
        if self.java is not None:
            return True
        p = self._cargar()
        try:
            return bool(p and p.tts)
        except Exception as e:
            self.error = str(e)
            return False

    def puede_escuchar(self):
        p = self._cargar()
        try:
            return bool(p and p.stt)
        except Exception as e:
            self.error = str(e)
            return False

    def _decir_java(self, texto, encolar):
        """La primera vez el motor tarda un momento en estar listo: espera (en un hilo) hasta 6 s."""
        if self.java.lista():
            return self.java.hablar(texto, encolar)

        def esperar():
            fin = time.monotonic() + 6
            while time.monotonic() < fin and not self.java.lista():
                time.sleep(0.1)
            try:
                self.java.hablar(texto, encolar)
            except Exception as e:
                self.error = f"voz: {e}"
        threading.Thread(target=esperar, daemon=True).start()
        return True

    def hablar(self, texto):
        """Lee el texto en voz alta (corta lo que estuviera diciendo). No bloquea. True si lo intentó."""
        texto = limpiar_para_voz(limpiar_entrada(texto))[:600]
        if not texto or not self.puede_hablar():
            return False
        # mientras habla no debe escucharse a sí misma: tiempo aproximado de lectura (unas 14 letras por segundo)
        self.hablando_hasta = time.monotonic() + 1.0 + len(texto) / 14.0
        if self.java is not None:
            try:
                return self._decir_java(texto, False)
            except Exception as e:
                self.error = f"voz: {e}"

        def decir():
            try:
                self._plyer.tts.speak(texto)
            except Exception as e:
                self.error = f"voz: {e}"
        threading.Thread(target=decir, daemon=True).start()
        return True

    def encolar(self, texto, primero=False):
        """Dice una frase DETRÁS de lo que ya está diciendo (para hablar mientras piensa). Solo con la voz propia;
        devuelve False si no puede (entonces se dice todo al final, como siempre)."""
        texto = limpiar_para_voz(texto)
        if self.java is None or not texto:
            return False
        self.hablando_hasta = max(self.hablando_hasta, time.monotonic()) + len(texto) / 14.0
        try:
            return self._decir_java(texto, not primero)
        except Exception as e:
            self.error = f"voz: {e}"
            return False

    def aviso(self):
        """Problema de la voz que conviene contar (p. ej. «no hay voz en español instalada»), o ''."""
        try:
            return self.java.aviso() if self.java is not None and hasattr(self.java, "aviso") else ""
        except Exception:
            return ""

    def callar(self):
        self.hablando_hasta = 0.0
        if self.java is not None:
            try:
                self.java.callar()
            except Exception:
                pass

    def iniciar_escucha(self, idioma="es-ES"):
        """Empieza a escuchar. Devuelve (ok, mensaje)."""
        if not self.puede_escuchar():
            return False, "No puedo escuchar en este dispositivo (falta plyer o no es compatible). Escríbeme."
        try:
            self._stt = self._plyer.stt
            try:
                self._stt.language = idioma
            except Exception:
                pass
            self._stt.start()
            return True, "Te escucho…"
        except Exception as e:
            return False, f"No pude activar el micrófono: {e}"

    def sondear(self):
        """('escuchando', '') | ('listo', texto) | ('error', mensaje)"""
        st = self._stt
        if st is None:
            return "error", "No estaba escuchando."
        try:
            if getattr(st, "listening", False):
                return "escuchando", ""
            errores = list(getattr(st, "errors", []) or [])
            resultados = list(getattr(st, "results", []) or [])
            if resultados:
                return "listo", limpiar_entrada(resultados[0])
            return "error", (str(errores[-1]) if errores else "No te he entendido.")
        except Exception as e:
            return "error", str(e)

    def parar_escucha(self):
        try:
            if self._stt is not None:
                self._stt.stop()
        except Exception:
            pass


# =====================================================================================
#  WIDGET KIVY
# =====================================================================================
def crear_widgets():
    from kivy.clock import Clock
    from kivy.graphics import Color, Ellipse, Line
    from kivy.properties import NumericProperty
    from kivy.uix.widget import Widget

    class OrbeKira(Widget):
        zoom = NumericProperty(1.0)     # la animación de entrada lo agranda
        brillo = NumericProperty(1.0)   # ... y lo desvanece

        def __init__(self, modelo=None, al_tocar=None, **kw):
            super().__init__(**kw)
            self.modelo, self.al_tocar, self._reloj = modelo or OrbeModelo(), al_tocar, None
            self.bind(size=self._dibujar, pos=self._dibujar, zoom=self._dibujar, brillo=self._dibujar)

        def iniciar(self):
            if self._reloj is None:
                self._reloj = Clock.schedule_interval(self._tick, 1 / 30.0)

        def detener(self):
            if self._reloj is not None:
                self._reloj.cancel()
                self._reloj = None

        def _tick(self, dt):
            self.modelo.paso(dt)
            self._dibujar()

        def _radio(self):
            return min(self.width, self.height) / 2.0 * 0.62 * self.zoom

        def _dibujar(self, *_):
            if self.width < 10 or self.height < 10:
                return
            f, R = self.modelo.fotograma(), self._radio()
            cx, cy = self.center
            r, g, b = f["color"]
            a = max(0.0, min(1.0, self.brillo))
            self.canvas.clear()
            with self.canvas:
                for k, alfa in ((1.55, 0.05), (1.3, 0.08), (1.1, 0.12)):          # halo
                    Color(r, g, b, alfa * a)
                    Ellipse(pos=(cx - R * k, cy - R * k), size=(2 * R * k, 2 * R * k))
                for radio, alfa in f["anillos"]:
                    Color(r, g, b, alfa * a)
                    Line(circle=(cx, cy, R * radio), width=1.4)
                n = f["nucleo"]
                for k, alfa in ((1.0, 0.35), (0.78, 0.5), (0.5, 0.75)):             # núcleo en capas
                    Color(r, g, b, alfa * a)
                    Ellipse(pos=(cx - R * n * k, cy - R * n * k), size=(2 * R * n * k, 2 * R * n * k))
                Color(1, 1, 1, 0.55 * a)
                Ellipse(pos=(cx - R * n * 0.18, cy - R * n * 0.18), size=(R * n * 0.36, R * n * 0.36))
                for x, y, tam, alfa in f["particulas"]:
                    Color(r, g, b, alfa * a)
                    d = max(2.0, 2 * R * tam)
                    Ellipse(pos=(cx + x * R - d / 2, cy + y * R - d / 2), size=(d, d))

        def on_touch_down(self, touch):
            if self.collide_point(*touch.pos) and dentro_del_orbe(touch.x, touch.y, *self.center, self._radio()):
                if self.al_tocar:
                    self.al_tocar()
                return True
            return super().on_touch_down(touch)

    return OrbeKira
