# -*- coding: utf-8 -*-
"""
disenos_kira.py - v3.74: KiraOS le ENCARGA diseños a la Kira del móvil. VA EN EL APK; puro, sin red ni Kivy.

Lo pidió el dueño: «que KiraOS le pida un logo, icono, fondo de pantalla, salvapantallas, estilo o tema del sistema,
estilo de ventana… que los haga Kira app, y cuando los tiene se los manda; y KiraOS me los enseña antes de aplicar:
si le doy el visto bueno, lo guarda y lo aplica».

Cómo va:
  1. En KiraOS: «pídele al móvil un icono de un escudo para el mapa» → `orden` + `pedir` lo apuntan (estado «pedido»).
  2. Al sincronizar, el encargo viaja al móvil (`para_movil`, con cursor: no se repite).
  3. El móvil lo guarda (`recibir`) y lo hace él solo (el núcleo del móvil: el PINTOR para las imágenes; para el tema y
     el estilo de ventana, colores y medidas, solo DATOS) → `hecho`.
  4. En la siguiente sincronía el resultado vuelve (`resultados_por_enviar`, 2 imágenes por viaje) y KiraOS lo guarda
     (`guardar_resultados`) como «listo»: ESPERA tu visto bueno. NADA se aplica solo.
  5. En KiraOS (Ajustes ▸ Diseños del móvil) lo ves y decides: Aplicar (dos toques), Rechazar o Pedir otro.

Seguridad: lo que viaja son imágenes PNG/JPEG de verdad (se mira la firma, tope 4 MB) y datos (colores #rrggbb y
números acotados). Ningún código, ningún HTML.
"""
import base64
import json
import os
import re
import time
import unicodedata
import uuid

TIPOS = ("icono", "logo", "fondo", "salvapantallas", "tema", "ventana")
IMAGEN = ("icono", "logo", "fondo", "salvapantallas")
NOMBRE_TIPO = {"icono": "icono", "logo": "logo", "fondo": "fondo de pantalla", "salvapantallas": "salvapantallas",
               "tema": "tema (colores) del sistema", "ventana": "estilo de las ventanas"}
ARCHIVO_KIRAOS = "encargos_diseno.json"
ARCHIVO_MOVIL = "encargos_diseno_movil.json"
CARPETA_KIRAOS = "disenos"            # en KiraOS: las imágenes que llegan (esperan tu visto bueno)
MAX_IMG_BYTES = 4 * 1024 * 1024
MAX_IMG_VIAJE = 2
MAX_DESC = 200
MAX_ENCARGOS = 60
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
CLAVES_TEMA = ("fondo", "neon", "acento", "texto")
DESC_DEFECTO = {"icono": "un icono sencillo y bonito", "logo": "el logo de Kira, un orbe brillante",
                "fondo": "un fondo de pantalla futurista y tranquilo", "salvapantallas": "un paisaje nocturno tranquilo",
                "tema": "colores bonitos y que se lean bien", "ventana": "ventanas modernas y redondeadas"}


# ------------------------------------------------------------------ disco
def _leer(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _escribir(ruta, d):
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, ruta)


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return " ".join("".join(c for c in t if unicodedata.category(c) != "Mn").split())


def _txt(v, maximo=MAX_DESC):
    return re.sub(r"[\x00-\x1f\x7f<>]", "", str(v or "")).strip()[:maximo]


# ------------------------------------------------------------------ la ORDEN (en KiraOS)
_MOVIL = r"(?:al?\s+(?:la\s+)?(?:kira\s+(?:del?\s+)?movil|kira\s+app|app\s+de\s+kira|movil|telefono|app|kira\s+del\s+telefono))"
_PIDE = re.compile(r"^(?:kira[, ]+)?(?:pide(?:le)?|encarga(?:le)?|dile|pidele|encargale|manda(?:le)?|que)\b(?P<resto>.*)$")
_TIPO_PAL = [("ventana", r"(?:estilo|diseno|aspecto|forma)\s+de\s+(?:las?\s+|tus\s+)?ventanas?|ventanas?"),
             ("salvapantallas", r"salva\s*pantallas?|protector\s+de\s+pantalla"),
             ("fondo", r"fondos?(?:\s+de\s+(?:pantalla|escritorio))?|wallpaper"),
             ("logo", r"logo(?:tipo)?s?|emblemas?"),
             ("icono", r"iconos?"),
             ("tema", r"tema(?:\s+del\s+sistema)?|estilo(?:\s+del\s+sistema)?|paleta(?:\s+de\s+colores)?|colores")]
_VER = re.compile(r"^(?:kira[, ]+)?(?:ensename|muestrame|abre|ver|que)\s+(?:los\s+|tus\s+|mis\s+)?(?:diseno|disenos)"
                  r"(?:\s+(?:del?\s+movil|de\s+kira\s+app|que\s+(?:te\s+)?han\s+llegado|tienes|hay))?$"
                  r"|^(?:que\s+)?disenos\s+(?:tienes|hay|han\s+llegado)$|^(?:tus\s+|los\s+)?disenos(?:\s+del\s+movil)?$")


def orden(texto):
    """None, ("ver", None) o ("pedir", {tipo, descripcion, destino})."""
    t = _plano(texto).strip(" .!?¡¿")
    if not t:
        return None
    if _VER.match(t):
        return ("ver", None)
    m = _PIDE.match(t)
    if not m or not re.search(r"\b(?:movil|kira\s+app|telefono|app\s+de\s+kira)\b", t):
        return None
    tipo, mt = None, None
    for clave, pal in _TIPO_PAL:
        mt = re.search(r"\b(?:" + pal + r")\b", t)
        if mt:
            tipo = clave
            break
    if not tipo:
        return None
    resto = t[mt.end():]
    destino = ""
    md = re.search(r"\b(?:para|en)\s+(?:el\s+|la\s+|mi\s+)?(?:icono\s+(?:del?\s+|de\s+la\s+)?)?(?P<d>[a-z ]{2,30}?)$", resto)
    if tipo in ("icono", "logo") and md and not re.match(r"^(?:kiraos|el sistema|ti|mi|el portatil|portatil)$", md.group("d")):
        destino = md.group("d").strip()
        resto = resto[:md.start()]
    resto = re.sub(r"\b(?:para|en)\s+(?:kiraos|el\s+sistema|ti|el\s+portatil|el\s+escritorio|tu\s+escritorio)\b", " ", resto)
    desc = re.sub(r"^\s*(?:de|con|que\s+sea|que\s+tenga|tipo|estilo|en)\s+", "", resto).strip(" ,.:")
    desc = re.sub(r"^(?:un|una|el|la)\s+", "", desc) if len(desc.split()) > 1 else desc
    return ("pedir", {"tipo": tipo, "descripcion": _txt(desc) or DESC_DEFECTO[tipo], "destino": _txt(destino, 40)})


# ------------------------------------------------------------------ KiraOS: los ENCARGOS
def _ruta_k(dir_):
    return os.path.join(dir_, ARCHIVO_KIRAOS)


def encargos(dir_):
    return [e for e in _leer(_ruta_k(dir_)).get("encargos", []) if isinstance(e, dict) and e.get("id")]


def _guardar_encargos(dir_, lista):
    _escribir(_ruta_k(dir_), {"encargos": lista[-MAX_ENCARGOS:]})


def pedir(dir_, tipo, descripcion="", destino=""):
    if tipo not in TIPOS:
        raise ValueError("Ese tipo de diseño no lo conozco. Hay: " + ", ".join(TIPOS) + ".")
    e = {"id": uuid.uuid4().hex[:10], "tipo": tipo, "descripcion": _txt(descripcion) or DESC_DEFECTO[tipo],
         "destino": _txt(destino, 40), "estado": "pedido", "cuando": int(time.time())}
    _guardar_encargos(dir_, encargos(dir_) + [e])
    return e


def uno(dir_, ident):
    return next((e for e in encargos(dir_) if e["id"] == str(ident)), None)


def _cambiar(dir_, ident, **campos):
    lista = encargos(dir_)
    for e in lista:
        if e["id"] == str(ident):
            e.update(campos)
            _guardar_encargos(dir_, lista)
            return e
    return None


def marcar(dir_, ident, estado):
    return _cambiar(dir_, ident, estado=estado, cuando_estado=int(time.time()))


def otro(dir_, ident):
    """«Pedir otro»: el viejo queda rechazado y se pide otro igual (el móvil lo pinta de nuevo)."""
    e = uno(dir_, ident)
    if not e:
        return None
    if e.get("estado") != "aplicado":
        marcar(dir_, ident, "rechazado")
    return pedir(dir_, e["tipo"], e.get("descripcion", ""), e.get("destino", ""))


def listos(dir_):
    return [e for e in encargos(dir_) if e.get("estado") == "listo"]


def para_movil(dir_, entregados):
    """Los encargos que el móvil aún no tiene (por su cursor)."""
    ya = set(entregados or [])
    return [{k: e.get(k, "") for k in ("id", "tipo", "descripcion", "destino")}
            for e in encargos(dir_) if e.get("estado") in ("pedido", "entregado") and e["id"] not in ya]


def marcar_entregados(dir_, ids):
    ids = set(ids or [])
    if not ids:
        return
    lista = encargos(dir_)
    cambio = False
    for e in lista:
        if e["id"] in ids and e.get("estado") == "pedido":
            e["estado"] = "entregado"
            cambio = True
    if cambio:
        _guardar_encargos(dir_, lista)


def ruta_imagen(dir_, e):
    """La imagen que llegó para ese encargo (o '')."""
    nombre = os.path.basename(str((e or {}).get("archivo") or ""))
    if not nombre:
        return ""
    r = os.path.join(dir_, CARPETA_KIRAOS, nombre)
    return r if os.path.isfile(r) else ""


def _es_imagen(datos):
    return datos.startswith(b"\x89PNG") or datos.startswith(b"\xff\xd8")


def guardar_resultados(dir_, resultados):
    """KiraOS mete lo que el móvil hizo: queda «listo» (espera tu visto bueno). Devuelve cuántos."""
    n = 0
    for r in resultados or []:
        if not isinstance(r, dict):
            continue
        e = uno(dir_, r.get("id"))
        if not e or e.get("estado") not in ("pedido", "entregado") or r.get("tipo") != e["tipo"]:
            continue
        campos = {"estado": "listo", "cuando_estado": int(time.time()), "nota": _txt(r.get("nota"), 200)}
        if r.get("fallo"):
            campos.update(estado="fallido", nota=_txt(r.get("fallo"), 200))
        elif e["tipo"] in IMAGEN:
            try:
                datos = base64.b64decode(str(r.get("imagen") or ""), validate=True)
            except Exception:
                continue
            if not datos or len(datos) > MAX_IMG_BYTES or not _es_imagen(datos):
                continue
            nombre = e["id"] + (".png" if datos.startswith(b"\x89PNG") else ".jpg")
            carpeta = os.path.join(dir_, CARPETA_KIRAOS)
            os.makedirs(carpeta, exist_ok=True)
            ruta = os.path.join(carpeta, nombre)
            with open(ruta + ".tmp", "wb") as f:
                f.write(datos)
            os.chmod(ruta + ".tmp", 0o600)
            os.replace(ruta + ".tmp", ruta)
            campos["archivo"] = nombre
        elif e["tipo"] == "tema":
            col = colores_validos(r.get("colores"))
            if not col:
                continue
            campos["colores"] = col
        elif e["tipo"] == "ventana":
            v = ventana_valida(r.get("ventana"))
            if not v:
                continue
            campos["ventana"] = v
        _cambiar(dir_, e["id"], **campos)
        n += 1
    return n


# ------------------------------------------------------------------ DATOS que se validan (tema y ventanas)
def colores_validos(c):
    if not isinstance(c, dict) or not all(isinstance(c.get(k), str) and _HEX.match(c[k]) for k in CLAVES_TEMA):
        return None
    return {k: c[k].lower() for k in CLAVES_TEMA}


def ventana_valida(v):
    if not isinstance(v, dict):
        return None
    try:
        radio = max(0, min(28, int(v.get("radio", 16))))
        borde = max(0, min(3, int(v.get("borde", 1))))
        opac = max(0.80, min(1.0, float(v.get("opacidad", 0.97))))
    except (TypeError, ValueError):
        return None
    return {"radio": radio, "borde": borde, "opacidad": round(opac, 2), "sombra": bool(v.get("sombra", True))}


# los colores, sin cerebro: por palabras de la descripción (y si no, unos derivados de la propia frase)
_PALABRAS_COLOR = [
    (("bosque", "verde", "naturaleza", "hoja", "selva"), {"fondo": "#06110b", "neon": "#4ade80", "acento": "#facc15", "texto": "#e6f4ea"}),
    (("mar", "oceano", "azul", "agua", "cielo"), {"fondo": "#04101c", "neon": "#38bdf8", "acento": "#818cf8", "texto": "#e3f1fb"}),
    (("fuego", "rojo", "naranja", "lava", "atardecer"), {"fondo": "#140806", "neon": "#fb923c", "acento": "#f43f5e", "texto": "#fbeee6"}),
    (("violeta", "morado", "lila", "magia", "galaxia"), {"fondo": "#0d0716", "neon": "#a78bfa", "acento": "#f472d0", "texto": "#efe9fb"}),
    (("claro", "blanco", "dia", "luminoso"), {"fondo": "#f4f6fb", "neon": "#0e7490", "acento": "#be185d", "texto": "#111827"}),
    (("oro", "dorado", "amarillo", "sol"), {"fondo": "#120e04", "neon": "#facc15", "acento": "#fb923c", "texto": "#fbf5e1"}),
    (("rosa", "sakura", "flor"), {"fondo": "#14070f", "neon": "#f472b6", "acento": "#c084fc", "texto": "#fbe9f3"}),
    (("matrix", "hacker", "terminal"), {"fondo": "#020803", "neon": "#22c55e", "acento": "#86efac", "texto": "#d9f99d"}),
    (("noche", "oscuro", "negro", "neon", "futurista"), {"fondo": "#05070f", "neon": "#22d3ee", "acento": "#f472d0", "texto": "#e7ecf5"}),
]


def colores_de_texto(descripcion):
    t = _plano(descripcion)
    for palabras, col in _PALABRAS_COLOR:
        if any(re.search(r"\b" + p, t) for p in palabras):
            return dict(col)
    import hashlib
    h = int(hashlib.sha1(t.encode("utf-8")).hexdigest()[:6], 16)
    tono = h % 360

    def hsl(hh, s, l):
        import colorsys
        r, g, b = colorsys.hls_to_rgb((hh % 360) / 360.0, l, s)
        return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
    return {"fondo": hsl(tono, 0.45, 0.05), "neon": hsl(tono, 0.85, 0.60), "acento": hsl(tono + 140, 0.80, 0.68),
            "texto": hsl(tono, 0.30, 0.93)}


def ventana_de_texto(descripcion):
    t = _plano(descripcion)
    v = {"radio": 16, "borde": 1, "opacidad": 0.97, "sombra": True}
    if re.search(r"\b(?:cuadrad|rect|recta|angul|sin\s+redonde)", t):
        v["radio"] = 0
    elif re.search(r"\b(?:muy\s+redonde|redondit|burbuja|suave)", t):
        v["radio"] = 26
    elif re.search(r"\bredonde", t):
        v["radio"] = 20
    if re.search(r"\b(?:sin\s+borde|limpi|minimal)", t):
        v["borde"] = 0
    elif re.search(r"\b(?:borde\s+grues|marcad|grues)", t):
        v["borde"] = 3
    if re.search(r"\b(?:transparent|cristal|vidrio)", t):
        v["opacidad"] = 0.85
    elif re.search(r"\b(?:opac|solid)", t):
        v["opacidad"] = 1.0
    if re.search(r"\b(?:sin\s+sombra|plan)", t):
        v["sombra"] = False
    return v


def colores_de_respuesta(texto):
    """Saca 4 colores #rrggbb de lo que contestó el cerebro (JSON o lista suelta). None si no hay 4."""
    s = str(texto or "")
    m = re.search(r"\{[^{}]*\}", s, re.S)
    if m:
        try:
            c = colores_validos(json.loads(m.group(0)))
            if c:
                return c
        except ValueError:
            pass
    hexes = re.findall(r"#[0-9a-fA-F]{6}\b", s)
    if len(hexes) >= 4:
        return dict(zip(CLAVES_TEMA, (h.lower() for h in hexes[:4])))
    return None


def prompt_imagen(e):
    """Lo que se le pide al pintor del móvil para cada tipo (en español: el pintor lo traduce)."""
    d = e.get("descripcion") or DESC_DEFECTO.get(e.get("tipo"), "")
    return {"icono": f"icono de aplicación, {d}, dibujo plano y sencillo, centrado, fondo oscuro liso",
            "logo": f"logotipo, {d}, sencillo y limpio, centrado, fondo oscuro liso",
            "fondo": f"fondo de pantalla de escritorio, {d}, panorámico, alta calidad",
            "salvapantallas": f"fondo de pantalla, {d}, tranquilo, panorámico"}.get(e.get("tipo"), d)


def formato_de(tipo):
    return "horizontal" if tipo in ("fondo", "salvapantallas") else "cuadrado"


# ------------------------------------------------------------------ el MÓVIL: recibe, hace y devuelve
def _ruta_m(dir_):
    return os.path.join(dir_, ARCHIVO_MOVIL)


def _estado_m(dir_):
    d = _leer(_ruta_m(dir_))
    d.setdefault("encargos", [])
    return d


def recibir(dir_, lista):
    """El móvil guarda los encargos de KiraOS (sin repetir). Devuelve cuántos nuevos."""
    d = _estado_m(dir_)
    ya = {e.get("id") for e in d["encargos"]}
    n = 0
    for e in lista or []:
        if not isinstance(e, dict) or e.get("tipo") not in TIPOS or not re.match(r"^[0-9a-f]{6,16}$", str(e.get("id"))):
            continue
        if e["id"] in ya:
            continue
        d["encargos"].append({"id": e["id"], "tipo": e["tipo"], "descripcion": _txt(e.get("descripcion")),
                              "destino": _txt(e.get("destino"), 40), "estado": "pedido", "cuando": int(time.time())})
        ya.add(e["id"])
        n += 1
    if n:
        d["encargos"] = d["encargos"][-MAX_ENCARGOS:]
        _escribir(_ruta_m(dir_), d)
    return n


def encargos_movil(dir_):
    return list(_estado_m(dir_)["encargos"])


def siguiente(dir_):
    return next((e for e in _estado_m(dir_)["encargos"] if e.get("estado") == "pedido"), None)


def hecho(dir_, ident, ruta_imagen_hecha=None, colores=None, ventana=None, fallo=None, nota=""):
    d = _estado_m(dir_)
    for e in d["encargos"]:
        if e["id"] == ident:
            e.update(estado="fallido" if fallo else "hecho", cuando_hecho=int(time.time()), nota=_txt(nota, 200))
            if fallo:
                e["fallo"] = _txt(fallo, 200)
            if ruta_imagen_hecha:
                e["ruta"] = str(ruta_imagen_hecha)
            if colores:
                e["colores"] = colores_validos(colores)
            if ventana:
                e["ventana"] = ventana_valida(ventana)
            _escribir(_ruta_m(dir_), d)
            return e
    return None


def resultados_por_enviar(dir_):
    """([resultado], [ids], quedan) — lo hecho que aún no ha llegado a KiraOS (como mucho 2 imágenes por viaje)."""
    fuera, ids, imgs, quedan = [], [], 0, False
    for e in _estado_m(dir_)["encargos"]:
        if e.get("estado") not in ("hecho", "fallido") or e.get("enviado"):
            continue
        r = {"id": e["id"], "tipo": e["tipo"], "nota": e.get("nota", "")}
        if e.get("estado") == "fallido":
            r["fallo"] = e.get("fallo") or "no pude hacerlo"
        elif e["tipo"] in IMAGEN:
            if imgs >= MAX_IMG_VIAJE:
                quedan = True
                continue
            try:
                with open(e.get("ruta") or "", "rb") as f:
                    datos = f.read()
            except OSError:
                r = {"id": e["id"], "tipo": e["tipo"], "fallo": "la imagen pintada ya no está en el móvil"}
                datos = None
            if datos is not None:
                if len(datos) > MAX_IMG_BYTES or not _es_imagen(datos):
                    r = {"id": e["id"], "tipo": e["tipo"], "fallo": "la imagen salió demasiado grande o rara"}
                else:
                    r["imagen"] = base64.b64encode(datos).decode("ascii")
                    imgs += 1
        elif e["tipo"] == "tema":
            r["colores"] = e.get("colores")
        else:
            r["ventana"] = e.get("ventana")
        fuera.append(r)
        ids.append(e["id"])
    return fuera, ids, quedan


def marcar_enviados(dir_, ids):
    ids = set(ids or [])
    if not ids:
        return
    d = _estado_m(dir_)
    for e in d["encargos"]:
        if e["id"] in ids:
            e["enviado"] = True
    _escribir(_ruta_m(dir_), d)


def pendientes_movil(dir_):
    return sum(1 for e in _estado_m(dir_)["encargos"] if e.get("estado") == "pedido")


# ------------------------------------------------------------------ textos
def texto_pedido(e):
    t = f"Hecho: le he encargado a la Kira del móvil un {NOMBRE_TIPO[e['tipo']]}"
    t += f" («{e['descripcion']}»)" + (f" para «{e['destino']}»" if e.get("destino") else "") + "."
    t += (" Se lo paso en la próxima sincronía (cuando el móvil esté en casa con Kira abierta); lo hace ella y, "
          "cuando me llegue, te lo enseño en Ajustes ▸ Diseños del móvil ANTES de aplicarlo: tú das el visto bueno.")
    return t


def texto_lista(dir_):
    lista = encargos(dir_)
    if not lista:
        return ("Aún no le he encargado ningún diseño al móvil. Pídemelo así: «pídele al móvil un icono de un escudo "
                "para el mapa», «pídele al móvil un fondo de pantalla de un bosque de noche», «pídele al móvil un tema "
                "en tonos violeta» o «pídele al móvil un estilo de ventanas redondeadas».")
    nombres = {"pedido": "esperando a que el móvil lo coja", "entregado": "el móvil lo está haciendo",
               "listo": "LISTO: espera tu visto bueno", "aplicado": "aplicado", "rechazado": "rechazado",
               "fallido": "el móvil no pudo"}
    lin = [f"· {NOMBRE_TIPO.get(e['tipo'], e['tipo'])}: «{e.get('descripcion', '')}»"
           + (f" (para {e['destino']})" if e.get("destino") else "") + f" — {nombres.get(e.get('estado'), e.get('estado'))}"
           + (f" ({e['nota']})" if e.get("estado") == "fallido" and e.get("nota") else "")
           for e in reversed(lista[-15:])]
    return "Diseños que le he encargado al móvil:\n" + "\n".join(lin)
