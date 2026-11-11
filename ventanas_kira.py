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
    raros = set(datos) - {"en", "titulo", "texto", "botones", "icono"}
    if raros:
        raise VentanaError("la ventana solo admite en, titulo, texto, botones e icono (sobra: " + ", ".join(sorted(map(str, raros))) + ")")
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
    r = {"id": ident, "en": en, "titulo": titulo, "texto": texto, "botones": limpios}
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
Opcional "icono" (el dibujo del icono en el escritorio): ''' + ", ".join(ICONOS_EXTRA) + '''.
Si el botón necesita algo nuevo, añade también su orden al diccionario (por ejemplo "mis redes hoy": funcion(texto)).'''


def ejemplo_para_cerebro(pedido):
    return ("\n\nPARA VENTANAS, SECCIONES, MENÚS Y BOTONES:\n" + EJEMPLO_VENTANA) if pedido_de_ventana(pedido) else ""


# ---------- las órdenes del dueño ----------
_CREAR = re.compile(r"^(?:por\s+favor\s+)?(?:kira[\s,]+)?(?:cr[eé]a(?:me)?|a[ñn]ade(?:me)?|pon(?:me)?|haz(?:me)?|"
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
