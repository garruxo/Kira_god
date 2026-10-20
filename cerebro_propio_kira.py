# -*- coding: utf-8 -*-
"""
cerebro_propio_kira.py - El CEREBRO PROPIO de Kira: un modelo de IA que corre DENTRO de la app (sin Termux, sin API).

  - El motor (llama-server de llama.cpp) va dentro del APK como librería nativa (libkira_cerebro*.so), compilado
    por herramientas_pc/compilar_cerebro_android.sh. Hay dos: _dp (rápido, móviles modernos) y genérico.
  - El modelo (archivo .gguf) se DESCARGA UNA VEZ desde Hugging Face, con barra de progreso, comprobando que hay
    espacio y pudiendo REANUDAR si se corta.
  - Kira lo enciende sola al abrirse (si ya está descargado) y le habla en http://127.0.0.1:8080, igual que antes
    hablaba con Termux. Solo escucha dentro del propio móvil (127.0.0.1): nadie de tu WiFi puede usarlo.
"""
import json
import os
import signal
import shutil
import subprocess
import threading
import time
import urllib.request

PUERTO = 8080
MODELOS = {
    "ligero": {"nombre": "Qwen3.5 2B (rápido)", "archivo": "Qwen_Qwen3.5-2B-Q4_K_M.gguf", "bytes": 1_396_198_496,
               "url": "https://huggingface.co/bartowski/Qwen_Qwen3.5-2B-GGUF/resolve/main/Qwen_Qwen3.5-2B-Q4_K_M.gguf",
               "ram_gb": 3,
               "ojos": {"nombre": "ojos del modelo ligero", "archivo": "mmproj-Qwen_Qwen3.5-2B-f16.gguf",
                        "bytes": 668_227_136,
                        "url": "https://huggingface.co/bartowski/Qwen_Qwen3.5-2B-GGUF/resolve/main/mmproj-Qwen_Qwen3.5-2B-f16.gguf"}},
    "listo": {"nombre": "Qwen3.5 4B (más listo)", "archivo": "Qwen_Qwen3.5-4B-Q4_K_M.gguf", "bytes": 3_013_027_808,
              "url": "https://huggingface.co/bartowski/Qwen_Qwen3.5-4B-GGUF/resolve/main/Qwen_Qwen3.5-4B-Q4_K_M.gguf",
              "ram_gb": 6,
              "ojos": {"nombre": "ojos del modelo listo", "archivo": "mmproj-Qwen_Qwen3.5-4B-f16.gguf",
                       "bytes": 672_423_488,
                       "url": "https://huggingface.co/bartowski/Qwen_Qwen3.5-4B-GGUF/resolve/main/mmproj-Qwen_Qwen3.5-4B-f16.gguf"}},
}
BINARIOS = ("libkira_cerebro_dp.so", "libkira_cerebro.so")    # primero el rápido; si el móvil no puede, el genérico
MARGEN_DISCO = 300 * 1024 * 1024
TROZO = 1024 * 1024


class CerebroPropioError(RuntimeError):
    pass


def carpeta_librerias_android():
    """Carpeta donde Android deja las librerías nativas del APK (ahí van los motores). None fuera de Android."""
    try:
        from jnius import autoclass
        actividad = autoclass("org.kivy.android.PythonActivity").mActivity
        return str(actividad.getApplicationInfo().nativeLibraryDir)
    except Exception:
        return None


def _vivo(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def _abrir_https(req, timeout=30):
    import red_kira
    return red_kira.abrir(req, timeout=timeout)


class CerebroPropio:
    def __init__(self, dir_datos, carpeta_binarios=None, abrir=_abrir_https, lanzar=subprocess.Popen,
                 salud=None, reloj=time.monotonic):
        self.dir = dir_datos
        self.carpeta_modelos = os.path.join(dir_datos, "modelos")
        self.ruta_cfg = os.path.join(dir_datos, "cerebro_propio.json")
        self.ruta_log = os.path.join(dir_datos, "cerebro_propio.log")
        self.ruta_pid = os.path.join(dir_datos, "cerebro_propio.pid")   # para reutilizar el cerebro ya cargado
        self.pid_externo = None
        self.ojos_cargados = False
        self._binarios_dir = carpeta_binarios
        self._abrir, self._lanzar, self._reloj = abrir, lanzar, reloj
        self._salud = salud or self._salud_http
        self._lock = threading.Lock()
        self.proceso = None
        self.estado = "apagado"            # apagado | descargando | arrancando | encendido | error
        self.progreso = 0.0
        self.mensaje = ""
        self.binario_usado = None
        self._cancelar = threading.Event()
        cfg = {}
        try:
            with open(self.ruta_cfg, encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, ValueError):
            pass
        cfg = cfg if isinstance(cfg, dict) else {}
        self.modelo = cfg.get("modelo") if cfg.get("modelo") in MODELOS else "ligero"
        self.auto = cfg.get("auto", True) is not False
        self.hilos = int(cfg.get("hilos", 4)) if str(cfg.get("hilos", 4)).isdigit() else 4

    def _guardar(self):
        tmp = self.ruta_cfg + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"modelo": self.modelo, "auto": self.auto, "hilos": self.hilos}, f)
        os.replace(tmp, self.ruta_cfg)

    # ---------- motor ----------
    def binarios(self):
        carpeta = self._binarios_dir or os.environ.get("KIRA_CEREBRO_DIR") or carpeta_librerias_android()
        if not carpeta:
            return []
        return [os.path.join(carpeta, b) for b in BINARIOS if os.path.isfile(os.path.join(carpeta, b))]

    def tiene_motor(self):
        return bool(self.binarios())

    # ---------- modelo ----------
    def ruta_modelo(self, id_=None):
        return os.path.join(self.carpeta_modelos, MODELOS[id_ or self.modelo]["archivo"])

    def modelo_instalado(self, id_=None):
        m = MODELOS[id_ or self.modelo]
        r = self.ruta_modelo(id_)
        return os.path.isfile(r) and os.path.getsize(r) == m["bytes"]

    def instalados(self):
        return [k for k in MODELOS if self.modelo_instalado(k)]

    def elegir(self, id_):
        if id_ not in MODELOS:
            raise CerebroPropioError(f"Modelo desconocido. Elige: {', '.join(MODELOS)}")
        self.modelo = id_
        self._guardar()

    # ---------- ojos (visión: entender fotos y la pantalla) ----------
    def ruta_ojos(self, id_=None):
        o = MODELOS[id_ or self.modelo].get("ojos")
        return os.path.join(self.carpeta_modelos, o["archivo"]) if o else ""

    def ojos_instalados(self, id_=None):
        o = MODELOS[id_ or self.modelo].get("ojos")
        if not o:
            return False
        r = self.ruta_ojos(id_)
        return os.path.isfile(r) and os.path.getsize(r) == o["bytes"]

    def con_ojos(self):
        """¿El cerebro encendido puede ver imágenes?"""
        return self.encendido() and self.ojos_cargados

    def descargar_ojos(self, id_=None, progreso=None):
        """Descarga los ojos del modelo (~670 MB, una vez). Si el cerebro estaba encendido, hay que reiniciarlo."""
        id_ = id_ or self.modelo
        if self.ojos_instalados(id_):
            return self.ruta_ojos(id_)
        return self._bajar(MODELOS[id_]["ojos"], self.ruta_ojos(id_), progreso)

    def descargar(self, id_=None, progreso=None):
        """Descarga el modelo (reanuda si estaba a medias). progreso(fraccion, bajados, total). Bloquea: úsalo en un hilo."""
        id_ = id_ or self.modelo
        if self.modelo_instalado(id_):
            return self.ruta_modelo(id_)
        return self._bajar(MODELOS[id_], self.ruta_modelo(id_), progreso)

    def _bajar(self, m, final, progreso=None):
        os.makedirs(self.carpeta_modelos, exist_ok=True)
        parcial = final + ".parte"
        ya = os.path.getsize(parcial) if os.path.isfile(parcial) else 0
        libre = shutil.disk_usage(self.carpeta_modelos).free
        if libre < (m["bytes"] - ya) + MARGEN_DISCO:
            raise CerebroPropioError(f"No hay espacio: hacen falta {(m['bytes'] - ya + MARGEN_DISCO) / 1e9:.1f} GB libres "
                                     f"y hay {libre / 1e9:.1f} GB.")
        self._cancelar.clear()
        self.estado, self.mensaje = "descargando", f"Descargando {m['nombre']}…"
        req = urllib.request.Request(m["url"], headers={"User-Agent": "KiraApp/1.0",
                                                        **({"Range": f"bytes={ya}-"} if ya else {})})
        try:
            with self._abrir(req, timeout=60) as r:
                if ya and getattr(r, "status", 200) != 206:       # el servidor no reanuda: se empieza de cero
                    ya = 0
                with open(parcial, "ab" if ya else "wb") as f:
                    bajados = ya
                    while True:
                        if self._cancelar.is_set():
                            raise CerebroPropioError("Descarga pausada. Pulsa otra vez para seguir donde se quedó.")
                        trozo = r.read(TROZO)
                        if not trozo:
                            break
                        f.write(trozo)
                        bajados += len(trozo)
                        self.progreso = bajados / m["bytes"]
                        if progreso:
                            progreso(self.progreso, bajados, m["bytes"])
        except CerebroPropioError:
            self.estado = "apagado"
            raise
        except Exception as e:
            self.estado, self.mensaje = "error", f"La descarga se cortó ({e}). Vuelve a pulsar: seguirá donde se quedó."
            raise CerebroPropioError(self.mensaje)
        if os.path.getsize(parcial) != m["bytes"]:
            self.estado = "error"
            self.mensaje = (f"La descarga no está completa ({os.path.getsize(parcial) / 1e9:.2f} de {m['bytes'] / 1e9:.2f} GB). "
                            "Vuelve a pulsar para seguir.")
            raise CerebroPropioError(self.mensaje)
        os.replace(parcial, final)
        self.estado, self.mensaje, self.progreso = "apagado", f"{m['nombre']} descargado.", 1.0
        return final

    def cancelar_descarga(self):
        self._cancelar.set()

    def borrar_modelo(self, id_):
        r = self.ruta_modelo(id_)
        for x in [r, r + ".parte"] + ([self.ruta_ojos(id_), self.ruta_ojos(id_) + ".parte"] if self.ruta_ojos(id_) else []):
            if os.path.isfile(x):
                os.remove(x)

    # ---------- encender / apagar ----------
    def _salud_http(self):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/health", timeout=2) as r:
                return 200 <= getattr(r, "status", 200) < 300
        except Exception:
            return False

    def _argumentos(self, binario, extra=True, ojos=None):
        args = [binario, "-m", self.ruta_modelo(), "-c", "2048", "-t", str(self.hilos),
                "--host", "127.0.0.1", "--port", str(PUERTO)]
        if self.ojos_instalados() if ojos is None else ojos:
            args += ["--mmproj", self.ruta_ojos()]       # con ojos: entiende fotos y capturas
        if extra:
            args += ["--reasoning-budget", "0"]     # sin «pensar en voz alta»: responde mucho antes
        return args

    def encendido(self):
        if self.estado != "encendido":
            return False
        if self.proceso is not None:
            return self.proceso.poll() is None
        return self.pid_externo is not None and _vivo(self.pid_externo)

    def _reutilizar(self):
        """Si el cerebro sigue cargado de antes (Kira se cerró pero el motor siguió vivo), se usa al momento."""
        try:
            partes = open(self.ruta_pid, encoding="utf-8").read().split()
            pid, modelo = int(partes[0]), partes[1]
            ojos = len(partes) > 2 and partes[2] == "ojos"
        except (OSError, ValueError, IndexError):
            return False
        if modelo != self.modelo or (self.ojos_instalados() and not ojos) or not _vivo(pid) or not self._salud():
            self._borrar_pid()
            return False
        self.pid_externo = pid
        self.ojos_cargados = ojos
        return True

    def _guardar_pid(self, pid):
        if isinstance(pid, int):
            try:
                with open(self.ruta_pid, "w", encoding="utf-8") as f:
                    f.write(f"{pid} {self.modelo} {'ojos' if self.ojos_cargados else 'sin_ojos'}")
            except OSError:
                pass

    def _borrar_pid(self):
        try:
            os.remove(self.ruta_pid)
        except OSError:
            pass

    def encender(self, espera=180.0):
        """Arranca el motor con el modelo elegido y espera a que responda. Bloquea: úsalo en un hilo.
        Prueba primero el motor rápido y, si este móvil no puede con él, el genérico."""
        with self._lock:
            if self.encendido():
                return True
            if not self.modelo_instalado():
                self.estado, self.mensaje = "apagado", "Primero hay que descargar el modelo."
                return False
            if self._reutilizar():
                self.estado, self.mensaje = "encendido", "Cerebro propio encendido (ya estaba cargado)."
                return True
            binarios = self.binarios()
            if not binarios:
                self.estado, self.mensaje = "error", "Esta versión de Kira no trae el motor del cerebro."
                return False
            self.estado, self.mensaje = "arrancando", "Kira se está despertando (cargando su cerebro)…"
            for ojos in ((True, False) if self.ojos_instalados() else (False,)):   # si con ojos no cabe, sin ellos
              for binario in binarios:
                for extra in (True, False):
                    if self._probar(binario, extra, espera, ojos):
                        self.binario_usado = binario
                        self.ojos_cargados = ojos
                        self._guardar_pid(getattr(self.proceso, "pid", None))
                        self.estado, self.mensaje = "encendido", "Cerebro propio encendido."
                        return True
            self.estado = "error"
            self.mensaje = "El cerebro no arrancó. Mira el registro (cerebro_propio.log) o prueba el modelo ligero."
            return False

    def _probar(self, binario, extra, espera, ojos=False):
        log = open(self.ruta_log, "ab")
        try:
            extra_kw = {"start_new_session": True} if self._lanzar is subprocess.Popen else {}
            self.proceso = self._lanzar(self._argumentos(binario, extra, ojos), stdout=log, stderr=subprocess.STDOUT,
                                        stdin=subprocess.DEVNULL, cwd=self.dir, **extra_kw)
        except OSError as e:
            log.close()
            self.mensaje = f"No se pudo lanzar el motor: {e}"
            return False
        limite = self._reloj() + espera
        while self._reloj() < limite:
            if self.proceso.poll() is not None:               # se cerró: opción no válida o instrucción no soportada
                log.close()
                self.proceso = None
                return False
            if self._salud():
                log.close()
                return True
            time.sleep(0.5)
        self.apagar()
        log.close()
        return False

    def apagar(self):
        externo, self.pid_externo = self.pid_externo, None
        if externo is not None and _vivo(externo):
            try:
                os.kill(externo, signal.SIGTERM)
            except OSError:
                pass
        self._borrar_pid()
        p, self.proceso = self.proceso, None
        if p is not None and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()
        if self.estado in ("encendido", "arrancando"):
            self.estado, self.mensaje = "apagado", "Cerebro propio apagado."

    def encender_en_segundo_plano(self, al_terminar=None):
        def correr():
            ok = self.encender()
            if al_terminar:
                al_terminar(ok)
        threading.Thread(target=correr, daemon=True, name="kira-cerebro").start()

    # ---------- texto ----------
    def estado_texto(self):
        m = MODELOS[self.modelo]
        partes = [f"Cerebro propio: {m['nombre']}"]
        if not self.tiene_motor():
            partes.append("motor: no incluido en esta versión")
        if self.estado == "descargando":
            partes.append(f"descargando {self.progreso * 100:.0f} %")
        elif self.modelo_instalado():
            partes.append("ENCENDIDO" if self.encendido() else ("arrancando…" if self.estado == "arrancando" else "apagado"))
        else:
            partes.append(f"sin descargar ({m['bytes'] / 1e9:.1f} GB)")
        if self.mensaje and self.estado == "error":
            partes.append(self.mensaje)
        return " · ".join(partes)
