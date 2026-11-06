# -*- coding: utf-8 -*-
"""
sentidos_portatil.py - Los SENTIDOS de KiraOS en el propio portátil (v2.93).

Lo pidió el dueño: que Kira tenga cámara, micrófono y pantalla también en el ordenador, y que cada máquina use lo
suyo. El OÍDO ya está (v2.90, `oido_portatil.py`). Aquí van los OJOS y la PANTALLA del portátil:
  - `foto()`    saca una foto con la webcam del portátil (fswebcam o ffmpeg) y LEE su texto (OCR con tesseract);
  - `pantalla()` hace una captura de la pantalla del portátil (scrot / import / grim / spectacle) y lee su texto.

Honestidad (ya dicha al dueño): en el portátil en modo ligero NO hay modelo de visión, así que Kira LEE el texto de lo
que ve (OCR), pero no te dice «eso es un gato». Para describir lo que hay (no solo letras) están sus OJOS del móvil.

Privacidad (regla del proyecto): la foto/captura se BORRA en cuanto se lee; solo se queda el texto.

Todo lo que toca el sistema (`_which`, `correr`) se puede inyectar, así las pruebas no abren la cámara de verdad.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata

IDIOMAS_OCR = "spa+eng"
MAX_TEXTO = 1500


class SentidoError(RuntimeError):
    pass


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# =====================================================================================
#  RECONOCER LA ORDEN (puro)
# =====================================================================================
def es_orden(texto):
    """¿Es una orden de MIRAR con la cámara o de LEER la pantalla? Devuelve (tipo, describir) o None.
    `describir`=True si pediste que te diga QUÉ hay (no solo las letras)."""
    t = _plano(texto)
    # pantalla / captura: solo si además hay un verbo de leer/mirar
    if re.search(r"\b(pantalla|captura)\b", t) and re.search(
            r"\b(lee|leeme|leer|lees|mira|mirar|miras|ver|dime|describe|que\s+(pone|hay|dice|sale|ves))\b", t):
        return ("pantalla", True)
    # cámara / foto
    camara = (re.search(r"\b(camara|webcam)\b", t)
              or re.search(r"\b(haz|hazme|saca|sacame|toma|tomame|echa|echame)\s+(una\s+)?foto\b", t)
              or re.search(r"\bque\s+(tengo|hay)\s+delante\b", t)
              or re.search(r"\bque\s+ves\b", t)
              or re.search(r"\bdescribe\s+lo\s+que\s+(ves|tengo|hay)\b", t))
    if camara:
        describir = bool(re.search(r"\b(que\s+(tengo|hay|ves)|describe|ves)\b", t))
        return ("camara", describir)
    return None


# =====================================================================================
#  ÓRDENES DE SISTEMA (puras: solo arman la lista de argumentos)
# =====================================================================================
HERRAMIENTAS_FOTO = ("fswebcam", "ffmpeg")
HERRAMIENTAS_PANTALLA = ("scrot", "import", "grim", "spectacle", "gnome-screenshot")


def orden_foto(herramienta, destino, dispositivo="/dev/video0"):
    if herramienta == "fswebcam":
        return ["fswebcam", "-q", "-D", "1", "-r", "1280x720", "--no-banner", "-d", dispositivo, destino]
    if herramienta == "ffmpeg":
        return ["ffmpeg", "-y", "-f", "v4l2", "-i", dispositivo, "-frames:v", "1", destino]
    raise SentidoError(f"herramienta de cámara desconocida: {herramienta}")


def orden_pantalla(herramienta, destino):
    if herramienta == "scrot":
        return ["scrot", "-o", destino]
    if herramienta == "import":                    # ImageMagick
        return ["import", "-window", "root", destino]
    if herramienta == "grim":                      # Wayland
        return ["grim", destino]
    if herramienta == "spectacle":                 # KDE
        return ["spectacle", "-b", "-n", "-o", destino]
    if herramienta == "gnome-screenshot":
        return ["gnome-screenshot", "-f", destino]
    raise SentidoError(f"herramienta de pantalla desconocida: {herramienta}")


def orden_ocr(ruta, idiomas=IDIOMAS_OCR):
    return ["tesseract", ruta, "stdout", "-l", idiomas]


def _nota_describir():
    return ("\n\n(En el portátil leo el texto de lo que veo. Para que te diga QUÉ hay —no solo las letras— necesito "
            "mis ojos, que están en el móvil: pídemelo desde allí.)")


# =====================================================================================
#  LOS SENTIDOS (hacen de verdad; `_which` y `correr` se inyectan en las pruebas)
# =====================================================================================
class Sentidos:
    def __init__(self, which=None, correr=None, carpeta_tmp=None):
        self._which = which or shutil.which
        self._correr = correr or self._correr_real
        self._tmp = carpeta_tmp or tempfile.gettempdir()

    def _correr_real(self, args, timeout=30):
        try:
            p = subprocess.run(args, capture_output=True, timeout=timeout)
        except FileNotFoundError:
            raise SentidoError(f"no encuentro «{args[0]}»")
        except subprocess.TimeoutExpired:
            raise SentidoError(f"«{args[0]}» tardó demasiado")
        return p.returncode, (p.stdout or b"").decode("utf-8", "replace")

    # ---- qué hay disponible ----
    def _primera(self, candidatas):
        for h in candidatas:
            if self._which(h):
                return h
        return None

    def camara_lista(self):
        return self._primera(HERRAMIENTAS_FOTO)

    def pantalla_lista(self):
        return self._primera(HERRAMIENTAS_PANTALLA)

    def ocr_listo(self):
        return bool(self._which("tesseract"))

    def estado(self):
        return {"camara": self.camara_lista(), "pantalla": self.pantalla_lista(), "ocr": self.ocr_listo()}

    # ---- leer una imagen con OCR y BORRARLA ----
    def _leer_y_borrar(self, ruta):
        try:
            if not self.ocr_listo():
                return None
            c, salida = self._correr(orden_ocr(ruta), timeout=40)
            return salida.strip() if c == 0 else ""
        finally:
            try:
                os.remove(ruta)                    # privacidad: la imagen se borra tras leerla
            except OSError:
                pass

    def _destino(self, nombre):
        return os.path.join(self._tmp, nombre)

    # ---- foto con la webcam ----
    def foto(self, describir=False, dispositivo="/dev/video0"):
        herr = self.camara_lista()
        if not herr:
            raise SentidoError("No encuentro cámara en el portátil (instala «fswebcam»: sudo apt install fswebcam).")
        destino = self._destino("kira_foto.jpg")
        c, salida = self._correr(orden_foto(herr, destino, dispositivo), timeout=25)
        if c != 0 or not os.path.isfile(destino):
            raise SentidoError("No pude sacar la foto (¿webcam conectada y con permiso?).")
        if not self.ocr_listo():
            try:
                os.remove(destino)
            except OSError:
                pass
            return ("He hecho la foto, pero no tengo el lector (tesseract) para leer su texto. "
                    "Instálalo: sudo apt install tesseract-ocr tesseract-ocr-spa." + (_nota_describir() if describir else ""))
        texto = self._leer_y_borrar(destino)
        return self._respuesta("Con la cámara leo", texto, describir)

    # ---- captura de la pantalla ----
    def pantalla(self, describir=True):
        herr = self.pantalla_lista()
        if not herr:
            raise SentidoError("No sé hacer capturas en este portátil (instala «scrot»: sudo apt install scrot).")
        destino = self._destino("kira_pantalla.png")
        c, salida = self._correr(orden_pantalla(herr, destino), timeout=20)
        if c != 0 or not os.path.isfile(destino):
            raise SentidoError("No pude capturar la pantalla.")
        if not self.ocr_listo():
            try:
                os.remove(destino)
            except OSError:
                pass
            return ("He capturado la pantalla, pero no tengo el lector (tesseract) para leer su texto. "
                    "Instálalo: sudo apt install tesseract-ocr tesseract-ocr-spa.")
        texto = self._leer_y_borrar(destino)
        return self._respuesta("En la pantalla leo", texto, False)

    def _respuesta(self, cabecera, texto, describir):
        if not texto:
            return ("No he leído ninguna letra" + (" (puede que no haya texto a la vista)" if texto == "" else "") + "."
                    + (_nota_describir() if describir else ""))
        corte = texto[:MAX_TEXTO] + ("…" if len(texto) > MAX_TEXTO else "")
        return f"{cabecera}:\n\n{corte}" + (_nota_describir() if describir else "")


def hacer(tipo, describir=False, sentidos=None):
    """Hace la orden de sentido ya reconocida y devuelve el texto para Kira."""
    s = sentidos or Sentidos()
    try:
        return s.foto(describir=describir) if tipo == "camara" else s.pantalla(describir=describir)
    except SentidoError as e:
        return f"[x] {e}"


def texto_estado(sentidos=None):
    s = sentidos or Sentidos()
    e = s.estado()
    partes = [("cámara: " + (e["camara"] if e["camara"] else "no")),
              ("pantalla: " + (e["pantalla"] if e["pantalla"] else "no")),
              ("lector: " + ("sí" if e["ocr"] else "no"))]
    return "Mis sentidos en el portátil — " + ", ".join(partes) + ". El oído va aparte (micrófono + Vosk)."


if __name__ == "__main__":
    import sys
    s = Sentidos()
    print(texto_estado(s))
    if "--foto" in sys.argv:
        print(s.foto(describir="describe" in sys.argv))
    if "--pantalla" in sys.argv:
        print(s.pantalla())
