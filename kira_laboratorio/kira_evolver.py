# -*- coding: utf-8 -*-
"""
kira_evolver.py - Autoevolución del laboratorio: PROPONE, prueba y registra; NO aplica (PASO 6)

Antes, aplicar_mejora() sobrescribía cualquier script sin aprobación, copia ni pruebas.
Ahora el evolver:
  1. valida la propuesta (nombre, tamaño, sintaxis),
  2. la guarda SOLO en datos/propuestas/,
  3. la hace probar por el laboratorio (servidor_lab.probar: carga aislada + tests fijos),
  4. confirma que el veredicto corresponde EXACTAMENTE a ese código (sha256),
  5. si falla, anota una lección en estado "propuesta" (no entra en el prompt hasta que tú la confirmes),
  6. NUNCA escribe fuera de datos/propuestas/ y nunca instala nada: aplicar es decisión humana.

Es el único camino de mejora del laboratorio. Los textos de error del laboratorio que se devuelven
al generador (reintentos) se limpian y se acotan, porque derivan de salida de código no fiable.
"""
import ast
import hashlib
import os
import re

from kira_bridge import KiraBridge
from labor_memory import KiraMemory, _limpiar
from lab_rutas import ruta_segura, RutaNoPermitida

NOMBRE_OK = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
MAX_CODIGO = 200_000
MAX_PROPUESTAS = 50
MAX_INTENTOS = 5
DIR_PROP = "propuestas"
DECISIONES = {"aprobada", "rechazada", "revertida", "nota"}


def _sha(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _probador_local(nombre, codigo):
    """Prueba con servidor_lab.probar (mismo equipo). Se puede sustituir por cualquier función igual."""
    try:
        import servidor_lab
        return servidor_lab.probar(nombre, codigo)
    except Exception as e:
        return {"ok": False, "error": f"No se pudo usar el laboratorio: {e}"}


def _avisos(arbol):
    try:
        from servidor_lab import avisos_de
        return avisos_de(arbol)
    except Exception:
        return []


def _nombre_desde(nombre_script):
    """Convierte 'algo/Mi Script.py' en un identificador válido ('mi_script')."""
    base = os.path.splitext(os.path.basename(str(nombre_script).replace("\\", "/")))[0].lower()
    base = re.sub(r"[^a-z0-9_]", "_", base).strip("_") or "mejora"
    if not base[0].isalpha():
        base = "m_" + base
    return base[:31]


class KiraEvolver:
    def __init__(self):
        self.bridge = KiraBridge()
        self.memory = KiraMemory()
        print("[EVOLVER] Módulo de autoevolución cargado (solo propone; no aplica).")

    # ---------- análisis ----------
    def analizar_script(self, nombre_script: str) -> dict:
        """Lee un script de datos/ y calcula métricas básicas. No modifica nada."""
        texto = self.bridge.leer_texto(nombre_script)
        if texto is None:
            return {"estado": "error", "mensaje": f"No se pudo leer {nombre_script}"}
        analisis = {"script": nombre_script, "lineas_totales": len(texto.splitlines()),
                    "documentado": False, "estado": "analizado", "sintaxis_ok": True,
                    "funciones": 0, "clases": 0, "imports": [], "avisos": []}
        try:
            arbol = ast.parse(texto)
            analisis["documentado"] = ast.get_docstring(arbol) is not None
            analisis["funciones"] = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(arbol))
            analisis["clases"] = sum(isinstance(n, ast.ClassDef) for n in ast.walk(arbol))
            mods = set()
            for n in ast.walk(arbol):
                if isinstance(n, ast.Import):
                    mods.update(a.name.split(".")[0] for a in n.names)
                elif isinstance(n, ast.ImportFrom) and n.module:
                    mods.add(n.module.split(".")[0])
            analisis["imports"] = sorted(mods)
            analisis["avisos"] = _avisos(arbol)
        except SyntaxError as e:
            analisis["sintaxis_ok"] = False
            analisis["estado"] = "con_errores"
            analisis["mensaje"] = f"Error de sintaxis: {e}"
        self.memory.registrar_evento("autoevolucion_analisis",
                                     f"Script {nombre_script} analizado ({analisis['lineas_totales']} líneas).")
        return analisis

    # ---------- propuestas ----------
    def _ruta_propuesta(self, nombre):
        if not NOMBRE_OK.match(nombre or ""):
            raise RutaNoPermitida("nombre de propuesta no válido")
        return ruta_segura(f"{DIR_PROP}/{nombre}.py", self.bridge.base)

    def listar_propuestas(self):
        carpeta = os.path.dirname(ruta_segura(f"{DIR_PROP}/x.py", self.bridge.base))
        if not os.path.isdir(carpeta):
            return []
        return sorted(f[:-3] for f in os.listdir(carpeta) if f.endswith(".py") and NOMBRE_OK.match(f[:-3]))

    def leer_propuesta(self, nombre):
        try:
            self._ruta_propuesta(nombre)
        except RutaNoPermitida:
            return None
        return self.bridge.leer_texto(f"{DIR_PROP}/{nombre}.py")

    def descartar_propuesta(self, nombre) -> bool:
        try:
            ruta = self._ruta_propuesta(nombre)
            os.remove(ruta)
            return True
        except (RutaNoPermitida, OSError):
            return False

    def proponer_mejora(self, nombre, codigo, pedido="", probador=None) -> dict:
        """Valida, guarda en propuestas/, prueba en el laboratorio y devuelve el veredicto. No aplica nada."""
        res = {"ok": False, "nombre": nombre, "sha": None, "aprobable": False,
               "etapas": [], "avisos": [], "motivo": "", "archivo": None}
        if not isinstance(nombre, str) or not NOMBRE_OK.match(nombre):
            res["motivo"] = "nombre no válido (minúsculas, números y _; máx. 31 caracteres)"
            return res
        if not isinstance(codigo, str) or not codigo.strip():
            res["motivo"] = "código vacío"
            return res
        if len(codigo.encode("utf-8")) > MAX_CODIGO:
            res["motivo"] = "código demasiado grande"
            return res
        try:
            ast.parse(codigo)
        except SyntaxError as e:
            res["motivo"] = f"error de sintaxis: {e}"
            return res
        if len(self.listar_propuestas()) >= MAX_PROPUESTAS and nombre not in self.listar_propuestas():
            res["motivo"] = f"hay {MAX_PROPUESTAS} propuestas pendientes; descarta alguna antes"
            return res

        sha = _sha(codigo)
        res["sha"] = sha
        guardado = self.bridge.guardar_archivo(f"{DIR_PROP}/{nombre}.py", codigo)
        if not guardado.startswith("[OK]"):
            res["motivo"] = guardado
            return res
        res["archivo"] = f"{DIR_PROP}/{nombre}.py"

        try:
            veredicto = (probador or _probador_local)(nombre, codigo)
            if not isinstance(veredicto, dict):
                raise TypeError("el laboratorio no devolvió un diccionario")
        except Exception as e:
            veredicto = {"ok": False, "error": f"fallo al probar: {e}"}

        res["etapas"] = veredicto.get("etapas", []) if isinstance(veredicto.get("etapas"), list) else []
        res["avisos"] = veredicto.get("avisos", []) if isinstance(veredicto.get("avisos"), list) else []
        res["ok"] = True  # el proceso de prueba se completó (aunque el veredicto sea negativo)
        res["aprobable"] = bool(veredicto.get("ok")) and veredicto.get("sha256") == sha

        if not res["aprobable"]:
            if veredicto.get("ok") and veredicto.get("sha256") != sha:
                res["motivo"] = "el veredicto del laboratorio no corresponde a este código (sha distinto)"
            else:
                fallida = next((e for e in res["etapas"] if isinstance(e, dict) and not e.get("ok")), None)
                if fallida:
                    # del traceback interesa la ÚLTIMA línea (el error real), no un trozo cortado
                    lineas = [l.strip() for l in str(fallida.get("detalle", "")).splitlines() if l.strip()]
                    res["motivo"] = f"falló '{fallida.get('nombre')}': {lineas[-1] if lineas else 'sin detalle'}"
                else:
                    res["motivo"] = str(veredicto.get("error") or "el laboratorio rechazó la mejora")
            self.descartar_propuesta(nombre)  # no dejar basura que no pasó las pruebas
            res["archivo"] = None
            self.memory.registrar_leccion(nombre, "fallo_lab", res["motivo"], pedido, fuente="auto")

        self.memory.registrar_evento(
            "evolver_propuesta", f"{nombre} sha={sha[:12]} aprobable={res['aprobable']}")
        return res

    def proponer_con_reintentos(self, pedido, generador, max_intentos=3, probador=None) -> dict:
        """generador(pedido, feedback)->(nombre, codigo). Reintenta con el motivo del fallo (máx. 5)."""
        max_intentos = max(1, min(int(max_intentos), MAX_INTENTOS))
        feedback, res = "", {"ok": False, "aprobable": False, "motivo": "sin intentos", "intentos": 0}
        for i in range(1, max_intentos + 1):
            try:
                nombre, codigo = generador(pedido, feedback)
            except Exception as e:
                return {"ok": False, "aprobable": False, "intentos": i,
                        "motivo": f"el generador falló: {e}"}
            res = self.proponer_mejora(nombre, codigo, pedido, probador)
            res["intentos"] = i
            if res["aprobable"]:
                return res
            feedback = _limpiar(res["motivo"], 600, una_linea=True)  # texto no fiable: limpio y acotado
        return res

    # ---------- decisiones humanas ----------
    def registrar_decision(self, nombre, resultado, motivo, pedido="") -> dict:
        """SOLO para texto TECLEADO por la persona. Crea una lección ACTIVA (fuente 'usuario')."""
        if resultado not in DECISIONES:
            raise ValueError("resultado debe ser uno de: " + ", ".join(sorted(DECISIONES)))
        leccion = self.memory.registrar_leccion(nombre, resultado, motivo, pedido, fuente="usuario")
        if resultado == "rechazada":
            self.descartar_propuesta(nombre)
        return leccion

    # ---------- presentación ----------
    def resumen(self, res) -> str:
        if not res.get("ok"):
            return f"[x] Propuesta rechazada antes de probar: {res.get('motivo')}"
        lineas = [f"{'[OK]' if res['aprobable'] else '[x]'} Propuesta '{res['nombre']}' "
                  f"{'superó' if res['aprobable'] else 'NO superó'} las pruebas del laboratorio."]
        if res.get("intentos"):
            lineas.append(f"  Intentos: {res['intentos']}")
        if not res["aprobable"]:
            lineas.append(f"  Motivo: {res['motivo']}")
        for a in res.get("avisos", []):
            lineas.append(f"  AVISO: {a}")
        if res["aprobable"]:
            lineas.append(f"  Guardada en {res['archivo']} (NO aplicada: la decisión es tuya).")
        return "\n".join(lineas)

    # ---------- compatibilidad con la versión anterior ----------
    def aplicar_mejora(self, nombre_script: str, codigo_optimizado: str) -> str:
        """YA NO APLICA NADA. Se conserva el nombre por compatibilidad: ahora guarda una PROPUESTA y la prueba."""
        res = self.proponer_mejora(_nombre_desde(nombre_script), codigo_optimizado)
        return "[i] aplicar_mejora ya no modifica el sistema; se trató como propuesta.\n" + self.resumen(res)


if __name__ == "__main__":
    ev = KiraEvolver()
    print("Reporte de análisis:", ev.analizar_script("studio_core.py"))
