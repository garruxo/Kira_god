# -*- coding: utf-8 -*-
"""
pintor_kira.py - El PINTOR de Kira: crea IMÁGENES con su propia IA, dentro del móvil, sin internet ni servicios de
terceros (una vez descargado el modelo).

Motor: stable-diffusion.cpp («sd-cli»), compilado para Android dentro del APK como libkira_pintor(_dp).so
(herramientas_pc/compilar_pintor_android.sh), igual que el cerebro. Modelos (se descargan UNA vez):
  - rapido   : SDXS-512 (683 MB): un solo paso, unos segundos. Bueno para ideas y bocetos.
  - realista : SD-Turbo pequeño (1,8 GB): 4 pasos, más detalle y más «foto».
  - ampliador: Real-ESRGAN ×4 (64 MB, opcional): pasa de 512 a 2048 píxeles (lento en el móvil).
Cómo pinta: la petición en español se convierte en un prompt en inglés (con el cerebro de Kira o Claude si están; si no,
con un pequeño diccionario), se añade el estilo (foto, ilustración, acuarela, anime, 3D, óleo, boceto) y se lanza el
motor. El progreso se lee de lo que va escribiendo el motor (cargar, pasos, decodificar).

Honesto: un móvil no es una tarjeta gráfica. Las imágenes son de 512 píxeles (ampliables), tardan de unos segundos a
un par de minutos según el móvil y el modelo, y no tienen la calidad de los generadores profesionales de pago (esos
necesitan un ordenador con GPU). Licencias: SDXS (openrail++), SD-Turbo (licencia comunitaria de Stability AI: uso
personal), Real-ESRGAN (BSD).
Lógica sin Kivy (se prueba en el PC con un motor falso).
"""
import json
import os
import random
import re
import signal
import subprocess
import threading
import time
import unicodedata

import descargas_kira as dsc

MODELOS = {
    "rapido": {"nombre": "pincel rápido (SDXS, 1 paso)", "archivo": "sdxs-512-tinySDdistilled_Q8_0.gguf",
               "bytes": 682_847_200, "mb": 683, "pasos": 1, "cfg": 1.0, "metodo": "euler_a", "ram_mb": 1300,
               "url": "https://huggingface.co/concedo/sdxs-512-tinySDdistilled-GGUF/resolve/main/"
                      "sdxs-512-tinySDdistilled_Q8_0.gguf",
               "sha256": "409ab23582ee074c6b9d5395784fc0741b0599fb9d138686c69087c71678eb6a"},
    "realista": {"nombre": "pincel realista (SD-Turbo, 4 pasos)", "archivo": "tiny-sd-turbo_q8_0.gguf",
                 "bytes": 1_838_924_448, "mb": 1839, "pasos": 4, "cfg": 1.0, "metodo": "euler_a", "ram_mb": 2600,
                 "url": "https://huggingface.co/akleine/tiny-sd-turbo_q8_0/resolve/main/tiny-sd-turbo_q8_0.gguf",
                 "sha256": "e852d17c483f1ce990e928344added502e4469e8114399ca3b363e708bdd8239"},
}
AMPLIADOR = {"nombre": "ampliador ×4 (Real-ESRGAN)", "archivo": "RealESRGAN_x4plus.pth", "bytes": None, "mb": 64,
             "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"}
BINARIOS = ("libkira_pintor_dp.so", "libkira_pintor.so")       # primero el rápido; si el móvil no puede, el genérico
FORMATOS = {"cuadrada": (512, 512), "vertical": (448, 640), "horizontal": (640, 448)}

ESTILOS = {
    "foto": ("realistic photo, natural light, sharp focus, high detail, 35mm photograph",
             ("foto", "fotografia", "realista", "real", "fotorrealista", "retrato")),
    "ilustracion": ("digital illustration, vibrant colors, detailed, artstation",
                    ("ilustracion", "dibujo", "caricatura", "dibujos animados", "comic", "cartel", "poster")),
    "acuarela": ("watercolor painting, soft colors, paper texture", ("acuarela",)),
    "anime": ("anime style, clean lines, vibrant colors", ("anime", "manga")),
    "3d": ("3d render, soft studio lighting, highly detailed", ("3d", "render", "pixar")),
    "oleo": ("oil painting, visible brush strokes, classic art", ("oleo", "cuadro", "pintura al oleo")),
    "boceto": ("pencil sketch, black and white, hand drawn", ("boceto", "lapiz", "a lapiz", "esbozo")),
}
NEGATIVO = "blurry, low quality, deformed, extra fingers, watermark, text"

# diccionario mínimo para cuando no hay cerebro (la IA de imágenes entiende mucho mejor el inglés)
_DICC = {
    "gato": "cat", "gatos": "cats", "perro": "dog", "perros": "dogs", "caballo": "horse", "pajaro": "bird",
    "pajaros": "birds", "pez": "fish", "leon": "lion", "tigre": "tiger", "oso": "bear", "lobo": "wolf", "zorro": "fox",
    "dragon": "dragon", "mariposa": "butterfly", "conejo": "rabbit", "vaca": "cow", "elefante": "elephant",
    "mujer": "woman", "hombre": "man", "nino": "child", "nina": "girl", "chico": "boy", "chica": "girl",
    "persona": "person", "gente": "people", "anciano": "old man", "anciana": "old woman", "bebe": "baby",
    "casa": "house", "castillo": "castle", "ciudad": "city", "pueblo": "village", "calle": "street", "puente": "bridge",
    "playa": "beach", "mar": "sea", "oceano": "ocean", "montana": "mountain", "montanas": "mountains", "bosque": "forest",
    "rio": "river", "lago": "lake", "desierto": "desert", "isla": "island", "cielo": "sky", "nubes": "clouds",
    "sol": "sun", "luna": "moon", "estrellas": "stars", "noche": "night", "dia": "day", "atardecer": "sunset",
    "amanecer": "sunrise", "lluvia": "rain", "nieve": "snow", "niebla": "fog", "tormenta": "storm", "flor": "flower",
    "flores": "flowers", "arbol": "tree", "arboles": "trees", "jardin": "garden", "campo": "field", "hierba": "grass",
    "coche": "car", "moto": "motorcycle", "barco": "boat", "avion": "airplane", "tren": "train", "bicicleta": "bicycle",
    "nave": "spaceship", "espacial": "space", "espacio": "outer space", "planeta": "planet", "robot": "robot",
    "comida": "food", "pizza": "pizza", "tarta": "cake", "cafe": "coffee", "fruta": "fruit", "manzana": "apple",
    "mesa": "table", "silla": "chair", "libro": "book", "ventana": "window", "puerta": "door", "habitacion": "room",
    "cocina": "kitchen", "oficina": "office", "biblioteca": "library", "iglesia": "church", "templo": "temple",
    "rojo": "red", "roja": "red", "azul": "blue", "verde": "green", "amarillo": "yellow", "amarilla": "yellow",
    "negro": "black", "negra": "black", "blanco": "white", "blanca": "white", "naranja": "orange", "rosa": "pink",
    "morado": "purple", "dorado": "golden", "plateado": "silver", "gris": "gray", "marron": "brown",
    "grande": "big", "pequeno": "small", "pequena": "small", "bonito": "beautiful", "bonita": "beautiful",
    "precioso": "gorgeous", "viejo": "old", "vieja": "old", "nuevo": "new", "antiguo": "ancient", "moderno": "modern",
    "futurista": "futuristic", "magico": "magical", "magica": "magical", "oscuro": "dark", "oscura": "dark",
    "brillante": "bright", "feliz": "happy", "triste": "sad", "tranquilo": "calm", "sonriendo": "smiling",
    "corriendo": "running", "volando": "flying", "durmiendo": "sleeping", "sentado": "sitting", "sentada": "sitting",
    "jugando": "playing", "leyendo": "reading", "comiendo": "eating", "bailando": "dancing", "nadando": "swimming",
    "con": "with", "en": "in", "sobre": "on", "bajo": "under", "junto": "next to", "y": "and", "de": "of",
    "al": "at the", "del": "of the", "entre": "between", "frente": "in front of", "detras": "behind",
}
_VACIAS = {"un", "una", "unos", "unas", "el", "la", "los", "las", "lo", "que", "me", "mi", "por", "favor", "imagen",
           "foto", "fotografia", "dibujo", "ilustracion", "pinta", "pintame", "dibuja", "dibujame", "hazme", "crea",
           "creame", "genera", "generame", "quiero", "estilo", "tipo", "realista"}


class PintorError(RuntimeError):
    pass


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def carpeta_librerias_android():
    try:
        from jnius import autoclass
        return str(autoclass("org.kivy.android.PythonActivity").mActivity.getApplicationInfo().nativeLibraryDir)
    except Exception:
        return None


def memoria_libre_mb():
    """MB de memoria disponibles (Linux/Android: /proc/meminfo). None si no se sabe."""
    try:
        with open("/proc/meminfo", encoding="ascii") as f:
            for linea in f:
                if linea.startswith("MemAvailable:"):
                    return int(linea.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


# =====================================================================================
#  PEDIDOS («Kira, pinta…») Y PROMPT
# =====================================================================================
_PIDE = re.compile(
    r"^(?:por\s+favor\s+)?(?:p[ií]ntame|pinta|dib[uú]jame|dibuja|hazme|haz|cr[eé]ame|crea|gen[eé]rame|genera|"
    r"quiero)\s+(?:(?:(?:una?|otra?)\s+)?(?P<que>imagen(?:es)?|foto(?:graf[ií]a)?|retrato|ilustraci[oó]n|dibujo|"
    r"cuadro|acuarela|p[oó]ster|cartel|fondo\s+de\s+pantalla|wallpaper|boceto)\s*(?:de|del|con|sobre)?\s+)?"
    r"(?P<resto>.+)$", re.I | re.S)


def pedido_imagen(texto, siempre_dibuja=True):
    """«pinta un gato en la luna», «hazme una foto de…», «dibuja…» -> la descripción. None si no es un pedido de
    imagen. Con «hazme / crea / genera / quiero» hace falta decir imagen, foto, dibujo… (si no, puede ser otra cosa).
    siempre_dibuja=False: «dibuja X» sin más no cuenta (lo hace el lienzo de siempre)."""
    t = " ".join(str(texto or "").split()).strip(" .!¡?¿")
    m = _PIDE.match(t)
    if not m:
        return None
    verbo = _plano(t.split()[0])
    que = m.group("que")
    resto = m.group("resto").strip(" ,.:")
    if len(resto) < 2:
        return None
    if verbo.startswith(("hazme", "haz", "crea", "genera", "quiero")) and not que:
        return None
    if verbo.startswith("dibuja") and not que and not siempre_dibuja:
        return None
    return ((que + " de " if que and _plano(que).startswith(("acuarela", "retrato", "boceto", "foto", "cuadro"))
             else "") + resto)[:300]


def estilo_de(texto):
    t = _plano(texto)
    for clave, (_ingles, palabras) in ESTILOS.items():
        if clave != "foto" and any(re.search(r"\b" + re.escape(p) + r"\b", t) for p in palabras):
            return clave
    return "foto"


def formato_de(texto):
    t = _plano(texto)
    if re.search(r"\b(vertical|de pie|fondo de pantalla|wallpaper|movil)\b", t):
        return "vertical"
    if re.search(r"\b(horizontal|apaisad[ao]|panoramic[ao]|paisaje ancho)\b", t):
        return "horizontal"
    return "cuadrada"


def traducir_simple(texto):
    """Traducción palabra a palabra (sin cerebro). No es buena, pero la IA de imágenes entiende mejor el inglés."""
    palabras = re.findall(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ0-9]+", str(texto))
    sal = []
    for p in palabras:
        q = _plano(p)
        if q in _VACIAS:
            continue
        sal.append(_DICC.get(q, p))
    return " ".join(sal)


SISTEMA_PROMPT = (
    "Convierte la petición de imagen del usuario (en español) en un prompt en INGLÉS para un generador de imágenes "
    "Stable Diffusion: el sujeto, qué hace, el lugar, la luz y el encuadre, de 12 a 40 palabras separadas por comas. "
    "Sin explicaciones ni comillas: responde SOLO con el prompt.")


def limpiar_prompt(texto):
    t = str(texto or "").strip().splitlines()[0] if str(texto or "").strip() else ""
    t = re.sub(r"^(?:prompt|english prompt)\s*:\s*", "", t, flags=re.I).strip(" \"'`*")
    return t[:400]


def preparar(descripcion, traducir=None):
    """{'prompt', 'negativo', 'estilo', 'formato', 'ingles_por'} a partir de lo que pediste en español.
    traducir(texto) -> prompt en inglés (el cerebro de Kira o Claude); si falla o no hay, diccionario simple."""
    estilo, formato = estilo_de(descripcion), formato_de(descripcion)
    ingles, por = "", "diccionario"
    if traducir is not None:
        try:
            ingles = limpiar_prompt(traducir(descripcion))
            por = "cerebro"
        except Exception:
            ingles = ""
        if len(ingles) < 4 or re.search(r"[áéíóúñ¿¡]", ingles) or \
                re.search(r"\b(?:un|una|unos|unas|el|los|las|del|con|y|que|muy|para|por)\b", ingles.lower()):
            ingles, por = "", "diccionario"          # contestó en español: mejor el diccionario
    if not ingles:
        ingles = traducir_simple(descripcion) or str(descripcion)
    return {"prompt": f"{ingles}, {ESTILOS[estilo][0]}"[:600], "negativo": NEGATIVO, "estilo": estilo,
            "formato": formato, "ingles_por": por}


# =====================================================================================
#  LEER EL PROGRESO DEL MOTOR
# =====================================================================================
_PASO = re.compile(r"(\d+)/(\d+)\s*-\s*([\d.]+)\s*(s/it|it/s|MB/s|GB/s)")


class Progreso:
    """Va leyendo lo que escribe sd-cli y da (fraccion, texto). Fases: cargar, preparar, pintar, revelar."""

    def __init__(self, pasos):
        self.pasos = max(1, int(pasos))
        self.fraccion, self.texto, self.fase = 0.02, "Preparando el pincel…", "cargar"
        self._resto = ""

    def leer(self, trozo):
        datos = self._resto + trozo
        partes = re.split(r"[\r\n]", datos)
        self._resto = partes.pop()                         # lo último puede estar a medias
        if len(self._resto) > 400:
            self._resto = self._resto[-200:]
        for linea in partes:
            self._linea(linea)
        m = list(_PASO.finditer(self._resto))              # la barra de pasos se repinta sin salto de línea
        if m:
            self._paso(m[-1])
        return self.fraccion, self.texto

    def _linea(self, l):
        bajo = l.lower()
        m = list(_PASO.finditer(l))
        if m:
            self._paso(m[-1])
        elif "loading model" in bajo or "loading diffusion model" in bajo:
            self._poner(0.04, "Cargando el pincel en la memoria…", "cargar")
        elif "get_learned_condition completed" in bajo or "generate_image " in bajo or "sampling using" in bajo:
            self._poner(0.20, "Entendiendo lo que me pides…", "preparar")
        elif "sampling completed" in bajo:
            self._poner(0.86, "Revelando la imagen…", "revelar")
        elif "decoding" in bajo:
            self._poner(0.88, "Revelando la imagen…", "revelar")
        elif "decode_first_stage completed" in bajo or "upscaling" in bajo or "upscale" in bajo and "completed" in bajo:
            self._poner(0.96, "Dando los últimos toques…", "revelar")
        elif "save result" in bajo or "generate_image completed" in bajo:
            self._poner(0.99, "Guardando…", "fin")

    def _paso(self, m):
        n, total, unidad = int(m.group(1)), int(m.group(2)), m.group(4)
        if unidad in ("MB/s", "GB/s"):                     # cargando el modelo
            self._poner(0.04 + 0.14 * n / max(1, total), "Cargando el pincel en la memoria…", "cargar")
        elif self.fase in ("cargar", "preparar", "pintar") and total == self.pasos:
            self._poner(0.20 + 0.66 * n / total, f"Pintando… paso {n} de {total}", "pintar")
        else:                                              # revelar por trozos, o ampliar
            self._poner(0.88 + 0.10 * n / max(1, total), "Revelando la imagen…" if self.fase != "ampliar" else
                        f"Ampliando… {n} de {total}", self.fase if self.fase == "ampliar" else "revelar")

    def _poner(self, f, texto, fase):
        self.fraccion = max(self.fraccion, min(0.995, f))
        self.texto, self.fase = texto, fase


# =====================================================================================
#  EL PINTOR
# =====================================================================================
class Pintor:
    def __init__(self, dir_datos, carpeta_binarios=None, abrir=dsc.abrir_https, lanzar=subprocess.Popen,
                 reloj=time.monotonic, memoria=memoria_libre_mb):
        self.dir = dir_datos
        self.carpeta_modelos = os.path.join(dir_datos, "pintor")
        self.carpeta_imagenes = os.path.join(dir_datos, "imagenes")
        self.ruta_cfg = os.path.join(dir_datos, "pintor.json")
        self.ruta_log = os.path.join(dir_datos, "pintor.log")
        self._binarios_dir = carpeta_binarios
        self._abrir, self._lanzar, self._reloj, self._memoria = abrir, lanzar, reloj, memoria
        self._cancelar = threading.Event()
        self.proceso = None
        self.estado, self.mensaje, self.progreso = "listo", "", 0.0
        self.binario_malo = set()                         # los que no arrancan en este móvil
        cfg = {}
        try:
            with open(self.ruta_cfg, encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, ValueError):
            pass
        cfg = cfg if isinstance(cfg, dict) else {}
        self.modelo = cfg.get("modelo") if cfg.get("modelo") in MODELOS else "rapido"
        h = cfg.get("hilos", 4)
        self.hilos = int(h) if isinstance(h, int) and 1 <= h <= 16 else 4

    def _guardar(self):
        os.makedirs(self.dir, exist_ok=True)
        tmp = self.ruta_cfg + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"modelo": self.modelo, "hilos": self.hilos}, f)
        os.replace(tmp, self.ruta_cfg)

    # ---------- motor ----------
    def binarios(self):
        carpeta = self._binarios_dir or os.environ.get("KIRA_PINTOR_DIR") or carpeta_librerias_android()
        if not carpeta:
            return []
        candidatos = list(BINARIOS) + ["kira_pintor"]              # «kira_pintor»: el compilado para PC (pruebas)
        return [os.path.join(carpeta, b) for b in candidatos
                if os.path.isfile(os.path.join(carpeta, b)) and os.path.join(carpeta, b) not in self.binario_malo]

    def tiene_motor(self):
        return bool(self.binarios())

    # ---------- modelos ----------
    def ruta_modelo(self, id_=None):
        return os.path.join(self.carpeta_modelos, MODELOS[id_ or self.modelo]["archivo"])

    def instalado(self, id_=None):
        m = MODELOS[id_ or self.modelo]
        r = self.ruta_modelo(id_)
        return os.path.isfile(r) and os.path.getsize(r) == m["bytes"]

    def instalados(self):
        return [k for k in MODELOS if self.instalado(k)]

    def elegir(self, id_):
        if id_ not in MODELOS:
            raise PintorError("Ese pincel no existe. Hay: " + ", ".join(MODELOS))
        self.modelo = id_
        self._guardar()

    def ruta_ampliador(self):
        return os.path.join(self.carpeta_modelos, AMPLIADOR["archivo"])

    def ampliador_instalado(self):
        r = self.ruta_ampliador()
        return os.path.isfile(r) and os.path.getsize(r) > 1_000_000

    def descargar(self, id_=None, progreso=None):
        """Descarga un pincel ('rapido' | 'realista') o el ampliador ('ampliador'). Bloquea: úsalo en un hilo."""
        id_ = id_ or self.modelo
        m = AMPLIADOR if id_ == "ampliador" else MODELOS[id_]
        final = self.ruta_ampliador() if id_ == "ampliador" else self.ruta_modelo(id_)
        self._cancelar.clear()
        self.estado, self.mensaje = "descargando", f"Descargando el {m['nombre']}…"

        def prog(f, bajados, total):
            self.progreso = f
            if progreso:
                progreso(f, bajados, total)
        try:
            ruta = dsc.bajar(m["url"], final, m["bytes"], m["nombre"], abrir=self._abrir, progreso=prog,
                             cancelado=self._cancelar.is_set)
        except dsc.DescargaError as e:
            self.estado, self.mensaje = "listo", str(e)
            raise PintorError(str(e))
        self.estado, self.mensaje, self.progreso = "listo", f"{m['nombre'].capitalize()} descargado.", 1.0
        return ruta

    def cancelar(self):
        """Pausa la descarga o corta la pintura en marcha."""
        self._cancelar.set()
        p = self.proceso
        if p is not None and p.poll() is None:
            try:
                p.terminate()
            except OSError:
                pass

    def borrar(self, id_):
        final = self.ruta_ampliador() if id_ == "ampliador" else self.ruta_modelo(id_)
        for x in (final, final + ".parte"):
            if os.path.isfile(x):
                os.remove(x)

    # ---------- pintar ----------
    def memoria_suficiente(self, id_=None):
        libre = self._memoria()
        return libre is None or libre >= MODELOS[id_ or self.modelo]["ram_mb"]

    def argumentos(self, binario, id_, prompt, negativo, ancho, alto, semilla, salida, vista=None):
        m = MODELOS[id_]
        args = [binario, "-m", self.ruta_modelo(id_), "-p", prompt, "-W", str(int(ancho)), "-H", str(int(alto)),
                "--steps", str(m["pasos"]), "--cfg-scale", str(m["cfg"]), "--sampling-method", m["metodo"],
                "-s", str(int(semilla)), "-t", str(self.hilos), "-o", salida, "--mmap", "--vae-tiling"]
        if negativo and m["cfg"] > 1.0:                    # con cfg 1 el negativo no hace nada: no se gasta
            args += ["-n", negativo]
        if vista and m["pasos"] > 1:
            args += ["--preview", "proj", "--preview-path", vista, "--preview-interval", "1"]
        return args

    def _correr(self, args, prog, al_progreso, limite):
        """Lanza el motor y lee su progreso. (codigo_salida, ultimas_lineas)."""
        os.makedirs(self.dir, exist_ok=True)
        extra = {"start_new_session": True} if self._lanzar is subprocess.Popen else {}
        self.proceso = self._lanzar(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                    cwd=self.dir, **extra)
        cola, fin = [], self._reloj() + limite
        vigia = threading.Timer(limite, self._matar)        # si se queda colgado sin escribir nada, se corta igual
        vigia.daemon = True
        vigia.start()
        try:
            modo = "wb" if os.path.isfile(self.ruta_log) and os.path.getsize(self.ruta_log) > 2_000_000 else "ab"
            with open(self.ruta_log, modo) as log:
                cola = self._leer_salida(log, prog, al_progreso, fin)
        finally:
            vigia.cancel()
        try:
            codigo = self.proceso.wait(timeout=10)
        except Exception:
            self._matar()
            codigo = -9
        self.proceso = None
        return codigo, "".join(cola)[-1500:]

    def _leer_salida(self, log, prog, al_progreso, fin):
        cola = []
        salida = self.proceso.stdout
        leer = salida.read1 if hasattr(salida, "read1") else salida.read
        while True:
            if self._cancelar.is_set() or self._reloj() > fin:
                self._matar()
                break
            trozo = leer(4096)
            if not trozo:
                break
            log.write(trozo)
            texto = trozo.decode("utf-8", "replace")
            cola.append(texto)
            cola = cola[-40:]
            f, t = prog.leer(texto)
            self.progreso = f
            if al_progreso:
                al_progreso(f, t)
        return cola

    def _matar(self):
        p = self.proceso
        if p is None or p.poll() is not None:
            return
        try:
            os.killpg(p.pid, signal.SIGKILL) if hasattr(os, "killpg") and self._lanzar is subprocess.Popen else p.kill()
        except (OSError, ProcessLookupError):
            try:
                p.kill()
            except OSError:
                pass

    def pintar(self, prompt, id_=None, formato="cuadrada", semilla=None, negativo=NEGATIVO, al_progreso=None,
               vista=None, limite=900):
        """Pinta. Devuelve {'ruta', 'segundos', 'semilla', 'modelo'}. Lanza PintorError si no puede.
        Bloquea (úsalo en un hilo); 'cancelar()' la corta."""
        id_ = id_ or self.modelo
        if id_ not in MODELOS:
            raise PintorError("Ese pincel no existe.")
        if not self.instalado(id_):
            raise PintorError(f"Aún no tengo el {MODELOS[id_]['nombre']}: descárgalo una vez ({MODELOS[id_]['mb']} MB) "
                              "en la pantalla «Pintor».")
        if not self.binarios():
            raise PintorError("Esta versión de Kira no trae el motor de pintar (solo va en el APK del móvil).")
        ancho, alto = FORMATOS.get(formato, FORMATOS["cuadrada"])
        semilla = int(semilla) if semilla is not None else random.randint(1, 2**31 - 2)
        os.makedirs(self.carpeta_imagenes, exist_ok=True)
        nombre = time.strftime("kira_%Y%m%d_%H%M%S") + f"_{semilla % 10000:04d}.png"
        salida = os.path.join(self.carpeta_imagenes, nombre)
        self._cancelar.clear()
        self.estado, self.progreso = "pintando", 0.0
        t0 = self._reloj()
        ultimo = ""
        try:
            for binario in self.binarios():
                prog = Progreso(MODELOS[id_]["pasos"])
                args = self.argumentos(binario, id_, prompt, negativo, ancho, alto, semilla, salida, vista)
                try:
                    codigo, ultimo = self._correr(args, prog, al_progreso, limite)
                except OSError as e:
                    self.binario_malo.add(binario)
                    ultimo = str(e)
                    continue
                if self._cancelar.is_set():
                    raise PintorError("Cancelado.")
                if codigo == 0 and os.path.isfile(salida) and os.path.getsize(salida) > 64:
                    if al_progreso:
                        al_progreso(1.0, "¡Lista!")
                    return {"ruta": salida, "segundos": round(self._reloj() - t0, 1), "semilla": semilla,
                            "modelo": id_}
                if codigo in (-4, 132, -11, 139) and binario.endswith("_dp.so"):   # instrucción que este móvil no tiene
                    self.binario_malo.add(binario)
                    continue
                break
            if self._reloj() - t0 >= limite:
                raise PintorError(f"Tardaba demasiado (más de {limite // 60} min): prueba el pincel rápido.")
            pista = ""
            if re.search(r"out of memory|failed to allocate|cannot allocate|std::bad_alloc", ultimo, re.I):
                pista = " Parece que faltó memoria: cierra otras apps o usa el pincel rápido."
            elif re.search(r"unknown format|init model loader from file failed|get sd version", ultimo, re.I):
                pista = " El archivo del pincel parece dañado: bórralo y descárgalo otra vez."
            lineas = [x for x in re.split(r"[\r\n]", ultimo) if x.strip()]
            errores = [x for x in lineas if "[ERROR" in x]
            linea = re.sub(r"^\[\w+\s*\]\s*[\w.]+:\d+\s*-\s*", "", (errores or lineas or ["sin detalle"])[0])
            raise PintorError(f"El motor no pudo pintar ({linea[-160:]}).{pista}")
        finally:
            self.estado = "listo"

    def ampliar(self, ruta, al_progreso=None, limite=1200):
        """Amplía una imagen ×4 con Real-ESRGAN. Devuelve la ruta nueva. Lento en el móvil."""
        if not self.ampliador_instalado():
            raise PintorError(f"Falta el {AMPLIADOR['nombre']} ({AMPLIADOR['mb']} MB): descárgalo en «Pintor».")
        if not self.binarios():
            raise PintorError("Esta versión de Kira no trae el motor de pintar.")
        salida = re.sub(r"\.png$", "", ruta) + "_x4.png"
        self._cancelar.clear()
        self.estado = "ampliando"
        try:
            for binario in self.binarios():
                prog = Progreso(1)
                prog.fase = "ampliar"
                args = [binario, "-M", "upscale", "-i", ruta, "--upscale-model", self.ruta_ampliador(), "-o", salida,
                        "-t", str(self.hilos)]
                try:
                    codigo, ultimo = self._correr(args, prog, al_progreso, limite)
                except OSError as e:
                    self.binario_malo.add(binario)
                    continue
                if self._cancelar.is_set():
                    raise PintorError("Cancelado.")
                if codigo == 0 and os.path.isfile(salida):
                    return salida
                if codigo in (-4, 132) and binario.endswith("_dp.so"):
                    self.binario_malo.add(binario)
                    continue
                break
            raise PintorError("No se pudo ampliar la imagen (¿falta memoria?).")
        finally:
            self.estado = "listo"

    # ---------- tus imágenes ----------
    def imagenes(self, n=60):
        try:
            nombres = [x for x in os.listdir(self.carpeta_imagenes) if x.lower().endswith(".png")]
        except OSError:
            return []
        rutas = [os.path.join(self.carpeta_imagenes, x) for x in nombres]
        return sorted(rutas, key=os.path.getmtime, reverse=True)[:n]

    def borrar_imagen(self, ruta):
        r = os.path.realpath(ruta)
        if os.path.dirname(r) != os.path.realpath(self.carpeta_imagenes):
            raise PintorError("Solo borro imágenes pintadas por Kira.")
        if os.path.isfile(r):
            os.remove(r)

    def estado_texto(self):
        partes = [f"Pincel elegido: {MODELOS[self.modelo]['nombre']}."]
        for k, m in MODELOS.items():
            falta = "sin descargar (%d MB)" % m["mb"]
            partes.append(f"- {m['nombre']}: " + ("descargado" if self.instalado(k) else falta))
        partes.append(f"- {AMPLIADOR['nombre']}: " + ("descargado" if self.ampliador_instalado()
                                                       else f"sin descargar ({AMPLIADOR['mb']} MB, opcional)"))
        partes.append("Motor: " + ("incluido" if self.tiene_motor() else "no incluido en esta versión (solo en el APK)"))
        partes.append(f"Imágenes pintadas: {len(self.imagenes(1000))}.")
        return "\n".join(partes)


def guardar_en_galeria(ruta):
    """Copia la imagen a la galería del móvil (Imágenes/Kira). (ok, mensaje). Llamar desde el hilo principal."""
    try:
        from jnius import autoclass
    except Exception:
        return False, "La galería solo existe en el móvil. La imagen sigue guardada dentro de Kira."
    try:
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        r = autoclass("org.kira.servicio.GaleriaKira").guardar(act, ruta, os.path.basename(ruta))
    except Exception as e:
        return False, f"No pude guardarla en la galería ({e}). Sigue guardada dentro de Kira."
    if r:
        return True, "Guardada en tu galería (Imágenes › Kira)."
    return False, "Android no me dejó guardarla en la galería. Sigue guardada dentro de Kira."
