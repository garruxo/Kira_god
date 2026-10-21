# -*- coding: utf-8 -*-
"""
saber_mejoras_kira.py - El SABER que Kira usa al programar una mejora.

Antes de pedir el código al cerebro, Kira busca:
  1. RECETAS probadas (recetas_*_kira.py y saber_avanzado_kira.py): módulos completos que ya pasan el laboratorio. La más parecida a lo que
     pides se le da al cerebro como guía (los modelos pequeños copian bien un ejemplo que funciona).
  2. Lo que ha ESTUDIADO (su baúl de recuerdos: Wikipedia, documentación de Python, lo que le enseñas).
Lógica pura (sin red): se prueba en el PC.
"""
import re
import unicodedata


def _recetas():
    todas = []
    for nombre in ("recetas_graficos_kira", "recetas_ingenieria_kira", "saber_avanzado_kira"):
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


# palabras que no dicen nada del tema (si no, «una IA que…» en un título encajaría con cualquier pedido)
_VACIAS = {"una", "uno", "unos", "unas", "que", "con", "los", "las", "del", "por", "para", "como", "sin", "mas",
           "muy", "pero", "sus", "este", "esta", "esto", "ese", "esa", "eso", "hay", "son", "ser", "les", "nos",
           "mis", "tus", "quiero", "hazme", "dame", "necesito", "puedes", "algo", "cosa", "the", "and", "for"}


def _raices(texto):
    """Raíces de las palabras (5 primeras letras): «partículas» y «partícula» coinciden. «2d» y «3d» también cuentan."""
    return {w[:5] for w in re.findall(r"[a-z0-9]{3,}|\b[23]d\b", normalizar(texto)) if w not in _VACIAS}


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


def contexto_para(pedido, recuerdos=None, local=False, para_editor=False):
    """Texto que se añade al pedido de mejora: la técnica probada más parecida y lo que Kira ha estudiado.
    Si el código de la receta es demasiado largo para ese cerebro, va solo la idea (y su coste), que también ayuda.
    para_editor=True: para un PROGRAMA del editor (las recetas de ingeniería van como programa con sus pruebas)."""
    partes = []
    tope_codigo = 2400 if local else 6000              # el cerebro del móvil tiene poca memoria de trabajo
    for _p, r in buscar(pedido, 1 if local else 2):
        codigo = (programa(r) if para_editor and r.get("prueba") else r["codigo"]).strip()
        if para_editor and "def registrar" in codigo:
            codigo = "# (receta en forma de MÓDULO de Kira: en el editor, un juego es una clase que hereda de Juego)\n" + codigo
        coste = f" Coste: {r['complejidad']}." if r.get("complejidad") else ""
        if len(codigo) > tope_codigo:
            partes.append(f"Técnica ya probada que se parece a lo pedido («{r['titulo']}»). Idea: {r['idea']}{coste}")
            continue
        partes.append(f"Técnica ya probada que se parece a lo pedido («{r['titulo']}»). Idea: {r['idea']}{coste}\n"
                      f"Ejemplo que funciona (adáptalo, no lo copies si no encaja):\n```python\n{codigo}\n```")
    if recuerdos is not None:
        try:
            sabe = recuerdos.contexto(pedido, n=2, maximo=500 if local else 900)
        except Exception:
            sabe = ""
        if sabe:
            partes.append("Lo que sabes de este tema (de tus estudios):\n" + sabe)
    return "\n\n".join(partes)


def programa(r):
    """El código de la receta listo para el editor: si tiene pruebas, con ellas impresas debajo (así «Ejecutar»
    enseña lo que hace)."""
    if r.get("prueba"):
        try:
            import recetas_ingenieria_kira as ri
            return ri.demo(r)
        except ImportError:
            pass
    return r["codigo"].strip() + "\n"


def area(r):
    return r.get("area") or "Gráficos y juegos"


def lista(filtro=""):
    """Las recetas agrupadas por área. Con filtro («ingeniería», «grafos», «gráficos»…) solo las de esas áreas."""
    f = normalizar(filtro).strip()
    if f.startswith("ingenier"):
        try:
            import recetas_ingenieria_kira as ri
            ids = {r["id"] for r in ri.RECETAS}
        except ImportError:
            ids = set()
        elegidas = [r for r in RECETAS if r["id"] in ids]
    elif f:
        elegidas = [r for r in RECETAS if f in normalizar(area(r))]          # «programación avanzada»: esa área
        elegidas = elegidas or [r for r in RECETAS if _raices(f) & _raices(area(r))]
    else:
        elegidas = RECETAS
    grupos = {}
    for r in elegidas:
        grupos.setdefault(area(r), []).append(r)
    return "\n".join(f"{a}:\n" + "\n".join(f"- {r['id'].replace('_', ' ')}: {r['titulo']}" for r in rs)
                     for a, rs in grupos.items())
