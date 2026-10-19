# -*- coding: utf-8 -*-
"""
kira_optimizer.py - Mantenimiento y limpieza del laboratorio (PASO 5)

Qué cambia respecto a la versión anterior (que borraba TODO .log y TODO test_* sin mirar la edad):
- Solo actúa dentro de datos/ y nunca sale de ahí (comprueba cada ruta; no sigue enlaces simbólicos).
- Reglas con EDAD mínima: logs > 7 días, test_* > 1 día, .tmp > 1 hora, memoria corrupta apartada > 30 días.
- NUNCA toca: carpetas ocultas (.respaldos = copias de seguridad), carpetas llamadas tests_fijos,
  archivos ocultos, ni enlaces simbólicos.
- Se puede PREVISUALIZAR sin borrar (previsualizar_purga / simular=True).
- Válvula de seguridad: si la purga borraría más de 200 archivos, se niega y pide revisión manual.
- Todo lo borrado queda anotado en la memoria del laboratorio.
Mismos métodos de siempre: purgar_logs_temporales() y compactar_memoria_historica().
"""
import os
import time

from lab_rutas import carpeta_datos, ruta_segura
from labor_memory import KiraMemory

HORA = 3600
DIA = 24 * HORA
MAX_BORRADOS = 200
CARPETAS_PROTEGIDAS = {"tests_fijos"}

# (motivo, función sobre el nombre, edad mínima en segundos). La edad de los logs es configurable.
def _reglas(dias_log):
    return [
        ("log antiguo", lambda n: n.endswith(".log"), dias_log * DIA),
        ("temporal de prueba", lambda n: n.startswith("test_"), 1 * DIA),
        ("escritura interrumpida", lambda n: n.endswith(".tmp"), 1 * HORA),
        ("memoria corrupta apartada", lambda n: ".corrupto-" in n, 30 * DIA),
    ]


def _dentro(base, ruta):
    try:
        real = os.path.realpath(ruta)
        return os.path.commonpath([base, real]) == base and real != base
    except ValueError:
        return False


class KiraOptimizer:
    def __init__(self, base_dir=None):
        self.base = carpeta_datos()
        if base_dir:
            self.base = ruta_segura(base_dir, self.base)
            os.makedirs(self.base, exist_ok=True)
        self.memory = KiraMemory()

    # ---------- plan de purga ----------
    def previsualizar_purga(self, dias_log=7, ahora=None):
        """Devuelve [(ruta_relativa, motivo, bytes)] de lo que se borraría. No borra nada."""
        ahora = time.time() if ahora is None else ahora
        reglas = _reglas(dias_log)
        plan = []
        for raiz, carpetas, archivos in os.walk(self.base, followlinks=False):
            carpetas[:] = [d for d in carpetas
                           if not d.startswith(".") and d not in CARPETAS_PROTEGIDAS
                           and not os.path.islink(os.path.join(raiz, d))]
            for nombre in archivos:
                if nombre.startswith("."):
                    continue
                ruta = os.path.join(raiz, nombre)
                if os.path.islink(ruta) or not _dentro(self.base, ruta):
                    continue
                try:
                    st = os.stat(ruta)
                except OSError:
                    continue
                for motivo, coincide, edad_min in reglas:
                    if coincide(nombre) and (ahora - st.st_mtime) >= edad_min:
                        plan.append((os.path.relpath(ruta, self.base), motivo, st.st_size))
                        break
        return sorted(plan)

    def purgar_logs_temporales(self, dias_log=7, ahora=None, simular=False) -> str:
        """Borra logs y temporales ANTIGUOS de datos/. Compatible con la versión anterior (devuelve texto)."""
        plan = self.previsualizar_purga(dias_log, ahora)
        total = sum(b for _, _, b in plan)
        if simular:
            nombres = ", ".join(p for p, _, _ in plan[:10]) or "(nada)"
            return f"[i] Simulación: se borrarían {len(plan)} archivos ({total} bytes): {nombres}"
        if len(plan) > MAX_BORRADOS:
            msg = (f"Se borrarían {len(plan)} archivos (máximo seguro: {MAX_BORRADOS}). "
                   "No se borró nada: revisa datos/ a mano.")
            self.memory.registrar_evento("mantenimiento_rechazado", msg)
            return f"[x] {msg}"
        borrados, liberados, fallos = [], 0, 0
        for rel, _motivo, tam in plan:
            ruta = os.path.join(self.base, rel)
            if os.path.islink(ruta) or not _dentro(self.base, ruta):
                continue
            try:
                os.remove(ruta)
                borrados.append(rel)
                liberados += tam
            except FileNotFoundError:
                pass  # ya no estaba
            except OSError:
                fallos += 1
        msg = f"Se han purgado {len(borrados)} archivos temporales/logs antiguos ({liberados} bytes)."
        if fallos:
            msg += f" {fallos} no se pudieron borrar."
        detalle = "; ".join(borrados[:20]) + ("…" if len(borrados) > 20 else "")
        self.memory.registrar_evento("mantenimiento", msg + (f" Borrados: {detalle}" if borrados else ""))
        return f"[OK] {msg}"

    # ---------- memoria ----------
    def compactar_memoria_historica(self, max_eventos=50) -> str:
        """Deja solo los últimos eventos del historial. Nunca toca las lecciones."""
        max_eventos = max(10, int(max_eventos))
        with self.memory._lock:
            hist = self.memory.datos.get("historial", [])
            if len(hist) <= max_eventos:
                return "[i] La memoria se encuentra optimizada y no requiere compactación."
            quitados = len(hist) - max_eventos
            self.memory.datos["historial"] = hist[-max_eventos:]
            self.memory.guardar_memoria()
        self.memory.registrar_evento("mantenimiento", f"Historial compactado: {quitados} eventos antiguos eliminados.")
        return f"[OK] Memoria compactada a los últimos {max_eventos} eventos."

    # ---------- informe ----------
    def informe(self) -> dict:
        """Uso de espacio de datos/: total, número de archivos y los más grandes."""
        archivos = []
        for raiz, carpetas, nombres in os.walk(self.base, followlinks=False):
            for n in nombres:
                ruta = os.path.join(raiz, n)
                if os.path.islink(ruta):
                    continue
                try:
                    archivos.append((os.path.relpath(ruta, self.base), os.path.getsize(ruta)))
                except OSError:
                    pass
        archivos.sort(key=lambda x: -x[1])
        return {"archivos": len(archivos), "bytes_total": sum(b for _, b in archivos),
                "mayores": archivos[:5]}


if __name__ == "__main__":
    opt = KiraOptimizer()
    print(opt.purgar_logs_temporales(simular=True))
    print(opt.compactar_memoria_historica())
