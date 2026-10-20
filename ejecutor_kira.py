# -*- coding: utf-8 -*-
"""
ejecutor_kira.py - Ejecuta TUS programas de Python dentro de Kira en «modo seguro» (lógica pura, sin Kivy).

Qué hace el modo seguro:
  - Antes de ejecutar, revisa el código (ast): sin archivos (open), sin red, sin el sistema (os, subprocess, socket…),
    sin eval/exec, y sin trucos con atributos internos (__subclasses__, __globals__…).
  - Solo deja importar módulos de una LISTA SEGURA (matemáticas, colecciones, fechas, regex, json, hilos, asyncio,
    sqlite en memoria, unittest…) y el motor de juegos de Kira.
  - Corta el programa si tarda más del límite (bucles infinitos) y recorta una salida enorme.
  - Lo que imprime con print() se recoge y se enseña en pantalla; input() lee de la caja de «entrada».
Honesto: es una protección contra ERRORES y accidentes, no una caja fuerte contra alguien que quiera saltársela a
propósito. No pegues ni ejecutes código de desconocidos.

Programas guardados: <datos>/programas/<nombre>.py (Programas).
"""
import ast
import builtins
import io
import json
import os
import re
import sys
import threading
import time
import traceback

LIMITE_SEGUNDOS = 5.0
MAX_SALIDA = 20_000
MAX_CODIGO = 200_000
MAX_PROGRAMAS = 300

MODULOS_PERMITIDOS = {
    "math", "cmath", "random", "statistics", "datetime", "time", "calendar", "collections", "itertools", "functools",
    "operator", "string", "textwrap", "re", "json", "dataclasses", "enum", "typing", "abc", "copy", "heapq", "bisect",
    "array", "decimal", "fractions", "numbers", "unicodedata", "difflib", "pprint", "threading", "queue", "asyncio",
    "contextlib", "sqlite3", "unittest", "uuid", "secrets", "hashlib", "hmac", "base64", "binascii", "struct",
    "zlib", "colorsys", "graphlib", "weakref", "types", "inspect", "dis", "keyword", "token", "tokenize",
    "motor_juegos_kira",
}
LLAMADAS_PROHIBIDAS = {"open", "eval", "exec", "compile", "__import__", "breakpoint", "globals", "vars",
                       "memoryview", "help", "exit", "quit", "getattr", "setattr", "delattr"}
ATRIBUTOS_PROHIBIDOS = {"__subclasses__", "__globals__", "__builtins__", "__code__", "__closure__", "__bases__",
                        "__mro__", "__dict__", "__getattribute__", "__import__", "__loader__", "__spec__",
                        "__reduce__", "__reduce_ex__", "gi_frame", "gi_code", "f_globals", "f_locals", "f_back",
                        "f_builtins", "tb_frame", "cr_frame", "ag_frame", "co_code", "settrace", "setprofile",
                        "system", "popen", "remove", "unlink", "rmtree"}


class TiempoAgotado(Exception):
    pass


def revisar(codigo):
    """None si el código pasa la revisión del modo seguro; si no, un texto con el motivo y la línea."""
    if not codigo or not codigo.strip():
        return "No hay código."
    if len(codigo) > MAX_CODIGO:
        return "El programa es demasiado largo."
    try:
        arbol = ast.parse(codigo)
    except SyntaxError as e:
        return f"Error de sintaxis en la línea {e.lineno}: {e.msg}"
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] not in MODULOS_PERMITIDOS:
                    return f"Línea {n.lineno}: el modo seguro no permite importar «{a.name}»."
        elif isinstance(n, ast.ImportFrom):
            if not n.module or n.level or n.module.split(".")[0] not in MODULOS_PERMITIDOS:
                return f"Línea {n.lineno}: el modo seguro no permite importar «{n.module or '.'}»."
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in LLAMADAS_PROHIBIDAS:
            return f"Línea {n.lineno}: el modo seguro no permite usar {n.func.id}()."
        elif isinstance(n, ast.Name) and n.id in ("__builtins__", "__import__", "__loader__", "__spec__"):
            return f"Línea {n.lineno}: el modo seguro no permite usar {n.id}."
        elif isinstance(n, ast.Attribute) and n.attr in ATRIBUTOS_PROHIBIDOS:
            return f"Línea {n.lineno}: el modo seguro no permite usar «.{n.attr}»."
    return None


def _importador(entorno_import):
    def importar(nombre, globales=None, locales=None, desde=(), nivel=0):
        if nivel or nombre.split(".")[0] not in MODULOS_PERMITIDOS:
            raise ImportError(f"el modo seguro no permite importar «{nombre}»")
        return entorno_import(nombre, globales, locales, desde, nivel)
    return importar


def ejecutar(codigo, entrada="", limite=LIMITE_SEGUNDOS, extra=None):
    """Ejecuta el programa. Devuelve {'ok', 'salida', 'error', 'segundos', 'globales'}.
    entrada: texto cuyas líneas leerá input(). extra: nombres que se le dan ya hechos al programa."""
    motivo = revisar(codigo)
    if motivo:
        return {"ok": False, "salida": "", "error": motivo, "segundos": 0.0, "globales": {}}
    salida = io.StringIO()
    lineas = iter(str(entrada or "").splitlines())
    recortado = {"si": False}

    def imprimir(*args, sep=" ", end="\n", **_):
        texto = sep.join(str(a) for a in args) + end
        if salida.tell() + len(texto) > MAX_SALIDA:
            recortado["si"] = True
            texto = texto[: max(0, MAX_SALIDA - salida.tell())]
        salida.write(texto)

    def leer(mensaje=""):
        imprimir(mensaje, end="")
        try:
            valor = next(lineas)
        except StopIteration:
            raise EOFError("input(): no hay más líneas en la caja de entrada")
        imprimir(valor)
        return valor

    seguros = {k: v for k, v in vars(builtins).items() if k not in LLAMADAS_PROHIBIDAS}
    seguros.update(print=imprimir, input=leer, __import__=_importador(builtins.__import__))
    globales = {"__builtins__": seguros, "__name__": "__main__"}
    if extra:
        globales.update(extra)

    fin = time.monotonic() + float(limite)
    hilo = threading.get_ident()
    activo = {"si": True}

    def rastreo(frame, evento, arg):
        # se vigila el hilo del programa y el código del programa (también en hilos que abra él); los demás hilos de
        # Kira que arranquen mientras tanto no se tocan y se sueltan al acabar (antes podían cortarse por error)
        propio = frame.f_code.co_filename == "<tu programa>"
        if not propio and (not activo["si"] or threading.get_ident() != hilo):
            if not activo["si"]:
                sys.settrace(None)
            return None
        if time.monotonic() > fin:
            raise TiempoAgotado()
        return rastreo

    inicio = time.monotonic()
    viejo, viejo_hilos = sys.gettrace(), threading.gettrace() if hasattr(threading, "gettrace") else None
    viejo_gancho = threading.excepthook

    def gancho_hilos(info):                           # un hilo cortado por tiempo no ensucia la consola
        if not issubclass(info.exc_type, TiempoAgotado):
            imprimir(f"[hilo] {info.exc_type.__name__}: {info.exc_value}")
    error = ""
    try:
        threading.excepthook = gancho_hilos
        sys.settrace(rastreo)
        threading.settrace(rastreo)
        exec(compile(codigo, "<tu programa>", "exec"), globales)
    except TiempoAgotado:
        error = f"Se cortó: tardaba más de {limite:g} s (¿un bucle infinito?)."
    except SystemExit:
        error = ""
    except BaseException as e:                         # el error de TU programa, con su línea
        tb = traceback.extract_tb(e.__traceback__)
        linea = next((f.lineno for f in reversed(tb) if f.filename == "<tu programa>"), None)
        error = f"{type(e).__name__}: {e}" + (f" (línea {linea})" if linea else "")
    finally:
        activo["si"] = False
        sys.settrace(viejo)
        threading.settrace(viejo_hilos)
        threading.excepthook = viejo_gancho
    texto = salida.getvalue()
    if recortado["si"]:
        texto += "\n… (salida recortada)"
    return {"ok": not error, "salida": texto, "error": error, "segundos": round(time.monotonic() - inicio, 3),
            "globales": globales}


def con_limite(funcion, limite, *args, **kw):
    """Llama a funcion(*args) cortándola si tarda más de 'limite' segundos (para cada fotograma de un juego).
    Devuelve su resultado o lanza TiempoAgotado."""
    fin = time.monotonic() + float(limite)

    def rastreo(frame, evento, arg):
        if time.monotonic() > fin:
            raise TiempoAgotado()
        return rastreo
    viejo = sys.gettrace()
    sys.settrace(rastreo)
    try:
        return funcion(*args, **kw)
    finally:
        sys.settrace(viejo)


# =====================================================================================
#  PROGRAMAS GUARDADOS
# =====================================================================================
_NOMBRE = re.compile(r"[^a-z0-9_]+")


def nombre_valido(nombre):
    n = _NOMBRE.sub("_", str(nombre or "").strip().lower()).strip("_")[:40]
    return n or None


class Programas:
    def __init__(self, carpeta):
        self.carpeta = carpeta
        os.makedirs(carpeta, exist_ok=True)

    def listar(self):
        try:
            nombres = [f[:-3] for f in os.listdir(self.carpeta) if f.endswith(".py")]
        except OSError:
            return []
        return sorted(nombres, key=lambda n: -os.path.getmtime(os.path.join(self.carpeta, n + ".py")))

    def guardar(self, nombre, codigo):
        n = nombre_valido(nombre)
        if not n:
            raise ValueError("Ponle un nombre al programa (letras, números y _).")
        if len(codigo) > MAX_CODIGO:
            raise ValueError("El programa es demasiado largo.")
        ruta = os.path.join(self.carpeta, n + ".py")
        if not os.path.exists(ruta) and len(self.listar()) >= MAX_PROGRAMAS:
            raise ValueError(f"Ya tienes {MAX_PROGRAMAS} programas: borra alguno.")
        tmp = ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(codigo)
        os.replace(tmp, ruta)
        return n

    def abrir(self, nombre):
        n = nombre_valido(nombre)
        if not n:
            return None
        try:
            with open(os.path.join(self.carpeta, n + ".py"), encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    def borrar(self, nombre):
        n = nombre_valido(nombre)
        ruta = os.path.join(self.carpeta, (n or "_") + ".py")
        if n and os.path.isfile(ruta):
            os.remove(ruta)
            return True
        return False
