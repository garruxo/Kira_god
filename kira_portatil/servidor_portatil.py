# -*- coding: utf-8 -*-
"""
servidor_portatil.py - El «cerebro de casa» de Kira: corre en el portátil (Linux + NVIDIA) y le presta al móvil
un cerebro grande y un pintor de verdad por la WiFi.

  - CEREBROS (llama.cpp, «llama-server»):
      rapido  Qwen3.5 9B, entero en la gráfica (8 GB): charla y órdenes, casi al instante.
      grande  Qwen3.5 35B-A3B (mezcla de expertos): la parte común en la gráfica y los «expertos» en la RAM (64 GB).
              Para programar juegos, mejoras largas y entender órdenes complicadas.
    Solo hay uno cargado cada vez (8 GB de gráfica no dan para los dos): el que se pide se carga solo (unos segundos).
  - PINTOR (stable-diffusion.cpp, «sd-cli»): SDXL-Turbo, imágenes de 512 a 1024 px en segundos. Mientras pinta,
    el cerebro se aparta para dejarle la gráfica.
  - SEGURIDAD: todo pide el token del laboratorio (el mismo con el que Kira se empareja con el código de 6 cifras),
    salvo /salud. Solo escucha en tu red de casa.
  - FARO (UDP 8767): Kira pregunta «¿hay un portátil de Kira?» y el faro contesta con su puerto (nunca con el token).

Rutas (cabecera X-Kira-Token):
  GET  /salud                       sin token: {"ok": true}
  GET  /hola                        quién soy y qué tengo (cerebros, pintor, cuál está cargado)
  POST /v1/chat/completions         como llama-server/OpenAI (también «stream»); "kira_cerebro": "rapido"|"grande"
  POST /pintar                      {"prompt", "negativo", "ancho", "alto", "semilla"} -> la imagen PNG
  POST /cerebro                     {"usar": "rapido"|"grande"} carga ese cerebro ya (para no esperar luego)

Solo librería estándar. Se instala con instalar_portatil.sh (lo deja arrancando solo al encender el portátil).
"""
import argparse
import hashlib
import hmac
import http.client
import json
import os
import random
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
HF = "https://huggingface.co/"
PUERTO = 8770
PUERTO_FARO = 8767
PREGUNTA = b"KIRA_BUSCA_PORTATIL 1"
PUERTO_CEREBRO = 8081                     # el llama-server de dentro (solo en este equipo)
MAX_CUERPO = 8 * 1024 * 1024              # una conversación con una foto cabe de sobra

CEREBROS = {
    "rapido": {"nombre": "Qwen3.5 9B (rápido)", "archivo": "Qwen_Qwen3.5-9B-Q4_K_M.gguf", "bytes": 6_169_341_984,
               "url": HF + "bartowski/Qwen_Qwen3.5-9B-GGUF/resolve/main/Qwen_Qwen3.5-9B-Q4_K_M.gguf",
               "ojos": {"archivo": "mmproj-Qwen_Qwen3.5-9B-f16.gguf", "bytes": 918_165_952,
                        "url": HF + "bartowski/Qwen_Qwen3.5-9B-GGUF/resolve/main/mmproj-Qwen_Qwen3.5-9B-f16.gguf"},
               "args": ["-ngl", "99", "-c", "16384"]},
    "grande": {"nombre": "Qwen3.5 35B-A3B (grande)", "archivo": "Qwen_Qwen3.5-35B-A3B-Q4_K_M.gguf",
               "bytes": 22_285_080_384,
               "url": HF + "bartowski/Qwen_Qwen3.5-35B-A3B-GGUF/resolve/main/Qwen_Qwen3.5-35B-A3B-Q4_K_M.gguf",
               "ojos": {"archivo": "mmproj-Qwen_Qwen3.5-35B-A3B-f16.gguf", "bytes": 899_283_552,
                        "url": HF + "bartowski/Qwen_Qwen3.5-35B-A3B-GGUF/resolve/main/mmproj-Qwen_Qwen3.5-35B-A3B-f16.gguf"},
               # los «expertos» en la RAM y el resto en la gráfica: así cabe en 8 GB y va rápido (usa ~3B por palabra)
               "args": ["-ngl", "99", "--n-cpu-moe", "99", "-c", "16384"]},
}
PINTOR = {"nombre": "SDXL-Turbo", "archivo": "sd_xl_turbo_1.0_fp16.safetensors", "bytes": 6_938_081_905,
          "url": HF + "stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors",
          "vae": {"archivo": "sdxl_vae.safetensors", "bytes": 334_641_162,
                  "url": HF + "madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors"},
          "pasos": 4, "cfg": 1.0, "metodo": "euler_a", "lado": 768}

# Modo PRUEBA (para comprobarlo en un ordenador sin gráfica, como el de GitHub): modelos pequeños del móvil
PRUEBA_CEREBRO = {"nombre": "Qwen3.5 2B (prueba)", "archivo": "Qwen_Qwen3.5-2B-Q4_K_M.gguf", "bytes": 1_396_198_496,
                  "url": HF + "bartowski/Qwen_Qwen3.5-2B-GGUF/resolve/main/Qwen_Qwen3.5-2B-Q4_K_M.gguf",
                  "ojos": None, "args": ["-c", "4096"]}
PRUEBA_PINTOR = {"nombre": "SDXS (prueba)", "archivo": "sdxs-512-tinySDdistilled_Q8_0.gguf", "bytes": None,
                 "url": HF + "concedo/sdxs-512-tinySDdistilled-GGUF/resolve/main/sdxs-512-tinySDdistilled_Q8_0.gguf",
                 "vae": None, "pasos": 1, "cfg": 1.0, "metodo": "euler_a", "lado": 512}


def config(prueba=False):
    if prueba:
        return {"rapido": dict(PRUEBA_CEREBRO), "grande": dict(PRUEBA_CEREBRO, nombre="Qwen3.5 2B (prueba, grande)")}, \
            dict(PRUEBA_PINTOR)
    return CEREBROS, PINTOR


def id_equipo(token):
    return hashlib.sha256(("kira-portatil:" + str(token)).encode("utf-8")).hexdigest()[:12]


def nombre_equipo():
    try:
        return (socket.gethostname() or "portatil")[:40]
    except OSError:
        return "portatil"


def gpu():
    """Qué gráfica hay (o '' si no hay NVIDIA)."""
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip().splitlines()[0] if r.returncode == 0 and r.stdout.strip() else ""
    except (OSError, subprocess.SubprocessError):
        return ""


# =====================================================================================
#  EL CEREBRO (un llama-server de dentro, que se cambia cuando se pide otro)
# =====================================================================================
class Cerebro:
    def __init__(self, binario, modelos, cerebros, puerto=PUERTO_CEREBRO, lanzar=subprocess.Popen, espera=600,
                 avisar=print):
        self.binario, self.modelos, self.cerebros = binario, modelos, cerebros
        self.puerto, self._lanzar, self.espera, self.avisar = puerto, lanzar, espera, avisar
        self.actual, self.proceso, self.estado = None, None, "apagado"
        self._lock = threading.RLock()
        self.uso = threading.Semaphore(1)         # una conversación cada vez (y nada de cambiar a mitad)

    def ruta(self, archivo):
        return os.path.join(self.modelos, archivo)

    def disponibles(self):
        return [k for k, c in self.cerebros.items() if os.path.isfile(self.ruta(c["archivo"]))]

    def vivo(self):
        return self.proceso is not None and self.proceso.poll() is None

    def _sano(self):
        try:
            c = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=3)
            c.request("GET", "/health")
            r = c.getresponse()
            r.read()
            return r.status == 200
        except (OSError, http.client.HTTPException):
            return False

    def parar(self):
        with self._lock:
            if self.vivo():
                self.proceso.terminate()
                try:
                    self.proceso.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    self.proceso.kill()
            self.proceso, self.actual, self.estado = None, None, "apagado"

    def usar(self, nombre):
        """Deja cargado ese cerebro (cambia si había otro). Lanza RuntimeError si no se puede."""
        nombre = nombre if nombre in self.cerebros else "rapido"
        with self._lock:
            if self.actual == nombre and self.vivo() and self._sano():
                return nombre
            c = self.cerebros[nombre]
            modelo = self.ruta(c["archivo"])
            if not os.path.isfile(modelo):
                otro = next((k for k in self.disponibles() if k != nombre), None)
                if otro is None:
                    raise RuntimeError(f"Falta el cerebro «{c['nombre']}»: vuelve a lanzar instalar_portatil.sh.")
                return self.usar(otro)
            self.parar()
            args = [self.binario, "-m", modelo, "--host", "127.0.0.1", "--port", str(self.puerto), "-np", "1",
                    "--reasoning-budget", "0"] + list(c.get("args", []))
            ojos = c.get("ojos")
            if ojos and os.path.isfile(self.ruta(ojos["archivo"])):
                args += ["--mmproj", self.ruta(ojos["archivo"])]
            self.estado = f"cargando {nombre}"
            self.avisar(f"[portátil] Cargo el cerebro {c['nombre']}…")
            self.proceso = self._lanzar(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        stdin=subprocess.DEVNULL)
            fin = time.monotonic() + self.espera
            while time.monotonic() < fin:
                if not self.vivo():
                    self.proceso, self.estado = None, "apagado"
                    raise RuntimeError(f"El cerebro «{c['nombre']}» no ha arrancado (¿falta memoria en la gráfica?).")
                if self._sano():
                    self.actual, self.estado = nombre, f"listo: {nombre}"
                    self.avisar(f"[portátil] Cerebro {c['nombre']} listo.")
                    return nombre
                time.sleep(0.5)
            self.parar()
            raise RuntimeError(f"El cerebro «{c['nombre']}» tarda demasiado en cargar.")


# =====================================================================================
#  EL PINTOR (sd-cli: una imagen cada vez)
# =====================================================================================
class Pintor:
    def __init__(self, binario, modelos, pintor, cerebro, correr=subprocess.run):
        self.binario, self.modelos, self.p, self.cerebro, self._correr = binario, modelos, pintor, cerebro, correr
        self._lock = threading.Lock()

    def listo(self):
        return bool(self.binario) and os.path.isfile(self.binario) and \
            os.path.isfile(os.path.join(self.modelos, self.p["archivo"]))

    def pintar(self, prompt, negativo="", ancho=None, alto=None, semilla=None):
        """Devuelve los bytes del PNG. Lanza RuntimeError."""
        if not self.listo():
            raise RuntimeError("El pintor no está instalado en el portátil.")
        lado = int(self.p.get("lado", 512))
        ancho = max(256, min(1024, int(ancho or lado))) // 64 * 64
        alto = max(256, min(1024, int(alto or lado))) // 64 * 64
        semilla = int(semilla) if semilla not in (None, "") else random.randint(0, 2 ** 31 - 1)
        with self._lock:
            self.cerebro.uso.acquire()                     # que no esté contestando mientras se aparta
            try:
                self.cerebro.parar()                       # la gráfica, para el pintor
                with tempfile.TemporaryDirectory() as d:
                    salida = os.path.join(d, "imagen.png")
                    args = [self.binario, "-m", os.path.join(self.modelos, self.p["archivo"]), "-p", str(prompt)[:1500],
                            "-W", str(ancho), "-H", str(alto), "--steps", str(self.p["pasos"]),
                            "--cfg-scale", str(self.p["cfg"]), "--sampling-method", self.p["metodo"],
                            "-s", str(semilla), "-o", salida]
                    vae = self.p.get("vae")
                    if vae and os.path.isfile(os.path.join(self.modelos, vae["archivo"])):
                        args += ["--vae", os.path.join(self.modelos, vae["archivo"])]
                    if negativo and self.p["cfg"] > 1.0:
                        args += ["-n", str(negativo)[:600]]
                    r = self._correr(args, capture_output=True, timeout=900)
                    if r.returncode != 0 or not os.path.isfile(salida):
                        cola = (r.stdout or b"")[-400:] if isinstance(r.stdout, bytes) else str(r.stdout or "")[-400:]
                        raise RuntimeError(f"El pintor ha fallado: {cola!r}")
                    with open(salida, "rb") as f:
                        return f.read()
            finally:
                self.cerebro.uso.release()


# =====================================================================================
#  EL FARO (que Kira encuentre el portátil en la WiFi)
# =====================================================================================
class Faro(threading.Thread):
    def __init__(self, puerto_http, nombre, host="0.0.0.0", puerto=PUERTO_FARO):
        super().__init__(daemon=True, name="kira-faro-portatil")
        self.puerto_http, self.nombre, self.host, self.puerto = int(puerto_http), nombre, host, int(puerto)
        self.listo, self.error, self._parar = threading.Event(), "", threading.Event()

    def parar(self):
        self._parar.set()

    def run(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.puerto))
            self.puerto = s.getsockname()[1]
            s.settimeout(0.5)
        except OSError as e:
            self.error = str(e)
            self.listo.set()
            return
        self.listo.set()
        respuesta = json.dumps({"kira_portatil": 1, "puerto": self.puerto_http, "nombre": self.nombre}).encode("utf-8")
        with s:
            while not self._parar.is_set():
                try:
                    datos, quien = s.recvfrom(256)
                except socket.timeout:
                    continue
                except OSError:
                    continue
                if datos.strip() == PREGUNTA:
                    try:
                        s.sendto(respuesta, quien)
                    except OSError:
                        pass


# =====================================================================================
#  EL SERVIDOR
# =====================================================================================
def _defensa_estado():
    try:
        import red_defensa_kira as rd
        return rd.disponibles()
    except Exception:
        return {}


def crear_servidor(host, puerto, token, cerebro, pintor, nombre=None):
    nombre = nombre or nombre_equipo()
    info_gpu = {"v": None}

    class Manejador(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _json(self, codigo, obj):
            datos = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            if codigo >= 400:                              # lo que no se leyó de la petición no debe liar a la siguiente
                self.close_connection = True
                self.send_header("Connection", "close")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def _autorizado(self):
            return hmac.compare_digest(self.headers.get("X-Kira-Token", ""), token)

        def _cuerpo(self):
            largo = int(self.headers.get("Content-Length", "0") or 0)
            if largo <= 0 or largo > MAX_CUERPO:
                raise ValueError("tamaño no válido")
            d = json.loads(self.rfile.read(largo).decode("utf-8"))
            if not isinstance(d, dict):
                raise ValueError("no es un objeto")
            return d

        def do_GET(self):
            ruta = self.path.split("?", 1)[0]
            if ruta == "/salud":
                return self._json(200, {"ok": True})
            if not self._autorizado():
                return self._json(401, {"ok": False, "error": "token incorrecto"})
            if ruta == "/hola":
                if info_gpu["v"] is None:
                    info_gpu["v"] = gpu()
                return self._json(200, {"ok": True, "tipo": "portatil", "id": id_equipo(token), "nombre": nombre,
                                        "gpu": info_gpu["v"], "cerebros": {k: c["nombre"] for k, c in
                                                                          cerebro.cerebros.items()},
                                        "instalados": cerebro.disponibles(), "cargado": cerebro.actual,
                                        "estado": cerebro.estado, "pintor": pintor.listo(),
                                        "defensa": _defensa_estado()})
            return self._json(404, {"ok": False, "error": "no encontrado"})

        def do_POST(self):
            ruta = self.path.split("?", 1)[0]
            if not self._autorizado():
                return self._json(401, {"ok": False, "error": "token incorrecto"})
            try:
                d = self._cuerpo()
            except (ValueError, UnicodeDecodeError):
                return self._json(400, {"ok": False, "error": "petición mal formada"})
            if ruta == "/cerebro":
                with cerebro.uso:                          # no se cambia en mitad de una respuesta
                    try:
                        return self._json(200, {"ok": True, "cargado": cerebro.usar(str(d.get("usar", "rapido")))})
                    except RuntimeError as e:
                        return self._json(503, {"ok": False, "error": str(e)})
            if ruta == "/pintar":
                try:
                    png = pintor.pintar(d.get("prompt", ""), d.get("negativo", ""), d.get("ancho"), d.get("alto"),
                                        d.get("semilla"))
                except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as e:
                    return self._json(503, {"ok": False, "error": str(e)})
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(png)))
                self.end_headers()
                self.wfile.write(png)
                return
            if ruta == "/v1/chat/completions":
                return self._charla(d)
            if ruta == "/defensa":
                return self._defensa(d)
            return self._json(404, {"ok": False, "error": "no encontrado"})

        def _defensa(self, d):
            """Vigilancia DEFENSIVA de TU red (Nmap/Wireshark), solo dentro de tu red local."""
            import red_defensa_kira as rd
            accion = str(d.get("accion", ""))
            try:
                if accion == "inventario":
                    return self._json(200, {"ok": True, "aparatos": rd.inventario()})
                if accion == "puertos":
                    return self._json(200, {"ok": True, **rd.puertos(d.get("host", ""))})
                if accion == "trafico":
                    return self._json(200, {"ok": True, **rd.trafico(d.get("segundos", 20))})
                if accion == "estado":
                    return self._json(200, {"ok": True, **rd.disponibles()})
                return self._json(400, {"ok": False, "error": "acción de defensa desconocida"})
            except rd.DefensaError as e:
                return self._json(400, {"ok": False, "error": str(e)})

        def _charla(self, d):
            quiero = str(d.pop("kira_cerebro", "rapido"))
            with cerebro.uso:
                try:
                    cerebro.usar(quiero)
                except RuntimeError as e:
                    return self._json(503, {"ok": False, "error": str(e)})
                datos = json.dumps(d).encode("utf-8")
                try:
                    c = http.client.HTTPConnection("127.0.0.1", cerebro.puerto, timeout=900)
                    c.request("POST", "/v1/chat/completions", body=datos,
                              headers={"Content-Type": "application/json", "Content-Length": str(len(datos))})
                    r = c.getresponse()
                except (OSError, http.client.HTTPException) as e:
                    return self._json(502, {"ok": False, "error": f"el cerebro no contesta: {e}"})
                self.send_response(r.status)
                self.send_header("Content-Type", r.getheader("Content-Type", "application/json"))
                if d.get("stream"):                        # va pasando cada trozo según llega
                    self.send_header("Transfer-Encoding", "chunked")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    try:
                        while True:
                            trozo = r.read1(65536) if hasattr(r, "read1") else r.read(65536)
                            if not trozo:
                                break
                            self.wfile.write(b"%x\r\n%s\r\n" % (len(trozo), trozo))
                            self.wfile.flush()
                        self.wfile.write(b"0\r\n\r\n")
                    except OSError:                         # el móvil colgó (p. ej. «para»): se deja de enviar
                        pass
                    finally:
                        c.close()
                    return
                cuerpo = r.read()
                c.close()
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

    return ThreadingHTTPServer((host, puerto), Manejador)


def descargas(prueba=False, sin_grande=False):
    """[(archivo, url, bytes|None)] de todo lo que hay que bajar (lo usa instalar_portatil.sh)."""
    cerebros, pintor = config(prueba)
    sal, vistos = [], set()
    for k, c in cerebros.items():
        if sin_grande and k == "grande":
            continue
        for m in (c, c.get("ojos")):
            if m and m["archivo"] not in vistos:
                vistos.add(m["archivo"])
                sal.append((m["archivo"], m["url"], m.get("bytes")))
    for m in (pintor, pintor.get("vae")):
        if m and m["archivo"] not in vistos:
            vistos.add(m["archivo"])
            sal.append((m["archivo"], m["url"], m.get("bytes")))
    return sal


def leer_token(ruta):
    t = os.environ.get("KIRA_LAB_TOKEN", "").strip()
    if not t and ruta and os.path.isfile(ruta):
        with open(ruta, encoding="utf-8") as f:
            t = f.read().strip()
    return t


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cerebro de casa de Kira (portátil)")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--puerto", type=int, default=PUERTO)
    ap.add_argument("--datos", default=os.path.expanduser("~/kira_portatil"), help="carpeta de modelos y programas")
    ap.add_argument("--token", default=os.path.join(os.path.dirname(AQUI), "kira_laboratorio", "token_lab.txt"))
    ap.add_argument("--prueba", action="store_true", help="modelos pequeños (para probar sin gráfica)")
    ap.add_argument("--sin-faro", action="store_true")
    ap.add_argument("--sin-precarga", action="store_true", help="no cargar el cerebro rápido al arrancar")
    ap.add_argument("--lista-descargas", action="store_true", help="solo escribe qué modelos hay que bajar")
    ap.add_argument("--sin-grande", action="store_true", help="(con --lista-descargas) sin el cerebro grande")
    a = ap.parse_args(argv)
    if a.lista_descargas:
        for archivo, url, tam in descargas(a.prueba, a.sin_grande):
            print(archivo, url, tam or 0)
        return
    token = leer_token(a.token)
    if len(token) < 16:
        sys.exit("No encuentro el token del laboratorio (arranca antes el laboratorio una vez: lo crea él).")
    cerebros, pintor_cfg = config(a.prueba)
    modelos = os.path.join(a.datos, "modelos")
    binarios = os.path.join(a.datos, "bin")
    cerebro = Cerebro(os.path.join(binarios, "llama-server"), modelos, cerebros, avisar=lambda t: print(t, flush=True))
    pintor = Pintor(os.path.join(binarios, "sd-cli"), modelos, pintor_cfg, cerebro)
    servidor = crear_servidor(a.host, a.puerto, token, cerebro, pintor)
    nombre = nombre_equipo()
    if not a.sin_faro:
        faro = Faro(a.puerto, nombre, a.host)
        faro.start()
        faro.listo.wait(2)
        if faro.error:
            print(f"[portátil] Aviso: no pude abrir el faro ({faro.error}).", flush=True)
    print(f"[portátil] Cerebro de casa de Kira en {a.host}:{a.puerto}. GPU: {gpu() or 'sin NVIDIA'}. "
          f"Cerebros instalados: {', '.join(cerebro.disponibles()) or 'ninguno'}; pintor: "
          f"{'sí' if pintor.listo() else 'no'}.", flush=True)
    if not a.sin_precarga and cerebro.disponibles():
        threading.Thread(target=lambda: _precargar(cerebro), daemon=True).start()
    try:
        servidor.serve_forever()
    finally:
        cerebro.parar()


def _precargar(cerebro):
    try:
        cerebro.usar("rapido")
    except RuntimeError as e:
        print(f"[portátil] {e}", flush=True)


if __name__ == "__main__":
    main()
