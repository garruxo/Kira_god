# -*- coding: utf-8 -*-
"""
pdf_kira.py - La BIBLIOTECA DE PDF de Kira: descargarlos desde un enlace, leerlos y gestionarlos.

  «Kira, descarga este PDF: https://…/apuntes.pdf»  -> lo baja (también enlaces de Google Drive, Dropbox, GitHub y
                                                       páginas que llevan a un PDF, como arXiv) y lo guarda.
  «mis pdf»                 -> la lista               «lee el pdf 2» / «lee la página 3 del pdf 2»
  «resume el pdf 2»         -> resumen con el cerebro «busca fotosíntesis en el pdf 2» -> en qué páginas sale
  «qué dice el pdf 2 sobre la clorofila» -> responde con las páginas que vienen al caso (y dice cuáles)
  «estudia el pdf 2»        -> lo guarda por trozos en el baúl (luego Kira lo responde sola)
  «renombra el pdf 2 a Biología» · «borra el pdf 2» · «guarda el pdf 2 en descargas» (carpeta Descargas del móvil)
  Compartir un PDF (o un enlace) desde otra app → Kira: lo añade a la biblioteca.

El texto se saca con pypdf (va dentro del APK; si faltara, un lector sencillo propio). Los PDF escaneados (fotos de
páginas) no tienen texto: para esos, «lee la captura» con una foto de la página.
Lógica pura (sin Kivy ni Android): se prueba en el PC. Los PDF se guardan en KIRA_DATA_DIR/pdf.
"""
import hashlib
import json
import os
import re
import threading
import time
import unicodedata
import urllib.parse
import urllib.request

MAX_BYTES = 150 * 1024 * 1024        # un PDF de más de 150 MB no se baja (sería un libro escaneado enorme)
MAX_PAGINAS_TEXTO = 2000
MAX_PDFS = 300


class PdfError(RuntimeError):
    pass


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def carpeta_base():
    return os.path.join(os.environ.get("KIRA_DATA_DIR") or os.path.expanduser("~"), "pdf")


# =====================================================================================
#  ENLACES: de «el enlace que me das» a «la dirección del archivo»
# =====================================================================================
_URL = re.compile(r"https?://[^\s<>\"'«»]+", re.I)


def url_de(texto):
    """La primera dirección web del texto (sin la puntuación que se cuela al final), o ''."""
    m = _URL.search(str(texto or ""))
    return m.group(0).rstrip(".,;:!?)]}»") if m else ""


def enlace_directo(url):
    """Los enlaces «para ver» de Drive, Dropbox, GitHub o arXiv, convertidos en el del archivo."""
    p = urllib.parse.urlsplit(url)
    host, ruta = p.netloc.lower(), p.path
    m = re.match(r"^/file/d/([\w-]{10,})", ruta)
    if host.endswith("drive.google.com") and m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    if host.endswith("drive.google.com") and "id=" in p.query:
        i = urllib.parse.parse_qs(p.query).get("id", [""])[0]
        if i:
            return f"https://drive.google.com/uc?export=download&id={i}"
    if host.endswith("dropbox.com"):
        q = urllib.parse.parse_qs(p.query)
        q["dl"] = ["1"]
        return urllib.parse.urlunsplit((p.scheme, p.netloc, ruta, urllib.parse.urlencode(q, doseq=True), ""))
    if host == "github.com" and "/blob/" in ruta:
        return "https://raw.githubusercontent.com" + ruta.replace("/blob/", "/", 1)
    m = re.match(r"^/abs/(.+?)(?:v\d+)?/?$", ruta)
    if host.endswith("arxiv.org") and m:
        return f"https://arxiv.org/pdf/{m.group(1)}"
    return url


def pdf_en_pagina(html, base):
    """Si el enlace era una PÁGINA que lleva a un PDF, la dirección de ese PDF (la que más lo parece), o ''."""
    t = html.decode("utf-8", "replace") if isinstance(html, bytes) else str(html)
    candidatos = re.findall(r"""href\s*=\s*["']([^"'#]+?\.pdf(?:\?[^"']*)?)["']""", t, re.I)
    candidatos += re.findall(r"""<meta[^>]+citation_pdf_url[^>]+content\s*=\s*["']([^"']+)["']""", t, re.I)
    for c in candidatos:
        u = urllib.parse.urljoin(base, c.replace("&amp;", "&"))
        if u.lower().startswith(("http://", "https://")):
            return u
    return ""


def nombre_de(url, cabeceras=None):
    """Un nombre de archivo razonable (de la cabecera Content-Disposition o de la dirección)."""
    cd = (cabeceras or {}).get("Content-Disposition", "") if cabeceras else ""
    m = re.search(r"filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)", cd or "", re.I)
    if m:
        nombre = urllib.parse.unquote(m.group(1) or m.group(2))
    else:
        nombre = urllib.parse.unquote(os.path.basename(urllib.parse.urlsplit(url).path)) or "documento"
    nombre = re.sub(r"\.pdf$", "", nombre.strip(), flags=re.I)
    nombre = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", " ", nombre).strip(" .") or "documento"
    return nombre[:80]


# =====================================================================================
#  TEXTO DE UN PDF
# =====================================================================================
def paginas_de(ruta):
    """(lista con el texto de cada página, info {'titulo', 'autor', 'paginas', 'cifrado'}). Lanza PdfError."""
    try:
        import pypdf
    except ImportError:
        pypdf = None
    if pypdf is not None:
        try:
            lector = pypdf.PdfReader(ruta)
            cifrado = bool(lector.is_encrypted)
            if cifrado:
                try:
                    lector.decrypt("")                  # muchos PDF «protegidos» abren con contraseña vacía
                except Exception:
                    raise PdfError("El PDF tiene contraseña: no lo puedo abrir.")
            textos = []
            for i, pag in enumerate(lector.pages):
                if i >= MAX_PAGINAS_TEXTO:
                    break
                try:
                    textos.append(_limpiar(pag.extract_text() or ""))
                except Exception:
                    textos.append("")
            meta = lector.metadata or {}
            info = {"titulo": str(meta.get("/Title") or "").strip()[:200], "autor": str(meta.get("/Author") or "").strip()[:120],
                    "paginas": len(lector.pages), "cifrado": cifrado}
            return textos, info
        except PdfError:
            raise
        except Exception as e:
            ultimo = e
        else:
            ultimo = None
    else:
        ultimo = None
    try:                                                # sin pypdf (o si no pudo): el lector sencillo propio
        import internet_kira as ik
        with open(ruta, "rb") as f:
            texto = ik.pdf_a_texto(f.read(MAX_BYTES))
    except Exception as e:
        raise PdfError(f"No puedo leer este PDF: {ultimo or e}")
    return ([_limpiar(texto)] if texto else []), {"titulo": "", "autor": "", "paginas": 1 if texto else 0,
                                                    "cifrado": False}


MAX_PAGINAS_OCR = 20                 # OCR en el móvil va lento: por defecto las primeras 20 páginas


def texto_ocr(ruta, leer_imagen, al_progreso=None, max_paginas=MAX_PAGINAS_OCR, cancelado=None):
    """Para PDF ESCANEADOS (fotos, sin texto): saca la imagen de cada página con pypdf y la lee con OCR.
    `leer_imagen(ruta_png) -> texto` se inyecta (en el móvil, el Tesseract de Kira). Devuelve [texto por página].
    Va lento y pesa; por eso solo las primeras `max_paginas`. Lanza PdfError si no se puede ni empezar."""
    import os as _os
    import tempfile
    try:
        import pypdf
    except ImportError:
        raise PdfError("No puedo hacer OCR: falta pypdf.")
    try:
        lector = pypdf.PdfReader(ruta)
        if lector.is_encrypted:
            try:
                lector.decrypt("")
            except Exception:
                pass
        n_tot = min(len(lector.pages), int(max_paginas))
    except Exception as e:
        raise PdfError(f"No pude abrir el PDF para OCR: {e}")
    textos = []
    for i in range(n_tot):
        if cancelado and cancelado():
            break
        if al_progreso:
            al_progreso(i / max(1, n_tot), f"Leyendo con OCR la página {i + 1} de {n_tot}…")
        try:
            imgs = list(lector.pages[i].images)
        except Exception:
            imgs = []
        trozos_pag = []
        for j, img in enumerate(imgs[:4]):                  # como mucho 4 imágenes por página
            ext = _os.path.splitext(getattr(img, "name", "") or "")[1].lower() or ".png"
            tmp = _os.path.join(tempfile.gettempdir(), f"kira_ocr_{i}_{j}{ext}")
            t = ""
            try:
                with open(tmp, "wb") as f:
                    f.write(img.data)
                t = leer_imagen(tmp) or ""
            except Exception:
                t = ""
            finally:
                try:
                    _os.remove(tmp)
                except OSError:
                    pass
            if t.strip():
                trozos_pag.append(t.strip())
        textos.append(_limpiar("\n".join(trozos_pag)))
    return textos


def _limpiar(t):
    t = t.replace("\x00", "").replace("\r", "\n")
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)               # palabras partidas al final de línea
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def trozos_de(texto, largo=1800):
    return trozos(texto, largo)


def trozos(texto, largo=1800):
    """El texto en trozos de ~largo letras, cortando por párrafos o frases."""
    res, actual = [], ""
    for parrafo in re.split(r"\n\s*\n", texto):
        p = parrafo.strip()
        while len(p) > largo:
            corte = max(p.rfind(". ", 0, largo), p.rfind("\n", 0, largo))
            corte = corte + 1 if corte > largo // 3 else largo
            res.append((actual + " " + p[:corte]).strip() if actual else p[:corte].strip())
            actual, p = "", p[corte:].strip()
        if len(actual) + len(p) + 2 > largo and actual:
            res.append(actual.strip())
            actual = ""
        actual = (actual + "\n\n" + p) if actual else p
    if actual.strip():
        res.append(actual.strip())
    return res


_VACIAS = {"que", "como", "para", "por", "con", "los", "las", "del", "una", "uno", "unos", "unas", "sobre", "dice",
           "pdf", "documento", "este", "esta", "esto", "cual", "cuales", "donde", "cuando", "the", "and", "of"}


def palabras(t):
    return {w[:6] for w in re.findall(r"[a-z0-9ñ]{3,}", _plano(t)) if w not in _VACIAS}


# =====================================================================================
#  LA BIBLIOTECA
# =====================================================================================
class Biblioteca:
    def __init__(self, carpeta=None, abrir=None):
        self.carpeta = carpeta or carpeta_base()
        os.makedirs(self.carpeta, exist_ok=True)
        self.ruta_indice = os.path.join(self.carpeta, "indice.json")
        self._abrir = abrir
        self._lock = threading.Lock()
        try:
            with open(self.ruta_indice, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = []
        self.lista = [e for e in d if isinstance(e, dict) and os.path.isfile(os.path.join(self.carpeta, e.get("archivo", "")))] \
            if isinstance(d, list) else []

    # ---------- índice ----------
    def _guardar(self):
        tmp = self.ruta_indice + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.lista, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta_indice)

    def ruta(self, e):
        return os.path.join(self.carpeta, e["archivo"])

    def buscar_doc(self, quien=None):
        """El PDF por número («2»), por nombre («biología») o el último si no se dice. None si no está."""
        if not self.lista:
            return None
        q = str(quien or "").strip().lower()
        if not q or q in ("ultimo", "último", "el ultimo", "el último", "este", "ese"):
            return self.lista[-1]
        if q.isdigit():
            n = int(q)
            return next((e for e in self.lista if e["n"] == n), None)
        qp = palabras(q)
        mejor = max(self.lista, key=lambda e: len(qp & palabras(e["nombre"] + " " + e.get("titulo", ""))))
        return mejor if qp & palabras(mejor["nombre"] + " " + mejor.get("titulo", "")) else None

    def texto_lista(self):
        if not self.lista:
            return ("No tengo ningún PDF todavía. Dime «descarga este PDF: » y el enlace, o comparte un PDF con Kira "
                    "desde otra app.")
        lineas = [f"Mis PDF ({len(self.lista)}):"]
        for e in self.lista:
            lineas.append(f"{e['n']}. {e['nombre']} — {e['paginas']} pág., {e['bytes'] / 1e6:.1f} MB"
                          + (" (estudiado)" if e.get("estudiado") else "") + (" (sin texto: escaneado)" if not e.get("con_texto", True) else ""))
        lineas.append("Di «lee el pdf N», «resume el pdf N», «qué dice el pdf N sobre …», «estudia el pdf N», "
                      "«borra el pdf N» o «guarda el pdf N en descargas».")
        return "\n".join(lineas)

    # ---------- añadir ----------
    def anadir_archivo(self, origen, nombre=None, url="", mover=False):
        """Mete en la biblioteca un PDF que ya está en el móvil. Devuelve su ficha."""
        with open(origen, "rb") as f:
            cabeza = f.read(1024)
        if b"%PDF-" not in cabeza:
            raise PdfError("Eso no es un PDF.")
        h = hashlib.sha256()
        with open(origen, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        huella = h.hexdigest()[:16]
        repetido = next((e for e in self.lista if e.get("huella") == huella), None)
        if repetido is not None:
            if mover:
                try:
                    os.remove(origen)
                except OSError:
                    pass
            return dict(repetido, repetido=True)
        with self._lock:
            n = max([e["n"] for e in self.lista] or [0]) + 1
            archivo = f"{n:03d}_{huella}.pdf"
            destino = os.path.join(self.carpeta, archivo)
            if mover:
                os.replace(origen, destino)
            else:
                import shutil
                shutil.copyfile(origen, destino)
        try:
            textos, info = paginas_de(destino)
        except PdfError:
            os.remove(destino)
            raise
        e = {"n": n, "nombre": (nombre or info["titulo"] or "documento")[:80], "titulo": info["titulo"],
             "autor": info["autor"], "archivo": archivo, "url": url, "paginas": info["paginas"],
             "bytes": os.path.getsize(destino), "fecha": time.strftime("%Y-%m-%d %H:%M"), "huella": huella,
             "con_texto": sum(len(t) for t in textos) > 40, "estudiado": False}
        self._guardar_textos(e, textos)
        with self._lock:
            self.lista.append(e)
            self.lista = self.lista[-MAX_PDFS:]
            self._guardar()
        return e

    def descargar(self, url, nombre=None, progreso=None, cancelado=None):
        """Baja el PDF del enlace y lo guarda. Devuelve su ficha. Lanza PdfError."""
        import descargas_kira as dk
        url = url_de(url) or str(url or "").strip()
        if not re.match(r"^https?://", url, re.I):
            raise PdfError("Eso no parece un enlace (tiene que empezar por http:// o https://).")
        directo = enlace_directo(url)
        tmp = os.path.join(self.carpeta, f"descarga_{int(time.time() * 1000)}.parte_pdf")
        cab = {}

        def abrir(req, timeout=60):
            r = (self._abrir or dk.abrir_https)(req, timeout=timeout)
            try:
                cab.update(dict(r.headers.items()))
            except Exception:
                pass
            largo = cab.get("Content-Length") or cab.get("content-length")
            if largo and str(largo).isdigit() and int(largo) > MAX_BYTES:
                r.close()
                raise PdfError(f"Ese archivo es demasiado grande ({int(largo) / 1e6:.0f} MB; el máximo es "
                               f"{MAX_BYTES // 1024 // 1024} MB).")
            return r

        def bajar(direccion):
            if os.path.exists(tmp):
                os.remove(tmp)

            def prog(f, bajados, total):
                if bajados > MAX_BYTES:
                    raise dk.DescargaError(f"Ese archivo pasa de {MAX_BYTES // 1024 // 1024} MB: lo dejo.")
                if progreso:
                    progreso(f, bajados, total)
            try:
                dk.bajar(direccion, tmp, None, "el PDF", abrir=abrir, progreso=prog, cancelado=cancelado)
            except PdfError:
                raise
            except dk.DescargaError as e:
                raise PdfError(str(e).replace("Vuelve a pulsar: seguirá donde se quedó.", "Vuelve a pedírmelo."))
            with open(tmp, "rb") as f:
                return f.read(4096)

        try:
            cabeza = bajar(directo)
            if b"%PDF-" not in cabeza[:1024]:               # era una PÁGINA: se busca el PDF dentro
                with open(tmp, "rb") as f:
                    html = f.read(3_000_000)
                otro = pdf_en_pagina(html, directo)
                if not otro:
                    if b"accounts.google.com" in html or b"ServiceLogin" in html:
                        raise PdfError("Ese enlace de Google Drive es privado: compártelo como «Cualquier persona con "
                                       "el enlace» y vuelve a dármelo.")
                    raise PdfError("En ese enlace no hay un PDF (es una página web). Si quieres leerla, dime «lee » "
                                   "y el enlace.")
                cabeza = bajar(otro)
                directo = otro
                if b"%PDF-" not in cabeza[:1024]:
                    raise PdfError("El enlace de esa página tampoco era un PDF.")
            return self.anadir_archivo(tmp, nombre or nombre_de(directo, cab), url=url, mover=True)
        finally:
            for r in (tmp, tmp + ".parte"):
                try:
                    os.remove(r)
                except OSError:
                    pass

    # ---------- leer ----------
    def _ruta_textos(self, e):
        return self.ruta(e)[:-4] + ".txt.json"

    def _guardar_textos(self, e, textos):
        with open(self._ruta_textos(e), "w", encoding="utf-8") as f:
            json.dump(textos, f, ensure_ascii=False)

    def textos(self, e):
        try:
            with open(self._ruta_textos(e), encoding="utf-8") as f:
                t = json.load(f)
            if isinstance(t, list):
                return t
        except (OSError, ValueError):
            pass
        t, _info = paginas_de(self.ruta(e))
        self._guardar_textos(e, t)
        return t

    def ocr(self, e, leer_imagen, al_progreso=None, cancelado=None):
        """Lee con OCR un PDF escaneado y GUARDA el texto sacado (así la próxima vez ya está). Devuelve el texto por
        página (o [] si no sacó nada)."""
        textos = texto_ocr(self.ruta(e), leer_imagen, al_progreso=al_progreso, cancelado=cancelado)
        if sum(len(t) for t in textos) > 40:
            self._guardar_textos(e, textos)
            e["con_texto"] = True
            e["ocr"] = True
            with self._lock:
                self._guardar()
            return textos
        return []

    def pagina(self, e, n):
        t = self.textos(e)
        if not t:
            return ""
        n = max(1, min(int(n), len(t)))
        return t[n - 1]

    def buscar_en(self, e, consulta, n=5):
        """[(página, trozo con lo buscado)] donde aparece. Primero la frase exacta; si no, las palabras."""
        q = _plano(consulta).strip()
        qp = palabras(consulta)
        res = []
        for i, t in enumerate(self.textos(e), 1):
            pt = _plano(t)
            if q and q in pt:
                pos = pt.index(q)
                res.append((10.0, i, t[max(0, pos - 120): pos + len(q) + 160]))
            elif qp:
                comunes = qp & palabras(t)
                if comunes:
                    w = next(iter(comunes))
                    pos = pt.find(w)
                    res.append((len(comunes) / len(qp), i, t[max(0, pos - 120): pos + 220]))
        res.sort(key=lambda x: (-x[0], x[1]))
        return [(i, " ".join(s.split())) for _p, i, s in res[:n]]

    def contexto_para(self, e, pregunta, maximo=3500):
        """Los trozos del PDF que más tienen que ver con la pregunta, con su página (para dárselos al cerebro)."""
        qp = palabras(pregunta)
        candidatos = []
        for i, t in enumerate(self.textos(e), 1):
            for tz in trozos(t, 1200):
                puntos = len(qp & palabras(tz))
                if puntos:
                    candidatos.append((puntos, i, tz))
        candidatos.sort(key=lambda x: (-x[0], x[1]))
        sal, largo = [], 0
        for _p, i, tz in candidatos:
            if largo + len(tz) > maximo:
                break
            sal.append(f"[página {i}] {tz}")
            largo += len(tz)
        if not sal:                                    # nada encaja: el principio del documento
            ini = " ".join(self.textos(e)[:2])[:maximo]
            if ini:
                sal.append(f"[página 1] {ini}")
        return "\n\n".join(sal)

    # ---------- RAG: preguntar a TODOS tus documentos ----------
    def recuperar(self, pregunta, n=5, largo=1100):
        """Los n trozos de TODOS los PDF que mejor responden la pregunta (BM25): [(puntos, ficha, página, trozo)]."""
        import math
        q = palabras(pregunta)
        if not q:
            return []
        trozos = []
        for e in self.lista:
            try:
                for i, t in enumerate(self.textos(e), 1):
                    for tz in trozos_de(t, largo):
                        trozos.append((e, i, tz, palabras(tz)))
            except PdfError:
                continue
        if not trozos:
            return []
        media = sum(len(p) for *_x, p in trozos) / len(trozos)
        df = {}
        for *_x, p in trozos:
            for w in p:
                df[w] = df.get(w, 0) + 1
        res = []
        for e, i, tz, p in trozos:
            punt = 0.0
            for w in q & p:
                idf = math.log(1 + (len(trozos) - df[w] + 0.5) / (df[w] + 0.5))
                f = _plano(tz).count(w)
                punt += idf * f * 2.5 / (f + 1.5 * (0.25 + 0.75 * len(p) / max(1.0, media)))
            if punt > 0:
                res.append((punt, e, i, tz))
        res.sort(key=lambda x: -x[0])
        return res[:n]

    # ---------- gestionar ----------
    def renombrar(self, e, nombre):
        nombre = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", " ", str(nombre or "")).strip()[:80]
        if not nombre:
            raise PdfError("Dime el nombre nuevo.")
        with self._lock:
            e["nombre"] = nombre
            self._guardar()
        return e

    def borrar(self, e):
        with self._lock:
            self.lista = [x for x in self.lista if x["n"] != e["n"]]
            self._guardar()
        for r in (self.ruta(e), self._ruta_textos(e)):
            try:
                os.remove(r)
            except OSError:
                pass

    def marcar_estudiado(self, e):
        with self._lock:
            e["estudiado"] = True
            self._guardar()


# =====================================================================================
#  QUÉ SE PIDE
# =====================================================================================
_N = r"(?:el\s+)?(?:pdf|documento|libro)\s*(?:n[uú]mero\s+)?(?P<doc>\d+|[^\s].*?)?"


def interpretar(texto):
    """{'accion', ...} si la frase es una orden de la biblioteca de PDF; si no, None.
    acciones: descargar(url) · lista · leer(doc, pagina) · resumir(doc) · buscar(doc, consulta) ·
              preguntar(doc, pregunta) · estudiar(doc) · borrar(doc) · renombrar(doc, nombre) · exportar(doc) · abrir(doc)"""
    t = " ".join(str(texto or "").split()).strip(" ¿?¡!")
    t = re.sub(r"^(?:oye\s+|hola\s+)?kira\b[\s,:;.]*", "", t, flags=re.I)
    b = _plano(t)
    url = url_de(t)
    if url and (re.search(r"\b(descarga|descargate|descargame|baja(?:te|me)?|bajate|guarda(?:me)?|gu[aá]rdate|"
                          r"a[nñ]ade|anade|coge|consigue|trae(?:me)?|lee(?:me)?|abre)\b", b)
                and (re.search(r"\bpdf\b|\bdocumento\b|\blibro\b|\barchivo\b|\bapuntes\b", b)
                     or url.lower().split("?")[0].endswith(".pdf"))):
        if re.match(r"^(?:lee(?:me)?|abre)\b", b) and not url.lower().split("?")[0].endswith(".pdf") \
                and not re.search(r"\bpdf\b", b):
            return None                                 # «lee https://…» de una página: es de internet
        return {"accion": "descargar", "url": url}
    if re.match(r"^(?:(?:abre|ensename|muestrame|ver|ve\s+a|llevame\s+a)\s+)?(?:mis|los|tus|lista\s+de\s+(?:mis\s+)?)\s*"
                r"(?:pdfs?|documentos\s+pdf)\s*$", b) or \
            b in ("biblioteca de pdf", "mi biblioteca", "mis documentos pdf", "que pdf tienes", "que pdfs tienes"):
        return {"accion": "lista"}
    m = re.match(r"^(?:preg[uú]nta(?:le)?\s+a\s+(?:mis|tus|los)\s+(?:documentos|pdfs?|apuntes|libros)|"
                 r"busca\s+en\s+(?:mis|tus|los)\s+(?:documentos|pdfs?|apuntes|libros)|"
                 r"qu[eé]\s+dicen\s+(?:mis|tus|los)\s+(?:documentos|pdfs?|apuntes|libros)\s+(?:sobre|de|del|acerca\s+de)|"
                 r"seg[uú]n\s+(?:mis|tus|los)\s+(?:documentos|pdfs?|apuntes|libros))\s*[:,]?\s*(?P<q>.+)$", t, re.I)
    if m:
        return {"accion": "rag", "pregunta": m.group("q").strip(" ¿?")}
    if not re.search(r"\b(?:pdf|documento\s+\d+|libro\s+\d+)\b", b):
        return None
    m = re.match(r"^(?:lee(?:me)?|leer)\s+(?:la\s+)?p[aá]gina\s+(?P<p>\d+)\s+(?:del?\s+)?" + _N + "$", t, re.I)
    if m:
        return {"accion": "leer", "doc": (m.group("doc") or "").strip(), "pagina": int(m.group("p"))}
    m = re.match(r"^(?:lee(?:me)?|leer)\s+" + _N + r"(?:\s*,?\s*p[aá]gina\s+(?P<p>\d+))?$", t, re.I)
    if m:
        return {"accion": "leer", "doc": (m.group("doc") or "").strip(), "pagina": int(m.group("p") or 1)}
    m = re.match(r"^(?:abre|ens[eé][nñ]ame|mu[eé]strame)\s+" + _N + "$", t, re.I)
    if m:
        return {"accion": "abrir", "doc": (m.group("doc") or "").strip()}
    m = re.match(r"^(?:res[uú]me(?:me)?|resumen\s+de[l]?|haz(?:me)?\s+un\s+resumen\s+del?)\s+" + _N + "$", t, re.I)
    if m:
        return {"accion": "resumir", "doc": (m.group("doc") or "").strip()}
    m = re.match(r"^busca\s+(?P<q>.+?)\s+en\s+" + _N + "$", t, re.I)
    if m:
        return {"accion": "buscar", "doc": (m.group("doc") or "").strip(), "consulta": m.group("q").strip(" «»\"")}
    m = re.match(r"^(?:qu[eé]\s+dice|qu[eé]\s+pone|qu[eé]\s+cuenta)\s+(?:el\s+)?(?:pdf|documento|libro)\s*(?P<doc>\d+)?"
                 r"\s+(?:sobre|de|del|acerca\s+de|:)\s*(?P<q>.+)$", t, re.I)
    if m:
        return {"accion": "preguntar", "doc": (m.group("doc") or "").strip(), "pregunta": m.group("q").strip()}
    m = re.match(r"^(?:preg[uú]ntale\s+al|pregunta\s+al)\s+(?:pdf|documento)\s*(?P<doc>\d+)?\s*:?\s*(?P<q>.+)$", t, re.I)
    if m:
        return {"accion": "preguntar", "doc": (m.group("doc") or "").strip(), "pregunta": m.group("q").strip()}
    m = re.match(r"^(?:estudia|aprende(?:te)?|memoriza)\s+" + _N + "$", t, re.I)
    if m:
        return {"accion": "estudiar", "doc": (m.group("doc") or "").strip()}
    m = re.match(r"^(?:borra|elimina|quita)\s+" + _N + "$", t, re.I)
    if m:
        return {"accion": "borrar", "doc": (m.group("doc") or "").strip()}
    m = re.match(r"^(?:renombra|cambia\s+(?:el\s+)?nombre\s+(?:a[l]?|del?))\s+(?:el\s+)?(?:pdf|documento)\s*(?P<doc>\d+)?\s+"
                 r"(?:a|como|por)\s+(?P<nombre>.+)$", t, re.I)
    if m:
        return {"accion": "renombrar", "doc": (m.group("doc") or "").strip(), "nombre": m.group("nombre").strip(" «»\"")}
    m = re.match(r"^(?:guarda|exporta|copia|pasa)\s+" + _N + r"\s+(?:en|a)\s+(?:las?\s+|mis\s+)?descargas$", t, re.I)
    if m:
        return {"accion": "exportar", "doc": (m.group("doc") or "").strip()}
    return None
