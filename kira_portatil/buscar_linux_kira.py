# -*- coding: utf-8 -*-
"""
buscar_linux_kira.py - v3.78: cuando el dueño quiere instalar un programa y lo que hay a mano es para OTRO sistema
(.exe, .msi, .dmg, .apk…) o la página no tiene un enlace directo, Kira BUSCA la versión para Linux por su cuenta:

  1. en la propia página (todos los enlaces de descarga, eligiendo el de Linux de 64 bits);
  2. en su GitHub, si la página enlaza uno (sus versiones publicadas);
  3. en las páginas de descargas de esa misma web («Download», «Descargas», «Releases», «Linux»…), un salto;
  4. si no hay archivo para Linux: en los programas de Xubuntu (apt) y en Flathub (flatpak), por el nombre.

Y lo dice claro: qué sistemas había en la página («solo para Windows y Mac») y qué ha encontrado. Instalar desde apt
o Flathub (otra fuente) NO lo hace solo: te lo propone con la orden exacta.

Puro salvo `traer` (bajar HTML), `correr` (apt-cache / flatpak) y `de_github`, que se inyectan en las pruebas.
"""
import re
import shutil
import subprocess
import urllib.parse

MAX_SUBPAGINAS = 4

PLATAFORMAS = {"windows": "Windows", "mac": "Mac", "android": "Android", "linux": "Linux", "otro": "otro sistema"}


def _fichero(url):
    return str(url or "").split("?")[0].split("#")[0].rstrip("/").split("/")[-1].lower()


def plataforma(url):
    """De qué sistema es un archivo de descarga: 'linux' | 'windows' | 'mac' | 'android' | 'otro' | '' (no es archivo)."""
    import apps_externas_kira as aex
    f = _fichero(url)
    if f.endswith((".exe", ".msi", ".msix", ".appx")) or re.search(r"(win32|win64|windows|[-_.]win[-_.])", f):
        return "windows"
    if f.endswith((".dmg", ".pkg", ".app")) or re.search(r"(macos|osx|darwin|[-_.]mac[-_.])", f):
        return "mac"
    if f.endswith((".apk", ".aab")) or "android" in f:
        return "android"
    if f.endswith(".rpm"):
        return "otro"
    if aex.es_descargable(url):
        return "linux"
    return ""


def plataformas(urls):
    """{'windows': [...], 'mac': [...], 'linux': [...]} de una lista de enlaces de descarga. Puro."""
    d = {}
    for u in urls:
        p = plataforma(u)
        if p:
            d.setdefault(p, []).append(u)
    return d


def texto_plataformas(d):
    """«Windows (.exe) y Mac (.dmg)». Puro."""
    partes = []
    for p in ("windows", "mac", "android", "otro"):
        if d.get(p):
            ext = sorted({"." + _fichero(u).rsplit(".", 1)[-1] for u in d[p] if "." in _fichero(u)})[:2]
            partes.append(PLATAFORMAS[p] + (f" ({', '.join(ext)})" if ext else ""))
    if not partes:
        return ""
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]


_PALABRAS_DESCARGA = re.compile(r"(download|descarga|releases?|linux|get[-_ ]?it|instal|ubuntu|debian|appimage)", re.I)


def subpaginas(html, base):
    """Enlaces de la MISMA web que parecen su página de descargas (por la dirección o el texto). Puro."""
    host = urllib.parse.urlparse(base).netloc.lower()
    fuera, vistos = [], {base.split("#")[0]}
    for m in re.finditer(r"""<a\b[^>]*href\s*=\s*["']([^"'<>]+)["'][^>]*>(.*?)</a>""", str(html or ""), re.I | re.S):
        href, txt = m.group(1).strip(), re.sub(r"<[^>]+>", " ", m.group(2))
        if href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        try:
            url = urllib.parse.urldefrag(urllib.parse.urljoin(base, href))[0]
        except ValueError:
            continue
        if urllib.parse.urlparse(url).netloc.lower() != host or url in vistos or plataforma(url):
            continue
        if _PALABRAS_DESCARGA.search(url) or _PALABRAS_DESCARGA.search(txt):
            vistos.add(url)
            fuera.append(url)
    return fuera[:MAX_SUBPAGINAS]


def github_de(html):
    """El primer repositorio de GitHub que enlaza la página («https://github.com/dueño/repo»). Puro."""
    for m in re.finditer(r"https?://github\.com/([\w.-]+)/([\w.-]+)", str(html or "")):
        dueno, repo = m.group(1), re.sub(r"\.git$", "", m.group(2))
        if dueno.lower() in ("sponsors", "features", "about", "login", "orgs", "topics", "marketplace", "site"):
            continue
        return f"https://github.com/{dueno}/{repo}"
    return None


def nombre_de(fuente, html=""):
    """Un nombre de programa para buscar en apt/Flathub: del archivo (sin versión ni sistema), del título o de la web."""
    f = _fichero(fuente)
    if f and "." in f and plataforma(fuente):
        b = re.split(r"[-_ ]?(?:v?\d[\d.]*|setup|install(?:er)?|win(?:32|64|dows)?|x64|x86|amd64|portable|mac|osx)",
                     f.rsplit(".", 1)[0], 1, flags=re.I)[0]
        if len(b) >= 2:
            return b.strip("-_ .")
    m = re.search(r"<title>(.*?)</title>", str(html or ""), re.I | re.S)
    if m:
        t = re.split(r"[-|–:·]", re.sub(r"\s+", " ", m.group(1)).strip())[0].strip()
        t = re.sub(r"(?i)\b(download|descargar?|official|oficial|site|web|página|page|free|gratis)\b", "", t).strip()
        if 2 <= len(t) <= 40:
            return t
    host = urllib.parse.urlparse(str(fuente)).netloc.lower()
    partes = [p for p in host.split(".") if p not in ("www", "com", "org", "net", "io", "es", "app", "dev", "download")]
    return partes[0] if partes else ""


def _correr_defecto(args, timeout=30):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def paquete_apt(nombre, correr=None, which=None):
    """El paquete de Xubuntu con ese nombre (si existe y tiene versión para instalar). Solo mira, no instala."""
    which = which or shutil.which
    if not nombre or not which("apt-cache"):
        return None
    correr = correr or _correr_defecto
    for cand in dict.fromkeys([nombre.lower(), nombre.lower().replace(" ", "-"), nombre.lower().replace(" ", "")]):
        if not re.match(r"^[a-z0-9][a-z0-9.+-]{1,40}$", cand):
            continue
        try:
            rc, sal = correr(["apt-cache", "policy", cand], timeout=20)
        except Exception:                                 # noqa: BLE001
            continue
        m = re.search(r"(?:Candidato|Candidate):\s*(\S+)", sal or "")
        if rc == 0 and m and m.group(1) not in ("(ninguno)", "(none)"):
            return cand
    return None


def app_flathub(nombre, correr=None, which=None):
    """El identificador de Flathub que encaja con el nombre (si flatpak está y tiene Flathub). Solo mira."""
    which = which or shutil.which
    if not nombre or not which("flatpak"):
        return None
    correr = correr or _correr_defecto
    try:
        rc, sal = correr(["flatpak", "search", "--columns=application,name", nombre], timeout=60)
    except Exception:                                     # noqa: BLE001
        return None
    if rc != 0:
        return None
    k = re.sub(r"[^a-z0-9]", "", nombre.lower())
    mejor = None
    for linea in (sal or "").splitlines():
        partes = [p.strip() for p in re.split(r"\t|\s{2,}", linea.strip()) if p.strip()]
        if not partes or not re.match(r"^[\w-]+(\.[\w-]+){2,}$", partes[0]):
            continue
        ident, nom = partes[0], (partes[1] if len(partes) > 1 else "")
        kn = re.sub(r"[^a-z0-9]", "", nom.lower())
        ki = re.sub(r"[^a-z0-9]", "", ident.split(".")[-1].lower())
        if k and (kn == k or ki == k):
            return ident
        if mejor is None and k and (k in kn or k in ki):
            mejor = ident
    return mejor


def buscar(fuente, nombre=None, pagina=None, traer=None, correr=None, de_github=None, which=None, al_paso=None):
    """Busca la versión para Linux de lo que se quiere instalar.

    `fuente`: la URL que falló (un .exe, una página sin enlace directo…); `pagina`: la página donde estaba (si se sabe).
    Devuelve {"ok": True, "fuente": url, "como": "pagina"|"github"|"subpagina", "texto": …} si encontró un archivo para
    Linux (o un GitHub con sus versiones), o {"ok": False, "apt": pkg|None, "flatpak": id|None, "texto": …}."""
    import apps_externas_kira as aex
    paso = al_paso or (lambda t: None)
    traer = traer or aex._traer_texto
    if de_github is None:
        import versiones_kira as vk
        de_github = vk.de_github
    vistas, todas, html_base = [], [], ""
    gh0 = github_de(fuente) if plataforma(fuente) else None   # un .exe de las versiones de un GitHub → ese GitHub
    if gh0:
        try:
            if de_github(gh0):
                return {"ok": True, "fuente": gh0, "como": "github",
                        "texto": f"Ese archivo es para otro sistema; miro las versiones de su GitHub ({gh0})."}
        except Exception:                                 # noqa: BLE001
            pass
    paginas = [u for u in (pagina, fuente) if u and not plataforma(u)]
    for i, url in enumerate(dict.fromkeys(paginas)):
        paso("Busco la versión para Linux en la página…")
        try:
            html = traer(url)
        except Exception:                                 # noqa: BLE001
            continue
        html_base = html_base or html
        vistas.append(url)
        enl = aex.enlaces_descarga(html, url)
        todas += enl
        mejor = aex.elegir_descarga(enl)
        if mejor:
            return {"ok": True, "fuente": mejor, "como": "pagina",
                    "texto": f"En la página había varias descargas; me quedo con la de Linux: {_fichero(mejor)}."}
        gh = github_de(html)
        if gh:
            paso("La página enlaza su GitHub: miro sus versiones…")
            try:
                ops = de_github(gh) or []
            except Exception:                             # noqa: BLE001
                ops = []
            if ops:
                return {"ok": True, "fuente": gh, "como": "github",
                        "texto": f"La página no tenía el archivo para Linux, pero su GitHub sí ({gh})."}
        for sub in subpaginas(html, url):
            paso("Miro su página de descargas…")
            try:
                h2 = traer(sub)
            except Exception:                             # noqa: BLE001
                continue
            e2 = aex.enlaces_descarga(h2, sub)
            todas += e2
            m2 = aex.elegir_descarga(e2)
            if m2:
                return {"ok": True, "fuente": m2, "como": "subpagina",
                        "texto": f"La encontré en su página de descargas ({sub}): {_fichero(m2)}."}
            gh2 = github_de(h2)
            if gh2:
                try:
                    if de_github(gh2):
                        return {"ok": True, "fuente": gh2, "como": "github",
                                "texto": f"Su página de descargas enlaza su GitHub ({gh2}), que sí tiene versiones."}
                except Exception:                         # noqa: BLE001
                    pass
    if plataforma(fuente):
        todas.append(fuente)
    hay = texto_plataformas(plataformas(todas))
    nom = (nombre or nombre_de(fuente, html_base) or "").strip()
    paso("Busco el programa en Xubuntu y en Flathub…")
    pkg = paquete_apt(nom, correr, which)
    fp = app_flathub(nom, correr, which)
    lin = [("No hay versión para Linux: lo que encontré es para " + hay + "." if hay else
            "No encontré en la página ningún archivo de descarga que sirva para Xubuntu.")]
    if pkg or fp:
        lin.append(f"Pero «{nom}» SÍ está para Linux por otro lado:")
        if pkg:
            lin.append(f" · en los programas de Xubuntu: dime «instala {pkg}» (con el permiso de administrador que me "
                       "diste, o te digo qué escribir en la Terminal).")
        if fp:
            lin.append(f" · en Flathub (sin administrador): dime «instala flatpak {fp}».")
    else:
        lin.append(f"Tampoco encuentro «{nom}» en los programas de Xubuntu ni en Flathub." if nom else
                   "Dime cómo se llama el programa y lo busco en Xubuntu y en Flathub.")
        if hay and "Windows" in hay:
            lin.append("Si solo existe para Windows, se podría probar con Wine (sudo apt install wine), pero no "
                       "siempre funciona: dime si quieres intentarlo.")
    return {"ok": False, "apt": pkg, "flatpak": fp, "nombre": nom, "plataformas": hay, "vistas": vistas,
            "texto": "\n".join(lin)}


# ---------------- instalar desde Flathub (sin administrador) ----------------
_FLATPAK = re.compile(r"^(?:flatpak[: ]+)([\w-]+(?:\.[\w-]+){2,})$", re.I)


def es_flatpak(fuente):
    """«flatpak org.videolan.VLC» / «flatpak:org.videolan.VLC» → el identificador; si no, None. Puro."""
    m = _FLATPAK.match(str(fuente or "").strip())
    return m.group(1) if m else None


def instalar_flatpak(ident, correr=None, which=None, al_paso=None):
    """Instala de Flathub para TU usuario (--user: sin administrador). Mismo formato que apps_externas_kira.instalar."""
    which = which or shutil.which
    paso = al_paso or (lambda t: None)
    nombre = ident.split(".")[-1]
    if not which("flatpak"):
        return {"ok": False, "admin": True, "nombre": nombre, "lanzar": None, "carpeta": "",
                "mensaje": ("No tengo Flatpak. Instálalo una vez en la Terminal: sudo apt install flatpak (con tu "
                            "contraseña) y vuelve a pedírmelo.")}
    correr = correr or _correr_defecto
    paso("Preparo Flathub…")
    try:
        correr(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
                "https://dl.flathub.org/repo/flathub.flatpakrepo"], timeout=120)
        paso(f"Descargo {nombre} de Flathub…")
        rc, sal = correr(["flatpak", "install", "--user", "-y", "--noninteractive", "flathub", ident], timeout=3600)
    except Exception as e:                                # noqa: BLE001
        return {"ok": False, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": "",
                "mensaje": f"No pude instalar {ident} de Flathub: {e}"}
    if rc != 0:
        return {"ok": False, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": "",
                "mensaje": f"Flathub no me dejó instalar {ident}: {(sal or '').strip()[-200:]}"}
    return {"ok": True, "admin": False, "nombre": nombre, "lanzar": ["flatpak", "run", ident], "carpeta": "",
            "analisis": {"nivel": "ok", "resumen": "de Flathub, en su caja de Flatpak"},
            "mensaje": f"{nombre} instalada desde Flathub (para tu usuario, sin tocar el sistema)."}
