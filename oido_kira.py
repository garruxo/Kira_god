# -*- coding: utf-8 -*-
"""
oido_kira.py - El OÍDO PROPIO de Kira: reconocimiento de voz CONTINUO y SIN CONEXIÓN (Vosk), dentro de la app.

Por qué: el reconocedor de Android se para tras cada frase, pita al volver a escuchar y a veces necesita internet.
Vosk escucha sin parar, sin pitidos y sin internet, con un modelo en español de 39 MB que se descarga una vez.

  - descargar_modelo(): baja vosk-model-small-es-0.42.zip (con progreso) y lo descomprime con cuidado.
  - Oido.encender(al_frase): empieza a escuchar; al_frase(texto) llega por cada frase reconocida
    (desde otro hilo: la interfaz la pasa a su hilo con Clock).
  - pausar(True/False): mientras Kira habla o piensa, no se escucha a sí misma.
La librería de Android (vosk-android) va en el APK (buildozer.spec, android.gradle_dependencies). En el PC no hay
oído propio: Kira usa el reconocedor de siempre o el teclado.
Lo que oye no se guarda: cada frase va a escucha_kira (borrador de 10 s en la RAM).
"""
import json
import os
import shutil
import threading
import urllib.request
import zipfile

MODELO = {"nombre": "vosk-model-small-es-0.42", "bytes_aprox": 39_000_000,
          "url": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"}
FRECUENCIA = 16000.0


class OidoError(RuntimeError):
    pass


def _abrir_https(req, timeout=60):
    import red_kira
    return red_kira.abrir(req, timeout=timeout)


def texto_de_resultado(json_vosk):
    """'{"text": "kira qué hora es"}' -> 'kira qué hora es' ('' si no hay nada)."""
    try:
        return str(json.loads(json_vosk or "{}").get("text", "")).strip()
    except (ValueError, AttributeError):
        return ""


class Oido:
    def __init__(self, dir_datos, abrir=_abrir_https):
        self.carpeta = os.path.join(dir_datos, "voz")
        self.ruta_modelo = os.path.join(self.carpeta, MODELO["nombre"])
        self._abrir = abrir
        self.estado = "apagado"            # apagado | descargando | cargando | escuchando | pausa | error
        self.mensaje = ""
        self.progreso = 0.0
        self._servicio = self._oyente = self._modelo = self._recon = None

    # ---------- disponibilidad ----------
    @staticmethod
    def libreria_disponible():
        """¿Está la librería de Vosk dentro de la app? (solo en Android)"""
        try:
            from jnius import autoclass
            autoclass("org.vosk.Model")
            return True
        except Exception:
            return False

    def modelo_instalado(self):
        return os.path.isdir(os.path.join(self.ruta_modelo, "am")) or os.path.isfile(os.path.join(self.ruta_modelo, "conf", "model.conf"))

    def disponible(self):
        return self.modelo_instalado() and self.libreria_disponible()

    # ---------- descarga ----------
    def descargar_modelo(self, progreso=None):
        """Descarga y descomprime el modelo en español. Bloquea: úsalo en un hilo."""
        if self.modelo_instalado():
            return self.ruta_modelo
        os.makedirs(self.carpeta, exist_ok=True)
        zip_ruta = os.path.join(self.carpeta, MODELO["nombre"] + ".zip")
        self.estado, self.mensaje = "descargando", "Descargando el oído de Kira (39 MB)…"
        try:
            req = urllib.request.Request(MODELO["url"], headers={"User-Agent": "KiraApp/1.0"})
            with self._abrir(req, timeout=60) as r, open(zip_ruta, "wb") as f:
                total = int(getattr(r, "headers", {}).get("Content-Length", 0) or 0) or MODELO["bytes_aprox"]
                bajados = 0
                while True:
                    trozo = r.read(256 * 1024)
                    if not trozo:
                        break
                    f.write(trozo)
                    bajados += len(trozo)
                    self.progreso = min(1.0, bajados / total)
                    if progreso:
                        progreso(self.progreso, bajados, total)
            self._descomprimir(zip_ruta)
        except OidoError:
            self.estado = "error"
            raise
        except Exception as e:
            self.estado, self.mensaje = "error", f"No se pudo descargar el oído: {e}"
            raise OidoError(self.mensaje)
        finally:
            if os.path.isfile(zip_ruta):
                os.remove(zip_ruta)
        if not self.modelo_instalado():
            self.estado, self.mensaje = "error", "El archivo descargado no es un modelo de Vosk."
            raise OidoError(self.mensaje)
        self.estado, self.mensaje = "apagado", "Oído de Kira instalado."
        return self.ruta_modelo

    def _descomprimir(self, zip_ruta):
        destino = os.path.realpath(self.carpeta)
        tmp = os.path.join(self.carpeta, ".descomprimiendo")
        shutil.rmtree(tmp, ignore_errors=True)
        with zipfile.ZipFile(zip_ruta) as z:
            for info in z.infolist():                   # nada puede salirse de la carpeta (zip slip)
                final = os.path.realpath(os.path.join(tmp, info.filename))
                if not final.startswith(os.path.realpath(tmp) + os.sep) and final != os.path.realpath(tmp):
                    raise OidoError("El zip del modelo tiene rutas peligrosas: no se descomprime.")
            z.extractall(tmp)
        dentro = [d for d in os.listdir(tmp) if not d.startswith(".")]
        if len(dentro) == 1 and os.path.isdir(os.path.join(tmp, dentro[0])):
            origen = os.path.join(tmp, dentro[0])         # el zip trae una carpeta (se llame como se llame)
        else:
            origen = tmp
        shutil.rmtree(self.ruta_modelo, ignore_errors=True)
        shutil.move(origen, self.ruta_modelo)
        shutil.rmtree(tmp, ignore_errors=True)
        if not os.path.realpath(self.ruta_modelo).startswith(destino):
            raise OidoError("Ruta del modelo no válida.")

    # ---------- escuchar (Android) ----------
    def encender(self, al_frase, al_estado=None):
        """Carga el modelo y escucha sin parar. al_frase(texto) por cada frase. Devuelve (ok, mensaje)."""
        if self.estado in ("escuchando", "pausa", "cargando"):
            return True, "Ya estoy escuchando."
        if not self.modelo_instalado():
            return False, "Falta descargar el oído de Kira (39 MB)."
        if not self.libreria_disponible():
            return False, "Esta versión de Kira no trae el oído propio."
        self.estado, self.mensaje = "cargando", "Preparando el oído…"

        def cargar():
            try:
                from jnius import autoclass, PythonJavaClass, java_method

                class Oyente(PythonJavaClass):
                    __javainterfaces__ = ["org/vosk/android/RecognitionListener"]
                    __javacontext__ = "app"

                    @java_method("(Ljava/lang/String;)V")
                    def onPartialResult(self, hipotesis):
                        pass

                    @java_method("(Ljava/lang/String;)V")
                    def onResult(self, hipotesis):
                        t = texto_de_resultado(hipotesis)
                        if t:
                            al_frase(t)

                    @java_method("(Ljava/lang/String;)V")
                    def onFinalResult(self, hipotesis):
                        t = texto_de_resultado(hipotesis)
                        if t:
                            al_frase(t)

                    @java_method("(Ljava/lang/Exception;)V")
                    def onError(self, e):
                        oido.estado, oido.mensaje = "error", f"Error del oído: {e.toString()}"
                        if al_estado:
                            al_estado(oido.estado)

                    @java_method("()V")
                    def onTimeout(self):
                        pass

                oido = self
                Model = autoclass("org.vosk.Model")
                Recognizer = autoclass("org.vosk.Recognizer")
                SpeechService = autoclass("org.vosk.android.SpeechService")
                self._modelo = Model(self.ruta_modelo)
                self._recon = Recognizer(self._modelo, FRECUENCIA)
                self._servicio = SpeechService(self._recon, FRECUENCIA)
                self._oyente = Oyente()                       # se guarda: si Python lo borra, Java se queda sin oyente
                self._servicio.startListening(self._oyente)
                self.estado, self.mensaje = "escuchando", "Te escucho (oído propio, sin internet)."
            except Exception as e:
                self.estado, self.mensaje = "error", f"No se pudo encender el oído: {e}"
            if al_estado:
                al_estado(self.estado)
        threading.Thread(target=cargar, daemon=True, name="kira-oido").start()
        return True, "Preparando el oído…"

    def pausar(self, si):
        if self._servicio is None or self.estado not in ("escuchando", "pausa"):
            return
        try:
            self._servicio.setPause(bool(si))
            self.estado = "pausa" if si else "escuchando"
        except Exception:
            pass

    def apagar(self):
        s, self._servicio = self._servicio, None
        if s is not None:
            try:
                s.stop()
                s.shutdown()
            except Exception:
                pass
        self.estado = "apagado"
