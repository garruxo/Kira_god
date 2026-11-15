# -*- coding: utf-8 -*-
"""
accesibilidad_kira.py - v3.77 (EXPERIMENTAL): Kira maneja programas DE VENTANA (GIMP, LibreOffice…) por dentro,
pulsando sus menús y botones por su NOMBRE, mientras tú lo ves pasar en la ventana de verdad.

Cómo: Linux tiene un sistema para personas ciegas (AT-SPI, «accesibilidad») que cuenta qué menús, botones y campos
tiene cada ventana y deja pulsarlos. Kira no ve la pantalla: LEE esos nombres.

Flujo (igual que el Taller):
  1. «maneja gimp por dentro: exporta la imagen como png» → Kira abre el programa (si no está abierto), lee sus
     menús y botones y su cerebro escribe un PLAN de pasos sencillos:
        PULSA: Archivo > Exportar como…
        ESCRIBE: Nombre = foto.png
        PULSA: Exportar
        ESPERA: 2
  2. La ventana Taller enseña los pasos. NO hace nada aún.
  3. Pulsas «Hazlo» (dos toques) → los hace uno a uno y apunta cada uno en vivo; «Parar» la corta.

Candados:
  - solo dentro del programa que pediste (nunca toca otras ventanas);
  - programas que no: terminales, KiraOS, ajustes del sistema, instaladores, contraseñas, navegadores;
  - botones que no: borrar/eliminar/papelera/vaciar, formatear, desinstalar, enviar, comprar/pagar, «no guardar»,
    sobrescribir/reemplazar, apagar/cerrar sesión;
  - nunca escribe en un campo de contraseña; texto corto (200), sin saltos de línea;
  - como mucho 12 pasos; esperas de 10 s como mucho; si un botón no aparece en 6 s, para (no improvisa).
  - vive en el proceso de la pantalla del portátil (necesita tu sesión): no se puede pedir desde la red ni el móvil.

HONESTO: va a medias. Depende de que el programa cuente bien sus botones (GTK como GIMP sí; LibreOffice necesita la
accesibilidad encendida) y de que el cerebro pequeño elija bien los pasos. Necesita `python3-pyatspi`.
"""
import os
import re
import shutil
import subprocess
import time
import unicodedata

MAX_PASOS = 12
MAX_TEXTO = 200
MAX_ELEMENTOS = 160
ESPERA_ELEMENTO = 6.0
ESPERA_APP = 25.0

APPS_NO = ("terminal", "xterm", "konsole", "tilix", "kitty", "alacritty", "urxvt", "kiraos", "kira", "pywebview",
           "settings", "configuracion", "ajustes", "xfce4-settings", "synaptic", "software", "update", "actualiz",
           "seahorse", "keyring", "contrasen", "password", "keepass", "bitwarden", "firefox", "chromium", "chrome",
           "brave", "opera", "epiphany", "thunderbird", "evolution", "gparted", "disks", "discos", "pkexec", "polkit")
BOTONES_NO = ("borrar", "eliminar", "suprimir", "delete", "remove", "papelera", "trash", "vaciar", "empty", "formatear",
              "format disk", "desinstalar", "uninstall", "enviar", "send", "comprar", "buy", "pagar", "pay", "no guardar",
              "don't save", "dont save", "discard", "descartar", "sobrescribir", "overwrite", "reemplazar", "replace",
              "apagar", "shut down", "cerrar sesion", "log out", "reiniciar", "restart", "quit without", "salir sin")
ROLES = {"push button": "botón", "menu item": "menú", "menu": "menú", "check box": "casilla", "radio button": "opción",
         "toggle button": "botón", "text": "campo", "entry": "campo", "combo box": "lista", "page tab": "pestaña",
         "spin button": "número", "check menu item": "menú", "radio menu item": "menú", "list item": "elemento",
         "password text": "contraseña", "tool bar": None, "label": None}
_PASO = re.compile(r"^\s*(?:\d+[.)]\s*)?(PULSA|ESCRIBE|ESPERA|MARCA)\s*:\s*(.+?)\s*$", re.I)


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _clave(t):
    return re.sub(r"[^a-z0-9]", "", _plano(t))


def app_bloqueada(nombre):
    n = _plano(nombre)
    return any(b in n for b in APPS_NO)


def boton_prohibido(nombre):
    n = _plano(nombre).replace("…", "").replace("...", "")
    return any(b in n for b in BOTONES_NO)


# ------------------------------------------------------------------ la ORDEN
_ORDENES = [
    re.compile(r"^(?:kira[, ]+)?(?:maneja|usa|controla|trabaja\s+con)\s+(?:el\s+programa\s+|la\s+app\s+)?(?P<a>[\w.+-]{2,40})"
               r"\s+(?:por\s+dentro|desde\s+(?:su|la)\s+ventana|con\s+(?:su|la)\s+ventana)\s*(?:[:,]|para|y)?\s*(?P<t>.*)$"),
    re.compile(r"^(?:kira[, ]+)?trabaja\s+dentro\s+de\s+(?:la\s+ventana\s+de\s+)?(?P<a>[\w.+-]{2,40})\s*(?:[:,]|para|y)?\s*(?P<t>.*)$"),
]


def es_orden(texto):
    """(app, tarea) para «maneja X por dentro: …», «usa X desde su ventana: …», «trabaja dentro de X: …»."""
    orig = re.sub(r"\s+", " ", str(texto or "")).strip().rstrip(" .!?")
    t = _plano(orig)
    for rx in _ORDENES:
        m = rx.match(t)
        if m:
            app = m.group("a")
            tarea = m.group("t").strip(" ,:")
            mo = re.search(r"(?:por dentro|desde (?:su|la) ventana|con (?:su|la) ventana|dentro de (?:la ventana de )?\S+)"
                           r"\s*(?:[:,]|para|y)?\s*", orig, re.I)
            if mo and tarea:
                tarea = orig[mo.end():].strip(" ,:") or tarea
            return app, tarea[:400]
    return None


# ------------------------------------------------------------------ el PLAN
def validar_paso(paso):
    """(verbo, datos) o ValueError en español. Datos: PULSA → [nombres del camino]; ESCRIBE → (campo, texto);
    ESPERA → segundos; MARCA → nombre."""
    m = _PASO.match(str(paso or ""))
    if not m:
        raise ValueError("no es un paso que sepa hacer (PULSA, ESCRIBE, MARCA o ESPERA)")
    verbo, resto = m.group(1).upper(), m.group(2).strip()
    if verbo == "ESPERA":
        mm = re.match(r"(\d{1,2})", resto)
        if not mm:
            raise ValueError("ESPERA necesita los segundos")
        return verbo, min(10, max(1, int(mm.group(1))))
    if verbo == "ESCRIBE":
        if "=" not in resto:
            raise ValueError("ESCRIBE va así: «ESCRIBE: campo = texto»")
        campo, texto = [x.strip().strip("«»\"'") for x in resto.split("=", 1)]
        if not texto or len(texto) > MAX_TEXTO or "\n" in texto:
            raise ValueError("texto vacío o demasiado largo")
        if re.search(r"contrase|password|clave|pin\b", _plano(campo)):
            raise ValueError("nunca escribo en un campo de contraseña")
        return verbo, (campo, texto)
    nombres = [x.strip().strip("«»\"'") for x in re.split(r"\s*(?:>|›|▸|->)\s*", resto) if x.strip()]
    if not nombres or len(nombres) > 5:
        raise ValueError("camino de menú vacío o demasiado largo")
    for n in nombres:
        if boton_prohibido(n):
            raise ValueError(f"«{n}» no lo pulso nunca (borrar, enviar, pagar, no guardar…)")
    return verbo, (nombres if verbo == "PULSA" else nombres[-1])


def pasos_de(respuesta):
    """Saca los pasos del texto del cerebro y separa los malos."""
    buenos, malos = [], []
    for l in str(respuesta or "").splitlines():
        s = l.strip().strip("`").strip()
        if not _PASO.match(s):
            continue
        s = _PASO.sub(lambda m: f"{m.group(1).upper()}: {m.group(2).strip()}", s)
        try:
            validar_paso(s)
            if s not in buenos:
                buenos.append(s)
        except ValueError as e:
            malos.append((s, str(e)))
    return buenos[:MAX_PASOS], malos


SISTEMA_VENTANA = ("Eres Kira y manejas un programa con ventana en Linux pulsando sus menús y botones por su NOMBRE. "
                   "Te doy la lista de lo que hay en la ventana y una tarea. Escribe SOLO los pasos, uno por línea, con "
                   "estas palabras: «PULSA: Menú > Opción» (o «PULSA: Botón»), «ESCRIBE: Campo = texto», «MARCA: "
                   "Casilla», «ESPERA: segundos». Como mucho 12 pasos. Usa los nombres TAL CUAL salen en la lista. "
                   "Nunca borres, envíes, pagues ni pulses «No guardar». Si no se puede, escribe una línea «NOTA: …».")


def pedido_ventana(app, tarea, resumen):
    return f"Programa: {app}\nTarea: {tarea or 'enséñame qué menús tiene'}\nLo que hay en la ventana:\n{resumen}"


# ------------------------------------------------------------------ el «backend» (pyatspi de verdad, o uno de mentira)
class BackendAtspi:
    """Lo mínimo de AT-SPI que hace falta. Se importa pyatspi solo aquí (en el portátil, con tu sesión)."""

    def __init__(self):
        import pyatspi                                    # noqa: F401 - python3-pyatspi
        self.p = pyatspi

    def apps(self):
        d = self.p.Registry.getDesktop(0)
        return [d.getChildAtIndex(i) for i in range(d.childCount)]

    def hijos(self, n):
        try:
            return [n.getChildAtIndex(i) for i in range(min(n.childCount, 400))]
        except Exception:                                 # noqa: BLE001
            return []

    def nombre(self, n):
        try:
            return n.name or ""
        except Exception:                                 # noqa: BLE001
            return ""

    def rol(self, n):
        try:
            return n.getRoleName()
        except Exception:                                 # noqa: BLE001
            return ""

    def visible(self, n):
        try:
            st = n.getState()
            return st.contains(self.p.STATE_SHOWING) and st.contains(self.p.STATE_SENSITIVE)
        except Exception:                                 # noqa: BLE001
            return False

    def pulsar(self, n):
        a = n.queryAction()
        for i in range(a.nActions):
            if a.getName(i) in ("click", "press", "activate", "toggle", "jump"):
                return a.doAction(i)
        return a.doAction(0) if a.nActions else False

    def escribir(self, n, texto):
        n.queryEditableText().setTextContents(texto)
        return True


def disponible():
    try:
        import pyatspi                                    # noqa: F401
        return True
    except Exception:                                     # noqa: BLE001
        return False


FALTA = ("Para manejar programas por dentro me falta la accesibilidad de Linux. En la Terminal: "
         "sudo apt install python3-pyatspi at-spi2-core (o con el permiso de admin: «instala python3-pyatspi»). "
         "Para LibreOffice, además: gsettings set org.gnome.desktop.interface toolkit-accessibility true y "
         "vuelve a abrirlo.")


def buscar_app(back, nombre):
    k = _clave(nombre)
    if not k:
        return None
    apps = back.apps()
    for a in apps:
        if _clave(back.nombre(a)) == k:
            return a
    for a in apps:
        ka = _clave(back.nombre(a))
        if ka and (k in ka or ka in k):
            return a
    return None


def elementos(back, app, maximo=MAX_ELEMENTOS):
    """[(nombre, rol, nodo)] de lo que se puede pulsar/escribir en el programa (menús, botones, campos…)."""
    out, pila, vistos = [], [(app, 0)], 0
    while pila and len(out) < maximo and vistos < 6000:
        n, prof = pila.pop()
        vistos += 1
        rol = back.rol(n)
        nom = back.nombre(n).strip()
        if rol in ROLES and ROLES[rol] and nom:
            out.append((nom[:80], rol, n))
        if prof < 25:
            pila.extend((h, prof + 1) for h in reversed(back.hijos(n)))
    return out


def resumen(elems, maximo=120):
    vistos, lin = set(), []
    for nom, rol, _n in elems:
        k = (nom, ROLES.get(rol))
        if k in vistos or rol == "password text":
            continue
        vistos.add(k)
        lin.append(f"{ROLES.get(rol)} «{nom}»")
        if len(lin) >= maximo:
            break
    return "\n".join(lin) or "(no cuenta nada: puede que este programa no tenga la accesibilidad encendida)"


def _encontrar(back, app_nombre, nombre, roles=None, esperar=ESPERA_ELEMENTO, dormir=time.sleep):
    """El elemento visible del programa con ese nombre (exacto primero, luego que lo contenga). Espera un poco."""
    k = _clave(nombre)
    fin = time.time() + esperar
    while True:
        app = buscar_app(back, app_nombre)
        if app is not None:
            el = [(n, r, x) for n, r, x in elementos(back, app, 2000) if roles is None or r in roles]
            for n, r, x in el:
                if _clave(n) == k and back.visible(x):
                    return x, n, r
            for n, r, x in el:
                if k and k in _clave(n) and back.visible(x):
                    return x, n, r
        if time.time() >= fin:
            return None
        dormir(0.4)


def hacer_paso(back, app_nombre, paso, dormir=time.sleep, esperar=ESPERA_ELEMENTO):
    """Hace un paso. Devuelve el texto de lo que hizo; lanza ValueError si no puede (y entonces se para)."""
    verbo, datos = validar_paso(paso)
    if verbo == "ESPERA":
        dormir(datos)
        return f"esperé {datos} s"
    if verbo == "ESCRIBE":
        campo, texto = datos
        roles = {"text", "entry", "spin button", "combo box"}
        r = _encontrar(back, app_nombre, campo, roles, esperar, dormir)
        if r is None:
            raise ValueError(f"no encuentro el campo «{campo}»")
        x, n, rol = r
        if rol == "password text":
            raise ValueError("eso es un campo de contraseña: no escribo ahí")
        back.escribir(x, texto)
        return f"escribí «{texto}» en «{n}»"
    nombres = datos if verbo == "PULSA" else [datos]
    hechos = []
    for nom in nombres:
        r = _encontrar(back, app_nombre, nom, None, esperar, dormir)
        if r is None:
            raise ValueError(f"no encuentro «{nom}»")
        x, n, rol = r
        if boton_prohibido(n):
            raise ValueError(f"«{n}» no lo pulso nunca")
        if rol in ("text", "entry", "password text"):
            raise ValueError(f"«{n}» es un campo, no un botón")
        back.pulsar(x)
        hechos.append(n)
        dormir(0.6)
    return ("marqué «" if verbo == "MARCA" else "pulsé «") + " > ".join(hechos) + "»"


def abrir(app, popen=None, which=None):
    """Abre el programa (si no se puede, lanza ValueError). Con tu sesión (DISPLAY) y la accesibilidad encendida."""
    if app_bloqueada(app):
        raise ValueError(f"«{app}» no lo manejo por dentro (por seguridad: terminales, ajustes, contraseñas, navegadores…)")
    which = which or shutil.which
    exe = which(app) or which(app.lower())
    if not exe:
        raise ValueError(f"no tengo «{app}» instalado")
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":0")
    env.pop("NO_AT_BRIDGE", None)
    env["GTK_MODULES"] = (env.get("GTK_MODULES", "") + ":gail:atk-bridge").strip(":")
    env["SAL_USE_VCLPLUGIN"] = env.get("SAL_USE_VCLPLUGIN", "gtk3")     # LibreOffice cuenta sus botones con gtk3
    (popen or subprocess.Popen)([exe], env=env, start_new_session=True, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return exe


def preparar(app, tarea, preguntar, back=None, popen=None, which=None, dormir=time.sleep, esperar_app=ESPERA_APP):
    """Abre el programa, lee su ventana, pide el plan al cerebro y deja la sesión del Taller ESPERANDO tu «Hazlo»."""
    import taller_programas_kira as tp
    if app_bloqueada(app):
        return None, f"[x] «{app}» no lo manejo por dentro (por seguridad: terminales, ajustes, contraseñas, navegadores…)."
    if back is None:
        if not disponible():
            return None, "[x] " + FALTA
        back = BackendAtspi()
    if buscar_app(back, app) is None:
        try:
            abrir(app, popen, which)
        except ValueError as e:
            return None, f"[x] {e}."
        fin = time.time() + esperar_app
        while buscar_app(back, app) is None and time.time() < fin:
            dormir(0.5)
    a = buscar_app(back, app)
    if a is None:
        return None, (f"[x] He abierto «{app}», pero no aparece en la accesibilidad de Linux (no cuenta sus botones). "
                      + FALTA)
    res = resumen(elementos(back, a))
    resp = preguntar(SISTEMA_VENTANA, pedido_ventana(app, tarea, res))
    buenos, malos = pasos_de(resp)
    notas = [tp._limpio(l.split(":", 1)[1], 200) for l in str(resp or "").splitlines()
             if l.strip().upper().startswith("NOTA:")]
    s = {"modo": "ventana", "programa": app, "tarea": tarea, "carpeta": "(la ventana de " + app + ")", "plan": buenos,
         "lanzar": None, "descargado": False, "de_receta": False,
         "rechazadas": [{"orden": o, "por": p} for o, p in malos][:8], "notas": notas[:4],
         "estado": "esperando" if buenos else "sin plan", "registro": [], "cuando": time.time(), "actual": -1}
    tp.guardar(s)
    if not buenos:
        return s, (f"[x] Mi cerebro no me ha dado pasos que pueda hacer en «{app}»"
                   + (f" (rechacé {len(malos)} por seguridad)" if malos else "") + ". Dímelo con más detalle.")
    return s, (f"EXPERIMENTAL: he preparado {len(buenos)} paso(s) para hacer en la ventana de «{app}»: {tarea}. Los tienes "
               "en la ventana Taller; pulsa «Hazlo» (dos toques) y mira la ventana del programa: verás cómo pulso sus "
               "menús y botones. Si algo no aparece, me paro.")
