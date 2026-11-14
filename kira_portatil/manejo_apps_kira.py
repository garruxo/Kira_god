# -*- coding: utf-8 -*-
"""
manejo_apps_kira.py — v3.35 (SOLO KiraOS): Kira MANEJA las aplicaciones instaladas: las enciende, las apaga, dice si
están abiertas, descubre sus HERRAMIENTAS y te dice las ÓRDENES para manejarlas.

Lo pidió el dueño: «que Kira pueda instalar, encender, apagar, manejar todas las herramientas del programa y
aplicaciones que instalé, que me diga cuáles son las órdenes para manejar dichos programas o aplicaciones».

Qué apps conoce:
  - las que Kira instaló (iconos del escritorio, `accesos_kira`, tipo «externa»);
  - las que TÚ instalaste en Xubuntu: las que salen en el menú (archivos .desktop de /usr/share/applications,
    ~/.local/share/applications, Flatpak y Snap). Solo por su NOMBRE exacto o el de su programa (nada de parecidos
    sueltos: «abre el mapa» sigue siendo la sala de Kira).

Qué hace (órdenes con `orden()`):
  «abre / enciende / lanza X [con <archivo>]», «cierra / apaga X» («… a la fuerza» si no responde), «reinicia X»,
  «¿está abierta X?», «qué apps tengo» / «qué apps hay abiertas», «órdenes de X» / «cómo manejo X» / «herramientas de
  X» (te dice todas), «en X, <herramienta>» / «usa la herramienta <h> de X».

Herramientas de una app (`herramientas()`): las ACCIONES de su .desktop (p. ej. «Nueva ventana», «Ventana privada») y,
si es un programa de terminal, sus opciones y subórdenes leídas de su «--help» (se lanza SIN pantalla —sin DISPLAY—
para que no abra ventanas, con tiempo máximo). Se guardan en ~/.kira_apps_herramientas.json.

Candados:
  - solo cierra procesos de TU usuario, que sean de ESA app (por su número o por la ruta exacta de su programa); nunca
    un «python3» genérico ni nada de Kira;
  - las herramientas se ejecutan con argumentos en lista (sin shell) y solo las que descubrió; un archivo extra solo si
    existe de verdad (o es una web http/https).

`correr`, `popen`, `pgrep` y `dirs` se inyectan para probar sin apps reales.
"""
import json
import os
import re
import shlex
import signal
import subprocess
import time
import unicodedata

RUTA_PROCESOS = os.environ.get("KIRA_APPS_PROCESOS") or os.path.expanduser("~/.kira_apps_procesos.json")
RUTA_HERR = os.environ.get("KIRA_APPS_HERR") or os.path.expanduser("~/.kira_apps_herramientas.json")
DIRS_DESKTOP = ("/usr/share/applications", "/usr/local/share/applications",
                os.path.expanduser("~/.local/share/applications"),
                "/var/lib/flatpak/exports/share/applications",
                os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
                "/var/lib/snapd/desktop/applications")
# palabras que son pantallas u órdenes de la propia Kira: nunca son una app del sistema
_DE_KIRA = re.compile(r"\b(?:sala|buscador|mapa|cuaderno|terminal|wifi|ajustes|programando|maquina|navegador de kira|"
                      r"receta|camara|pantalla|kernel|pagina|web|video|youtube|red|bluetooth|brillo|volumen|sonido|"
                      r"icono|iconos|ventana|ventanas|sesion|orbe|kira|kiraos|mejoras?|tareas|pensar|portatil|movil|"
                      r"puerta|puertos|salvapantallas|enlace|enlaces|libreria|pdf)\b")
_INTERPRETES = {"python", "python3", "bash", "sh", "npm", "node", "java", "env", "flatpak", "snap", "perl", "ruby"}


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


def _sin_kira(texto):
    return re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", str(texto or ""), flags=re.I).strip()


# ---------------------------------------------------------------- órdenes
def orden(texto):
    """(accion, nombre_app, extra) o None. Puro. accion: abrir|cerrar|forzar|reiniciar|estado|ordenes|herramienta|
    lista|abiertas."""
    t = _sin_kira(texto).strip(" ¿¡").rstrip(" .!¡?¿")
    low = _norm(t)
    if re.match(r"^(?:que|cuales|mis)\s+(?:apps?|aplicaciones|programas)\s+(?:tengo|hay)\s+abiert[oa]s$|"
                r"^(?:que|cuales)\s+(?:apps?|aplicaciones|programas)\s+(?:estan|tengo)\s+abiert[oa]s$", low):
        return ("abiertas", "", "")
    if re.match(r"^(?:que|cuales)\s+(?:apps?|aplicaciones|programas)\s+(?:tengo|hay)(?:\s+instalad[oa]s)?$|"
                r"^(?:mis|tus|las)\s+(?:apps?|aplicaciones|programas)(?:\s+instalad[oa]s)?$|"
                r"^(?:lista|ensename|muestrame)\s+(?:de\s+)?(?:mis|las|tus)\s+(?:apps?|aplicaciones|programas)$", low):
        return ("lista", "", "")

    def resto(m):
        return t[m.start(m.lastindex):].strip(" .:\"'¿?") if len(t) == len(low) else m.group(m.lastindex)

    m = re.match(r"^(?:que\s+)?(?:ordenes|comandos|herramientas|funciones|opciones)\s+(?:de|del|tiene|para)\s+"
                 r"(?:la\s+app\s+|el\s+programa\s+)?(.+)$|^como\s+(?:manejo|uso|se\s+usa|se\s+maneja|controlo)\s+"
                 r"(?:la\s+app\s+|el\s+programa\s+|a\s+)?(.+)$|^que\s+(?:puedo|puedes|sabes)\s+hacer\s+con\s+(.+)$", low)
    if m:
        return ("ordenes", resto(m), "")
    m = re.match(r"^(?:esta|estan)\s+(?:abiert[oa]|encendid[oa]|funcionando|en\s+marcha)\s+(.+)$|"
                 r"^(.+?)\s+(?:esta|sigue)\s+(?:abiert[oa]|encendid[oa]|funcionando|en\s+marcha)$", low)
    if m:
        return ("estado", resto(m) if m.lastindex == 1 else m.group(2), "")
    m = re.match(r"^(?:usa|ejecuta|lanza)\s+(?:la\s+)?(?:herramienta|accion|opcion|funcion)\s+(.+?)\s+de\s+(.+)$", low)
    if m:
        return ("herramienta", m.group(2), m.group(1))
    m = re.match(r"^en\s+(.+?)\s*,\s*(?:haz|usa|abre|pon|ejecuta)?\s*(.+)$|^en\s+(.+?)\s+(?:haz|usa|ejecuta)\s+(.+)$", low)
    if m:
        app = m.group(1) or m.group(3)
        herr = m.group(2) or m.group(4)
        return ("herramienta", app, herr)
    m = re.match(r"^(?:cierra|apaga|termina|mata|sal\s+de|para)\s+(?:la\s+app\s+|el\s+programa\s+|la\s+aplicacion\s+)?(.+?)"
                 r"(\s+(?:a\s+la\s+fuerza|del\s+todo|forzad[oa]|ya))?$", low)
    if m:
        return ("forzar" if m.group(2) else "cerrar", m.group(1), "")
    m = re.match(r"^(?:reinicia|reabre)\s+(?:la\s+app\s+|el\s+programa\s+|la\s+aplicacion\s+)?(.+)$", low)
    if m:
        return ("reiniciar", m.group(1), "")
    m = re.match(r"^(?:abre|abrir|enciende|lanza|arranca|inicia|usa|ejecuta)\s+(?:la\s+app\s+|el\s+programa\s+|"
                 r"la\s+aplicacion\s+)?(.+?)(?:\s+con\s+(.+))?$", low)
    if m:
        extra = ""
        if m.group(2):
            mo = re.search(r"\s+con\s+(.+)$", t)
            extra = (mo.group(1) if mo else m.group(2)).strip(" \"'")
        return ("abrir", m.group(1), extra)
    return None


# ---------------------------------------------------------------- encontrar la app
def exec_a_args(exec_txt):
    """Exec= de un .desktop → lista de argumentos sin los códigos %f %U… Devuelve (args, admite_archivo). Puro."""
    try:
        partes = shlex.split(str(exec_txt or ""))
    except ValueError:
        partes = str(exec_txt or "").split()
    admite = any(p in ("%f", "%F", "%u", "%U") for p in partes)
    args = [p for p in partes if not re.fullmatch(r"%[a-zA-Z]", p)]
    return args, admite


def leer_desktop(ruta):
    """Lee un .desktop: {titulo, generico, lanzar, admite_archivo, acciones:[{nombre, lanzar}], archivo, oculta}."""
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            texto = f.read()
    except OSError:
        return None
    secciones, actual = {}, None
    for linea in texto.splitlines():
        linea = linea.strip()
        if linea.startswith("[") and linea.endswith("]"):
            actual = linea[1:-1]
            secciones.setdefault(actual, {})
        elif actual and "=" in linea and not linea.startswith("#"):
            k, v = linea.split("=", 1)
            secciones[actual][k.strip()] = v.strip()
    d = secciones.get("Desktop Entry") or {}
    if d.get("Type", "Application") != "Application" or not d.get("Exec"):
        return None
    nombre = d.get("Name[es]") or d.get("Name") or os.path.basename(ruta)[:-8]
    lanzar, admite = exec_a_args(d.get("Exec"))
    acciones = []
    for a in [x for x in d.get("Actions", "").split(";") if x]:
        s = secciones.get(f"Desktop Action {a}") or {}
        if s.get("Exec"):
            acciones.append({"nombre": s.get("Name[es]") or s.get("Name") or a, "lanzar": exec_a_args(s["Exec"])[0]})
    return {"titulo": nombre, "generico": d.get("GenericName[es]") or d.get("GenericName") or "",
            "lanzar": lanzar, "admite_archivo": admite, "acciones": acciones, "archivo": ruta,
            "oculta": d.get("NoDisplay", "").lower() == "true" or d.get("Hidden", "").lower() == "true",
            "origen": "sistema",
            "categorias": [c for c in d.get("Categories", "").split(";") if c],      # v3.45: para el menú
            "icono": d.get("Icon", "")}


def apps_del_sistema(dirs=None):
    vistas, fuera = set(), []
    for d in (dirs or DIRS_DESKTOP):
        try:
            nombres = sorted(os.listdir(d))
        except OSError:
            continue
        for n in nombres:
            if not n.endswith(".desktop") or n in vistas:
                continue
            app = leer_desktop(os.path.join(d, n))
            if app and not app["oculta"]:
                vistas.add(n)
                fuera.append(app)
    return fuera


def _de_kira(accesos):
    fuera = []
    for a in accesos or []:
        if a.get("tipo") == "externa":
            fuera.append({"titulo": a.get("titulo", ""), "lanzar": list(a.get("lanzar") or []),
                          "carpeta": a.get("carpeta") or "", "acciones": [], "admite_archivo": True,
                          "origen": "kira", "id": a.get("id")})
    return fuera


def _programa(app):
    """El programa de verdad (sin el intérprete delante): «python3 /x/main.py» → /x/main.py."""
    lan = list(app.get("lanzar") or [])
    while lan and os.path.basename(lan[0]) in _INTERPRETES and len(lan) > 1:
        if os.path.basename(lan[0]) == "flatpak" and "run" in lan:
            return lan[-1]
        lan = lan[1:]
        while lan and lan[0].startswith("-"):
            lan = lan[1:]
    return lan[0] if lan else ""


def buscar(nombre, accesos=None, dirs=None):
    """La app que se llama así (Kira primero, luego las del menú de Xubuntu). Solo coincidencias claras. None si no."""
    n = _norm(nombre).strip(" .\"'")
    n = re.sub(r"^(?:la\s+app\s+|el\s+programa\s+|la\s+aplicacion\s+|el\s+|la\s+)", "", n)
    if len(n) < 2 or _DE_KIRA.search(n):
        return None
    for app in _de_kira(accesos):
        tl = _norm(app["titulo"])
        if tl == n or (len(n) >= 3 and (tl.startswith(n) or n.startswith(tl))):
            return app
    sistema = apps_del_sistema(dirs)
    for app in sistema:                                          # nombre exacto
        if _norm(app["titulo"]) == n:
            return app
    for app in sistema:                                          # el programa («firefox», «gimp-2.10»)
        prog = _norm(os.path.basename(_programa(app)))
        if prog and (prog == n or prog.split("-")[0] == n or prog.split(".")[0] == n):
            return app
    for app in sistema:                                          # el nombre empieza por lo dicho («libreoffice writer»)
        tl = _norm(app["titulo"])
        if len(n) >= 4 and (tl.startswith(n + " ") or n.startswith(tl + " ")):
            return app
    return None


# ---------------------------------------------------------------- procesos
def _leer_json(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _guardar_json(ruta, d):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, ruta)


def _vivo(pid):
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError):
        return False
    try:                                                         # un zombi no cuenta
        with open(f"/proc/{int(pid)}/stat") as f:
            return f.read().split(")")[-1].split()[0] != "Z"
    except OSError:
        return True


def _pgrep_defecto(args):
    p = subprocess.run(["pgrep"] + args, capture_output=True, text=True, timeout=10)
    return [int(x) for x in p.stdout.split() if x.isdigit()]


class Manejo:
    def __init__(self, accesos=None, dirs=None, popen=None, correr=None, pgrep=None, matar=None,
                 ruta_procesos=None, ruta_herr=None):
        self.accesos = accesos if accesos is not None else []
        self.dirs = dirs
        self.popen = popen or subprocess.Popen
        self.correr = correr
        self.pgrep = pgrep or _pgrep_defecto
        self.matar = matar or os.kill
        self.ruta_procesos = ruta_procesos or RUTA_PROCESOS
        self.ruta_herr = ruta_herr or RUTA_HERR

    def buscar(self, nombre):
        return buscar(nombre, self.accesos, self.dirs)

    # -------- abrir / cerrar / estado --------
    def _clave(self, app):
        return _norm(app.get("titulo", ""))

    def procesos(self, app):
        """Los números de proceso de ESA app (de tu usuario): los que abrió Kira y los que corren su programa."""
        pids = set()
        d = _leer_json(self.ruta_procesos)
        for p in d.get(self._clave(app), []):
            if _vivo(p):
                pids.add(int(p))
        prog = _programa(app)
        uid = str(os.getuid())
        try:
            if prog and os.path.isabs(prog):
                pids.update(self.pgrep(["-u", uid, "-f", re.sub(r"([.\[\](){}*+?|^$\\])", r"\\\1", prog)]) or [])
            elif prog and os.path.basename(prog) not in _INTERPRETES and len(prog) >= 3:
                pids.update(self.pgrep(["-u", uid, "-x", os.path.basename(prog)[:15]]) or [])
        except Exception:                                        # noqa: BLE001 - sin pgrep
            pass
        yo = {os.getpid(), os.getppid()}
        return sorted(p for p in pids if p not in yo)

    def abrir(self, app, archivo=""):
        lan = list(app.get("lanzar") or [])
        if not lan:
            return {"ok": False, "texto": f"No sé cómo arrancar {app.get('titulo', 'esa app')}."}
        if archivo:
            a = os.path.expanduser(archivo)
            if not (re.match(r"^https?://", a) or os.path.exists(a)):
                return {"ok": False, "texto": f"No encuentro «{archivo}» para abrirlo con {app['titulo']}."}
            lan.append(a)
        env = dict(os.environ)
        env.setdefault("DISPLAY", ":0")
        try:
            p = self.popen(lan, cwd=app.get("carpeta") or None, env=env, start_new_session=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        except Exception as e:                                   # noqa: BLE001
            return {"ok": False, "texto": f"No pude abrir {app['titulo']}: {e}"}
        d = _leer_json(self.ruta_procesos)
        vivos = [x for x in d.get(self._clave(app), []) if _vivo(x)]
        d[self._clave(app)] = (vivos + [p.pid])[-10:]
        _guardar_json(self.ruta_procesos, d)
        return {"ok": True, "pid": p.pid,
                "texto": f"Abriendo {app['titulo']}" + (f" con {archivo}" if archivo else "") + "…"}

    def cerrar(self, app, forzar=False, espera=3.0):
        pids = self.procesos(app)
        if not pids:
            return {"ok": True, "texto": f"{app['titulo']} no está abierta."}
        sen = signal.SIGKILL if forzar else signal.SIGTERM
        for p in pids:
            try:
                self.matar(p, sen)
            except OSError:
                pass
        fin = time.time() + espera
        while time.time() < fin and any(_vivo(p) for p in pids):
            time.sleep(0.2)
        quedan = [p for p in pids if _vivo(p)]
        d = _leer_json(self.ruta_procesos)
        d.pop(self._clave(app), None)
        _guardar_json(self.ruta_procesos, d)
        if quedan and not forzar:
            return {"ok": False, "texto": (f"He pedido a {app['titulo']} que se cierre, pero sigue abierta (quizá te "
                                           f"pregunta si guardar algo). Si quieres, dime «cierra {app['titulo']} a la "
                                           "fuerza» (se perdería lo que no hayas guardado).")}
        return {"ok": True, "texto": f"{app['titulo']} cerrada" + (" a la fuerza." if forzar else ".")}

    def estado(self, app):
        pids = self.procesos(app)
        return pids

    # -------- herramientas --------
    def herramientas(self, app, refrescar=False):
        """[{nombre, args, tipo: 'accion'|'opcion'|'suborden', desc}] de la app (de su .desktop y su --help)."""
        cache = _leer_json(self.ruta_herr)
        k = self._clave(app)
        if not refrescar and isinstance(cache.get(k), list):
            return cache[k]
        herr = [{"nombre": a["nombre"], "args": a["lanzar"], "tipo": "accion", "desc": ""}
                for a in app.get("acciones") or []]
        lan = list(app.get("lanzar") or [])
        if lan:
            herr += self._de_ayuda(lan)
        cache[k] = herr[:40]
        try:
            _guardar_json(self.ruta_herr, cache)
        except OSError:
            pass
        return cache[k]

    def _de_ayuda(self, lan):
        env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}   # sin abrir ventanas
        try:
            if self.correr:
                rc, salida = self.correr(lan + ["--help"], timeout=8)
            else:
                p = subprocess.run(lan + ["--help"], capture_output=True, text=True, timeout=8, env=env,
                                   stdin=subprocess.DEVNULL)
                salida = (p.stdout or "") + (p.stderr or "")
        except Exception:                                        # noqa: BLE001 - no tiene --help / se queda colgada
            return []
        return analizar_ayuda(salida)

    def usar(self, app, herramienta, extra=""):
        herr = self.herramientas(app)
        h = elegir_herramienta(herr, herramienta)
        if not h:
            nombres = ", ".join(x["nombre"] for x in herr[:12])
            return {"ok": False, "texto": (f"{app['titulo']} no tiene la herramienta «{herramienta}»." +
                                           (f" Las que tiene: {nombres}." if nombres else
                                            " No le he encontrado herramientas propias."))}
        if h["tipo"] == "accion":                                # acción del menú: abre su ventana
            return self.abrir(dict(app, lanzar=h["args"]), extra)
        args = list(app.get("lanzar") or []) + list(h["args"])
        if extra:
            a = os.path.expanduser(extra)
            if not (re.match(r"^https?://", a) or os.path.exists(a)):
                return {"ok": False, "texto": f"No encuentro «{extra}»."}
            args.append(a)
        try:
            if self.correr:
                rc, salida = self.correr(args, timeout=120)
            else:
                p = subprocess.run(args, capture_output=True, text=True, timeout=120, cwd=app.get("carpeta") or None,
                                   stdin=subprocess.DEVNULL)
                rc, salida = p.returncode, (p.stdout or "") + (p.stderr or "")
        except subprocess.TimeoutExpired:
            return {"ok": False, "texto": f"«{h['nombre']}» de {app['titulo']} tardaba demasiado; lo he parado."}
        except Exception as e:                                   # noqa: BLE001
            return {"ok": False, "texto": f"No pude usar «{h['nombre']}»: {e}"}
        salida = salida.strip()
        return {"ok": rc == 0, "texto": (f"{app['titulo']} {h['nombre']}" + (" ✓" if rc == 0 else f" (salió con {rc})") +
                                         (":\n" + salida[-1500:] if salida else "."))}

    # -------- textos --------
    def texto_ordenes(self, app):
        t = app["titulo"]
        lin = [f"Órdenes para manejar {t}:",
               f" · «abre {t}» / «enciende {t}»" + (f"  —  «abre {t} con <archivo o web>»" if app.get("admite_archivo")
                                                     else ""),
               f" · «cierra {t}» (y «cierra {t} a la fuerza» si no responde)",
               f" · «reinicia {t}»   · «¿está abierta {t}?»"]
        herr = self.herramientas(app)
        acc = [h for h in herr if h["tipo"] == "accion"]
        otras = [h for h in herr if h["tipo"] != "accion"]
        if acc:
            lin.append("Sus acciones (abren su ventana así):")
            lin += [f" · «en {t}, {h['nombre']}»" for h in acc[:10]]
        if otras:
            lin.append("Sus herramientas (te digo lo que conteste):")
            lin += [f" · «en {t}, {h['nombre']}»" + (f" — {h['desc'][:70]}" if h.get("desc") else "")
                    for h in otras[:20]]
        if not herr:
            lin.append("No le he encontrado herramientas propias (ni acciones en su menú ni ayuda por terminal): se "
                       "maneja desde su propia ventana.")
        if app.get("origen") == "kira":
            lin.append(f" · Para quitarla: clic derecho en su icono ▸ Desinstalar.")
        return "\n".join(lin)

    def texto_lista(self, solo_abiertas=False):
        kira = _de_kira(self.accesos)
        sistema = apps_del_sistema(self.dirs)
        lin = []
        if solo_abiertas:
            abiertas = [a["titulo"] for a in kira + sistema if self.procesos(a)]
            if not abiertas:
                return "Ahora mismo no tengo ninguna app abierta (de las que conozco)."
            return "Apps abiertas: " + ", ".join(sorted(set(abiertas))) + ". Ciérralas con «cierra X»."
        if kira:
            lin.append("Las que te instalé yo (en el escritorio): " + ", ".join(a["titulo"] for a in kira) + ".")
        if sistema:
            nombres = sorted(set(a["titulo"] for a in sistema), key=_norm)
            lin.append(f"Las de Xubuntu ({len(nombres)}): " + ", ".join(nombres[:60]) +
                       ("…" if len(nombres) > 60 else "") + ".")
        if not lin:
            return "No encuentro apps instaladas."
        lin.append("Dime «órdenes de X» y te digo cómo manejar cualquiera.")
        return "\n".join(lin)


def analizar_ayuda(texto, maximo=30):
    """De la salida de «--help»: opciones («-v, --version  Muestra…») y subórdenes («build   Compila…»). Puro."""
    fuera, vistos = [], set()
    seccion_ordenes = False
    for linea in str(texto or "").splitlines()[:400]:
        if re.match(r"^\s*(?:commands|subcommands|ordenes|comandos|available commands)\s*:?\s*$", linea, re.I):
            seccion_ordenes = True
            continue
        if re.match(r"^\S", linea):
            seccion_ordenes = bool(re.match(r"^\s*(?:commands|subcommands|ordenes|comandos)", linea, re.I))
        m = re.match(r"^\s{1,8}((?:-\w|--[\w-]+)(?:[ ,=]+(?:-\w|--[\w-]+))*)(?:[ =]([<\[]?[A-Z_a-z]+[>\]]?))?\s{2,}(.+)$",
                     linea)
        if m:
            opciones = re.findall(r"--[\w-]+|-\w", m.group(1))
            larga = next((o for o in opciones if o.startswith("--")), opciones[0])
            if larga in ("--help", "-h") or larga in vistos or m.group(2):
                continue                                         # las que piden un valor no se ofrecen sueltas
            vistos.add(larga)
            fuera.append({"nombre": larga, "args": [larga], "tipo": "opcion", "desc": m.group(3).strip()[:120]})
            continue
        if seccion_ordenes:
            m = re.match(r"^\s{1,8}([a-z][\w-]{1,24})\s{2,}(.+)$", linea)
            if m and m.group(1) not in vistos and m.group(1) != "help":
                vistos.add(m.group(1))
                fuera.append({"nombre": m.group(1), "args": [m.group(1)], "tipo": "suborden",
                              "desc": m.group(2).strip()[:120]})
        if len(fuera) >= maximo:
            break
    return fuera


def elegir_herramienta(herr, pedido):
    """La herramienta que encaja con lo pedido («version» → --version, «nueva ventana privada»…). Puro."""
    p = _norm(pedido).strip(" .\"'")
    p_sin = p.lstrip("-")
    for h in herr:
        n = _norm(h["nombre"])
        if n == p or n.lstrip("-") == p_sin:
            return h
    for h in herr:
        n = _norm(h["nombre"]).lstrip("-").replace("-", " ")
        if p_sin and (n.startswith(p_sin) or p_sin.replace("-", " ") == n):
            return h
    palabras = set(re.findall(r"[a-z0-9]{3,}", p))
    mejor, puntos = None, 0
    for h in herr:
        pal = set(re.findall(r"[a-z0-9]{3,}", _norm(h["nombre"] + " " + h.get("desc", ""))))
        pt = len(palabras & pal)
        if pt > puntos:
            mejor, puntos = h, pt
    return mejor if puntos else None


def hacer(manejo, accion, nombre="", extra=""):
    """Hace la orden. Devuelve {texto, ok?} o None si la app no existe (para que siga el reparto normal)."""
    if accion == "lista":
        return {"texto": manejo.texto_lista()}
    if accion == "abiertas":
        return {"texto": manejo.texto_lista(solo_abiertas=True)}
    app = manejo.buscar(nombre)
    if not app:
        return None
    if accion == "abrir":
        return manejo.abrir(app, extra)
    if accion in ("cerrar", "forzar"):
        return manejo.cerrar(app, forzar=accion == "forzar")
    if accion == "reiniciar":
        r = manejo.cerrar(app)
        if not r.get("ok"):
            return r
        time.sleep(0.5)
        r2 = manejo.abrir(app)
        return {"ok": r2.get("ok", True), "texto": f"Reiniciando {app['titulo']}: " + r2["texto"]}
    if accion == "estado":
        pids = manejo.estado(app)
        return {"texto": (f"Sí, {app['titulo']} está abierta" + (f" ({len(pids)} proceso(s))." if len(pids) > 1 else ".")
                          if pids else f"No, {app['titulo']} no está abierta. «abre {app['titulo']}» para encenderla.")}
    if accion == "ordenes":
        return {"texto": manejo.texto_ordenes(app)}
    if accion == "herramienta":
        m = re.match(r"^(.+?)\s+(?:con|en|sobre)\s+(\S+)$", extra.strip())
        herr, arch = (m.group(1), m.group(2)) if m and (os.path.exists(os.path.expanduser(m.group(2))) or
                                                         m.group(2).startswith("http")) else (extra, "")
        return manejo.usar(app, herr, arch)
    return None


def breve(titulo):
    """Lo que se añade al instalar una app: cómo manejarla. Puro."""
    return (f" Para manejarla: «abre {titulo}», «cierra {titulo}», «¿está abierta {titulo}?» y «órdenes de "
            f"{titulo}» (te digo todas sus herramientas).")
