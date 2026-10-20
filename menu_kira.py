# -*- coding: utf-8 -*-
"""
menu_kira.py - Lógica PURA (sin Kivy) del menú de Kira: apartados, búsqueda local, notas, ajustes, estado.

Todo es local: nada de aquí sale a internet. La "búsqueda" busca en TUS notas, lecciones, módulos y
conversaciones; para preguntar a Kira se usa su conversación (que sí usa la API si hay clave).
"""
import json
import os
import re
import shutil
import sys
import threading
import unicodedata

# destino: ("panel", pantalla_del_panel) | ("pantalla", nombre)
# El menú enseña primero los PRINCIPALES (más sencillo); el resto aparece al tocar «Más apartados».
PRINCIPALES = ("hablar", "cerebro_kira", "mejoras", "lector", "juegos", "editor_codigo", "sala", "diseno", "ciber", "config")
APARTADOS = [
    {"id": "hablar",    "titulo": "Hablar con Kira", "desc": "Volver al botón de Kira",              "color": (0.10, 0.80, 0.50), "destino": ("pantalla", "inicio")},
    {"id": "sala",      "titulo": "Sala Hacker",     "desc": "Habitación 3D: programa y mejora", "color": (0.10, 0.90, 0.40), "destino": ("pantalla", "sala_hacker")},
    {"id": "diseno",    "titulo": "Sala de Diseño", "desc": "Playa 3D: webs, apps, videoclips", "color": (0.20, 0.75, 0.85), "destino": ("pantalla", "sala_diseno")},
    {"id": "cine",      "titulo": "Sala de Cine",    "desc": "Butacas: tus vídeos y clips",  "color": (0.85, 0.35, 0.40), "destino": ("pantalla", "sala_cine")},
    {"id": "mediateca", "titulo": "Mediateca",       "desc": "Tus vídeos y tu música",       "color": (0.95, 0.60, 0.30), "destino": ("pantalla", "mediateca")},
    {"id": "mezcla",    "titulo": "Mesa de mezcla",  "desc": "Mezcla pistas de audio",       "color": (0.90, 0.45, 0.70), "destino": ("pantalla", "mezcla")},
    {"id": "editor",    "titulo": "Editor de vídeo", "desc": "Cortar, unir, música…",        "color": (0.55, 0.45, 0.95), "destino": ("pantalla", "editor_video")},
    {"id": "cerebro_kira", "titulo": "Cerebro y oído", "desc": "Su IA y su oído, sin internet", "color": (0.55, 0.40, 0.95), "destino": ("pantalla", "cerebro_kira")},
    {"id": "lector",    "titulo": "Lector",          "desc": "Lee capturas: texto y código", "color": (0.20, 0.65, 0.75), "destino": ("pantalla", "lector")},
    {"id": "juegos",    "titulo": "Juegos",          "desc": "Juega y programa juegos",     "color": (0.95, 0.45, 0.30), "destino": ("pantalla", "juegos")},
    {"id": "editor_codigo", "titulo": "Editor de código", "desc": "Escribe y ejecuta Python", "color": (0.30, 0.55, 0.95), "destino": ("pantalla", "editor_codigo")},
    {"id": "taller",    "titulo": "Taller",          "desc": "Qué le falta y cómo prepararse", "color": (0.90, 0.75, 0.25), "destino": ("pantalla", "taller")},
    {"id": "ciber",     "titulo": "Ciberseguridad", "desc": "Búnker: defensa, aprendizaje, dispositivo", "color": (0.15, 0.85, 0.45), "destino": ("pantalla", "sala_ciber")},
    {"id": "bitacora",  "titulo": "Bitácora",        "desc": "Pasos, guías y arreglos",       "color": (0.70, 0.70, 0.78), "destino": ("pantalla", "bitacora")},
    {"id": "mejoras",   "titulo": "Mejoras",         "desc": "Pide una función nueva",      "color": (0.20, 0.70, 0.60), "destino": ("panel", "orden")},
    {"id": "pasarela",  "titulo": "Pasarela",        "desc": "Laboratorio de pruebas",      "color": (0.25, 0.55, 1.00), "destino": ("pantalla", "pasarela")},
    {"id": "modulos",   "titulo": "Módulos",         "desc": "Lo que Kira ya sabe hacer",   "color": (0.35, 0.50, 0.95), "destino": ("panel", "modulos")},
    {"id": "busqueda",  "titulo": "Búsqueda",        "desc": "Notas, lecciones, módulos",   "color": (0.95, 0.70, 0.20), "destino": ("pantalla", "busqueda")},
    {"id": "lienzo",    "titulo": "Lienzo",         "desc": "Kira dibuja paisajes",        "color": (0.40, 0.85, 0.95), "destino": ("pantalla", "lienzo")},
    {"id": "conocimiento", "titulo": "Conocimiento", "desc": "Lo que ha aprendido y estudia",    "color": (0.55, 0.90, 0.55), "destino": ("pantalla", "conocimiento")},
    {"id": "notas",     "titulo": "Notas",           "desc": "Apuntes rápidos",             "color": (0.95, 0.55, 0.25), "destino": ("pantalla", "notas")},
    {"id": "memoria",   "titulo": "Memoria",         "desc": "Conversación y lecciones",    "color": (0.75, 0.45, 1.00), "destino": ("pantalla", "memoria")},
    {"id": "estado",    "titulo": "Estado",          "desc": "Cómo está todo",              "color": (0.30, 0.80, 0.85), "destino": ("pantalla", "estado")},
    {"id": "consola",   "titulo": "Consola",         "desc": "Órdenes en texto",            "color": (0.55, 0.60, 0.65), "destino": ("panel", "consola")},
    {"id": "config",    "titulo": "Configuración",   "desc": "Voz, efectos, clave",         "color": (0.85, 0.40, 0.55), "destino": ("pantalla", "config")},
    {"id": "ayuda",     "titulo": "Ayuda",           "desc": "Qué hace cada cosa",          "color": (0.60, 0.75, 0.40), "destino": ("pantalla", "ayuda")},
]

AYUDA = (
    "ORBE: toca el orbe para entrar. Debajo puedes escribir o usar el micrófono.\n"
    "Si lo que dices es una orden de Kira (por ejemplo 'estado'), la ejecuta; si no, charla contigo "
    "(hace falta la clave de la API).\n\n"
    "SALA HACKER: una habitación en 3D. Caminas hasta la mesa; arrastra para mirar: a la izquierda la BIBLIOTECA, a la "
    "derecha la SALIDA. Toca el ordenador (o di «hackear» / «programar») para entrar en la terminal: APRENDER programación "
    "o MEJORAR a Kira con módulos nuevos (probados en el laboratorio y con tu confirmación).\n"
    "SALA DE DISEÑO: una habitación playera en 3D con una ventana a la playa. Al fondo, el ordenador de DISEÑO (webs de una página, "
    "maquetas de apps y videoclips); a la izquierda la MEDIATECA (tus vídeos y tu música) y la puerta de regreso; a la derecha la "
    "puerta del CINE. El «videoclip» es un guion con un storyboard animado; «Crear vídeo MP4» lo convierte en un vídeo MP4 real "
    "(escenas dibujadas por código, no imágenes de IA) en el laboratorio del PC, o aquí si el dispositivo tiene ffmpeg. "
    "Aún no edita vídeos ajenos ni mezcla audio.\n"
    "MESA DE MEZCLA: elige audios de tu mediateca y ajusta el volumen y la panorámica (izquierda/derecha) de cada pista; "
    "«Mezclar» crea un audio real. EDITOR DE VÍDEO: elige un vídeo y córtalo, redimensiónalo, únelo con otro (sin sonido), "
    "ponle música o quítale el audio. Todo se hace con ffmpeg: aquí si el aparato lo tiene, o en el laboratorio del PC; "
    "el resultado va a la mediateca.\n"
    "SALA DE CINE: butacas frente a una pantalla grande. Reproduce los videoclips creados, tu música y, si el APK incluye un "
    "reproductor de vídeo, los vídeos del móvil.\n"
    "CIBERSEGURIDAD: un búnker de SOLO lectura y aprendizaje. En la pantalla central Kira te enseña a defenderte de "
    "amenazas conocidas (malware, phishing, ransomware, contraseñas, WiFi, permisos…): qué son, sus señales y cómo "
    "protegerte, con tu progreso de estudio. REVISIÓN comprueba hábitos de seguridad del propio Kira y del aparato. "
    "DISPOSITIVO muestra el estado real (RAM, CPU, disco, red, batería). Aquí Kira NO ejecuta, descarga ni analiza nada "
    "peligroso, ni hace ataques: solo lee e informa.\n"
    "BITÁCORA: Kira recuerda los pasos para montarla (instalar ffmpeg, arrancar el laboratorio, la clave, el APK…), dónde "
    "está cada cosa y qué ha fallado. Di «bitácora» para ver el resumen, «cómo instalar ffmpeg» para una guía, "
    "«diagnosticar» para que relacione los fallos recientes con su arreglo, «apunta: …» para dejarle una nota y "
    "«fallos resueltos» cuando lo arregles.\n"
    "ESCUCHA: con la escucha permanente activada, Kira oye siempre pero SOLO contesta cuando dices «Kira» (por ejemplo "
    "«Kira, ¿qué hora es?», o «Kira» y luego lo que quieras). Lo que oye sin su nombre se borra a los 15 segundos y nunca "
    "se guarda. Funciona con la app abierta en pantalla. Se apaga en Configuración.\n"
    "MEJORAS POR VOZ: «Kira, mejora…», «Kira, aprende a…» o «Kira, añade…» abre la terminal de mejoras, lo programa y "
    "lo prueba en el laboratorio, y te lee el resultado. Instalarlo SIEMPRE requiere tocar «Aplicar» dos veces: la voz "
    "puede pedir, pero no aprobar. Necesita cerebro de IA y el laboratorio conectado.\n"
    "PORTADA: toca el botón redondo de neón para entrar al menú. El neón brilla más cuando Kira te escucha y cuando habla.\n"
    "EDITOR DE CÓDIGO: escribe Python, pulsa «Ejecutar» y ves lo que imprime. «Ejemplos…» trae el curso básico y avanzado, "
    "programas completos y juegos. Modo seguro: sin archivos, red ni sistema y se corta a los 5 segundos. «Guardar» lo deja "
    "en «Abrir…».\n"
    "JUEGOS: Rompeladrillos, Serpiente, Esquiva, Saltarín y Pong, hechos con el motor de Kira. Con «Código» los abres en el "
    "editor; «Programar un juego nuevo» trae una plantilla. Un juego es una clase que hereda de Juego (motor_juegos_kira).\n"
    "MEJORAS MÁS POTENTES: los módulos pueden guardar sus propios datos, usar los recuerdos de Kira, programar avisos "
    "(«avísame en 10 minutos…») y añadir juegos. Escribe «avisos» para ver los pendientes.\n"
    "CEREBRO Y OÍDO: Kira puede tener su PROPIA IA dentro de la app (sin Termux ni API): en «Cerebro y oído» descarga una "
    "vez el modelo ligero (1,4 GB, rápido) o el listo (3 GB) y se enciende sola al abrir Kira. Las respuestas van "
    "apareciendo mientras piensa. El OÍDO PROPIO (39 MB) escucha sin parar, sin pitidos y sin internet, en todas las "
    "pantallas; si no está, usa el reconocedor de Android.\n"
    "LECTOR: Kira lee el texto y el código de tus capturas de pantalla, sin internet. Descarga una vez los idiomas (6 MB) "
    "y di «lee la última captura». Si es código, reconstruye la sangría y puedes abrirlo en el editor para ejecutarlo.\n"
    "AL ABRIR: sale «Preparando a Kira» y deja listo el oído, el cerebro (lo carga en la memoria; si no está y "
    "tienes WiFi, lo descarga), el lector y el permiso de la pantalla. Entra sola cuando todo está listo, o pulsa "
    "«Entrar ya». Con «Siempre activa», el cerebro se queda cargado al cerrar Kira y la próxima vez arranca al momento.\n"
    "VER LA PANTALLA: en Cerebro y oído pulsa «Siempre activa» (Kira sigue oyendo aunque uses otra app; sale una "
    "notificación fija) y «Dejar que vea la pantalla» (Android te pide permiso). Luego di «Kira, ¿qué ves?», «lee la "
    "pantalla» o «explícame la pantalla». Solo mira cuando se lo pides y borra la captura al momento. En las apps "
    "privadas (WhatsApp, Telegram, Gmail, Fotos…) no mira: «no mires esta app» añade la que tengas abierta y «apps "
    "privadas» te enseña la lista (hace falta el permiso para saber qué app usas). Las apps de bancos salen en negro.\n"
    "RECUERDOS: Kira guarda en una carpeta suya (privada y firmada) lo que le enseñas y lo que le explica Claude. "
    "Antes de preguntar a nadie busca ahí, y solo abre los trozos del índice que necesita, sin llenar la RAM. "
    "Busca también por significado: sabe que minino es gato, y aprende palabras nuevas (con el modelo del móvil o con "
    "«parecido: minino = gato, felino»). Órdenes: «guarda recuerdo: …», «qué recuerdas de …», «olvida recuerdo N», «recuerdos».\n"
    "ESTUDIO: Kira aprende sola sin la API. «estudia: tema» lee la Wikipedia y lo guarda; «estudia python» guarda la "
    "documentación de Python que trae el móvil (sin internet); «aprende sola» recorre un plan de estudio poco a poco; "
    "«plan de estudio» y «qué has aprendido» para ver cómo va.\n"
    "CEREBRO: Kira puede pensar con un modelo de IA en el propio móvil (llama.cpp en Termux, sin internet ni API) o con "
    "Claude. Escribe «cerebro» para ver cuál usa; «cerebro auto» usa el local si está encendido. Guía: CEREBRO_LOCAL.md.\n"
    "TALLER: la lista de lo que Kira sabe hacer y lo que le falta. Para cada cosa que falta te dice si puede programarla "
    "ya (botón «Programarla con Kira»: deja el pedido listo en la terminal de mejoras) o qué hace falta antes (casi siempre "
    "ffmpeg en el PC). Si arrancaste el laboratorio con --permitir-instalar, también puede pedirle al PC que instale lo que "
    "falta, siempre con tu confirmación. Escribe «capacidades» o «preparar mesa de mezcla» para lo mismo por texto.\n"
    "MEJORAS: describes una función, Kira escribe el código, el laboratorio lo prueba y TÚ decides si se aplica.\n"
    "PASARELA: el laboratorio donde se prueban las mejoras (otro programa, en tu PC o Termux).\n"
    "BÚSQUEDA: busca en tus notas, lecciones, módulos y conversaciones guardadas. No busca en internet.\n"
    "APRENDER: dile «aprende que mi gato se llama Miko». Si preguntas algo que no sabe («qué es un agujero negro»), "
    "busca en la Wikipedia, te enseña el resumen con su fuente y solo lo guarda si dices «sí». «Eso está mal» lo descarta.\n"
    "LIENZO: «dibuja una playa al atardecer con palmeras» (también montañas, bosque, desierto, ciudad, lago, espacio). "
    "Dibuja por código, no es una IA de imágenes.\n"
    "NOTAS: apuntes locales. MEMORIA: lo que habéis hablado y las lecciones de mejoras.\n"
    "ESTADO: clave, laboratorio, módulos, espacio libre.\n\n"
    "Todo se guarda solo en este dispositivo. Nada se aplica sin tu confirmación."
)


# =====================================================================================
#  BÚSQUEDA LOCAL
# =====================================================================================
def _norm(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def buscar_local(consulta, fuentes, maximo=30):
    """fuentes: {nombre: [textos]}. Coincidencia por TODAS las palabras, sin tildes ni mayúsculas.
    Devuelve [(fuente, texto_recortado)]. Sin regex: lo que escribas se toma literal."""
    palabras = [p for p in _norm(re.sub(r"\s+", " ", str(consulta)).strip()[:100]).split(" ") if p]
    if not palabras:
        return []
    res = []
    for nombre, textos in fuentes.items():
        for t in textos:
            n = _norm(t)
            if all(p in n for p in palabras):
                res.append((nombre, str(t).strip()[:240]))
                if len(res) >= maximo:
                    return res
    return res


# =====================================================================================
#  ALMACENES JSON (atómicos)
# =====================================================================================
def _leer_json(ruta, defecto):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, type(defecto)) else defecto
    except (OSError, ValueError):
        return defecto


def _guardar_json(ruta, datos):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


class Notas:
    MAX_NOTAS, MAX_CHARS = 200, 500

    def __init__(self, ruta):
        self.ruta, self._lock = ruta, threading.Lock()
        self.items = [n for n in _leer_json(ruta, []) if isinstance(n, dict) and "id" in n and "texto" in n]

    def listar(self):
        with self._lock:
            return list(reversed(self.items))

    def textos(self):
        return [n["texto"] for n in self.listar()]

    def anadir(self, texto):
        texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", str(texto)).strip()[: self.MAX_CHARS]
        if not texto:
            return False, "La nota está vacía."
        with self._lock:
            if len(self.items) >= self.MAX_NOTAS:
                return False, f"Hay {self.MAX_NOTAS} notas: borra alguna antes."
            nuevo = max((n["id"] for n in self.items), default=0) + 1
            self.items.append({"id": nuevo, "texto": texto})
            _guardar_json(self.ruta, self.items)
        return True, "Nota guardada."

    def borrar(self, id_nota):
        with self._lock:
            antes = len(self.items)
            self.items = [n for n in self.items if n["id"] != id_nota]
            if len(self.items) != antes:
                _guardar_json(self.ruta, self.items)
                return True
        return False


def principales():
    return [a for a in APARTADOS if a["id"] in PRINCIPALES]


def secundarios():
    return [a for a in APARTADOS if a["id"] not in PRINCIPALES]


def color_claro(rgb, mezcla=0.82):
    """Fondo pastel para una baldosa del menú: el color mezclado con blanco."""
    return tuple(c * (1 - mezcla) + mezcla for c in rgb) + (1,)


def color_oscuro(rgb, factor=0.55):
    """Texto legible sobre el fondo claro: el mismo color, oscurecido."""
    return tuple(c * factor for c in rgb) + (1,)


class AjustesInterfaz:
    """Preferencias de la interfaz (voz, escucha permanente y velocidad del texto)."""
    DEFECTO = {"voz_hablar": True, "velocidad": 45, "escucha_permanente": True, "oido_propio": True}

    def __init__(self, ruta):
        self.ruta = ruta
        datos = _leer_json(ruta, {})
        self.voz_hablar = datos.get("voz_hablar", True) is not False
        v = datos.get("velocidad", 45)
        self.velocidad = int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 45
        self.velocidad = max(15, min(self.velocidad, 120))
        self.escucha_permanente = datos.get("escucha_permanente", True) is not False
        self.oido_propio = datos.get("oido_propio", True) is not False

    def guardar(self):
        try:
            _guardar_json(self.ruta, {"voz_hablar": self.voz_hablar, "velocidad": self.velocidad,
                                      "escucha_permanente": self.escucha_permanente, "oido_propio": self.oido_propio})
        except OSError:
            pass

    def cambiar_velocidad(self, delta):
        self.velocidad = max(15, min(120, self.velocidad + int(delta)))
        self.guardar()

    def alternar_voz(self):
        self.voz_hablar = not self.voz_hablar
        self.guardar()
        return self.voz_hablar

    def alternar_oido(self):
        self.oido_propio = not self.oido_propio
        self.guardar()
        return self.oido_propio

    def alternar_escucha(self):
        self.escucha_permanente = not self.escucha_permanente
        self.guardar()
        return self.escucha_permanente


# =====================================================================================
#  ESTADO REAL DEL SISTEMA
# =====================================================================================
def _ram_libre():
    try:
        import psutil
        m = psutil.virtual_memory()
        return f"{m.available / 1024 ** 3:.1f} GB libres de {m.total / 1024 ** 3:.1f} GB"
    except Exception:
        pass
    try:  # Linux / Android
        with open("/proc/meminfo", encoding="utf-8") as f:
            d = {l.split(":")[0]: int(l.split()[1]) for l in f if ":" in l and len(l.split()) > 1}
        return f"{d['MemAvailable'] / 1024 ** 2:.1f} GB libres de {d['MemTotal'] / 1024 ** 2:.1f} GB"
    except Exception:
        return "no disponible"


def estado_sistema(ctl, dir_datos):
    """Lista de líneas con datos reales. 'ctl' es PanelControl (puede tardar unos segundos: hace una consulta de red)."""
    e = ctl.estado()
    core = getattr(ctl, "core", None)
    activo = core.cerebro_activo() if callable(getattr(core, "cerebro_activo", None)) else ("claude" if e["clave"] else None)
    lineas = [f"Cerebro de IA: {({'local': 'modelo local (sin internet)', 'claude': 'Claude (API)'}).get(activo, 'FALTA (ni modelo local encendido ni clave de Claude)')}",
              f"Laboratorio: {e['lab']}",
              f"Módulos instalados: {e['modulos']}",
              f"Mejora pendiente de decidir: {'sí' if e['pendiente'] else 'no'}"]
    try:
        libre = shutil.disk_usage(dir_datos).free
        lineas.append(f"Espacio libre: {libre / 1024 ** 3:.1f} GB")
    except OSError:
        lineas.append("Espacio libre: no disponible")
    lineas.append(f"Memoria: {_ram_libre()}")
    try:
        import psutil
        b = psutil.sensors_battery()
        if b is not None:
            lineas.append(f"Batería: {b.percent:.0f}%")
    except Exception:
        pass
    lineas.append(f"Python {sys.version.split()[0]} en {sys.platform}")
    return lineas
