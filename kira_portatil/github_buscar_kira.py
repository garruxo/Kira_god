# -*- coding: utf-8 -*-
"""
github_buscar_kira.py - v3.79: «instala X de github» SOLO con el nombre → Kira busca X en GitHub, te enseña los
proyectos más conocidos con ese nombre (estrellas, de quién es, qué hace, si está abandonado) y TÚ eliges cuál.
Nunca instala el primero que sale: hay muchos proyectos con nombres parecidos (y alguno con mala idea).

Después de elegir, sigue el camino de siempre: sus versiones publicadas («¿cuál quieres?»), análisis antes de
instalar, icono en el escritorio y su ventanita de órdenes.

Y «instala lo que he descargado» → el último archivo de tu carpeta Descargas (lo que bajaste tú con el navegador).

Puro salvo `traer_json` (la API de GitHub) y la carpeta de descargas, que se inyectan en las pruebas.
"""
import json
import os
import re
import time
import unicodedata
import urllib.parse

MAX_OPCIONES = 6
DURA = 30 * 60


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# ------------------------------------------------------------------ la ORDEN
_ORDEN = [
    re.compile(r"^(?:kira[, ]+)?(?:inst[aá]la(?:me)?|desc[aá]rga(?:me)?|b[aá]ja(?:me)?|consigue(?:me)?)\s+"
               r"(?:el\s+programa\s+|la\s+app\s+|la\s+aplicaci[oó]n\s+)?(?P<n>.+?)\s+(?:de|desde|en)\s+github$", re.I),
    re.compile(r"^(?:kira[, ]+)?(?:inst[aá]la(?:me)?|desc[aá]rga(?:me)?)\s+(?:de|desde)\s+github\s+(?P<n>.+)$", re.I),
    re.compile(r"^(?:kira[, ]+)?b[uú]sca(?:me)?\s+(?P<n>.+?)\s+en\s+github\s+y\s+(?:inst[aá]la|desc[aá]rga)\w*$", re.I),
    re.compile(r"^(?:kira[, ]+)?b[uú]sca(?:me)?\s+en\s+github\s+(?P<n>.+?)\s+y\s+(?:inst[aá]la|desc[aá]rga)\w*$", re.I),
]


def es_orden(texto):
    """El NOMBRE que hay que buscar en GitHub, o None. No se mete con un enlace ni con «dueño/proyecto» (esos se
    instalan directo, como antes)."""
    t = re.sub(r"\s+", " ", str(texto or "")).strip().rstrip(" .!?")
    for rx in _ORDEN:
        m = rx.match(t)
        if m:
            n = m.group("n").strip(" «»\"'.,:")
            n = re.sub(r"^(?:el|la|los|las|un|una)\s+", "", n, flags=re.I)
            if not n or "://" in n or "github.com" in n.lower() or re.match(r"^[\w.-]+/[\w.-]+$", n):
                return None
            if len(n) > 60:
                return None
            return n
    return None


# ------------------------------------------------------------------ BUSCAR en GitHub
def _traer_json_defecto(url):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "KiraOS", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read(4_000_000).decode("utf-8", "ignore"))


def buscar(nombre, traer_json=None, maximo=MAX_OPCIONES):
    """Los proyectos de GitHub que encajan con el nombre, los más conocidos primero. Lanza si GitHub no contesta."""
    traer = traer_json or _traer_json_defecto
    q = urllib.parse.quote(f"{nombre} in:name,description")
    d = traer(f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=15")
    items = (d or {}).get("items") or [] if isinstance(d, dict) else []
    k = re.sub(r"[^a-z0-9]", "", _plano(nombre))
    ops = []
    for it in items:
        if not isinstance(it, dict) or not it.get("full_name") or it.get("fork"):
            continue
        nom = str(it.get("name") or "")
        kn = re.sub(r"[^a-z0-9]", "", _plano(nom))
        ops.append({"repo": it["full_name"], "url": it.get("html_url") or "https://github.com/" + it["full_name"],
                    "estrellas": int(it.get("stargazers_count") or 0),
                    "descripcion": re.sub(r"\s+", " ", str(it.get("description") or "")).strip()[:140],
                    "lenguaje": it.get("language") or "", "archivado": bool(it.get("archived")),
                    "actualizado": str(it.get("pushed_at") or "")[:10], "exacto": kn == k})
    # el que se llama EXACTAMENTE así primero (a igualdad, el de más estrellas), los archivados al final
    ops.sort(key=lambda o: (o["archivado"], not o["exacto"], -o["estrellas"]))
    return ops[:maximo]


def _estrellas(n):
    if n >= 1000:
        return f"{n / 1000:.1f}".replace(".", ",").replace(",0", "") + " mil"
    return str(n)


def texto_opciones(nombre, ops):
    if not ops:
        return texto_no_encontrado(nombre)
    lin = [f"En GitHub hay varios proyectos con «{nombre}». ¿Cuál quieres?"]
    for i, o in enumerate(ops, 1):
        extra = []
        if o["lenguaje"]:
            extra.append(o["lenguaje"])
        if o["actualizado"]:
            extra.append("último cambio " + o["actualizado"])
        if o["archivado"]:
            extra.append("ABANDONADO (archivado)")
        lin.append(f" {i}. {o['repo']} — ★ {_estrellas(o['estrellas'])}" + (f" — {o['descripcion']}" if o["descripcion"] else "")
                   + (f" ({', '.join(extra)})" if extra else ""))
    lin.append("Dime «el 1», «el 2»…, o «ninguno». Si no está, búscalo tú en el Buscador («busca "
               f"{nombre} en github»), entra en su página y pulsa su descarga.")
    return "\n".join(lin)


def texto_no_encontrado(nombre, motivo=""):
    return ((f"No he encontrado «{nombre}» en GitHub" + (f" ({motivo})" if motivo else "") + ". ") +
            f"Búscalo tú en el Buscador («busca {nombre} en github» o en internet): entra en la página, mira su "
            "contenido y pulsa el enlace de descarga que quieras (o «Abrir en el navegador» para descargarlo tú). "
            "Si lo descargas tú, dime luego «instala lo que he descargado».")


# ------------------------------------------------------------------ la pregunta pendiente
def _ruta():
    return os.environ.get("KIRA_GITHUB_BUSCA") or os.path.expanduser("~/.kira_github_busca.json")


def guardar_pendiente(nombre, ops):
    ruta = _ruta()
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"nombre": nombre, "opciones": ops, "cuando": time.time()}, f, ensure_ascii=False)
    os.chmod(ruta + ".tmp", 0o600)
    os.replace(ruta + ".tmp", ruta)


def pendiente():
    try:
        with open(_ruta(), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or time.time() - float(d.get("cuando") or 0) > DURA or not d.get("opciones"):
        return None
    return d


def borrar_pendiente():
    try:
        os.remove(_ruta())
    except OSError:
        pass


_ORDINALES = {"primero": 1, "primera": 1, "segundo": 2, "segunda": 2, "tercero": 3, "tercera": 3, "cuarto": 4,
              "cuarta": 4, "quinto": 5, "quinta": 5, "sexto": 6, "sexta": 6, "uno": 1, "dos": 2, "tres": 3,
              "cuatro": 4, "cinco": 5, "seis": 6}


def eleccion(texto, ops):
    """Índice (0…) del proyecto elegido, «cancelar», o None si no es una respuesta. Puro."""
    t = _plano(texto).strip(" .!?")
    if re.match(r"^(?:ninguno|ninguna|nada|dejalo|deja(?:lo)?|cancela|olvidalo|no)$", t):
        return "cancelar"
    m = re.match(r"^(?:kira[, ]+)?(?:el|la|elijo el|elijo la|quiero el|quiero la|instala el|instala la|"
                 r"numero|opcion|proyecto)?\s*(\d{1,2})$", t)
    if m:
        i = int(m.group(1)) - 1
        return i if 0 <= i < len(ops) else None
    m = re.match(r"^(?:el|la|elijo el|elijo la|quiero el|quiero la)?\s*(" + "|".join(_ORDINALES) + r")$", t)
    if m:
        i = _ORDINALES[m.group(1)] - 1
        return i if i < len(ops) else None
    for i, o in enumerate(ops):                           # «el de dueño/proyecto» o el nombre del dueño
        r = o["repo"].lower()
        if t in (r, "el de " + r, r.split("/")[0], "el de " + r.split("/")[0]):
            return i
    return None


def es_respuesta(texto, ops):
    return eleccion(texto, ops) is not None


# ------------------------------------------------------------------ lo que TÚ descargaste
_ORDEN_DESCARGADO = re.compile(
    r"^(?:kira[, ]+)?inst[aá]la(?:me)?\s+(?:lo|el\s+archivo|el\s+programa|eso)\s+(?:que\s+)?(?:he\s+|acabo\s+de\s+|ya\s+)?"
    r"(?:descargad[oa]|bajad[oa]|descargu[eé]|baj[eé])\b.*$|"
    r"^(?:kira[, ]+)?inst[aá]la(?:me)?\s+(?:lo\s+)?(?:[uú]ltimo\s+)?(?:que\s+)?(?:he\s+)?(?:descargad[oa]|descargu[eé]|"
    r"baj[eé])\b.*$|"
    r"^(?:kira[, ]+)?inst[aá]la(?:me)?\s+lo\s+de\s+(?:la\s+carpeta\s+)?(?:descargas|downloads)$|"
    # v3.94: lo que AÚN se está bajando en el navegador de Xubuntu
    r"^(?:kira[, ]+)?inst[aá]la(?:me)?\s+(?:lo|el\s+archivo|el\s+programa|eso)\s+que\s+(?:estoy|est[aá]s?|se\s+est[aá])\s+"
    r"(?:descargando|bajando)\b.*$|"
    r"^(?:kira[, ]+)?cuando\s+(?:acabe|termine)\s+(?:de\s+)?(?:descargarse|bajarse|la\s+descarga)\s*,?\s*inst[aá]la(?:lo|la)\b.*$",
    re.I)


def es_orden_descargado(texto):
    """«instala lo que he descargado», «instala lo último que descargué», «instala el archivo que bajé», «instala lo
    de descargas». Puro."""
    return bool(_ORDEN_DESCARGADO.match(re.sub(r"\s+", " ", str(texto or "")).strip().rstrip(" .!?")))


def carpetas_descargas():
    casa = os.path.expanduser("~")
    return [os.path.join(casa, c) for c in ("Descargas", "Downloads") if os.path.isdir(os.path.join(casa, c))]


_EN_CURSO = (".part", ".crdownload", ".download", ".tmp", ".opdownload")


def _final_de(nombre):
    for e in _EN_CURSO:
        if nombre.endswith(e):
            return nombre[:-len(e)]
    return nombre


def descargas_en_curso(carpetas=None, tipo_de=None):
    """v3.94: lo que el navegador de Xubuntu está bajando AHORA en Descargas (Firefox «X.part», Chrome
    «X.crdownload»…) y que parece un programa. [(ruta_parcial, nombre_final, bytes)]."""
    if tipo_de is None:
        import apps_externas_kira as aex
        tipo_de = aex.tipo_archivo
    r = []
    for c in (carpetas if carpetas is not None else carpetas_descargas()):
        try:
            nombres = os.listdir(c)
        except OSError:
            continue
        for n in nombres:
            if n.startswith(".") or not n.endswith(_EN_CURSO):
                continue
            final = _final_de(n)
            # Chrome pone «Sin confirmar 1234.crdownload» (sin el nombre): también vale, no sabemos el tipo aún
            if tipo_de(final) == "" and not final.lower().startswith(("sin confirmar", "unconfirmed")):
                continue
            ruta = os.path.join(c, n)
            try:
                r.append((ruta, final, os.path.getsize(ruta)))
            except OSError:
                continue
    return r


def esperar_descarga(carpetas=None, tipo_de=None, al_paso=None, parar=None, tope=3600, quieta=300, cada=3.0,
                     dormir=None):
    """v3.94: si el navegador aún está bajando un programa, ESPERA a que acabe (mira que el «.part» desaparezca) y
    devuelve (ruta_final | None, motivo). Para si `parar()` dice que sí, si pasa `tope` s, o si la descarga lleva
    `quieta` s sin crecer (atascada)."""
    import time as _t
    dormir = dormir or _t.sleep
    paso = al_paso or (lambda _t2: None)
    parar = parar or (lambda: False)
    inicio = _t.time()
    ultimo_tam, ultimo_cambio = -1, _t.time()
    nombre = ""
    while True:
        curso = descargas_en_curso(carpetas, tipo_de)
        if not curso:
            if nombre:
                paso(f"Ya ha acabado de descargarse {nombre}.")
            return ultimo_descargado(carpetas, tipo_de), "ok"
        ruta, nombre, tam = max(curso, key=lambda x: x[2])
        tot = sum(x[2] for x in curso)
        if tot != ultimo_tam:
            ultimo_tam, ultimo_cambio = tot, _t.time()
            paso(f"Se está descargando {nombre} ({tot / 1048576:.1f} MB)… espero a que acabe para instalarlo.")
        if parar():
            return None, "parada"
        if _t.time() - ultimo_cambio > quieta:
            return None, "atascada"
        if _t.time() - inicio > tope:
            return None, "tope"
        dormir(cada)


def ultimo_descargado(carpetas=None, tipo_de=None):
    """El archivo más nuevo de Descargas que sea un programa (o uno de otro sistema, para avisarlo). None si no hay.
    Se salta lo que aún se está descargando (.part, .crdownload…)."""
    if tipo_de is None:
        import apps_externas_kira as aex
        tipo_de = aex.tipo_archivo
    mejor = None
    for c in (carpetas if carpetas is not None else carpetas_descargas()):
        try:
            nombres = os.listdir(c)
        except OSError:
            continue
        enc = set(nombres)
        for n in nombres:
            if n.startswith(".") or n.endswith(_EN_CURSO):
                continue
            if any(n + e in enc for e in _EN_CURSO):    # v3.94: Firefox deja un archivo VACÍO con el nombre final
                continue                                 # mientras baja «X.part»: aún no está
            ruta = os.path.join(c, n)
            if not os.path.isfile(ruta) or tipo_de(n) == "":
                continue
            try:
                if os.path.getsize(ruta) == 0:
                    continue
            except OSError:
                continue
            m = os.path.getmtime(ruta)
            if mejor is None or m > mejor[0]:
                mejor = (m, ruta)
    return mejor[1] if mejor else None
