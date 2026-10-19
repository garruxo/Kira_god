# -*- coding: utf-8 -*-
"""
lector_kira.py - Kira LEE imágenes: capturas de pantalla con texto o código (OCR), todo DENTRO del móvil.

  - Motor: Tesseract (Tesseract4Android, Apache 2.0), dentro del APK (buildozer.spec, android.gradle_dependencies).
  - Idiomas: español + inglés («tessdata_fast», unos 6 MB) se descargan UNA vez desde el proyecto oficial.
  - Código: los lectores de texto pierden los espacios del principio de línea (y en Python importan). Kira los
    RECONSTRUYE con la posición de cada palabra en la imagen (salida TSV de Tesseract) y arregla comillas raras.
  - ultima_captura(): la captura más reciente de la carpeta de capturas del móvil.
La lógica de maquetación es pura y se prueba en el PC; la lectura en sí solo funciona en Android.
"""
import os
import re
import statistics
import urllib.request

IDIOMAS = {"spa": "https://github.com/tesseract-ocr/tessdata_fast/raw/main/spa.traineddata",
           "eng": "https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata"}
CARPETAS_CAPTURAS = ("/storage/emulated/0/Pictures/Screenshots", "/storage/emulated/0/DCIM/Screenshots",
                     "/sdcard/Pictures/Screenshots", "/sdcard/DCIM/Screenshots")
EXTENSIONES = (".png", ".jpg", ".jpeg", ".webp")


class LectorError(RuntimeError):
    pass


def _abrir_https(req, timeout=60):
    import red_kira
    return red_kira.abrir(req, timeout=timeout)


# =====================================================================================
#  MAQUETACIÓN (pura): de las palabras con posición (TSV) a texto con su sangría
# =====================================================================================
def leer_tsv(tsv):
    """Palabras del TSV de Tesseract: [(bloque, parrafo, linea, izquierda, ancho, confianza, texto, arriba, alto)]."""
    palabras = []
    for fila in str(tsv or "").splitlines():
        c = fila.split("\t")
        if len(c) < 12 or c[0] != "5":                              # nivel 5 = palabra
            continue
        texto = c[11]
        if not texto.strip():
            continue
        try:
            palabras.append((int(c[2]), int(c[3]), int(c[4]), int(c[6]), int(c[8]), float(c[10]), texto,
                             int(c[7]), int(c[9])))
        except ValueError:
            continue
    return palabras


def parece_codigo(lineas):
    """¿El texto parece código? (símbolos típicos y palabras clave)"""
    texto = "\n".join(lineas)
    señales = len(re.findall(r"[{}();=\[\]<>]|\bdef |\bclass |\bimport |\breturn\b|print\(|function|=>|//", texto))
    return señales >= max(3, len(lineas) // 3)


def _margen(izquierdas, letra):
    """El margen del texto: la posición más a la izquierda donde EMPIEZAN VARIAS líneas (una barra de título suelta
    o un número de línea aislado no cuentan)."""
    for x in sorted(izquierdas):
        if sum(1 for y in izquierdas if abs(y - x) <= letra * 0.6) >= 2:
            return x
    return min(izquierdas)


def maquetar(palabras):
    """Texto con saltos de línea, líneas en blanco y la SANGRÍA reconstruida a partir de dónde empieza cada línea."""
    if not palabras:
        return ""
    lineas = {}
    for b, p, l, izq, ancho, conf, txt, top, alto in palabras:
        lineas.setdefault((b, p, l), []).append((izq, ancho, txt, top, alto))
    filas_raw = []
    for ps in lineas.values():
        ps.sort()
        filas_raw.append((min(q[3] for q in ps), ps))
    filas_raw.sort(key=lambda f: f[0])                              # en orden de lectura, de arriba abajo
    anchos = [w / max(1, len(t)) for _, ps in filas_raw for _, w, t, _, _ in ps if len(t) >= 2]
    letra = statistics.median(anchos) if anchos else 10.0           # ancho de una letra, en píxeles
    margen = _margen([ps[0][0] for _, ps in filas_raw], letra)
    saltos = [b[0] - a[0] for a, b in zip(filas_raw, filas_raw[1:]) if b[0] - a[0] > 0]
    if saltos:                                                      # interlineado típico: mediana de los saltos pequeños
        mitad = sorted(saltos)[: max(1, (len(saltos) + 1) // 2)]
        paso_linea = statistics.median(mitad)
    else:
        paso_linea = 0
    filas, arriba_previa = [], None
    for top, ps in filas_raw:
        sangria = max(0, int(round((ps[0][0] - margen) / letra)))
        px = max(0, ps[0][0] - margen)
        texto, fin = "", None
        for x, w, t, _, _ in ps:
            if fin is not None:
                hueco = int(round((x - fin) / letra))
                texto += " " * (hueco if hueco >= 3 else 1)
            texto += t
            fin = x + w
        if arriba_previa is not None and paso_linea and top - arriba_previa > 1.6 * paso_linea:
            filas.append((0, "", 0))                                 # había una línea en blanco
        arriba_previa = top
        filas.append((sangria, texto, px))
    if parece_codigo([t for _, t, _ in filas]):                      # código: sangrías de 4 en 4
        # el escalón de sangría se mide en píxeles: la menor distancia entre dos comienzos de línea distintos
        grupos = []
        for x in sorted(px for _, t, px in filas if t):
            if not grupos or x - grupos[-1][-1] > letra * 0.8:
                grupos.append([x])
            else:
                grupos[-1].append(x)
        centros = [statistics.median(g) for g in grupos]
        difs = [b - a for a, b in zip(centros, centros[1:])]
        unidad = min(difs) if difs else letra * 4
        return limpiar_codigo("\n".join(" " * (int(round(px / unidad)) * 4) + t for _, t, px in filas))
    return "\n".join(t for _, t, _ in filas)


def limpiar_codigo(texto):
    """Arreglos típicos de un OCR sobre código: comillas tipográficas, guiones largos, etc."""
    t = texto.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").replace("—", "-").replace("–", "-")
    t = t.replace("…", "...").replace(" ", " ")
    return "\n".join(l.rstrip() for l in t.splitlines())


def ultima_captura(carpetas=CARPETAS_CAPTURAS):
    """Ruta de la captura más reciente, o None."""
    mejor, fecha = None, -1.0
    for c in carpetas:
        try:
            for n in os.listdir(c):
                if n.lower().endswith(EXTENSIONES):
                    r = os.path.join(c, n)
                    m = os.path.getmtime(r)
                    if m > fecha:
                        mejor, fecha = r, m
        except OSError:
            continue
    return mejor


# =====================================================================================
#  LECTOR
# =====================================================================================
class Lector:
    def __init__(self, dir_datos, abrir=_abrir_https, motor=None):
        self.carpeta = os.path.join(dir_datos, "ocr")
        self.tessdata = os.path.join(self.carpeta, "tessdata")
        self._abrir = abrir
        self._motor = motor             # para pruebas: motor(ruta, tessdata, idiomas) -> TSV
        self.ultimo = ""                # el último texto leído (para abrirlo en el editor, guardarlo…)
        self.estado, self.mensaje, self.progreso = "listo", "", 0.0

    @staticmethod
    def libreria_disponible():
        try:
            from jnius import autoclass
            autoclass("com.googlecode.tesseract.android.TessBaseAPI")
            return True
        except Exception:
            return False

    def idiomas_instalados(self):
        return all(os.path.isfile(os.path.join(self.tessdata, i + ".traineddata"))
                   and os.path.getsize(os.path.join(self.tessdata, i + ".traineddata")) > 100_000 for i in IDIOMAS)

    def disponible(self):
        return self.idiomas_instalados() and (self._motor is not None or self.libreria_disponible())

    def descargar_idiomas(self, progreso=None):
        """Descarga español e inglés (una vez). Bloquea: úsalo en un hilo."""
        os.makedirs(self.tessdata, exist_ok=True)
        self.estado = "descargando"
        for k, (idioma, url) in enumerate(IDIOMAS.items()):
            final = os.path.join(self.tessdata, idioma + ".traineddata")
            if os.path.isfile(final) and os.path.getsize(final) > 100_000:
                continue
            try:
                with self._abrir(urllib.request.Request(url, headers={"User-Agent": "KiraApp/1.0"}), timeout=60) as r:
                    datos = r.read(60_000_000)
            except Exception as e:
                self.estado, self.mensaje = "error", f"No se pudo descargar el idioma {idioma}: {e}"
                raise LectorError(self.mensaje)
            if len(datos) < 100_000:
                self.estado, self.mensaje = "error", f"El archivo del idioma {idioma} no es válido."
                raise LectorError(self.mensaje)
            with open(final + ".tmp", "wb") as f:
                f.write(datos)
            os.replace(final + ".tmp", final)
            self.progreso = (k + 1) / len(IDIOMAS)
            if progreso:
                progreso(self.progreso)
        self.estado, self.mensaje = "listo", "Lector instalado."
        return True

    def _tsv_android(self, ruta):
        from jnius import autoclass
        TessBaseAPI = autoclass("com.googlecode.tesseract.android.TessBaseAPI")
        File = autoclass("java.io.File")
        api = TessBaseAPI()
        try:
            if not api.init(self.carpeta, "+".join(IDIOMAS)):
                raise LectorError("No se pudo preparar el lector (idiomas).")
            api.setVariable("preserve_interword_spaces", "1")
            api.setImage(File(ruta))
            return str(api.getTSVText(0) or "")
        finally:
            api.recycle()

    def leer(self, ruta):
        """Texto de la imagen (con la sangría del código reconstruida). Bloquea: úsalo en un hilo."""
        if not ruta or not os.path.isfile(ruta):
            raise LectorError("No encuentro esa imagen.")
        if not self.idiomas_instalados():
            raise LectorError("Primero descarga el lector (unos 6 MB).")
        self.estado = "leyendo"
        try:
            tsv = self._motor(ruta, self.tessdata, list(IDIOMAS)) if self._motor else self._tsv_android(ruta)
        except LectorError:
            self.estado = "listo"
            raise
        except Exception as e:
            self.estado = "listo"
            raise LectorError(f"No pude leer la imagen: {e}")
        self.estado = "listo"
        palabras = [p for p in leer_tsv(tsv) if p[5] >= 20]        # se descartan las palabras muy dudosas
        texto = maquetar(palabras)
        if not texto.strip():
            raise LectorError("No veo texto en esa imagen.")
        self.ultimo = texto
        return texto
