# -*- coding: utf-8 -*-
"""
investigar_kira.py — el dueño le da a Kira preguntas/encargos NUEVOS (aparte de los que ya se hace sola) y Kira los
INVESTIGA; según lo que sean: si es REFLEXIÓN la guarda, si es PROGRAMACIÓN lo programa, si es APP la crea.

Lo pidió el dueño (v2.80): «que yo le pueda decir que se pregunte, por ejemplo "qué es un…" o "puedes hacer lo
mismo que…", y que lo investigue; si es reflexión lo guarda, si es programación lo implementa, si es app la crea».

Aquí va solo la parte PURA (sin Kivy ni cerebro): clasificar el encargo, reconocer la orden, y guardar las preguntas
del dueño en disco para que Kira las repase. El «investigar» de verdad (estudiar, programar, hacer la app) lo hace
el núcleo reusando lo que ya tiene. HONESTO: programar/meter en Kira sigue con las mismas reglas (laboratorio + la
auto-mejora o tus dos toques); nada se salta eso.
"""
import json
import os
import time
import unicodedata

MIS_PREGUNTAS = "preguntas_mias.json"


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


# ---------- clasificar el encargo: ¿reflexión, programa o app? ----------
# palabras de programar (con límite de palabra, para no confundir «funciona» con «función», etc.)
_PROG_PALABRAS = (r"\b(?:programa|programame|programar|programe|codigo|algoritmo|implementa|implementame|implement[ae]lo|"
                  r"script|calculadora|convierteme|convierte|replica|clona|simula|automatiza)\b")
# frases de «hazme / crea / puedes hacer lo mismo…»
_PROG_FRASES = ("puedes hacer lo mismo", "haz lo mismo", "haz un ", "hazme un ", "haz una ", "hazme una ", "crea un ",
                "crea una", "creame un", "escribe un ", "escribe una ", "escribeme un", "haz que ",
                "resuelve el problema", "monta un", "monta una")


def clasificar_peticion(texto):
    """'app' | 'programa' | 'reflexion'. Mira primero app, luego programa; si no, es para pensar/estudiar (reflexión)."""
    import re
    n = _norm(texto)
    if "app" in n.split() or "aplicacion" in n:
        return "app"
    if re.search(_PROG_PALABRAS, n) or any(f in n for f in (_norm(x) for x in _PROG_FRASES)):
        return "programa"
    return "reflexion"


# ---------- reconocer la orden del dueño ----------
_ORDEN = (
    r"^(?:invest[ií]ga(?:me)?|aver[ií]gua|preg[uú]ntate(?:\s+(?:si|que|qu[eé]))?|"
    r"mira a ver(?:\s+si)?|quiero que te preguntes|a ver si)\s+(.+)$"
)
_ORDEN_RECORDAR = (
    r"^(?:preg[uú]ntate tambi[eé]n|a[ñn]ade(?:\s+la)?\s+pregunta|agrega(?:\s+la)?\s+pregunta|"
    r"apunta(?:\s+la)?\s+pregunta|guarda(?:\s+la)?\s+pregunta)\s*:?\s*(.+)$"
)
_LISTAR = r"^(?:tus preguntas|mis preguntas|qu[eé] preguntas tienes|tus encargos)$"


def es_orden(texto):
    """Devuelve (accion, carga): accion 'investiga'|'recordar'|'listar'|None. 'carga' es el texto del encargo."""
    import re
    t = re.sub(r"^\s*kira[\s,:]+", "", str(texto or ""), flags=re.I).strip()
    m = re.match(_ORDEN_RECORDAR, t, re.I)
    if m:
        return ("recordar", m.group(1).strip(" .?¿!¡"))
    if re.match(_LISTAR, _norm(t)):
        return ("listar", "")
    m = re.match(_ORDEN, t, re.I)
    if m:
        carga = m.group(1).strip(" .?¿!¡")
        # «investiga X hasta resolverlo» NO es esto: eso es el FOCO (lo coge antes el pensador)
        if re.search(r"\bhasta\s+resolverl", _norm(carga)):
            return (None, "")
        return ("investiga", carga)
    return (None, "")


# ---------- las preguntas del dueño, guardadas en disco ----------
def _ruta(dir_):
    return os.path.join(dir_, MIS_PREGUNTAS)


def _leer(dir_):
    try:
        with open(_ruta(dir_), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _guardar(dir_, lista):
    try:
        tmp = _ruta(dir_) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(lista[-200:], f, ensure_ascii=False)
        os.replace(tmp, _ruta(dir_))
        os.chmod(_ruta(dir_), 0o600)
    except OSError:
        pass


def anadir(dir_, texto, recurrente=False):
    """Apunta una pregunta/encargo del dueño para que Kira la repase en su pensar."""
    texto = str(texto or "").strip()
    if len(texto) < 3:
        return False
    lista = _leer(dir_)
    if any(_norm(p.get("texto")) == _norm(texto) for p in lista):
        return False
    lista.append({"texto": texto, "hecha": False, "recurrente": bool(recurrente), "cuando": int(time.time())})
    _guardar(dir_, lista)
    return True


def pendiente(dir_):
    """La siguiente pregunta del dueño sin investigar (o None)."""
    for p in _leer(dir_):
        if not p.get("hecha"):
            return p.get("texto")
    return None


def marcar_hecha(dir_, texto):
    lista = _leer(dir_)
    for p in lista:
        if _norm(p.get("texto")) == _norm(texto):
            p["hecha"] = True if not p.get("recurrente") else False   # las recurrentes se vuelven a mirar
            p["ultima"] = int(time.time())
            break
    _guardar(dir_, lista)


def quitar(dir_, i):
    """v3.10: borra el encargo número i (botón «Borrar» del cuaderno). Devuelve su texto o None."""
    lista = _leer(dir_)
    if not 0 <= int(i) < len(lista):
        return None
    e = lista.pop(int(i))
    _guardar(dir_, lista)
    return e.get("texto")


def adelantar(dir_, i):
    """v3.10: botón «Empezar»: el encargo i pasa el PRIMERO (y, si ya estaba hecho, se vuelve a investigar)."""
    lista = _leer(dir_)
    if not 0 <= int(i) < len(lista):
        return None
    e = lista.pop(int(i))
    e["hecha"] = False
    lista.insert(0, e)
    _guardar(dir_, lista)
    return e.get("texto")


def listar(dir_):
    return _leer(dir_)


def texto_listar(dir_):
    lista = _leer(dir_)
    if not lista:
        return ("No me has dado ninguna pregunta todavía. Dime «pregúntate también: …» o «investiga …» y me pongo. "
                "Según sea, lo guardo (reflexión), lo programo o te hago la app.")
    out = ["Tus preguntas/encargos:"]
    for p in lista[-20:]:
        estado = "✔ hecha" if p.get("hecha") else ("↻ recurrente" if p.get("recurrente") else "• pendiente")
        out.append(f"\n{estado}: {p.get('texto', '')}")
    return "\n".join(out)
