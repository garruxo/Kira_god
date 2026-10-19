# -*- coding: utf-8 -*-
"""
kira_registry.py - Índice del laboratorio y sellos de integridad (PASO 7)

1) INVENTARIO de datos/ (escanear_laboratorio): catálogo de scripts, configuraciones y logs.
   - Mismo método y mismas claves de siempre (scripts_py, configs, logs) + propuestas y huellas.
   - Ahora son rutas relativas (antes solo el nombre, que se repetía entre subcarpetas).
   - El manifiesto se escribe con KiraBridge (dentro de datos/, atómico, con copias de seguridad).
   - No sigue enlaces simbólicos ni mira carpetas ocultas (.respaldos).

2) SELLOS DE INTEGRIDAD (sellar_nucleo / verificar_integridad):
   Guarda la huella sha256 del código del laboratorio (*.py de la raíz y tests_fijos/*.py) en
   sellos.json, FUERA de datos/. Más tarde, verificar_integridad() avisa de archivos modificados,
   nuevos o desaparecidos: así se detecta si alguien tocó servidor_lab.py o los tests fijos.
   Sellar exige la frase "SELLAR NUCLEO" para que no se haga por accidente.
   Los sellos DETECTAN cambios; no los impiden. Quien pueda escribir en la carpeta del laboratorio
   también podría rehacer los sellos: por eso la decisión de sellar es tuya.
"""
import datetime
import hashlib
import json
import os

from kira_bridge import KiraBridge
from labor_memory import KiraMemory
from lab_rutas import RAIZ, carpeta_datos, ruta_segura

FRASE_SELLAR = "SELLAR NUCLEO"
MANIFIESTO = "kira_manifest.json"
MAX_HASH_BYTES = 5_000_000


def _huella(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        restante = MAX_HASH_BYTES
        while restante > 0:
            bloque = f.read(min(65536, restante))
            if not bloque:
                break
            h.update(bloque)
            restante -= len(bloque)
    return h.hexdigest()


class KiraRegistry:
    def __init__(self, base_dir=None, raiz=None):
        self.base = carpeta_datos()
        if base_dir:
            self.base = ruta_segura(base_dir, self.base)
            os.makedirs(self.base, exist_ok=True)
        self.raiz = os.path.realpath(raiz or RAIZ)
        self.ruta_sellos = os.path.join(self.raiz, "sellos.json")
        self.bridge = KiraBridge()
        self.memory = KiraMemory()
        print("[REGISTRY] Índice de recursos del laboratorio inicializado.")

    # ---------- inventario ----------
    def escanear_laboratorio(self) -> dict:
        recursos = {"scripts_py": [], "configs": [], "logs": [], "propuestas": [], "huellas": {}}
        for raiz, carpetas, archivos in os.walk(self.base, followlinks=False):
            carpetas[:] = [d for d in carpetas if not d.startswith(".")
                           and not os.path.islink(os.path.join(raiz, d))]
            for nombre in archivos:
                ruta = os.path.join(raiz, nombre)
                if nombre.startswith(".") or os.path.islink(ruta) or nombre == MANIFIESTO:
                    continue
                rel = os.path.relpath(ruta, self.base).replace(os.sep, "/")
                if nombre.endswith(".py"):
                    recursos["scripts_py"].append(rel)
                    if rel.startswith("propuestas/"):
                        recursos["propuestas"].append(rel)
                    try:
                        recursos["huellas"][rel] = _huella(ruta)[:16]
                    except OSError:
                        pass
                elif nombre.endswith((".json", ".spec")):
                    recursos["configs"].append(rel)
                elif nombre.endswith(".log"):
                    recursos["logs"].append(rel)
        for clave in ("scripts_py", "configs", "logs", "propuestas"):
            recursos[clave].sort()

        self.bridge.guardar_archivo(MANIFIESTO, json.dumps(recursos, indent=2, ensure_ascii=False))
        self.memory.registrar_evento(
            "registro", f"Laboratorio escaneado: {len(recursos['scripts_py'])} scripts encontrados.")
        return recursos

    # ---------- sellos de integridad ----------
    def _archivos_nucleo(self):
        """Código que debe permanecer intacto: *.py de la raíz y de tests_fijos/ (sin enlaces simbólicos)."""
        lista = []
        for carpeta in (self.raiz, os.path.join(self.raiz, "tests_fijos")):
            if not os.path.isdir(carpeta):
                continue
            for nombre in sorted(os.listdir(carpeta)):
                ruta = os.path.join(carpeta, nombre)
                if nombre.endswith(".py") and os.path.isfile(ruta) and not os.path.islink(ruta):
                    lista.append(ruta)
        return lista

    def _huellas_actuales(self):
        return {os.path.relpath(r, self.raiz).replace(os.sep, "/"): _huella(r) for r in self._archivos_nucleo()}

    def sellar_nucleo(self, confirmacion="") -> str:
        """Guarda la huella del código actual del laboratorio. Requiere la frase exacta 'SELLAR NUCLEO'."""
        if confirmacion != FRASE_SELLAR:
            return f"[x] No se selló nada. Para sellar escribe exactamente: {FRASE_SELLAR}"
        huellas = self._huellas_actuales()
        datos = {"creado": datetime.datetime.now().isoformat(timespec="seconds"), "archivos": huellas}
        tmp = self.ruta_sellos + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.ruta_sellos)
        self.memory.registrar_evento("integridad_sellada", f"Núcleo sellado: {len(huellas)} archivos.")
        return f"[OK] Núcleo sellado: {len(huellas)} archivos protegidos."

    def verificar_integridad(self) -> dict:
        """Compara el código actual con los sellos. ok=True solo si todo coincide."""
        res = {"ok": False, "sellado": False, "modificados": [], "nuevos": [], "faltan": [], "mensaje": ""}
        if not os.path.isfile(self.ruta_sellos):
            res["mensaje"] = "No hay sellos. Usa sellar_nucleo() cuando el código esté como quieres."
            return res
        try:
            with open(self.ruta_sellos, "r", encoding="utf-8") as f:
                sellos = json.load(f)["archivos"]
            if not isinstance(sellos, dict):
                raise ValueError("formato incorrecto")
        except Exception as e:
            res["mensaje"] = f"No se pueden leer los sellos ({e}). Trátalo como sospechoso."
            return res
        res["sellado"] = True
        actuales = self._huellas_actuales()
        res["modificados"] = sorted(n for n in sellos if n in actuales and actuales[n] != sellos[n])
        res["faltan"] = sorted(n for n in sellos if n not in actuales)
        res["nuevos"] = sorted(n for n in actuales if n not in sellos)
        res["ok"] = not (res["modificados"] or res["faltan"] or res["nuevos"])
        res["mensaje"] = "Integridad correcta." if res["ok"] else (
            "CAMBIOS detectados: " + "; ".join(
                f"{k}: {', '.join(v)}" for k, v in
                (("modificados", res["modificados"]), ("faltan", res["faltan"]), ("nuevos", res["nuevos"])) if v))
        self.memory.registrar_evento("integridad_ok" if res["ok"] else "integridad_fallo", res["mensaje"])
        return res


if __name__ == "__main__":
    registry = KiraRegistry()
    inventario = registry.escanear_laboratorio()
    print("Inventario actual del laboratorio:", {k: v for k, v in inventario.items() if k != "huellas"})
    print(registry.verificar_integridad()["mensaje"])
