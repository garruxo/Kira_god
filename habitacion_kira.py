# -*- coding: utf-8 -*-
"""
habitacion_kira.py - La Sala Hacker como una HABITACIÓN 3D (Kivy, móvil y PC)

Entras por la puerta, avanzas hasta la mesa del ordenador y desde allí puedes mirar alrededor:
  izquierda = BIBLIOTECA   |   frente = ORDENADOR (mesa)   |   derecha = SALIDA
Tocar un objeto (o decir "hackear", "programar", "biblioteca", "salir"...) te acerca a él.

Qué es: un motor 3D sencillo hecho a mano (proyección en perspectiva + recorte + ordenación de caras).
        La habitación es de verdad un cubo con muebles en 3D, no una imagen plana. Se mira arrastrando.
Qué NO es: no usa OpenGL 3D ni modelos; es geometría simple y estilizada. Es estética: no añade herramientas
        de hacking (la terminal del ordenador es el aprendizaje de programación y las mejoras de Kira).
        No he podido medir la fluidez en un móvil real: el diseño limita las caras (~250) y solo redibuja cuando algo se mueve.

Dos capas, como el resto del proyecto:
  - PURA (sin Kivy): construir_escena(), render_caras(), Recorrido (cámara, paseo, giros, toques).
  - Kivy: crear_widgets() -> HabitacionWidget.

Ejes: x derecha, y arriba, z hacia el fondo. Habitación: x de -3 a 3, y de 0 a 2.8, z de 0 a 8.
"""
import math
import random

ANCHO, ALTO, FONDO = 3.0, 2.8, 8.0
NEAR = 0.08
LUZ = (0.3, 0.8, -0.4)
_n = math.sqrt(sum(c * c for c in LUZ))
LUZ = tuple(c / _n for c in LUZ)
NIEBLA = (0.01, 0.02, 0.03)

# poses de cámara: (x, y, z, yaw_grados, pitch_grados)
POSE_ENTRADA = (0.0, 1.62, 0.5, 0.0, 0.0)
POSE_MESA = (0.0, 1.55, 5.2, 0.0, 0.0)
POSE_ORDENADOR = (0.0, 1.32, 5.95, 0.0, 0.0)
POSE_BIBLIOTECA = (-1.35, 1.5, 4.0, -90.0, 0.0)
POSE_SALIDA = (1.35, 1.5, 4.1, 90.0, 0.0)
DURACION_PASEO = 4.5
DURACION_GIRO = 1.3
LIMITE_YAW, LIMITE_PITCH = 115.0, 18.0


# =====================================================================================
#  ESCENA (caras en 3D)
# =====================================================================================
# cara = (puntos3d, color_rgb, normal|None, capa, hotspot|None, emisiva)
def _q(P, a, b, c, d, color, normal=None, capa=1, hot=None, emi=False):
    P.append(((a, b, c, d), color, normal, capa, hot, emi))


def _caja(P, x0, y0, z0, x1, y1, z1, color, capa=1, hot=None, emi=False):
    _q(P, (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), color, (0, 0, -1), capa, hot, emi)   # frente (-z)
    _q(P, (x1, y0, z1), (x0, y0, z1), (x0, y1, z1), (x1, y1, z1), color, (0, 0, 1), capa, hot, emi)    # fondo (+z)
    _q(P, (x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1), color, (-1, 0, 0), capa, hot, emi)   # izquierda
    _q(P, (x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0), color, (1, 0, 0), capa, hot, emi)    # derecha
    _q(P, (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1), color, (0, 1, 0), capa, hot, emi)    # arriba


def construir_escena(semilla=7):
    rnd = random.Random(semilla)
    P = []
    # --- estructura (capa 0) ---
    for i in range(16):                                                      # suelo de tablas
        z0 = i * 0.5
        _q(P, (-ANCHO, 0, z0), (ANCHO, 0, z0), (ANCHO, 0, z0 + 0.5), (-ANCHO, 0, z0 + 0.5),
           (0.22, 0.14, 0.09) if i % 2 else (0.19, 0.12, 0.08), (0, 1, 0), 0)
    pared = (0.08, 0.13, 0.16)
    _q(P, (-ANCHO, 0, 0), (-ANCHO, 0, FONDO), (-ANCHO, ALTO, FONDO), (-ANCHO, ALTO, 0), pared, (1, 0, 0), 0)
    _q(P, (ANCHO, 0, FONDO), (ANCHO, 0, 0), (ANCHO, ALTO, 0), (ANCHO, ALTO, FONDO), pared, (-1, 0, 0), 0)
    _q(P, (-ANCHO, 0, FONDO), (ANCHO, 0, FONDO), (ANCHO, ALTO, FONDO), (-ANCHO, ALTO, FONDO), (0.07, 0.11, 0.14), (0, 0, -1), 0)
    _q(P, (ANCHO, 0, 0), (-ANCHO, 0, 0), (-ANCHO, ALTO, 0), (ANCHO, ALTO, 0), pared, (0, 0, 1), 0)
    _q(P, (-ANCHO, ALTO, 0), (ANCHO, ALTO, 0), (ANCHO, ALTO, FONDO), (-ANCHO, ALTO, FONDO), (0.04, 0.05, 0.07), (0, -1, 0), 0)
    for z in (1.5, 4.0, 6.5):                                               # paneles de luz del techo
        _q(P, (-0.6, ALTO - 0.01, z), (0.6, ALTO - 0.01, z), (0.6, ALTO - 0.01, z + 0.5), (-0.6, ALTO - 0.01, z + 0.5),
           (0.50, 0.66, 0.60), (0, -1, 0), 2, None, True)
    _q(P, (-1.9, 0.01, 5.2), (1.9, 0.01, 5.2), (1.9, 0.01, 7.5), (-1.9, 0.01, 7.5), (0.07, 0.15, 0.19), (0, 1, 0), 1)  # alfombra
    # ventana con luna en la pared del fondo
    _q(P, (-2.6, 1.1, FONDO - 0.01), (-1.4, 1.1, FONDO - 0.01), (-1.4, 2.1, FONDO - 0.01), (-2.6, 2.1, FONDO - 0.01),
       (0.03, 0.06, 0.18), (0, 0, -1), 1, None, True)
    _q(P, (-2.2, 1.6, FONDO - 0.02), (-2.0, 1.6, FONDO - 0.02), (-2.0, 1.8, FONDO - 0.02), (-2.2, 1.8, FONDO - 0.02),
       (0.92, 0.93, 1.0), (0, 0, -1), 2, None, True)
    _q(P, (1.5, 1.2, FONDO - 0.01), (2.5, 1.2, FONDO - 0.01), (2.5, 2.0, FONDO - 0.01), (1.5, 2.0, FONDO - 0.01),
       (0.08, 0.20, 0.35), (0, 0, -1), 1)                                  # póster

    # --- mesa y ordenador (hotspot "ordenador") ---
    madera = (0.30, 0.20, 0.12)
    _caja(P, -1.4, 0.74, 6.4, 1.4, 0.80, 7.6, madera, 1, "ordenador")
    for lx, lz in ((-1.35, 6.45), (1.27, 6.45), (-1.35, 7.47), (1.27, 7.47)):
        _caja(P, lx, 0.0, lz, lx + 0.08, 0.74, lz + 0.08, (0.22, 0.14, 0.08), 1, "ordenador")
    _caja(P, -0.55, 0.98, 6.9, 0.55, 1.58, 6.98, (0.05, 0.05, 0.07), 1, "ordenador")           # marco del monitor
    _caja(P, -0.06, 0.80, 6.92, 0.06, 1.0, 7.0, (0.08, 0.08, 0.1), 1, "ordenador")
    _caja(P, -0.2, 0.80, 6.8, 0.2, 0.83, 7.05, (0.08, 0.08, 0.1), 1, "ordenador")
    _q(P, (-0.5, 1.02, 6.89), (0.5, 1.02, 6.89), (0.5, 1.54, 6.89), (-0.5, 1.54, 6.89),
       (0.02, 0.12, 0.07), (0, 0, -1), 2, "ordenador", True)                                    # pantalla
    for i in range(9):                                                                          # líneas de "código"
        y = 1.50 - i * 0.052
        ancho = rnd.uniform(0.18, 0.8)
        sangria = 0.08 * rnd.choice((0, 0, 1, 2))
        _q(P, (-0.45 + sangria, y - 0.012, 6.885), (-0.45 + sangria + ancho, y - 0.012, 6.885),
           (-0.45 + sangria + ancho, y + 0.012, 6.885), (-0.45 + sangria, y + 0.012, 6.885),
           (0.10, 0.85, 0.42) if i % 4 else (0.35, 0.8, 1.0), (0, 0, -1), 3, "ordenador", True)
    _q(P, (-0.45, 1.03, 6.884), (-0.4, 1.03, 6.884), (-0.4, 1.07, 6.884), (-0.45, 1.07, 6.884),
       (0.8, 1.0, 0.85), (0, 0, -1), 3, "ordenador", True)                                      # cursor
    _caja(P, -0.35, 0.80, 6.5, 0.35, 0.82, 6.75, (0.10, 0.10, 0.13), 2, "ordenador")           # teclado
    for k in range(3):
        _q(P, (-0.32, 0.822, 6.55 + k * 0.06), (0.32, 0.822, 6.55 + k * 0.06), (0.32, 0.822, 6.57 + k * 0.06),
           (-0.32, 0.822, 6.57 + k * 0.06), (0.2, 0.25, 0.3), (0, 1, 0), 3, "ordenador")
    _caja(P, 0.9, 0.80, 6.95, 0.98, 1.05, 7.03, (0.15, 0.15, 0.17), 1, "ordenador")           # lámpara
    _caja(P, 0.85, 1.05, 6.9, 1.05, 1.12, 7.1, (1.0, 0.85, 0.5), 2, "ordenador", True)
    _caja(P, -1.1, 0.80, 6.9, -0.95, 0.9, 7.05, (0.5, 0.2, 0.2), 2, "ordenador")               # taza
    for i, col in enumerate(((0.7, 0.2, 0.2), (0.2, 0.4, 0.7), (0.2, 0.6, 0.3))):              # libros sobre la mesa
        _caja(P, -1.3, 0.80 + i * 0.05, 7.1, -0.9, 0.85 + i * 0.05, 7.35, col, 2, "ordenador")

    # --- biblioteca (pared izquierda, hotspot "biblioteca") ---
    for (za, zb) in ((1.0, 2.8), (3.0, 4.8), (5.0, 6.8)):
        _q(P, (-ANCHO + 0.01, 0.1, za), (-ANCHO + 0.01, 0.1, zb), (-ANCHO + 0.01, 2.4, zb), (-ANCHO + 0.01, 2.4, za),
           (0.14, 0.09, 0.05), (1, 0, 0), 1, "biblioteca")
        for zp in (za, zb - 0.06):
            _caja(P, -ANCHO, 0.1, zp, -ANCHO + 0.4, 2.4, zp + 0.06, (0.24, 0.15, 0.08), 1, "biblioteca")
        for fila in range(4):
            y = 0.1 + fila * 0.58
            _caja(P, -ANCHO, y, za, -ANCHO + 0.4, y + 0.04, zb, (0.26, 0.17, 0.09), 1, "biblioteca")
            z = za + 0.08
            while z < zb - 0.2:
                ancho = rnd.uniform(0.07, 0.15)
                alto = rnd.uniform(0.3, 0.5)
                col = rnd.choice(((0.6, 0.15, 0.15), (0.15, 0.3, 0.6), (0.15, 0.5, 0.25), (0.65, 0.5, 0.15),
                                  (0.4, 0.2, 0.55), (0.2, 0.5, 0.55), (0.55, 0.55, 0.5)))
                _q(P, (-ANCHO + 0.05, y + 0.04, z), (-ANCHO + 0.05, y + 0.04, z + ancho), (-ANCHO + 0.05, y + 0.04 + alto, z + ancho),
                   (-ANCHO + 0.05, y + 0.04 + alto, z), col, (1, 0, 0), 2, "biblioteca")
                z += ancho + 0.01

    # --- puerta de salida (pared derecha, hotspot "salida") ---
    _caja(P, ANCHO - 0.12, 0.0, 3.35, ANCHO, 2.25, 4.85, (0.12, 0.08, 0.05), 1, "salida")
    _q(P, (ANCHO - 0.13, 0.0, 3.5), (ANCHO - 0.13, 0.0, 4.7), (ANCHO - 0.13, 2.1, 4.7), (ANCHO - 0.13, 2.1, 3.5),
       (0.35, 0.22, 0.12), (-1, 0, 0), 2, "salida")
    _q(P, (ANCHO - 0.14, 0.95, 4.5), (ANCHO - 0.14, 0.95, 4.58), (ANCHO - 0.14, 1.05, 4.58), (ANCHO - 0.14, 1.05, 4.5),
       (0.9, 0.75, 0.3), (-1, 0, 0), 3, "salida")
    _q(P, (ANCHO - 0.14, 2.3, 3.6), (ANCHO - 0.14, 2.3, 4.6), (ANCHO - 0.14, 2.52, 4.6), (ANCHO - 0.14, 2.52, 3.6),
       (0.1, 0.9, 0.4), (-1, 0, 0), 3, "salida", True)                                          # cartel luminoso

    # --- detalles: tira LED bajo la mesa, servidor con pilotos, planta y silla ---
    _q(P, (-1.35, 0.70, 6.39), (1.35, 0.70, 6.39), (1.35, 0.73, 6.39), (-1.35, 0.73, 6.39),
       (0.1, 0.75, 0.95), (0, 0, -1), 2, "ordenador", True)                                    # tira LED (ilumina el suelo)
    _caja(P, 2.15, 0.0, 6.6, 2.85, 1.9, 7.5, (0.07, 0.08, 0.1), 1)                              # armario de servidores
    for fila in range(7):
        y = 0.25 + fila * 0.23
        _caja(P, 2.18, y, 6.58, 2.82, y + 0.16, 6.6, (0.11, 0.12, 0.15), 2)                     # bandejas
        for k in range(3):
            col = ((0.1, 1.0, 0.45), (1.0, 0.75, 0.1), (0.2, 0.6, 1.0))[(fila + k) % 3]
            x = 2.3 + k * 0.07
            _q(P, (x, y + 0.06, 6.575), (x + 0.03, y + 0.06, 6.575), (x + 0.03, y + 0.09, 6.575), (x, y + 0.09, 6.575),
               col, (0, 0, -1), 3, None, True)                                                  # pilotos que parpadean
    _caja(P, -2.6, 0.0, 7.1, -2.2, 0.38, 7.5, (0.45, 0.28, 0.18), 1)                            # maceta
    for hx, hz, ha in ((-2.45, 7.3, 0.9), (-2.3, 7.2, 0.75), (-2.5, 7.4, 0.68), (-2.35, 7.38, 1.05)):
        _caja(P, hx - 0.09, 0.38, hz - 0.09, hx + 0.09, ha, hz + 0.09, (0.12, 0.42, 0.2), 1)    # hojas
    _caja(P, 1.45, 0.42, 5.8, 1.95, 0.48, 6.3, (0.12, 0.13, 0.16), 1)                           # silla: asiento
    _caja(P, 1.45, 0.48, 6.24, 1.95, 1.05, 6.3, (0.12, 0.13, 0.16), 1)                          # respaldo
    _caja(P, 1.67, 0.0, 6.02, 1.73, 0.42, 6.08, (0.2, 0.2, 0.22), 1)                            # pata
    return P


ANCLAS = {"ordenador": (0.0, 1.75, 6.88), "biblioteca": (-2.9, 2.55, 3.9), "salida": (2.85, 2.7, 4.1)}
NOMBRES = {"ordenador": "ORDENADOR", "biblioteca": "BIBLIOTECA", "salida": "SALIDA"}


# =====================================================================================
#  PROYECCIÓN Y RENDER (puro)
# =====================================================================================
def a_camara(p, pose):
    """Punto del mundo -> espacio de cámara (x derecha, y arriba, z hacia delante)."""
    ex, ey, ez, yaw, pitch = pose
    dx, dy, dz = p[0] - ex, p[1] - ey, p[2] - ez
    cy_, sy_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    x = dx * cy_ - dz * sy_
    z = dx * sy_ + dz * cy_
    cp, sp_ = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    return (x, dy * cp - z * sp_, dy * sp_ + z * cp)


def proyectar(pc, w, h, f):
    return (w / 2 + f * pc[0] / pc[2], h / 2 + f * pc[1] / pc[2])


def _recortar(pts):
    """Recorta un polígono (espacio de cámara) contra el plano cercano z=NEAR."""
    sal = []
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        ina, inb = a[2] >= NEAR, b[2] >= NEAR
        if ina:
            sal.append(a)
        if ina != inb:
            t = (NEAR - a[2]) / (b[2] - a[2])
            sal.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, NEAR))
    return sal


def _sombrear(color, normal, dist, emisiva, niebla=NIEBLA, luz=None):
    if emisiva:
        base = color
        f = min(1.0, dist / 14.0) * 0.25
    elif luz is not None:                                   # iluminación calculada (luz3d_kira): lámparas de colores
        base = tuple(min(1.0, c * k) for c, k in zip(color, luz))
        f = min(1.0, dist / 13.0) * 0.42
    else:
        lamb = 0.45 + 0.55 * max(0.0, normal[0] * LUZ[0] + normal[1] * LUZ[1] + normal[2] * LUZ[2]) if normal else 0.8
        base = tuple(c * lamb for c in color)
        f = min(1.0, dist / 12.0) * 0.5
    return tuple(b + (n - b) * f for b, n in zip(base, niebla))


def render_caras(escena, pose, w, h, f=None, niebla=NIEBLA, luz=None, anim=None, t=0.0):
    """[(puntos_pantalla, (r,g,b), hotspot)] de atrás hacia delante. y de pantalla hacia ARRIBA.
    luz/anim (opcionales, de luz3d_kira.preparar): factor de luz por cara y animación de lo que brilla."""
    return [(pp, col, hot) for pp, col, hot, _i, _d in render_caras_idx(escena, pose, w, h, f, niebla, luz, anim, t)]


def color_cara(escena, i, dist, niebla=NIEBLA, luz=None, anim=None, t=0.0):
    """Color de la cara i (a 'dist' de la cámara) en el instante t. Sirve para repintar SOLO lo que brilla."""
    _pts, color, normal, _capa, _hot, emi = escena[i]
    if emi and anim is not None:
        import luz3d_kira
        color = luz3d_kira.color_animado(color, anim[i], t)
    return _sombrear(color, normal, dist, emi, niebla, luz[i] if luz is not None else None)


def render_caras_idx(escena, pose, w, h, f=None, niebla=NIEBLA, luz=None, anim=None, t=0.0):
    """Como render_caras, pero cada cara lleva también su índice en la escena y su distancia:
    [(puntos_pantalla, (r,g,b), hotspot, indice, distancia)]."""
    f = f or 0.9 * w
    ex, ey, ez = pose[0], pose[1], pose[2]
    visibles = []
    if luz is not None or anim is not None:
        import luz3d_kira
    for i, (pts, color, normal, capa, hot, emi) in enumerate(escena):
        if normal is not None:                                   # descarta caras de espaldas
            p0 = pts[0]
            if normal[0] * (ex - p0[0]) + normal[1] * (ey - p0[1]) + normal[2] * (ez - p0[2]) <= 0:
                continue
        pc = [a_camara(p, pose) for p in pts]
        if max(p[2] for p in pc) < NEAR:
            continue
        cx = sum(p[0] for p in pts) / len(pts) - ex
        cy_ = sum(p[1] for p in pts) / len(pts) - ey
        cz = sum(p[2] for p in pts) / len(pts) - ez
        dist2 = cx * cx + cy_ * cy_ + cz * cz
        if min(p[2] for p in pc) < NEAR:
            pc = _recortar(pc)
            if len(pc) < 3:
                continue
        pp = [proyectar(p, w, h, f) for p in pc]
        if max(p[0] for p in pp) < -50 or min(p[0] for p in pp) > w + 50 or max(p[1] for p in pp) < -50 or min(p[1] for p in pp) > h + 50:
            continue
        if emi and anim is not None:
            color = luz3d_kira.color_animado(color, anim[i], t)
        dist = math.sqrt(dist2)
        visibles.append((capa, -dist2, pp, _sombrear(color, normal, dist, emi, niebla,
                                                     luz[i] if luz is not None else None), hot, i, dist))
    visibles.sort(key=lambda v: (v[0], v[1]))
    return [(pp, col, hot, i, dist) for _, _, pp, col, hot, i, dist in visibles]


def punto_en_poligono(x, y, pts):
    dentro = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi:
            dentro = not dentro
        j = i
    return dentro


def hotspot_en(caras, x, y):
    """Hotspot de la cara más cercana bajo el punto (x, y) (y hacia arriba), o None."""
    for pp, _col, hot in reversed(caras):
        if punto_en_poligono(x, y, pp):
            return hot
    return None


def etiquetas(pose, w, h, f=None, anclas=None, nombres=None):
    """[(texto, x, y)] de los carteles visibles de la sala (por defecto, los de la Sala Hacker)."""
    f = f or 0.9 * w
    anclas, nombres = anclas or ANCLAS, nombres or NOMBRES
    res = []
    for k, p in anclas.items():
        pc = a_camara(p, pose)
        if pc[2] > 1.0:
            x, y = proyectar(pc, w, h, f)
            if 0 <= x <= w and 0 <= y <= h:
                res.append((nombres[k], x, y))
    return res


# =====================================================================================
#  INTENCIONES (voz o texto)
# =====================================================================================
def intencion_sala(texto):
    """'salida' | 'biblioteca' | 'ordenador' | None según lo que digas dentro de la sala."""
    import unicodedata
    t = unicodedata.normalize("NFD", str(texto).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    if any(k in t for k in ("salir", "salida", "vamonos", "irme", "volver al menu", "ir al menu", "sal de aqui", "adios")):
        return "salida"
    if any(k in t for k in ("biblioteca", "libro", "estanteria", "apuntes", "leccion", "lecciones")):
        return "biblioteca"
    if any(k in t for k in ("hack", "program", "codig", "ordenador", "computadora", "terminal", "consola", "script",
                            "desarroll", "mejorar a kira", "mejora de kira", "mejorar el sistema", "mejorar la aplicacion",
                            "mejorar tu codigo", "aprender a programar", "vamos a aprender")):
        return "ordenador"
    return None


# =====================================================================================
#  CONFIGURACIÓN DE SALA (las demás salas -salas_kira.py- usan el mismo motor con otra cfg)
# =====================================================================================
CFG_HACKER = {
    "entrada": POSE_ENTRADA, "mesa": POSE_MESA, "niebla": NIEBLA, "anclas": ANCLAS, "nombres": NOMBRES,
    "poses": {"ordenador": POSE_ORDENADOR, "biblioteca": POSE_BIBLIOTECA, "salida": POSE_SALIDA},
}


# =====================================================================================
#  RECORRIDO (cámara y estados)
# =====================================================================================
def _suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _mezcla_pose(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


class Recorrido:
    """Estados: 'caminando' (paseo hasta la mesa) | 'libre' (puedes mirar) | 'yendo' (hacia un objeto)
    | 'dentro' (esperando; el evento ya se emitió) | 'volviendo' (de vuelta a la mesa)."""

    def __init__(self, escena=None, cfg=None, luces=True):
        self.cfg = cfg or CFG_HACKER
        self.escena = escena if escena is not None else construir_escena()
        self.luz = self.anim = None
        self.luces = []
        if luces and self.cfg.get("luces", True):          # iluminación de verdad (luz3d_kira), igual en todas las salas
            import luz3d_kira
            prep = luz3d_kira.preparar(self.escena)
            self.escena, self.luz, self.anim, self.luces = prep["caras"], prep["luz"], prep["anim"], prep["luces"]
        self.reloj = 0.0                                   # para las animaciones (lo que brilla, cursores)
        self._ultimo_anim = 0.0
        self.anim_sucio = False                            # solo cambió el brillo: se repinta el color, no la sala
        self.reiniciar()

    def reiniciar(self):
        self.estado, self.t, self.destino = "caminando", 0.0, None
        self.pose = self.cfg["entrada"]
        self._origen, self._objetivo = self.cfg["entrada"], self.cfg["mesa"]
        self._dur = DURACION_PASEO
        self.sucio = True

    def pose_actual(self):
        x, y, z, yaw, pitch = self.pose
        return (x, y, z, yaw, pitch)

    def _ir(self, destino_pose, dur, estado, destino=None):
        self._origen, self._objetivo, self._dur = self.pose, destino_pose, dur
        self.t, self.estado, self.destino = 0.0, estado, destino
        self.sucio = True

    def paso(self, dt):
        """Avanza el tiempo. Devuelve 'ordenador' | 'biblioteca' | 'salida' cuando llegas a ese objeto."""
        dt = max(0.0, min(float(dt), 0.25))
        self.reloj += dt
        if self.anim is not None and self.reloj - self._ultimo_anim > 0.12:   # animación suave aunque estés quieto
            self._ultimo_anim = self.reloj
            self.anim_sucio = True                          # quieto: basta con cambiar el color de lo que brilla
        if self.estado in ("libre", "dentro"):
            return None
        self.t += dt
        k = _suave(self.t / self._dur)
        self.pose = _mezcla_pose(self._origen, self._objetivo, k)
        if self.estado == "caminando":                          # balanceo al andar
            x, y, z, yaw, pit = self.pose
            self.pose = (x, y + 0.025 * math.sin(self.t * 7.5) * (1 - k), z, yaw, pit)
        self.sucio = True
        if self.t >= self._dur:
            self.pose = self._objetivo
            if self.estado in ("caminando", "volviendo"):
                self.estado = "libre"
                return None
            self.estado, destino = "dentro", self.destino
            return destino
        return None

    # ---- gestos ----
    def saltar_paseo(self):
        if self.estado == "caminando":
            self._ir(self.cfg["mesa"], 0.4, "caminando")

    def arrastrar(self, dx_px, dy_px, ancho_px):
        """Mirar alrededor con el dedo. Solo en estado libre."""
        if self.estado != "libre" or ancho_px <= 0:
            return
        x, y, z, yaw, pit = self.pose
        grados = 70.0 / ancho_px
        yaw = max(-LIMITE_YAW, min(LIMITE_YAW, yaw - dx_px * grados))
        pit = max(-LIMITE_PITCH, min(LIMITE_PITCH, pit + dy_px * grados))
        self.pose = (x, y, z, yaw, pit)
        self.sucio = True

    def mirar(self, lado):
        """'izquierda' | 'derecha' | 'centro': giro suave sin acercarse."""
        yaw = {"izquierda": -75.0, "derecha": 75.0, "centro": 0.0}.get(lado)
        if yaw is None or self.estado not in ("libre",):
            return False
        x, y, z, _, _ = self.pose
        self._ir((x, y, z, yaw, 0.0), 0.8, "volviendo")
        return True

    def ordenar(self, destino):
        """Ir a 'ordenador' | 'biblioteca' | 'salida'. False si no se puede ahora."""
        pose = self.cfg["poses"].get(destino)
        if pose is None or self.estado not in ("libre", "caminando", "volviendo"):
            return False
        self._ir(pose, DURACION_GIRO, "yendo", destino)
        return True

    def volver(self):
        """Tras cerrar la terminal/biblioteca: vuelve a la mesa."""
        if self.estado in ("dentro", "yendo"):
            self._ir(self.cfg["mesa"], 1.0, "volviendo")

    def render(self, w, h):
        return render_caras(self.escena, self.pose, w, h, niebla=self.cfg["niebla"], luz=self.luz, anim=self.anim,
                            t=self.reloj)

    def halos(self, w, h, f=None):
        """[(x, y, radio_px, (r, g, b))] resplandor en pantalla alrededor de cada luz visible."""
        f = f or 0.9 * w
        sal = []
        import luz3d_kira
        for pos, col, inten, alcance, _n, area in self.luces:
            if area > luz3d_kira.HALO_AREA:
                continue                                    # las grandes (paneles, pantallas) ya iluminan la sala
            pc = a_camara(pos, self.pose)
            if pc[2] < 0.3:
                continue
            x, y = proyectar(pc, w, h, f)
            if -w * 0.2 < x < w * 1.2 and -h * 0.2 < y < h * 1.2:
                sal.append((x, y, min(w * 0.3, f * 0.16 * (0.6 + inten) / pc[2]), col))
        return sal

    def tocar(self, x, y, w, h):
        """Toque en pantalla (y hacia arriba). Devuelve el objeto tocado (y empieza a ir hacia él) o None."""
        if self.estado == "caminando":
            hot = hotspot_en(self.render(w, h), x, y)
            if hot == self.cfg.get("principal", "ordenador"):
                self.saltar_paseo()
            return hot
        hot = hotspot_en(self.render(w, h), x, y)
        if hot:
            self.ordenar(hot)
        return hot


# =====================================================================================
#  WIDGET KIVY
# =====================================================================================
def crear_widgets():
    from kivy.clock import Clock
    from kivy.graphics import Color, Ellipse, Rectangle, Triangle
    from kivy.metrics import dp, sp
    from kivy.uix.label import Label
    from kivy.uix.widget import Widget

    class HabitacionWidget(Widget):
        def __init__(self, recorrido=None, al_evento=None, al_tocar=None, **kw):
            super().__init__(**kw)
            self.rec = recorrido or Recorrido()
            self.al_evento, self.al_tocar = al_evento, al_tocar
            self._reloj, self._arrastre, self._inicio = None, False, (0, 0)
            self._rotulos = {}
            self.bind(size=self._marcar, pos=self._marcar)

        def _marcar(self, *_):
            self.rec.sucio = True

        def iniciar(self):
            if self._reloj is None:
                self._reloj = Clock.schedule_interval(self._tick, 1 / 30.0)

        def detener(self):
            if self._reloj is not None:
                self._reloj.cancel()
                self._reloj = None

        def _tick(self, dt):
            ev = self.rec.paso(dt)
            if self.rec.sucio:                                       # no se redibuja si nada se mueve
                self._dibujar()
                self.rec.sucio = self.rec.anim_sucio = False
            elif self.rec.anim_sucio:                                # quieto: solo cambia el color de lo que brilla
                self._repintar_brillos()
                self.rec.anim_sucio = False
            if ev and self.al_evento:
                self.al_evento(ev)

        def _dibujar(self):
            w, h = self.width, self.height
            if w < 10 or h < 10:
                return
            rec = self.rec
            caras = render_caras_idx(rec.escena, rec.pose, w, h, niebla=rec.cfg["niebla"], luz=rec.luz, anim=rec.anim,
                                     t=rec.reloj)
            ox, oy = self.x, self.y
            self._brillos = []                                       # (instrucción Color, cara, distancia)
            self.canvas.clear()
            with self.canvas:
                Color(*self.rec.cfg["niebla"], 1)
                Rectangle(pos=self.pos, size=self.size)
                for pp, col, _hot, i, dist in caras:
                    c = Color(*col, 1)
                    if rec.anim is not None and rec.anim[i] is not None:
                        self._brillos.append((c, i, dist))
                    p0 = (pp[0][0] + ox, pp[0][1] + oy)
                    for i in range(1, len(pp) - 1):
                        Triangle(points=[*p0, pp[i][0] + ox, pp[i][1] + oy, pp[i + 1][0] + ox, pp[i + 1][1] + oy])
                for x, y, r, col in self.rec.halos(w, h):          # resplandor de las luces
                    for k in (1.0, 0.82, 0.66, 0.52, 0.4, 0.3, 0.21):
                        Color(*col, 0.028)
                        Ellipse(pos=(ox + x - r * k, oy + y - r * k), size=(2 * r * k, 2 * r * k))
                for i in range(6):                                   # viñeta: bordes un poco más oscuros
                    a = 0.07 * (6 - i) / 6
                    m = (i + 1) * min(w, h) * 0.018
                    Color(0, 0, 0, a)
                    Rectangle(pos=(ox, oy), size=(w, m))
                    Rectangle(pos=(ox, oy + h - m), size=(w, m))
                    Rectangle(pos=(ox, oy), size=(m, h))
                    Rectangle(pos=(ox + w - m, oy), size=(m, h))
            vistos = set()
            for texto, x, y in etiquetas(self.rec.pose, w, h, None, self.rec.cfg["anclas"], self.rec.cfg["nombres"]):
                vistos.add(texto)
                lb = self._rotulos.get(texto)
                if lb is None:
                    lb = self._rotulos[texto] = Label(text=texto, size_hint=(None, None), font_size=sp(13),
                                                      color=(0.7, 1, 0.8, 1), size=(dp(120), dp(24)))
                    self.add_widget(lb)
                lb.opacity = 1 if self.rec.estado in ("libre", "caminando") else 0
                lb.center = (ox + x, oy + y)
            for texto, lb in self._rotulos.items():
                if texto not in vistos:
                    lb.opacity = 0

        def _repintar_brillos(self):
            rec = self.rec
            for c, i, dist in getattr(self, "_brillos", ()):
                c.rgb = color_cara(rec.escena, i, dist, niebla=rec.cfg["niebla"], luz=rec.luz, anim=rec.anim, t=rec.reloj)

        # ---- gestos: arrastrar = mirar; tocar = ir al objeto ----
        def on_touch_down(self, touch):
            if not self.collide_point(*touch.pos):
                return False
            self._arrastre, self._inicio = False, (touch.x, touch.y)
            touch.grab(self)
            return True

        def on_touch_move(self, touch):
            if touch.grab_current is not self:
                return False
            if abs(touch.x - self._inicio[0]) + abs(touch.y - self._inicio[1]) > dp(10):
                self._arrastre = True
            if self._arrastre:
                self.rec.arrastrar(touch.dx, touch.dy, self.width)
            return True

        def on_touch_up(self, touch):
            if touch.grab_current is not self:
                return False
            touch.ungrab(self)
            if not self._arrastre:
                hot = self.rec.tocar(touch.x - self.x, touch.y - self.y, self.width, self.height)
                if self.al_tocar:
                    self.al_tocar(hot)
            return True

    return HabitacionWidget
