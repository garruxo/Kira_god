# -*- coding: utf-8 -*-
"""
servidor_lab.py  -  NO VA EN EL APK (corre en el PC o en Termux)

Recibe una mejora, la prueba en un proceso aparte y devuelve un veredicto.
NUNCA envía código al móvil ni toca el sistema real.

Uso:
  export KIRA_LAB_TOKEN="un-token-largo-y-aleatorio"      (Windows: set KIRA_LAB_TOKEN=...)
  python servidor_lab.py                          # solo este equipo (127.0.0.1)
  python servidor_lab.py --host 0.0.0.0           # accesible desde tu WiFi (el token es obligatorio)

Vídeo (motor gráfico real): POST /video, GET /video/estado, GET /video/archivo, POST /audio (ver lab_video.py).

Etapas:
  1. sintaxis      2. revisión de patrones sensibles (avisos para el humano)
  3. carga aislada con límite de tiempo   4. tests fijos de laboratorio/tests_fijos/

AVISO HONESTO: un subproceso con límites NO es una caja de seguridad completa.
Para código realmente no fiable, ejecuta este servidor en una máquina virtual,
contenedor o usuario sin privilegios y sin tus claves ni datos personales.
"""
import argparse
import ast
import glob
import hashlib
import hmac
import json
import os
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import lab_instalar
import lab_video

TOKEN = os.environ.get("KIRA_LAB_TOKEN", "")
AQUI = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.join(AQUI, "tests_fijos")
MAX_BODY = 300_000
IMPORTS_SENSIBLES = {"subprocess", "socket", "shutil", "ctypes", "urllib", "requests", "pickle", "importlib"}
LLAMADAS_SENSIBLES = {"eval", "exec", "compile", "__import__", "open"}

TRABAJOS = lab_video.Trabajos()

LOADER = (
    "import importlib.util,sys\n"
    "s=importlib.util.spec_from_file_location('mejora',sys.argv[1])\n"
    "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print('CARGA_OK')\n"
)


def limites():
    """Límites de CPU y memoria (solo Linux/Termux)."""
    if os.name != "posix":
        return None
    import resource

    def f():
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
        try:
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        except (ValueError, OSError):
            pass
    return f


def ejecutar(args, cwd, timeout):
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}
    try:
        p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True,
                           timeout=timeout, preexec_fn=limites())
        salida = (p.stdout + p.stderr)[-1500:]
        return p.returncode == 0, salida.strip()
    except subprocess.TimeoutExpired:
        return False, f"Tiempo excedido ({timeout}s): posible bucle infinito."
    except Exception as e:
        return False, f"Error al ejecutar: {e}"


def avisos_de(arbol):
    avisos = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] in IMPORTS_SENSIBLES:
                    avisos.add(f"importa '{a.name}' (línea {n.lineno})")
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] in IMPORTS_SENSIBLES:
                avisos.add(f"importa de '{n.module}' (línea {n.lineno})")
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id in LLAMADAS_SENSIBLES:
                avisos.add(f"llama a '{n.func.id}()' (línea {n.lineno})")
    return sorted(avisos)


def probar(nombre, codigo):
    sha = hashlib.sha256(codigo.encode("utf-8")).hexdigest()
    res = {"ok": False, "sha256": sha, "etapas": [], "avisos": []}

    try:
        arbol = ast.parse(codigo)
        res["etapas"].append({"nombre": "sintaxis", "ok": True})
    except SyntaxError as e:
        res["etapas"].append({"nombre": "sintaxis", "ok": False, "detalle": str(e)})
        return res

    res["avisos"] = avisos_de(arbol)
    res["etapas"].append({"nombre": "revision_patrones", "ok": True,
                          "detalle": f"{len(res['avisos'])} aviso(s)"})

    with tempfile.TemporaryDirectory() as tmp:
        ruta = os.path.join(tmp, nombre + ".py")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(codigo)

        ok, out = ejecutar([sys.executable, "-I", "-c", LOADER, ruta], tmp, 10)
        res["etapas"].append({"nombre": "carga_aislada", "ok": ok, "detalle": out[-300:]})
        if not ok:
            return res

        tests = sorted(glob.glob(os.path.join(TESTS, "test_*.py")))
        if not tests:
            res["etapas"].append({"nombre": "tests_fijos", "ok": False,
                                  "detalle": "No hay tests fijos: no se aprueba nada sin ellos."})
            return res
        for t in tests:
            ok, out = ejecutar([sys.executable, "-I", t, ruta], tmp, 15)
            res["etapas"].append({"nombre": "test:" + os.path.basename(t), "ok": ok,
                                  "detalle": out[-300:]})
            if not ok:
                return res

    res["ok"] = True
    return res


class Handler(BaseHTTPRequestHandler):
    def _json(self, codigo, obj):
        datos = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def _autorizado(self):
        return hmac.compare_digest(self.headers.get("X-Kira-Token", ""), TOKEN)

    def do_GET(self):
        ruta, _, consulta = self.path.partition("?")
        if ruta == "/salud":
            return self._json(200, {"ok": True})
        if ruta in ("/video/estado", "/video/archivo", "/video/capacidad", "/instalar/lista"):
            if not self._autorizado():
                return self._json(401, {"ok": False, "error": "token incorrecto"})
            if ruta == "/video/capacidad":
                c = TRABAJOS.capacidad()
                return self._json(200, {"ok": bool(c.get("listo")), "motivo": c.get("motivo", ""), "codec": c.get("codec"),
                                        "ffmpeg": bool(c.get("ffmpeg")), "instalar": lab_instalar.HABILITADO})
            if ruta == "/instalar/lista":
                return self._json(200, {"ok": True, "habilitado": lab_instalar.HABILITADO, "paquetes": lab_instalar.estado_paquetes()})
            id_ = dict(p.split("=", 1) for p in consulta.split("&") if "=" in p).get("id", "")
            if ruta == "/video/estado":
                e = TRABAJOS.estado(id_)
                return self._json(200, {"ok": True, **e}) if e else self._json(404, {"ok": False, "error": "trabajo desconocido"})
            r = TRABAJOS.ruta(id_)
            if not r:
                return self._json(404, {"ok": False, "error": "el vídeo no está listo o ya caducó"})
            self.send_response(200)
            self.send_header("Content-Type", {".mp4": "video/mp4", ".webm": "video/webm", ".mp3": "audio/mpeg", ".wav": "audio/wav",
                                              ".m4a": "audio/mp4", ".ogg": "audio/ogg", ".flac": "audio/flac", ".aac": "audio/aac",
                                              ".opus": "audio/ogg"}.get(os.path.splitext(r)[1].lower(), "application/octet-stream"))
            self.send_header("Content-Length", str(os.path.getsize(r)))
            self.end_headers()
            with open(r, "rb") as f:
                while True:
                    trozo = f.read(65536)
                    if not trozo:
                        break
                    self.wfile.write(trozo)
            return
        self._json(404, {"ok": False, "error": "no encontrado"})

    def _leer(self, maximo):
        largo = int(self.headers.get("Content-Length", "0"))
        if largo <= 0 or largo > maximo:
            raise ValueError("tamaño no válido")
        return self.rfile.read(largo)

    def do_POST(self):
        ruta, _, consulta = self.path.partition("?")
        if ruta not in ("/probar", "/video", "/audio", "/archivo", "/ffmpeg", "/instalar"):
            return self._json(404, {"ok": False, "error": "no encontrado"})
        if not self._autorizado():
            return self._json(401, {"ok": False, "error": "token incorrecto"})
        if ruta == "/audio":
            try:
                nombre = dict(p.split("=", 1) for p in consulta.split("&") if "=" in p).get("nombre", "")
                ok, r = TRABAJOS.guardar_audio(nombre, self._leer(lab_video.MAX_AUDIO))
            except Exception:
                return self._json(400, {"ok": False, "error": "petición mal formada"})
            return self._json(200 if ok else 400, {"ok": True, "audio_id": r} if ok else {"ok": False, "error": r})
        if ruta == "/archivo":
            try:
                nombre = dict(p.split("=", 1) for p in consulta.split("&") if "=" in p).get("nombre", "")
                largo = int(self.headers.get("Content-Length", "0"))
                ok, r = TRABAJOS.guardar_archivo(nombre, self.rfile, largo)
            except Exception:
                return self._json(400, {"ok": False, "error": "petición mal formada"})
            return self._json(200 if ok else 400, {"ok": True, "archivo_id": r} if ok else {"ok": False, "error": r})
        if ruta == "/ffmpeg":
            try:
                d = json.loads(self._leer(MAX_BODY).decode("utf-8"))
                ok, r = TRABAJOS.iniciar_ffmpeg(d["entradas"], d["args"], str(d.get("salida", "mp4")))
            except Exception:
                return self._json(400, {"ok": False, "error": "petición mal formada"})
            return self._json(200 if ok else 400, {"ok": True, "id": r} if ok else {"ok": False, "error": r})
        if ruta == "/instalar":
            if not lab_instalar.HABILITADO:
                return self._json(403, {"ok": False, "error": "La instalación está desactivada en este laboratorio (arráncalo con --permitir-instalar)."})
            try:
                d = json.loads(self._leer(MAX_BODY).decode("utf-8"))
                ok, r = lab_instalar.instalar(d["paquetes"])
            except Exception:
                return self._json(400, {"ok": False, "error": "petición mal formada"})
            return self._json(200 if ok else 400, {"ok": ok, "detalle": r})
        if ruta == "/video":
            try:
                d = json.loads(self._leer(MAX_BODY).decode("utf-8"))
                ok, r = TRABAJOS.iniciar(d["guion"], str(d.get("formato", "16:9")), str(d.get("calidad", "normal")), d.get("audio_id"))
            except Exception:
                return self._json(400, {"ok": False, "error": "petición mal formada"})
            return self._json(200 if ok else 400, {"ok": True, "id": r} if ok else {"ok": False, "error": r})
        try:
            datos = json.loads(self._leer(MAX_BODY).decode("utf-8"))
            nombre, codigo = str(datos["nombre"]), str(datos["codigo"])
            import re
            if not re.match(r"^[a-z][a-z0-9_]{0,30}$", nombre):
                return self._json(400, {"ok": False, "error": "nombre no válido"})
        except ValueError:
            return self._json(413, {"ok": False, "error": "tamaño no válido"})
        except Exception:
            return self._json(400, {"ok": False, "error": "petición mal formada"})
        self._json(200, probar(nombre, codigo))

    def log_message(self, fmt, *args):
        sys.stderr.write("[lab] " + fmt % args + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--permitir-instalar", action="store_true",
                    help="deja que el móvil (con el token y tu confirmación) pida instalar paquetes de la lista blanca con pip")
    a = ap.parse_args()
    lab_instalar.HABILITADO = a.permitir_instalar
    if len(TOKEN) < 16:
        sys.exit("Define KIRA_LAB_TOKEN con al menos 16 caracteres antes de arrancar.")
    print(f"[lab] Escuchando en {a.host}:{a.port}  (Ctrl+C para parar)")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
