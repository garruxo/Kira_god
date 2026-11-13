# -*- coding: utf-8 -*-
"""
versiones_kira.py — v3.35 (SOLO KiraOS): cuando hay VARIAS VERSIONES de lo que el dueño quiere descargar, Kira se las
enseña y le pregunta cuál quiere.

Lo pidió el dueño: «cuando busca en internet algo para descargar, suele haber varias versiones, y Kira no reconoce los
enlaces de las versiones; que me diga qué versiones hay y cuál quiero descargar».

  - `version_de(url)` saca el número de versión de un enlace (v1.2.3, 2.0.1-beta, 2024.05…), del nombre del archivo
    o de la carpeta (/releases/download/v1.4.0/…).
  - `opciones_de_urls(urls)` agrupa los enlaces de una página por versión y, de cada una, elige el archivo que sirve
    en Xubuntu de 64 bits (AppImage > comprimido > .deb), con las demás formas de esa versión.
  - `de_github(repo)` pregunta a GitHub las «releases» del proyecto (sus versiones publicadas con su archivo).
  - `texto_opciones` = la lista para el dueño; `eleccion(texto, opciones)` entiende su respuesta («la 2», «la versión
    1.4.0», «la más nueva», «la estable», «la segunda», «en .deb», «ninguna»).
  - La pregunta queda apuntada en ~/.kira_versiones.json (0600) 30 minutos: la contesta igual por la barra de Kira o
    por el núcleo (son dos procesos).

Puro salvo `traer_json` (inyectable) y el archivo de la pregunta pendiente.
"""
import json
import os
import re
import time
import unicodedata

import apps_externas_kira as aex

RUTA = os.environ.get("KIRA_VERSIONES") or os.path.expanduser("~/.kira_versiones.json")
DURA_MIN = 30
MAX_OPCIONES = 8
_PRE = r"(?:alpha|beta|rc|pre|preview|dev|nightly|canary|snapshot|b|a)"
_RE_VERSION = re.compile(r"(?<![\w.])v?(\d+(?:\.\d+){1,3}(?:[-_.~+]?" + _PRE + r"[.\-_]?\d*)?)(?![\w])", re.I)


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def version_de(url_o_nombre):
    """El número de versión del enlace (sin la «v»), o ''. Mira primero el archivo y luego las carpetas. Puro."""
    u = str(url_o_nombre or "").split("?")[0].split("#")[0]
    trozos = [t for t in u.split("/") if t]
    candidatos = []
    if trozos:
        archivo = re.sub(r"(x86[_-]64|amd64|i[3-6]86|arm64|aarch64|armv\d\w*|x64|win(?:32|64)|ubuntu\d*|"
                         r"debian\d*|el\d+|fc\d+|qt\d|gtk\d)", " ", trozos[-1], flags=re.I)
        archivo = re.sub(r"\.(?:appimage|deb|rpm|tar\.gz|tgz|tar\.xz|txz|tar\.bz2|tbz2|tar|zip|exe|msi|dmg|sh|run|"
                         r"bin|apk|pkg)$", "", archivo, flags=re.I)
        candidatos.append(archivo)
        candidatos.extend(reversed(trozos[:-1]))
    for c in candidatos:
        m = _RE_VERSION.search(c.replace("_", "-"))
        if m:
            return m.group(1).rstrip(".-_")
    return ""


def clave_version(v):
    """Para ordenar: (números…, estable) — 2.0 > 2.0-rc1 > 1.9. Puro."""
    nums = [int(x) for x in re.findall(r"\d+", re.split(_PRE, str(v), flags=re.I)[0])[:4]]
    estable = 0 if re.search(_PRE + r"(?![a-z])", str(v), re.I) else 1
    return tuple(nums + [0] * (4 - len(nums))) + (estable,)


def es_estable(v):
    return clave_version(v)[-1] == 1 if v else True


def _forma(tipo):
    return {"appimage": "AppImage", "deb": ".deb", "comprimido": "comprimido", "script": "instalador .sh",
            "binario": "binario"}.get(tipo, tipo)


def opciones_de_urls(urls, maximo=MAX_OPCIONES):
    """Agrupa los enlaces por versión. De cada versión, el mejor archivo para Xubuntu 64 bits y sus otras formas.
    Devuelve [{n, version, url, archivo, tipo, forma, estable, otras:[{forma, url}]}] de la más nueva a la más vieja
    (las que solo tienen archivos de Windows/Mac quedan fuera). Puro."""
    grupos = {}
    for u in urls or []:
        if not aex.es_descargable(u):
            continue
        v = version_de(u) or "?"
        grupos.setdefault(v, []).append(u)
    ops = []
    for v, us in grupos.items():
        mejor = aex.elegir_descarga(us)
        if not mejor:
            continue
        otras, vistas = [], {aex.tipo_archivo(mejor)}
        for u in sorted(us, key=lambda x: -{"appimage": 5, "deb": 4, "comprimido": 3, "binario": 2,
                                           "script": 1}.get(aex.tipo_archivo(x), 0)):
            tp = aex.tipo_archivo(u)
            if tp not in vistas and aex.elegir_descarga([u]):
                vistas.add(tp)
                otras.append({"forma": _forma(tp), "url": u, "tipo": tp})
        tipo = aex.tipo_archivo(mejor)
        ops.append({"version": "" if v == "?" else v, "url": mejor, "archivo": aex._nombre_fichero(mejor),
                    "tipo": tipo, "forma": _forma(tipo), "estable": es_estable(v if v != "?" else ""),
                    "otras": otras})
    ops.sort(key=lambda o: clave_version(o["version"]) if o["version"] else (-1,), reverse=True)
    ops = ops[:maximo]
    for i, o in enumerate(ops, 1):
        o["n"] = i
    return ops


def repo_github(fuente):
    """«usuario/repo» de una fuente de GitHub (URL o usuario/repo), o None. Puro."""
    f = str(fuente or "").strip()
    m = re.match(r"^(?:https?://)?(?:www\.)?github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/.*)?$", f, re.I)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    if re.match(r"^[\w.-]+/[\w.-]+$", f):
        return f
    return None


def _traer_json_defecto(url):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "KiraOS", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read(4_000_000).decode("utf-8", "ignore"))


def de_github(fuente, traer_json=None, maximo=MAX_OPCIONES):
    """Las versiones publicadas (releases) de un proyecto de GitHub que traen archivo para Xubuntu. [] si no hay o
    si GitHub no contesta (entonces se clona el código como antes)."""
    repo = repo_github(fuente)
    if not repo:
        return []
    traer = traer_json or _traer_json_defecto
    try:
        rel = traer(f"https://api.github.com/repos/{repo}/releases?per_page=20")
    except Exception:                                 # noqa: BLE001 - sin internet / límite de GitHub
        return []
    if not isinstance(rel, list):
        return []
    ops = []
    for r in rel:
        if not isinstance(r, dict) or r.get("draft"):
            continue
        urls = [a.get("browser_download_url", "") for a in (r.get("assets") or []) if isinstance(a, dict)]
        mejor = aex.elegir_descarga([u for u in urls if u])
        if not mejor:
            continue
        v = str(r.get("tag_name") or "").lstrip("vV") or version_de(mejor)
        otras = []
        vistas = {aex.tipo_archivo(mejor)}
        for u in urls:
            tp = aex.tipo_archivo(u)
            if u and tp not in vistas and aex.elegir_descarga([u]):
                vistas.add(tp)
                otras.append({"forma": _forma(tp), "url": u, "tipo": tp})
        tipo = aex.tipo_archivo(mejor)
        ops.append({"version": v, "url": mejor, "archivo": aex._nombre_fichero(mejor), "tipo": tipo,
                    "forma": _forma(tipo), "estable": not r.get("prerelease") and es_estable(v),
                    "fecha": str(r.get("published_at") or "")[:10], "otras": otras})
        if len(ops) >= maximo:
            break
    for i, o in enumerate(ops, 1):
        o["n"] = i
    return ops


def texto_opciones(nombre, opciones, con_codigo=False):
    """La pregunta para el dueño. Puro."""
    if not opciones:
        return ""
    lin = [f"He encontrado {len(opciones)} versiones de {nombre} para Xubuntu:"]
    primera_estable = next((o["n"] for o in opciones if o.get("estable")), None)
    for o in opciones:
        nota = []
        if o["n"] == 1:
            nota.append("la más nueva")
        if o["n"] == primera_estable and o["n"] != 1:
            nota.append("la estable más nueva")
        elif o["n"] == primera_estable:
            nota.append("estable")
        if not o.get("estable"):
            nota.append("de prueba: puede fallar")
        if o.get("fecha"):
            nota.append(o["fecha"])
        formas = o["forma"] + ("".join(f", también {x['forma']}" for x in o.get("otras", [])))
        lin.append(f" {o['n']}) {o['version'] or 'sin número'} — {formas}" + (f" ({', '.join(nota)})" if nota else ""))
    lin.append("¿Cuál quieres que descargue? Dime «instala la 1», «la versión " + (opciones[-1]["version"] or "X") +
               "», «la más nueva» o «la estable»" + (" (o «clónalo» para bajar el código fuente)" if con_codigo else "") +
               ". También «la 2 en .deb» si prefieres otra forma. «Ninguna» para dejarlo.")
    return "\n".join(lin)


_ORD = {"primera": 1, "primero": 1, "segunda": 2, "segundo": 2, "tercera": 3, "tercero": 3, "cuarta": 4, "cuarto": 4,
        "quinta": 5, "quinto": 5, "sexta": 6, "septima": 7, "octava": 8}


def eleccion(texto, opciones):
    """Lo que eligió el dueño: la opción (dict, con 'url' ya de la forma pedida), 'cancelar', 'clonar' o None. Puro."""
    t = _norm(re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", str(texto or ""), flags=re.I)).strip(" .!?¿¡")
    if not t or not opciones:
        return None
    if re.search(r"^(?:ninguna|ninguno|nada|cancela\w*|dejalo|da\s+igual\s+no|no\s+quiero\s+ninguna|olvidalo)\b", t):
        return "cancelar"
    if re.search(r"\b(?:clonal[oa]|el\s+codigo\s+fuente|la\s+fuente|codigo\s+fuente)\b", t):
        return "clonar"
    elegida = None
    for o in sorted(opciones, key=lambda x: -len(x.get("version") or "")):   # «1.4.10» antes que «1.4.1»
        v = _norm(o.get("version") or "")
        if v and re.search(r"(?<![\d.])v?" + re.escape(v) + r"(?![\d])", t):
            elegida = o
            break
    if elegida is None and re.search(r"\b(?:mas\s+nueva|mas\s+reciente|ultima|ultimo|mas\s+actual|nueva)\b", t) \
            and not re.search(r"\bestable\b", t):
        elegida = opciones[0]
    if elegida is None and re.search(r"\bestable\b", t):
        elegida = next((o for o in opciones if o.get("estable")), opciones[0])
    if elegida is None:
        for pal, num in _ORD.items():
            if re.search(r"\b" + pal + r"\b", t) and num > 0:
                elegida = next((o for o in opciones if o["n"] == num), None)
                break
    if elegida is None:
        m = re.search(r"(?:^|\b(?:la|el|opcion|numero|n|#|instala(?:me)?|descarga(?:me)?|baja(?:me)?|quiero|"
                      r"elijo|ponme|dame)\s+)(?:la\s+|el\s+|opcion\s+|numero\s+)?(\d{1,2})(?![\d.])", t)
        if m:
            elegida = next((o for o in opciones if o["n"] == int(m.group(1))), None)
    if elegida is None:
        return None
    o = dict(elegida)
    forma = re.search(r"\ben\s+(?:\.?(deb|appimage)|(comprimido|tar|zip))\b", t)
    if forma:
        quiero = "deb" if forma.group(1) == "deb" else ("appimage" if forma.group(1) else "comprimido")
        for x in [{"tipo": o["tipo"], "url": o["url"], "forma": o["forma"]}] + list(o.get("otras") or []):
            if x.get("tipo") == quiero:
                o.update(url=x["url"], tipo=x["tipo"], forma=x["forma"])
                break
    return o


def es_respuesta(texto, opciones):
    """¿Este mensaje contesta a la pregunta de versiones? (frases cortas de elegir). Puro."""
    t = _norm(re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", str(texto or ""), flags=re.I)).strip(" .!?¿¡")
    if len(t) > 80:
        return False
    if not re.match(r"^(?:instala(?:me)?|descarga(?:me)?|baja(?:me)?|quiero|ponme|dame|elijo|prefiero|la|el|opcion|"
                    r"version|numero|ninguna|ninguno|nada|cancela\w*|dejalo|olvidalo|clonal[oa]|\d)", t):
        return False
    return eleccion(texto, opciones) is not None


# ---------------- la pregunta pendiente (compartida entre la pantalla y el núcleo) ----------------
def guardar_pendiente(nombre, fuente, opciones, ruta=None):
    ruta = ruta or RUTA
    datos = {"nombre": nombre, "fuente": fuente, "opciones": opciones, "cuando": time.time()}
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, ruta)


def pendiente(ruta=None, dura_min=DURA_MIN):
    ruta = ruta or RUTA
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or time.time() - float(d.get("cuando", 0)) > dura_min * 60:
        return None
    return d if d.get("opciones") else None


def borrar_pendiente(ruta=None):
    try:
        os.remove(ruta or RUTA)
    except OSError:
        pass


def nombre_bonito(nombre, version):
    """«Krita 5.2.3» → el nombre de la app sin la versión pegada (para el icono). Puro."""
    n = str(nombre or "app")
    num = re.match(r"\d+(?:\.\d+)*", str(version or ""))
    if num:                                       # «App 2.2.0 rc1 x86 64» → «App» (el guion ya es espacio)
        n = re.sub(r"[\s_-]*v?" + re.escape(num.group(0)) + r"\b.*$", "", n, flags=re.I) or n
    n = re.sub(r"\s+(?:x86\s*64|amd64|linux|x64)\b.*$", "", n, flags=re.I).strip(" -_")
    return n or "app"
