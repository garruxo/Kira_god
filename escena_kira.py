# -*- coding: utf-8 -*-
"""
escena_kira.py - Kira DIBUJA escenas por código (local, sin internet, sin API, sin imágenes de IA)

  "dibuja un paisaje de una playa al atardecer con palmeras"  ->  lista de formas  ->  lienzo en pantalla

Qué es: un generador PROCEDURAL. Entiende un tema (playa, montaña, bosque, desierto, ciudad, lago, espacio),
        un momento (día, atardecer, amanecer, noche) y detalles (palmeras, nubes, barco, sombrilla, aves, luna,
        estrellas). El resultado es estilizado (formas planas y degradados), no una foto.
Qué NO es: no es una IA de imágenes: no dibuja "lo que sea". Si pides algo que no conoce, lo dice.

Capas (como el resto del proyecto):
  - PURA (sin Kivy): interpretar(), construir(), render_pil() (solo para pruebas/PC con Pillow).
  - Kivy: crear_widgets() -> EscenaWidget (dibuja las formas) y exportar_png().

Espacio de la escena: x de 0 a 1, y de 0 a 0.75 (4:3), y hacia ARRIBA.
Formas: ("rect",x,y,w,h,color) ("circ",cx,cy,r,color) ("poly",[(x,y)...],color) [convexo] ("line",[(x,y)...],grosor,color)
"""
import math
import random
import re
import unicodedata
import zlib

W, H = 1.0, 0.75
TEMAS = {
    "playa": ("playa", "costa", "orilla", "mar"),
    "montana": ("montana", "sierra", "volcan", "monte"),
    "bosque": ("bosque", "selva", "pinar"),
    "desierto": ("desierto", "dunas"),
    "ciudad": ("ciudad", "urbano", "rascacielos", "skyline"),
    "lago": ("lago", "laguna"),
    "espacio": ("espacio", "galaxia", "planeta", "cosmos"),
}
NOMBRES = {"playa": "una playa", "montana": "unas montañas", "bosque": "un bosque", "desierto": "un desierto",
           "ciudad": "una ciudad", "lago": "un lago", "espacio": "el espacio"}
MOMENTOS = {"atardecer": ("atardecer", "ocaso", "puesta de sol", "anochecer"),
            "amanecer": ("amanecer", "alba", "madrugada", "salida del sol"),
            "noche": ("noche", "nocturn", "luna")}
VERBOS = re.compile(r"\b(dibuja|dibujame|dibujar|pinta|pintame|arma|armame|armar|haz|hazme|crea|creame|genera|generame|"
                    r"disena|disename|muestrame|imagina)\b")
OBJETO = re.compile(r"\b(paisaje|escena|dibujo|imagen|ilustracion|cuadro|fondo)\b")
EXTRAS = {"palmeras": ("palmera",), "nubes": ("nube",), "barco": ("barco", "velero"), "sombrilla": ("sombrilla",),
          "aves": ("pajaro", "ave", "gaviota"), "luna": ("luna",), "estrellas": ("estrella",), "sol": ("sol",)}

# (cielo arriba, cielo horizonte, sol, agua lejos, agua cerca, arena)
PALETAS = {
    "dia":       ((0.25, 0.55, 0.95), (0.72, 0.89, 1.00), (1.00, 0.95, 0.70), (0.20, 0.62, 0.85), (0.05, 0.40, 0.70), (0.95, 0.85, 0.60)),
    "atardecer": ((0.22, 0.16, 0.46), (1.00, 0.58, 0.28), (1.00, 0.82, 0.35), (0.62, 0.35, 0.50), (0.18, 0.18, 0.40), (0.86, 0.62, 0.42)),
    "amanecer":  ((0.30, 0.40, 0.78), (1.00, 0.76, 0.62), (1.00, 0.90, 0.60), (0.55, 0.62, 0.82), (0.25, 0.38, 0.65), (0.90, 0.76, 0.58)),
    "noche":     ((0.02, 0.03, 0.12), (0.10, 0.15, 0.32), (0.92, 0.93, 1.00), (0.07, 0.14, 0.30), (0.02, 0.06, 0.18), (0.36, 0.34, 0.40)),
}


def _norm(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _mezcla(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


# =====================================================================================
#  INTERPRETAR
# =====================================================================================
def interpretar(texto, variante=0):
    """None si no es una petición de dibujo. Si lo es: dict con tema (None si no lo conoce), momento, extras..."""
    n = _norm(texto)
    pide = VERBOS.search(n) is not None
    tema = next((t for t, claves in TEMAS.items() if any(re.search(r"\b" + c, n) for c in claves)), None)
    dibuja = re.search(r"\b(dibuja|dibujame|dibujar|pinta|pintame)\b", n) is not None
    if not (pide and (tema or OBJETO.search(n) or dibuja)):
        return None
    momento = next((m for m, claves in MOMENTOS.items() if any(c in n for c in claves)), "dia")
    extras = {e for e, claves in EXTRAS.items() if any(re.search(r"\b" + c, n) for c in claves)}
    sin = set(re.findall(r"sin\s+(\w+)", n))
    extras = {e for e in extras if not any(e.startswith(s[:5]) for s in sin)}
    if tema == "playa" and "palmeras" not in extras and not any(s.startswith("palm") for s in sin):
        extras.add("palmeras")
    d = {"tema": tema, "momento": momento, "extras": sorted(extras),
         "semilla": (zlib.crc32(n.encode("utf-8")) + int(variante) * 7919) & 0xFFFFFFFF}
    d["titulo"] = (f"{NOMBRES[tema]} de {momento}" if momento != "dia" else f"{NOMBRES[tema]} de día") if tema else "(tema desconocido)"
    return d


def temas_conocidos():
    return ", ".join(NOMBRES[t].split(" ", 1)[1] for t in TEMAS)


# =====================================================================================
#  CONSTRUIR (formas)
# =====================================================================================
def _bandas(P, y0, y1, c0, c1, n=24):
    h = (y1 - y0) / n
    for i in range(n):
        P.append(("rect", 0.0, y0 + i * h, W, h + 0.002, _mezcla(c0, c1, i / max(1, n - 1))))


def _estrellas(P, rnd, n, y_min):
    for _ in range(n):
        P.append(("circ", rnd.uniform(0.02, 0.98), rnd.uniform(y_min, H - 0.02), rnd.uniform(0.002, 0.005),
                  (1, 1, 1, rnd.uniform(0.5, 0.95))))


def _nubes(P, rnd, n, y0, y1, color):
    for _ in range(n):
        cx, cy, e = rnd.uniform(0.1, 0.9), rnd.uniform(y0, y1), rnd.uniform(0.05, 0.1)
        for dx, dy, k in ((-0.6, 0, 0.7), (0, 0.25, 1.0), (0.6, 0, 0.75), (0.2, -0.05, 0.8), (-0.25, -0.05, 0.7)):
            P.append(("circ", cx + dx * e, cy + dy * e * 0.5, e * 0.45 * k, color + (0.8,)))


def _astro(P, momento, x, y, r, pal):
    c = pal[2]
    for k, a in ((3.0, 0.07), (2.2, 0.12), (1.5, 0.2)):
        P.append(("circ", x, y, r * k, c + (a,)))
    P.append(("circ", x, y, r, c))


def _aves(P, rnd, n, color=(0.1, 0.1, 0.15)):
    for _ in range(n):
        x, y, s = rnd.uniform(0.1, 0.9), rnd.uniform(0.52, 0.7), rnd.uniform(0.012, 0.022)
        P.append(("line", [(x - s, y + s * 0.4), (x, y), (x + s, y + s * 0.4)], 0.003, color))


def _palma(P, rnd, x, y, alto, incl, pal_noche):
    tx, ty = x + incl, y + alto
    marron = (0.30, 0.20, 0.12) if not pal_noche else (0.08, 0.06, 0.06)
    pts = [(x + incl * (i / 6) ** 2, y + alto * (i / 6)) for i in range(7)]
    for i in range(6):
        g0, g1 = 0.012 * (1 - i / 7), 0.012 * (1 - (i + 1) / 7)
        (xa, ya), (xb, yb) = pts[i], pts[i + 1]
        P.append(("poly", [(xa - g0, ya), (xa + g0, ya), (xb + g1, yb), (xb - g1, yb)], marron))
    verde = [(0.10, 0.45, 0.18), (0.14, 0.55, 0.22), (0.08, 0.38, 0.15)]
    if pal_noche:
        verde = [tuple(c * 0.35 for c in v) for v in verde]
    n = 8
    for i in range(n):
        a = math.radians(10 + 160 * i / (n - 1)) + rnd.uniform(-0.1, 0.1)
        largo = alto * rnd.uniform(0.42, 0.55)
        dx, dy = math.cos(a), math.sin(a)
        punta = (tx + dx * largo, ty + dy * largo * 0.55 - largo * 0.3)
        medio = (tx + dx * largo * 0.5, ty + dy * largo * 0.4 + largo * 0.05)
        px, py = -dy * largo * 0.1, dx * largo * 0.1
        P.append(("poly", [(tx, ty), (medio[0] + px, medio[1] + py), punta, (medio[0] - px, medio[1] - py)],
                  verde[i % 3]))
    for dx in (-0.008, 0.008):
        P.append(("circ", tx + dx, ty - 0.012, 0.007, (0.25, 0.16, 0.08)))


def _playa(d, rnd, pal):
    P, m = [], d["momento"]
    hor = 0.40
    _bandas(P, hor, H, pal[1], pal[0], 28)
    if m == "noche":
        _estrellas(P, rnd, 70, hor + 0.03)
    sx, sy = {"dia": (0.68, 0.62), "atardecer": (0.62, hor + 0.06), "amanecer": (0.3, hor + 0.07), "noche": (0.76, 0.6)}[m]
    _astro(P, m, sx, sy, 0.05 if m != "noche" else 0.04, pal)
    if m != "noche" or "nubes" in d["extras"]:
        _nubes(P, rnd, 3 if "nubes" not in d["extras"] else 5, 0.5, 0.7,
               (1, 1, 1) if m == "dia" else _mezcla(pal[1], (1, 1, 1), 0.4))
    if m in ("dia", "atardecer") or "aves" in d["extras"]:
        _aves(P, rnd, 3)
    _bandas(P, 0.10, hor, pal[4], pal[3], 20)
    for k in range(9):                                      # reflejo del astro
        P.append(("rect", sx - 0.035 * (1 - k * 0.07), hor - 0.014 * (k + 1), 0.07 * (1 - k * 0.07), 0.008,
                  pal[2] + (0.42 - 0.04 * k,)))
    for _ in range(14):                                      # olas
        x, y = rnd.uniform(0.02, 0.9), rnd.uniform(0.22, hor - 0.02)
        P.append(("line", [(x, y), (x + 0.04, y + 0.004), (x + 0.08, y)], 0.002, (1, 1, 1, 0.35)))
    if "barco" in d["extras"]:
        bx, by = rnd.uniform(0.15, 0.4), hor - 0.01
        P.append(("poly", [(bx, by), (bx + 0.05, by), (bx + 0.04, by - 0.012), (bx + 0.01, by - 0.012)], (0.25, 0.15, 0.1)))
        P.append(("poly", [(bx + 0.025, by), (bx + 0.025, by + 0.07), (bx + 0.048, by)], (0.97, 0.97, 0.95)))
    fase = rnd.uniform(0, 6)
    ys = lambda x: 0.2 + 0.025 * math.sin(x * 6 + fase) + 0.008 * math.sin(x * 17)
    N = 40
    for i in range(N):
        x0, w = i / N, 1.0 / N + 0.002
        top = ys(x0 + w / 2)
        P.append(("rect", x0, 0.0, w, top - 0.03, pal[5]))
        P.append(("rect", x0, top - 0.03, w, 0.03, _mezcla(pal[5], (0.3, 0.2, 0.1), 0.35)))
        P.append(("rect", x0, top, w, 0.012, (1, 1, 1, 0.7)))
    for i in range(6):
        P.append(("rect", 0, i * 0.03, W, 0.03, (0.0, 0.0, 0.0, 0.015 * (6 - i))))
    if "palmeras" in d["extras"]:
        _palma(P, rnd, rnd.uniform(0.08, 0.2), 0.04, rnd.uniform(0.3, 0.38), rnd.uniform(0.04, 0.09), m == "noche")
        _palma(P, rnd, rnd.uniform(0.8, 0.92), 0.02, rnd.uniform(0.22, 0.3), -rnd.uniform(0.03, 0.07), m == "noche")
    if "sombrilla" in d["extras"]:
        ux, uy = rnd.uniform(0.45, 0.6), 0.1
        P.append(("line", [(ux, uy), (ux + 0.01, uy + 0.12)], 0.004, (0.4, 0.3, 0.2)))
        P.append(("poly", [(ux - 0.07, uy + 0.115), (ux + 0.09, uy + 0.115), (ux + 0.01, uy + 0.16)], (0.9, 0.2, 0.2)))
    return P


def _montana(d, rnd, pal, con_lago=False):
    P, m = [], d["momento"]
    _bandas(P, 0.3, H, pal[1], pal[0], 24)
    if m == "noche":
        _estrellas(P, rnd, 60, 0.4)
    _astro(P, m, rnd.uniform(0.3, 0.75), 0.55 if m != "atardecer" else 0.38, 0.045, pal)
    if m in ("dia", "atardecer"):
        _nubes(P, rnd, 3, 0.55, 0.7, (1, 1, 1) if m == "dia" else _mezcla(pal[1], (1, 1, 1), 0.4))
    base = 0.3
    for capa, (col, alt) in enumerate(((_mezcla(pal[3], pal[1], 0.4), 0.22), (_mezcla(pal[3], (0.2, 0.25, 0.3), 0.5), 0.3),
                                       (_mezcla(pal[4], (0.1, 0.15, 0.1), 0.5), 0.36))):
        x = -0.1
        while x < 1.1:
            ancho = rnd.uniform(0.25, 0.4)
            cima = base + rnd.uniform(alt * 0.6, alt)
            cx = x + ancho / 2
            P.append(("poly", [(x, base), (cx, cima), (x + ancho, base)], col))
            if capa >= 1 and cima > base + 0.2:
                P.append(("poly", [(cx - ancho * 0.12, cima - 0.045), (cx, cima), (cx + ancho * 0.12, cima - 0.045)],
                          (0.96, 0.97, 1.0)))
            x += ancho * 0.7
    if con_lago:
        _bandas(P, 0.0, base, pal[4], _mezcla(pal[3], pal[1], 0.5), 18)
        for _ in range(12):
            x, y = rnd.uniform(0.05, 0.85), rnd.uniform(0.03, 0.26)
            P.append(("line", [(x, y), (x + 0.05, y + 0.003), (x + 0.1, y)], 0.002, (1, 1, 1, 0.3)))
    else:
        P.append(("rect", 0, 0, W, base, _mezcla((0.25, 0.5, 0.2), (0, 0, 0), 0.5 if m == "noche" else 0.0)))
    return P


def _bosque(d, rnd, pal):
    P, m = [], d["momento"]
    _bandas(P, 0.25, H, pal[1], pal[0], 24)
    if m == "noche":
        _estrellas(P, rnd, 50, 0.4)
    _astro(P, m, rnd.uniform(0.3, 0.7), 0.6, 0.04, pal)
    for capa, (y, esc, oscuro) in enumerate(((0.3, 0.7, 0.55), (0.2, 0.9, 0.35), (0.08, 1.2, 0.15))):
        P.append(("rect", 0, 0, W, y + 0.02, _mezcla((0.12, 0.32, 0.14), (0, 0, 0), oscuro)))
        for _ in range(9 + capa * 2):
            x, h = rnd.uniform(0, 1), rnd.uniform(0.2, 0.3) * esc
            col = _mezcla((0.1, 0.4, 0.18), (0, 0, 0), oscuro + (0.3 if m == "noche" else 0))
            P.append(("rect", x - 0.004 * esc, y, 0.008 * esc, 0.05 * esc, (0.25, 0.15, 0.08)))
            for k in range(3):
                an = (0.09 - k * 0.02) * esc
                P.append(("poly", [(x - an, y + 0.04 * esc + k * 0.07 * esc), (x, y + 0.04 * esc + k * 0.07 * esc + 0.1 * esc),
                                   (x + an, y + 0.04 * esc + k * 0.07 * esc)], col))
    return P


def _desierto(d, rnd, pal):
    P, m = [], d["momento"]
    _bandas(P, 0.3, H, pal[1], pal[0], 24)
    if m == "noche":
        _estrellas(P, rnd, 70, 0.35)
    _astro(P, m, rnd.uniform(0.25, 0.75), 0.6 if m == "dia" else 0.42, 0.07, pal)
    arena = pal[5]
    for capa, (y, amp, osc) in enumerate(((0.28, 0.05, 0.12), (0.17, 0.07, 0.05), (0.04, 0.08, 0.0))):
        f = rnd.uniform(0, 6)
        for i in range(40):
            x0 = i / 40
            P.append(("rect", x0, 0, 1 / 40 + 0.002, y + amp * (0.5 + 0.5 * math.sin(x0 * 5 + f + capa)), _mezcla(arena, (0.3, 0.1, 0.0), osc)))
    cx = rnd.uniform(0.7, 0.9)
    verde = (0.12, 0.4, 0.2) if m != "noche" else (0.05, 0.15, 0.08)
    P.append(("rect", cx - 0.01, 0.08, 0.02, 0.14, verde))
    P.append(("rect", cx - 0.045, 0.14, 0.035, 0.012, verde)); P.append(("rect", cx - 0.045, 0.14, 0.012, 0.06, verde))
    P.append(("rect", cx + 0.01, 0.12, 0.035, 0.012, verde)); P.append(("rect", cx + 0.033, 0.12, 0.012, 0.05, verde))
    return P


def _ciudad(d, rnd, pal):
    P = []
    _bandas(P, 0.2, H, pal[1], pal[0], 24)
    _estrellas(P, rnd, 60, 0.45) if d["momento"] == "noche" else None
    _astro(P, d["momento"], 0.8, 0.6, 0.04, pal)
    for capa, (osc, alto) in enumerate(((0.55, 0.25), (0.3, 0.33), (0.1, 0.4))):
        x = 0.0
        while x < 1.0:
            w, h = rnd.uniform(0.05, 0.1), rnd.uniform(0.08, alto)
            col = _mezcla(pal[3], (0.02, 0.02, 0.06), 1 - osc)
            P.append(("rect", x, 0.0 if capa == 2 else 0.12, w, h + (0.1 if capa == 2 else 0.0), col))
            if capa >= 1:
                for fy in range(int(h / 0.03)):
                    for fx in range(max(1, int(w / 0.02))):
                        if rnd.random() < 0.45:
                            P.append(("rect", x + 0.006 + fx * 0.018, 0.12 + 0.01 + fy * 0.03 + (0.1 if capa == 2 else 0), 0.008, 0.012,
                                      (1.0, 0.88, 0.45, 0.9)))
            x += w + rnd.uniform(0.0, 0.015)
    P.append(("rect", 0, 0, W, 0.06, (0.05, 0.05, 0.07)))
    return P


def _espacio(d, rnd, pal):
    P = [("rect", 0, 0, W, H, (0.01, 0.01, 0.05))]
    for _ in range(40):
        P.append(("circ", rnd.uniform(0.1, 0.9), rnd.uniform(0.1, 0.65), rnd.uniform(0.04, 0.12),
                  rnd.choice([(0.4, 0.1, 0.6), (0.1, 0.2, 0.6), (0.6, 0.1, 0.3)]) + (0.035,)))
    _estrellas(P, rnd, 160, 0.0)
    px, py, r = rnd.uniform(0.3, 0.7), rnd.uniform(0.3, 0.5), rnd.uniform(0.1, 0.16)
    color = rnd.choice([(0.8, 0.45, 0.25), (0.25, 0.5, 0.8), (0.6, 0.35, 0.7)])
    P.append(("circ", px, py, r * 1.3, color + (0.1,)))
    P.append(("circ", px, py, r, color))
    P.append(("circ", px + r * 0.25, py + r * 0.2, r * 0.7, (1, 1, 1, 0.12)))
    P.append(("circ", px - r * 0.3, py - r * 0.2, r * 0.75, (0, 0, 0, 0.25)))
    anillo = [(px + math.cos(a / 20 * 6.283) * r * 1.9, py + math.sin(a / 20 * 6.283) * r * 0.45) for a in range(21)]
    P.append(("line", anillo, 0.006, (0.9, 0.85, 0.7, 0.8)))
    return P


def construir(d):
    """Formas de la escena descrita por interpretar(). Lanza ValueError si el tema no se conoce."""
    if not d or not d.get("tema"):
        raise ValueError("tema desconocido")
    rnd = random.Random(d["semilla"])
    pal = PALETAS[d["momento"]]
    t = d["tema"]
    if t == "playa":
        return _playa(d, rnd, pal)
    if t == "montana":
        return _montana(d, rnd, pal)
    if t == "lago":
        return _montana(d, rnd, pal, con_lago=True)
    if t == "bosque":
        return _bosque(d, rnd, pal)
    if t == "desierto":
        return _desierto(d, rnd, pal)
    if t == "ciudad":
        return _ciudad(d, rnd, pal)
    return _espacio(d, rnd, pal)


# =====================================================================================
#  RENDER CON PILLOW (pruebas / PC; en Android se usa Kivy)
# =====================================================================================
def render_pil(formas, ancho=800):
    from PIL import Image, ImageDraw
    alto = int(ancho * H)
    im = Image.new("RGB", (ancho, alto), (0, 0, 0))
    dr = ImageDraw.Draw(im, "RGBA")
    px = lambda x, y: (x * ancho, alto - y * ancho)

    def col(c):
        c = tuple(c) if len(c) == 4 else tuple(c) + (1.0,)
        return tuple(int(max(0, min(1, v)) * 255) for v in c)
    for f in formas:
        k = f[0]
        if k == "rect":
            _, x, y, w, h, c = f
            dr.rectangle([px(x, y + h), px(x + w, y)], fill=col(c))
        elif k == "circ":
            _, cx, cy, r, c = f
            dr.ellipse([px(cx - r, cy + r), px(cx + r, cy - r)], fill=col(c))
        elif k == "poly":
            dr.polygon([px(*p) for p in f[1]], fill=col(f[2]))
        elif k == "line":
            dr.line([px(*p) for p in f[1]], fill=col(f[3]), width=max(1, int(f[2] * ancho)))
    return im


# =====================================================================================
#  KIVY
# =====================================================================================
def crear_widgets():
    from kivy.graphics import Color, Ellipse, Fbo, Line, Rectangle, Triangle
    from kivy.uix.widget import Widget

    def pintar(formas, ox, oy, ancho):
        """Dibuja las formas en el canvas actual con origen (ox, oy) y ancho en píxeles."""
        def c(col):
            Color(*(tuple(col) if len(col) == 4 else tuple(col) + (1.0,)))
        for f in formas:
            k = f[0]
            if k == "rect":
                _, x, y, w, h, col = f
                c(col)
                Rectangle(pos=(ox + x * ancho, oy + y * ancho), size=(w * ancho, h * ancho))
            elif k == "circ":
                _, cx, cy, r, col = f
                c(col)
                Ellipse(pos=(ox + (cx - r) * ancho, oy + (cy - r) * ancho), size=(2 * r * ancho, 2 * r * ancho))
            elif k == "poly":
                c(f[2])
                p = [(ox + x * ancho, oy + y * ancho) for x, y in f[1]]
                for i in range(1, len(p) - 1):                 # abanico de triángulos (formas convexas)
                    Triangle(points=[*p[0], *p[i], *p[i + 1]])
            elif k == "line":
                c(f[3])
                Line(points=[v for x, y in f[1] for v in (ox + x * ancho, oy + y * ancho)], width=max(1.0, f[2] * ancho))

    class EscenaWidget(Widget):
        """Muestra la escena en 4:3 centrada. Asigna .formas = construir(descripcion)."""

        def __init__(self, **kw):
            super().__init__(**kw)
            self.formas = []
            self.bind(size=self._redibujar, pos=self._redibujar)

        def poner(self, formas):
            self.formas = list(formas)
            self._redibujar()

        def _redibujar(self, *_):
            if self.width < 10 or self.height < 10:
                return
            ancho = min(self.width, self.height / H)
            ox, oy = self.x + (self.width - ancho) / 2, self.y + (self.height - ancho * H) / 2
            self.canvas.clear()
            with self.canvas:
                Color(0, 0, 0, 1)
                Rectangle(pos=self.pos, size=self.size)
                pintar(self.formas, ox, oy, ancho)

    def exportar_png(formas, ruta, ancho=1280):
        """Guarda la escena como PNG. Devuelve (ok, mensaje)."""
        try:
            fbo = Fbo(size=(ancho, int(ancho * H)))
            with fbo:
                Color(0, 0, 0, 1)
                Rectangle(size=(ancho, int(ancho * H)))
                pintar(formas, 0, 0, ancho)
            fbo.draw()
            fbo.texture.save(ruta, flipped=False)
            return True, f"Guardado en {ruta}"
        except Exception as e:
            try:                       # plan B: Pillow, si está instalado (PC)
                render_pil(formas, ancho).save(ruta)
                return True, f"Guardado en {ruta}"
            except Exception:
                return False, f"No se pudo guardar la imagen: {e}"

    return EscenaWidget, exportar_png
