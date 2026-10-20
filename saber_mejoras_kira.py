# -*- coding: utf-8 -*-
"""
saber_mejoras_kira.py - El SABER que Kira usa al programar una mejora.

Antes de pedir el código al cerebro, Kira busca:
  1. RECETAS probadas (recetas_*_kira.py): módulos completos que ya pasan el laboratorio. La más parecida a lo que
     pides se le da al cerebro como guía (los modelos pequeños copian bien un ejemplo que funciona).
  2. Lo que ha ESTUDIADO (su baúl de recuerdos: Wikipedia, documentación de Python, lo que le enseñas).
Lógica pura (sin red): se prueba en el PC.
"""
import re
import unicodedata


def _recetas():
    todas = []
    for nombre in ("recetas_graficos_kira", "recetas_ingenieria_kira"):
        try:
            mod = __import__(nombre)
            todas.extend(getattr(mod, "RECETAS", []))
        except ImportError:
            continue
    return todas


RECETAS = _recetas()


def normalizar(texto):
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _raices(texto):
    """Raíces de las palabras (5 primeras letras): «partículas» y «partícula» coinciden."""
    return {w[:5] for w in re.findall(r"[a-z0-9]{3,}", normalizar(texto))}


def buscar(pedido, n=2):
    """Las n recetas más parecidas al pedido: [(puntos, receta)], de más a menos parecida."""
    p = _raices(pedido)
    if not p:
        return []
    res = []
    for r in RECETAS:
        temas = _raices(r["temas"] + " " + r["titulo"] + " " + r["id"].replace("_", " "))
        puntos = len(p & temas)
        if puntos:
            res.append((puntos, r))
    res.sort(key=lambda x: -x[0])
    return res[:n]


def receta(id_o_nombre):
    q = normalizar(id_o_nombre).strip()
    for r in RECETAS:
        if q in (r["id"], normalizar(r["titulo"])) or q.replace(" ", "_") == r["id"]:
            return r
    hallado = buscar(q, 1)
    return hallado[0][1] if hallado else None


def contexto_para(pedido, recuerdos=None, local=False):
    """Texto que se añade al pedido de mejora: la técnica probada más parecida y lo que Kira ha estudiado."""
    partes = []
    tope_codigo = 2600 if local else 6000
    for _p, r in buscar(pedido, 1 if local else 2):
        codigo = r["codigo"].strip()
        if len(codigo) > tope_codigo:
            continue
        partes.append(f"Técnica ya probada que se parece a lo pedido («{r['titulo']}»). Idea: {r['idea']}\n"
                      f"Ejemplo que funciona (adáptalo, no lo copies si no encaja):\n```python\n{codigo}\n```")
    if recuerdos is not None:
        try:
            sabe = recuerdos.contexto(pedido, n=2, maximo=500 if local else 900)
        except Exception:
            sabe = ""
        if sabe:
            partes.append("Lo que sabes de este tema (de tus estudios):\n" + sabe)
    return "\n\n".join(partes)


def lista():
    return "\n".join(f"- {r['id']}: {r['titulo']}" for r in RECETAS)
