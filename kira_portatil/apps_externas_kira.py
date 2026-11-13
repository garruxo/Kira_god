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


def _url_github(fuente):
    f = str(fuente or "").strip()
    if re.match(r"^[\w.-]+/[\w.-]+$", f):
        return "https://github.com/" + f + ".git"
    if f.startswith("http") and "github.com" in f:
        return f if f.endswith(".git") else f.rstrip("/") + ".git"
    return f


def _nombre_de(fuente):
    f = str(fuente or "").strip().rstrip("/")
    base = re.sub(r"\.git$|\.appimage$", "", f.split("/")[-1], flags=re.I) or "app"
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
        lanzar = como_arrancar(carpeta)
        nota = " (" + an["resumen"] + ")" if an["nivel"] != "ok" else ""
        if not lanzar:
            return {"ok": True, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": carpeta, "analisis": an,
                    "mensaje": (f"He descargado {nombre} en tu carpeta de apps, pero no veo claro cómo arrancarla "
                                "(mira su README). La dejo en el escritorio igualmente." + nota)}
        return {"ok": True, "admin": False, "nombre": nombre, "lanzar": lanzar, "carpeta": carpeta, "analisis": an,
                "mensaje": f"{nombre} instalada (de GitHub, revisada, sin tocar el sistema). La tienes en el escritorio." + nota}

    # appimage / descarga directa
    if met in ("appimage", "descarga"):
        os.makedirs(carpeta, exist_ok=True)
        nomfich = fuente.split("/")[-1] or (nombre + ".AppImage")
        destino = os.path.join(carpeta, re.sub(r"[^\w.\-]", "_", nomfich))
        paso(f"Descargando {nombre}…")
        try:
            bajar(fuente, destino)
        except Exception as e:                       # noqa: BLE001
            return {"ok": False, "admin": False, "nombre": nombre, "lanzar": None, "carpeta": "",
                    "mensaje": f"No pude descargar {nombre}: {e}"}
        try:
            os.chmod(destino, 0o755)
        except OSError:
            pass
        return {"ok": True, "admin": False, "nombre": nombre, "lanzar": [destino], "carpeta": carpeta,
                "analisis": {"nivel": "ojo", "resumen": "es un binario y no puedo mirarlo por dentro"},
                "mensaje": (f"{nombre} descargada (sin tocar el sistema). La tienes en el escritorio. Ojo: es un AppImage "
                            "(un binario) y no puedo revisarlo por dentro como un repo; fíate de quién te lo dio.")}

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
