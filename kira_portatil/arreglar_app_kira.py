"""arreglar_app_kira.py — v3.81: si un programa que Kira instaló NO ARRANCA, Kira lo estudia y lo arregla SOLA.

Pedido del dueño: «si el programa no arranca, que estudie hasta que arranque y que lo haga automáticamente, sin decir
nada; si reconoce que no se puede abrir, estudia cómo hacerlo desde la misma página donde lo ha descargado».

Cómo funciona:
  1. Al abrir una app instalada por Kira, su salida se guarda en un registro y se VIGILA unos segundos.
  2. Si se cierra con error, Kira lee el error y prueba arreglos, uno tras otro, volviendo a abrirla tras cada uno:
       permiso de ejecución · AppImage sin FUSE (se abre sin montarse) · paquetes de Python/JavaScript que faltan ·
       librerías u órdenes del sistema (solo si el dueño ya dio el permiso de administrador UNA vez, v3.33) ·
       otra forma de arrancarla que haya en su carpeta · las órdenes que dicen su README y la PÁGINA de donde se
       descargó (y, si está, lo que sugiera su cerebro).
  3. En cuanto arranca (sigue viva pasados unos segundos), se queda abierta, Kira apunta la nueva forma de lanzarla
     y deja UN aviso al final con lo que hizo. Si no lo consigue, el aviso dice el error y lo que probó.

CANDADOS (lo que sale del README, de la página o del cerebro pasa por `orden_segura`, nada más):
  - solo `chmod +x` de archivos de SU carpeta, `pip install` de nombres de paquete (para tu usuario), `npm install`
    en su carpeta, y `apt install` de paquetes que existen y SOLO con el permiso que ya diste (sudo -n);
  - arrancar solo archivos de SU carpeta (python3, bash, node, el ejecutable, npm start);
  - nunca shells, tuberías, `curl | bash`, borrar, `sudo` para otra cosa, ni rutas fuera de su carpeta.
"""
import html as _html
import os
import re
import shlex
import shutil
import subprocess
import threading
import time

REGISTROS = os.path.expanduser("~/kira_portatil/apps_registro")
ESPERA = 8.0                    # segundos que tiene que seguir viva para contar como «ha arrancado»
MAX_INTENTOS = 8
_NOMBRE_PIP = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]*(\[[A-Za-z0-9,_\-]+\])?(?:[<>=!~]=?[0-9A-Za-z.*+\-]+)?$")
_NOMBRE_APT = re.compile(r"^[a-z0-9][a-z0-9+.\-]{1,60}$")

MODULO_A_PIP = {                # el nombre del import no siempre es el del paquete
    "cv2": "opencv-python", "PIL": "pillow", "yaml": "pyyaml", "sklearn": "scikit-learn", "bs4": "beautifulsoup4",
    "Crypto": "pycryptodome", "dateutil": "python-dateutil", "dotenv": "python-dotenv", "serial": "pyserial",
    "usb": "pyusb", "magic": "python-magic", "OpenGL": "PyOpenGL", "wx": "wxPython", "attr": "attrs",
    "skimage": "scikit-image", "Levenshtein": "python-Levenshtein", "jwt": "PyJWT", "telegram": "python-telegram-bot",
    "discord": "discord.py", "docx": "python-docx", "pptx": "python-pptx", "fitz": "pymupdf", "gi": None,
    "tkinter": None, "_tkinter": None,
}
MODULO_A_APT = {"gi": "python3-gi", "tkinter": "python3-tk", "_tkinter": "python3-tk", "dbus": "python3-dbus",
                "apt": "python3-apt", "PyQt5": "python3-pyqt5", "PyQt6": "python3-pyqt6"}
ORDEN_A_APT = {"node": "nodejs", "nodejs": "nodejs", "npm": "npm", "java": "default-jre", "python": "python-is-python3",
               "pip3": "python3-pip", "pip": "python3-pip", "git": "git", "make": "make", "gcc": "gcc",
               "ffmpeg": "ffmpeg", "wine": "wine", "xdg-open": "xdg-utils", "zenity": "zenity", "curl": "curl",
               "wget": "wget", "unzip": "unzip", "electron": None}
LIB_A_APT = {"libfuse.so.2": ["libfuse2t64", "libfuse2"], "libgtk-3.so.0": ["libgtk-3-0t64", "libgtk-3-0"],
             "libnss3.so": ["libnss3"], "libasound.so.2": ["libasound2t64", "libasound2"], "libGL.so.1": ["libgl1"],
             "libgbm.so.1": ["libgbm1"], "libxss.so.1": ["libxss1"], "libatk-bridge-2.0.so.0":
             ["libatk-bridge2.0-0t64", "libatk-bridge2.0-0"], "libdrm.so.2": ["libdrm2"], "libsdl2-2.0.so.0":
             ["libsdl2-2.0-0"], "libportaudio.so.2": ["libportaudio2"], "libQt5Widgets.so.5": ["libqt5widgets5t64",
             "libqt5widgets5"], "libwebkit2gtk-4.0.so.37": ["libwebkit2gtk-4.0-37"], "libssl.so.3": ["libssl3t64",
             "libssl3"], "libpython3": ["libpython3-dev"]}


# ---------------- ¿arrancó? ----------------
def ruta_registro(app_id):
    os.makedirs(REGISTROS, mode=0o700, exist_ok=True)
    return os.path.join(REGISTROS, re.sub(r"[^\w.-]", "_", str(app_id or "app"))[:60] + ".log")


def leer_registro(ruta, tope=65536):
    try:
        with open(ruta, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - tope))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def lanzar_con_registro(lanzar, carpeta, ruta, popen=None, entorno=None):
    """Abre la app guardando lo que escribe (salida y errores) en `ruta`. Devuelve el proceso."""
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":0")
    env.update(entorno or {})
    f = open(ruta, "wb")
    try:
        os.chmod(ruta, 0o600)
    except OSError:
        pass
    try:
        return (popen or subprocess.Popen)(list(lanzar), cwd=carpeta or None, env=env, start_new_session=True,
                                           stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    finally:
        f.close()


def esperar_arranque(p, espera=ESPERA, dormir=time.sleep):
    """(arrancó, código). Arranca = sigue viva pasados `espera` s, o se acabó con código 0 (programas de órdenes)."""
    fin = time.time() + espera
    while time.time() < fin:
        rc = p.poll()
        if rc is not None:
            return _bien(rc), rc
        dormir(0.25)
    rc = p.poll()
    return (rc is None or _bien(rc)), rc


def _bien(rc):
    """0 = acabó bien; cerrada por alguien (tú, «cierra X»: SIGTERM/SIGKILL/SIGINT/SIGHUP) tampoco es un fallo."""
    return rc == 0 or rc in (-15, -9, -2, -1)


# ---------------- leer el error ----------------
def diagnostico(salida, lanzar=()):
    """Qué le pasa, según lo que escribió al fallar. Lista de {tipo, que} por orden de probabilidad. PURO."""
    t = str(salida or "")
    d = []
    prim = str(lanzar[0]) if lanzar else ""
    if re.search(r"(?i)permission denied|permiso denegado", t) or (prim and os.path.isfile(prim)
                                                                    and not os.access(prim, os.X_OK)):
        d.append({"tipo": "permiso", "que": prim})
    if re.search(r"(?i)fuse|libfuse\.so\.2|dlopen\(\): error loading libfuse|AppImages require FUSE", t) or \
            (prim.lower().endswith(".appimage") and re.search(r"(?i)cannot mount|squashfs", t)):
        d.append({"tipo": "appimage_fuse", "que": prim})
    for m in re.finditer(r"No module named ['\"]?([A-Za-z0-9_.]+)", t):
        d.append({"tipo": "modulo", "que": m.group(1).split(".")[0]})
    if re.search(r"(?i)cannot find module|ERR_MODULE_NOT_FOUND|node_modules", t):
        d.append({"tipo": "npm", "que": ""})
    for m in re.finditer(r"error while loading shared libraries:\s*([\w.+-]+\.so[\w.]*)", t):
        d.append({"tipo": "libreria", "que": m.group(1)})
    for m in re.finditer(r"(?m)(?:^|[\s:/])([\w.+-]+): (?:command not found|not found|orden no encontrada)", t):
        d.append({"tipo": "orden", "que": m.group(1)})
    if re.search(r"(?i)exec format error|cannot execute binary file", t):
        d.append({"tipo": "arquitectura", "que": prim})
    m = re.search(r"GLIBC_([\d.]+)' not found", t)
    if m:
        d.append({"tipo": "glibc", "que": m.group(1)})
    if re.search(r"(?i)externally[- ]managed[- ]environment", t):
        d.append({"tipo": "pep668", "que": ""})
    vistos, sal = set(), []
    for x in d:
        k = (x["tipo"], x["que"])
        if k not in vistos:
            vistos.add(k)
            sal.append(x)
    return sal


def ultima_linea_error(salida):
    lineas = [l.strip() for l in str(salida or "").splitlines() if l.strip()]
    for l in reversed(lineas):
        if re.search(r"(?i)error|not found|no module|denied|cannot|failed|traceback|exception", l):
            return l[:200]
    return (lineas[-1][:200] if lineas else "se cerró sin decir nada")


# ---------------- candado: solo órdenes seguras ----------------
def _dentro(carpeta, ruta):
    if not carpeta:
        return False
    c = os.path.realpath(carpeta)
    r = os.path.realpath(ruta if os.path.isabs(ruta) else os.path.join(carpeta, ruta))
    return r == c or r.startswith(c + os.sep)


def _abs(carpeta, ruta):
    return os.path.realpath(ruta if os.path.isabs(ruta) else os.path.join(carpeta, ruta))


def orden_segura(args, carpeta, admin=False):
    """(tipo, args_normalizados) o None. tipo: 'arreglo' (se ejecuta y luego se reintenta) o 'lanzar' (otra forma
    de arrancarla). Lo que no encaja aquí NO se ejecuta nunca."""
    if isinstance(args, str):
        if re.search(r"[|;&<>`$\\]|\(\)|\$\(", args):
            return None
        try:
            args = shlex.split(args)
        except ValueError:
            return None
    a = [str(x) for x in args if str(x).strip()]
    if not a or len(a) > 20:
        return None
    if a[0] in ("python", "python3") and len(a) >= 3 and a[1] == "-m" and a[2] in ("pip", "pip3"):
        a = ["pip3"] + a[3:]
    if a[0] == "sudo":
        b = a[1:]
        if b and b[0] == "-n":
            b = b[1:]
        if admin and len(b) >= 3 and b[0] in ("apt", "apt-get") and b[1] == "install":
            pk = [x for x in b[2:] if not x.startswith("-")]
            if pk and len(pk) <= 8 and all(_NOMBRE_APT.match(x) for x in pk):
                return "arreglo", ["sudo", "-n", "apt-get", "install", "-y"] + pk
        return None
    if a[0] == "chmod" and len(a) == 3 and a[1] in ("+x", "u+x", "755", "a+x") and _dentro(carpeta, a[2]):
        return "arreglo", ["chmod", "+x", _abs(carpeta, a[2])]
    if a[0] in ("pip", "pip3") and len(a) >= 2 and a[1] == "install":
        resto = [x for x in a[2:] if x not in ("--user", "-U", "--upgrade", "--break-system-packages")]
        if len(resto) == 2 and resto[0] == "-r" and _dentro(carpeta, resto[1]):
            return "arreglo", ["pip3", "install", "--user", "-r", _abs(carpeta, resto[1])]
        if resto == ["-e", "."] or resto == ["."]:
            return "arreglo", ["pip3", "install", "--user", carpeta]
        if resto and len(resto) <= 12 and all(_NOMBRE_PIP.match(x) for x in resto):
            return "arreglo", ["pip3", "install", "--user"] + resto
        return None
    if a[0] == "npm":
        if a[1:] in (["install"], ["i"], ["ci"]):
            return "arreglo", ["npm", "install"]
        if a[1:] == ["start"] or (len(a) == 3 and a[1] == "run" and re.match(r"^[\w:-]{1,30}$", a[2])):
            return "lanzar", a
        return None
    if a[0] in ("python", "python3") and len(a) >= 2 and a[1].endswith(".py") and _dentro(carpeta, a[1]) and \
            os.path.isfile(_abs(carpeta, a[1])):
        return "lanzar", ["python3", _abs(carpeta, a[1])] + [x for x in a[2:] if not x.startswith("/")][:6]
    if a[0] in ("python", "python3") and len(a) == 3 and a[1] == "-m" and re.match(r"^[\w.]{1,40}$", a[2]):
        return "lanzar", ["python3", "-m", a[2]]
    if a[0] in ("bash", "sh") and len(a) >= 2 and _dentro(carpeta, a[1]) and os.path.isfile(_abs(carpeta, a[1])):
        return "lanzar", ["bash", _abs(carpeta, a[1])]
    if a[0] == "node" and len(a) >= 2 and _dentro(carpeta, a[1]) and os.path.isfile(_abs(carpeta, a[1])):
        return "lanzar", ["node", _abs(carpeta, a[1])]
    if (a[0].startswith("./") or os.path.isabs(a[0])) and _dentro(carpeta, a[0]) and os.path.isfile(_abs(carpeta, a[0])):
        return "lanzar", [_abs(carpeta, a[0])] + [x for x in a[1:] if not x.startswith("/")][:6]
    return None


# ---------------- estudiar: README y la página de donde se bajó ----------------
_CODIGO = re.compile(r"(?is)<(?:pre|code)[^>]*>(.*?)</(?:pre|code)>")


def ordenes_de_texto(texto):
    """Líneas que parecen órdenes en un README o una página: bloques de código, líneas con «$ » delante. PURO."""
    t = str(texto or "")
    trozos = [_html.unescape(re.sub(r"<[^>]+>", "", m)) for m in _CODIGO.findall(t)]
    trozos += re.findall(r"(?s)```[a-zA-Z]*\n(.*?)```", t)
    trozos += [l for l in t.splitlines() if re.match(r"^\s*(?:\$|>)\s+\S", l)]
    sal = []
    for tr in trozos:
        for l in str(tr).splitlines():
            l = re.sub(r"^\s*(?:\$|>|#)\s*", "", l.strip())
            if 2 < len(l) < 200 and l not in sal:
                sal.append(l)
    return sal[:80]


def leer_readme(carpeta):
    for raiz, dirs, fich in os.walk(carpeta or ""):
        if raiz[len(carpeta):].count(os.sep) > 1:
            dirs[:] = []
            continue
        for f in sorted(fich):
            if re.match(r"(?i)^(readme|install|instalar|usage|uso)(\.(md|txt|rst))?$", f):
                try:
                    with open(os.path.join(raiz, f), encoding="utf-8", errors="ignore") as fh:
                        return fh.read(200_000)
                except OSError:
                    pass
    return ""


def otros_lanzadores(carpeta, actual):
    """Otras formas de arrancarla que hay en su carpeta (archivos .py de arranque, AppImage, .sh, ejecutables)."""
    import apps_externas_kira as aex
    c = []
    for f in (aex.como_arrancar(carpeta) if carpeta else None, aex.buscar_lanzador(carpeta) if carpeta else None):
        if f and list(f) != list(actual) and f not in c:
            c.append(list(f))
    return c


# ---------------- arreglos concretos ----------------
def _apt_existe(pkg, correr):
    try:
        rc, s = correr(["apt-cache", "policy", pkg], timeout=30)
    except Exception:                                  # noqa: BLE001
        return False
    return rc == 0 and "Candidate:" in s and "Candidate: (none)" not in s


def _apt_de_lib(lib, correr):
    nombres = []
    for k, v in LIB_A_APT.items():
        if lib.startswith(k) or k.startswith(lib):
            nombres += v
    m = re.match(r"^(lib[\w+-]+?)(?:-[\d.]+)?\.so\.?(\d*)", lib)
    if m:
        base = m.group(1).lower()
        num = m.group(2)
        nombres += [base + num + "t64", base + num, base + "-" + num, base]
    for n in dict.fromkeys(nombres):
        if _NOMBRE_APT.match(n) and _apt_existe(n, correr):
            return n
    return None


def arreglos_para(d, app, admin, correr):
    """Lista de arreglos a probar para un diagnóstico: [{"args"|"lanzar"|"entorno", "que"}]."""
    carpeta = app.get("carpeta") or ""
    lan = list(app.get("lanzar") or [])
    t, q = d["tipo"], d["que"]
    if t == "permiso" and q and _dentro(carpeta, q):
        return [{"args": ["chmod", "+x", _abs(carpeta, q)], "que": "le di permiso para ejecutarse"}]
    if t == "appimage_fuse":
        r = [{"entorno": {"APPIMAGE_EXTRACT_AND_RUN": "1"}, "lanzar": lan + ["--appimage-extract-and-run"],
              "que": "la abrí sin montarla (le faltaba FUSE)"}]
        if admin:
            pk = _apt_de_lib("libfuse.so.2", correr)
            if pk:
                r.append({"args": ["sudo", "-n", "apt-get", "install", "-y", pk], "que": f"instalé {pk} (FUSE)"})
        return r
    if t == "modulo":
        if q in MODULO_A_APT and admin:
            return [{"args": ["sudo", "-n", "apt-get", "install", "-y", MODULO_A_APT[q]],
                     "que": f"instalé {MODULO_A_APT[q]} del sistema"}]
        pk = MODULO_A_PIP.get(q, q)
        if pk and _NOMBRE_PIP.match(pk):
            return [{"args": ["pip3", "install", "--user", pk], "que": f"instalé el paquete de Python {pk}"}]
        return []
    if t == "npm" and carpeta and os.path.isfile(os.path.join(carpeta, "package.json")):
        return [{"args": ["npm", "install"], "que": "instalé sus paquetes de JavaScript (npm install)"}]
    if t == "libreria" and admin:
        pk = _apt_de_lib(q, correr)
        return [{"args": ["sudo", "-n", "apt-get", "install", "-y", pk], "que": f"instalé la librería {pk}"}] if pk else []
    if t == "orden" and admin:
        pk = ORDEN_A_APT.get(q, q if _NOMBRE_APT.match(q or "") else None)
        if pk and _apt_existe(pk, correr):
            return [{"args": ["sudo", "-n", "apt-get", "install", "-y", pk], "que": f"instalé {pk}"}]
    return []


def _correr_arreglo(args, carpeta, correr):
    """Ejecuta un arreglo seguro. Si pip choca con el «entorno gestionado» de Ubuntu 24.04, lo repite para tu usuario
    con --break-system-packages (solo toca ~/.local, nunca el sistema)."""
    rc, s = correr(args, cwd=carpeta or None, timeout=900)
    if rc != 0 and args[:2] == ["pip3", "install"] and re.search(r"(?i)externally[- ]managed", s or ""):
        rc, s = correr(args[:3] + ["--break-system-packages"] + args[3:], cwd=carpeta or None, timeout=900)
    return rc, s


# ---------------- el bucle: estudiar hasta que arranque ----------------
def reparar(app, salida, *, lanzador=None, correr=None, admin=None, traer=None, preguntar=None, espera=ESPERA,
            intentos=MAX_INTENTOS, al_paso=None, registro=None):
    """Prueba arreglos hasta que la app arranque. `lanzador(lanzar, carpeta, entorno)` → (arrancó, salida, proceso).
    Devuelve {ok, lanzar, entorno, hecho:[...], error, proceso}."""
    import apps_externas_kira as aex
    correr = correr or aex._correr_defecto
    if admin is None:
        admin = aex.admin_sin_clave(correr)
    paso = al_paso or (lambda _t: None)
    carpeta = app.get("carpeta") or ""
    lanzar = list(app.get("lanzar") or [])
    entorno = dict(app.get("entorno") or {})
    hecho, probado, falta_admin = [], set(), []
    estudiado = {"readme": False, "pagina": False, "cerebro": False}
    cola = []

    def encolar_de(texto_salida):
        for d in diagnostico(texto_salida, lanzar):
            if d["tipo"] in ("libreria", "orden") and not admin:
                falta_admin.append(d["que"])
            for a in arreglos_para(d, {"carpeta": carpeta, "lanzar": lanzar}, admin, correr):
                cola.append(a)

    def encolar_ordenes(lista, de):
        for linea in lista:
            o = orden_segura(linea, carpeta, admin)
            if o:
                cola.append({("args" if o[0] == "arreglo" else "lanzar"): o[1], "que": f"seguí lo que dice {de}: "
                             + " ".join(os.path.basename(x) if os.path.isabs(x) else x for x in o[1])[:90]})

    encolar_de(salida)
    ultimo = salida
    for _ in range(intentos * 3):
        if len(probado) >= intentos:
            break
        if not cola:                                  # no hay arreglo claro: ESTUDIA
            if not estudiado["readme"]:
                estudiado["readme"] = True
                paso("Leo su README…")
                for l in otros_lanzadores(carpeta, lanzar):
                    cola.append({"lanzar": l, "que": "la arranqué de otra forma que traía en su carpeta"})
                encolar_ordenes(ordenes_de_texto(leer_readme(carpeta)), "su README")
            elif not estudiado["pagina"]:
                estudiado["pagina"] = True
                pag = app.get("pagina") or app.get("fuente") or ""
                if re.match(r"^https?://", pag):
                    paso("Estudio la página de donde la descargué…")
                    try:
                        texto = (traer or aex._traer_texto)(pag)
                        encolar_ordenes(ordenes_de_texto(texto), "la página de descarga")
                    except Exception:                 # noqa: BLE001 - sin internet: sigue con lo demás
                        pass
            elif not estudiado["cerebro"] and preguntar:
                estudiado["cerebro"] = True
                paso("Le pregunto a mi cerebro cómo arrancarla…")
                try:
                    r = preguntar("Eres un experto en Linux (Xubuntu 24.04). Contesta solo con órdenes.", ("Un programa de Linux instalado en " + carpeta + " no arranca con: "
                                   + " ".join(lanzar) + "\nError:\n" + str(ultimo)[-1500:] + "\nREADME:\n"
                                   + leer_readme(carpeta)[:1500] + "\nDime hasta 3 órdenes para arreglarlo o "
                                   "arrancarlo, cada una en una línea que empiece por «$ ». Nada más."))
                    encolar_ordenes([l[2:] for l in str(r or "").splitlines() if l.strip().startswith("$ ")],
                                    "mi cerebro")
                except Exception:                     # noqa: BLE001
                    pass
            else:
                break
            continue
        a = cola.pop(0)
        clave = repr((a.get("args"), a.get("lanzar"), a.get("entorno")))
        if clave in probado:
            continue
        probado.add(clave)
        if a.get("args"):
            paso("Arreglo: " + a["que"] + "…")
            try:
                rc, s = _correr_arreglo(a["args"], carpeta, correr)
            except Exception as e:                    # noqa: BLE001
                rc, s = 1, str(e)
            if rc != 0:
                ultimo = s or ultimo
                encolar_de(s)
                continue
            hecho.append(a["que"])
        nuevo_lan = list(a.get("lanzar") or lanzar)
        nuevo_ent = dict(entorno, **(a.get("entorno") or {}))
        paso("La vuelvo a abrir…")
        ok, s, proceso = lanzador(nuevo_lan, carpeta, nuevo_ent)
        if ok:
            if a.get("lanzar") or a.get("entorno"):
                hecho.append(a["que"])
            return {"ok": True, "lanzar": nuevo_lan, "entorno": nuevo_ent, "hecho": hecho, "error": "",
                    "proceso": proceso}
        ultimo = s or ultimo
        lanzar, entorno = (nuevo_lan, nuevo_ent) if (a.get("lanzar") or a.get("entorno")) and \
            diagnostico(s, nuevo_lan) else (lanzar, entorno)
        encolar_de(s)
    motivo = ultima_linea_error(ultimo)
    for d in diagnostico(ultimo, lanzar):
        if d["tipo"] == "arquitectura":
            motivo += " (es para otro tipo de procesador: busca la versión x86_64/amd64)"
        elif d["tipo"] == "glibc":
            motivo += f" (pide un Linux más nuevo, GLIBC {d['que']}: prueba una versión más antigua del programa)"
    if falta_admin:
        motivo += (" Necesita cosas del sistema (" + ", ".join(dict.fromkeys(falta_admin)) + ") y para instalarlas "
                   "sin preguntarte hace falta que me des el permiso una vez: en la Terminal, kira-permiso.")
    return {"ok": False, "lanzar": list(app.get("lanzar") or []), "entorno": dict(app.get("entorno") or {}),
            "hecho": hecho, "error": motivo, "proceso": None}


def texto_resultado(titulo, r):
    if r.get("ok"):
        return (f"«{titulo}» no arrancaba y lo he arreglado: " + "; ".join(r["hecho"] or ["la abrí de otra forma"])
                + ". Ya está abierta y la próxima vez se abrirá así.")
    return (f"«{titulo}» no arranca y no he conseguido arreglarla. Error: {r['error']}"
            + (" Lo que probé: " + "; ".join(r["hecho"]) + "." if r.get("hecho") else ""))


# ---------------- vigilar al abrir (lo usan la pantalla y el núcleo) ----------------
def lanzador_real(app_id, popen=None, espera=ESPERA):
    def lanzar(lan, carpeta, entorno):
        ruta = ruta_registro(app_id)
        try:
            p = lanzar_con_registro(lan, carpeta, ruta, popen=popen, entorno=entorno)
        except Exception as e:                        # noqa: BLE001 - no existe el archivo, sin permiso…
            return False, str(e), None
        ok, _rc = esperar_arranque(p, espera)
        return ok, leer_registro(ruta), p
    return lanzar


def abrir_vigilando(acceso, dir_accesos, *, popen=None, correr=None, traer=None, preguntar=None, espera=ESPERA,
                    avisar=None, al_pid=None, en_hilo=True, admin=None):
    """Abre una app EXTERNA de Kira y la vigila: si no arranca, la arregla sola (en segundo plano) y avisa al final.
    Devuelve {ok, texto, pid} enseguida (como abrir de siempre)."""
    import accesos_kira as ak
    app_id = acceso.get("id") or acceso.get("titulo") or "app"
    titulo = acceso.get("titulo") or "la app"
    lan = list(acceso.get("lanzar") or [])
    carpeta = acceso.get("carpeta") or ""
    if not lan:
        return {"ok": False, "texto": f"No sé cómo arrancar {titulo}."}
    ruta = ruta_registro(app_id)
    try:
        p = lanzar_con_registro(lan, carpeta, ruta, popen=popen, entorno=acceso.get("entorno"))
    except Exception as e:                            # noqa: BLE001 - p. ej. el archivo ya no está
        p, error_inicial = None, str(e)
    else:
        error_inicial = ""
        if al_pid:
            al_pid(p.pid)
    avisar = avisar or (lambda titulo_aviso, texto: _aviso(titulo_aviso, texto))

    def vigilar():
        if p is not None:
            ok, _rc = esperar_arranque(p, espera)
            if ok:
                return
            salida = leer_registro(ruta)
        else:
            salida = error_inicial
        r = reparar(acceso, salida, lanzador=_con_pid(lanzador_real(app_id, popen=popen, espera=espera), al_pid),
                    correr=correr, traer=traer, preguntar=preguntar, espera=espera, admin=admin)
        if r["ok"]:
            try:
                ak.actualizar_externa(dir_accesos, acceso.get("id"), lanzar=r["lanzar"], entorno=r["entorno"],
                                      arreglos=r["hecho"])
            except Exception:                         # noqa: BLE001
                pass
        avisar("Kira arregló un programa" if r["ok"] else "Un programa no arranca", texto_resultado(titulo, r))

    if en_hilo:
        threading.Thread(target=vigilar, daemon=True, name="kira-arreglar-app").start()
    else:
        vigilar()
    return {"ok": True, "pid": getattr(p, "pid", None), "texto": f"Abriendo {titulo}… (si no arranca, lo arreglo yo)"}


def _con_pid(lanzador, al_pid):
    if not al_pid:
        return lanzador

    def f(lan, carpeta, entorno):
        ok, s, p = lanzador(lan, carpeta, entorno)
        if ok and p is not None:
            al_pid(p.pid)
        return ok, s, p
    return f


def _aviso(titulo, texto):
    try:
        import avisos_kira
        avisos_kira.prioritario(texto, titulo=titulo)
    except Exception:                                 # noqa: BLE001
        pass
