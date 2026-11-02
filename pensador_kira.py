# -*- coding: utf-8 -*-
"""
pensador_kira.py - El NÚCLEO de la curiosidad de Kira (compartido: móvil y portátil). Lógica pura, sin red ni Kivy.

La idea del dueño: que Kira no solo GUARDE lo que sabe, sino que lo CUESTIONE sola y constantemente: «¿por qué esto
funciona así?, ¿cómo se hace?, ¿para qué sirve?, ¿y si fuera de otra forma?». Y, como es programadora, que cuando la
pregunta sea de código no se quede en pensar: que EXPERIMENTE (escriba un programa y lo pruebe) para entenderlo.

Aquí va solo la parte PURA (se prueba sin nada):
  - generar_preguntas(semilla)      las preguntas que se hace;
  - clasificar_respuesta(texto)     seguridad (alta/media/baja) y si es una duda;
  - es_programable(texto)           si conviene PROBARLO con código;
  - Cuaderno (cargar/guardar/anotar/ya_pensada/proxima_semilla/texto/resumen);
  - pensar_una(estado, preguntar, estudiar, experimentar, ...)  un pensamiento entero, con todo inyectado.

Cada sitio (móvil / portátil) pone sus propias funciones `preguntar` (su cerebro), `estudiar` (su internet) y
`experimentar` (su editor seguro o su espacio aislado). HONESTO: lo que piensa son NOTAS; nunca se aplica solo
(para eso: su laboratorio + los dos toques del dueño). El cerebro se equivoca: por eso cada nota lleva su seguridad.
"""
import json
import os
import time
import unicodedata

MAX_NOTAS = 2000

SEMILLAS = [
    "una función", "un bucle", "la recursividad", "una lista", "un diccionario", "una pila", "una cola",
    "un árbol binario", "un grafo", "la complejidad de un algoritmo", "la ordenación rápida (quicksort)",
    "la búsqueda binaria", "una tabla hash", "la memoria caché", "un hilo (thread)", "un proceso",
    "el cifrado", "una función hash", "una petición HTTP", "una base de datos", "una expresión regular",
    "la programación orientada a objetos", "una excepción", "un puntero", "la pila de llamadas",
    "un cortafuegos", "el phishing", "la detección de anomalías", "una contraseña segura", "una clave pública",
]

_TIPOS_PREGUNTA = [
    "¿por qué {s} funciona así por dentro?",
    "¿cómo se hace o se construye {s}, paso a paso?",
    "¿para qué sirve {s} en la práctica, con un ejemplo?",
    "¿qué pasaría si {s} fallara o no existiera?",
    "¿en qué se parece y en qué se diferencia {s} de algo que ya conozco?",
]

_PROGRAMABLE = ("funcion", "bucle", "recursi", "lista", "diccionario", "pila", "cola", "arbol", "grafo",
                "algoritmo", "quicksort", "ordenac", "busqueda binaria", "tabla hash", "hash", "cache",
                "hilo", "thread", "proceso", "cifrado", "regex", "expresion regular", "objeto", "clase",
                "excepcion", "puntero", "anomalia", "contrasena")


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


def es_programable(texto):
    n = _norm(texto)
    return any(p in n for p in _PROGRAMABLE)


def generar_preguntas(semilla):
    return [p.format(s=semilla) for p in _TIPOS_PREGUNTA]


def clasificar_respuesta(texto):
    """(seguridad 'alta'|'media'|'baja', es_duda)."""
    t = _norm(texto)
    if len(t) < 25 or any(f in t for f in ("no lo se", "no se ", "no estoy seguro", "no tengo ni idea",
                                           "no puedo responder", "desconozco")):
        return "baja", True
    if any(f in t for f in ("creo que", "quiza", "quizas", "puede que", "tal vez", "no estoy del todo",
                            "probablemente", "me parece que")):
        return "media", False
    return "alta", False


def _vacio():
    return {"notas": [], "vistas": [], "desde": int(time.time()), "i": 0}


def cargar(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        for k, v in _vacio().items():
            d.setdefault(k, v)
        return d
    except (OSError, ValueError):
        return _vacio()


def guardar(estado, ruta):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False)
    os.replace(tmp, ruta)
    try:
        os.chmod(ruta, 0o600)
    except OSError:
        pass


def ya_pensada(estado, pregunta):
    return _norm(pregunta) in set(estado.get("vistas", []))


def anotar(estado, nota):
    clave = _norm(nota.get("pregunta", ""))
    if not clave or clave in set(estado.get("vistas", [])):
        return False
    estado.setdefault("notas", []).append(nota)
    estado.setdefault("vistas", []).append(clave)
    if len(estado["notas"]) > MAX_NOTAS:
        estado["notas"] = estado["notas"][-MAX_NOTAS:]
        estado["vistas"] = estado["vistas"][-MAX_NOTAS:]
    return True


def proxima_semilla(estado, semillas=None):
    semillas = semillas or SEMILLAS
    notas = estado.get("notas", [])
    i = estado.get("i", 0)
    estado["i"] = i + 1
    if notas and i % 3 == 2:
        base = notas[-1].get("semilla") or ""
        if base:
            return base + " (más a fondo)"
    return semillas[i % len(semillas)]


def pensar_una(estado, preguntar, estudiar=None, experimentar=None, comparar=None, semillas=None, ahora=None):
    """Un pensamiento: elige semilla + pregunta NUEVA, se responde, estudia si duda y, si es de código, EXPERIMENTA
    y (si puede) COMPARA su código con uno de fuera para mejorar. Todo inyectado. Devuelve la nota (o None)."""
    ahora = int(ahora if ahora is not None else time.time())
    semilla = proxima_semilla(estado, semillas)
    pregunta = next((q for q in generar_preguntas(semilla) if not ya_pensada(estado, q)), None)
    if pregunta is None:
        pregunta = f"¿qué más debería entender sobre {semilla}?"
        if ya_pensada(estado, pregunta):
            return None

    base = ("Piensa como programadora curiosa. Responde BREVE y claro. Si no lo sabes, di «NO LO SÉ».\n"
            "Pregunta: " + pregunta)
    try:
        respuesta = str(preguntar(base) or "")
    except Exception as e:                               # el cerebro no está listo, sin red, etc.: QUE SE VEA
        nota = {"cuando": ahora, "semilla": semilla, "pregunta": pregunta,
                "respuesta": f"(no pude pensar ahora: {e})", "seguridad": "baja", "duda": True,
                "fuente": "sin cerebro", "tipo": "idea"}
        anotar(estado, nota)
        return nota
    seguridad, duda = clasificar_respuesta(respuesta)
    fuente = "lo que sé"

    if duda and estudiar is not None:
        try:
            material = str(estudiar(pregunta) or "")
        except Exception:
            material = ""
        if material:
            respuesta = str(preguntar(base + "\n\nMe he informado y dice:\n" + material[:1500] +
                                      "\n\nAhora respóndete con esto.") or "") or respuesta
            seguridad, duda = clasificar_respuesta(respuesta)
            fuente = "estudiado"

    nota = {"cuando": ahora, "semilla": semilla, "pregunta": pregunta, "respuesta": respuesta.strip(),
            "seguridad": seguridad, "duda": duda, "fuente": fuente, "tipo": "idea"}

    if experimentar is not None and es_programable(semilla):
        try:
            exp = experimentar(pregunta, semilla)
        except Exception as e:
            exp = {"ok": False, "resultado": f"no pude experimentar: {e}"}
        if exp:
            nota["tipo"] = "experimento"
            nota["experimento"] = exp
            if exp.get("ok"):
                nota["seguridad"] = "alta" if seguridad != "baja" else "media"

    # Comparar su código con uno de fuera (para mejorar su técnica). Es una NOTA; nada se mete solo en su cerebro.
    if comparar is not None and es_programable(semilla):
        codigo_mio = (nota.get("experimento") or {}).get("codigo", "")
        try:
            comp = comparar(pregunta, semilla, codigo_mio)
        except Exception:
            comp = None
        if comp:
            nota["comparacion"] = comp

    anotar(estado, nota)
    return nota


def texto_cuaderno(estado, n=15):
    notas = estado.get("notas", [])[-n:]
    if not notas:
        return "El cuaderno está vacío. Cuando Kira piense, aquí verás sus preguntas y lo que fue entendiendo."
    marca = {"alta": "✔", "media": "~", "baja": "?"}
    out = [f"Cuaderno de Kira — {len(estado.get('notas', []))} pensamiento(s):"]
    for nt in notas:
        m = marca.get(nt.get("seguridad"), "~")
        etq = " [experimento]" if nt.get("tipo") == "experimento" else (" [duda]" if nt.get("duda") else "")
        resp = (nt.get("respuesta", "") or "").replace("\n", " ")[:160]
        out.append(f"\n{m}{etq} {nt.get('pregunta', '')}\n   -> {resp} ({nt.get('fuente', '')})")
        exp = nt.get("experimento")
        if exp:
            out.append(f"   . prueba: {'OK' if exp.get('ok') else 'fallo'} - {str(exp.get('resultado', ''))[:120]}")
        comp = nt.get("comparacion")
        if comp:
            out.append(f"   . comparé con {comp.get('fuente', 'otra fuente')}: {str(comp.get('resumen', ''))[:140]}")
    return "\n".join(out)


def resumen(estado):
    notas = estado.get("notas", [])
    if not notas:
        return "Kira aún no ha pensado nada. Dile «piensa» para que empiece a cuestionarse las cosas."
    exps = sum(1 for n in notas if n.get("tipo") == "experimento")
    dudas = sum(1 for n in notas if n.get("duda"))
    return (f"Kira lleva {len(notas)} pensamiento(s): {exps} con experimento y {dudas} duda(s) por resolver. "
            "Dile «tu cuaderno» para leer qué se ha ido preguntando. (Son notas suyas; nada se aplica solo.)")
