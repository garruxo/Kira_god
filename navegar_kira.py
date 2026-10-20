# -*- coding: utf-8 -*-
"""
navegar_kira.py - Kira se MUEVE por la app y FUERA de ella cuando se lo pides (VA EN EL APK).

Dentro de Kira:  «Kira, abre la sala hacker», «ve a los juegos», «llévame al editor», «enséñame mis notas»,
                 «juega a la serpiente», «atrás», «ve al menú».
Fuera de Kira:   «abre WhatsApp» (cualquier app instalada, por su nombre), «ve al inicio del móvil» / «minimízate»,
                 «abre los ajustes del wifi», «busca en google recetas de paella», «abre youtube.com»,
                 «marca el 600 123 456» (abre el teclado del teléfono con el número: NO llama sola),
                 «vuelve» (desde otra app, Kira vuelve a primer plano).
Desde otra app (Kira en segundo plano con «Siempre activa»), Android solo deja abrir cosas si le das el permiso
«Mostrar sobre otras apps» («Kira, permiso para abrir apps»). Depende del móvil: no está probado en todos.

Dos capas, como el resto del proyecto:
  - interpretar(frase) -> qué hacer (lógica pura, se prueba en el PC).
  - Movil: lo hace en Android con Intents (pyjnius). Las clases de Java se buscan al crearla, en el hilo principal.
Kira no pulsa botones DENTRO de otras apps (eso necesitaría el permiso de accesibilidad, que lo ve todo).
"""
import difflib
import re
import time
import unicodedata

# pantallas de Kira: destino -> (alias, frase al ir). destino = "pantalla" o "panel:sub"
DESTINOS = {
    "inicio": (("inicio", "portada", "pantalla principal", "principio", "boton de kira", "boton"), "Vuelvo a mi botón."),
    "menu": (("menu", "apartados", "menu principal"), "Te abro el menú."),
    "sala_hacker": (("sala hacker", "sala jaquer", "sala de hacker", "sala de hackers", "sala hackers", "hacker",
                     "habitacion hacker", "sala de programar"), "Vamos a la Sala Hacker."),
    "terminal": (("terminal", "ordenador de la sala hacker", "terminal de la sala"), "Te abro la terminal."),
    "biblioteca": (("biblioteca",), "Vamos a la biblioteca."),
    "sala_diseno": (("sala de diseno", "sala diseno", "diseno"), "Vamos a la Sala de Diseño."),
    "estudio": (("estudio de diseno", "ordenador de diseno"), "Te abro el ordenador de diseño."),
    "sala_cine": (("sala de cine", "cine"), "Vamos al cine."),
    "reproductor": (("reproductor",), "Te abro el reproductor."),
    "mediateca": (("mediateca", "mis videos", "mi musica", "videoteca"), "Te abro la mediateca."),
    "mezcla": (("mesa de mezclas", "mesa de mezcla", "mezclador", "mezcla"), "Te abro la mesa de mezcla."),
    "editor_video": (("editor de videos", "editor de video", "editar videos", "editar video"), "Te abro el editor de vídeo."),
    "cerebro_kira": (("cerebro y oido", "tu cerebro", "cerebro", "oido"), "Te abro «Cerebro y oído»."),
    "lector": (("lector de capturas", "lector"), "Te abro el lector."),
    "juegos": (("juegos", "zona de juegos", "lista de juegos"), "Vamos a los juegos."),
    "editor_codigo": (("editor de codigo", "editor de programas", "editor"), "Te abro el editor de código."),
    "taller": (("taller",), "Vamos al taller."),
    "sala_ciber": (("sala de ciberseguridad", "ciberseguridad", "ciber", "bunker"), "Vamos al búnker de ciberseguridad."),
    "bitacora": (("bitacora",), "Te abro la bitácora."),
    "panel:orden": (("mejoras", "pedir una mejora", "pedir mejoras"), "Te abro las mejoras."),
    "pasarela": (("pasarela", "pantalla del laboratorio"), "Te abro la pasarela."),
    "panel:modulos": (("modulos", "mis modulos"), "Te abro los módulos."),
    "busqueda": (("busqueda", "buscador"), "Te abro la búsqueda."),
    "lienzo": (("lienzo", "dibujos"), "Te abro el lienzo."),
    "pintor": (("pintor", "estudio de pintura", "pinceles", "mis imagenes", "imagenes de kira", "tus imagenes"),
               "Te abro el pintor."),
    "internet": (("buscador de internet", "pantalla de internet", "internet de kira", "busquedas en internet",
                  "resultados de internet"), "Te abro internet."),
    "conocimiento": (("conocimiento", "lo que has aprendido"), "Te enseño lo que he aprendido."),
    "notas": (("notas", "apuntes"), "Te abro tus notas."),
    "memoria": (("memoria", "conversacion"), "Te abro la memoria."),
    "estado": (("estado",), "Te enseño el estado."),
    "panel:consola": (("consola",), "Te abro la consola."),
    "config": (("configuracion", "ajustes", "opciones"), "Te abro la configuración."),
    "ayuda": (("ayuda",), "Te abro la ayuda."),
}
PANTALLAS = {d.split(":")[0] for d in DESTINOS}

JUEGOS = {"rompeladrillos": ("rompeladrillos", "ladrillos", "arkanoid", "breakout"),
          "serpiente": ("serpiente", "culebra", "snake"),
          "esquiva": ("esquiva meteoritos", "esquiva", "meteoritos"),
          "saltarin": ("saltarin", "saltar"),
          "pong": ("pong",)}

AJUSTES_MOVIL = {          # palabra -> acción de Android
    "wifi": "android.settings.WIFI_SETTINGS", "wi fi": "android.settings.WIFI_SETTINGS",
    "bluetooth": "android.settings.BLUETOOTH_SETTINGS", "pantalla": "android.settings.DISPLAY_SETTINGS",
    "sonido": "android.settings.SOUND_SETTINGS", "volumen": "android.settings.SOUND_SETTINGS",
    "bateria": "android.intent.action.POWER_USAGE_SUMMARY", "aplicaciones": "android.settings.APPLICATION_SETTINGS",
    "apps": "android.settings.APPLICATION_SETTINGS", "ubicacion": "android.settings.LOCATION_SOURCE_SETTINGS",
    "gps": "android.settings.LOCATION_SOURCE_SETTINGS", "datos": "android.settings.DATA_ROAMING_SETTINGS",
}
AJUSTES_GENERAL = "android.settings.SETTINGS"
NOMBRE_AJUSTES = {"android.settings.WIFI_SETTINGS": "del WiFi", "android.settings.BLUETOOTH_SETTINGS": "del Bluetooth",
                  "android.settings.DISPLAY_SETTINGS": "de la pantalla", "android.settings.SOUND_SETTINGS": "del sonido",
                  "android.intent.action.POWER_USAGE_SUMMARY": "de la batería",
                  "android.settings.APPLICATION_SETTINGS": "de las aplicaciones",
                  "android.settings.LOCATION_SOURCE_SETTINGS": "de la ubicación",
                  "android.settings.DATA_ROAMING_SETTINGS": "de los datos móviles", AJUSTES_GENERAL: "del móvil"}

# lo que ya hacen otras órdenes de Kira: aquí no se toca
_DE_OTROS = re.compile(r"^(?:la |tu )?(?:camara|lo leido|la receta|receta|captura|ultima captura)\b")
_LAB = re.compile(r"^(?:el |al |la |mi )?(?:laboratorio|lab|ordenador|pc|portatil|computadora)\b")
_ARTICULOS = re.compile(r"^(?:(?:el|la|los|las|un|una|mi|mis|tu|tus|al|del|de|a)\s+)+")
_COLA = re.compile(r"\s+(?:por favor|ya|ahora|ahora mismo|de kira|kira|anda|porfa)$")

_VERBO_IR = r"(?:ve|vete|vamos|vamonos|llevame|llevarme|llevanos|lleva me|ir|quiero ir|pasa|cambia|accede|regresa|vuelve)"
_VERBO_ABRIR = r"(?:abre|abrir|abreme|abre me|entra|entrar|metete|ensename|muestrame|muestra|pon|ponme|sacame|saca)"
_VERBO_APP = r"(?:abre|abrir|abreme|abre me|lanza|arranca|inicia|ejecuta)"
_CORTESIA = re.compile(r"^(?:kira\s+)?(?:por favor\s+)?(?:(?:puedes|podrias|quiero que|me)\s+)*")


def normalizar(texto, puntos=False):
    """Minúsculas, sin tildes ni signos. puntos=True conserva . / : (para direcciones web)."""
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[¿?¡!,;«»\"']" if puntos else r"[¿?¡!.,;:«»\"']", " ", t)
    return re.sub(r"\s+", " ", t).strip(" .")


def _destino(resto):
    """«la sala hacker por favor» -> 'sala_hacker'. None si no es una pantalla de Kira."""
    r = _COLA.sub("", _ARTICULOS.sub("", resto)).strip()
    if not r:
        return None
    pares = sorted(((a, d) for d, (alias, _f) in DESTINOS.items() for a in alias), key=lambda p: -len(p[0]))
    for alias, destino in pares:
        if r == alias or r.startswith(alias + " de kira") or r == alias + "s":
            return destino
    return None


def _juego(resto, extra=()):
    r = re.sub(r"^(?:juego|partida)\s+(?:de\s+|a\s+|al\s+)?(?:la\s+|el\s+)?", "", _COLA.sub("", _ARTICULOS.sub("", resto)))
    r = _ARTICULOS.sub("", r).strip()
    for id_, alias in JUEGOS.items():
        if r in alias or any(r.startswith(a + " ") for a in alias):
            return id_
    for nombre in extra:                       # juegos que añadieron las mejoras («juego tetris» -> «tetris»)
        n = normalizar(nombre)
        if r == n or (len(r) >= 4 and (r in n or n in r)):
            return "mejora:" + nombre
    return None


def interpretar(texto, juegos_extra=()):
    """Qué hacer con la frase, o None si no es moverse. Devuelve un dict con 'tipo':
    'pantalla' (destino, frase) | 'juego' (id) | 'atras' | 'kira' (volver a primer plano) |
    'app' (nombre, seguro) | 'inicio_movil' | 'ajustes' (accion, nombre) | 'web' (url) | 'marcar' (numero) |
    'llamar_nombre' (nombre) | 'permiso_fondo'."""
    t = _CORTESIA.sub("", normalizar(texto)).strip()
    if not t or len(t) > 120:
        return None
    # ---- atrás / volver ----
    if re.fullmatch(r"(?:atras|ve atras|vuelve atras|volver|regresa|vuelve|sal de aqui|salir de aqui|anterior)", t):
        return {"tipo": "atras"}
    if re.fullmatch(r"(?:ven|ven aqui|aparece|abrete|muestrate|vuelve a primer plano|abre kira|vuelve conmigo)", t):
        return {"tipo": "kira"}
    if re.search(r"permiso (?:para|de) abrir (?:apps|aplicaciones|cosas)|mostrar(?:te)? (?:sobre|encima de) (?:otras|las) apps", t):
        return {"tipo": "permiso_fondo"}
    # ---- inicio del móvil ----
    if re.fullmatch(r"(?:minimizate|escondete|sal de la app|salte de la app|sal de kira|cierra la app|vete al escritorio|"
                    r"(?:ve|vete|vamos|llevame|ir) al? (?:inicio|escritorio|pantalla de inicio|pantalla principal) "
                    r"del? (?:movil|telefono|sistema|android)|(?:inicio|escritorio|pantalla de inicio) del? (?:movil|telefono))", t):
        return {"tipo": "inicio_movil"}
    # ---- juegos ----
    m = re.match(r"^(?:juega(?:mos)?|jugamos|juguemos|jugar|echa(?:mos)?|echemos|pon(?:me)?|abre|empieza|quiero jugar|vamos a jugar)\s+"
                 r"(?:una partida\s+)?(?:(?:al|a|el juego|juego|una partida)\s+)?(?:(?:de|al|a)\s+)?(.+)$", t)
    if m:
        j = _juego(m.group(1), juegos_extra)
        if j:
            return {"tipo": "juego", "id": j}
    # ---- web ----
    # «busca en internet…» lo hace Kira sola (internet_kira); en el navegador solo si dices «en google / el navegador»
    m = re.match(r"^(?:busca(?:me)?|buscar)\s+en\s+(?:google|el navegador)\s+(.+)$", t)
    if m:
        import urllib.parse
        return {"tipo": "web", "url": "https://www.google.com/search?q=" + urllib.parse.quote(m.group(1)[:200])}
    m = re.match(r"^(?:kira\s+)?(?:" + _VERBO_APP + r"|" + _VERBO_IR + r" a|entra en)\s+(?:la (?:web|pagina)\s+(?:de\s+)?)?"
                 r"((?:https?://)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|es|org|net|io|dev|tv|app|info|eu)(?:/\S*)?)$",
                 normalizar(texto, puntos=True))
    if m:
        url = m.group(1) if m.group(1).startswith("http") else "https://" + m.group(1)
        return {"tipo": "web", "url": url}
    # ---- teléfono ----
    m = re.match(r"^(?:llama(?:me)?|marca(?:me)?|marcar|llamar)\s+(?:al?|el)?\s*(?:numero\s+|telefono\s+)?(.+)$", t)
    if m:
        import enlace_lab_kira
        resto = m.group(1)
        numero = re.sub(r"[^\d+]", "", resto) if re.search(r"\d", resto) else enlace_lab_kira.cifras_dichas(resto)
        if len(numero.lstrip("+")) >= 3:
            return {"tipo": "marcar", "numero": numero[:20]}
        if re.match(r"^(?:a\s+)?[a-z]", resto):
            return {"tipo": "llamar_nombre", "nombre": resto[:40]}
    # ---- ajustes del móvil ----
    m = re.match(r"^(?:" + _VERBO_ABRIR + r"|" + _VERBO_IR + r" a)\s+(?:(?:los|las|el|la|a|al)\s+)*"
                 r"(?:ajustes|configuracion|opciones)\s+(?:del?|de la|de los)\s+(.+)$", t) or \
        re.match(r"^(?:" + _VERBO_ABRIR + r")\s+(?:(?:el|la|los)\s+)?(wifi|wi fi|bluetooth|gps|ubicacion)$", t)
    if m:
        que = _COLA.sub("", m.group(1)).strip()
        if re.match(r"^(?:kira|la app|esta app)$", que):
            return {"tipo": "pantalla", "destino": "config", "frase": DESTINOS["config"][1]}
        accion = next((a for k, a in AJUSTES_MOVIL.items() if que.startswith(k)), None)
        if accion or re.match(r"^(?:movil|telefono|sistema|android)$", que):
            accion = accion or AJUSTES_GENERAL
            return {"tipo": "ajustes", "accion": accion, "nombre": NOMBRE_AJUSTES[accion]}
    # ---- pantallas de Kira ----
    m = re.match(r"^(?:" + _VERBO_IR + r")\s+(?:a|al|a la|hacia)\s+(.+)$", t) or \
        re.match(r"^(?:" + _VERBO_ABRIR + r")\s+(?:(?:en|a)\s+)?(.+)$", t)
    resto = m.group(1) if m else None
    if resto is not None:
        if _DE_OTROS.match(resto) or _LAB.match(resto):
            return None                            # cámara, lector, recetas, laboratorio: tienen sus propias órdenes
        d = _destino(resto)
        if d:
            return {"tipo": "pantalla", "destino": d, "frase": DESTINOS[d][1]}
    # ---- otra app, por su nombre ----
    m = re.match(r"^(" + _VERBO_APP + r"|entra|entrar|ve|vete|pon|ponme)\s+(?:(?:en|a|al)\s+)?(?:la app(?:licacion)? (?:de |del )?)?(.+)$", t)
    if m:
        nombre = _COLA.sub("", _ARTICULOS.sub("", m.group(2))).strip()
        if nombre and not _DE_OTROS.match(nombre) and not _LAB.match(nombre) and len(nombre) <= 40:
            seguro = bool(re.match(_VERBO_APP + r"$", m.group(1))) or "app" in t.split()[1:3]
            return {"tipo": "app", "nombre": nombre, "seguro": seguro}
    return None


# =====================================================================================
#  ANDROID (Intents). Se crea en el hilo principal; sus métodos valen desde cualquier hilo.
# =====================================================================================
class JavaMovil:
    def __init__(self):
        from jnius import autoclass
        self.Intent = autoclass("android.content.Intent")
        self.Uri = autoclass("android.net.Uri")
        self.Settings = autoclass("android.provider.Settings")
        self.actividad = autoclass("org.kivy.android.PythonActivity").mActivity
        self.paquete = str(self.actividad.getPackageName())
        self.NUEVA = self.Intent.FLAG_ACTIVITY_NEW_TASK
        self.DELANTE = self.Intent.FLAG_ACTIVITY_REORDER_TO_FRONT

    def _lanzar(self, intent):
        intent.addFlags(self.NUEVA)
        self.actividad.startActivity(intent)
        return True

    def apps(self):
        pm = self.actividad.getPackageManager()
        i = self.Intent(self.Intent.ACTION_MAIN)
        i.addCategory(self.Intent.CATEGORY_LAUNCHER)
        lista = pm.queryIntentActivities(i, 0)
        res = []
        for k in range(lista.size()):
            ri = lista.get(k)
            res.append((str(ri.loadLabel(pm).toString()), str(ri.activityInfo.packageName)))
        return res

    def abrir_paquete(self, paquete):
        intent = self.actividad.getPackageManager().getLaunchIntentForPackage(paquete)
        return False if intent is None else self._lanzar(intent)

    def inicio(self):
        i = self.Intent(self.Intent.ACTION_MAIN)
        i.addCategory(self.Intent.CATEGORY_HOME)
        return self._lanzar(i)

    def ajustes(self, accion):
        return self._lanzar(self.Intent(accion))

    def ver(self, url):
        return self._lanzar(self.Intent(self.Intent.ACTION_VIEW, self.Uri.parse(url)))

    def marcar(self, numero):
        return self._lanzar(self.Intent(self.Intent.ACTION_DIAL, self.Uri.parse("tel:" + numero)))

    def traer_kira(self):
        i = self.Intent(self.actividad, self.actividad.getClass())
        i.addFlags(self.DELANTE)
        return self._lanzar(i)

    def puede_desde_fondo(self):
        try:
            return bool(self.Settings.canDrawOverlays(self.actividad))
        except Exception:
            return True                                     # Android antiguo: no hacía falta

    def pedir_permiso_fondo(self):
        return self._lanzar(self.Intent("android.settings.action.MANAGE_OVERLAY_PERMISSION",
                                        self.Uri.parse("package:" + self.paquete)))


def java_movil():
    try:
        return JavaMovil()
    except Exception:
        return None


class Movil:
    """Lo que Kira hace FUERA de la app. java: JavaMovil (Android) o un falso en las pruebas; None en el PC."""
    SOLO_MOVIL = "Abrir cosas fuera de mí solo funciona en el móvil."
    SIN_PERMISO_FONDO = ("Mientras usas otra app, Android no me deja abrir nada. Si quieres que pueda, ábreme y dime "
                         "«Kira, permiso para abrir apps»: te llevo a «Mostrar sobre otras apps» para activarlo.")

    def __init__(self, java=None, reloj=time.monotonic):
        self.java = java
        self._reloj = reloj
        self._apps, self._apps_t = None, -1e9

    def disponible(self):
        return self.java is not None

    def apps(self, refrescar=False):
        if self.java is None:
            return []
        if refrescar or self._apps is None or self._reloj() - self._apps_t > 120:
            try:
                self._apps = self.java.apps()
            except Exception:
                self._apps = self._apps or []
            self._apps_t = self._reloj()
        return self._apps

    def buscar_app(self, nombre):
        """(etiqueta, paquete) de la app que más se parece al nombre, o None."""
        q = normalizar(nombre)
        if not q:
            return None
        lista = [(normalizar(l), l, p) for l, p in self.apps() if p != getattr(self.java, "paquete", None)]
        for prueba in (lambda n, p: n == q, lambda n, p: n.startswith(q + " ") or n.startswith(q),
                       lambda n, p: len(q) >= 3 and q in n, lambda n, p: len(q) >= 4 and q.replace(" ", "") in p.lower()):
            hallados = [(l, p) for n, l, p in lista if prueba(n, p)]
            if hallados:
                return min(hallados, key=lambda x: len(x[0]))
        cerca = difflib.get_close_matches(q, [n for n, _l, _p in lista], n=1, cutoff=0.75)
        if cerca:
            return next((l, p) for n, l, p in lista if n == cerca[0])
        return None

    def hacer(self, accion, en_fondo=False):
        """(hecho, texto). hecho=None: no era cosa suya (que lo intente otra orden o la charla)."""
        tipo = accion.get("tipo")
        if tipo not in ("app", "inicio_movil", "ajustes", "web", "marcar", "llamar_nombre", "kira", "permiso_fondo"):
            return None, ""
        if tipo == "llamar_nombre":
            return False, ("Para llamar a alguien por su nombre necesitaría leer tus contactos, y no lo hago. Dime el "
                           "número («Kira, marca el 600 123 456») y te abro el teléfono con él.")
        if self.java is None:
            return (False, self.SOLO_MOVIL) if tipo != "app" or accion.get("seguro") else (None, "")
        if tipo == "permiso_fondo":
            if self.java.puede_desde_fondo():
                return True, "Ya tengo ese permiso: puedo abrir apps aunque estés en otra."
            self.java.pedir_permiso_fondo()
            return True, "Te abro «Mostrar sobre otras apps»: activa el interruptor de Kira y vuelve."
        if en_fondo and not self.java.puede_desde_fondo():
            return False, self.SIN_PERMISO_FONDO
        try:
            if tipo == "kira":
                self.java.traer_kira()
                return True, "Aquí estoy."
            if tipo == "inicio_movil":
                self.java.inicio()
                return True, "Me aparto: sigo escuchándote si tengo «Siempre activa»."
            if tipo == "ajustes":
                self.java.ajustes(accion["accion"])
                return True, f"Te abro los ajustes {accion.get('nombre', 'del móvil')}."
            if tipo == "web":
                self.java.ver(accion["url"])
                return True, "Te lo abro en el navegador."
            if tipo == "marcar":
                self.java.marcar(accion["numero"])
                return True, f"Te abro el teléfono con el {accion['numero']}. Pulsa llamar si quieres llamar."
            hallada = self.buscar_app(accion["nombre"])
            if hallada is None:
                if not accion.get("seguro"):
                    return None, ""
                return False, f"No encuentro ninguna app que se llame «{accion['nombre']}»."
            etiqueta, paquete = hallada
            if not self.java.abrir_paquete(paquete):
                return False, f"«{etiqueta}» está instalada pero no se deja abrir."
            return True, f"Abro {etiqueta}."
        except Exception as e:
            return False, f"Android no me ha dejado: {e}"
