# -*- coding: utf-8 -*-
"""
video_cliente_kira.py - VA DENTRO DEL APK (solo librería estándar).

Crea el MP4 de un videoclip por el mejor camino disponible:
  1. LOCAL: si este equipo tiene Pillow + ffmpeg (el PC, o un móvil con ffmpeg compilado) usa motor_video_kira.
  2. LABORATORIO: si no, envía el GUION (solo datos) al laboratorio del PC (pasarela.json: url y token) y descarga el MP4.
  3. Si ninguno está disponible, lo explica con claridad (no finge).

El laboratorio nunca recibe ni envía código: solo guion/audio -> vídeo.
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import diseno_kira as dk
import pasarela_cliente as pc

MAX_AUDIO = 40 * 1024 * 1024
AUDIO_EXT = (".mp3", ".ogg", ".wav", ".m4a", ".flac", ".aac", ".opus")


class VideoError(RuntimeError):
    pass


def _salud(url, timeout=3):
    try:
        with urllib.request.urlopen(url + "/salud", timeout=timeout) as r:
            return json.loads(r.read(200).decode("utf-8")).get("ok") is True
    except Exception:
        return False


SIN_LAB = "Laboratorio sin configurar: dime «Kira, conéctate al ordenador» (con el laboratorio encendido en el PC)."


class ClienteVideo:
    def __init__(self, url=None, token=None):
        self._p = pc.PasarelaCliente(url, token)      # url y token se releen si cambia pasarela.json

    @property
    def url(self):
        return self._p.url

    @property
    def token(self):
        return self._p.token

    def _req(self, ruta, datos=None, metodo="GET", tipo="application/json", timeout=30):
        if not self.url or not self.token:
            raise VideoError(SIN_LAB)
        for intento in (1, 2):
            r = urllib.request.Request(self.url + ruta, data=datos, method=metodo,
                                       headers={"Content-Type": tipo, "X-Kira-Token": self.token})
            try:
                return urllib.request.urlopen(r, timeout=timeout)
            except urllib.error.HTTPError as e:
                try:
                    msg = json.loads(e.read(5000).decode("utf-8")).get("error", "")
                except Exception:
                    msg = ""
                raise VideoError(f"El laboratorio respondió {e.code}" + (f": {msg}" if msg else "."))
            except Exception as e:
                if intento == 1 and self._p.reubicar():  # ¿el PC cambió de dirección? lo busca y repite
                    continue
                raise VideoError(f"Laboratorio no alcanzable: {e}")

    def _json(self, ruta, datos=None, metodo="GET", timeout=30):
        cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
        with self._req(ruta, cuerpo, metodo, timeout=timeout) as r:
            return json.loads(r.read(1_000_000).decode("utf-8"))

    def capacidad(self):
        """(ok, motivo): ¿puede el laboratorio crear vídeo ahora mismo?"""
        try:
            d = self._json("/video/capacidad")
            return bool(d.get("ok")), d.get("motivo", "")
        except VideoError as e:
            return False, str(e)

    def subir_audio(self, ruta):
        ext = os.path.splitext(ruta)[1].lower()
        if ext not in AUDIO_EXT or not os.path.isfile(ruta):
            raise VideoError("El audio no existe o su formato no es de audio.")
        if os.path.getsize(ruta) > MAX_AUDIO:
            raise VideoError("El audio supera los 40 MB.")
        with open(ruta, "rb") as f:
            datos = f.read()
        with self._req("/audio?nombre=" + urllib.parse.quote("a" + ext), datos, "POST", "application/octet-stream", timeout=120) as r:
            return json.loads(r.read(100_000).decode("utf-8"))["audio_id"]

    def subir_archivo(self, ruta):
        """Sube un audio o vídeo (máx. 150 MB) al laboratorio y devuelve su id. Lo envía por trozos (sin cargarlo entero)."""
        import ffmpeg_seguro as fs
        ext = os.path.splitext(ruta)[1].lower()
        if ext not in fs.EXT_ENTRADA or not os.path.isfile(ruta):
            raise VideoError("El archivo no existe o su formato no es de audio/vídeo.")
        largo = os.path.getsize(ruta)
        if largo > 150 * 1024 * 1024:
            raise VideoError("El archivo supera los 150 MB.")
        if not self.url or not self.token:
            raise VideoError(SIN_LAB)
        if not _salud(self.url):
            self._p.reubicar()
        with open(ruta, "rb") as f:
            r = urllib.request.Request(self.url + "/archivo?nombre=" + urllib.parse.quote("a" + ext), data=f, method="POST",
                                       headers={"Content-Type": "application/octet-stream", "Content-Length": str(largo),
                                                "X-Kira-Token": self.token})
            try:
                with urllib.request.urlopen(r, timeout=300) as resp:
                    return json.loads(resp.read(100_000).decode("utf-8"))["archivo_id"]
            except urllib.error.HTTPError as e:
                raise VideoError(f"El laboratorio respondió {e.code} al subir el archivo.")
            except Exception as e:
                raise VideoError(f"Laboratorio no alcanzable: {e}")

    def ffmpeg(self, entradas, destino, args, progreso=None, sondeo=1.0, cancelar=None):
        """Trabajo de ffmpeg restringido en el laboratorio: sube las entradas, espera y descarga el resultado a 'destino'."""
        progreso = progreso or (lambda f, t: None)
        ids = []
        for k, e in enumerate(entradas):
            progreso(0.02 + 0.2 * k / max(1, len(entradas)), "Subiendo archivos al laboratorio…")
            ids.append(self.subir_archivo(e))
        limite = time.time() + 180
        while True:
            try:
                d = self._json("/ffmpeg", {"entradas": ids, "args": list(args), "salida": os.path.splitext(destino)[1].lstrip(".")}, "POST")
                break
            except VideoError as e:
                if "ocupado" not in str(e) or time.time() > limite:
                    raise
                time.sleep(max(0.2, min(sondeo * 2, 3.0)))
        id_ = d["id"]
        while True:
            if cancelar is not None and cancelar.is_set():
                raise VideoError("Cancelado.")
            e = self.estado(id_)
            if e["estado"] == "error":
                raise VideoError(e["error"])
            progreso(0.25 + 0.65 * float(e["progreso"]), "El laboratorio está procesando…")
            if e["estado"] == "listo":
                break
            time.sleep(sondeo)
        progreso(0.92, "Descargando el resultado…")
        self.descargar(id_, destino)
        progreso(1.0, "Listo")
        return destino

    def instalar(self, paquetes):
        """Pide al laboratorio instalar paquetes de su lista blanca (solo si el PC lo permitió). (ok, detalle)."""
        try:
            d = self._json("/instalar", {"paquetes": list(paquetes)}, "POST", timeout=900)
            return bool(d.get("ok")), d.get("detalle", "")
        except VideoError as e:
            return False, str(e)

    def lista_paquetes(self):
        """(habilitado, [{'nombre','para_que','instalado'}]) o lanza VideoError."""
        d = self._json("/instalar/lista")
        return bool(d.get("habilitado")), d.get("paquetes", [])

    def info(self, timeout=5):
        """{'ok','ffmpeg','instalar'} del laboratorio o {'ok': False, 'motivo'} si no se alcanza."""
        try:
            return self._json("/video/capacidad", timeout=timeout)
        except VideoError as e:
            return {"ok": False, "ffmpeg": False, "instalar": False, "motivo": str(e)}

    def renderizar(self, guion, formato, calidad, audio_id=None):
        d = self._json("/video", {"guion": guion, "formato": formato, "calidad": calidad, "audio_id": audio_id}, "POST")
        return d["id"]

    def estado(self, id_):
        return self._json("/video/estado?id=" + urllib.parse.quote(id_))

    def descargar(self, id_, destino):
        os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
        parcial = destino + ".part"
        with self._req("/video/archivo?id=" + urllib.parse.quote(id_), timeout=120) as r, open(parcial, "wb") as f:
            while True:
                trozo = r.read(65536)
                if not trozo:
                    break
                f.write(trozo)
        if os.path.getsize(parcial) == 0:
            os.remove(parcial)
            raise VideoError("El laboratorio devolvió un archivo vacío.")
        os.replace(parcial, destino)
        return destino


def motor_local_listo():
    try:
        import motor_video_kira as mv
        i = mv.info_motor()
        return i["listo"], i["motivo"]
    except Exception as e:
        return False, f"El motor local no está disponible en este dispositivo ({e.__class__.__name__})."


def donde_se_renderiza():
    """('local'|'laboratorio'|None, explicación). Para mostrarlo al usuario antes de empezar."""
    ok, motivo_local = motor_local_listo()
    if ok:
        return "local", "Se creará aquí mismo (este equipo tiene ffmpeg)."
    ok_lab, motivo_lab = ClienteVideo().capacidad()
    if ok_lab:
        return "laboratorio", "Se creará en el laboratorio de tu PC."
    return None, f"No se puede crear vídeo ahora. Aquí: {motivo_local} Laboratorio: {motivo_lab}"


def crear_video(guion, destino, formato="16:9", calidad="normal", audio=None, progreso=None, cancelar=None, sondeo=1.0):
    """Devuelve (donde, info). Lanza VideoError con un mensaje claro. 'progreso(fracción, texto)'."""
    guion = dk.normalizar_guion(guion)
    progreso = progreso or (lambda f, t: None)
    donde, motivo = donde_se_renderiza()
    if donde is None:
        raise VideoError(motivo)
    if donde == "local":
        import motor_video_kira as mv
        try:
            progreso(0.0, "Creando el vídeo aquí…")
            info = mv.renderizar(guion, destino, formato, calidad, audio, progreso=lambda f: progreso(f, "Creando el vídeo aquí…"), cancelar=cancelar)
        except mv.MotorError as e:
            raise VideoError(str(e))
        return "local", info
    cl = ClienteVideo()
    audio_id = None
    if audio:
        progreso(0.02, "Subiendo la música al laboratorio…")
        audio_id = cl.subir_audio(audio)
    limite = time.time() + 180                   # si el laboratorio está ocupado con otros vídeos, espera su turno (máx. 3 min)
    while True:
        try:
            id_ = cl.renderizar(guion, formato, calidad, audio_id)
            break
        except VideoError as e:
            if "ocupado" not in str(e) or time.time() > limite:
                raise
            if cancelar is not None and cancelar.is_set():
                raise VideoError("Cancelado.")
            progreso(0.03, "El laboratorio está ocupado; esperando turno…")
            time.sleep(max(0.2, min(sondeo * 2, 3.0)))
    while True:
        if cancelar is not None and cancelar.is_set():
            raise VideoError("Cancelado.")
        e = cl.estado(id_)
        if e["estado"] == "error":
            raise VideoError(f"El laboratorio no pudo crear el vídeo: {e['error']}")
        progreso(0.05 + 0.85 * float(e["progreso"]), "El laboratorio está creando el vídeo…")
        if e["estado"] == "listo":
            break
        time.sleep(sondeo)
    progreso(0.92, "Descargando el vídeo…")
    cl.descargar(id_, destino)
    progreso(1.0, "Listo")
    return "laboratorio", e.get("info") or {"ruta": destino}
