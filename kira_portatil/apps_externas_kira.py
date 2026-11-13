# -*- coding: utf-8 -*-
"""
apps_externas_kira.py — v3.28 (SOLO KiraOS, el portátil).

Lo pidió el dueño: «que pueda instalar aplicaciones que yo le diga, sea lo que sea, como de GitHub u otro sitio, que
las ponga en la pantalla principal con su icono (para desinstalarlas con el botón derecho), y que KiraOS pueda usarlas
cuando se lo ordene».

REGLAS (seguras, acordes a lo que eligió el dueño: «admin solo cuando yo lo pida»):
- SOLO se instala cuando el dueño lo ORDENA (nunca sola mientras piensa).
- Por defecto SIN tocar el sistema (sin contraseña): clona un repo de GitHub o baja un AppImage a una carpeta SUYA
  (`~/kira_portatil/apps_externas/<app>/`). Así, si algo sale mal, se queda en su cuenta de usuario.
- Si de verdad hace falta administrador (p. ej. `apt`), NO lo hace sola: le dice al dueño que lo escriba en la Terminal,
  donde Xubuntu le pedirá SU contraseña.
- La app queda como ICONO en el escritorio (reusa `accesos_kira`): clic = la lanza; clic derecho ▸ Desinstalar = borra
  su carpeta.

Honesto: instalar y ejecutar código de internet siempre tiene algún riesgo (es como clonar y ejecutar uno mismo). Por
eso: solo con la orden del dueño, sin administrador por defecto, y cada instalación se le confirma.

`correr(args, cwd, timeout)` y `bajar(url, destino)` se inyectan (para probar sin git/red reales).
"""
import os
import re
import subprocess
import urllib.request

BASE_POR_DEFECTO = os.path.expanduser("~/kira_portatil/apps_externas")
ARRANQUES = ("main.py", "app.py", "run.py", "inicio.py", "__main__.py")


# ---------------- reconocer las órdenes ----------------
def _sin_kira(texto):
    t = str(texto or "")
    m = re.match(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", t, re.I)
    return t[m.end():] if m else t


def es_orden_instalar(texto):
    """«instala X» / «instálame la app X» / «instala este github: URL» / «descarga e instala X» / «pon X en el
    escritorio». Devuelve la FUENTE (una URL o un nombre), o None. No se mete con «instala las mejoras / la receta /
    la solución / una librería» (eso tiene su sitio)."""
    t = _sin_kira(texto).strip()
    low = t.lower()
    if re.search(r"\b(mejoras?|actualizaci|receta|soluci[oó]n|librer[ií]a)\b", low):
        return None
    m = re.search(r"\b(?:inst[aá]la(?:me|r|mela)?|descarga\s+e\s+instala|baja\s+e\s+instala)\b\s*(.*)$", t, re.I)
    if not m and "escritorio" in low and re.search(r"\bpon(?:me|er)?\b", low):
        m = re.search(r"\bpon(?:me|er)?\b\s*(.*?)\s+en\s+el\s+escritorio", t, re.I)
    if not m:
        return None
    resto = m.group(1).strip()
    resto = re.sub(r"^(?:la\s+|el\s+)?(?:app|aplicaci[oó]n|programa|herramienta)\s+", "", resto, flags=re.I)
    resto = re.sub(r"^(?:este\s+github|de\s+github|desde\s+github|el\s+github)\b\s*:?\s*", "", resto, flags=re.I)
    resto = re.sub(r"^(?:de|desde)\s+", "", resto, flags=re.I)
    # quita el «igualmente / de todas formas» del final (es para FORZAR, no parte del nombre; v3.29)
    resto = re.sub(r"\s+(?:igualmente|igual|de\s+todas\s+(?:formas|maneras)|f[oó]rzal[ao]|aunque\s+sea\s+peligros\w*)\s*$",
                   "", resto, flags=re.I)
    return resto.strip(" .:\"'") or None


def es_orden_instalar_esto(texto):
    """v3.31: «descarga e instala esto», «instala esto», «instala lo que estoy viendo / veo», «descárgate esto y hazme
    el icono», «instala esta app/página». Devuelve True = usa la página que el dueño está viendo en el Buscador. No se
    mete con «instala las mejoras / la receta / la solución»."""
    t = _sin_kira(texto).strip().lower()
    if re.search(r"\b(mejora|actualizaci|receta|soluci[oó]n|librer[ií]a)\b", t):
        return False
    if not re.search(r"\b(inst[aá]la\w*|descarg\w*|baj[ae]\w*|b[aá]jate|desc[aá]rgate)\b", t):
        return False
    return bool(re.search(r"\b(esto|esta\s+(?:p[aá]gina|app|aplicaci[oó]n|web|cosa)|lo\s+que\s+"
                          r"(?:estoy\s+viendo|veo|hay|sale|pone)|aqu[ií]|lo\s+de\s+aqu[ií])\b", t))


def es_orden_dependencias(texto):
    """v3.32: «descarga/instala las dependencias de X», «descarga lo que necesita X», «baja lo que le falta a X»,
    «consigue las librerías de X». Devuelve el nombre de la app, o None. (El dueño CONFIRMA así la descarga: nunca sola.)"""
    t = _sin_kira(texto).strip()
    low = t.lower()
    if not re.search(r"\b(descarg\w*|instal\w*|baj[ae]\w*|b[aá]jate|consigue|pon|busca)\b", low):
        return None
    if not re.search(r"\b(dependencias?|librer[ií]as?|lo\s+que\s+(?:necesita|le\s+falta|le\s+hace\s+falta|le\s+haga\s+falta))", low):
        return None
    m = re.search(r"(?:dependencias?|librer[ií]as?)\s+(?:de\s+|para\s+)?(?:la\s+app\s+|la\s+aplicaci[oó]n\s+|el\s+programa\s+)?(.+)$", t, re.I)
    if not m:
        m = re.search(r"\b(?:necesita|le\s+falta|le\s+hace\s+falta|le\s+haga\s+falta)\s+(?:a\s+|la\s+app\s+|el\s+programa\s+)?(.+)$", t, re.I)
    nombre = (m.group(1) if m else "").strip()
    nombre = re.sub(r"^(?:la\s+|el\s+)?(?:app|aplicaci[oó]n|programa)\s+", "", nombre, flags=re.I)
    nombre = re.sub(r"\s+(?:para|y|por\s+favor)\b.*$", "", nombre, flags=re.I).strip(" .:\"'")
    return nombre or None


def es_orden_usar(texto):
    """«usa X» / «abre X» / «lanza X» / «ejecuta la app X» / «arranca X». Devuelve el nombre, o None. (No se mete con
    «abre la sala…» ni «abre el buscador», que son pantallas de Kira, ni con «abre el mapa/cuaderno…».)"""
    t = _sin_kira(texto).strip()
    m = re.match(r"\b(usa|abre|abrir|lanza|lanzar|ejecuta|ejecutar|arranca|arrancar|inicia|iniciar)\b\s+(.*)$", t, re.I)
    if not m:
        return None
    nombre = m.group(2).strip()
    nombre = re.sub(r"^(?:la\s+|el\s+)?(?:app|aplicaci[oó]n|programa)\s+", "", nombre, flags=re.I)
    low = nombre.lower()
    # pantallas/órdenes propias de Kira: no son apps externas
    if re.search(r"\b(sala|buscador|mapa|cuaderno|terminal|wifi|ajustes|programando|m[aá]quina|navegador|receta|"
                 r"c[aá]mara|pantalla|puerto|p[aá]gina|web|v[ií]deo|youtube)\b", low):
        return None
    return nombre.strip(" .:\"'") or None


# ---------------- decidir cómo instalar ----------------
def metodo(fuente):
    f = str(fuente or "").strip()
    low = f.lower()
    if ".appimage" in low:
        return "appimage"
    if "github.com" in low or re.match(r"^[\w.-]+/[\w.-]+$", f):
        return "github"
    if low.startswith("http://") or low.startswith("https://"):
        return "descarga"
    return "nombre"               # un nombre suelto: seguramente del sistema (apt) → necesita administrador


# ---------------- qué clase de archivo es (v3.31) ----------------
_EXT_COMPRIMIDO = (".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2", ".tar", ".zip")


def _nombre_fichero(url):
    return str(url or "").split("?")[0].split("#")[0].rstrip("/").split("/")[-1].lower()


def tipo_archivo(url_o_nombre):
    """Qué sé hacer con el archivo al que apunta la URL: 'appimage' | 'deb' | 'comprimido' | 'script' | 'binario' |
    'ajeno' (de Windows/Mac/otro) | '' (no parece un archivo: seguramente una página)."""
    b = _nombre_fichero(url_o_nombre)
    if b.endswith(".appimage"):
        return "appimage"
    if b.endswith(".deb"):
        return "deb"
    if b.endswith(_EXT_COMPRIMIDO):
        return "comprimido"
    if b.endswith((".sh", ".run")):
        return "script"
    if b.endswith((".bin", ".x86_64")):
        return "binario"
    if b.endswith((".rpm", ".exe", ".msi", ".dmg", ".pkg", ".apk", ".app")):
        return "ajeno"
    return ""


def es_descargable(url):
    """¿La URL apunta a un archivo que SÉ instalar (AppImage, .deb, comprimido, script, binario)?"""
    return tipo_archivo(url) in ("appimage", "deb", "comprimido", "script", "binario")


# ---------------- buscar el enlace de descarga en una página (v3.31) ----------------
def enlaces_descarga(html, base_url):
    """Saca de un HTML los enlaces que apuntan a un archivo descargable (AppImage, .deb, .tar.gz, .zip…), ya absolutos
    y sin repetir. Así, cuando el dueño ve una página en el Buscador, Kira encuentra el archivo a bajar."""
    import urllib.parse
    fuera, vistos = [], set()
    for m in re.finditer(r"""href\s*=\s*["']([^"'<>]+)["']""", str(html or ""), re.I):
        href = m.group(1).strip()
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:", "data:")):
            continue
        try:
            url = urllib.parse.urldefrag(urllib.parse.urljoin(base_url, href))[0]
        except ValueError:
            continue
        if not url.lower().startswith(("http://", "https://")):
            continue
        if (es_descargable(url) or tipo_archivo(url) == "ajeno") and url not in vistos:
            vistos.add(url)
            fuera.append(url)
    return fuera


def elegir_descarga(urls, texto=""):
    """De varias URLs de descarga, la MEJOR para un Xubuntu de 64 bits: AppImage primero (sin administrador), luego
    comprimido, luego .deb; evita Windows/Mac/ARM/32 bits/código fuente. None si ninguna sirve."""
    def malo(u):
        l = u.lower()
        return any(x in l for x in ("win32", "win64", "windows", ".exe", ".msi", "-win", "_win", "macos", "mac-", "osx",
                                    ".dmg", "darwin", "aarch64", "arm64", "armv", "armhf", "-arm", "i386", "i686",
                                    "-386", "32bit", "32-bit", "x86.", "-x86-", "source", "-src", "src.", ".rpm",
                                    ".apk", "android"))
    def punt(u):
        l = u.lower()
        p = {"appimage": 100, "comprimido": 60, "deb": 40, "binario": 30, "script": 10}.get(tipo_archivo(u), 0)
        if any(x in l for x in ("linux", "x86_64", "amd64", "x64", "ubuntu", "debian")):
            p += 15
        return p
    buenas = [u for u in urls if not malo(u) and es_descargable(u)]
    buenas.sort(key=punt, reverse=True)
    return buenas[0] if buenas else None


def _traer_texto(url, traer=None):
    """Baja el HTML de una página como texto (para buscar en él el enlace de descarga). `traer` se inyecta en pruebas."""
    if traer is not None:
        return traer(url)
    req = urllib.request.Request(url, headers={"User-Agent": "KiraOS"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(3_000_000).decode("utf-8", "ignore")


def _url_github(fuente):
    f = str(fuente or "").strip()
    if re.match(r"^[\w.-]+/[\w.-]+$", f):
        return "https://github.com/" + f + ".git"
    if f.startswith("http") and "github.com" in f:
        return f if f.endswith(".git") else f.rstrip("/") + ".git"
    return f


def _nombre_de(fuente):
    f = str(fuente or "").strip().rstrip("/").split("?")[0].split("#")[0]
    base = f.split("/")[-1] or "app"
    base = re.sub(r"\.(?:git|appimage|deb|tar\.gz|tgz|tar\.xz|txz|tar\.bz2|tbz2|tar|zip|run|sh|bin|x86_64)$", "",
                  base, flags=re.I)
    return base.replace("_", " ").replace("-", " ").strip()[:60] or "app"


def _carpeta_id(nombre):
    return re.sub(r"[^a-z0-9]+", "_", nombre.lower()).strip("_")[:40] or "app"


def como_arrancar(carpeta):
    """Busca un modo de arrancar lo clonado, por orden: un .py conocido, un AppImage, un .sh, package.json (npm), o un
    ejecutable con permiso de ejecución. Devuelve la lista de argumentos, o None si no sabe."""
    try:
        ficheros = sorted(os.listdir(carpeta))
    except OSError:
        return None
    for nombre in ARRANQUES:
        if os.path.isfile(os.path.join(carpeta, nombre)):
            return ["python3", os.path.join(carpeta, nombre)]
    for f in ficheros:
        if f.lower().endswith(".appimage"):
            return [os.path.join(carpeta, f)]
    for f in ficheros:
        if f.lower().endswith(".sh"):
            return ["bash", os.path.join(carpeta, f)]
    if os.path.isfile(os.path.join(carpeta, "package.json")):
        return ["npm", "start"]
    for f in ficheros:
        p = os.path.join(carpeta, f)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return [p]
    return None


# ---------------- descomprimir con candado + buscar cómo arrancar (v3.31) ----------------
def _dentro(destino, nombre):
    """¿`nombre` (del archivo comprimido) se queda DENTRO de `destino`? (candado contra rutas con «..»)."""
    d = os.path.realpath(destino)
    r = os.path.realpath(os.path.join(destino, nombre))
    return r == d or r.startswith(d + os.sep)


def _extraer(archivo, destino):
    """Descomprime .zip o .tar.* en `destino`, sin dejar que ningún archivo se salga de la carpeta. True si pudo."""
    import tarfile
    import zipfile
    os.makedirs(destino, exist_ok=True)
    try:
        if archivo.lower().endswith(".zip"):
            with zipfile.ZipFile(archivo) as z:
                if any(not _dentro(destino, n) for n in z.namelist()):
                    return False
                z.extractall(destino)
        else:
            with tarfile.open(archivo) as tf:
                for mi in tf.getmembers():
                    if not _dentro(destino, mi.name):
                        return False
                    if (mi.issym() or mi.islnk()) and not _dentro(destino, os.path.join(os.path.dirname(mi.name),
                                                                                         mi.linkname)):
                        return False
                try:
                    tf.extractall(destino, filter="data")     # Python 3.12+: filtro de seguridad
                except TypeError:
                    tf.extractall(destino)
        return True
    except Exception:                                         # noqa: BLE001 - archivo dañado / formato raro
        return False


def _desktop_exec(carpeta):
    """Lee un .desktop (p. ej. de un .deb en usr/share/applications) y busca el binario de su «Exec=» dentro de la
    carpeta. Devuelve [ruta] o None."""
    for raiz, _d, fich in os.walk(carpeta):
        for f in fich:
            if not f.lower().endswith(".desktop"):
                continue
            try:
                txt = open(os.path.join(raiz, f), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            m = re.search(r"(?mi)^\s*Exec\s*=\s*(.+)$", txt)
            if not m:
                continue
            cmd = m.group(1).split()
            base = os.path.basename(cmd[0]) if cmd else ""
            if not base or base in ("sh", "bash", "env", "python", "python3"):
                base = os.path.basename(cmd[1]) if len(cmd) > 1 else base
            if not base:
                continue
            for r2, _d2, f2 in os.walk(carpeta):
                if base in f2:
                    p = os.path.join(r2, base)
                    if os.path.isfile(p):
                        try:
                            os.chmod(p, 0o755)
                        except OSError:
                            pass
                        return [p]
    return None


def buscar_lanzador(carpeta):
    """Cómo arrancar algo descomprimido/extraído (comprimido o .deb): un .desktop (Exec→binario), un .py conocido, un
    AppImage, un binario en usr/bin|usr/games|opt|bin, o un .sh. Devuelve la lista de argumentos, o None."""
    d = _desktop_exec(carpeta)
    if d:
        return d
    binarios = []
    for raiz, dirs, fich in os.walk(carpeta):
        if raiz[len(carpeta):].count(os.sep) > 4:
            dirs[:] = []
            continue
        for nombre in ARRANQUES:
            if nombre in fich:
                return ["python3", os.path.join(raiz, nombre)]
        for f in fich:
            if f.lower().endswith(".appimage"):
                p = os.path.join(raiz, f)
                try:
                    os.chmod(p, 0o755)
                except OSError:
                    pass
                return [p]
        rel = raiz.replace("\\", "/").lower()
        pri = 0
        for i, clave in enumerate(("/usr/bin", "/usr/games", "/usr/local/bin", "/opt", "/bin")):
            if clave in rel:
                pri = 6 - i
                break
        for f in fich:
            p = os.path.join(raiz, f)
            if os.path.isfile(p) and os.access(p, os.X_OK) and not f.lower().endswith((".so", ".txt", ".md", ".desktop")):
                binarios.append((pri, p))
    if binarios:
        binarios.sort(reverse=True)
        return [binarios[0][1]]
    for raiz, _d, fich in os.walk(carpeta):
        for f in fich:
            if f.lower().endswith(".sh"):
                return ["bash", os.path.join(raiz, f)]
    return None


# ---------------- analizar ANTES de instalar (defensa) ----------------
_PELIGRO = [
    (r"rm\s+-rf\s+(/|~|\$home|\*|/\*)", "borra archivos en bloque (rm -rf)"),
    (r"(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh\b", "descarga y ejecuta directo de internet (curl|bash)"),
    (r"/dev/tcp/|\bnc\s+-e\b|bash\s+-i\s*>\s*&", "parece una puerta trasera / shell inversa"),
    (r"stratum\+tcp|xmrig|minerd|cryptonight", "parece minar criptomonedas"),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "bomba de forks"),
    (r"id_rsa|authorized_keys|\.ssh/", "toca las llaves SSH"),
    (r"(exec|eval)\s*\(\s*(requests|urllib|urlopen|__import__)", "ejecuta código bajado de internet"),
    (r"\bmkfs\b|dd\s+if=.*of=/dev/", "escribe sobre el disco entero"),
]
_OJO = [
    (r"\bsudo\b", "usa sudo (administrador)"),
    (r"os\.system\(|subprocess\.|Popen\(", "ejecuta comandos del sistema"),
    (r"(^|[^\w])/etc/|/boot/|/usr/s?bin", "toca carpetas del sistema"),
    (r"chmod\s+(777|\+x)|chown\b", "cambia permisos"),
    (r"crontab|systemctl|/etc/cron|\.bashrc|autostart", "se engancha al arranque / tareas programadas"),
    (r"base64\s+-d|b64decode", "tiene algo codificado en base64"),
    (r"pip\s+install|npm\s+install|apt(-get)?\s+install", "quiere instalar más cosas"),
]
_TEXTO_EXT = (".py", ".sh", ".bash", ".js", ".ts", ".json", ".txt", ".md", ".cfg", ".ini", ".yml", ".yaml",
              ".toml", ".c", ".cpp", ".h", ".rb", ".pl", ".php", ".go", ".rs", ".java", ".bat", ".ps1", ".mk", "")


def _es_texto(ruta):
    if os.path.splitext(ruta)[1].lower() not in _TEXTO_EXT:
        return False
    try:
        if os.path.getsize(ruta) > 200000:
            return False
        with open(ruta, "rb") as f:
            cacho = f.read(4096)
        return b"\x00" not in cacho
    except OSError:
        return False


def analizar(carpeta, max_archivos=500):
    """v3.29: revisa lo descargado ANTES de dejarlo instalado, buscando señales feas (curl|bash, rm -rf, shell inversa,
    minería, tocar las llaves SSH, código bajado y ejecutado…). Devuelve {nivel: ok|ojo|peligro, hallazgos, binarios,
    archivos, resumen}. HONESTO: pilla lo obvio, NO es garantía (el malware bien hecho se esconde)."""
    import re as _re
    hallazgos, binarios, archivos = [], 0, 0
    nivel = "ok"
    for raiz, _dirs, ficheros in os.walk(carpeta):
        if "/.git" in raiz.replace("\\", "/"):
            continue
        for f in ficheros:
            ruta = os.path.join(raiz, f)
            archivos += 1
            if archivos > max_archivos:
                break
            if not _es_texto(ruta):
                if os.path.isfile(ruta) and os.access(ruta, os.X_OK):
                    binarios += 1
                continue
            try:
                with open(ruta, encoding="utf-8", errors="ignore") as fh:
                    txt = fh.read()
            except OSError:
                continue
            low = txt.lower()
            rel = os.path.relpath(ruta, carpeta)
            for patron, motivo in _PELIGRO:
                if _re.search(patron, low):
                    hallazgos.append(("peligro", rel, motivo))
                    nivel = "peligro"
            for patron, motivo in _OJO:
                if _re.search(patron, low):
                    hallazgos.append(("ojo", rel, motivo))
    if nivel != "peligro" and (binarios or any(h[0] == "ojo" for h in hallazgos)):
        nivel = "ojo"
    # resumen corto, sin repetir motivos
    motivos_p = []
    for sev, _rel, mot in hallazgos:
        if sev == "peligro" and mot not in motivos_p:
            motivos_p.append(mot)
    motivos_o = []
    for sev, _rel, mot in hallazgos:
        if sev == "ojo" and mot not in motivos_o:
            motivos_o.append(mot)
    if nivel == "peligro":
        resumen = "⚠ Encontré cosas PELIGROSAS: " + "; ".join(motivos_p[:5]) + "."
    elif nivel == "ojo":
        extra = (f" y {binarios} archivo(s) que no puedo mirar por dentro (binarios)" if binarios else "")
        resumen = "Ojo: " + "; ".join((motivos_o or ["nada grave"])[:4]) + extra + "."
    else:
        resumen = "No vi nada raro (pero un análisis así no es garantía)."
    return {"nivel": nivel, "hallazgos": hallazgos, "binarios": binarios, "archivos": archivos, "resumen": resumen}


def quiere_forzar(texto):
    """¿El dueño dice que la instale AUNQUE haya avisado? («igualmente», «de todas formas», «fórzala»…)."""
    import re as _re
    return bool(_re.search(r"\b(igualmente|de\s+todas\s+(formas|maneras)|f[oó]rzal[ao]|forzar|aunque\s+sea\s+peligros)\b",
                           str(texto or ""), _re.I))


# ---------------- lo que una app NECESITA para funcionar (v3.32) ----------------
def _lee(ruta):
    try:
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            return f.read(200000)
    except OSError:
        return ""


def _pip_de_requirements(txt):
    libs = []
    for linea in str(txt or "").splitlines():
        l = linea.strip()
        if not l or l.startswith(("#", "-", "git+", "http")):
            continue
        m = re.match(r"^([A-Za-z0-9_.][A-Za-z0-9_.\-]*)", l)
        if m:
            libs.append(m.group(1))
    return libs


def dependencias(carpeta):
    """Mira qué le hace falta a la app para funcionar, SIN instalar nada: paquetes de Python (requirements.txt,
    pyproject.toml, setup.py) y de JavaScript (package.json). Devuelve {pip:[...], archivo_req, npm:bool, tiene:bool,
    resumen:str}. PURO."""
    pip, archivo_req, npm = [], None, False
    for raiz, dirs, fich in os.walk(carpeta):
        if raiz[len(carpeta):].count(os.sep) > 2 or "/node_modules" in raiz.replace("\\", "/"):
            dirs[:] = []
            continue
        for f in fich:
            fl = f.lower()
            ruta = os.path.join(raiz, f)
            if fl == "requirements.txt" and not archivo_req:
                archivo_req = ruta
                pip += _pip_de_requirements(_lee(ruta))
            elif fl == "pyproject.toml" and not pip:
                m = re.search(r"dependencies\s*=\s*\[(.*?)\]", _lee(ruta), re.S)
                if m:
                    pip += [re.match(r"[A-Za-z0-9_.\-]+", x).group(0)
                            for x in re.findall(r'["\']([A-Za-z0-9_.][^"\']*)', m.group(1))]
            elif fl == "setup.py" and not pip:
                m = re.search(r"install_requires\s*=\s*\[(.*?)\]", _lee(ruta), re.S)
                if m:
                    pip += [re.match(r"[A-Za-z0-9_.\-]+", x).group(0)
                            for x in re.findall(r'["\']([A-Za-z0-9_.][^"\']*)', m.group(1))]
            elif fl == "package.json" and not npm and '"dependencies"' in _lee(ruta):
                npm = True
    pip = sorted(dict.fromkeys(p for p in pip if p.lower() not in ("python", "python3", "pip")))
    partes = []
    if pip:
        partes.append("paquetes de Python: " + ", ".join(pip[:8]) + ("…" if len(pip) > 8 else ""))
    if npm:
        partes.append("paquetes de JavaScript (npm)")
    return {"pip": pip, "archivo_req": archivo_req, "npm": npm, "tiene": bool(pip or npm),
            "resumen": "; ".join(partes)}


def instalar_dependencias(carpeta, correr=None, al_paso=None, con_npm=True):
    """Descarga e instala lo que la app necesita, SIN administrador (pip --user, npm en su carpeta). Se llama SOLO
    cuando el dueño lo confirma. Devuelve {ok, mensaje}. Lo que necesite administrador (una librería del sistema)
    se lo dice al dueño (Terminal + su contraseña)."""
    correr = correr or _correr_defecto
    paso = al_paso or (lambda _t: None)
    dep = dependencias(carpeta)
    if not dep["tiene"]:
        return {"ok": True, "mensaje": "No le veo dependencias que descargar; debería funcionar tal cual."}
    hechos, avisos = [], []
    if dep["pip"]:
        paso("Descargando los paquetes de Python…")
        args = (["pip3", "install", "--user", "-r", dep["archivo_req"]] if dep["archivo_req"]
                else ["pip3", "install", "--user"] + dep["pip"])
        try:
            rc, salida = correr(args, cwd=carpeta, timeout=900)
        except Exception as e:                        # noqa: BLE001
            rc, salida = 127, str(e)
        if rc == 0:
            hechos.append("los paquetes de Python (" + ", ".join(dep["pip"][:6]) + ")")
        elif rc == 127 or "No module named pip" in salida or "not found" in salida.lower():
            avisos.append("no tengo pip para Python; en la Terminal:  sudo apt install python3-pip")
        else:
            falta = faltan_por_error(salida)
            extra = (" Parece que necesita una librería del sistema: " + falta["consejo"]) if falta and falta["tipo"] == "sistema" else ""
            avisos.append("algún paquete de Python no se pudo bajar solo." + extra + " (" + salida[-160:].strip() + ")")
    if dep["npm"] and con_npm:
        paso("Descargando los paquetes de JavaScript (npm)…")
        try:
            rc, salida = correr(["npm", "install"], cwd=carpeta, timeout=900)
        except Exception as e:                        # noqa: BLE001
            rc, salida = 127, str(e)
        if rc == 0:
            hechos.append("los paquetes de JavaScript (npm)")
        else:
            avisos.append("npm no pudo instalar (¿está node/npm? en la Terminal:  sudo apt install npm)")
    msg = ("Descargué " + " y ".join(hechos) + " (sin tocar el sistema). " if hechos else "")
    if avisos:
        msg += "Ojo: " + "; ".join(avisos) + "."
    return {"ok": bool(hechos) or not avisos, "mensaje": msg or "No necesité descargar nada."}


def faltan_por_error(salida):
    """De un error al arrancar/instalar, saca qué falta: un módulo de Python (→ pip), una librería del sistema o una
    orden (→ apt, con contraseña). Devuelve {tipo:'pip'|'sistema', que, consejo} o None."""
    t = str(salida or "")
    m = re.search(r"No module named ['\"]?([A-Za-z0-9_.]+)", t)
    if m:
        lib = m.group(1).split(".")[0]
        return {"tipo": "pip", "que": lib, "consejo": "pip3 install --user " + lib}
    m = re.search(r"error while loading shared libraries:\s*([\w.+-]+\.so[\w.]*)", t)
    if m:
        return {"tipo": "sistema", "que": m.group(1),
                "consejo": "en la Terminal, instala la librería del sistema que la trae:  sudo apt install …"}
    m = re.search(r"([\w.+-]+): (?:command not found|not found)", t)
    if m:
        return {"tipo": "sistema", "que": m.group(1), "consejo": "en la Terminal:  sudo apt install " + m.group(1)}
    return None


def aviso_dependencias(dep, nombre):
    """El aviso que se le añade al mensaje de instalar: qué necesita y cómo pedir que lo descargue (con tu permiso)."""
    if not dep or not dep.get("tiene"):
        return ""
    return (f" Además, para funcionar necesita {dep['resumen']}. ¿Quieres que lo descargue (sin administrador)? "
            f"Dime «descarga las dependencias de {nombre}».")


# ---------------- instalar ----------------
def _correr_defecto(args, cwd=None, timeout=600):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _bajar_defecto(url, destino):
    req = urllib.request.Request(url, headers={"User-Agent": "KiraOS"})
    with urllib.request.urlopen(req, timeout=120) as r, open(destino, "wb") as f:
        while True:
            trozo = r.read(65536)
            if not trozo:
                break
            f.write(trozo)
    return os.path.getsize(destino)


def _revisar(carpeta, nombre, fuente, forzar, met):
    """v3.29: analiza lo descargado ANTES de dejarlo instalado. Si es PELIGROSO y no se fuerza, devuelve el aviso (para
    borrarlo y no instalarlo); si no, devuelve None y se sigue. Un AppImage/binario no se puede mirar por dentro: avisa
    pero no bloquea (es cosa del dueño fiarse de la fuente)."""
    an = analizar(carpeta)
    if an["nivel"] == "peligro" and not forzar:
        return {"ok": False, "admin": False, "peligro": True, "analisis": an, "nombre": nombre, "lanzar": None,
                "carpeta": "", "mensaje": (f"He mirado «{nombre}» antes de instalarla y NO me fío: {an['resumen']} "
                                           f"Por tu seguridad no la instalo. Si aun así la quieres, dime: «instala "
                                           f"{fuente} igualmente».")}
    return None


def instalar(fuente, base=None, correr=None, bajar=None, al_paso=None, forzar=False):
    """Instala la app de `fuente` (SIN administrador). ANTES de dejarla, la ANALIZA (v3.29): si encuentra algo peligroso
    y no se fuerza, no la instala. Devuelve {ok, nombre, lanzar, carpeta, mensaje, admin, analisis}.
    `admin=True` = hace falta la Terminal con la contraseña del dueño (no se hace sola)."""
    base = base or BASE_POR_DEFECTO
    correr = correr or _correr_defecto
    bajar = bajar or _bajar_defecto
    paso = al_paso or (lambda _t: None)
    met = metodo(fuente)
    nombre = _nombre_de(fuente)
    carpeta = os.path.join(base, _carpeta_id(nombre))

    if met == "nombre":
        return {"ok": False, "admin": True, "nombre": nombre, "lanzar": None, "carpeta": "",
                "mensaje": (f"«{fuente}» parece un programa del sistema y para instalarlo necesito administrador. Por "
                            "seguridad no lo hago sola: ábreme la Terminal y escribe  sudo apt install " + str(fuente) +
                            "  — Xubuntu te pedirá TU contraseña. (O dime la dirección de GitHub o un AppImage y lo "
                            "instalo yo sin contraseña.)")}

    try:
        os.makedirs(base, exist_ok=True)
    except OSError as e:
        return {"ok": False, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": "",
                "mensaje": f"No pude preparar la carpeta de apps: {e}"}

    if met == "github":
        if os.path.isdir(carpeta):
            import shutil
            shutil.rmtree(carpeta, ignore_errors=True)
        paso(f"Clonando {nombre} de GitHub…")
        try:
            rc, salida = correr(["git", "clone", "--depth", "1", _url_github(fuente), carpeta], timeout=900)
        except Exception as e:                       # noqa: BLE001
            return {"ok": False, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": "",
                    "mensaje": f"No pude clonar {nombre}: {e}"}
        if rc != 0:
            return {"ok": False, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": "",
                    "mensaje": f"No pude clonar {nombre} de GitHub (¿existe el repo? ¿hay internet?). {salida[-200:]}"}
        paso("La reviso antes de instalarla…")
        bloqueo = _revisar(carpeta, nombre, fuente, forzar, "github")   # v3.29: analiza ANTES de dejarla
        if bloqueo:
            import shutil
            shutil.rmtree(carpeta, ignore_errors=True)
            return bloqueo
        an = analizar(carpeta)
        dep = dependencias(carpeta)                   # v3.32: qué le hace falta para funcionar (no se instala aún)
        lanzar = como_arrancar(carpeta)
        nota = " (" + an["resumen"] + ")" if an["nivel"] != "ok" else ""
        if not lanzar:
            return {"ok": True, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": carpeta, "analisis": an,
                    "dependencias": dep,
                    "mensaje": (f"He descargado {nombre} en tu carpeta de apps, pero no veo claro cómo arrancarla "
                                "(mira su README). La dejo en el escritorio igualmente." + nota)}
        return {"ok": True, "admin": False, "nombre": nombre, "lanzar": lanzar, "carpeta": carpeta, "analisis": an,
                "dependencias": dep,
                "mensaje": f"{nombre} instalada (de GitHub, revisada, sin tocar el sistema). La tienes en el escritorio." + nota}

    # appimage / descarga directa (AppImage, binario, script, comprimido, .deb) — v3.31: «sea lo que sea»
    if met in ("appimage", "descarga"):
        tipo = tipo_archivo(fuente)
        if tipo == "":                               # no parece un archivo: será una página
            return {"ok": False, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": "",
                    "mensaje": ("Eso parece una página web, no un archivo. Ábrela en el Buscador y, cuando veas el "
                                "programa, dime «descarga e instala esto»; o pégame el enlace directo del archivo "
                                "(.AppImage, .deb, .tar.gz, .zip…).")}
        if tipo == "ajeno":
            return {"ok": False, "admin": True, "nombre": nombre, "lanzar": None, "carpeta": "",
                    "mensaje": (f"«{_nombre_fichero(fuente)}» no es un programa para Xubuntu (parece de Windows, Mac, "
                                "Android u otro sistema). Busca la versión para Linux (AppImage, .deb o .tar.gz) y te "
                                "la instalo.")}
        os.makedirs(carpeta, exist_ok=True)
        crudo = str(fuente).split("?")[0].split("#")[0].rstrip("/").split("/")[-1]   # conserva mayúsculas del archivo
        nomfich = re.sub(r"[^\w.\-]", "_", crudo or (nombre + ".bin"))
        destino = os.path.join(carpeta, nomfich)
        paso(f"Descargando {nombre}…")
        try:
            bajar(fuente, destino)
        except Exception as e:                       # noqa: BLE001
            import shutil
            shutil.rmtree(carpeta, ignore_errors=True)
            return {"ok": False, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": "",
                    "mensaje": f"No pude descargar {nombre}: {e}"}

        if tipo in ("appimage", "binario"):
            try:
                os.chmod(destino, 0o755)
            except OSError:
                pass
            comoes = "AppImage" if tipo == "appimage" else "binario"
            return {"ok": True, "admin": False, "nombre": nombre, "lanzar": [destino], "carpeta": carpeta,
                    "analisis": {"nivel": "ojo", "resumen": "es un binario y no puedo mirarlo por dentro"},
                    "mensaje": (f"{nombre} descargada (sin tocar el sistema). La tienes en el escritorio. Ojo: es un "
                                f"{comoes} y no puedo revisarlo por dentro como un repo; fíate de quién te lo dio.")}

        if tipo == "script":                         # un instalador .sh/.run (texto: lo puedo analizar)
            bloqueo = _revisar(carpeta, nombre, fuente, forzar, "script")
            if bloqueo:
                import shutil
                shutil.rmtree(carpeta, ignore_errors=True)
                return bloqueo
            an = analizar(carpeta)
            try:
                os.chmod(destino, 0o755)
            except OSError:
                pass
            return {"ok": True, "admin": False, "nombre": nombre, "lanzar": ["bash", destino], "carpeta": carpeta,
                    "analisis": an,
                    "mensaje": (f"{nombre} descargada. Es un instalador (script): al pulsar su icono se ejecuta y "
                                "puede pedirte TU contraseña si necesita administrador. "
                                + (an["resumen"] if an["nivel"] != "ok" else ""))}

        # comprimido o .deb → extraer a <carpeta>/contenido (sin administrador) y buscar cómo arrancarlo
        raiz = os.path.join(carpeta, "contenido")
        paso("Descomprimiendo…")
        if tipo == "deb":
            try:
                rc, _salida = correr(["dpkg-deb", "-x", destino, raiz], timeout=300)
            except Exception:                        # noqa: BLE001 - no está dpkg-deb
                rc = 127
            if rc != 0:
                return {"ok": False, "admin": True, "nombre": nombre, "lanzar": None, "carpeta": carpeta,
                        "mensaje": (f"Descargué {nombre} (.deb), pero para instalarlo del todo necesito administrador. "
                                    "Ábreme la Terminal y escribe  sudo dpkg -i " + destino + "  (si se queja de "
                                    "dependencias, luego  sudo apt -f install ). Te pedirá TU contraseña.")}
        else:
            if not _extraer(destino, raiz):
                import shutil
                shutil.rmtree(carpeta, ignore_errors=True)
                return {"ok": False, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": "",
                        "mensaje": f"No pude descomprimir {nombre} (¿archivo dañado o formato raro?)."}
        bloqueo = _revisar(raiz, nombre, fuente, forzar, tipo)
        if bloqueo:
            import shutil
            shutil.rmtree(carpeta, ignore_errors=True)
            return bloqueo
        an = analizar(raiz)
        dep = dependencias(raiz)                       # v3.32: qué le hace falta para funcionar (no se instala aún)
        lanzar = buscar_lanzador(raiz)
        nota = " (" + an["resumen"] + ")" if an["nivel"] != "ok" else ""
        if not lanzar:
            manual = ("  Para instalarlo del todo, en la Terminal:  sudo dpkg -i " + destino if tipo == "deb" else "")
            return {"ok": True, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": carpeta, "analisis": an,
                    "dependencias": dep,
                    "mensaje": (f"Descargué y extraje {nombre}, pero no veo claro cómo arrancarlo (mira su README)." +
                                manual + " Lo dejo en el escritorio igualmente." + nota)}
        como = ("(.deb extraído en tu carpeta, sin administrador; alguna app así puede fallar por librerías del "
                "sistema)" if tipo == "deb" else "(comprimido, revisado, sin tocar el sistema)")
        return {"ok": True, "admin": False, "nombre": nombre, "lanzar": lanzar, "carpeta": carpeta, "analisis": an,
                "dependencias": dep,
                "mensaje": f"{nombre} instalada {como}. La tienes en el escritorio." + nota}

    return {"ok": False, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": "",
            "mensaje": f"No sé instalar «{fuente}»."}


def lanzar(acceso, correr=None):
    """USA la app (clic en su icono o «usa X»): la arranca en la sesión del dueño. Devuelve {ok, mensaje}."""
    lan = (acceso or {}).get("lanzar") or []
    carpeta = (acceso or {}).get("carpeta") or None
    titulo = (acceso or {}).get("titulo") or "la app"
    if not lan:
        return {"ok": False, "mensaje": f"No sé cómo arrancar {titulo} (no vi cómo se ejecuta al instalarla)."}
    if correr is not None:                            # pruebas
        try:
            correr(lan, cwd=carpeta, timeout=5)
            return {"ok": True, "mensaje": f"Abriendo {titulo}…"}
        except Exception as e:                        # noqa: BLE001
            return {"ok": False, "mensaje": f"No pude abrir {titulo}: {e}"}
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":0")
    try:
        subprocess.Popen(lan, cwd=carpeta, env=env, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True, "mensaje": f"Abriendo {titulo}…"}
    except Exception as e:                            # noqa: BLE001
        return {"ok": False, "mensaje": f"No pude abrir {titulo}: {e}"}
