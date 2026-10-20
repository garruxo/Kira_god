# -*- coding: utf-8 -*-
"""
diseno_kira.py - Lógica PURA (sin Kivy) de la Sala de Diseño: mediateca, páginas web, maquetas de app y videoclips.

Qué hace (de verdad):
  - MEDIATECA: lista tus vídeos y tu música (los del móvil que le indiques, los creados y los "en desarrollo").
  - PÁGINA WEB: genera un .html de una sola página (HTML+CSS, sin JavaScript) a partir de una descripción.
        Sin clave de API usa plantillas locales; con clave, la IA propone TEXTOS y COLORES en JSON y la plantilla
        los pinta (la IA nunca escribe el HTML, así que el resultado no puede traer scripts).
  - MAQUETA DE APP: genera pantallas "wireframe" (rectángulos) de 1 a 3 pantallas de una aplicación.
  - VIDEOCLIP: genera un GUION (escenas con duración, plano y texto) y un "vídeo" de storyboard: una secuencia de
        escenas dibujadas por código (escena_kira) que se reproduce en el cine. Es un storyboard animado, no un
        videoclip con imagen real ni edición profesional.
Qué NO hace: no edita vídeo real, no genera imágenes de IA, no compone música.
"""
import html
import json
import os
import re
import sys
import threading
import unicodedata

import escena_kira as ek

EXT_VIDEO = (".mp4", ".mkv", ".webm", ".3gp", ".mov", ".avi", ".m4v")
EXT_AUDIO = (".mp3", ".ogg", ".wav", ".m4a", ".flac", ".aac", ".opus")
ESTADOS = ("personal", "creado", "desarrollo")
TIPOS = ("video", "audio", "clip")
MAX_ITEMS, MAX_ESCANEO = 500, 300


def _norm(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _limpio(t, n):
    return re.sub(r"[\x00-\x1f\x7f]", " ", " ".join(str(t).split()))[:n]


def _leer_json(ruta, defecto):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, type(defecto)) else defecto
    except (OSError, ValueError):
        return defecto


def _guardar_json(ruta, datos):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


# =====================================================================================
#  MEDIATECA
# =====================================================================================
def tipo_por_extension(ruta):
    e = os.path.splitext(str(ruta))[1].lower()
    return "video" if e in EXT_VIDEO else "audio" if e in EXT_AUDIO else None


def carpetas_medios():
    """Carpetas donde buscar medios por defecto (Android o PC)."""
    if "ANDROID_ARGUMENT" in os.environ or os.path.isdir("/storage/emulated/0"):
        base = "/storage/emulated/0"
        return [os.path.join(base, d) for d in ("Movies", "DCIM", "Music", "Download", "Recordings")]
    home = os.path.expanduser("~")
    return [os.path.join(home, d) for d in ("Videos", "Music", "Downloads")]


def pedir_permisos_medios():
    """En Android pide permiso de lectura de medios; en otros sitios no hace nada. Devuelve True si lo ha pedido."""
    try:
        from android.permissions import Permission, request_permissions  # type: ignore
        nombres = [n for n in ("READ_MEDIA_VIDEO", "READ_MEDIA_AUDIO", "READ_EXTERNAL_STORAGE") if hasattr(Permission, n)]
        request_permissions([getattr(Permission, n) for n in nombres])
        return True
    except Exception:
        return False


class Mediateca:
    """Lista de medios: {id, tipo(video|audio|clip), titulo, ruta, estado(personal|creado|desarrollo)}."""

    def __init__(self, ruta):
        self.ruta, self._lock = ruta, threading.Lock()
        self._mtime = None
        self.items = []
        self._recargar()

    def _recargar(self, forzar=True):
        """Lee del disco si el archivo cambió (otra pantalla puede haber añadido medios). Llamar con el candado."""
        try:
            st = os.stat(self.ruta)
            m = (st.st_mtime_ns, st.st_size)
        except OSError:
            m = None
        if forzar or m != self._mtime:
            self.items = [i for i in _leer_json(self.ruta, []) if isinstance(i, dict) and {"id", "tipo", "titulo", "ruta"} <= set(i)]
            self._mtime = m

    def _guardar(self):
        _guardar_json(self.ruta, self.items)
        try:
            st = os.stat(self.ruta)
            self._mtime = (st.st_mtime_ns, st.st_size)
        except OSError:
            self._mtime = None

    def listar(self, tipo=None, estado=None):
        with self._lock:
            self._recargar(forzar=False)
            return [dict(i) for i in reversed(self.items)
                    if (tipo is None or i["tipo"] == tipo) and (estado is None or i.get("estado") == estado)]

    def anadir(self, titulo, ruta, tipo=None, estado="personal"):
        """(ok, mensaje, id). El archivo debe existir (salvo clips, que son archivos creados por Kira)."""
        ruta = str(ruta)
        tipo = tipo or tipo_por_extension(ruta)
        if tipo not in TIPOS:
            return False, "Tipo de archivo no reconocido (vídeo o audio).", None
        if estado not in ESTADOS:
            estado = "personal"
        if not os.path.isfile(ruta):
            return False, "Ese archivo no existe.", None
        titulo = _limpio(titulo, 80) or os.path.splitext(os.path.basename(ruta))[0][:80]
        with self._lock:
            self._recargar()
            for i in self.items:
                if i["ruta"] == ruta:
                    return False, "Ya está en la mediateca.", i["id"]
            if len(self.items) >= MAX_ITEMS:
                return False, f"Hay {MAX_ITEMS} elementos: borra alguno antes.", None
            nuevo = max((i["id"] for i in self.items), default=0) + 1
            self.items.append({"id": nuevo, "tipo": tipo, "titulo": titulo, "ruta": ruta, "estado": estado})
            self._guardar()
        return True, "Añadido a la mediateca.", nuevo

    def cambiar_estado(self, id_, estado):
        if estado not in ESTADOS:
            return False
        with self._lock:
            self._recargar()
            for i in self.items:
                if i["id"] == id_:
                    i["estado"] = estado
                    self._guardar()
                    return True
        return False

    def borrar(self, id_):
        """Quita de la lista. NO borra el archivo del dispositivo."""
        with self._lock:
            self._recargar()
            antes = len(self.items)
            self.items = [i for i in self.items if i["id"] != id_]
            if len(self.items) != antes:
                self._guardar()
                return True
        return False

    def escanear(self, carpetas=None, maximo=MAX_ESCANEO, profundidad=2):
        """Busca vídeos y música en las carpetas (sin entrar en carpetas ocultas) y los añade. Devuelve (nuevos, vistos)."""
        carpetas = carpetas or carpetas_medios()
        nuevos = vistos = 0
        for base in carpetas:
            if not os.path.isdir(base):
                continue
            nivel0 = base.rstrip(os.sep).count(os.sep)
            for raiz, dirs, archivos in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                if raiz.count(os.sep) - nivel0 >= profundidad:
                    dirs[:] = []
                for a in sorted(archivos):
                    if a.startswith(".") or tipo_por_extension(a) is None:
                        continue
                    vistos += 1
                    if vistos > maximo:
                        return nuevos, vistos - 1
                    ok, _m, _i = self.anadir("", os.path.join(raiz, a))
                    nuevos += 1 if ok else 0
        return nuevos, vistos


# =====================================================================================
#  UTILIDADES PARA LA IA (JSON)
# =====================================================================================
def extraer_json(texto):
    """Primer objeto JSON de un texto (quita ``` si los hay). None si no hay uno válido."""
    t = str(texto)
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _color_hex(c, defecto):
    return c if isinstance(c, str) and _HEX.match(c) else defecto


def _hex_a_rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


# =====================================================================================
#  PÁGINAS WEB
# =====================================================================================
PALETAS_WEB = {
    "playa": {"fondo": "#fff8e7", "texto": "#23424a", "acento": "#1e90b4", "suave": "#bfe6ee"},
    "oscuro": {"fondo": "#0d1117", "texto": "#d7e3ea", "acento": "#2ee6a6", "suave": "#16202b"},
    "naturaleza": {"fondo": "#f3f8ee", "texto": "#25402a", "acento": "#3a9d4f", "suave": "#d6ebd0"},
    "calido": {"fondo": "#fff5ee", "texto": "#4a2c20", "acento": "#e8683a", "suave": "#fbd9c6"},
    "claro": {"fondo": "#ffffff", "texto": "#1f2933", "acento": "#3b6fe0", "suave": "#e6edfb"},
}
_CLAVES_PALETA = (("playa", ("playa", "mar", "verano", "surf", "costa")),
                  ("oscuro", ("oscuro", "hacker", "neon", "noche", "tecnolog", "gamer", "negro")),
                  ("naturaleza", ("naturaleza", "verde", "bosque", "jardin", "eco", "planta")),
                  ("calido", ("calido", "restaurante", "cafe", "panaderia", "cocina", "atardecer", "pizz")))
SECCIONES_POR_TIPO = {
    "negocio": ("restaurante", "tienda", "negocio", "cafe", "panaderia", "servicios", "empresa", "pizz"),
    "portfolio": ("portfolio", "portafolio", "personal", "cv", "curriculum", "fotograf", "artista", "disenador"),
    "evento": ("evento", "boda", "fiesta", "concierto", "festival", "cumple"),
}


def elegir_paleta(texto):
    n = _norm(texto)
    return next((p for p, claves in _CLAVES_PALETA if any(c in n for c in claves)), "claro")


def spec_pagina_local(descripcion):
    """Contenido de la página a partir de la descripción, sin IA (plantilla)."""
    d = _limpio(descripcion, 300)
    n = _norm(d)
    tipo = next((t for t, claves in SECCIONES_POR_TIPO.items() if any(c in n for c in claves)), "landing")
    titulo = d.split(".")[0][:60].strip().capitalize() or "Mi página"
    textos = {
        "negocio": [("Quiénes somos", f"{titulo}. Cuéntale a tus clientes quién eres, qué haces y qué te hace especial."),
                    ("Qué ofrecemos", "Lista aquí tus productos o servicios principales con una frase para cada uno."),
                    ("Dónde estamos", "Añade la dirección, el horario y una forma de contacto.")],
        "portfolio": [("Sobre mí", f"{titulo}. Presenta tu trabajo y tu forma de entender el oficio en pocas frases."),
                      ("Proyectos", "Elige tus 3 mejores trabajos y descríbelos en una frase cada uno."),
                      ("Contacto", "Dile a la gente cómo escribirte.")],
        "evento": [("El evento", f"{titulo}. Resume de qué trata el evento."),
                   ("Cuándo y dónde", "Fecha, hora y lugar. Añade cómo llegar."),
                   ("Cómo participar", "Explica cómo confirmar asistencia o comprar entradas.")],
        "landing": [("Qué es", f"{titulo}. Explica en dos frases el problema que resuelve."),
                    ("Por qué te gustará", "Tres ventajas claras, una por línea."),
                    ("Empieza hoy", "Una llamada a la acción sencilla y directa.")],
    }[tipo]
    return normalizar_spec({"titulo": titulo, "subtitulo": "Hecha con Kira",
                            "secciones": [{"titulo": t, "texto": x} for t, x in textos],
                            "paleta": elegir_paleta(d), "boton": "Saber más"})


def normalizar_spec(d):
    """Valida y recorta lo que venga (de la IA o de la plantilla). Lanza ValueError si no hay contenido útil."""
    if not isinstance(d, dict):
        raise ValueError("Contenido de página no válido.")
    titulo = _limpio(d.get("titulo", ""), 80)
    if not titulo:
        raise ValueError("La página no tiene título.")
    secs = []
    for s in (d.get("secciones") or [])[:6]:
        if isinstance(s, dict) and _limpio(s.get("titulo", ""), 60):
            secs.append({"titulo": _limpio(s["titulo"], 60), "texto": _limpio(s.get("texto", ""), 500)})
    if not secs:
        raise ValueError("La página no tiene secciones.")
    pal = d.get("paleta")
    if isinstance(pal, str):
        p = PALETAS_WEB.get(pal, PALETAS_WEB["claro"])
    elif isinstance(pal, dict):
        base = PALETAS_WEB["claro"]
        p = {k: _color_hex(pal.get(k), base[k]) for k in base}
    else:
        p = PALETAS_WEB["claro"]
    return {"titulo": titulo, "subtitulo": _limpio(d.get("subtitulo", ""), 140), "secciones": secs,
            "boton": _limpio(d.get("boton", ""), 30), "paleta": dict(p)}


def html_desde_spec(spec):
    """Documento HTML completo (sin JavaScript, sin recursos externos). Todo el texto va escapado."""
    spec = normalizar_spec(spec)
    p = spec["paleta"]
    e = html.escape
    secciones = "\n".join(f'    <section><h2>{e(s["titulo"])}</h2><p>{e(s["texto"])}</p></section>' for s in spec["secciones"])
    boton = f'<a class="boton" href="#contenido">{e(spec["boton"])}</a>' if spec["boton"] else ""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(spec["titulo"])}</title>
<style>
  *{{box-sizing:border-box}} body{{margin:0;font-family:system-ui,sans-serif;background:{p["fondo"]};color:{p["texto"]};line-height:1.55}}
  header{{background:{p["acento"]};color:#fff;padding:3rem 1.2rem;text-align:center}}
  header h1{{margin:0 0 .4rem;font-size:2rem}} header p{{margin:0 0 1.2rem;opacity:.9}}
  .boton{{display:inline-block;background:#fff;color:{p["acento"]};padding:.7rem 1.4rem;border-radius:999px;text-decoration:none;font-weight:600}}
  main{{max-width:720px;margin:0 auto;padding:1.2rem}} section{{background:{p["suave"]};border-radius:14px;padding:1.1rem 1.3rem;margin:1rem 0}}
  h2{{margin:.1rem 0 .4rem;color:{p["acento"]}}} footer{{text-align:center;padding:1.5rem;opacity:.7;font-size:.9rem}}
</style>
</head>
<body>
  <header><h1>{e(spec["titulo"])}</h1><p>{e(spec["subtitulo"])}</p>{boton}</header>
  <main id="contenido">
{secciones}
  </main>
  <footer>Creada con Kira</footer>
</body>
</html>
"""


# =====================================================================================
#  MAQUETAS DE APP
# =====================================================================================
ELEMENTOS = ("barra", "texto", "boton", "lista", "imagen", "campo")


def spec_app_local(descripcion):
    d = _limpio(descripcion, 200)
    n = _norm(d)
    nombre = (d.split(".")[0][:40].strip().capitalize()) or "Mi app"
    if any(k in n for k in ("tienda", "compra", "catalogo", "producto")):
        pant = [("Inicio", ["barra", "imagen", "lista", "boton"]), ("Producto", ["barra", "imagen", "texto", "boton"]),
                ("Carrito", ["barra", "lista", "texto", "boton"])]
    elif any(k in n for k in ("nota", "tarea", "lista", "agenda", "recordator")):
        pant = [("Mis elementos", ["barra", "lista", "boton"]), ("Nuevo", ["barra", "campo", "campo", "boton"]),
                ("Ajustes", ["barra", "texto", "texto", "boton"])]
    elif any(k in n for k in ("musica", "reproductor", "video", "radio", "podcast")):
        pant = [("Biblioteca", ["barra", "lista", "lista"]), ("Reproduciendo", ["barra", "imagen", "texto", "boton"]),
                ("Búsqueda", ["barra", "campo", "lista"])]
    else:
        pant = [("Inicio", ["barra", "imagen", "texto", "boton"]), ("Detalle", ["barra", "texto", "lista", "boton"]),
                ("Perfil", ["barra", "imagen", "campo", "boton"])]
    return normalizar_app({"nombre": nombre, "color": "#3b6fe0",
                           "pantallas": [{"titulo": t, "elementos": e} for t, e in pant]})


def normalizar_app(d):
    if not isinstance(d, dict):
        raise ValueError("Maqueta no válida.")
    nombre = _limpio(d.get("nombre", ""), 40)
    if not nombre:
        raise ValueError("La app no tiene nombre.")
    pantallas = []
    for p in (d.get("pantallas") or [])[:3]:
        if not isinstance(p, dict):
            continue
        els = [str(x) for x in (p.get("elementos") or []) if str(x) in ELEMENTOS][:8]
        if els:
            pantallas.append({"titulo": _limpio(p.get("titulo", "Pantalla"), 40) or "Pantalla", "elementos": els})
    if not pantallas:
        raise ValueError("La app no tiene pantallas.")
    return {"nombre": nombre, "color": _color_hex(d.get("color"), "#3b6fe0"), "pantallas": pantallas}


def maqueta_formas(app):
    """Formas para escena_kira (rect/circ) con las pantallas de la app dibujadas como wireframes."""
    app = normalizar_app(app)
    acento = _hex_a_rgb(app["color"])
    formas = [("rect", 0, 0, ek.W, ek.H, (0.93, 0.94, 0.96))]
    n = len(app["pantallas"])
    pw, ph = 0.27, 0.68
    hueco = 0.04
    x0 = (1.0 - (n * pw + (n - 1) * hueco)) / 2
    for k, pantalla in enumerate(app["pantallas"]):
        x, y = x0 + k * (pw + hueco), 0.035
        formas.append(("rect", x - 0.008, y - 0.008, pw + 0.016, ph + 0.016, (0.10, 0.11, 0.14)))
        formas.append(("rect", x, y, pw, ph, (1, 1, 1)))
        cur = y + ph - 0.01
        for el in pantalla["elementos"]:
            if el == "barra":
                formas.append(("rect", x, cur - 0.05, pw, 0.05, acento))
                formas.append(("rect", x + 0.012, cur - 0.03, pw * 0.4, 0.01, (1, 1, 1)))
                cur -= 0.06
            elif el == "texto":
                for j, f in enumerate((0.9, 0.75, 0.55)):
                    formas.append(("rect", x + 0.012, cur - 0.02 - j * 0.02, (pw - 0.024) * f, 0.009, (0.72, 0.74, 0.78)))
                cur -= 0.08
            elif el == "boton":
                formas.append(("rect", x + 0.02, cur - 0.045, pw - 0.04, 0.04, acento))
                cur -= 0.06
            elif el == "lista":
                for j in range(3):
                    yy = cur - 0.045 - j * 0.05
                    formas.append(("circ", x + 0.03, yy + 0.015, 0.014, (0.72, 0.74, 0.78)))
                    formas.append(("rect", x + 0.055, yy + 0.012, (pw - 0.07) * 0.8, 0.009, (0.55, 0.57, 0.62)))
                    formas.append(("rect", x + 0.055, yy - 0.002, (pw - 0.07) * 0.5, 0.007, (0.78, 0.8, 0.84)))
                cur -= 0.17
            elif el == "imagen":
                formas.append(("rect", x + 0.012, cur - 0.12, pw - 0.024, 0.11, (0.82, 0.85, 0.9)))
                formas.append(("circ", x + pw * 0.5, cur - 0.065, 0.025, (0.65, 0.7, 0.8)))
                cur -= 0.135
            elif el == "campo":
                formas.append(("rect", x + 0.02, cur - 0.04, pw - 0.04, 0.032, (0.8, 0.82, 0.86)))
                formas.append(("rect", x + 0.022, cur - 0.038, pw - 0.044, 0.028, (1, 1, 1)))
                cur -= 0.055
            if cur < y + 0.02:
                break
    return formas


def texto_maqueta(app):
    app = normalizar_app(app)
    return "\n".join([f"App: {app['nombre']}"] + [f"  Pantalla {i + 1}: {p['titulo']}  ({', '.join(p['elementos'])})"
                                                   for i, p in enumerate(app["pantallas"])])


# =====================================================================================
#  VIDEOCLIP (guion + storyboard animado)
# =====================================================================================
TEMAS_CLIP = ("playa", "montaña", "bosque", "desierto", "ciudad", "lago", "espacio")
PLANOS = ("plano general", "plano medio", "plano detalle", "travelling lento", "plano cenital", "fundido")
MOMENTOS_CLIP = ("amanecer", "día", "atardecer", "noche")


def _escena_clip(tema_texto, momento):
    """Texto de petición que entiende escena_kira; si no conoce el tema usa el espacio (que siempre existe)."""
    n = _norm(tema_texto)
    tema = next((t for t, claves in ek.TEMAS.items() if any(re.search(r"\b" + c, n) for c in claves)), None) or "espacio"
    return f"dibuja {ek.NOMBRES[tema]} de {_norm(momento) if momento else 'dia'}"


def guion_local(descripcion, escenas=6, segundos=4.0):
    """Guion sencillo: progresión de momentos del día sobre el tema pedido. Sin IA."""
    d = _limpio(descripcion, 200)
    n = _norm(d)
    tema = next((t for t, claves in ek.TEMAS.items() if any(re.search(r"\b" + c, n) for c in claves)), "playa")
    orden = ("amanecer", "dia", "dia", "atardecer", "atardecer", "noche")
    esc = []
    for i in range(max(2, min(int(escenas), 10))):
        mom = orden[min(i * len(orden) // max(2, int(escenas)), len(orden) - 1)]
        esc.append({"titulo": f"Escena {i + 1}", "plano": PLANOS[i % len(PLANOS)], "texto": f"{ek.NOMBRES[tema].capitalize()} {'de noche' if mom == 'noche' else 'de día' if mom == 'dia' else 'al ' + mom}.",
                    "escena": f"dibuja {ek.NOMBRES[tema]} de {mom}", "dur": float(segundos)})
    return normalizar_guion({"titulo": d.split(".")[0][:60].capitalize() or "Mi videoclip", "cancion": "", "escenas": esc})


def normalizar_guion(d):
    if not isinstance(d, dict):
        raise ValueError("Guion no válido.")
    titulo = _limpio(d.get("titulo", ""), 60)
    if not titulo:
        raise ValueError("El videoclip no tiene título.")
    escenas = []
    for e in (d.get("escenas") or [])[:12]:
        if not isinstance(e, dict):
            continue
        try:
            dur = float(e.get("dur", 4))
        except (TypeError, ValueError):
            dur = 4.0
        dur = max(1.5, min(dur, 12.0))
        pedido = _limpio(e.get("escena", "") or e.get("texto", ""), 120)
        if not pedido.lower().startswith(("dibuja", "pinta")):
            pedido = _escena_clip(pedido, e.get("momento", ""))
        interp = ek.interpretar(pedido)
        if not interp or not interp.get("tema"):
            pedido = "dibuja el espacio de noche"
        escenas.append({"titulo": _limpio(e.get("titulo", ""), 40) or f"Escena {len(escenas) + 1}",
                        "plano": _limpio(e.get("plano", ""), 40), "texto": _limpio(e.get("texto", ""), 160),
                        "escena": pedido, "dur": dur})
    if len(escenas) < 2:
        raise ValueError("El videoclip necesita al menos 2 escenas.")
    return {"titulo": titulo, "cancion": _limpio(d.get("cancion", ""), 80), "escenas": escenas}


def duracion_total(guion):
    return sum(e["dur"] for e in guion["escenas"])


def fotograma(guion, t):
    """(indice_escena, progreso 0..1 dentro de la escena, terminado) para el instante t (segundos)."""
    acumulado = 0.0
    for i, e in enumerate(guion["escenas"]):
        if t < acumulado + e["dur"]:
            return i, (t - acumulado) / e["dur"], False
        acumulado += e["dur"]
    return len(guion["escenas"]) - 1, 1.0, True


def formas_escena(escena, variante=0):
    """Formas de una escena del guion (usa escena_kira). Nunca lanza: si falla, devuelve el espacio."""
    try:
        return ek.construir(ek.interpretar(escena["escena"], variante))
    except Exception:
        return ek.construir(ek.interpretar("dibuja el espacio de noche"))


class ReproductorClip:
    """Reloj del storyboard (puro): play/pausa/parar y 'tick(dt)'. Devuelve (indice, cambio_de_escena, terminado)."""

    def __init__(self, guion):
        self.guion = normalizar_guion(guion)
        self.t, self.reproduciendo, self._ultimo = 0.0, False, -1

    def play(self):
        if fotograma(self.guion, self.t)[2]:
            self.t, self._ultimo = 0.0, -1               # si había terminado, empieza de nuevo
        self.reproduciendo = True

    def pausa(self):
        self.reproduciendo = False

    def parar(self):
        self.reproduciendo, self.t, self._ultimo = False, 0.0, -1

    def tick(self, dt):
        if self.reproduciendo:
            self.t += max(0.0, min(float(dt), 0.5))
        i, _p, fin = fotograma(self.guion, self.t)
        cambio = i != self._ultimo
        self._ultimo = i
        if fin and self.reproduciendo:
            self.reproduciendo = False
        return i, cambio, fin

    def progreso(self):
        return min(1.0, self.t / (duracion_total(self.guion) or 1.0))


def texto_guion(guion):
    guion = normalizar_guion(guion)
    l = [f"VIDEOCLIP: {guion['titulo']}" + (f"  (música: {guion['cancion']})" if guion["cancion"] else ""),
         f"Duración: {duracion_total(guion):.0f} s, {len(guion['escenas'])} escenas", ""]
    t = 0.0
    for e in guion["escenas"]:
        l.append(f"{int(t // 60):02d}:{int(t % 60):02d}  {e['titulo']} - {e['plano']}\n        {e['texto']}")
        t += e["dur"]
    return "\n".join(l)


# =====================================================================================
#  PROYECTOS (archivos creados)
# =====================================================================================
def _nombre_archivo(nombre, ext, n=1):
    """Nombre de archivo seguro (solo a-z, 0-9 y _); el sufijo _n se añade DESPUÉS de recortar."""
    base = re.sub(r"[^a-z0-9]+", "_", _norm(nombre)).strip("_")[:40] or "proyecto"
    return (base if n <= 1 else f"{base}_{n}") + ext


class Proyectos:
    """Guarda lo creado en <datos>/diseno/ (webs .html, maquetas .json, videoclips .clip.json)."""

    def __init__(self, dir_datos):
        self.dir = os.path.join(dir_datos, "diseno")

    def _escribir(self, nombre, ext, contenido):
        os.makedirs(self.dir, exist_ok=True)
        n = 1
        ruta = os.path.join(self.dir, _nombre_archivo(nombre, ext))
        while os.path.exists(ruta):
            n += 1
            ruta = os.path.join(self.dir, _nombre_archivo(nombre, ext, n))
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        return ruta

    def ruta_video(self, nombre):
        """Ruta libre para un MP4 en <datos>/diseno/videos/ (no crea el archivo)."""
        carpeta = os.path.join(self.dir, "videos")
        os.makedirs(carpeta, exist_ok=True)
        n = 1
        ruta = os.path.join(carpeta, _nombre_archivo(nombre, ".mp4"))
        while os.path.exists(ruta):
            n += 1
            ruta = os.path.join(carpeta, _nombre_archivo(nombre, ".mp4", n))
        return ruta

    def guardar_web(self, spec):
        return self._escribir(spec["titulo"], ".html", html_desde_spec(spec))

    def guardar_app(self, app):
        app = normalizar_app(app)
        return self._escribir(app["nombre"], ".app.json", json.dumps(app, ensure_ascii=False, indent=1))

    def guardar_clip(self, guion):
        guion = normalizar_guion(guion)
        return self._escribir(guion["titulo"], ".clip.json", json.dumps(guion, ensure_ascii=False, indent=1))

    def exportar(self, ruta, destinos=None):
        """Copia un archivo creado a Descargas (o a otra carpeta). Devuelve (ok, mensaje). En Android reciente el
        sistema puede impedirlo; en ese caso lo dice."""
        import shutil
        destinos = destinos or [os.path.join(b, "Download") for b in ("/storage/emulated/0",)] + \
            [os.path.join(os.path.expanduser("~"), "Downloads")]
        for d in destinos:
            if os.path.isdir(d):
                try:
                    dest = os.path.join(d, os.path.basename(ruta))
                    shutil.copyfile(ruta, dest)
                    return True, f"Copiado a {dest}"
                except OSError:
                    continue
        return False, "No se pudo copiar a Descargas (el sistema lo impide). El archivo sigue guardado dentro de Kira."

    @staticmethod
    def leer_clip(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return normalizar_guion(json.load(f))


# =====================================================================================
#  PETICIÓN A LA IA (opcional): el núcleo la llama; aquí solo se arman prompt y se interpreta
# =====================================================================================
SISTEMAS = {
    "web": ("Eres diseñador web. Responde SOLO con un objeto JSON: {\"titulo\":str,\"subtitulo\":str,\"boton\":str,"
            "\"paleta\":{\"fondo\":\"#rrggbb\",\"texto\":\"#rrggbb\",\"acento\":\"#rrggbb\",\"suave\":\"#rrggbb\"},"
            "\"secciones\":[{\"titulo\":str,\"texto\":str}]} con 3 a 5 secciones, textos en español, cortos, sin HTML."),
    "app": ("Eres diseñador de apps. Responde SOLO con un objeto JSON: {\"nombre\":str,\"color\":\"#rrggbb\","
            "\"pantallas\":[{\"titulo\":str,\"elementos\":[...]}]} con 2 o 3 pantallas. Cada elemento es una de estas "
            "palabras: barra, texto, boton, lista, imagen, campo."),
    "clip": ("Eres guionista de videoclips. Responde SOLO con un objeto JSON: {\"titulo\":str,\"cancion\":str,"
             "\"escenas\":[{\"titulo\":str,\"plano\":str,\"texto\":str,\"dur\":numero,\"escena\":\"dibuja <tema> de "
             "<momento>\"}]} con 5 a 8 escenas. Los temas posibles son: playa, montañas, bosque, desierto, ciudad, lago, "
             "espacio. Los momentos: amanecer, día, atardecer, noche. dur en segundos (3 a 6)."),
}
NORMALIZADORES = {"web": normalizar_spec, "app": normalizar_app, "clip": normalizar_guion}
LOCALES = {"web": spec_pagina_local, "app": spec_app_local, "clip": guion_local}


_PIDE_DISENO = re.compile(
    r"^(?:por\s+favor\s+)?(?P<verbo>dis[eé][ñn]a(?:me)?|hazme|haz|cr[eé]a(?:me)?|prep[aá]rame|monta(?:me)?)\s+"
    r"(?:(?:una?|el|la|otra?)\s+)?(?P<que>p[aá]gina(?:\s+web)?|web|landing|maqueta(?:\s+de\s+(?:una?\s+)?app)?|"
    r"app|aplicaci[oó]n|v[ií]deo\s*clip|videoclip|clip|storyboard)\b\s*(?P<resto>.*)$", re.I | re.S)


def pedido_diseno(texto):
    """«Kira, diséñame una web para mi bar», «hazme una maqueta de app de tareas», «crea un videoclip de la playa»
    -> ('web' | 'app' | 'clip', descripción). Si no es un pedido de diseño, None. «diséñame …» sin decir qué -> web."""
    t = " ".join(str(texto or "").split()).strip(" .!¡?¿")
    m = _PIDE_DISENO.match(t)
    if m:
        que = _norm(m.group("que"))
        tipo = "web" if que.startswith(("pagina", "web", "landing")) else (
            "clip" if any(x in que for x in ("clip", "storyboard")) else "app")
        resto = m.group("resto").strip(" ,.:")
        if len(resto) < 3:
            return None
        return tipo, (m.group("que") + " " + resto)[:300]
    m = re.match(r"^dis[eé][ñn]a(?:me)?\s+(.{3,})$", t, re.I)
    if m:
        return "web", m.group(1)[:300]
    return None


def interpretar_respuesta(tipo, texto):
    """Respuesta de la IA -> contenido validado. Lanza ValueError si no sirve."""
    d = extraer_json(texto)
    if d is None:
        raise ValueError("La IA no devolvió un JSON válido.")
    return NORMALIZADORES[tipo](d)
