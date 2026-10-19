# -*- coding: utf-8 -*-
"""
salas_kira.py - Las otras habitaciones 3D de Kira (mismo motor que la Sala Hacker; ver habitacion_kira.py)

  SALA DE DISEÑO (playera): ordenador de diseño al fondo con una ventana panorámica a una PLAYA, biblioteca de
      vídeo y música a la izquierda, puerta de regreso a la izquierda, puerta del CINE a la derecha.
  SALA DE CINE: pantalla grande al fondo, filas de butacas en gradas, puerta de regreso (a la sala de diseño)
      a la izquierda y salida a la derecha.
  SALA DE CIBERSEGURIDAD (búnker/matrix): pantalla grande al fondo con la silueta de Kira, panel de datos del
      dispositivo en la pared izquierda, puerta de regreso. Es una sala SOLO de lectura y aprendizaje (ver ciber_kira.py).

Puro (sin Kivy). Estética: es geometría simple y estilizada, no un modelo realista.
Ejes: x derecha, y arriba, z hacia el fondo. Habitación: x de -3 a 3, y de 0 a 2.8, z de 0 a 8.
"""
import math
import random
import re
import unicodedata

import habitacion_kira as hk
from habitacion_kira import ANCHO, ALTO, FONDO, _q, _caja


# =====================================================================================
#  AYUDAS DE GEOMETRÍA
# =====================================================================================
def _fondo(P, x0, y0, x1, y1, color, capa=1, hot=None, emi=True, z=FONDO - 0.01):
    """Rectángulo pegado a la pared del fondo, mirando a la cámara (-z)."""
    _q(P, (x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z), color, (0, 0, -1), capa, hot, emi)


def _poli_fondo(P, puntos, color, capa=2, emi=True, z=FONDO - 0.02):
    """Polígono convexo en el plano del fondo. Orden de vértices: el de las demás caras (visto desde -z)."""
    pts = [(x, y, z) for x, y in puntos]
    P.append((tuple(pts), color, (0, 0, -1), capa, None, emi))


def _disco_fondo(P, cx, cy, r, color, capa=2, n=14, z=FONDO - 0.02):
    _poli_fondo(P, [(cx + r * math.cos(a / n * 2 * math.pi), cy + r * math.sin(a / n * 2 * math.pi)) for a in range(n)],
                color, capa, True, z)


def _palma_fondo(P, x, base_y, alto, incl, capa=3):
    """Palmera en silueta sobre la ventana (plano del fondo)."""
    tx, ty = x + incl, base_y + alto
    _poli_fondo(P, [(x - 0.035, base_y), (x + 0.035, base_y), (tx + 0.02, ty), (tx - 0.02, ty)], (0.30, 0.20, 0.12), capa)
    for ang, largo in ((15, 0.42), (50, 0.38), (95, 0.30), (140, 0.38), (175, 0.42), (-20, 0.36), (200, 0.36)):
        a = math.radians(ang)
        ex, ey = tx + largo * math.cos(a), ty + largo * math.sin(a) * 0.7 - 0.05
        nx, ny = -math.sin(a) * 0.045, math.cos(a) * 0.045
        _poli_fondo(P, [(tx, ty), (tx + (ex - tx) * 0.5 + nx, ty + (ey - ty) * 0.5 + ny), (ex, ey),
                        (tx + (ex - tx) * 0.5 - nx, ty + (ey - ty) * 0.5 - ny)], (0.10, 0.45, 0.22), capa + 1)


def _palma_maceta(P, x, z, rnd):
    """Planta tipo palmera en maceta, en 3D (hojas como triángulos inclinados)."""
    _caja(P, x - 0.18, 0.0, z - 0.18, x + 0.18, 0.36, z + 0.18, (0.70, 0.45, 0.28), 1)
    _caja(P, x - 0.04, 0.36, z - 0.04, x + 0.04, 1.2, z + 0.04, (0.40, 0.28, 0.16), 1)
    for k in range(7):
        a = k / 7 * 2 * math.pi + rnd.uniform(-0.2, 0.2)
        dx, dz = math.cos(a), math.sin(a)
        punta = (x + dx * 0.75, 1.0, z + dz * 0.75)
        lado = (-dz * 0.07, dx * 0.07)
        base = (x, 1.22, z)
        P.append(((base, (x + dx * 0.4 + lado[0], 1.25, z + dz * 0.4 + lado[1]), punta,
                   (x + dx * 0.4 - lado[0], 1.25, z + dz * 0.4 - lado[1])),
                  (0.12, 0.52, 0.25) if k % 2 else (0.18, 0.60, 0.30), None, 2, None, False))


# =====================================================================================
#  SALA DE DISEÑO (playera)
# =====================================================================================
POSE_D_ENTRADA = (0.0, 1.62, 0.5, 0.0, 0.0)
POSE_D_MESA = (0.0, 1.55, 5.0, 0.0, 0.0)
POSE_D_ORDENADOR = (0.0, 1.30, 5.85, 0.0, 0.0)
POSE_D_BIBLIOTECA = (-1.35, 1.5, 5.5, -90.0, 0.0)
POSE_D_REGRESO = (-1.35, 1.5, 2.3, -90.0, 0.0)
POSE_D_CINE = (1.35, 1.5, 4.1, 90.0, 0.0)
NIEBLA_PLAYA = (0.80, 0.78, 0.66)

ANCLAS_D = {"ordenador": (0.0, 1.78, 6.85), "biblioteca": (-2.9, 2.55, 5.5), "regreso": (-2.85, 2.55, 2.3),
            "cine": (2.85, 2.7, 4.1)}
NOMBRES_D = {"ordenador": "DISEÑO", "biblioteca": "MEDIATECA", "regreso": "VOLVER", "cine": "CINE"}


def construir_diseno(semilla=11):
    rnd = random.Random(semilla)
    P = []
    # --- estructura (capa 0): suelo de madera clara, paredes color agua, techo de bambú ---
    for i in range(16):
        z0 = i * 0.5
        _q(P, (-ANCHO, 0, z0), (ANCHO, 0, z0), (ANCHO, 0, z0 + 0.5), (-ANCHO, 0, z0 + 0.5),
           (0.80, 0.66, 0.46) if i % 2 else (0.74, 0.60, 0.41), (0, 1, 0), 0)
    agua = (0.52, 0.84, 0.84)
    _q(P, (-ANCHO, 0, 0), (-ANCHO, 0, FONDO), (-ANCHO, ALTO, FONDO), (-ANCHO, ALTO, 0), agua, (1, 0, 0), 0)
    _q(P, (ANCHO, 0, FONDO), (ANCHO, 0, 0), (ANCHO, ALTO, 0), (ANCHO, ALTO, FONDO), (0.95, 0.90, 0.78), (-1, 0, 0), 0)
    _q(P, (-ANCHO, 0, FONDO), (ANCHO, 0, FONDO), (ANCHO, ALTO, FONDO), (-ANCHO, ALTO, FONDO), (0.96, 0.92, 0.80), (0, 0, -1), 0)
    _q(P, (ANCHO, 0, 0), (-ANCHO, 0, 0), (-ANCHO, ALTO, 0), (ANCHO, ALTO, 0), agua, (0, 0, 1), 0)
    _q(P, (-ANCHO, ALTO, 0), (ANCHO, ALTO, 0), (ANCHO, ALTO, FONDO), (-ANCHO, ALTO, FONDO), (0.90, 0.80, 0.60), (0, -1, 0), 0)
    for z in (1.0, 3.0, 5.0, 7.0):                                           # vigas de bambú
        _caja(P, -ANCHO, ALTO - 0.14, z, ANCHO, ALTO, z + 0.14, (0.55, 0.38, 0.20), 1)
    for z in (1.8, 4.2, 6.6):                                                # luces cálidas
        for x in (-1.4, 1.4):
            _q(P, (x - 0.3, ALTO - 0.15, z), (x + 0.3, ALTO - 0.15, z), (x + 0.3, ALTO - 0.15, z + 0.3),
               (x - 0.3, ALTO - 0.15, z + 0.3), (1.0, 0.92, 0.7), (0, -1, 0), 2, None, True)
    # alfombra de rayas azul y crema bajo el escritorio
    for k in range(6):
        _q(P, (-1.9 + k * 0.633, 0.01, 5.0), (-1.9 + (k + 1) * 0.633, 0.01, 5.0), (-1.9 + (k + 1) * 0.633, 0.01, 7.6),
           (-1.9 + k * 0.633, 0.01, 7.6), (0.20, 0.52, 0.66) if k % 2 == 0 else (0.96, 0.92, 0.80), (0, 1, 0), 1)

    # --- VENTANA PANORÁMICA a la playa (pared del fondo) ---
    X0, X1, Y0, Y1 = -2.4, 2.4, 0.95, 2.5
    _fondo(P, X0, 1.80, X1, Y1, (0.40, 0.72, 0.95), 1)                       # cielo
    _fondo(P, X0, 1.45, X1, 1.80, (0.72, 0.88, 0.96), 1)
    _fondo(P, X0, 1.30, X1, 1.45, (0.20, 0.64, 0.84), 1)                     # mar: franjas
    _fondo(P, X0, 1.16, X1, 1.30, (0.14, 0.55, 0.78), 1)
    _fondo(P, X0, 1.04, X1, 1.16, (0.30, 0.78, 0.82), 1)
    _fondo(P, X0, Y0, X1, 1.04, (0.95, 0.86, 0.64), 1)                       # arena
    _fondo(P, X0, 1.00, X1, 1.07, (0.98, 0.98, 0.95), 2)                     # espuma
    _disco_fondo(P, 1.1, 2.02, 0.22, (1.0, 0.93, 0.55), 2)                  # sol
    for (cx, cy, r) in ((-1.2, 2.2, 0.16), (-0.95, 2.17, 0.2), (-0.68, 2.2, 0.15), (0.2, 2.3, 0.14), (0.45, 2.27, 0.18)):
        _disco_fondo(P, cx, cy, r, (1.0, 1.0, 1.0), 2, 10)                  # nubes
    _poli_fondo(P, [(-0.2, 1.46), (0.22, 1.46), (0.1, 1.56), (-0.12, 1.56)], (0.55, 0.30, 0.18), 2)   # barco
    _poli_fondo(P, [(0.02, 1.56), (0.17, 1.56), (0.02, 1.86)], (1.0, 1.0, 1.0), 2)
    _palma_fondo(P, -1.9, 0.98, 0.95, 0.18)
    _palma_fondo(P, 1.95, 0.98, 1.05, -0.2)
    _poli_fondo(P, [(-1.0, 0.98), (-0.7, 0.98), (-0.78, 1.1), (-0.95, 1.1)], (0.95, 0.35, 0.4), 2)    # toalla
    # marco de madera blanca y parteluces
    blanco = (0.97, 0.95, 0.90)
    _caja(P, X0 - 0.1, Y0 - 0.08, FONDO - 0.12, X1 + 0.1, Y0, FONDO, blanco, 2)
    _caja(P, X0 - 0.1, Y1, FONDO - 0.12, X1 + 0.1, Y1 + 0.08, FONDO, blanco, 2)
    for x in (X0 - 0.1, X1, -0.8, 0.8):
        _caja(P, x, Y0, FONDO - 0.1, x + 0.1, Y1, FONDO, blanco, 2)
    _caja(P, X0 - 0.2, Y0 - 0.14, FONDO - 0.32, X1 + 0.2, Y0 - 0.08, FONDO, (0.85, 0.72, 0.5), 2)      # alféizar
    for (xa, xb) in ((-2.9, -2.45), (2.45, 2.9)):                           # cortinas
        _caja(P, xa, 0.3, FONDO - 0.22, xb, 2.65, FONDO - 0.12, (0.98, 0.93, 0.82), 2)
        _caja(P, xa, 0.3, FONDO - 0.24, xb, 0.34, FONDO - 0.12, (0.9, 0.78, 0.6), 2)

    # --- escritorio de diseño (hotspot "ordenador") ---
    madera = (0.92, 0.82, 0.62)
    _caja(P, -1.5, 0.74, 6.3, 1.5, 0.80, 7.5, madera, 1, "ordenador")
    for lx, lz in ((-1.45, 6.35), (1.37, 6.35), (-1.45, 7.37), (1.37, 7.37)):
        _caja(P, lx, 0.0, lz, lx + 0.08, 0.74, lz + 0.08, (0.85, 0.72, 0.5), 1, "ordenador")
    _caja(P, -0.7, 0.98, 6.9, 0.7, 1.68, 6.98, (0.95, 0.95, 0.97), 1, "ordenador")            # monitor ancho, marco blanco
    _caja(P, -0.06, 0.80, 6.92, 0.06, 1.0, 7.0, (0.85, 0.85, 0.88), 1, "ordenador")
    _caja(P, -0.22, 0.80, 6.8, 0.22, 0.83, 7.05, (0.85, 0.85, 0.88), 1, "ordenador")
    _q(P, (-0.65, 1.02, 6.89), (0.65, 1.02, 6.89), (0.65, 1.64, 6.89), (-0.65, 1.64, 6.89), (0.10, 0.12, 0.2), (0, 0, -1), 2, "ordenador", True)
    # contenido de la pantalla: barra superior, herramientas, lienzo con degradado de atardecer, línea de tiempo
    _q(P, (-0.65, 1.58, 6.885), (0.65, 1.58, 6.885), (0.65, 1.64, 6.885), (-0.65, 1.64, 6.885), (0.30, 0.35, 0.6), (0, 0, -1), 3, "ordenador", True)
    for k in range(5):
        _q(P, (-0.62, 1.50 - k * 0.09, 6.884), (-0.52, 1.50 - k * 0.09, 6.884), (-0.52, 1.56 - k * 0.09, 6.884),
           (-0.62, 1.56 - k * 0.09, 6.884), (0.5, 0.6, 0.9), (0, 0, -1), 3, "ordenador", True)
    for k, col in enumerate(((0.28, 0.2, 0.55), (0.9, 0.45, 0.35), (1.0, 0.7, 0.3))):
        _q(P, (-0.45, 1.12 + k * 0.1, 6.884), (0.35, 1.12 + k * 0.1, 6.884), (0.35, 1.22 + k * 0.1, 6.884),
           (-0.45, 1.22 + k * 0.1, 6.884), col, (0, 0, -1), 3, "ordenador", True)           # lienzo
    _q(P, (-0.45, 1.42, 6.884), (0.35, 1.42, 6.884), (0.35, 1.54, 6.884), (-0.45, 1.54, 6.884), (0.2, 0.15, 0.4), (0, 0, -1), 3, "ordenador", True)
    _q(P, (0.42, 1.10, 6.884), (0.62, 1.10, 6.884), (0.62, 1.54, 6.884), (0.42, 1.54, 6.884), (0.2, 0.25, 0.4), (0, 0, -1), 3, "ordenador", True)  # paneles
    for k, col in enumerate(((0.9, 0.3, 0.4), (0.3, 0.8, 0.9), (0.95, 0.8, 0.3))):
        _q(P, (0.44, 1.46 - k * 0.1, 6.883), (0.60, 1.46 - k * 0.1, 6.883), (0.60, 1.52 - k * 0.1, 6.883),
           (0.44, 1.52 - k * 0.1, 6.883), col, (0, 0, -1), 4, "ordenador", True)
    _q(P, (-0.45, 1.05, 6.883), (0.35, 1.05, 6.883), (0.35, 1.09, 6.883), (-0.45, 1.09, 6.883), (0.3, 0.9, 0.6), (0, 0, -1), 4, "ordenador", True)  # timeline
    _caja(P, -0.4, 0.80, 6.4, 0.2, 0.82, 6.7, (0.96, 0.96, 0.98), 2, "ordenador")              # teclado
    _caja(P, 0.55, 0.80, 6.4, 0.95, 0.815, 6.8, (0.12, 0.12, 0.15), 2, "ordenador")            # tableta gráfica
    _caja(P, 0.7, 0.815, 6.5, 0.72, 0.83, 6.62, (0.9, 0.3, 0.3), 3, "ordenador")               # lápiz
    _caja(P, -1.3, 0.80, 6.9, -1.1, 1.15, 7.05, (0.15, 0.15, 0.18), 2, "ordenador")            # altavoces
    _caja(P, 1.1, 0.80, 6.9, 1.3, 1.15, 7.05, (0.15, 0.15, 0.18), 2, "ordenador")
    _caja(P, -1.0, 0.80, 6.5, -0.85, 0.95, 6.65, (0.85, 0.5, 0.3), 2, "ordenador")             # maceta con cactus
    _caja(P, -0.96, 0.95, 6.54, -0.89, 1.15, 6.61, (0.2, 0.6, 0.3), 3, "ordenador")

    # --- biblioteca de vídeo y música (pared izquierda, hotspot "biblioteca") ---
    cols = ((0.95, 0.4, 0.4), (0.3, 0.7, 0.9), (0.98, 0.8, 0.3), (0.4, 0.8, 0.6), (0.7, 0.5, 0.9), (0.95, 0.6, 0.3), (0.2, 0.2, 0.25))
    for (za, zb) in ((3.7, 5.5), (5.5, 7.3)):
        _q(P, (-ANCHO + 0.01, 0.1, za), (-ANCHO + 0.01, 0.1, zb), (-ANCHO + 0.01, 2.4, zb), (-ANCHO + 0.01, 2.4, za),
           (0.55, 0.40, 0.24), (1, 0, 0), 1, "biblioteca")
        for zp in (za, zb - 0.06):
            _caja(P, -ANCHO, 0.1, zp, -ANCHO + 0.4, 2.4, zp + 0.06, (0.85, 0.72, 0.5), 1, "biblioteca")
        for fila in range(4):
            y = 0.1 + fila * 0.58
            _caja(P, -ANCHO, y, za, -ANCHO + 0.4, y + 0.04, zb, (0.88, 0.76, 0.54), 1, "biblioteca")
            z = za + 0.08
            while z < zb - 0.2:
                ancho = rnd.uniform(0.08, 0.16)
                col = rnd.choice(cols)
                if fila % 2 == 0:                                   # cajas de vídeo (altas)
                    alto = rnd.uniform(0.34, 0.5)
                else:                                               # discos / cintas (bajitos y anchos)
                    alto = rnd.uniform(0.18, 0.28)
                _q(P, (-ANCHO + 0.05, y + 0.04, z), (-ANCHO + 0.05, y + 0.04, z + ancho), (-ANCHO + 0.05, y + 0.04 + alto, z + ancho),
                   (-ANCHO + 0.05, y + 0.04 + alto, z), col, (1, 0, 0), 2, "biblioteca")
                z += ancho + 0.01
    _caja(P, -ANCHO + 0.02, 2.4, 3.9, -ANCHO + 0.3, 2.52, 7.1, (0.9, 0.3, 0.35), 2, "biblioteca", True)   # rótulo de neón MEDIATECA

    # --- puerta de regreso (pared izquierda, hotspot "regreso") ---
    _caja(P, -ANCHO, 0.0, 1.55, -ANCHO + 0.12, 2.25, 3.05, (0.95, 0.92, 0.85), 1, "regreso")
    _q(P, (-ANCHO + 0.13, 0.0, 1.7), (-ANCHO + 0.13, 0.0, 2.9), (-ANCHO + 0.13, 2.1, 2.9), (-ANCHO + 0.13, 2.1, 1.7),
       (0.35, 0.65, 0.78), (1, 0, 0), 2, "regreso")
    for k in range(3):                                                          # tablillas
        _q(P, (-ANCHO + 0.14, 0.2 + k * 0.6, 1.8), (-ANCHO + 0.14, 0.2 + k * 0.6, 2.8), (-ANCHO + 0.14, 0.26 + k * 0.6, 2.8),
           (-ANCHO + 0.14, 0.26 + k * 0.6, 1.8), (0.45, 0.75, 0.88), (1, 0, 0), 3, "regreso")
    _q(P, (-ANCHO + 0.14, 0.95, 1.8), (-ANCHO + 0.14, 0.95, 1.88), (-ANCHO + 0.14, 1.05, 1.88), (-ANCHO + 0.14, 1.05, 1.8),
       (0.9, 0.75, 0.3), (1, 0, 0), 3, "regreso")
    _q(P, (-ANCHO + 0.14, 2.3, 1.8), (-ANCHO + 0.14, 2.3, 2.8), (-ANCHO + 0.14, 2.52, 2.8), (-ANCHO + 0.14, 2.52, 1.8),
       (0.2, 0.85, 0.9), (1, 0, 0), 3, "regreso", True)                                       # cartel luminoso

    # --- puerta del CINE (pared derecha, hotspot "cine") ---
    _caja(P, ANCHO - 0.12, 0.0, 3.3, ANCHO, 2.3, 4.9, (0.35, 0.10, 0.12), 1, "cine")
    _q(P, (ANCHO - 0.13, 0.0, 3.45), (ANCHO - 0.13, 0.0, 4.75), (ANCHO - 0.13, 2.1, 4.75), (ANCHO - 0.13, 2.1, 3.45),
       (0.62, 0.14, 0.18), (-1, 0, 0), 2, "cine")
    for zc in (3.9, 4.3):                                                       # ojos de buey
        _q(P, (ANCHO - 0.14, 1.5, zc - 0.12), (ANCHO - 0.14, 1.5, zc + 0.12), (ANCHO - 0.14, 1.74, zc + 0.12),
           (ANCHO - 0.14, 1.74, zc - 0.12), (0.95, 0.85, 0.5), (-1, 0, 0), 3, "cine", True)
    _q(P, (ANCHO - 0.14, 0.95, 4.55), (ANCHO - 0.14, 0.95, 4.63), (ANCHO - 0.14, 1.05, 4.63), (ANCHO - 0.14, 1.05, 4.55),
       (0.9, 0.75, 0.3), (-1, 0, 0), 3, "cine")
    _q(P, (ANCHO - 0.14, 2.32, 3.5), (ANCHO - 0.14, 2.32, 4.7), (ANCHO - 0.14, 2.55, 4.7), (ANCHO - 0.14, 2.55, 3.5),
       (1.0, 0.75, 0.2), (-1, 0, 0), 3, "cine", True)                                         # cartel CINE
    for zc in (3.65, 3.95, 4.25, 4.55):                                         # bombillas del cartel
        _q(P, (ANCHO - 0.15, 2.37, zc - 0.04), (ANCHO - 0.15, 2.37, zc + 0.04), (ANCHO - 0.15, 2.5, zc + 0.04),
           (ANCHO - 0.15, 2.5, zc - 0.04), (1.0, 0.3, 0.2), (-1, 0, 0), 4, "cine", True)

    # --- decoración playera ---
    for zt, col in ((0.9, (0.95, 0.45, 0.3)), (1.35, (0.3, 0.75, 0.85))):       # tablas de surf contra la pared derecha
        _q(P, (ANCHO - 0.06, 0.05, zt - 0.17), (ANCHO - 0.06, 0.05, zt + 0.17), (ANCHO - 0.06, 2.0, zt + 0.12), (ANCHO - 0.06, 2.0, zt - 0.12),
           col, (-1, 0, 0), 1)
        _q(P, (ANCHO - 0.07, 0.05, zt - 0.03), (ANCHO - 0.07, 0.05, zt + 0.03), (ANCHO - 0.07, 2.0, zt + 0.02), (ANCHO - 0.07, 2.0, zt - 0.02),
           (1.0, 1.0, 0.95), (-1, 0, 0), 2)
    # sombrilla
    sx, sz = 2.0, 2.0
    _caja(P, sx - 0.03, 0.0, sz - 0.03, sx + 0.03, 2.0, sz + 0.03, (0.9, 0.9, 0.85), 1)
    n = 8
    for k in range(n):
        a0, a1 = k / n * 2 * math.pi, (k + 1) / n * 2 * math.pi
        P.append((((sx, 2.25, sz), (sx + 0.85 * math.cos(a0), 1.95, sz + 0.85 * math.sin(a0)),
                   (sx + 0.85 * math.cos(a1), 1.95, sz + 0.85 * math.sin(a1))),
                  (0.95, 0.3, 0.3) if k % 2 else (1.0, 0.97, 0.92), None, 2, None, False))
    # hamaca en el rincón derecho del fondo (entre dos postes)
    for zp in (5.4, 7.0):
        _caja(P, ANCHO - 0.5, 0.0, zp, ANCHO - 0.4, 1.5, zp + 0.1, (0.55, 0.38, 0.2), 1)
    for k in range(6):
        t0, t1 = k / 6, (k + 1) / 6
        z0, z1 = 5.45 + 1.6 * t0, 5.45 + 1.6 * t1
        y0, y1 = 1.35 - 0.55 * math.sin(math.pi * t0), 1.35 - 0.55 * math.sin(math.pi * t1)
        _q(P, (ANCHO - 0.9, y0, z0), (ANCHO - 0.5, y0 + 0.05, z0), (ANCHO - 0.5, y1 + 0.05, z1), (ANCHO - 0.9, y1, z1),
           (0.98, 0.93, 0.82) if k % 2 else (0.3, 0.7, 0.8), (0, 1, 0), 2)
    # plantas, conchas y estrella de mar
    _palma_maceta(P, 2.45, 7.55, rnd)
    _palma_maceta(P, -2.4, 1.1, rnd)
    for (cx, cz, col) in ((-0.6, 3.0, (1.0, 0.8, 0.8)), (0.7, 2.4, (0.98, 0.92, 0.85)), (-1.2, 4.3, (0.95, 0.7, 0.7)), (1.1, 3.6, (1.0, 0.95, 0.9))):
        _q(P, (cx - 0.07, 0.02, cz - 0.05), (cx + 0.07, 0.02, cz - 0.05), (cx + 0.05, 0.02, cz + 0.06), (cx - 0.05, 0.02, cz + 0.06), col, (0, 1, 0), 2)
    puntos = []
    for k in range(10):
        r = 0.2 if k % 2 == 0 else 0.08
        a = k / 10 * 2 * math.pi
        puntos.append((0.2 + r * math.cos(a), 0.02, 1.6 + r * math.sin(a)))
    P.append((tuple(puntos[::-1]), (0.95, 0.5, 0.25), (0, 1, 0), 2, None, False))
    # pelota de playa (rombos de colores)
    for k, col in enumerate(((0.95, 0.3, 0.3), (1.0, 0.95, 0.9), (0.3, 0.6, 0.95), (1.0, 0.85, 0.3))):
        a0, a1 = k / 4 * 2 * math.pi, (k + 1) / 4 * 2 * math.pi
        P.append((((-0.1, 0.03, 4.0), (-0.1 + 0.18 * math.cos(a0), 0.03, 4.0 + 0.18 * math.sin(a0)),
                   (-0.1 + 0.18 * math.cos(a1), 0.03, 4.0 + 0.18 * math.sin(a1))), col, (0, 1, 0), 2, None, False))
    return P


# =====================================================================================
#  SALA DE CINE
# =====================================================================================
POSE_C_ENTRADA = (0.0, 1.62, 0.4, 0.0, 0.0)
POSE_C_MESA = (0.0, 1.8, 3.4, 0.0, 0.0)
POSE_C_PANTALLA = (0.0, 1.75, 5.2, 0.0, 0.0)
POSE_C_REGRESO = (-1.35, 1.75, 3.4, -90.0, 0.0)
POSE_C_SALIDA = (1.35, 1.75, 3.4, 90.0, 0.0)
NIEBLA_CINE = (0.03, 0.01, 0.02)
ANCLAS_C = {"pantalla": (0.0, 2.85, 7.9), "regreso": (-2.85, 2.55, 3.4), "salida": (2.85, 2.55, 3.4)}
NOMBRES_C = {"pantalla": "PANTALLA", "regreso": "SALA DE DISEÑO", "salida": "SALIR"}
FILAS_Z = (1.9, 3.1, 4.3, 5.5)
FILAS_Y = (0.45, 0.30, 0.15, 0.0)


def construir_cine(semilla=5):
    rnd = random.Random(semilla)
    P = []
    # estructura
    for i in range(16):
        z0 = i * 0.5
        _q(P, (-ANCHO, 0, z0), (ANCHO, 0, z0), (ANCHO, 0, z0 + 0.5), (-ANCHO, 0, z0 + 0.5),
           (0.30, 0.05, 0.08) if i % 2 else (0.26, 0.04, 0.07), (0, 1, 0), 0)
    pared = (0.22, 0.05, 0.08)
    _q(P, (-ANCHO, 0, 0), (-ANCHO, 0, FONDO), (-ANCHO, ALTO, FONDO), (-ANCHO, ALTO, 0), pared, (1, 0, 0), 0)
    _q(P, (ANCHO, 0, FONDO), (ANCHO, 0, 0), (ANCHO, ALTO, 0), (ANCHO, ALTO, FONDO), pared, (-1, 0, 0), 0)
    _q(P, (-ANCHO, 0, FONDO), (ANCHO, 0, FONDO), (ANCHO, ALTO, FONDO), (-ANCHO, ALTO, FONDO), (0.12, 0.03, 0.05), (0, 0, -1), 0)
    _q(P, (ANCHO, 0, 0), (-ANCHO, 0, 0), (-ANCHO, ALTO, 0), (ANCHO, ALTO, 0), pared, (0, 0, 1), 0)
    _q(P, (-ANCHO, ALTO, 0), (ANCHO, ALTO, 0), (ANCHO, ALTO, FONDO), (-ANCHO, ALTO, FONDO), (0.06, 0.02, 0.04), (0, -1, 0), 0)
    for k in range(18):                                                      # "estrellas" del techo
        x = rnd.uniform(-2.8, 2.8)
        z = rnd.uniform(0.5, 7.5)
        _q(P, (x, ALTO - 0.01, z), (x + 0.06, ALTO - 0.01, z), (x + 0.06, ALTO - 0.01, z + 0.06), (x, ALTO - 0.01, z + 0.06),
           (0.9, 0.85, 0.6), (0, -1, 0), 2, None, True)
    # pantalla grande con marco, cortinas y escenario
    _caja(P, -2.7, 0.0, 7.5, 2.7, 0.55, 8.0, (0.14, 0.05, 0.07), 1, "pantalla")
    _caja(P, -2.55, 0.7, 7.9, 2.55, 2.75, 8.0, (0.04, 0.04, 0.05), 1, "pantalla")
    _q(P, (-2.45, 0.8, 7.89), (2.45, 0.8, 7.89), (2.45, 2.65, 7.89), (-2.45, 2.65, 7.89), (0.80, 0.84, 0.92), (0, 0, -1), 2, "pantalla", True)
    # imagen en la pantalla: logotipo estilizado (una playa) para que se vea "encendida"
    _q(P, (-2.45, 1.9, 7.88), (2.45, 1.9, 7.88), (2.45, 2.65, 7.88), (-2.45, 2.65, 7.88), (0.35, 0.60, 0.9), (0, 0, -1), 3, "pantalla", True)
    _q(P, (-2.45, 1.45, 7.88), (2.45, 1.45, 7.88), (2.45, 1.9, 7.88), (-2.45, 1.9, 7.88), (0.15, 0.50, 0.75), (0, 0, -1), 3, "pantalla", True)
    _q(P, (-2.45, 0.8, 7.88), (2.45, 0.8, 7.88), (2.45, 1.45, 7.88), (-2.45, 1.45, 7.88), (0.93, 0.83, 0.58), (0, 0, -1), 3, "pantalla", True)
    n = 14
    P.append((tuple((1.4 + 0.3 * math.cos(a / n * 6.2832), 2.25 + 0.3 * math.sin(a / n * 6.2832), 7.87) for a in range(n)),
              (1.0, 0.92, 0.5), (0, 0, -1), 4, "pantalla", True))
    for (xa, xb) in ((-3.0, -2.6), (2.6, 3.0)):                              # cortinas de terciopelo
        _caja(P, xa, 0.0, 7.2, xb, 2.8, 7.95, (0.55, 0.06, 0.12), 2, "pantalla")
    _caja(P, -3.0, 2.6, 7.2, 3.0, 2.8, 7.95, (0.55, 0.06, 0.12), 2, "pantalla")
    # gradas y butacas
    for zr, yr in zip(FILAS_Z, FILAS_Y):
        if yr > 0:
            _caja(P, -2.85, 0.0, zr - 0.2, 2.85, yr, zr + 1.0, (0.28, 0.05, 0.08), 1, "pantalla")
        _q(P, (-2.85, yr + 0.003, zr - 0.2), (2.85, yr + 0.003, zr - 0.2), (2.85, yr + 0.003, zr - 0.2 + 1.2),
           (-2.85, yr + 0.003, zr - 0.2 + 1.2), (0.30, 0.06, 0.10), (0, 1, 0), 1)
        for lado in (-1, 1):
            for k in range(3):
                x0 = (0.55 + k * 0.62) * lado
                xa, xb = (x0, x0 + 0.55) if lado > 0 else (x0 - 0.55, x0)
                _caja(P, xa + 0.02, yr + 0.05, zr + 0.1, xb - 0.02, yr + 0.45, zr + 0.6, (0.62, 0.08, 0.14), 2, "pantalla")     # asiento
                _caja(P, xa + 0.02, yr + 0.45, zr + 0.0, xb - 0.02, yr + 1.1, zr + 0.14, (0.55, 0.06, 0.12), 2, "pantalla")     # respaldo
                _caja(P, xa - 0.02, yr + 0.3, zr + 0.1, xa + 0.04, yr + 0.62, zr + 0.6, (0.35, 0.04, 0.08), 3, "pantalla")      # reposabrazos
    # luces de pasillo
    for zr, yr in zip(FILAS_Z, FILAS_Y):
        for x in (-0.46, 0.46):
            _q(P, (x - 0.03, yr + 0.01, zr), (x + 0.03, yr + 0.01, zr), (x + 0.03, yr + 0.01, zr + 0.9), (x - 0.03, yr + 0.01, zr + 0.9),
               (1.0, 0.7, 0.3), (0, 1, 0), 2, None, True)
    # carteles de películas en las paredes (formas de colores, sin marcas)
    for z, col in ((1.2, (0.9, 0.5, 0.2)), (6.0, (0.2, 0.55, 0.85))):
        _q(P, (-ANCHO + 0.03, 1.0, z), (-ANCHO + 0.03, 1.0, z + 0.7), (-ANCHO + 0.03, 2.1, z + 0.7), (-ANCHO + 0.03, 2.1, z),
           col, (1, 0, 0), 1, None, True)
        _q(P, (-ANCHO + 0.04, 1.6, z + 0.1), (-ANCHO + 0.04, 1.6, z + 0.6), (-ANCHO + 0.04, 1.9, z + 0.6), (-ANCHO + 0.04, 1.9, z + 0.1),
           (0.1, 0.1, 0.15), (1, 0, 0), 2, None, True)
    # puerta de regreso a la sala de diseño (izquierda) y salida (derecha) a la altura del pasillo
    _caja(P, -ANCHO, 0.0, 2.65, -ANCHO + 0.12, 2.3, 4.15, (0.20, 0.45, 0.55), 1, "regreso")
    _q(P, (-ANCHO + 0.13, 0.0, 2.8), (-ANCHO + 0.13, 0.0, 4.0), (-ANCHO + 0.13, 2.1, 4.0), (-ANCHO + 0.13, 2.1, 2.8),
       (0.40, 0.75, 0.82), (1, 0, 0), 2, "regreso")
    _q(P, (-ANCHO + 0.14, 2.32, 2.85), (-ANCHO + 0.14, 2.32, 3.95), (-ANCHO + 0.14, 2.52, 3.95), (-ANCHO + 0.14, 2.52, 2.85),
       (0.2, 0.85, 0.9), (1, 0, 0), 3, "regreso", True)
    _caja(P, ANCHO - 0.12, 0.0, 2.65, ANCHO, 2.3, 4.15, (0.10, 0.18, 0.12), 1, "salida")
    _q(P, (ANCHO - 0.13, 0.0, 2.8), (ANCHO - 0.13, 0.0, 4.0), (ANCHO - 0.13, 2.1, 4.0), (ANCHO - 0.13, 2.1, 2.8),
       (0.18, 0.32, 0.2), (-1, 0, 0), 2, "salida")
    _q(P, (ANCHO - 0.14, 2.32, 2.85), (ANCHO - 0.14, 2.32, 3.95), (ANCHO - 0.14, 2.52, 3.95), (ANCHO - 0.14, 2.52, 2.85),
       (0.1, 0.9, 0.4), (-1, 0, 0), 3, "salida", True)
    # puesto de palomitas junto a la entrada
    _caja(P, 2.2, 0.0, 0.5, 2.8, 1.0, 1.1, (0.85, 0.15, 0.15), 1)
    _caja(P, 2.15, 1.0, 0.45, 2.85, 1.2, 1.15, (1.0, 0.95, 0.7), 2)
    _caja(P, 2.3, 1.2, 0.6, 2.7, 1.45, 1.0, (1.0, 0.85, 0.3), 3, None, True)
    return P


# =====================================================================================
#  INTENCIONES (voz o texto)
# =====================================================================================
def _norm(texto):
    t = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def intencion_diseno(texto):
    t = _norm(texto)
    if any(k in t for k in ("salir", "salida", "volver", "regres", "menu", "adios", "vamonos")):
        return "regreso"
    if any(k in t for k in ("cine", "pelicula", "butaca", "proyect", "ver un video", "ver el video", "ver video")):
        return "cine"
    if any(k in t for k in ("crear", "hacer", "dise", "videoclip", "guion", "maqueta", "pagina", "web", "aplicacion")) or \
            re.search(r"\bapp\b", t):
        return "ordenador"
    if any(k in t for k in ("biblioteca", "mediateca", "musica", "cancion", "video", "audio", "album", "coleccion")):
        return "biblioteca"
    if any(k in t for k in ("grafic", "ordenador", "computadora", "clip")):
        return "ordenador"
    return None


def intencion_cine(texto):
    t = _norm(texto)
    if any(k in t for k in ("salir", "salida", "menu", "adios", "vamonos")):
        return "salida"
    if any(k in t for k in ("dise", "volver", "regres", "estudio")):
        return "regreso"
    if any(k in t for k in ("ver", "pelicula", "video", "pantalla", "reproduc", "poner", "play", "empez", "cine")):
        return "pantalla"
    return None


# =====================================================================================
#  CONFIGURACIONES PARA EL MOTOR
# =====================================================================================
CFG_DISENO = {
    "entrada": POSE_D_ENTRADA, "mesa": POSE_D_MESA, "niebla": NIEBLA_PLAYA, "anclas": ANCLAS_D, "nombres": NOMBRES_D,
    "poses": {"ordenador": POSE_D_ORDENADOR, "biblioteca": POSE_D_BIBLIOTECA, "regreso": POSE_D_REGRESO, "cine": POSE_D_CINE},
    "principal": "ordenador",
}
CFG_CINE = {
    "entrada": POSE_C_ENTRADA, "mesa": POSE_C_MESA, "niebla": NIEBLA_CINE, "anclas": ANCLAS_C, "nombres": NOMBRES_C,
    "poses": {"pantalla": POSE_C_PANTALLA, "regreso": POSE_C_REGRESO, "salida": POSE_C_SALIDA},
    "principal": "pantalla",
}


def recorrido_diseno():
    return hk.Recorrido(construir_diseno(), CFG_DISENO)


def recorrido_cine():
    return hk.Recorrido(construir_cine(), CFG_CINE)


# =====================================================================================
#  SALA DE CIBERSEGURIDAD (búnker / matrix) - SOLO lectura y aprendizaje
# =====================================================================================
POSE_X_ENTRADA = (0.0, 1.62, 0.5, 0.0, 0.0)
POSE_X_MESA = (0.0, 1.55, 5.2, 0.0, 0.0)
POSE_X_CENTRO = (0.0, 1.45, 6.1, 0.0, 0.0)
POSE_X_DISPOSITIVO = (-1.35, 1.5, 4.2, -90.0, 0.0)
POSE_X_REGRESO = (1.35, 1.5, 4.1, 90.0, 0.0)
NIEBLA_CIBER = (0.01, 0.03, 0.02)
ANCLAS_X = {"centro": (0.0, 2.0, 6.9), "dispositivo": (-2.9, 2.5, 4.2), "regreso": (2.85, 2.6, 4.1)}
NOMBRES_X = {"centro": "KIRA", "dispositivo": "DISPOSITIVO", "regreso": "SALIR"}
_VERDE_MATRIX = (0.15, 0.95, 0.45)


def _rejilla_pared(P, eje, fijo, a0, a1, b0, b1, normal, color, paso=0.5):
    """Líneas finas de rejilla (emisivas) sobre una pared. eje='x' (pared lateral, varía z,y) o 'z' (fondo, varía x,y)."""
    g = 0.012
    a = a0
    while a <= a1 + 1e-6:
        if eje == "z":
            _q(P, (a, b0, fijo), (a + g, b0, fijo), (a + g, b1, fijo), (a, b1, fijo), color, normal, 1, None, True)
        else:
            _q(P, (fijo, b0, a), (fijo, b0, a + g), (fijo, b1, a + g), (fijo, b1, a), color, normal, 1, None, True)
        a += paso
    b = b0
    while b <= b1 + 1e-6:
        if eje == "z":
            _q(P, (a0, b, fijo), (a1, b, fijo), (a1, b + g, fijo), (a0, b + g, fijo), color, normal, 1, None, True)
        else:
            _q(P, (fijo, b, a0), (fijo, b, a1), (fijo, b + g, a1), (fijo, b + g, a0), color, normal, 1, None, True)
        b += paso


def _silueta_kira(P, cx, cy, z, esc, hot):
    """Silueta estilizada de Kira (emisiva) en el plano del fondo, sobre la pantalla central."""
    v = _VERDE_MATRIX
    def poly(pts, color=v, capa=3):
        P.append((tuple((cx + x * esc, cy + y * esc, z) for x, y in pts), color, (0, 0, -1), capa, hot, True))
    poly([(-0.18, 0.0), (0.18, 0.0), (0.26, 0.9), (-0.26, 0.9)])                     # torso/vestido (trapecio)
    poly([(-0.26, 0.9), (0.26, 0.9), (0.18, 1.02), (-0.18, 1.02)])                   # hombros
    poly([(-0.1, 1.02), (0.1, 1.02), (0.12, 1.2), (-0.12, 1.2)])                     # cuello
    n = 12                                                                           # cabeza (círculo)
    poly([(0.17 * math.cos(a / n * 6.2832), 1.42 + 0.17 * math.sin(a / n * 6.2832)) for a in range(n)])
    poly([(-0.22, 1.5), (0.22, 1.5), (0.2, 1.2), (-0.2, 1.2)])                       # pelo (aura sobre los hombros)


def construir_ciber(semilla=9):
    rnd = random.Random(semilla)
    P = []
    oscuro = (0.02, 0.05, 0.04)
    for i in range(16):                                                              # suelo oscuro con brillo tenue
        z0 = i * 0.5
        _q(P, (-ANCHO, 0, z0), (ANCHO, 0, z0), (ANCHO, 0, z0 + 0.5), (-ANCHO, 0, z0 + 0.5),
           (0.03, 0.07, 0.05) if i % 2 else (0.02, 0.05, 0.04), (0, 1, 0), 0)
    _q(P, (-ANCHO, 0, 0), (-ANCHO, 0, FONDO), (-ANCHO, ALTO, FONDO), (-ANCHO, ALTO, 0), oscuro, (1, 0, 0), 0)
    _q(P, (ANCHO, 0, FONDO), (ANCHO, 0, 0), (ANCHO, ALTO, 0), (ANCHO, ALTO, FONDO), oscuro, (-1, 0, 0), 0)
    _q(P, (-ANCHO, 0, FONDO), (ANCHO, 0, FONDO), (ANCHO, ALTO, FONDO), (-ANCHO, ALTO, FONDO), (0.01, 0.03, 0.02), (0, 0, -1), 0)
    _q(P, (ANCHO, 0, 0), (-ANCHO, 0, 0), (-ANCHO, ALTO, 0), (ANCHO, ALTO, 0), oscuro, (0, 0, 1), 0)
    _q(P, (-ANCHO, ALTO, 0), (ANCHO, ALTO, 0), (ANCHO, ALTO, FONDO), (-ANCHO, ALTO, FONDO), (0.01, 0.02, 0.02), (0, -1, 0), 0)
    # rejilla verde en las paredes (estética matrix)
    rej = (0.05, 0.3, 0.18)
    _rejilla_pared(P, "x", -ANCHO + 0.02, 1.0, 7.0, 0.3, 2.5, (1, 0, 0), rej)
    _rejilla_pared(P, "x", ANCHO - 0.02, 1.0, 7.0, 0.3, 2.5, (-1, 0, 0), rej)
    _rejilla_pared(P, "z", FONDO - 0.03, -2.6, 2.6, 0.3, 2.6, (0, 0, -1), rej)
    for z in (1.5, 4.0, 6.5):                                                        # tiras de luz del techo (verdes)
        _q(P, (-0.6, ALTO - 0.01, z), (0.6, ALTO - 0.01, z), (0.6, ALTO - 0.01, z + 0.4), (-0.6, ALTO - 0.01, z + 0.4),
           (0.1, 0.5, 0.3), (0, -1, 0), 2, None, True)

    # --- PANTALLA CENTRAL con la silueta de Kira (hotspot "centro") ---
    _caja(P, -1.9, 0.0, 7.6, 1.9, 0.5, 8.0, (0.04, 0.08, 0.06), 1, "centro")         # base
    _caja(P, -1.95, 0.55, 7.85, 1.95, 2.65, 8.0, (0.03, 0.05, 0.05), 1, "centro")    # marco
    _q(P, (-1.8, 0.7, 7.84), (1.8, 0.7, 7.84), (1.8, 2.55, 7.84), (-1.8, 2.55, 7.84),
       (0.02, 0.1, 0.06), (0, 0, -1), 2, "centro", True)                             # pantalla
    _silueta_kira(P, 0.0, 0.95, 7.83, 1.0, "centro")                                 # Kira
    for k in range(10):                                                              # "lluvia de código" a los lados
        x = rnd.choice((-1.6, -1.4, 1.4, 1.6))
        y = rnd.uniform(0.8, 2.4)
        _q(P, (x, y, 7.835), (x + 0.05, y, 7.835), (x + 0.05, y + 0.08, 7.835), (x, y + 0.08, 7.835),
           _VERDE_MATRIX, (0, 0, -1), 3, "centro", True)
    # mesa/consola delante de la pantalla
    _caja(P, -1.2, 0.74, 6.5, 1.2, 0.80, 7.3, (0.05, 0.09, 0.07), 1, "centro")
    for lx in (-1.15, 1.07):
        _caja(P, lx, 0.0, 6.55, lx + 0.08, 0.74, 6.63, (0.03, 0.06, 0.05), 1, "centro")
    _caja(P, -0.4, 0.80, 6.6, 0.4, 0.82, 6.9, (0.02, 0.05, 0.04), 2, "centro")       # teclado
    for k in range(3):
        _q(P, (-0.36, 0.822, 6.64 + k * 0.07), (0.36, 0.822, 6.64 + k * 0.07), (0.36, 0.822, 6.66 + k * 0.07),
           (-0.36, 0.822, 6.66 + k * 0.07), (0.1, 0.45, 0.25), (0, 1, 0), 3, "centro", True)

    # --- PANEL DEL DISPOSITIVO (pared izquierda, hotspot "dispositivo") ---
    _q(P, (-ANCHO + 0.02, 1.0, 3.2), (-ANCHO + 0.02, 1.0, 5.2), (-ANCHO + 0.02, 2.3, 5.2), (-ANCHO + 0.02, 2.3, 3.2),
       (0.03, 0.06, 0.05), (1, 0, 0), 1, "dispositivo")
    _q(P, (-ANCHO + 0.03, 1.1, 3.3), (-ANCHO + 0.03, 1.1, 5.1), (-ANCHO + 0.03, 2.2, 5.1), (-ANCHO + 0.03, 2.2, 3.3),
       (0.02, 0.12, 0.08), (1, 0, 0), 2, "dispositivo", True)                        # pantalla del panel
    for k in range(5):                                                               # barras tipo monitor de recursos
        y = 1.25 + k * 0.2
        largo = rnd.uniform(0.5, 1.6)
        _q(P, (-ANCHO + 0.04, y, 3.45), (-ANCHO + 0.04, y, 3.45 + largo), (-ANCHO + 0.04, y + 0.1, 3.45 + largo),
           (-ANCHO + 0.04, y + 0.1, 3.45), (0.12, 0.8, 0.45) if k % 2 else (0.2, 0.7, 0.9), (1, 0, 0), 3, "dispositivo", True)

    # --- torres de servidores con luces (decoración) ---
    for zt in (1.2, 1.9):
        _caja(P, ANCHO - 0.5, 0.0, zt, ANCHO - 0.1, 2.0, zt + 0.5, (0.04, 0.07, 0.06), 1)
        for f in range(6):
            _q(P, (ANCHO - 0.11, 0.3 + f * 0.25, zt + 0.1), (ANCHO - 0.11, 0.3 + f * 0.25, zt + 0.4),
               (ANCHO - 0.11, 0.34 + f * 0.25, zt + 0.4), (ANCHO - 0.11, 0.34 + f * 0.25, zt + 0.1),
               rnd.choice(((0.2, 0.9, 0.4), (0.9, 0.7, 0.2), (0.2, 0.6, 0.95))), (-1, 0, 0), 2, None, True)

    # --- puerta de regreso (pared derecha, hotspot "regreso") ---
    _caja(P, ANCHO - 0.12, 0.0, 3.35, ANCHO, 2.25, 4.85, (0.04, 0.08, 0.06), 1, "regreso")
    _q(P, (ANCHO - 0.13, 0.0, 3.5), (ANCHO - 0.13, 0.0, 4.7), (ANCHO - 0.13, 2.1, 4.7), (ANCHO - 0.13, 2.1, 3.5),
       (0.06, 0.14, 0.1), (-1, 0, 0), 2, "regreso")
    _q(P, (ANCHO - 0.14, 2.3, 3.6), (ANCHO - 0.14, 2.3, 4.6), (ANCHO - 0.14, 2.52, 4.6), (ANCHO - 0.14, 2.52, 3.6),
       (0.1, 0.9, 0.4), (-1, 0, 0), 3, "regreso", True)                              # cartel SALIR luminoso
    return P


def intencion_ciber(texto):
    import ciber_kira
    return ciber_kira.intencion_ciber(texto)


CFG_CIBER = {
    "entrada": POSE_X_ENTRADA, "mesa": POSE_X_MESA, "niebla": NIEBLA_CIBER, "anclas": ANCLAS_X, "nombres": NOMBRES_X,
    "poses": {"centro": POSE_X_CENTRO, "dispositivo": POSE_X_DISPOSITIVO, "regreso": POSE_X_REGRESO},
    "principal": "centro",
}


def recorrido_ciber():
    return hk.Recorrido(construir_ciber(), CFG_CIBER)
