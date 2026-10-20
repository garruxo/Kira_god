# -*- coding: utf-8 -*-
"""
juego_realista_kira.py - «Kira, hazme un juego realista de un caballero que esquiva dragones»:
  1. Kira entiende quién es el protagonista, qué hay que esquivar, qué se recoge y dónde pasa (con su cerebro o
     Claude; si no hay, lo saca de la frase);
  2. el PINTOR dibuja el escenario y los personajes en estilo realista (los personajes, recortados sin fondo);
  3. escribe el JUEGO (un programa normal del editor, que puedes leer y cambiar) que usa esos dibujos.
Cualquier juego puede tener dibujos así: atributos «sprites» y «dibujos» y la pieza imagen() del motor.
Lógica pura (sin Kivy).
"""
import json
import re
import unicodedata

import sprites_kira as spk

ESTILO_PERSONAJE = ("only one, alone, full body, centered, isolated on a pure white background, realistic photo, "
                    "highly detailed, no text")
ESTILO_FONDO = "empty scene with no characters, wide view, realistic photo, natural light, highly detailed, game background"

SISTEMA_PLAN = (
    "Diseñas un juego móvil sencillo de «esquivar y recoger» con gráficos realistas a partir de lo que pide el usuario. "
    "Responde SOLO con un objeto JSON: {\"titulo\": str (español, corto), \"protagonista\": str (español), "
    "\"enemigo\": str (español, lo que hay que esquivar), \"premio\": str (español, lo que se recoge), "
    "\"escenario\": str (español), \"protagonista_en\": str, \"enemigo_en\": str, \"premio_en\": str, "
    "(personajes y objetos en SINGULAR: uno solo) "
    "\"escenario_en\": str} — los *_en son descripciones visuales en INGLÉS de 6 a 15 palabras para pintarlos.")

_RE_PEDIDO = re.compile(
    r"^(?:juego|jueguito)\s+(?:realista|real|realistas|con\s+gr[aá]ficos\s+(?:reales|realistas)|"
    r"fotorrealista|con\s+im[aá]genes\s+(?:reales|realistas))\b\s*(?:de|del|con|sobre)?\s*(?P<resto>.*)$", re.I)


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def es_realista(pedido):
    """'juego realista de …' (lo que devuelve programar_kira.pedido_programa) -> el resto, o None."""
    t = " ".join(str(pedido or "").split())
    m = _RE_PEDIDO.match(t)
    if m:
        return m.group("resto").strip(" ,.:")
    if re.match(r"^(?:juego|jueguito)\b", t, re.I) and re.search(r"\b(realistas?|fotorrealista|gr[aá]ficos\s+reales)\b", t, re.I):
        resto = re.sub(r"\s*\b(?:con\s+gr[aá]ficos\s+(?:reales|realistas)|realistas?|fotorrealista)\b", "", t, flags=re.I)
        resto = re.sub(r"^(?:juego|jueguito)\s*(?:de|del|con|sobre)?\s*", "", resto, flags=re.I)
        return resto.strip(" ,.:")
    return None


def plan_simple(resto, traducir=None):
    """Sin cerebro: «un caballero que esquiva dragones y recoge monedas en un castillo»."""
    t = " ".join(str(resto or "").split())
    prota, enemigo, premio, lugar = t or "un explorador", "rocas que caen", "monedas de oro", "un paisaje"
    m = re.match(r"^(?P<p>.+?)\s+que\s+(?:esquiva|evita|huye\s+de|escapa\s+de)\s+(?P<e>.+?)"
                 r"(?:\s+y\s+(?:recoge|coge|come|atrapa)\s+(?P<r>.+?))?(?:\s+(?:en|por)\s+(?P<l>.+))?$", t, re.I)
    if m:
        prota, enemigo = m.group("p"), m.group("e")
        premio = m.group("r") or premio
        lugar = m.group("l") or lugar
    else:
        m = re.match(r"^(?P<p>.+?)\s+(?:en|por)\s+(?P<l>.+)$", t, re.I)
        if m:
            prota, lugar = m.group("p"), m.group("l")
    tr = traducir or (lambda x: x)
    return normalizar({"titulo": (prota[:1].upper() + prota[1:])[:40], "protagonista": prota, "enemigo": enemigo,
                       "premio": premio, "escenario": lugar, "protagonista_en": tr(prota), "enemigo_en": tr(enemigo),
                       "premio_en": tr(premio), "escenario_en": tr(lugar)})


def normalizar(d):
    if not isinstance(d, dict):
        raise ValueError("el plan no es un objeto")
    sal = {}
    for k, defecto in (("titulo", "Juego realista"), ("protagonista", "el héroe"), ("enemigo", "obstáculos"),
                       ("premio", "monedas"), ("escenario", "un paisaje"), ("protagonista_en", "a brave explorer"),
                       ("enemigo_en", "a falling rock"), ("premio_en", "a shiny gold coin"),
                       ("escenario_en", "a beautiful landscape")):
        v = " ".join(str(d.get(k) or "").split())[:120]
        sal[k] = re.sub(r"[\"'\\{}<>\[\]]", "", v) or defecto
    sal["carpeta"] = spk.nombre_valido(_plano(sal["titulo"]))[:30] or "juego_realista"
    return sal


def plan_desde_ia(texto):
    m = re.search(r"\{.*\}", str(texto or ""), re.S)
    if not m:
        raise ValueError("sin JSON")
    return normalizar(json.loads(m.group(0)))


def singular(texto):
    """«dragons» -> «a dragon»: un personaje de juego es UNO (en plural el pintor dibuja varios)."""
    palabras = str(texto or "").split()
    sal = []
    for p in palabras:
        if len(p) > 3 and p.lower().endswith("s") and not p.lower().endswith(("ss", "us", "is")):
            p = p[:-3] + "y" if p.lower().endswith("ies") else p[:-1]
        sal.append(p)
    t = " ".join(sal)
    return t if re.match(r"^(?:a|an|one|the)\b", t, re.I) else ("an " if t[:1].lower() in "aeiou" else "a ") + t


def dibujos(plan):
    """{nombre: descripción en inglés} con el estilo realista ya puesto."""
    return {"fondo": f"{plan['escenario_en']}, {ESTILO_FONDO}",
            "jugador": f"{singular(plan['protagonista_en'])}, {ESTILO_PERSONAJE}",
            "enemigo": f"{singular(plan['enemigo_en'])}, {ESTILO_PERSONAJE}",
            "premio": f"{singular(plan['premio_en'])}, {ESTILO_PERSONAJE}"}


def codigo(plan):
    """El programa del juego (se abre en el editor: puedes leerlo y cambiarlo)."""
    d = dibujos(plan)
    lineas_dibujos = "\n".join(f"        {k!r}: {v!r}," for k, v in d.items())
    return f'''from motor_juegos_kira import Juego

# Juego realista hecho por Kira: los dibujos los pinta su pintor (estilo real) y se guardan en la carpeta «sprites».
# Para cambiar un personaje, cambia su descripción en «dibujos» y dile a Kira «pinta los dibujos del juego».


class JuegoRealista(Juego):
    titulo = {plan["titulo"]!r}
    instrucciones = "Mueve a {plan["protagonista"]} con el dedo: esquiva {plan["enemigo"]} y recoge {plan["premio"]}."
    sprites = {plan["carpeta"]!r}
    dibujos = {{
{lineas_dibujos}
    }}

    def preparar(self):
        self.imagen(0, 0, self.ancho, self.alto, "fondo")          # el escenario, a pantalla completa
        self.jugador = self.imagen(140, 30, 84, 84, "jugador")
        self.reloj, self.ritmo = 0.0, 1.1                         # cada cuánto cae algo (cada vez más rápido)

    def toca(self, a, b):
        """Choque «justo»: los dibujos tienen bordes transparentes, así que se mira solo su parte central."""
        ax1, ay1, ax2, ay2 = a.caja()
        bx1, by1, bx2, by2 = b.caja()
        ma, mb = a.w * 0.22, b.w * 0.22
        return ax1 + ma < bx2 - mb and bx1 + mb < ax2 - ma and ay1 + ma < by2 - mb and by1 + mb < ay2 - ma

    def actualizar(self, dt):
        if self.dedo:                                              # el protagonista sigue a tu dedo
            self.jugador.x = self.dedo[0] - self.jugador.w / 2
        self.limitar(self.jugador)
        self.reloj += dt
        if self.reloj >= self.ritmo:
            self.reloj = 0.0
            self.ritmo = max(0.4, self.ritmo * 0.97)
            if self.azar(0, 1) < 0.7:
                cosa = self.imagen(self.azar(0, self.ancho - 72), self.alto, 72, 72, "enemigo")
                cosa.datos["tipo"] = "enemigo"
            else:
                cosa = self.imagen(self.azar(0, self.ancho - 56), self.alto, 56, 56, "premio")
                cosa.datos["tipo"] = "premio"
            cosa.vy = -self.azar(150, 240) - self.puntos * 1.5      # caen más deprisa cuantos más puntos llevas
        for e in self.con_etiqueta("enemigo"):
            if self.toca(e, self.jugador):
                self.borrar(e)
                self.vidas -= 1
                if self.vidas <= 0:
                    self.fin("¡Te han alcanzado!")
            elif e.y < -e.h:
                self.borrar(e)
        for p in self.con_etiqueta("premio"):
            if self.toca(p, self.jugador):
                self.borrar(p)
                self.puntos += 10
            elif p.y < -p.h:
                self.borrar(p)
'''
