# -*- coding: utf-8 -*-
"""
oido_portatil.py - El OÍDO de KiraOS en el portátil (v2.90): le hablas y Kira te entiende. Sin internet.

Lo pidió el dueño: «que pueda hablar con Kira en cualquier punto del sistema: yo escribo o hablo y Kira responde por
voz». En la barra de abajo de KiraOS hay un botón de micrófono: lo pulsas, hablas, y en cuanto te callas Kira tiene la
frase. Usa Vosk (el mismo oído que el móvil) con su modelo pequeño de español y `arecord` (el micrófono de Linux).

Privacidad: el audio vive solo en la memoria mientras se escucha; no se guarda nada en el disco ni sale del portátil.
"""
import json
import os
import shutil
import subprocess
import time

MODELO = os.environ.get("KIRA_VOSK_MODELO", os.path.expanduser("~/kira_portatil/oido/vosk-model-small-es-0.42"))
URL_MODELO = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
FRECUENCIA = 16000


class OidoError(Exception):
    pass


def disponible():
    """(True, "") si se puede escuchar; si no, (False, por qué)."""
    try:
        import vosk  # noqa: F401
    except Exception:
        return False, "Me falta el oído (Vosk). Vuelve a ejecutar el instalador de Kira."
    if not os.path.isdir(MODELO):
        return False, "Me falta el modelo de español del oído. Vuelve a ejecutar el instalador de Kira (lo descarga)."
    if not shutil.which("arecord"):
        return False, "No encuentro «arecord» (el micrófono de Linux): sudo apt install alsa-utils."
    return True, ""


def _micro():
    """Trozos de audio del micrófono (16 kHz, mono, 16 bits), hasta que se cierre."""
    p = subprocess.Popen(["arecord", "-q", "-f", "S16_LE", "-r", str(FRECUENCIA), "-c", "1", "-t", "raw"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        while True:
            trozo = p.stdout.read(4000)
            if not trozo:
                return
            yield trozo
    finally:
        try:
            p.kill()
        except Exception:
            pass


def _reconocedor():
    import vosk
    vosk.SetLogLevel(-1)
    return vosk.KaldiRecognizer(vosk.Model(MODELO), FRECUENCIA)


def escuchar(maximo=8.0, fuente=None, reconocedor=None, reloj=time.monotonic):
    """Escucha hasta que terminas la frase (o `maximo` segundos) y devuelve el texto ('' si no oyó nada).
    `fuente` (trozos de audio) y `reconocedor` se pueden inyectar en las pruebas."""
    if fuente is None or reconocedor is None:
        ok, porque = disponible()
        if not ok:
            raise OidoError(porque)
    rec = reconocedor or _reconocedor()
    trozos = fuente if fuente is not None else _micro()
    fin = reloj() + float(maximo)
    texto = ""
    try:
        for trozo in trozos:
            if rec.AcceptWaveform(trozo):
                texto = (json.loads(rec.Result() or "{}").get("text") or "").strip()
                if texto:                                  # terminó una frase con palabras: ya está
                    break
            if reloj() > fin:
                break
        if not texto:
            texto = (json.loads(rec.FinalResult() or "{}").get("text") or "").strip()
    finally:
        cerrar = getattr(trozos, "close", None)
        if cerrar:
            cerrar()
    return texto


if __name__ == "__main__":
    ok, porque = disponible()
    if not ok:
        raise SystemExit(porque)
    print("Habla ahora…")
    print("Oí:", escuchar() or "(nada)")
