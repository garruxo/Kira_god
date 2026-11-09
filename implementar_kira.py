# -*- coding: utf-8 -*-
"""v3.20: «implementa la receta X» / «usa la solución X en Kira» — meter en Kira algo que YA tiene (una receta probada
o una solución de su cuaderno) sin que el cerebro lo vuelva a escribir. Pasa por el laboratorio y queda esperando
tus DOS toques, como cualquier mejora (nunca se instala sola).

Lógica PURA: `orden(texto)` reconoce la frase (sin tildes y con faltas típicas: «solucin», «contrasena»).
"""
import re
import unicodedata

_VERBOS = (r"(?:implementa(?:me|r)?|instala(?:me|r)?|pon(?:me|te|er)?|aplica(?:r)?|usa(?:r)?|mete(?:me|te|r)?|"
           r"integra(?:r)?|anade(?:me|te)?|activa(?:r)?)")
_RECETA = re.compile(r"^(?:por favor\s+)?(?:kira[\s,]+)?" + _VERBOS +
                     r"\s+(?:la\s+|una\s+|esta\s+|tu\s+)?receta\s+(?:de\s+(?:la\s+|el\s+|una?\s+)?|del\s+|llamada\s+)?"
                     r"(?P<x>.+?)(?:\s+(?:en|a|dentro de)\s+(?:kira(?:\s?os)?|ti(?:\s+misma)?|mi|el sistema))?$")
_SOLUCION = re.compile(r"^(?:por favor\s+)?(?:kira[\s,]+)?" + _VERBOS +
                       r"\s+(?:la\s+|esta\s+|tu\s+|mi\s+)?soluc(?:io|i|o)n\s+(?:de\s+(?:la\s+|el\s+)?|del\s+|para\s+)?"
                       r"(?P<x>.+?)(?:\s+(?:en|a|dentro de)\s+(?:kira(?:\s?os)?|ti(?:\s+misma)?|mi|el sistema))?$")


def plano(texto):
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip().strip(" .!?¡¿«»\"'")


def orden(texto):
    """('receta', nombre) | ('solucion', nombre) | None."""
    t = plano(texto)
    for tipo, rx in (("receta", _RECETA), ("solucion", _SOLUCION)):
        m = rx.match(t)
        if m and len(m.group("x").strip()) >= 2:
            return (tipo, m.group("x").strip(" .:«»\"'"))
    return None


def buscar_solucion(soluciones, nombre):
    """La solución guardada que mejor casa con `nombre` (tema exacto, o que lo contenga, o con más palabras en común).
    Devuelve (tema, solucion) o (None, None)."""
    n = plano(nombre)
    if not n or not soluciones:
        return None, None
    temas = {plano(k): k for k in soluciones}
    if n in temas:
        return temas[n], soluciones[temas[n]]
    for pt, k in temas.items():
        if n in pt or pt in n:
            return k, soluciones[k]
    palabras = {p for p in re.findall(r"[a-z0-9]{3,}", n)}
    mejor, puntos = None, 0
    for pt, k in temas.items():
        p = len(palabras & set(re.findall(r"[a-z0-9]{3,}", pt)))
        if p > puntos:
            mejor, puntos = k, p
    return (mejor, soluciones[mejor]) if mejor and puntos >= max(1, len(palabras) // 2) else (None, None)
