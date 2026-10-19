# -*- coding: utf-8 -*-
"""
luz3d_kira.py - Iluminación de las salas 3D (lógica PURA, sin Kivy). La usan TODAS las salas a través de
habitacion_kira.Recorrido, sin tener que retocarlas una a una:

  1. LUCES AUTOMÁTICAS: cada cosa que brilla en la sala (paneles del techo, monitor, lámpara, carteles, ventana,
     pantalla del cine…) se convierte en una luz de su color que ilumina lo que tiene cerca.
  2. DEGRADADOS: paredes, suelo y techo se dividen en losas para que la luz cambie a lo largo de ellos.
  3. SOMBRAS DE CONTACTO: el suelo se oscurece debajo de mesas y muebles; las esquinas, un poco (oclusión).
  4. VIDA: lo que brilla parpadea muy suave y los detalles diminutos (cursores, pilotos) parpadean de verdad.
Todo se calcula UNA vez al entrar en la sala; en cada fotograma solo se aplica (cuesta muy poco).
"""
import math

AMBIENTE = 0.30
DIRECCIONAL = 0.30
MAX_LUCES = 10
CELDA = 0.9           # tamaño de las losas (metros)
MAX_DIVISIONES = 12
OBJETIVO = 0.80       # brillo medio de la sala tras iluminarla (como el sombreado de antes)
TOPE = 1.3            # máximo que puede aclarar una luz
HALO_AREA = 0.15      # solo las luces pequeñas (lámparas, pilotos) llevan resplandor en pantalla


def _resta(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cruz(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _largo(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def area(pts):
    """Área de un polígono plano en 3D."""
    tot = (0.0, 0.0, 0.0)
    for i in range(1, len(pts) - 1):
        c = _cruz(_resta(pts[i], pts[0]), _resta(pts[i + 1], pts[0]))
        tot = (tot[0] + c[0], tot[1] + c[1], tot[2] + c[2])
    return _largo(tot) / 2.0


def centro(pts):
    n = len(pts)
    return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n, sum(p[2] for p in pts) / n)


def normal_de(pts):
    c = _cruz(_resta(pts[1], pts[0]), _resta(pts[2], pts[0]))
    l = _largo(c) or 1.0
    return (c[0] / l, c[1] / l, c[2] / l)


def _mezcla(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def subdividir(escena, celda=CELDA):
    """Divide los cuadriláteros grandes de la estructura (capa 0, no emisivos) en losas."""
    sal = []
    for cara in escena:
        pts, color, normal, capa, hot, emi = cara
        if capa != 0 or emi or len(pts) != 4:
            sal.append(cara)
            continue
        a, b, c, d = pts
        nu = max(1, min(MAX_DIVISIONES, int(math.ceil(_largo(_resta(b, a)) / celda))))
        nv = max(1, min(MAX_DIVISIONES, int(math.ceil(_largo(_resta(d, a)) / celda))))
        if nu == nv == 1:
            sal.append(cara)
            continue
        for i in range(nu):
            for j in range(nv):
                def p(u, v):
                    return _mezcla(_mezcla(a, b, u), _mezcla(d, c, u), v)
                u0, u1, v0, v1 = i / nu, (i + 1) / nu, j / nv, (j + 1) / nv
                sal.append(((p(u0, v0), p(u1, v0), p(u1, v1), p(u0, v1)), color, normal, capa, hot, emi))
    return sal


def luces_de(escena, maximo=MAX_LUCES):
    """[(posición, color, intensidad, alcance)] a partir de las caras que brillan."""
    cand = []
    for pts, color, normal, capa, hot, emi in escena:
        if not emi:
            continue
        a = area(pts)
        brillo = max(color)
        if a < 0.01 or brillo < 0.15:
            continue
        n = normal or normal_de(pts)
        c = centro(pts)
        pos = (c[0] + n[0] * 0.2, c[1] + n[1] * 0.2, c[2] + n[2] * 0.2)
        col = tuple(min(1.0, v / brillo) for v in color)          # el tono del objeto, a plena luz
        intensidad = min(1.6, 0.35 + a * 1.2) * (0.4 + 0.6 * brillo)
        alcance = 1.0 + min(3.0, math.sqrt(a) * 2.0)
        cand.append((intensidad * alcance, (pos, col, intensidad, alcance, n, a)))
    cand.sort(key=lambda x: -x[0])
    # luces casi en el mismo sitio se juntan (p. ej. las líneas de código del monitor)
    elegidas = []
    for _, l in cand:
        if all(_largo(_resta(l[0], e[0])) > 0.45 for e in elegidas):
            elegidas.append(l)
        if len(elegidas) >= maximo:
            break
    return elegidas


def _encima(c, tapas):
    """¿Hay un mueble encima de este punto del suelo? (sombra de contacto)"""
    for x0, x1, z0, z1, y in tapas:
        if x0 <= c[0] <= x1 and z0 <= c[2] <= z1 and y > c[1] + 0.15:
            return True
    return False


def iluminar(escena, luces, ambiente=AMBIENTE, direccional=DIRECCIONAL, dir_luz=(0.3, 0.8, -0.4)):
    """Factor de luz (r, g, b) de cada cara (None para las que brillan)."""
    l = _largo(dir_luz) or 1.0
    dl = (dir_luz[0] / l, dir_luz[1] / l, dir_luz[2] / l)
    tapas = []                                       # la parte de arriba de mesas y muebles (de 0,25 m a 1,4 m)
    for pts, color, normal, capa, hot, emi in escena:
        if capa >= 1 and normal and normal[1] > 0.9:
            y = centro(pts)[1]
            if 0.25 < y < 1.4:
                xs, zs = [p[0] for p in pts], [p[2] for p in pts]
                tapas.append((min(xs) - 0.05, max(xs) + 0.05, min(zs) - 0.05, max(zs) + 0.05, y))
    alto_sala = max((p[1] for pts, *_ in escena for p in pts), default=3.0)
    factores = []
    for pts, color, normal, capa, hot, emi in escena:
        if emi:
            factores.append(None)
            continue
        n = normal or normal_de(pts)
        c = centro(pts)
        lamb = max(0.0, n[0] * dl[0] + n[1] * dl[1] + n[2] * dl[2])
        r = g = b = ambiente + direccional * lamb
        for pos, col, inten, alcance, nl, _a in luces:
            v = _resta(pos, c)
            d = _largo(v) or 1e-6
            ndotl = (n[0] * v[0] + n[1] * v[1] + n[2] * v[2]) / d
            if ndotl <= 0:
                continue
            # la luz sale hacia delante de lo que brilla, no por detrás
            frente = (-(nl[0] * v[0] + nl[1] * v[1] + nl[2] * v[2]) / d)
            if frente < -0.2:
                continue
            k = inten * ndotl / (1.0 + (d / alcance) ** 2) * (0.55 + 0.45 * max(0.0, frente))
            r, g, b = r + col[0] * k, g + col[1] * k, b + col[2] * k
        sombra = 1.0
        if n[1] > 0.9 and c[1] < 0.06 and _encima(c, tapas):
            sombra *= 0.55                           # suelo bajo un mueble
        if abs(n[1]) < 0.2:                          # paredes: más oscuras abajo y arriba (rincones)
            if c[1] < 0.4:
                sombra *= 0.72 + 0.28 * (c[1] / 0.4)
            elif c[1] > alto_sala - 0.35:
                sombra *= 0.85
        factores.append((r * sombra, g * sombra, b * sombra, area(pts)))
    # AUTOEXPOSICIÓN: cada sala conserva su brillo general (la de la playa sigue luminosa, el búnker oscuro),
    # pero gana el contraste y el color de sus lámparas.
    peso = sum(f[3] for f in factores if f) or 1.0
    media = sum((0.3 * f[0] + 0.55 * f[1] + 0.15 * f[2]) * f[3] for f in factores if f) / peso
    escala = OBJETIVO / max(media, 0.05)
    return [None if f is None else tuple(min(TOPE, v * escala) for v in f[:3]) for f in factores]


def animaciones(escena):
    """Para cada cara que brilla: ('parpadeo', fase) si es diminuta (cursor, piloto) o ('brillo', fase). None si no brilla."""
    anim = []
    for i, (pts, color, normal, capa, hot, emi) in enumerate(escena):
        if not emi:
            anim.append(None)
            continue
        fase = (i * 2.399963) % 6.283
        anim.append(("parpadeo" if area(pts) < 0.0025 else "brillo", fase))
    return anim


def color_animado(color, anim, t):
    if anim is None:
        return color
    tipo, fase = anim
    if tipo == "parpadeo":
        k = 1.0 if math.sin(t * 3.4 + fase) > -0.2 else 0.3
    else:
        k = 0.93 + 0.07 * math.sin(t * 1.7 + fase)
    return (color[0] * k, color[1] * k, color[2] * k)


def preparar(escena, celda=CELDA, maximo=MAX_LUCES, ambiente=AMBIENTE):
    """Todo lo que hace falta para pintar la sala iluminada. Se llama una vez por sala."""
    caras = subdividir(escena, celda)
    luces = luces_de(caras, maximo)
    return {"caras": caras, "luces": luces, "luz": iluminar(caras, luces, ambiente), "anim": animaciones(caras)}
