# -*- coding: utf-8 -*-
"""
lab_video.py  -  NO VA EN EL APK (corre en el PC del laboratorio, junto a servidor_lab.py)

Trabajos de vídeo: el móvil envía un GUION (datos, nunca código) y recibe un MP4. Usa el motor de Kira_god
(motor_video_kira.py), que debe estar en una carpeta hermana llamada Kira_god, o en la ruta de KIRA_GOD_DIR.

  - Máx. 2 renders a la vez, 20 trabajos guardados, caducan a la hora.
  - El audio se sube aparte (máx. 40 MB, solo extensiones de audio) y se referencia por id.
  - Los archivos viven en datos/video/ y nunca se ejecutan.
  - Trabajos de ffmpeg RESTRINGIDO (mezcla de audio, edición de vídeo) con ffmpeg_seguro.py: archivos subidos por id,
    opciones y filtros de lista blanca, salida con extensión permitida.
"""
import os
import re
import secrets
import sys
import threading
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
KIRA_GOD = os.environ.get("KIRA_GOD_DIR") or os.path.join(os.path.dirname(AQUI), "Kira_god")
if not os.path.isfile(os.path.join(KIRA_GOD, "motor_video_kira.py")) and \
        os.path.isfile(os.path.join(os.path.dirname(AQUI), "motor_video_kira.py")):
    KIRA_GOD = os.path.dirname(AQUI)                   # el laboratorio DENTRO de la carpeta de Kira (como en GitHub)
if os.path.isdir(KIRA_GOD) and KIRA_GOD not in sys.path:
    sys.path.insert(0, KIRA_GOD)

MAX_AUDIO = 40 * 1024 * 1024
MAX_ARCHIVO = 150 * 1024 * 1024
MAX_SIMULTANEOS, MAX_GUARDADOS, CADUCA = 2, 20, 3600
ID_OK = re.compile(r"^[0-9a-f]{16}$")
AUDIO_EXT = (".mp3", ".ogg", ".wav", ".m4a", ".flac", ".aac", ".opus")


def carpeta():
    d = os.path.join(AQUI, "datos", "video")
    os.makedirs(d, exist_ok=True)
    return d


class Trabajos:
    def __init__(self, dir_trabajo=None):
        self.dir = dir_trabajo or carpeta()
        os.makedirs(self.dir, exist_ok=True)
        self.t, self.lock = {}, threading.Lock()

    def _motor(self):
        import motor_video_kira as mv          # import tardío: el servidor arranca aunque falte el motor
        return mv

    def capacidad(self):
        try:
            return self._motor().info_motor()
        except Exception as e:
            return {"listo": False, "motivo": f"No se pudo cargar el motor: {e}"}

    def _limpiar(self):
        ahora = time.time()
        for i, j in list(self.t.items()):
            if j["estado"] != "trabajando" and ahora - j["creado"] > CADUCA:
                self._borrar(i)
        while len(self.t) > MAX_GUARDADOS:
            viejo = min((i for i, j in self.t.items() if j["estado"] != "trabajando"), key=lambda i: self.t[i]["creado"], default=None)
            if viejo is None:
                break
            self._borrar(viejo)

    def _borrar(self, id_):
        j = self.t.pop(id_, None)
        if j and j.get("ruta"):
            try:
                os.remove(j["ruta"])
            except OSError:
                pass

    def guardar_audio(self, nombre, datos):
        """(ok, audio_id|error). El archivo se guarda con un nombre aleatorio; solo importa su extensión."""
        ext = os.path.splitext(str(nombre))[1].lower()
        if ext not in AUDIO_EXT:
            return False, "Formato de audio no admitido."
        if not datos or len(datos) > MAX_AUDIO:
            return False, "Tamaño de audio no válido (máx. 40 MB)."
        id_ = secrets.token_hex(8)
        with open(os.path.join(self.dir, f"f_{id_}{ext}"), "wb") as f:
            f.write(datos)
        return True, id_

    def guardar_archivo(self, nombre, flujo, largo):
        """Sube un audio o vídeo (máx. 150 MB) leyendo el flujo por trozos. (ok, id|error)."""
        ext = os.path.splitext(str(nombre))[1].lower()
        if ext not in self._ffs().EXT_ENTRADA:
            return False, "Formato de archivo no admitido."
        if largo <= 0 or largo > MAX_ARCHIVO:
            return False, "Tamaño no válido (máx. 150 MB)."
        id_ = secrets.token_hex(8)
        ruta, resto = os.path.join(self.dir, f"f_{id_}{ext}"), largo
        with open(ruta, "wb") as f:
            while resto > 0:
                trozo = flujo.read(min(65536, resto))
                if not trozo:
                    break
                f.write(trozo)
                resto -= len(trozo)
        if resto > 0:
            os.remove(ruta)
            return False, "La subida se cortó."
        return True, id_

    def _ffs(self):
        import ffmpeg_seguro
        return ffmpeg_seguro

    def _ruta_subida(self, id_, solo_audio=False):
        if not ID_OK.match(str(id_)):
            raise ValueError("id de archivo no válido")
        exts = AUDIO_EXT if solo_audio else self._ffs().EXT_ENTRADA
        for ext in exts:
            r = os.path.join(self.dir, f"f_{id_}{ext}")
            if os.path.isfile(r):
                return r
        raise ValueError("Ese archivo no está en el laboratorio (súbelo de nuevo).")

    def iniciar_ffmpeg(self, ids, args, ext_salida):
        """Trabajo de ffmpeg restringido. (ok, id|error)."""
        ffs, mv = self._ffs(), self._motor()
        cap = mv.info_motor()
        if not cap["ffmpeg"]:
            return False, "El laboratorio no tiene ffmpeg."
        ext_salida = "." + str(ext_salida).lower().lstrip(".")
        try:
            if not isinstance(ids, list):
                raise ValueError("entradas debe ser una lista")
            entradas = [self._ruta_subida(i) for i in ids]
            with self.lock:
                self._limpiar()
                if sum(1 for j in self.t.values() if j["estado"] == "trabajando") >= MAX_SIMULTANEOS:
                    return False, "El laboratorio está ocupado con otros trabajos. Prueba en un minuto."
                id_ = secrets.token_hex(8)
                salida = os.path.join(self.dir, f"v_{id_}{ext_salida}")
                ffs.construir_comando(cap["ffmpeg"], entradas, salida, args)        # valida todo antes de aceptar
                self.t[id_] = {"estado": "trabajando", "progreso": 0.0, "error": "", "ruta": None, "creado": time.time(), "info": None}
        except (ValueError, ffs.FfmpegError) as e:
            return False, str(e)
        threading.Thread(target=self._trabajo_ffmpeg, args=(id_, cap["ffmpeg"], entradas, salida, list(args)), daemon=True).start()
        return True, id_

    def _trabajo_ffmpeg(self, id_, ffmpeg, entradas, salida, args):
        j = self.t[id_]
        try:
            ok, msg = self._ffs().ejecutar(ffmpeg, entradas, salida, args)
            if ok:
                j.update(estado="listo", ruta=salida, progreso=1.0, info={"bytes": os.path.getsize(salida), "mensaje": msg})
            else:
                j.update(estado="error", error=msg[:400])
        except Exception as e:
            j.update(estado="error", error=str(e)[:400])

    def _ruta_audio(self, id_):
        if not id_:
            return None
        if not ID_OK.match(str(id_)):
            raise ValueError("audio_id no válido")
        for ext in AUDIO_EXT:
            r = os.path.join(self.dir, f"f_{id_}{ext}")
            if os.path.isfile(r):
                return r
        raise ValueError("Ese audio no está en el laboratorio (súbelo de nuevo).")

    def iniciar(self, guion, formato="16:9", calidad="normal", audio_id=None):
        """(ok, id|error). Valida todo antes de aceptar el trabajo."""
        mv = self._motor()
        cap = mv.info_motor()
        if not cap["listo"]:
            return False, f"El laboratorio no puede crear vídeo: {cap['motivo']}"
        try:
            guion = mv.dk.normalizar_guion(guion)
            mv.dimensiones(formato, calidad)
            audio = self._ruta_audio(audio_id)
        except (ValueError, mv.MotorError) as e:
            return False, str(e)
        with self.lock:
            self._limpiar()
            if sum(1 for j in self.t.values() if j["estado"] == "trabajando") >= MAX_SIMULTANEOS:
                return False, "El laboratorio está ocupado con otros vídeos. Prueba en un minuto."
            id_ = secrets.token_hex(8)
            self.t[id_] = {"estado": "trabajando", "progreso": 0.0, "error": "", "ruta": None, "creado": time.time(), "info": None}
        threading.Thread(target=self._trabajo, args=(id_, guion, formato, calidad, audio), daemon=True).start()
        return True, id_

    def _trabajo(self, id_, guion, formato, calidad, audio):
        mv = self._motor()
        j = self.t[id_]
        try:
            r = mv.renderizar(guion, os.path.join(self.dir, f"v_{id_}.mp4"), formato, calidad, audio,
                              progreso=lambda f: j.__setitem__("progreso", round(f, 3)))
            j.update(estado="listo", ruta=r["ruta"], info=r, progreso=1.0)
        except Exception as e:
            j.update(estado="error", error=str(e)[:400])

    def estado(self, id_):
        if not ID_OK.match(str(id_)) or id_ not in self.t:
            return None
        j = self.t[id_]
        return {"estado": j["estado"], "progreso": j["progreso"], "error": j["error"], "info": j["info"]}

    def ruta(self, id_):
        j = self.t.get(id_) if ID_OK.match(str(id_)) else None
        return j["ruta"] if j and j["estado"] == "listo" and j["ruta"] and os.path.isfile(j["ruta"]) else None
