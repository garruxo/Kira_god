# -*- coding: utf-8 -*-
"""
api_modulos_kira.py - Lo que puede usar un MÓDULO DE MEJORA a través del objeto 'kira' (función (texto, kira)).

Además de audio, vídeo y archivos de trabajo (herramientas_kira), cada módulo tiene, con límites:
  kira.guardar_dato(clave, valor) / kira.leer_dato(clave, defecto=None) / kira.borrar_dato(clave) / kira.datos()
        -> sus PROPIOS datos (JSON), separados de los de los demás módulos y de los de Kira (máx. 256 KB).
  kira.recordar(texto) / kira.buscar_recuerdos(consulta, n=3)
        -> el baúl de recuerdos de Kira (lo que guarda queda marcado como «módulo <nombre>»).
  kira.avisar_en(segundos, texto) / kira.decir(texto)
        -> Kira lo dirá en voz alta (y en pantalla) cuando toque. Hasta 20 avisos pendientes por módulo.
  kira.ahora() -> «2026-10-19 22:51».
Y para JUEGOS: registrar() puede devolver {"juego <nombre>": crear} donde crear(motor) devuelve una clase que hereda
de motor.Juego (motor = motor_juegos_kira). Aparece en la pantalla de Juegos.
Nada de esto da acceso a claves, a los archivos de Kira, a la red ni al sistema.
"""
import datetime
import json
import os
import re
import threading
import time

MAX_DATOS = 256 * 1024
MAX_AVISOS_MODULO = 20
MAX_SEGUNDOS = 7 * 24 * 3600
_CLAVE = re.compile(r"^[\w .:-]{1,80}$")
PERMITIDAS = ("medios", "importar", "ffmpeg", "escribir", "leer", "exportar", "listar", "existe", "borrar")


class ApiError(RuntimeError):
    pass


class Avisos:
    """Avisos pendientes de todos los módulos (en memoria). La interfaz los recoge con vencidos()."""

    def __init__(self, reloj=time.time):
        self._reloj = reloj
        self._lock = threading.Lock()
        self._pend = []                    # [(instante, modulo, texto)]

    def programar(self, modulo, segundos, texto):
        try:
            segundos = float(segundos)
        except (TypeError, ValueError):
            raise ApiError("avisar_en: los segundos deben ser un número")
        if not 0 <= segundos <= MAX_SEGUNDOS:
            raise ApiError("avisar_en: entre 0 segundos y 7 días")
        texto = re.sub(r"\s+", " ", str(texto or "")).strip()[:300]
        if not texto:
            raise ApiError("avisar_en: falta el texto")
        with self._lock:
            if sum(1 for _, m, _ in self._pend if m == modulo) >= MAX_AVISOS_MODULO:
                raise ApiError(f"avisar_en: máximo {MAX_AVISOS_MODULO} avisos pendientes por módulo")
            self._pend.append((self._reloj() + segundos, modulo, texto))
            self._pend.sort()
        return len(self._pend)

    def vencidos(self):
        ahora = self._reloj()
        with self._lock:
            listos = [(m, t) for i, m, t in self._pend if i <= ahora]
            self._pend = [x for x in self._pend if x[0] > ahora]
        return listos

    def pendientes(self):
        with self._lock:
            return [(round(i - self._reloj()), m, t) for i, m, t in self._pend]


class ApiModulo:
    def __init__(self, nombre, herramientas=None, dir_datos=".", recuerdos=None, avisos=None):
        self.nombre = str(nombre)
        self._herr = herramientas
        self._ruta = os.path.join(dir_datos, "datos_modulos", re.sub(r"[^a-z0-9_]", "_", self.nombre.lower()) + ".json")
        self._recuerdos = recuerdos
        self._avisos = avisos
        self._lock = threading.Lock()

    # ---- herramientas de audio/vídeo/archivos de trabajo (las de siempre) ----
    def __getattr__(self, n):
        if n in PERMITIDAS and self._herr is not None:
            return getattr(self._herr, n)
        raise AttributeError(f"'kira' no tiene «{n}». Mira la lista en api_modulos_kira.py")

    # ---- datos propios ----
    def _leer(self):
        try:
            with open(self._ruta, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def guardar_dato(self, clave, valor):
        clave = str(clave)
        if not _CLAVE.match(clave):
            raise ApiError("guardar_dato: la clave debe ser un texto corto (letras, números, espacios, . : - _)")
        with self._lock:
            d = self._leer()
            d[clave] = valor
            try:
                texto = json.dumps(d, ensure_ascii=False)
            except (TypeError, ValueError):
                raise ApiError("guardar_dato: solo textos, números, listas y diccionarios (JSON)")
            if len(texto.encode("utf-8")) > MAX_DATOS:
                raise ApiError("guardar_dato: los datos del módulo superan 256 KB")
            os.makedirs(os.path.dirname(self._ruta), exist_ok=True)
            tmp = self._ruta + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(texto)
            os.replace(tmp, self._ruta)
        return True

    def leer_dato(self, clave, defecto=None):
        return self._leer().get(str(clave), defecto)

    def borrar_dato(self, clave):
        with self._lock:
            d = self._leer()
            if str(clave) not in d:
                return False
            del d[str(clave)]
            with open(self._ruta, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
            return True

    def datos(self):
        return dict(self._leer())

    # ---- recuerdos ----
    def recordar(self, texto):
        if self._recuerdos is None:
            raise ApiError("recordar: el baúl de recuerdos no está disponible")
        return self._recuerdos.guardar(str(texto)[:2000], fuente=f"módulo {self.nombre}")

    def buscar_recuerdos(self, consulta, n=3):
        if self._recuerdos is None:
            return []
        return [r["texto"] for r in self._recuerdos.buscar(str(consulta), n=max(1, min(int(n), 10)), excluir_web=False)]

    # ---- avisos ----
    def avisar_en(self, segundos, texto):
        if self._avisos is None:
            raise ApiError("avisar_en: no disponible aquí")
        self._avisos.programar(self.nombre, segundos, texto)
        return True

    def decir(self, texto):
        return self.avisar_en(0, texto)

    @staticmethod
    def ahora():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
