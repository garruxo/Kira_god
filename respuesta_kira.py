# -*- coding: utf-8 -*-
"""
respuesta_kira.py - Que la charla de Kira no te devuelva tu propia orden ni diga que «no puede» lo que SÍ sabe hacer.

El cerebro del móvil es pequeño: cuando le das una orden que la app no reconoce, a veces repite tu frase («Kira, busca
en internet…»), se pone a hablar como si fuera tú (empieza por «Kira,») o se niega («no puedo crear juegos ni aprender
habilidades nuevas»), cuando sí puede con la orden adecuada. Aquí se arregla la respuesta:
  - quita el «Kira,» del principio (Kira no se llama a sí misma);
  - si es casi tu misma frase, o niega algo que Kira sí hace, la cambia por «así no lo entiendo como orden; prueba…»
    con las órdenes que encajan con lo que pedías.
Lógica pura (sin Kivy).
"""
import re
import unicodedata

VACIAS = set("""a al ante con contra de del desde el en entre es esta este esto ha la las lo los mas me mi mis muy
no o para pero por que se si sin su sus te tu tus un una uno unos unas y ya yo kira luego tambien como cuando""".split())

_NIEGA = re.compile(
    r"\b(no (?:puedo|soy capaz de|tengo (?:la )?(?:capacidad|forma|manera|acceso)|me es posible|se me permite)"
    r"(?: de)?\s+(?:\w+\s+){0,4}?(?:modificar|crear|programar|aprender|hacer|disenar|probar|instalar|descargar|"
    r"buscar|navegar|acceder|ejecutar|implementar|cambiar|desarrollar|generar|escribir)"
    r"|como (?:modelo|asistente|ia) de (?:lenguaje|texto)|solo (?:puedo|soy) (?:un )?(?:texto|conversar|charlar|hablar)"
    r"|no (?:tengo|dispongo de) (?:habilidades|funciones|capacidades))")


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _palabras(t):
    return {p for p in re.findall(r"[a-z0-9ñ]+", _plano(t)) if len(p) > 2 and p not in VACIAS}


def quitar_nombre(respuesta):
    """«Kira, no puedo…» -> «No puedo…»."""
    r = re.sub(r"^\s*kira\s*[,:.!-]+\s*", "", str(respuesta or ""), flags=re.I)
    return r[:1].upper() + r[1:] if r else r


def es_eco(respuesta, pregunta):
    """¿La respuesta es casi la misma frase que dijiste (repetida o con otras palabras)?"""
    a, b = _palabras(respuesta), _palabras(pregunta)
    if len(b) < 3 or not a:
        return False
    comunes = len(a & b)
    return comunes / max(1, len(b)) >= 0.6 and comunes / max(1, len(a)) >= 0.5


def es_pregunta(texto):
    """«¿cómo es…?», «qué es…», «explícame…»: ahí repetir palabras es normal (no es un eco de una orden)."""
    t = _plano(re.sub(r"^\s*kira\s*[,:]*\s*", "", str(texto or ""), flags=re.I)).strip(" ¡!")
    return "?" in t or bool(re.match(r"^(que|como|cual|cuales|cuanto|cuanta|cuantos|por que|porque|quien|quienes|donde|"
                                      r"cuando|explica|explicame|cuentame|dime|sabes|conoces|has|eres|estas)\b", t))


def niega(respuesta):
    return bool(_NIEGA.search(_plano(respuesta)))


GENEROS = [("carrera", "carreras de coches"), ("coche", "carreras de coches"), ("moto", "carreras de motos"),
           ("plataforma", "plataformas de un ninja"), ("salt", "plataformas de un ninja"),
           ("nave", "naves espaciales"), ("dispar", "naves espaciales"), ("luch", "combate de karate"),
           ("combate", "combate de karate"), ("pelea", "combate de karate"), ("laberinto", "laberinto retro"),
           ("retro", "laberinto retro"), ("comecocos", "laberinto retro")]

TEMAS = [
    (r"\b(app|aplicacion|apk|instalable|icono)\b", ["conviértelo en una app", "conviértelo en una app de verdad"]),
    (r"\b(aprende|aprender|habilidad|habilidades|mejora|mejorar|funcion|funciones|modificar|modificate)",
     ["aprende a … (lo que quieras que sepa hacer)", "receta de …"]),
    (r"\b(programa|codigo|script|implementa|editor)\b", ["escríbeme un programa que …", "implementa este código"]),
    (r"\b(experiment|inventa|nuevo|original)", ["experimenta con …"]),
    (r"\b(estudia|investiga|internet|busca|biblioteca|libreria|informacion)",
     ["busca en internet …", "estudia en internet …", "instala la librería …"]),
    (r"\b(pdf|documento|libro)\b", ["descarga este PDF: enlace", "resume el pdf 1"]),
    (r"\b(web|pagina|diseno|disena|maqueta)\b", ["diséñame una web de …", "diséñame una maqueta de app de …"]),
    (r"\b(dibuja|pinta|imagen|foto|dibujo)\b", ["pinta …", "hazme una foto de …"]),
]


def sugerencias(pregunta, maximo=3):
    """Las órdenes que la app SÍ entiende y encajan con lo que pedías."""
    t = _plano(pregunta)
    sal = []
    if re.search(r"\b(juego|juegos|videojuego|jugar)\b", t):
        genero = next((g for clave, g in GENEROS if clave in t), None)
        if genero:
            sal.append(f"hazme un juego de {genero}")
        else:
            sal += ["hazme un juego de carreras de coches", "hazme un juego retro"]
        if re.search(r"\b3 ?d\b|tridimensional", t):
            sal.append("(Los juegos de Kira son en 2D: el 3D aún no lo sé hacer.)")
    for rx, ordenes in TEMAS:
        if re.search(rx, t):
            sal += ordenes
    vistos, unicas = set(), []
    for s in sal:
        if s not in vistos:
            vistos.add(s)
            unicas.append(s)
    notas = [s for s in unicas if s.startswith("(")]
    return [s for s in unicas if not s.startswith("(")][:maximo] + notas[:1]


def arreglar(respuesta, pregunta):
    """La respuesta que se enseña y se dice. Devuelve (texto, cambiada)."""
    r = quitar_nombre(respuesta)
    if not ((es_eco(r, pregunta) and not es_pregunta(pregunta)) or niega(r)):
        return r, r != respuesta
    sug = sugerencias(pregunta)
    if sug:
        ordenes = [s for s in sug if not s.startswith("(")]
        nota = next((s for s in sug if s.startswith("(")), "")
        return ("Así, todo junto, no lo entiendo como orden, pero sí sé hacerlo. Pídemelo así: "
                + ", ".join(f"«Kira, {s}»" for s in ordenes) + "." + (f" {nota[1:-1]}" if nota else "")), True
    return ("Así no lo entiendo como orden. Pídeme una cosa cada vez, por ejemplo: «Kira, hazme un juego de carreras», "
            "«Kira, aprende a …» o «Kira, busca en internet …». Di «ayuda» para ver todo lo que sé hacer."), True
