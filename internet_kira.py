# -*- coding: utf-8 -*-
"""
internet_kira.py - Kira BUSCA y LEE en internet cuando se lo pides (solo librería estándar, sin claves ni pagos).

  «Kira, busca en internet cómo plantar tomates»      -> web: DuckDuckGo (+ Wikipedia)
  «Kira, busca código de un servidor web en Python»   -> código: Stack Overflow, GitHub y la web
  «Kira, busca documentos sobre la fotosíntesis»      -> documentos: PDF, manuales y apuntes
  «lee el 2» / «resume el 2» / «guarda el 2» / «abre el 2 en el editor» / «ábrelo en el navegador»
  «Kira, estudia en internet la Revolución Francesa»  -> lee los mejores resultados y guarda lo aprendido en su baúl

Leer: páginas web (solo el texto y los bloques de código, sin anuncios ni menús), código de GitHub (README y archivos),
texto plano y PDF sencillos.
Seguridad: lo que se baja es TEXTO: nunca se ejecuta (el código va al editor, en modo seguro, y lo ejecutas tú), se
recorta y no se mezcla con las instrucciones de Kira. Tamaño máximo por página y tiempo máximo por conexión.
Honesto: DuckDuckGo puede frenar las búsquedas automáticas si se hacen muchas seguidas; entonces Kira usa la Wikipedia,
Stack Overflow y GitHub, y lo dice. Algunos PDF (escaneados o con fuentes raras) no se pueden leer.
"""
import gzip
import html
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zlib
from html.parser import HTMLParser

MAX_BYTES = 3_000_000
MAX_TEXTO = 40_000
AGENTE = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"


class InternetError(RuntimeError):
    pass


def _abrir(req, timeout=20):
    import red_kira
    return red_kira.abrir(req, timeout=timeout)


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _limpio(t, n=400):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", str(t or "")))).strip()[:n]


def dominio(url):
    try:
        d = urllib.parse.urlsplit(url).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except ValueError:
        return ""


# =====================================================================================
#  ÓRDENES
# =====================================================================================
_BUSCA = re.compile(
    r"^(?:por\s+favor\s+)?(?:b[uú]scame|busca|buscar|investiga|averigua|consulta)\s+(?P<resto>.+)$", re.I | re.S)
_ESTUDIA = re.compile(r"^(?:estudia|aprende)\s+(?:en|de|por)\s+(?:internet|la\s+web|la\s+red)\s+(?:sobre\s+|de\s+)?(?P<q>.+)$",
                      re.I | re.S)
_RESULTADO = re.compile(
    r"^(?P<acc>l[eé]e(?:me)?|abre|ens[eé][ñn]ame|resume(?:me)?|res[uú]meme|guarda|aprende\s+(?:de|del)|"
    r"[aá]brelo\s+en\s+el\s+navegador|abre\s+en\s+el\s+navegador)\s+(?:el\s+)?(?:resultado\s+|enlace\s+|n[uú]mero\s+)?"
    r"(?P<n>\d{1,2}|primero|segundo|tercero|cuarto|quinto)(?P<editor>\s+en\s+el\s+editor)?(?P<nav>\s+en\s+el\s+navegador)?$",
    re.I)
_ORDINAL = {"primero": 1, "segundo": 2, "tercero": 3, "cuarto": 4, "quinto": 5}
_LEER_URL = re.compile(r"^(?:l[eé]e(?:me)?|abre|resume(?:me)?|guarda)\s+(?:esta\s+|la\s+)?(?:p[aá]gina|web|enlace|url)?\s*:?\s*"
                       r"(?P<url>https?://\S+)$", re.I)


def interpretar(texto):
    """Qué se pide. Devuelve un dict o None:
      {'accion': 'buscar', 'tipo': 'web'|'codigo'|'docs', 'consulta': str}
      {'accion': 'estudiar', 'consulta': str}
      {'accion': 'leer'|'resumir'|'guardar'|'editor'|'navegador', 'n': int}  (de los últimos resultados)
      {'accion': 'leer'|'resumir'|'guardar', 'url': str}"""
    t = " ".join(str(texto or "").split()).strip(" .!¡?¿")
    if not t:
        return None
    m = _LEER_URL.match(t)
    if m:
        acc = _plano(t.split()[0])
        return {"accion": "resumir" if acc.startswith("resum") else ("guardar" if acc == "guarda" else "leer"),
                "url": m.group("url")}
    m = _ESTUDIA.match(t)
    if m:
        return {"accion": "estudiar", "consulta": m.group("q").strip(" ,.:")[:200]}
    m = _RESULTADO.match(t)
    if m:
        n = m.group("n").lower()
        n = int(n) if n.isdigit() else _ORDINAL[_plano(n)]
        acc = _plano(m.group("acc"))
        if m.group("editor"):
            accion = "editor"
        elif m.group("nav") or "navegador" in acc:
            accion = "navegador"
        elif acc.startswith("resum"):
            accion = "resumir"
        elif acc.startswith(("guarda", "aprende")):
            accion = "guardar"
        else:
            accion = "leer"
        return {"accion": accion, "n": n}
    m = _BUSCA.match(t)
    if not m:
        return None
    resto = m.group("resto").strip(" ,.:")
    p = _plano(resto)
    if re.match(r"^(?:en\s+)?(?:tus|mis)\s+(?:recuerdos|notas)\b", p) or re.match(r"^en\s+google\b", p):
        return None                                        # recuerdos: el baúl; «en google»: el navegador
    tipo = "web"
    if re.search(r"\b(codigo|ejemplos?\s+de\s+codigo|script|programa(?:r|cion)?\s+en|en\s+python|en\s+javascript|"
                 r"funcion\s+(?:de|que|para)|libreria|repositorio|github|stack\s*overflow|snippet)\b", p):
        tipo = "codigo"
    elif re.search(r"\b(documentos?|pdfs?|apuntes|manual(?:es)?|libros?\s+(?:de|sobre)|articulos?\s+cientificos?|"
                   r"papers?|tesis|temario)\b", p):
        tipo = "docs"
    consulta = re.sub(r"^(?:en\s+(?:internet|la\s+web|la\s+red|linea)|online|por\s+internet)\s+", "", resto, flags=re.I)
    consulta = re.sub(r"\s+(?:en\s+(?:internet|la\s+web|la\s+red)|online|por\s+internet)$", "", consulta, flags=re.I)
    consulta = re.sub(r"^(?:informaci[oó]n|info|algo)\s+(?:sobre|de|acerca\s+de)\s+", "", consulta, flags=re.I)
    consulta = re.sub(r"^(?:c[oó]digo|ejemplos?\s+de\s+c[oó]digo|documentos?|pdfs?|apuntes|manual(?:es)?)\s+"
                      r"(?:de|sobre|para|del?)\s+", "", consulta, flags=re.I)
    consulta = consulta.strip(" ,.:")
    if len(consulta) < 2:
        return None
    return {"accion": "buscar", "tipo": tipo, "consulta": consulta[:200]}


# =====================================================================================
#  HTML -> TEXTO (sin menús, anuncios ni scripts), con los bloques de código aparte
# =====================================================================================
class _HtmlATexto(HTMLParser):
    FUERA = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form", "iframe", "button",
             "select", "template", "canvas"}
    BLOQUE = {"p", "div", "section", "article", "li", "tr", "br", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote",
              "dd", "dt", "table", "ul", "ol", "main", "figcaption"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes, self.codigos, self.titulo = [], [], ""
        self._fuera, self._pre, self._en_titulo, self._codigo = 0, 0, False, []

    def handle_starttag(self, tag, attrs):
        if tag in self.FUERA:
            self._fuera += 1
            return
        if tag == "title":
            self._en_titulo = True
        if self._fuera:
            return
        if tag == "pre":
            self._pre += 1
            self._codigo = []
        elif tag in ("h1", "h2", "h3"):
            self.partes.append("\n\n## ")
        elif tag == "li":
            self.partes.append("\n- ")
        elif tag in self.BLOQUE:
            self.partes.append("\n")

    def handle_endtag(self, tag):
        if tag in self.FUERA:
            self._fuera = max(0, self._fuera - 1)
            return
        if tag == "title":
            self._en_titulo = False
        if self._fuera:
            return
        if tag == "pre" and self._pre:
            self._pre -= 1
            codigo = "".join(self._codigo).strip("\n")
            if codigo.strip():
                self.codigos.append(codigo)
                self.partes.append("\n```\n" + codigo + "\n```\n")
            self._codigo = []
        elif tag in self.BLOQUE:
            self.partes.append("\n")

    def handle_data(self, data):
        if self._en_titulo:
            self.titulo += data
            return
        if self._fuera:
            return
        if self._pre:
            self._codigo.append(data)
        else:
            self.partes.append(data)

    def texto(self):
        t = "".join(self.partes)
        bloques = re.split(r"(\n```\n.*?\n```\n)", t, flags=re.S)
        salida = []
        for b in bloques:
            if b.startswith("\n```"):
                salida.append(b)
            else:
                b = re.sub(r"[ \t\r\f\v]+", " ", b)
                b = re.sub(r" *\n *", "\n", b)
                b = re.sub(r"\n{3,}", "\n\n", b)
                salida.append(b)
        return "".join(salida).strip()


def html_a_texto(contenido):
    """(titulo, texto, [bloques de código]) de una página HTML."""
    p = _HtmlATexto()
    try:
        p.feed(contenido)
        p.close()
    except Exception:
        pass
    texto = p.texto()
    # quita líneas sueltas muy cortas repetidas (restos de menús): se quedan las frases y los títulos
    lineas = [l for l in texto.split("\n")]
    vistas, limpias = set(), []
    for l in lineas:
        clave = l.strip().lower()
        if clave and len(clave) < 40 and clave in vistas and not clave.startswith("```"):
            continue
        vistas.add(clave)
        limpias.append(l)
    return " ".join(p.titulo.split())[:200], "\n".join(limpias).strip()[:MAX_TEXTO], p.codigos[:20]


# =====================================================================================
#  PDF sencillo -> texto (sin librerías: solo los textos de los flujos comprimidos con zlib)
# =====================================================================================
_PDF_STREAM = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
_PDF_TEXTO = re.compile(rb"\((?:\\.|[^\\)])*\)\s*(?:Tj|'|\")|\[(?:[^\]]*)\]\s*TJ|T\*|Td|TD|ET", re.S)
_PDF_CADENA = re.compile(rb"\((?:\\.|[^\\)])*\)", re.S)


def _pdf_cadena(b):
    b = b[1:-1]
    sal, i = bytearray(), 0
    escapes = {ord("n"): b"\n", ord("r"): b"\r", ord("t"): b"\t", ord("b"): b"", ord("f"): b"", ord("("): b"(",
               ord(")"): b")", ord("\\"): b"\\"}
    while i < len(b):
        c = b[i]
        if c == 0x5C and i + 1 < len(b):
            n = b[i + 1]
            if n in escapes:
                sal += escapes[n]
                i += 2
                continue
            m = re.match(rb"[0-7]{1,3}", b[i + 1:i + 4])
            if m:
                sal.append(int(m.group(0), 8) & 0xFF)
                i += 1 + len(m.group(0))
                continue
            i += 1
            continue
        sal.append(c)
        i += 1
    return sal.decode("latin-1")


def pdf_a_texto(datos):
    """Texto de un PDF sencillo. Devuelve '' si no se puede (escaneado, fuentes especiales, cifrado)."""
    trozos = []
    for m in _PDF_STREAM.finditer(datos[:MAX_BYTES]):
        crudo = m.group(1)
        try:
            contenido = zlib.decompress(crudo)
        except zlib.error:
            contenido = crudo
        if b"Tj" not in contenido and b"TJ" not in contenido:
            continue
        for op in _PDF_TEXTO.finditer(contenido):
            o = op.group(0)
            if o in (b"T*", b"Td", b"TD", b"ET"):
                if trozos and not trozos[-1].endswith("\n"):
                    trozos.append("\n")
                continue
            for c in _PDF_CADENA.findall(o):
                trozos.append(_pdf_cadena(c))
            if o.endswith(b"TJ"):
                trozos.append("")
    texto = re.sub(r"[ \t]+", " ", "".join(trozos))
    texto = re.sub(r"\n\s*\n+", "\n\n", texto).strip()
    letras = sum(ch.isalpha() for ch in texto)
    if len(texto) < 40 or letras < 0.5 * len(texto.replace(" ", "").replace("\n", "")):
        return ""
    return texto[:MAX_TEXTO]


# =====================================================================================
#  RESULTADOS DE BUSCADORES
# =====================================================================================
class _Duck(HTMLParser):
    """Resultados de la página HTML de DuckDuckGo (html.duckduckgo.com y lite.duckduckgo.com)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.res, self._en, self._snip = [], None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        clase = a.get("class", "") or ""
        if tag == "a" and ("result__a" in clase or "result-link" in clase):
            self._en = {"titulo": "", "url": a.get("href", ""), "resumen": ""}
            self.res.append(self._en)
        elif ("result__snippet" in clase or "result-snippet" in clase) and self.res:
            self._snip = self.res[-1]

    def handle_endtag(self, tag):
        if tag == "a" and self._en is not None:
            self._en = None
        elif tag in ("a", "td", "div") and self._snip is not None:
            self._snip = None

    def handle_data(self, data):
        if self._en is not None:
            self._en["titulo"] += data
        elif self._snip is not None:
            self._snip["resumen"] += data


def url_real(href):
    """DuckDuckGo envuelve los enlaces (/l/?uddg=…): saca la dirección de verdad. None si es un anuncio."""
    if not href:
        return None
    if href.startswith("//"):
        href = "https:" + href
    partes = urllib.parse.urlsplit(href)
    if partes.netloc.endswith("duckduckgo.com"):
        q = urllib.parse.parse_qs(partes.query)
        if "uddg" in q:
            return q["uddg"][0]
        return None                                        # anuncios (y.js) u otras cosas de DuckDuckGo
    return href if partes.scheme in ("http", "https") else None


def resultados_duck(contenido):
    p = _Duck()
    try:
        p.feed(contenido)
    except Exception:
        pass
    sal, vistas = [], set()
    for r in p.res:
        url = url_real(r["url"])
        if not url or url in vistas:
            continue
        vistas.add(url)
        sal.append({"titulo": _limpio(r["titulo"], 160) or dominio(url), "url": url,
                    "resumen": _limpio(r["resumen"], 300), "fuente": dominio(url)})
    return sal


# =====================================================================================
#  EL BUSCADOR
# =====================================================================================
class Internet:
    def __init__(self, carpeta, abrir=_abrir, reloj=time.time):
        self.carpeta = carpeta
        self._abrir, self._reloj = abrir, reloj
        self.ultimos, self.consulta, self.tipo = [], "", "web"
        self.pagina = None                                   # la última página leída
        self.avisos = []
        self._ultima_duck = -10.0

    # ---------- red ----------
    def _pedir(self, url, datos=None, cabeceras=None, maximo=MAX_BYTES, timeout=20):
        """(bytes, content_type, url_final)."""
        h = {"User-Agent": AGENTE, "Accept-Language": "es-ES,es;q=0.9,en;q=0.6", "Accept-Encoding": "gzip"}
        h.update(cabeceras or {})
        req = urllib.request.Request(url, data=datos, headers=h, method="POST" if datos else "GET")
        try:
            with self._abrir(req, timeout=timeout) as r:
                crudo = r.read(maximo + 1)
                tipo = (r.headers.get("Content-Type") or "") if getattr(r, "headers", None) is not None else ""
                codif = (r.headers.get("Content-Encoding") or "") if getattr(r, "headers", None) is not None else ""
                final = getattr(r, "url", url) or url
        except urllib.error.HTTPError as e:
            raise InternetError(f"La web respondió {e.code}.")
        except Exception as e:
            raise InternetError(f"No pude conectarme ({str(e)[:120]}). ¿Hay internet?")
        if len(crudo) > maximo:
            crudo = crudo[:maximo]
        if "gzip" in codif.lower() or crudo[:2] == b"\x1f\x8b":
            try:
                crudo = gzip.decompress(crudo)
            except (OSError, EOFError):
                pass
        return crudo, tipo.lower(), final

    @staticmethod
    def _texto(crudo, tipo=""):
        m = re.search(r"charset=([\w-]+)", tipo)
        for cod in ([m.group(1)] if m else []) + ["utf-8", "latin-1"]:
            try:
                return crudo.decode(cod)
            except (LookupError, UnicodeDecodeError):
                continue
        return crudo.decode("utf-8", "replace")

    def _json(self, url, cabeceras=None):
        crudo, tipo, _ = self._pedir(url, cabeceras=cabeceras, maximo=2_000_000)
        try:
            return json.loads(self._texto(crudo, tipo))
        except ValueError:
            raise InternetError("Respuesta rara del servidor.")

    # ---------- buscadores ----------
    def duck(self, consulta, n=8):
        espera = 1.2 - (self._reloj() - self._ultima_duck)  # sin prisas: muchas seguidas y DuckDuckGo frena
        if espera > 0:
            time.sleep(espera)
        self._ultima_duck = self._reloj()
        q = urllib.parse.urlencode({"q": consulta, "kl": "es-es"})
        for url in ("https://html.duckduckgo.com/html/?" + q, "https://lite.duckduckgo.com/lite/?" + q):
            try:
                crudo, tipo, _ = self._pedir(url, maximo=1_500_000)
            except InternetError:
                continue
            res = resultados_duck(self._texto(crudo, tipo))
            if res:
                return res[:n]
        return []

    def wikipedia(self, consulta, n=3):
        q = urllib.parse.urlencode({"action": "query", "list": "search", "srsearch": consulta, "format": "json",
                                    "srlimit": n, "utf8": 1})
        d = self._json("https://es.wikipedia.org/w/api.php?" + q)
        sal = []
        for x in (d.get("query", {}) or {}).get("search", [])[:n]:
            t = str(x.get("title", ""))
            if t:
                sal.append({"titulo": t + " (Wikipedia)", "fuente": "es.wikipedia.org",
                            "url": "https://es.wikipedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_")),
                            "resumen": _limpio(x.get("snippet", ""), 300)})
        return sal

    def stackoverflow(self, consulta, n=4, sitio="stackoverflow"):
        q = urllib.parse.urlencode({"order": "desc", "sort": "relevance", "q": consulta, "site": sitio,
                                    "pagesize": n})
        d = self._json("https://api.stackexchange.com/2.3/search/advanced?" + q)
        sal = []
        for x in d.get("items", [])[:n]:
            etiquetas = ", ".join(x.get("tags", [])[:4])
            sal.append({"titulo": _limpio(x.get("title", ""), 160), "url": str(x.get("link", "")),
                        "fuente": "stackoverflow.com" if sitio == "stackoverflow" else f"{sitio}.com",
                        "resumen": (("respondida · " if x.get("is_answered") else "") +
                                    f"{x.get('score', 0)} votos" + (f" · {etiquetas}" if etiquetas else ""))})
        return [r for r in sal if r["url"].startswith("https://")]

    def github(self, consulta, n=4):
        q = urllib.parse.urlencode({"q": consulta, "sort": "stars", "per_page": n})
        d = self._json("https://api.github.com/search/repositories?" + q,
                       cabeceras={"Accept": "application/vnd.github+json"})
        sal = []
        for x in d.get("items", [])[:n]:
            sal.append({"titulo": str(x.get("full_name", "")) + " (GitHub)", "url": str(x.get("html_url", "")),
                        "fuente": "github.com",
                        "resumen": _limpio(x.get("description", ""), 220) +
                        f" · ★ {x.get('stargazers_count', 0)}" + (f" · {x['language']}" if x.get("language") else "")})
        return [r for r in sal if r["url"].startswith("https://github.com/")]

    def buscar(self, consulta, tipo="web", n=8):
        """Lista de resultados {'titulo', 'url', 'resumen', 'fuente'}. Guarda los últimos para «lee el 2»."""
        consulta = " ".join(str(consulta or "").split())[:200]
        if len(consulta) < 2:
            raise InternetError("Dime qué quieres que busque.")
        self.avisos = []
        res = []

        def intentar(fuente, *a):
            try:
                return fuente(*a)
            except InternetError as e:
                self.avisos.append(str(e))
                return []
        if tipo == "codigo":
            res += intentar(self.stackoverflow, consulta, 4)
            res += intentar(self.github, consulta, 3)
            res += intentar(self.duck, consulta + " ejemplo código", 4)
        elif tipo == "docs":
            docs = intentar(self.duck, consulta + " pdf apuntes", n)
            res += sorted(docs, key=lambda r: not r["url"].lower().split("?")[0].endswith(".pdf"))  # PDF primero
            res += intentar(self.wikipedia, consulta, 1)
        else:
            web = intentar(self.duck, consulta, n)
            wiki = intentar(self.wikipedia, consulta, 2)
            if not web:
                self.avisos.append("El buscador general no ha respondido ahora: te enseño lo que hay en la Wikipedia.")
            res = web[:2] + [w for w in wiki if w["url"] not in {r["url"] for r in web}][:1] + web[2:] if web else wiki
        vistos, unicos = set(), []
        for r in res:
            if r["url"] and r["url"] not in vistos:
                vistos.add(r["url"])
                unicos.append(r)
        if not unicos:
            raise InternetError("No he encontrado nada" + (f" ({self.avisos[0]})" if self.avisos else "") + ".")
        self.ultimos, self.consulta, self.tipo = unicos[:n], consulta, tipo
        return self.ultimos

    def resultado(self, n):
        if not self.ultimos:
            raise InternetError("Primero dime qué busco («Kira, busca en internet …»).")
        if not 1 <= n <= len(self.ultimos):
            raise InternetError(f"Solo tengo {len(self.ultimos)} resultado(s).")
        return self.ultimos[n - 1]

    # ---------- leer ----------
    @staticmethod
    def _github(url):
        """Las páginas de GitHub se leen mejor en crudo: README del repositorio o el archivo tal cual."""
        p = urllib.parse.urlsplit(url)
        if p.netloc not in ("github.com", "www.github.com"):
            return None
        trozos = [x for x in p.path.split("/") if x]
        if len(trozos) == 2:
            return f"https://api.github.com/repos/{trozos[0]}/{trozos[1]}/readme", {"Accept": "application/vnd.github.raw"}
        if len(trozos) >= 5 and trozos[2] == "blob":
            return ("https://raw.githubusercontent.com/" + "/".join([trozos[0], trozos[1]] + trozos[3:]), {})
        return None

    def leer(self, url):
        """{'url', 'titulo', 'texto', 'codigos', 'tipo'} de una página (o PDF, o código)."""
        if not re.match(r"^https?://", str(url or "")):
            raise InternetError("Esa dirección no es una página web.")
        gh = self._github(url)
        destino, cab = gh if gh else (url, None)
        try:
            crudo, tipo, final = self._pedir(destino, cabeceras=cab)
        except InternetError:
            if not gh:
                raise
            gh, destino = None, url                         # sin README: la página normal del repositorio
            crudo, tipo, final = self._pedir(url)
        ext = os.path.splitext(urllib.parse.urlsplit(final).path)[1].lower()
        if "pdf" in tipo or crudo[:5] == b"%PDF-":
            texto = pdf_a_texto(crudo)
            if not texto:
                raise InternetError("Es un PDF que no puedo leer en el móvil (escaneado o con fuentes especiales). "
                                    "Ábrelo en el navegador.")
            pag = {"url": url, "titulo": os.path.basename(urllib.parse.urlsplit(url).path) or dominio(url),
                   "texto": texto, "codigos": [], "tipo": "pdf"}
        elif "html" in tipo or crudo.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")):
            titulo, texto, codigos = html_a_texto(self._texto(crudo, tipo))
            if len(texto) < 30 and not codigos:
                raise InternetError("Esa página no tiene texto que pueda leer (puede que necesite el navegador).")
            pag = {"url": url, "titulo": titulo or dominio(url), "texto": texto, "codigos": codigos, "tipo": "web"}
        elif tipo.startswith(("text/", "application/json", "application/javascript")) or gh or \
                ext in (".py", ".js", ".md", ".txt", ".json", ".c", ".java", ".kt", ".sh", ".css"):
            texto = self._texto(crudo, tipo)[:MAX_TEXTO]
            es_codigo = ext not in (".md", ".txt", "") or (gh and not destino.endswith("/readme"))
            pag = {"url": url, "titulo": os.path.basename(urllib.parse.urlsplit(url).path) or dominio(url),
                   "texto": texto, "codigos": [texto] if es_codigo else re.findall(r"```\w*\n(.*?)```", texto, re.S)[:20],
                   "tipo": "codigo" if es_codigo else "texto"}
        else:
            raise InternetError(f"No sé leer ese tipo de archivo ({tipo or 'desconocido'}). Ábrelo en el navegador.")
        self.pagina = pag
        return pag

    # ---------- textos para enseñar ----------
    def texto_resultados(self, res=None):
        res = res if res is not None else self.ultimos
        cab = {"codigo": "Código", "docs": "Documentos"}.get(self.tipo, "Resultados")
        lineas = [f"{cab} de «{self.consulta}»:"]
        for i, r in enumerate(res, 1):
            lineas.append(f"{i}. {r['titulo']} — {r['fuente']}" + (f"\n   {r['resumen']}" if r.get("resumen") else ""))
        if self.avisos:
            lineas.append("(" + self.avisos[0] + ")")
        lineas.append("Di «lee el 2», «resume el 2», «guarda el 2» (lo aprendo)" +
                      (", «abre el 2 en el editor»" if self.tipo == "codigo" else "") + " o «abre el 2 en el navegador».")
        return "\n".join(lineas)

    @staticmethod
    def texto_pagina(pag, maximo=2500):
        t = pag["texto"]
        corte = t[:maximo]
        return (f"{pag['titulo']}\n{pag['url']}\n\n{corte}" + ("…\n\n(sigue: «resume» para el resumen)" if len(t) > maximo
                                                               else "") +
                (f"\n\nTiene {len(pag['codigos'])} bloque(s) de código: «abre en el editor»." if pag["codigos"] else ""))

    @staticmethod
    def codigo_de(pag):
        """El código de la página para el editor (el bloque más largo; si es un archivo de código, entero)."""
        cods = pag.get("codigos") or []
        if not cods:
            return ""
        return max(cods, key=len) if pag.get("tipo") != "codigo" else cods[0]

    def es_orden(self, texto):
        return interpretar(texto) is not None
