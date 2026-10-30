# -*- coding: utf-8 -*-
"""
experimentos_kira.py - Kira INVENTA código nuevo y experimental (sin instalar nada y sin tocarse a sí misma).

«Kira, experimenta con colores y música», «inventa un algoritmo nuevo para repartir árboles en un mapa»,
«hazme un código experimental de física»:
  1. PLAN: busca en su saber las técnicas probadas que tienen que ver (recetas de ingeniería, programación avanzada,
     diseño y gráficos) y se plantea 2 o 3 HIPÓTESIS distintas: mezclar dos técnicas, llevar una técnica a otro
     campo, o inventar una variante con una regla nueva.
  2. Para cada hipótesis escribe un programa (su cerebro o Claude), lo prueba en MODO SEGURO (el del editor: sin
     archivos, red ni sistema, con tiempo máximo) y, si falla, lo corrige con el error.
  3. PUNTÚA cada resultado (funciona, muestra resultados, no es una copia de la receta, no es enorme) y se queda
     con el mejor; si está Claude, lo revisan juntos (acuerdo_kira).
  4. Lo apunta todo en su CUADERNO DE EXPERIMENTOS («mis experimentos») y guarda la LECCIÓN en el baúl (qué
     funcionó y qué falló), así el siguiente experimento parte de lo aprendido.
  5. Te deja el mejor en el editor. Lo experimental se queda en el editor: si te gusta y quieres que sea parte de
     Kira, «implementa este código» y los dos toques de siempre.
Lógica pura (sin Kivy ni red): se prueba en el PC.
"""
import difflib
import json
import os
import re
import threading
import time
import unicodedata

MAX_EXPERIMENTOS = 60
FUENTE_LECCION = "experimentos de Kira"

ENFOQUES = {
    "mezcla": ("Mezclar dos técnicas",
               "COMBINA las dos técnicas de referencia en un programa NUEVO que no sea ninguna de las dos: que una "
               "alimente a la otra o que juntas resuelvan algo que por separado no pueden."),
    "otro_campo": ("Llevar una técnica a otro campo",
                   "Coge la idea de la técnica de referencia y APLÍCALA a un campo distinto del suyo (por ejemplo, "
                   "un algoritmo de grafos para diseñar, o uno de diseño para un juego), de forma original."),
    "variante": ("Inventar una variante",
                 "Inventa una VARIANTE nueva: cambia una regla, añade una restricción o generaliza la idea, y MIDE "
                 "con datos de ejemplo si la variante es mejor o peor que la original (imprime la comparación)."),
    "mejorar": ("Mejorar un código que ya funciona",
                "PARTE del código de referencia (que ya funciona) y MEJÓRALO: hazlo más rápido, más claro o más "
                "completo SIN cambiar lo que hace. Imprime una comparación (antes/después) que demuestre la mejora."),
}

_MEJORAR = re.compile(r"\b(mejora|mejorando|mejorar|optimiz\w*|perfeccion\w*|a\s+partir\s+de\s+lo\s+que\s+sabes|"
                      r"con\s+lo\s+que\s+(?:sabes|has\s+aprendido|aprendiste))", re.I)


def quiere_mejorar(texto):
    """¿El experimento pide MEJORAR/optimizar algo ya aprendido (en vez de inventar desde cero)?"""
    return bool(_MEJORAR.search(" " + str(texto or "") + " "))

INSTRUCCIONES_EXPERIMENTO = (
    "Es un EXPERIMENTO: inventa algo NUEVO, no copies el ejemplo. Al principio, un comentario «# Hipótesis: …» "
    "(qué quieres comprobar). Usa datos de ejemplo dentro del programa (o random con semilla fija) y termina "
    "imprimiendo lo que DESCUBRE con números o un dibujo de texto, y una línea «Conclusión: …».")


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# =====================================================================================
#  ENTENDER EL PEDIDO
# =====================================================================================
_PIDE = re.compile(
    r"^(?:por\s+favor\s+)?(?:"
    r"experimenta(?:r)?\s+(?:con|sobre|en)\s+(?P<a>.+)"
    r"|(?:haz(?:me)?|crea(?:me)?|prueba)\s+(?:un|otro)\s+experimento\s+(?:de|con|sobre|para|que)\s+(?P<b>.+)"
    r"|(?:inventa(?:te|me)?|(?:crea|haz|escribe)(?:me)?\s+(?:algo|un\s+c[oó]digo|un\s+programa)\s+(?:nuevo|original)\s*)"
    r"\s*(?:un|una|otro|otra|algo)?\s*(?P<cn>c[oó]digo|programa|algoritmo|t[eé]cnica|juego|efecto|sistema|m[eé]todo)?"
    r"\s*(?:nuevo|nueva|original|experimental)?\s*(?:de|del|para|que|con|sobre)?\s+(?P<c>.+)"
    r"|(?:haz(?:me)?|crea(?:me)?|escr[ií]be(?:me)?)\s+(?:un|una)\s+(?:c[oó]digo|programa|algoritmo)\s+experimental\s*"
    r"(?:de|del|para|que|con|sobre)?\s+(?P<d>.+)"
    r"|c[oó]digo\s+experimental\s+(?:de|del|para|que|con|sobre)\s+(?P<e>.+)"
    r")$", re.I | re.S)


def pedido_experimento(texto):
    """El tema del experimento («colores y música») si la frase lo pide; si no, None."""
    t = " ".join(str(texto or "").split()).strip(" .!¡?¿")
    t = re.sub(r"^(?:oye\s+|hola\s+)?kira\b[\s,:;.]*", "", t, flags=re.I)
    m = _PIDE.match(t)
    if not m:
        return None
    tema = next(m.group(k) for k in "abcde" if m.group(k)).strip(" ,.:")
    if _plano(tema) in ("algo", "eso", "esto", "nuevo", "algo nuevo") or len(tema) < 2:
        return None
    if (m.group("cn") or "").lower() == "juego" and not _plano(tema).startswith("juego"):
        tema = "un juego de " + tema
    return tema


# =====================================================================================
#  PLAN: QUÉ HIPÓTESIS PROBAR
# =====================================================================================
def plan(tema, n=3, recetas=None, mejorar=False):
    """[{'enfoque', 'titulo', 'instruccion', 'recetas': [receta, …], 'codigo_base'?}] con n hipótesis. Usa las
    técnicas probadas más parecidas al tema; si no hay ninguna parecida, inventa desde cero. mejorar=True: la
    primera hipótesis es MEJORAR el código de la receta aprendida más parecida (a partir de lo que sabe)."""
    import saber_mejoras_kira as sm_
    if recetas is None:
        recetas = [r for _p, r in sm_.buscar(tema, n=4)]
    sal = []
    if mejorar and recetas:
        titulo, instr = ENFOQUES["mejorar"]
        sal.append({"enfoque": "mejorar", "titulo": titulo, "instruccion": instr, "recetas": recetas[:1],
                    "codigo_base": recetas[0].get("codigo", "")})
    hip = []
    if len(recetas) >= 2:
        hip.append(("mezcla", recetas[:2]))
    if recetas:
        hip.append(("otro_campo", recetas[:1]))
        hip.append(("variante", recetas[1:2] or recetas[:1]))
    else:
        hip = [("variante", []), ("mezcla", []), ("otro_campo", [])]
    for enfoque, rs in hip:
        if len(sal) >= max(1, n):
            break
        titulo, instr = ENFOQUES[enfoque]
        if not rs:
            instr = "No hay técnica de referencia: inventa desde cero. " + instr.split(":")[0] + "."
        sal.append({"enfoque": enfoque, "titulo": titulo, "instruccion": instr, "recetas": rs})
    return sal[:max(1, n)]


def pedido_de(tema, hipotesis, local=False):
    """El texto que se le da al cerebro para UNA hipótesis (con las ideas de las técnicas, no su código entero:
    así no la copia)."""
    refs = []
    for r in hipotesis["recetas"]:
        refs.append(f"- «{r['titulo']}»: {r['idea'][:300 if local else 600]}")
    base = hipotesis.get("codigo_base")
    if base:                                             # MEJORAR: se le da el código que ya funciona para partir de él
        tope = 1200 if local else 3000
        base_txt = ("\nCódigo que YA FUNCIONA (mejóralo, no lo dejes igual):\n```python\n"
                    + base.strip()[:tope] + "\n```\n")
    else:
        base_txt = ""
    return (f"programa EXPERIMENTAL sobre: {tema}\n\nHipótesis a probar ({hipotesis['titulo']}): "
            f"{hipotesis['instruccion']}\n" + base_txt + ("Técnicas de referencia (ya probadas):\n" + "\n".join(refs)
                                                          + "\n" if refs else "") + "\n" + INSTRUCCIONES_EXPERIMENTO)


# =====================================================================================
#  PUNTUAR
# =====================================================================================
def parecido_a_recetas(codigo, recetas):
    """0..1: cuánto se parece al código de las recetas de referencia (1 = copia)."""
    mejor = 0.0
    for r in recetas or []:
        try:
            mejor = max(mejor, difflib.SequenceMatcher(None, r["codigo"], codigo, autojunk=False).quick_ratio()
                        if len(codigo) > 4 * len(r["codigo"]) else
                        difflib.SequenceMatcher(None, r["codigo"], codigo, autojunk=False).ratio())
        except Exception:
            continue
    return mejor


def puntuar(ok, dato, codigo, recetas=()):
    """(puntos 0..100, [notas]). Lo que cuenta: que funcione, que muestre resultados y una conclusión, que sea
    original y que no sea enorme."""
    if not ok:
        return 0, ["no funciona"]
    p, notas = 50, ["funciona en modo seguro"]
    salida = (dato or {}).get("salida", "") if isinstance(dato, dict) else ""
    juego = isinstance(dato, dict) and dato.get("juego")
    if juego:
        p += 20
        notas.append("es un juego que se puede jugar")
    elif salida.strip():
        p += 15
        notas.append("muestra resultados")
        if re.search(r"conclusi[oó]n", salida, re.I):
            p += 10
            notas.append("saca una conclusión")
        if re.search(r"\d", salida):
            p += 5
            notas.append("con números")
    if re.search(r"^\s*#\s*hip[oó]tesis", codigo, re.I | re.M):
        p += 5
        notas.append("dice su hipótesis")
    copia = parecido_a_recetas(codigo, recetas)
    if copia > 0.8:
        p -= 35
        notas.append(f"se parece demasiado a la técnica de referencia ({copia:.0%})")
    elif copia < 0.5:
        p += 10
        notas.append("es original")
    lineas = codigo.count("\n") + 1
    if lineas > 260:
        p -= 10
        notas.append(f"muy largo ({lineas} líneas)")
    avisos = (dato or {}).get("avisos", []) if isinstance(dato, dict) else []
    if avisos:
        p -= 5 * len(avisos)
        notas.extend(avisos)
    return max(1, min(100, p)), notas


def hipotesis_del_codigo(codigo):
    m = re.search(r"^\s*#\s*hip[oó]tesis\s*:?\s*(.+)$", codigo or "", re.I | re.M)
    return m.group(1).strip()[:200] if m else ""


def conclusion_de(salida):
    m = None
    for m in re.finditer(r"conclusi[oó]n\s*:?\s*(.+)", salida or "", re.I):
        pass
    return m.group(1).strip()[:240] if m else ""


# =====================================================================================
#  LECCIÓN (al baúl) E INFORME
# =====================================================================================
def leccion(tema, resultados):
    """Texto corto de lo aprendido para el baúl de recuerdos."""
    partes = []
    for r in resultados:
        if r["ok"]:
            c = r.get("conclusion") or r.get("hipotesis") or ""
            partes.append(f"«{r['titulo']}» funcionó ({r['puntos']} puntos)" + (f": {c}" if c else ""))
        else:
            partes.append(f"«{r['titulo']}» falló ({str(r.get('motivo') or 'sin motivo')[:140]})")
    return f"Experimento sobre {tema}: " + "; ".join(partes) + "."


def informe(tema, resultados, elegido):
    lineas = [f"EXPERIMENTO: {tema}"]
    for i, r in enumerate(resultados, 1):
        marca = "★" if elegido is not None and r is elegido else ("✓" if r["ok"] else "✗")
        lineas.append(f"{marca} Hipótesis {i} — {r['titulo']}"
                      + (f" (con {', '.join(r['recetas'])})" if r.get("recetas") else ""))
        if r.get("hipotesis"):
            lineas.append(f"   Idea: {r['hipotesis']}")
        if r["ok"]:
            lineas.append(f"   {r['puntos']} puntos: {', '.join(r['notas'])}")
            if r.get("conclusion"):
                lineas.append(f"   Conclusión: {r['conclusion']}")
        else:
            lineas.append(f"   No funcionó: {str(r.get('motivo') or '')[:200]}")
    if elegido is None:
        lineas.append("Ninguna hipótesis ha dado un programa que funcione. Lo apunto para la próxima.")
    return "\n".join(lineas)


# =====================================================================================
#  CUADERNO DE EXPERIMENTOS
# =====================================================================================
class Cuaderno:
    def __init__(self, ruta):
        self.ruta = ruta
        self._lock = threading.Lock()
        try:
            with open(ruta, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = []
        self.lista = [e for e in d if isinstance(e, dict)] if isinstance(d, list) else []

    def _guardar(self):
        os.makedirs(os.path.dirname(self.ruta) or ".", exist_ok=True)
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.lista, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta)

    def anadir(self, tema, resultados, elegido, acuerdo=None):
        with self._lock:
            n = (self.lista[-1]["n"] + 1) if self.lista else 1
            e = {"n": n, "fecha": time.strftime("%Y-%m-%d %H:%M"), "tema": str(tema)[:160], "acuerdo": acuerdo,
                 "hipotesis": [{"titulo": r["titulo"], "ok": r["ok"], "puntos": r.get("puntos", 0),
                                "motivo": str(r.get("motivo") or "")[:200], "nombre": r.get("nombre") or "",
                                "conclusion": r.get("conclusion", ""),
                                "codigo": (r.get("codigo") or "")[:60000] if r["ok"] else ""} for r in resultados],
                 "mejor": resultados.index(elegido) if elegido is not None else None}
            self.lista.append(e)
            self.lista = self.lista[-MAX_EXPERIMENTOS:]
            self._guardar()
            return n

    def buscar(self, n):
        return next((e for e in self.lista if e.get("n") == n), None)

    def codigo(self, n, hipotesis=None):
        """(nombre, código) del experimento n (el mejor, o la hipótesis indicada, contando desde 1)."""
        e = self.buscar(n)
        if e is None:
            return None
        i = (hipotesis - 1) if hipotesis else e.get("mejor")
        if i is None or not (0 <= i < len(e["hipotesis"])) or not e["hipotesis"][i].get("codigo"):
            return None
        h = e["hipotesis"][i]
        return h.get("nombre") or f"experimento_{n}", h["codigo"]

    def texto(self, ultimos=12):
        if not self.lista:
            return ("Mi cuaderno de experimentos está vacío. Pídeme «experimenta con …» o «inventa un algoritmo "
                    "nuevo para …».")
        lineas = [f"Cuaderno de experimentos ({len(self.lista)}):"]
        for e in self.lista[-ultimos:][::-1]:
            buenas = sum(1 for h in e["hipotesis"] if h["ok"])
            mejor = e["hipotesis"][e["mejor"]] if e.get("mejor") is not None else None
            lineas.append(f"{e['n']}. {e['tema']} ({e['fecha']}): {buenas} de {len(e['hipotesis'])} hipótesis "
                          "funcionan" + (f"; la mejor, «{mejor['titulo']}» ({mejor['puntos']} puntos)" if mejor else ""))
        lineas.append("Di «abre el experimento N» para llevarlo al editor (o «abre el experimento N hipótesis 2»).")
        return "\n".join(lineas)
