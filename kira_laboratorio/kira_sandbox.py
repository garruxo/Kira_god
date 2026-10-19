# -*- coding: utf-8 -*-
"""
kira_sandbox.py - Ejecución aislada de scripts del laboratorio (PASO 4)

Mejoras sobre la versión anterior:
- Solo ejecuta .py que estén dentro de datos/ (lab_rutas); rechaza '../' y rutas absolutas.
- Python en modo aislado (-I) y ENTORNO LIMPIO: no hereda KIRA_API_KEY, tokens ni variables tuyas.
- Se ejecuta en una carpeta temporal que se borra: lo que el script escriba por ruta relativa no toca datos/.
- Límites (Linux/Termux): tiempo de CPU, memoria (512 MB) y tamaño de archivo/salida (1 MB).
- Si se acaba el tiempo se mata TODO el grupo de procesos (no quedan procesos hijos huérfanos).
- La salida se recorta; no puede llenar la memoria.

LÍMITES QUE SIGUEN EXISTIENDO (esto no es una máquina virtual):
- El script aún puede leer archivos legibles por tu usuario y abrir conexiones de red.
- En Windows no hay límites de memoria/CPU ni grupo de procesos (solo tiempo máximo).
Para código realmente no fiable: Termux (otro usuario de Android), una máquina virtual o un contenedor.
Este módulo es del LABORATORIO (PC/Termux), no está pensado para correr dentro del APK.
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from lab_rutas import carpeta_datos, ruta_segura, RutaNoPermitida
from labor_memory import KiraMemory

TIMEOUT_DEFECTO = 10
MAX_SALIDA = 2000
MAX_ARCHIVO = 1_000_000
MAX_MEMORIA = 512 * 1024 * 1024


def _hacer_limites(timeout):
    if os.name != "posix":
        return None
    import resource

    def aplicar():
        cpu = int(timeout) + 2
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        for limite, valor in ((resource.RLIMIT_AS, MAX_MEMORIA), (resource.RLIMIT_FSIZE, MAX_ARCHIVO)):
            try:
                resource.setrlimit(limite, (valor, valor))
            except (ValueError, OSError):
                pass
        os.umask(0o077)
    return aplicar


def _entorno_limpio():
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8",
           "PYTHONDONTWRITEBYTECODE": "1"}
    if os.name == "nt" and os.environ.get("SYSTEMROOT"):
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return env


def _cola(ruta):
    try:
        with open(ruta, "rb") as f:
            datos = f.read()
        return datos[-MAX_SALIDA:].decode("utf-8", "replace").strip()
    except OSError:
        return ""


class KiraSandbox:
    def __init__(self, base_dir=None):
        self.base = carpeta_datos()
        if base_dir:
            self.base = ruta_segura(base_dir, self.base)
        self.memory = KiraMemory()

    def ejecutar(self, nombre, timeout=TIMEOUT_DEFECTO) -> dict:
        """Ejecuta datos/<nombre>. Devuelve dict: ok, codigo, salida, errores, motivo, duracion."""
        res = {"ok": False, "codigo": None, "salida": "", "errores": "", "motivo": "", "duracion": 0.0}
        try:
            ruta = ruta_segura(nombre, self.base)
            if not ruta.lower().endswith(".py"):
                raise RutaNoPermitida("solo se ejecutan archivos .py")
        except RutaNoPermitida as e:
            res["motivo"] = f"rechazado: {e}"
            return res
        if not os.path.isfile(ruta):
            res["motivo"] = "el archivo no existe"
            return res

        posix = os.name == "posix"
        inicio = time.time()
        with tempfile.TemporaryDirectory(prefix="kira_sbx_") as tmp:
            copia = os.path.join(tmp, os.path.basename(ruta))
            shutil.copy2(ruta, copia)
            ruta_out, ruta_err = os.path.join(tmp, ".out"), os.path.join(tmp, ".err")
            with open(ruta_out, "wb") as fo, open(ruta_err, "wb") as fe:
                try:
                    p = subprocess.Popen(
                        [sys.executable, "-I", copia], cwd=tmp, env=_entorno_limpio(),
                        stdin=subprocess.DEVNULL, stdout=fo, stderr=fe,
                        preexec_fn=_hacer_limites(timeout), start_new_session=posix)
                except OSError as e:
                    res["motivo"] = f"no se pudo lanzar el proceso: {e}"
                    return res
                try:
                    p.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    try:
                        if posix:
                            os.killpg(p.pid, signal.SIGKILL)  # mata también a los hijos
                        else:
                            p.kill()
                    except (ProcessLookupError, OSError):
                        pass
                    p.wait()
                    res["motivo"] = f"tiempo agotado ({timeout}s): posible bucle infinito"
            res["codigo"] = p.returncode
            res["salida"], res["errores"] = _cola(ruta_out), _cola(ruta_err)
        res["duracion"] = round(time.time() - inicio, 2)

        if not res["motivo"]:
            if p.returncode == 0:
                res["ok"] = True
            elif posix and p.returncode == -signal.SIGXCPU:
                res["motivo"] = "límite de CPU superado"
            elif posix and p.returncode == -signal.SIGXFSZ:
                res["motivo"] = "escribió demasiado (límite de 1 MB)"
            elif "File too large" in res["errores"] or "EFBIG" in res["errores"]:
                res["motivo"] = "escribió demasiado (límite de 1 MB)"
            elif "MemoryError" in res["errores"] or (posix and p.returncode == -signal.SIGKILL):
                res["motivo"] = "límite de memoria superado"
            else:
                res["motivo"] = f"terminó con error (código {p.returncode})"
        return res

    def ejecutar_script_seguro(self, nombre_archivo: str) -> str:
        """Compatible con la versión anterior: devuelve un texto [OK]/[x]."""
        r = self.ejecutar(nombre_archivo)
        if r["ok"]:
            self.memory.registrar_evento("sandbox_exito", f"Script {nombre_archivo} ejecutado correctamente.")
            return f"[OK] Ejecución exitosa de {nombre_archivo}:\n{r['salida']}"
        self.memory.registrar_evento("sandbox_error", f"{nombre_archivo}: {r['motivo']} {r['errores'][:100]}")
        detalle = f"\n{r['errores']}" if r["errores"] else ""
        return f"[x] {nombre_archivo}: {r['motivo']}{detalle}"


if __name__ == "__main__":
    print(KiraSandbox().ejecutar_script_seguro("kira_diagnostico.py"))
