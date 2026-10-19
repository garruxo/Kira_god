# -*- coding: utf-8 -*-
"""
KiraOS - Studio & Room Core (studio_core.py)  (PASO 8)
Gestiona la lógica del estudio en 3 zonas (Archivador, Escritorio Audiovisual y Taller).

IMPORTANTE (sinceridad): este módulo guarda ESTADO (qué zona está activa y los valores de los filtros).
Nada de aquí dibuja ni procesa imágenes todavía: los filtros son números que una interfaz podrá leer.

Cambios respecto a la versión anterior:
- taller_automejora() ya NO dice "aplicada al núcleo con éxito": nunca aplicó nada (solo escribía un
  archivo de texto). Ahora entrega el código al KiraEvolver como PROPUESTA, la prueba en el laboratorio
  y cuenta la verdad: pasó o no pasó, y que la decisión de aplicar es tuya.
- Los filtros aceptan enteros o texto, admiten 0 (antes se rechazaba por ser "falso") y tienen rango:
  brightness/contrast 0..200, hue-rotate -360..360 (antes aceptaba cualquier número).
- La biblioteca del Archivador muestra los archivos REALES de datos/ (antes era una lista fija inventada
  que incluía kira.lock).
- Log propio en datos/ con rotación (antes: basicConfig global en el directorio actual, que podía fallar
  en Android y pisaba la configuración de logging de otros módulos).
- Seguro entre hilos. Mismos métodos y atributos de siempre.
"""
import logging
import logging.handlers
import os
import threading

from lab_rutas import carpeta_datos

ZONAS = ("archivador", "escritorio", "taller")
RANGOS_FILTROS = {"brightness": (0, 200), "contrast": (0, 200), "hue-rotate": (-360, 360)}
FILTROS_INICIALES = {"brightness": 100, "contrast": 100, "hue-rotate": 0}
MAX_ARCHIVOS_LISTADOS = 50

logger = logging.getLogger("KiraRoomCore")
logger.propagate = False  # no duplicar líneas en el logger raíz


def _configurar_log():
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    try:
        h = logging.handlers.RotatingFileHandler(
            os.path.join(carpeta_datos(), "kira_studio_room.log"),
            maxBytes=200_000, backupCount=2, encoding="utf-8")
        h.setFormatter(logging.Formatter('%(asctime)s - [KIRA-ROOM] - %(levelname)s - %(message)s'))
        logger.addHandler(h)
    except Exception:
        logger.addHandler(logging.NullHandler())  # sin log, pero la habitación funciona


def _a_entero(valor):
    """Acepta int, texto con un entero ('150', ' -90 ') o float entero (150.0). Rechaza el resto."""
    if isinstance(valor, bool):
        raise ValueError
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    if isinstance(valor, str):
        return int(valor.strip())
    raise ValueError


class KiraStudioRoom:
    def __init__(self):
        _configurar_log()
        print("[ESTUDIO 3D] Inicializando habitación de Kira (Archivador, Escritorio y Taller)...")
        logger.info("Habitación de estudio iniciada.")
        self._lock = threading.Lock()
        self._evolver = None
        self.zona_actual = "escritorio"  # archivador, escritorio, taller
        self.filtros_activos = dict(FILTROS_INICIALES)

    # ---------- Archivador ----------
    @property
    def biblioteca_archivos(self):
        """Archivos reales de datos/ (rutas relativas, sin ocultos ni enlaces simbólicos)."""
        base = carpeta_datos()
        lista = []
        for raiz, carpetas, archivos in os.walk(base, followlinks=False):
            carpetas[:] = [d for d in carpetas if not d.startswith(".")
                           and not os.path.islink(os.path.join(raiz, d))]
            for nombre in archivos:
                ruta = os.path.join(raiz, nombre)
                if not nombre.startswith(".") and not os.path.islink(ruta):
                    lista.append(os.path.relpath(ruta, base).replace(os.sep, "/"))
        return sorted(lista)[:MAX_ARCHIVOS_LISTADOS]

    # ---------- Escritorio y zonas ----------
    def estado(self) -> dict:
        with self._lock:
            return {"zona": self.zona_actual, "filtros": dict(self.filtros_activos)}

    def cambiar_zona(self, zona: str) -> str:
        """Mueve el enfoque entre las zonas de la habitación."""
        if not isinstance(zona, str) or not zona.strip():
            return "[x] Zona no especificada."
        z = zona.lower().strip()
        if z in ZONAS:
            with self._lock:
                self.zona_actual = z
            msg = f"Desplazado a la zona: {z.upper()}"
            logger.info(msg)
            return f"[OK] {msg}"
        return "[x] Zona desconocida. Opciones válidas: archivador, escritorio, taller."

    def ajustar_regulador_remoto(self, filtro: str, valor) -> str:
        """Ajusta el valor guardado de un filtro audiovisual (acepta número o texto numérico)."""
        if not isinstance(filtro, str) or not filtro.strip() or valor is None \
                or (isinstance(valor, str) and not valor.strip()):
            return "[x] Parámetros de filtro o valor incompletos."
        f = filtro.lower().strip()
        if f not in RANGOS_FILTROS:
            return "[x] Filtro '" + f[:30] + "' no reconocido. Opciones: brightness, contrast, hue-rotate."
        try:
            val = _a_entero(valor)
        except (ValueError, TypeError):
            return f"[x] El valor '{str(valor)[:30]}' debe ser un número entero."
        minimo, maximo = RANGOS_FILTROS[f]
        if not minimo <= val <= maximo:
            return f"[x] El valor {val} está fuera de rango para '{f}' ({minimo} a {maximo})."
        with self._lock:
            self.filtros_activos[f] = val
        msg = f"Filtro '{f}' ajustado a {val} en el escritorio."
        logger.info(msg)
        return f"[OK] {msg}"

    # ---------- Taller ----------
    def _get_evolver(self):
        if self._evolver is None:
            from kira_evolver import KiraEvolver  # import tardío: el estudio funciona aunque falte el resto
            self._evolver = KiraEvolver()
        return self._evolver

    def taller_automejora(self, codigo_nuevo: str, nombre: str = "autoupgrade") -> str:
        """Entrega código al evolver como PROPUESTA y lo prueba en el laboratorio. NO aplica nada."""
        print("[TALLER] Kira analizando código para automejora...")
        try:
            evolver = self._get_evolver()
            res = evolver.proponer_mejora(nombre, codigo_nuevo, pedido="taller_automejora")
            texto = evolver.resumen(res)
            logger.info(f"Taller: propuesta '{nombre}' aprobable={res.get('aprobable')}")
            return texto
        except Exception as e:
            error_msg = f"Error en automejora: {e}"
            logger.error(error_msg)
            return f"[x] {error_msg}"


if __name__ == "__main__":
    room = KiraStudioRoom()
    print("[OK] Studio Room Core listo en el laboratorio.")
