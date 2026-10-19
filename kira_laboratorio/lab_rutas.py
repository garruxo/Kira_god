# -*- coding: utf-8 -*-
"""
lab_rutas.py - Rutas únicas del laboratorio y validación (PASO 1)

Todo el laboratorio escribe SOLO dentro de DATOS. Ningún módulo debe construir
rutas por su cuenta: usa ruta_segura(). Así un nombre como '../../x.py', una ruta
absoluta o un enlace simbólico no pueden sacar un archivo de la zona de trabajo.

Carpetas:
  RAIZ   = carpeta de este archivo (servidor_lab.py y tests_fijos/ viven aquí, FUERA de DATOS)
  DATOS  = RAIZ/datos  (o la variable de entorno KIRA_LAB_DATA)
"""
import os
import re

RAIZ = os.path.dirname(os.path.abspath(__file__))


class RutaNoPermitida(ValueError):
    """El nombre o la ruta pedida intenta salir de la zona de trabajo."""


def carpeta_datos():
    d = os.environ.get("KIRA_LAB_DATA") or os.path.join(RAIZ, "datos")
    os.makedirs(d, exist_ok=True)
    return os.path.realpath(d)


def ruta_segura(nombre, base=None):
    """Devuelve la ruta absoluta de 'nombre' dentro de 'base' (por defecto DATOS), o lanza RutaNoPermitida."""
    if not isinstance(nombre, str) or not nombre.strip():
        raise RutaNoPermitida("Nombre vacío o no válido.")
    if "\x00" in nombre:
        raise RutaNoPermitida("El nombre contiene caracteres nulos.")

    n = nombre.strip().replace("\\", "/")
    if n.startswith("/") or re.match(r"^[A-Za-z]:", n):
        raise RutaNoPermitida("No se permiten rutas absolutas.")

    partes = [p for p in n.split("/") if p not in ("", ".")]
    if not partes:
        raise RutaNoPermitida("Nombre vacío.")
    if any(p == ".." for p in partes):
        raise RutaNoPermitida("No se permite '..' en las rutas.")
    if any(p.startswith(".") for p in partes):
        raise RutaNoPermitida("No se permiten nombres ocultos (empiezan por '.').")

    raiz = os.path.realpath(base) if base else carpeta_datos()
    destino = os.path.realpath(os.path.join(raiz, *partes))  # resuelve enlaces simbólicos
    try:
        dentro = os.path.commonpath([raiz, destino]) == raiz and destino != raiz
    except ValueError:  # p. ej. otra unidad en Windows
        dentro = False
    if not dentro:
        raise RutaNoPermitida("La ruta sale de la zona de trabajo.")
    return destino
