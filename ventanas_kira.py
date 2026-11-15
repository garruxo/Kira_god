# -*- coding: utf-8 -*-
"""v3.19: VENTANAS, SECCIONES y BOTONES que Kira se añade a sí misma cuando tú se lo pides.

«Kira, crea en la WiFi una sección con un botón que diga qué redes tengo guardadas», «Kira, ponte en el escritorio una
ventana "Mi día" con tres botones…» → Kira escribe una MEJORA (un módulo) que, además de órdenes, declara su ventana.

Cómo es una ventana (solo DATOS, nunca código de pantalla): en el módulo,

    def registrar():
        def ventana(texto):
            return {"en": "wifi", "titulo": "Mis redes", "texto": "Lo que quieras explicar.",
                    "botones": [{"texto": "Redes guardadas", "orden": "redes guardadas"}]}
        return {"ventana mis redes": ventana, ...las órdenes de siempre...}

- «en»: dónde aparece: "escritorio" (un icono nuevo) o dentro de una ventana que ya existe (EN_VENTANAS: wifi, red,
  maquina, cuaderno, movil, ajustes, terminal, buscador, mapa, programando, hablar) como un botón más arriba.
- cada botón le da una ORDEN a Kira (como si se la dijeras tú): pasa por los mismos candados de siempre.
- nada de HTML ni JavaScript: la pantalla solo pinta texto y botones (así una mejora no puede romper ni espiar la
  pantalla). Por eso es seguro: lo peligroso seguiría pasando por el laboratorio y tus dos toques.

Lógica PURA: `validar` limpia y comprueba; `ejemplo_para_cerebro` es lo que se le enseña al cerebro al escribirla.
"""
import re

EN_VENTANAS = ("escritorio", "wifi", "red", "maquina", "cuaderno", "movil", "ajustes", "terminal", "buscador", "mapa",
               "programando", "hablar")
# v3.21: el DIBUJO del icono de una ventana nueva (solo un nombre de esta lista: la pantalla tiene los dibujos)
ICONOS_EXTRA = ("estrella", "corazon", "rayo", "nota", "casa", "sol", "luna", "musica", "camara", "libro", "escudo",
                "reloj", "bluetooth", "altavoz", "brillo", "juego", "mensaje", "carpeta")
# v3.23: dónde sale DENTRO de una sala: «boton» (arriba, en la cabecera; lo de siempre), «arriba» o «abajo» (una
# tarjeta dentro de la propia sala, con su texto y sus botones)
LUGARES = ("boton", "arriba", "abajo")
MAX_TITULO = 40
MAX_TEXTO = 3000
MAX_BOTONES = 12
MAX_TEXTO_BOTON = 40
MAX_ORDEN = 200
MAX_VENTANAS = 30
_ID = re.compile(r"^[a-z0-9áéíóúñü][a-z0-9áéíóúñü _-]{0,39}$")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_ALIAS_EN = {"inicio": "escritorio", "pantalla principal": "escritorio", "principal": "escritorio", "escritorio": "escritorio",
             "wi-fi": "wifi", "wi fi": "wifi", "mi red": "red", "maquina virtual": "maquina", "máquina": "maquina",
             "máquina virtual": "maquina", "móvil": "movil", "configuracion": "ajustes", "configuración": "ajustes",
             "ajustes": "ajustes"}


class VentanaError(ValueError):
    pass


def es_ventana(prefijo):
    return isinstance(prefijo, str) and prefijo.startswith("ventana ")


def id_de(prefijo):
    """«ventana mis redes» → «mis redes»."""
    return str(prefijo)[len("ventana "):].strip()


def _texto(v, maximo, que):
    if v is None:
        return ""
    if not isinstance(v, (str, int, float)):
        raise VentanaError(f"{que} debe ser un texto")
    t = _CONTROL.sub("", str(v)).strip()
    if len(t) > maximo:
        t = t[:maximo - 1].rstrip() + "…"
    return t


def validar(ident, datos):
    """Comprueba y LIMPIA lo que devuelve la función de la ventana. Devuelve el dict limpio o lanza VentanaError
    con un motivo en español (para que el laboratorio se lo diga al cerebro y lo corrija)."""
    ident = str(ident or "").strip().lower()
    if not _ID.match(ident):
        raise VentanaError(f"el nombre de la ventana «{ident}» no vale: minúsculas, números y espacios, máx. 40")
    if not isinstance(datos, dict):
        raise VentanaError("la función de la ventana debe devolver un diccionario {\"en\", \"titulo\", \"texto\", \"botones\"}")
    raros = set(datos) - {"en", "titulo", "texto", "botones", "icono", "lugar"}
    if raros:
        raise VentanaError("la ventana solo admite en, titulo, texto, botones, icono y lugar (sobra: " + ", ".join(sorted(map(str, raros))) + ")")
    en = _texto(datos.get("en") or "escritorio", 30, "«en»").lower()
    en = _ALIAS_EN.get(en, en)
    if en not in EN_VENTANAS:
        raise VentanaError(f"«en» debe ser uno de: {', '.join(EN_VENTANAS)} (no «{en}»)")
    titulo = _texto(datos.get("titulo") or ident.capitalize(), MAX_TITULO, "el título")
    icono = _texto(datos.get("icono"), 20, "«icono»").lower().translate(str.maketrans("áéíóú", "aeiou"))
    if icono and icono not in ICONOS_EXTRA:
        raise VentanaError(f"«icono» debe ser uno de: {', '.join(ICONOS_EXTRA)} (no «{icono}»)")
    texto = _texto(datos.get("texto"), MAX_TEXTO, "el texto")
    botones = datos.get("botones") or []
    if not isinstance(botones, (list, tuple)):
        raise VentanaError("«botones» debe ser una lista de {\"texto\", \"orden\"}")
    if len(botones) > MAX_BOTONES:
        raise VentanaError(f"como mucho {MAX_BOTONES} botones por ventana")
    limpios = []
    for b in botones:
        if not isinstance(b, dict):
            raise VentanaError("cada botón debe ser {\"texto\": …, \"orden\": …}")
        bt = _texto(b.get("texto"), MAX_TEXTO_BOTON, "el texto del botón")
        orden = _texto(b.get("orden"), MAX_ORDEN, "la orden del botón").replace("\n", " ")
        if not bt or not orden:
            raise VentanaError("cada botón necesita «texto» (lo que pone) y «orden» (lo que me pide al pulsarlo)")
        limpios.append({"texto": bt, "orden": orden})
    if not texto and not limpios:
        raise VentanaError("la ventana está vacía: pon un texto o algún botón")
    lugar = _texto(datos.get("lugar") or "boton", 10, "«lugar»").lower().replace("botón", "boton")
    if lugar not in LUGARES:
        raise VentanaError(f"«lugar» debe ser uno de: {', '.join(LUGARES)} (no «{lugar}»)")
    if en == "escritorio":
        lugar = "boton"                      # en el escritorio es un icono
    r = {"id": ident, "en": en, "titulo": titulo, "texto": texto, "botones": limpios}
    if lugar != "boton":
        r["lugar"] = lugar
    if icono:
        r["icono"] = icono
    return r


def probar(tabla):
    """Para el laboratorio: valida TODAS las ventanas de un registrar(). None si están bien, o el motivo."""
    n = 0
    for prefijo, fn in (tabla or {}).items():
        if not es_ventana(prefijo):
            continue
        n += 1
        if n > MAX_VENTANAS:
            return f"demasiadas ventanas (máximo {MAX_VENTANAS})"
        if not callable(fn):
            return f"«{prefijo}» debe ser una función ventana(texto) que devuelve sus datos"
        try:
            datos = fn("")
            validar(id_de(prefijo), datos)
        except VentanaError as e:
            return f"«{prefijo}»: {e}"
        except Exception as e:                       # noqa: BLE001
            return f"«{prefijo}» falla al pedir sus datos: {type(e).__name__}: {e}"
    return None


def pedido_de_ventana(texto):
    """¿El pedido es crear o cambiar una ventana/botón/sección/apartado/menú? Para dar al cerebro el ejemplo bueno."""
    return bool(re.search(r"\b(?:ventana|bot[oó]n|botones|secci[oó]n|apartado|men[uú]|pesta[ñn]a|icono|pantalla)\b",
                          str(texto or ""), re.I))


EJEMPLO_VENTANA = '''Ejemplo (una ventana con botones; cada botón le da una orden a Kira):
NOMBRE: mis_redes
```python
def registrar():
    def ventana(texto):
        # solo datos: dónde sale, título, explicación y botones
        return {"en": "wifi", "titulo": "Mis redes",
                "texto": "Atajos para mis redes de casa.",
                "botones": [{"texto": "Redes guardadas", "orden": "redes guardadas"},
                            {"texto": "Arregla la wifi", "orden": "arregla la wifi"}]}
    return {"ventana mis redes": ventana}
```
«en» puede ser: ''' + ", ".join(EN_VENTANAS) + ''' («escritorio» = un icono nuevo). Cada botón: {"texto", "orden"}.
Opcional "lugar" (si sale DENTRO de una sala): "boton" (un botón arriba, por defecto), "arriba" o "abajo" (una tarjeta dentro de la sala).
Opcional "icono" (el dibujo del icono en el escritorio): ''' + ", ".join(ICONOS_EXTRA) + '''.
Si el botón necesita algo nuevo, añade también su orden al diccionario (por ejemplo "mis redes hoy": funcion(texto)).'''


def ejemplo_para_cerebro(pedido):
    return ("\n\nPARA VENTANAS, SECCIONES, MENÚS Y BOTONES:\n" + EJEMPLO_VENTANA) if pedido_de_ventana(pedido) else ""


# ---------- las órdenes del dueño ----------
_CREAR = re.compile(r"^(?:por\s+favor\s+)?(?:kira[\s,]+)?(?:en\s+(?:\S+[\s,]+){1,5}?)?(?:cr[eé]a(?:me)?|a[ñn]ade(?:me)?|pon(?:me)?|haz(?:me)?|"
                    r"hazte|ponte|a[ñn][aá]dete|construye(?:me)?)\s+"
                    r"(?:(?!(?:programa|juego|app|aplicaci[oó]n|apk|web|p[aá]gina)\b)\S+\s+){0,6}?"
                    r"(?:ventana|bot[oó]n(?:es)?|secci[oó]n|apartado|men[uú]|pesta[ñn]a|icono)\b(?P<p>.*)$",
                    re.I)
_CAMBIAR = re.compile(r"^(?:por\s+favor\s+)?(?:kira[\s,]+)?(?:cambia|modifica|mejora|arregla|edita|toca|ajusta)\s+"
                      r"(?:la\s+|el\s+|tu\s+|mi\s+)?(?:ventana|bot[oó]n|secci[oó]n|apartado|men[uú]|pesta[ñn]a|icono)\s+"
                      r"(?:de\s+|del\s+|de\s+la\s+)?[«\"']?(?P<n>[^:«»\"',]{1,40}?)[»\"']?\s*(?:[:,]|para\s+que|que|y)\s*(?P<p>.+)$",
                      re.I)
_QUITAR = re.compile(r"^(?:por\s+favor\s+)?(?:kira[\s,]+)?(?:quita|borra|elimina)\s+(?:la\s+|el\s+|tu\s+|mi\s+)?"
                     r"(?:ventana|bot[oó]n|secci[oó]n|apartado|men[uú]|pesta[ñn]a|icono)\s+(?:de\s+)?[«\"']?(?P<n>[^«»\"']{1,40}?)[»\"']?\s*$",
                     re.I)


def orden(texto):
    """(«crear», pedido) | («cambiar», nombre, cambios) | («quitar», nombre) | None."""
    t = re.sub(r"\s+", " ", str(texto or "")).strip().rstrip(" .!?")
    m = _CAMBIAR.match(t)
    if m:
        return ("cambiar", m.group("n").strip().lower(), m.group("p").strip())
    m = _QUITAR.match(t)
    if m:
        return ("quitar", m.group("n").strip().lower())
    m = _CREAR.match(t)
    if m and len(m.group("p").strip()) >= 3:
        return ("crear", t)
    return None


def buscar(ventanas, nombre):
    """La ventana instalada que más se parece a `nombre` (por su id o su título). None si ninguna."""
    nombre = str(nombre or "").strip().lower()
    if not nombre:
        return None
    for v in ventanas:
        if nombre in (v["id"], v["titulo"].lower()):
            return v
    for v in ventanas:
        if nombre in v["id"] or nombre in v["titulo"].lower() or v["id"] in nombre:
            return v
    return None


def pedido_cambio(v, codigo, cambios):
    """El pedido para el cerebro al CAMBIAR una ventana: el código de ahora + lo que quieres (mismo NOMBRE → la
    nueva versión sustituye a la vieja, y «Volver atrás» devuelve la de antes)."""
    return (f"Cambia mi módulo «{v['modulo']}» (su ventana «{v['id']}»). Mantén NOMBRE: {v['modulo']} y todo lo que ya "
            f"hace, y cambia SOLO esto: {cambios}\nCódigo actual:\n```python\n{str(codigo).strip()}\n```")


# ---------- v3.75: la ventana / el botón se CONSTRUYE directamente de tu frase (sin depender del cerebro) ----------
# Una ventana es solo DATOS, así que no hace falta que el cerebro pequeño la escriba (se equivocaba: hacía una orden
# normal y la ventana no salía). Si la frase se entiende, se arma el módulo aquí; si no, se le pide al cerebro.
import unicodedata as _ud

_SALAS = [("pantalla principal", "escritorio"), ("escritorio", "escritorio"), ("inicio", "escritorio"),
          ("maquina virtual", "maquina"), ("maquina", "maquina"), ("wi fi", "wifi"), ("wifi", "wifi"),
          ("mi red", "red"), ("red", "red"), ("cuaderno", "cuaderno"), ("movil", "movil"), ("ajustes", "ajustes"),
          ("configuracion", "ajustes"), ("terminal", "terminal"), ("buscador", "buscador"), ("mapa", "mapa"),
          ("programando", "programando"), ("hablar", "hablar")]
_NOMBRE_SALA = {"maquina": "tu máquina", "wifi": "la wifi", "red": "la red", "cuaderno": "tu cuaderno",
                "movil": "el móvil", "terminal": "la terminal", "mapa": "el mapa", "buscador": "el buscador"}
_SUBJ = {"muestre": "enséñame", "ensene": "enséñame", "enseñe": "enséñame", "diga": "dime", "haga": "haz",
         "ponga": "pon", "abra": "abre", "busque": "busca", "encienda": "enciende", "apague": "apaga",
         "estudie": "estudia", "lea": "lee", "compruebe": "comprueba", "mire": "mira", "revise": "revisa",
         "arregle": "arregla", "conecte": "conecta", "desconecte": "desconecta", "cierre": "cierra",
         "borre": "borra", "cuente": "cuenta", "calcule": "calcula", "piense": "piensa", "pinte": "pinta",
         "guarde": "guarda", "investigue": "investiga", "resuma": "resume", "explique": "explica",
         "actualice": "actualiza", "liste": "lista", "escanee": "escanea", "vigile": "vigila",
         "reinicie": "reinicia", "programe": "programa", "trabaje": "trabaja", "use": "usa", "traiga": "trae", "lance": "lanza", "ejecute": "ejecuta"}
_INF = {"mostrar": "enséñame", "ensenar": "enséñame", "ver": "enséñame", "decir": "dime", "hacer": "haz",
        "poner": "pon", "abrir": "abre", "buscar": "busca", "encender": "enciende", "apagar": "apaga",
        "estudiar": "estudia", "leer": "lee", "comprobar": "comprueba", "mirar": "mira", "revisar": "revisa",
        "arreglar": "arregla", "conectar": "conecta", "desconectar": "desconecta", "cerrar": "cierra",
        "borrar": "borra", "contar": "cuenta", "calcular": "calcula", "pensar": "piensa", "pintar": "pinta",
        "guardar": "guarda", "investigar": "investiga", "resumir": "resume", "explicar": "explica",
        "actualizar": "actualiza", "listar": "lista", "escanear": "escanea", "vigilar": "vigila",
        "reiniciar": "reinicia", "programar": "programa", "trabajar": "trabaja", "usar": "usa", "lanzar": "lanza", "ejecutar": "ejecuta"}


def _sin_tildes(t):
    return "".join(c for c in _ud.normalize("NFD", str(t or "")) if _ud.category(c) != "Mn")


def _sala_de(plano):
    for pal, sala in _SALAS:
        if re.search(r"\b(?:en|dentro\s+de|a)\s+(?:la\s+|el\s+|mi\s+|tu\s+)?(?:ventana\s+|sala\s+|seccion\s+|pantalla\s+)?"
                     r"(?:de\s+|del\s+)?(?:la\s+|el\s+|mi\s+|tu\s+)?" + pal + r"\b", plano):
            return sala
    return None


def _a_orden(frase, sala):
    """«que me muestre las redes guardadas» → «enséñame las redes guardadas»; «para encenderla» → «enciende tu máquina»."""
    f = re.sub(r"^(?:que\s+|para\s+que\s+|para\s+|y\s+)", "", frase.strip(" ,.:;"), flags=re.I).strip()
    f = re.sub(r"^(?:me\s+|te\s+|nos\s+)", "", f, flags=re.I)
    palabras = f.split()
    if not palabras:
        return ""
    p0 = _sin_tildes(palabras[0]).lower()
    clitico = ""
    m = re.match(r"^([a-z]+?(?:ar|er|ir))(la|lo|las|los|me)?$", p0)
    if p0 in _SUBJ:
        palabras[0] = _SUBJ[p0]
    elif m and m.group(1) in _INF:
        palabras[0], clitico = _INF[m.group(1)], m.group(2) or ""
    o = " ".join(palabras)
    if clitico in ("la", "lo", "las", "los") and sala in _NOMBRE_SALA and len(palabras) == 1:
        o += " " + _NOMBRE_SALA[sala]
    return o.strip()[:MAX_ORDEN]


def _corto(t, n=MAX_TEXTO_BOTON):
    t = t.strip(" ,.:;«»\"'")
    t = t[:1].upper() + t[1:]
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


def construir(pedido):
    """(nombre, código, datos) armado directamente desde la frase, o None si no se entiende bien.
    El código es un módulo de Kira normal (registrar() con «ventana <id>»): pasa por el laboratorio y tus dos toques."""
    orig = re.sub(r"\s+", " ", str(pedido or "")).strip().rstrip(" .!?")
    plano = _sin_tildes(orig).lower()
    if not re.search(r"\b(?:ventana|boton(?:es)?|seccion|apartado|menu|pestana|icono)\b", plano):
        return None
    sala = _sala_de(plano)
    es_seccion = bool(re.search(r"\b(?:seccion|apartado)\b", plano))
    titulo = ""
    mt = re.search(r"[«\"“']([^«»\"”']{2,40})[»\"”']", orig) or \
        re.search(r"\b(?:llamad[oa]|que\s+se\s+llame|con\s+el\s+nombre(?:\s+de)?|de\s+nombre)\s+([^,.:;]{2,40}?)"
                  r"(?=\s+(?:que|para|con|en|y)\b|[,.:;]|$)", orig, re.I)
    if mt:
        titulo = mt.group(1).strip()
    botones = []
    ml = re.search(r"\b(?:botones|funciones|opciones|cosas)\b[^:]*:\s*(?P<l>.+)$", orig, re.I)
    if ml:
        for it in re.split(r"\s*(?:,|;|\by\b|\be\b)\s*", ml.group("l")):
            it = it.strip(" .«»\"'")
            if len(it) >= 2:
                o = _a_orden(it, sala)
                botones.append({"texto": _corto(it), "orden": o or it})
    else:
        # lo que hace el botón: lo que va tras «que / para» después de la palabra botón/sección/ventana
        ma = re.search(r"\b(?:bot[oó]n(?:es)?|secci[oó]n|apartado|ventana|men[uú]|icono)\b(?P<r>.*)$", orig, re.I)
        resto = ma.group("r") if ma else ""
        resto = re.sub(r"[«\"“'][^«»\"”']{2,40}[»\"”']", " ", resto)
        resto = re.sub(r"\b(?:llamad[oa]|que\s+se\s+llame|con\s+el\s+nombre(?:\s+de)?|de\s+nombre)\s+[^,.:;]{2,40}?"
                       r"(?=\s+(?:que|para|con|en|y)\b|[,.:;]|$)", " ", resto, flags=re.I)
        # quita «en la ventana de X» (la sala) del resto
        resto = re.sub(r"\b(?:en|dentro\s+de)\s+(?:la\s+|el\s+|mi\s+|tu\s+)?(?:ventana\s+|sala\s+|pantalla\s+)?"
                       r"(?:de\s+|del\s+)?(?:la\s+|el\s+|mi\s+|tu\s+)?[\wáéíóúñ ]{2,20}?(?=\s+(?:que|para|con)\b|[,.:;]|$)",
                       " ", resto, flags=re.I)
        resto = re.sub(r"\b(?:nuev[oa]s?|con\s+un\s+bot[oó]n|con\s+bot[oó]n|un\s+bot[oó]n)\b", " ", resto, flags=re.I)
        mq = re.search(r"\b(?:que|para(?:\s+que)?)\b\s+(?P<a>.+)$", resto, re.I)
        accion = mq.group("a").strip(" ,.") if mq else ""
        if accion:
            o = _a_orden(accion, sala)
            if o:
                botones.append({"texto": _corto(titulo or o), "orden": o})
    if not botones:
        return None
    if not titulo:
        titulo = botones[0]["texto"] if len(botones) == 1 else ("Mis atajos" if sala and sala != "escritorio" else "Mi ventana")
    titulo = _corto(titulo, MAX_TITULO)
    ident = re.sub(r"[^a-z0-9 ]+", "", _sin_tildes(titulo).lower()).strip()[:40] or "mi ventana"
    if not _ID.match(ident):
        ident = "mi ventana"
    datos = {"en": sala or "escritorio", "titulo": titulo,
             "texto": "Me la añadí cuando me lo pediste: «" + orig[:150] + "».", "botones": botones[:MAX_BOTONES]}
    if es_seccion and sala and sala != "escritorio":
        datos["lugar"] = "arriba"
    validar(ident, datos)                              # si algo no vale, mejor saberlo ya (lanza VentanaError)
    nombre = ("ventana_" + re.sub(r"[^a-z0-9]+", "_", ident).strip("_"))[:31]
    codigo = ("# Mejora de KiraOS: una ventana/botón pedido por el dueño (solo datos: texto y botones).\n"
              "def registrar():\n"
              "    def ventana(texto):\n"
              f"        return {datos!r}\n"
              f"    return {{{('ventana ' + ident)!r}: ventana}}\n")
    return nombre, codigo, datos


def texto_construida(datos):
    donde = "en el escritorio (un icono nuevo)" if datos["en"] == "escritorio" else (
        f"dentro de «{datos['en']}» " + ("(una tarjeta arriba)" if datos.get("lugar") == "arriba" else
                                       "(un botón «+ " + datos["titulo"] + "» arriba, en la cabecera)"))
    bots = "; ".join(f"«{b['texto']}» → me dice «{b['orden']}»" for b in datos["botones"])
    return f"He preparado «{datos['titulo']}» {donde}, con: {bots}."


def tiene_ventana(codigo):
    """¿El módulo declara de verdad alguna «ventana …»? (si no, no saldría nada en la pantalla)."""
    return bool(re.search(r"""["']ventana\s+[^"']+["']\s*:""", str(codigo or "")))
