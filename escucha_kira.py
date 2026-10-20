# -*- coding: utf-8 -*-
"""
escucha_kira.py - Escucha PERMANENTE con palabra de activación «Kira» y la luz de neón de la portada.
Lógica PURA (sin Kivy, sin micrófono): se puede probar entera en el PC.

Cómo funciona la escucha:
  - Kira oye frases sueltas (lo que le pasa el reconocimiento de voz del móvil) y las deja en un BORRADOR en la RAM.
  - Todo lo del borrador que tenga más de 15 segundos se BORRA solo. Nunca se guarda en disco ni sale del móvil.
  - Si en una frase aparece su nombre («Kira»), el borrador se para y Kira atiende:
        «Kira, ¿qué hora es?»  -> orden: «¿qué hora es?»
        «Kira»  (y nada más)    -> se queda ATENTA unos segundos: la siguiente frase es la orden.
  - Mientras no oiga su nombre, no contesta nada.
"""
import math
import re
import time
import unicodedata

VENTANA = 15.0            # segundos que dura una frase en el borrador
ATENTA = 8.0              # segundos que espera la orden después de oír solo «Kira»
NOMBRES = ("kira", "kyra", "kirah", "kiraa", "quira", "kiraaa")   # cómo suele escribirlo el reconocedor de voz


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


_NOMBRE = re.compile(r"\b(?:" + "|".join(NOMBRES) + r")\b")


def fonetica(palabra):
    """Cómo SUENA una palabra en español, simplificado: «quiera» -> «kiera», «kyra» -> «kira»."""
    w = _norm(palabra)
    w = re.sub(r"[^a-zñ]", "", w).replace("qu", "k").replace("h", "").replace("y", "i")
    w = re.sub(r"c(?=[aou])", "k", w)
    return w


def _distancia(a, b):
    previa = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        actual = [i]
        for j, cb in enumerate(b, 1):
            actual.append(min(previa[j] + 1, actual[j - 1] + 1, previa[j - 1] + (ca != cb)))
        previa = actual
    return previa[-1]


def suena_a_kira(palabra):
    """Para la PRIMERA palabra de una frase: el reconocedor sin conexión puede no conocer «Kira» y escribir
    «quiera», «kiara» o «quira». Se acepta si suena casi igual y empieza por el sonido K («quiero», «mira» no)."""
    f = fonetica(palabra)
    return f.startswith("ki") and len(f) <= 6 and _distancia(f, "kira") <= 1


def contiene_nombre(texto):
    """(True, lo_que_va_después_del_nombre) si la frase nombra a Kira; (False, '') si no."""
    original = str(texto or "")
    m = _NOMBRE.search(_norm(original))
    if not m:
        partes = original.strip().split(None, 1)
        if partes and suena_a_kira(partes[0]):
            resto = re.sub(r"^[\s,.:;!¡?¿-]+", "", partes[1] if len(partes) > 1 else "").strip()
            return True, resto
        return False, ""
    # el texto normalizado tiene la misma longitud que el original salvo tildes combinadas: se busca en el original
    m2 = re.search(r"\b(?:k|q)[iíy]r[aá]+h?\b", original, re.I)
    resto = original[m2.end():] if m2 else original[m.end():]
    resto = re.sub(r"^[\s,.:;!¡?¿-]+", "", resto).strip()
    return True, resto


class Escucha:
    def __init__(self, reloj=time.monotonic, ventana=VENTANA, atenta=ATENTA):
        self._reloj = reloj
        self.ventana, self.espera = float(ventana), float(atenta)
        self.borrador = []             # [(instante, frase)] solo en RAM
        self.atenta_hasta = 0.0

    @property
    def atenta(self):
        return self._reloj() < self.atenta_hasta

    def purgar(self):
        """Borra lo que tiene más de 'ventana' segundos. Devuelve cuántas frases borró."""
        limite = self._reloj() - self.ventana
        antes = len(self.borrador)
        self.borrador = [(t, f) for t, f in self.borrador if t >= limite]
        return antes - len(self.borrador)

    def olvidar(self):
        self.borrador = []
        self.atenta_hasta = 0.0

    def atender(self, segundos):
        """Kira acaba de preguntarte algo (por ejemplo el código del laboratorio): durante 'segundos' tu respuesta
        vale sin decir «Kira» otra vez."""
        self.atenta_hasta = max(self.atenta_hasta, self._reloj() + max(0.0, float(segundos)))

    def oir(self, frase):
        """Una frase que llega del micrófono. Devuelve ('nada', None) | ('atenta', None) | ('orden', texto)."""
        frase = re.sub(r"\s+", " ", str(frase or "")).strip()[:500]
        self.purgar()
        if not frase:
            return "nada", None
        ahora = self._reloj()
        hay_nombre, resto = contiene_nombre(frase)
        if self.atenta and not hay_nombre:
            self.olvidar()                             # la orden ya llegó: el borrador no hace falta
            return "orden", frase
        if hay_nombre:
            self.borrador = []                         # para el borrador: Kira atiende
            if len(re.sub(r"\W", "", resto)) >= 2:
                self.atenta_hasta = 0.0
                return "orden", resto
            self.atenta_hasta = ahora + self.espera
            return "atenta", None
        self.borrador.append((ahora, frase))
        return "nada", None


# =====================================================================================
#  LUZ DE NEÓN de la portada: cuánto brilla según lo que hace Kira
# =====================================================================================
ESTADOS = ("reposo", "escuchando", "atenta", "pensando", "hablando")
TONOS = {                                   # color del neón (RGB) por estado
    "reposo": (0.00, 0.78, 1.00),
    "escuchando": (0.00, 0.78, 1.00),
    "atenta": (0.20, 0.55, 1.00),
    "pensando": (0.62, 0.35, 1.00),
    "hablando": (1.00, 0.25, 0.75),
}


class NeonModelo:
    def __init__(self):
        self.estado = "reposo"
        self.t = 0.0
        self.intensidad = 0.35
        self.color = TONOS["reposo"]

    def poner_estado(self, estado):
        if estado in ESTADOS:
            self.estado = estado

    def objetivo(self):
        t = self.t
        if self.estado == "hablando":         # late como una voz: se amplifica al hablar
            return 0.78 + 0.22 * (0.5 + 0.5 * math.sin(t * 10.5)) * (0.6 + 0.4 * math.sin(t * 2.7 + 1.0))
        if self.estado == "atenta":           # te está escuchando de verdad: muy brillante
            return 0.92 + 0.08 * math.sin(t * 6.0)
        if self.estado == "pensando":
            return 0.62 + 0.14 * math.sin(t * 5.0)
        if self.estado == "escuchando":       # escucha permanente de fondo: un poco más que en reposo
            return 0.48 + 0.06 * math.sin(t * 2.2)
        return 0.34 + 0.08 * math.sin(t * 1.4)   # respira despacio

    def paso(self, dt):
        dt = max(0.0, min(float(dt), 0.25))
        self.t += dt
        k = min(1.0, dt * 6.0)
        self.intensidad += (self.objetivo() - self.intensidad) * k
        self.color = tuple(c + (o - c) * min(1.0, dt * 4.0) for c, o in zip(self.color, TONOS[self.estado]))
        return self.intensidad


def dentro_del_boton(px, py, cx, cy, radio):
    """¿El toque cae dentro del botón redondo (con un margen cómodo para el dedo)?"""
    return (px - cx) ** 2 + (py - cy) ** 2 <= (radio * 1.2) ** 2


def rejilla_letras(ancho, alto, paso_x, paso_y):
    """Posiciones (x, y) de las palabras «Kira» del fondo, en filas alternadas como un papel pintado."""
    pos = []
    if ancho <= 0 or alto <= 0 or paso_x <= 0 or paso_y <= 0:
        return pos
    fila = 0
    y = -paso_y * 0.3
    while y < alto + paso_y:
        x = -paso_x * (0.5 if fila % 2 else 0.0)
        while x < ancho + paso_x:
            pos.append((x, y))
            x += paso_x
        y += paso_y
        fila += 1
    return pos
