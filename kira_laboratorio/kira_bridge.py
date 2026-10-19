# -*- coding: utf-8 -*-
"""
kira_bridge.py - Puente de archivos del laboratorio (PASO 2)

Cambios respecto a la versión anterior:
- Todas las rutas pasan por lab_rutas.ruta_segura(): no se puede escribir fuera de datos/.
- Solo extensiones permitidas y tamaño máximo.
- Escritura atómica y copia de seguridad automática (últimas 5 por archivo).
- Mismos métodos de siempre (guardar_archivo / leer_archivo) para no romper lo que ya los usa,
  más leer_texto() que devuelve None si falla (sin depender de buscar '[x]' en el contenido).
"""
import os
import shutil
import time

from lab_rutas import carpeta_datos, ruta_segura, RutaNoPermitida

EXT_PERMITIDAS = {".py", ".json", ".txt", ".md", ".csv"}
MAX_BYTES = 1_000_000
COPIAS_A_GUARDAR = 5


class KiraBridge:
    def __init__(self, base_dir=None):
        # base_dir se acepta por compatibilidad, pero SIEMPRE dentro de la carpeta de datos
        self.base = carpeta_datos()
        if base_dir:
            self.base = ruta_segura(base_dir, self.base)
            os.makedirs(self.base, exist_ok=True)
        self.dir_respaldos = os.path.join(self.base, ".respaldos")

    # ---------- utilidades ----------
    def _ruta(self, nombre):
        ruta = ruta_segura(nombre, self.base)
        if os.path.splitext(ruta)[1].lower() not in EXT_PERMITIDAS:
            raise RutaNoPermitida(
                "Extensión no permitida (solo " + ", ".join(sorted(EXT_PERMITIDAS)) + ").")
        return ruta

    def _respaldar(self, ruta, nombre):
        os.makedirs(self.dir_respaldos, exist_ok=True)
        plano = nombre.replace("\\", "/").strip("/").replace("/", "__")
        shutil.copy2(ruta, os.path.join(self.dir_respaldos, f"{plano}.{int(time.time() * 1000)}"))
        copias = sorted(f for f in os.listdir(self.dir_respaldos) if f.startswith(plano + "."))
        for vieja in copias[:-COPIAS_A_GUARDAR]:
            os.remove(os.path.join(self.dir_respaldos, vieja))

    # ---------- API nueva ----------
    def existe(self, nombre):
        try:
            return os.path.isfile(self._ruta(nombre))
        except RutaNoPermitida:
            return False

    def leer_texto(self, nombre):
        """Devuelve el contenido o None si no existe / no está permitido."""
        try:
            ruta = self._ruta(nombre)
            if not os.path.isfile(ruta):
                return None
            with open(ruta, "r", encoding="utf-8") as f:
                return f.read()
        except (RutaNoPermitida, OSError, UnicodeDecodeError):
            return None

    # ---------- API compatible con la versión anterior ----------
    def guardar_archivo(self, nombre: str, contenido: str) -> str:
        """Guarda un archivo dentro de datos/. Devuelve un mensaje que empieza por [OK] o [x]."""
        try:
            if not isinstance(contenido, str):
                return "[x] El contenido debe ser texto."
            if len(contenido.encode("utf-8")) > MAX_BYTES:
                return f"[x] '{nombre}' supera el máximo de {MAX_BYTES} bytes."
            ruta = self._ruta(nombre)
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            if os.path.isfile(ruta):
                self._respaldar(ruta, nombre)
            tmp = ruta + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(contenido)
            os.replace(tmp, ruta)  # escritura atómica
            return f"[OK] Archivo '{nombre}' guardado en el laboratorio."
        except RutaNoPermitida as e:
            return f"[x] Rechazado '{nombre}': {e}"
        except OSError as e:
            return f"[x] Error al guardar '{nombre}': {e}"

    def leer_archivo(self, nombre: str) -> str:
        """Compatibilidad: devuelve el contenido o un mensaje que empieza por [x]."""
        try:
            ruta = self._ruta(nombre)
        except RutaNoPermitida as e:
            return f"[x] Rechazado '{nombre}': {e}"
        texto = self.leer_texto(nombre)
        if texto is None:
            return f"[x] Archivo '{nombre}' no encontrado en el laboratorio."
        return texto
