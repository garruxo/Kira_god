# -*- coding: utf-8 -*-
"""
cerebro_local.py - El "pensamiento" local de Kira (sin Kivy, sin API). Funciona en el propio dispositivo.

Orden de respuesta (lo decide Conversacion en inicio_kira.py):
    1) órdenes del núcleo  ->  2) ESTE CEREBRO (memoria rápida y luego el BAÚL de recuerdos en disco)  ->
    3) modelo de IA local o API de Claude (solo si hace falta)

Qué sabe hacer, de verdad:
  - Habilidades locales: hora, fecha, calculadora segura, quién es Kira.
  - Memoria que APRENDE: "aprende que mi gato se llama Miko", "recuerda que ...". Responde con lo aprendido.
  - Aprender de internet: si preguntas algo informativo ("qué es un agujero negro") y no lo sabe, busca en la
    Wikipedia en español, te ENSEÑA el resumen con su fuente y SOLO lo guarda si tú dices "sí".
  - Corrección: "eso está mal" descarta lo último que usó; "olvida X" borra lo aprendido sobre X.
  - Pedir dibujos: "dibuja un paisaje de una playa al atardecer" (los dibuja escena_kira.py, por código).

Qué NO es: no es un modelo de lenguaje local; no entiende cualquier frase. Sin clave de API, la charla libre
queda limitada. Seguridad: lo que se baja de internet es TEXTO, nunca se ejecuta, se recorta y se limpia, y no
se mezcla en los prompts de la API (así una web no puede darle órdenes a Kira).
"""
import ast
import datetime
import json
import operator
import os
import re
import threading
import time
import unicodedata
import urllib.parse
import urllib.request

MAX_ENTRADAS = 500
MAX_TEXTO = 600
UMBRAL = 0.6
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
PARADA = set("el la los las un una unos unas de del al a en y o que qué es son fue era se me te mi tu su por para con sin "
             "lo le les como cómo cual cuál cuales quien quién sobre mas más muy ya no si sí hay ser".split())


def _norm(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


_PARADA_N = {_norm(x) for x in PARADA}


def tokens(texto):
    """Palabras significativas (sin tildes ni palabras vacías)."""
    return {p for p in re.findall(r"[a-z0-9ñ]+", _norm(texto)) if p not in _PARADA_N and len(p) > 1}


def _limpio(texto, maximo=MAX_TEXTO):
    t = re.sub(r"\s+", " ", _CONTROL.sub(" ", str(texto))).strip()
    t = re.sub(r"<[^>]{0,200}>", "", t)                      # sin etiquetas HTML
    if len(t) <= maximo:
        return t
    corte = t[:maximo]
    punto = max(corte.rfind(". "), corte.rfind("; "))
    return (corte[: punto + 1] if punto > maximo * 0.5 else corte.rstrip() + "…")


# =====================================================================================
#  MEMORIA DE CONOCIMIENTO
# =====================================================================================
class Conocimiento:
    def __init__(self, ruta):
        self.ruta, self._lock = ruta, threading.Lock()
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            self.items = [d for d in datos if isinstance(d, dict) and {"id", "tema", "texto"} <= set(d)][-MAX_ENTRADAS:]
        except (OSError, ValueError, TypeError):
            self.items = []

    def _guardar(self):
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta)

    def listar(self):
        with self._lock:
            return [dict(i) for i in reversed(self.items) if i.get("estado") != "descartada"]

    def guardar(self, tema, texto, fuente="usuario"):
        tema, texto = _limpio(tema, 80), _limpio(texto)
        if not tema or not texto:
            return None
        with self._lock:
            for i in self.items:                                   # mismo tema: se actualiza, no se duplica
                if _norm(i["tema"]) == _norm(tema) and i.get("estado") != "descartada":
                    i.update(texto=texto, fuente=fuente, t=time.time())
                    self._guardar()
                    return i["id"]
            nuevo = max((i["id"] for i in self.items), default=0) + 1
            self.items.append({"id": nuevo, "tema": tema, "texto": texto, "fuente": str(fuente)[:200],
                               "estado": "activa", "usos": 0, "t": time.time()})
            del self.items[:-MAX_ENTRADAS]
            self._guardar()
            return nuevo

    def buscar(self, consulta):
        """(entrada, puntuación) de la mejor coincidencia o (None, 0)."""
        q = tokens(consulta)
        if not q:
            return None, 0.0
        mejor, punt = None, 0.0
        with self._lock:
            for i in self.items:
                if i.get("estado") == "descartada":
                    continue
                tt, tx = tokens(i["tema"]), tokens(i["texto"])
                p = (len(q & tt) * 1.0 + len(q & (tx - tt)) * 0.6) / len(q)
                if p > punt:
                    mejor, punt = i, p
            return (dict(mejor), punt) if mejor else (None, 0.0)

    def usar(self, id_):
        with self._lock:
            for i in self.items:
                if i["id"] == id_:
                    i["usos"] = i.get("usos", 0) + 1
            try:
                self._guardar()
            except OSError:
                pass

    def descartar(self, id_):
        with self._lock:
            for i in self.items:
                if i["id"] == id_:
                    i["estado"] = "descartada"
                    self._guardar()
                    return True
        return False

    def olvidar_sobre(self, tema):
        e, p = self.buscar(tema)
        if e and p >= UMBRAL:
            self.descartar(e["id"])
            return e["tema"]
        return None


# =====================================================================================
#  CALCULADORA SEGURA (sin eval)
# =====================================================================================
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv,
        ast.USub: operator.neg, ast.UAdd: operator.pos}


def calcular(expresion):
    """Evalúa una operación aritmética. Lanza ValueError si no es solo aritmética o es demasiado grande."""
    arbol = ast.parse(expresion.strip(), mode="eval")

    def ev(n, prof=0):
        if prof > 20:
            raise ValueError("demasiado compleja")
        if isinstance(n, ast.Expression):
            return ev(n.body, prof + 1)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            a, b = ev(n.left, prof + 1), ev(n.right, prof + 1)
            if isinstance(n.op, ast.Pow) and (abs(b) > 100 or abs(a) > 1e6):
                raise ValueError("potencia demasiado grande")
            return _OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand, prof + 1))
        raise ValueError("no es aritmética")
    r = ev(arbol)
    return round(r, 10) if isinstance(r, float) else r


# =====================================================================================
#  BÚSQUEDA EN INTERNET (solo Wikipedia en español; el dominio es fijo)
# =====================================================================================
UA = "KiraApp/1.0 (asistente personal; contacto: usuario local)"
MAX_BYTES = 200_000


def _pedir_json(url, timeout=8):
    if not url.startswith("https://es.wikipedia.org/"):
        raise ValueError("dominio no permitido")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(MAX_BYTES).decode("utf-8"))


def buscar_web(tema, pedir=_pedir_json):
    """Resumen de Wikipedia: {'titulo','texto','fuente'} o None. 'pedir' se puede sustituir (pruebas)."""
    tema = _limpio(tema, 80)
    if len(tema) < 2:
        return None
    try:
        q = urllib.parse.quote(tema)
        sug = pedir(f"https://es.wikipedia.org/w/api.php?action=opensearch&search={q}&limit=1&namespace=0&format=json")
        titulos = sug[1] if isinstance(sug, list) and len(sug) > 1 else []
        if not titulos:
            return None
        titulo = str(titulos[0])
        res = pedir("https://es.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(titulo.replace(" ", "_"), safe=""))
        texto = _limpio(res.get("extract", ""))
        if not texto or res.get("type") == "disambiguation":
            return None
        return {"titulo": _limpio(titulo, 80), "texto": texto,
                "fuente": "https://es.wikipedia.org/wiki/" + urllib.parse.quote(titulo.replace(" ", "_"), safe="")}
    except Exception:
        return None


# =====================================================================================
#  INTENCIONES
# =====================================================================================
_PREGUNTA_INFO = re.compile(
    r"^(?:dime\s+)?(?:(?:qu[eé]|quien|qui[eé]n)\s+(?:es|son|fue|fueron|era|eran|significa|significan)\s+(?P<a>.+)"
    r"|(?:busca|buscar|investiga|investigar|aprende\s+sobre|h[aá]blame\s+de|expl[ií]came|expl[ií]ca(?:me)?)"
    r"\s+(?:en\s+internet\s+|sobre\s+|de\s+)?(?P<b>.+))\??$", re.I)
_ENSENAR = re.compile(r"^(?:aprende|recuerda|acu[eé]rdate|apunta)\s+(?:que|de)\s+(.+)$", re.I)
_OLVIDAR = re.compile(r"^(?:olvida|olvídate\s+de|borra\s+de\s+tu\s+memoria)\s+(.+)$", re.I)
_MAL = re.compile(r"^(?:eso\s+)?(?:est[aá]\s+mal|es\s+falso|no\s+es\s+(?:as[ií]|correcto|verdad)|te\s+equivocas)\W*$", re.I)
_SI = re.compile(r"^(?:s[ií]|vale|ok|gu[aá]rda(?:lo)?|s[ií],?\s*gu[aá]rda(?:lo)?|claro|adelante)\W*$", re.I)
_NO = re.compile(r"^(?:no|no\s+guardes(?:lo)?|d[eé]jalo|olv[ií]dalo|cancela)\W*$", re.I)
_HORA = re.compile(r"\bqu[eé]\s+hora\s+es\b|\bme\s+dices\s+la\s+hora\b", re.I)
_FECHA = re.compile(r"\bqu[eé]\s+d[ií]a\s+(?:es|estamos)\b|\bqu[eé]\s+fecha\b", re.I)
_CALC = re.compile(r"^(?:cu[aá]nto\s+(?:es|son)|calcula|calcular)\s+(.+?)\??$", re.I)
_QUIEN = re.compile(r"\b(?:qui[eé]n\s+eres|c[oó]mo\s+te\s+llamas|qu[eé]\s+eres)\b", re.I)
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


class CerebroLocal:
    """intentar(texto) -> (respuesta, via) o None (= "no es cosa mía, que siga el siguiente paso")."""

    def __init__(self, ruta_conocimiento, buscar=buscar_web, ahora=datetime.datetime.now, escena=None, recuerdos=None):
        self.conocimiento = Conocimiento(ruta_conocimiento)
        self.recuerdos = recuerdos     # recuerdos_kira.Recuerdos (opcional): el baúl en disco, sin límite de 500
        self.ultimo_recuerdo = None
        self._buscar, self._ahora, self._escena = buscar, ahora, escena   # escena(texto) -> descripción o None
        self.pendiente = None          # propuesta de aprendizaje esperando tu "sí"/"no" (solo en memoria)
        self.ultimo_usado = None       # id de lo último que respondió desde su memoria
        self.ultima_escena = None
        self.error_web = False

    @staticmethod
    def _temas():
        try:
            import escena_kira
            return escena_kira.temas_conocidos()
        except Exception:
            return "playa, montañas, bosque…"

    # ---------- confirmaciones ----------
    def responder_pendiente(self, texto):
        if self.pendiente is None:
            return None
        t = texto.strip()
        if _SI.match(t):
            p, self.pendiente = self.pendiente, None
            self.conocimiento.guardar(p["titulo"], p["texto"], fuente=p["fuente"])
            self._al_baul(p["texto"], p["titulo"], p["fuente"])
            return f"Hecho, he aprendido sobre «{p['titulo']}».", "aprender"
        if _NO.match(t):
            self.pendiente = None
            return "Vale, no lo guardo.", "aprender"
        self.pendiente = None          # cualquier otra cosa cancela la propuesta (no se guarda nada por descuido)
        return None

    def _al_baul(self, texto, tema, fuente):
        if self.recuerdos is not None:
            try:
                self.recuerdos.guardar(texto, tema=tema, fuente=fuente)
            except Exception:
                pass                    # sin espacio o sin permiso: la memoria rápida sigue funcionando

    # ---------- principal ----------
    def intentar(self, texto):
        t = _limpio(texto, 400)
        if not t:
            return None
        if _MAL.match(t):
            if self.ultimo_recuerdo is not None and self.recuerdos is not None and self.recuerdos.olvidar(self.ultimo_recuerdo):
                self.ultimo_recuerdo = None
                return "Perdona. He olvidado ese recuerdo para no repetirlo.", "local"
            if self.ultimo_usado is not None and self.conocimiento.descartar(self.ultimo_usado):
                self.ultimo_usado = None
                return "Perdona. He descartado eso de mi memoria para no repetirlo.", "local"
            return "Vale. No tengo nada reciente de mi memoria que descartar.", "local"
        m = _OLVIDAR.match(t)
        if m:
            tema = self.conocimiento.olvidar_sobre(m.group(1))
            if self.recuerdos is not None:
                r = self.recuerdos.olvidar_sobre(m.group(1))
                tema = tema or (r and (r["tema"] or r["texto"][:60]))
            return ((f"Olvidado: «{tema}».", "local") if tema else ("No encuentro nada sobre eso en mi memoria.", "local"))
        m = _ENSENAR.match(t)
        if m:
            frase = _limpio(m.group(1))
            if len(tokens(frase)) < 2:
                return "Cuéntame algo más completo para poder recordarlo.", "local"
            tema = " ".join(sorted(tokens(frase)))[:80]
            self.conocimiento.guardar(tema, frase, fuente="usuario")
            self._al_baul(frase, "", "usuario")
            return "Anotado. Lo recordaré.", "aprender"
        if self._escena is not None:
            d = self._escena(t)
            if d and not d.get("tema"):
                return ("Todavía solo sé dibujar paisajes por código: " + self._temas() + ". "
                        "Prueba, por ejemplo: «dibuja una playa al atardecer con palmeras»."), "local"
            if d:
                self.ultima_escena = d
                return f"Aquí tienes {d['titulo']}.", "escena"
        if _HORA.search(t):
            return f"Son las {self._ahora():%H:%M}.", "local"
        if _FECHA.search(t):
            a = self._ahora()
            return f"Hoy es {DIAS[a.weekday()]} {a.day} de {MESES[a.month - 1]} de {a.year}.", "local"
        if _QUIEN.search(t):
            return "Soy Kira. Aprendo lo que me enseñas, dibujo escenas sencillas y, si hay clave, charlo.", "local"
        m = _CALC.match(t)
        if m:
            try:
                return f"Son {calcular(m.group(1).replace('x', '*').replace('^', '**').replace(',', '.'))}.", "local"
            except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, TypeError):
                return "Eso no lo puedo calcular (solo aritmética sencilla).", "local"
        # memoria aprendida
        e, p = self.conocimiento.buscar(t)
        if e and p >= UMBRAL:
            self.conocimiento.usar(e["id"])
            self.ultimo_usado = e["id"]
            return e["texto"], "local"
        # el baúl de recuerdos en disco: antes de buscar en internet o de preguntar a Claude
        if self.recuerdos is not None:
            try:
                r = self.recuerdos.respuesta_directa(t)
            except Exception:
                r = None
            if r:
                self.ultimo_recuerdo = r["n"]
                return r["texto"], "local"
        # información que no sé: busco en internet y lo propongo
        m = _PREGUNTA_INFO.match(t)
        if m:
            tema = _limpio(m.group("a") or m.group("b"), 80).rstrip("?¿ .")
            tema = re.sub(r"^(?:el|la|los|las|un|una)\s+", "", tema, flags=re.I)
            r = self._buscar(tema)
            if r:
                self.pendiente = r
                return (f"No lo sabía. En la Wikipedia dice: {r['texto']}  (Fuente: {r['fuente']}). "
                        "¿Lo guardo? Responde «sí» o «no»."), "aprender"
            self.error_web = True
            return None            # que lo intente la API, si hay clave
        return None
