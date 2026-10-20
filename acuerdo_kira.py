# -*- coding: utf-8 -*-
"""
acuerdo_kira.py - Kira y Claude trabajan JUNTOS y se ponen de acuerdo (mejoras, programas, diseños y estudio).

Cómo es el trato (cuando están los dos: el cerebro del móvil encendido y la clave de Claude):
  1. Kira (el cerebro del móvil) propone: escribe la mejora o el programa con lo que ha estudiado.
  2. El laboratorio lo prueba (en el móvil; y en el ordenador si está conectado).
  3. Claude lo revisa: si está de acuerdo, hay ACUERDO. Si no, dice por qué y puede traer su versión.
  4. Si Claude trae su versión, también se prueba, y Kira dice si la acepta. Si no, Kira corrige la suya con lo que
     dijo Claude y vuelta a empezar (como mucho unas pocas rondas, para no gastar de más).
  5. Al final te enseñan el resultado y la conversación. Lo que se instala lo sigues decidiendo TÚ (dos toques).
Con «cerebro mejoras claude», propone Claude y revisa Kira. Si solo hay uno de los dos, trabaja solo (como antes).

«acuerdo con claude» (ver), «activa / desactiva el acuerdo con claude». Lógica pura (sin red, sin Kivy).
"""
import json
import os
import re
import unicodedata

NOMBRES = {"local": "Kira", "claude": "Claude"}
RONDAS = 3

SISTEMA_REVISION = (
    "Trabajas en equipo con Kira, una asistente que corre en un móvil con un modelo de IA pequeño. Uno de los dos ha "
    "escrito este código y ya ha pasado las pruebas automáticas del laboratorio. Tú decides si de verdad hace lo que "
    "pidió el usuario, sin fallos claros (entradas raras, mensajes confusos, casos que no contempla) y respetando las "
    "reglas. Responde SOLO con este formato:\n"
    "ACUERDO: SÍ o NO\nMOTIVOS: <1 a 3 frases en español, claras, para el usuario>\n"
    "Si es NO y sabes arreglarlo, añade tu versión completa corregida con el mismo formato que la original:\n"
    "NOMBRE: <nombre>\n```python\n<código completo>\n```\n"
    "No digas NO por detalles de estilo: solo si algo falla o no hace lo pedido.\nReglas del código: ")

SISTEMA_REVISION_LOCAL = (
    "Eres Kira. Revisa si este código hace lo que pidió el usuario. Responde SOLO con una línea:\n"
    "SÍ\n(si estás de acuerdo) o\nNO: <motivo corto>\n(si ves un fallo claro).")

SISTEMA_REPASO = (
    "Eres el profesor de Kira, una asistente que aprende en un móvil. Kira ha estudiado un tema en la Wikipedia y te "
    "enseña sus fichas. Escribe UNA ficha de repaso en español, de 4 a 6 frases claras: lo esencial del tema, corrige "
    "lo que esté mal en sus fichas y añade lo importante que falte. Sin markdown ni listas. Si sus fichas no tienen "
    "nada que ver con el tema, explica el tema tú mismo.")

SISTEMA_DISENO_REVISION = (
    "Revisas, junto a Kira, el CONTENIDO de un diseño (textos y colores en JSON). Kira propone uno; mejóralo si hace "
    "falta (textos más claros y atractivos, colores que combinen, que encaje con lo pedido) y devuelve SOLO el JSON "
    "final con EXACTAMENTE las mismas claves y el mismo formato. ")


class Reintentar(Exception):
    """El autor tiene que volver a intentarlo (el texto es lo que se le explica)."""


class Parar(Exception):
    """No se puede seguir (sin cerebro, laboratorio caído…). El texto se le enseña al usuario."""


# =====================================================================================
#  AJUSTE: activo / inactivo
# =====================================================================================
class Ajuste:
    """Desde la v2.26 viene APAGADO (lo pidió el dueño: las mejoras, solo con su criterio y el de Kira). Lo guardado
    antes de la v2.26 no cuenta; si el dueño lo vuelve a encender («activa el acuerdo con claude»), se respeta."""
    VERSION = 2

    def __init__(self, ruta):
        self.ruta = ruta
        self.activo = False
        try:
            with open(ruta, encoding="utf-8") as f:
                d = json.load(f)
            if d.get("v") == self.VERSION:
                self.activo = d.get("activo") is True
        except (OSError, ValueError, AttributeError):
            pass

    def poner(self, valor):
        self.activo = bool(valor)
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"activo": self.activo, "v": self.VERSION}, f)
        os.replace(tmp, self.ruta)
        return self.activo


ORDEN = re.compile(r"^(?:(activa|desactiva|enciende|apaga|quita|pon)\s+)?(?:el\s+)?acuerdo\s+con\s+claude\s*$", re.I)


def es_orden(texto):
    return bool(ORDEN.match(" ".join(str(texto or "").lower().split()).strip(" .!¡?¿")))


# =====================================================================================
#  LEER LA REVISIÓN
# =====================================================================================
def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def interpretar_revision(texto, extraer=None):
    """{'acuerdo': True|False|None, 'motivos': str, 'nombre': str|None, 'codigo': str|None}.
    extraer(texto) -> (nombre, codigo) saca la versión propia del revisor (si la trae). None = no se entiende."""
    t = str(texto or "").strip()
    acuerdo, motivos = None, ""
    m = re.search(r"ACUERDO[\s:*_]*(S[IÍ]|NO)\b", t, re.I)
    if m:
        acuerdo = _plano(m.group(1)).startswith("s")
    else:
        primera = next((l.strip(" *#>-") for l in t.splitlines() if l.strip(" *#>-")), "")
        p = _plano(primera)
        if re.match(r"^(si|de acuerdo|estoy de acuerdo|correcto|vale)\b", p):
            acuerdo = True
        elif re.match(r"^no\b", p):
            acuerdo = False
            motivos = primera.split(":", 1)[1].strip() if ":" in primera else ""
    mm = re.search(r"MOTIVOS?[*_]*\s*:[\s*_]*(.+?)(?:\n[\s*_]*NOMBRE\s*:|```|\Z)", t, re.S | re.I)
    if mm:
        motivos = mm.group(1)
    elif not motivos and acuerdo is not None:
        resto = [l.strip() for l in t.splitlines()[1:] if l.strip() and not l.strip().startswith(("```", "NOMBRE"))]
        motivos = " ".join(resto[:2])
    motivos = " ".join(motivos.split())[:400]
    nombre = codigo = None
    if acuerdo is False and extraer is not None and "```" in t:
        try:
            nombre, codigo = extraer(t)
        except ValueError:
            nombre = codigo = None
    return {"acuerdo": acuerdo, "motivos": motivos, "nombre": nombre, "codigo": codigo}


def informe_lab(res):
    """Resumen corto del laboratorio para quien revisa."""
    if not isinstance(res, dict):
        return "sin datos del laboratorio"
    etapas = [f"{e.get('nombre')}: {'OK' if e.get('ok') else 'FALLÓ'}" for e in res.get("etapas", []) if isinstance(e, dict)]
    avisos = [str(a) for a in res.get("avisos", [])][:6]
    return ("Pasa las pruebas" if res.get("ok") else "No pasa las pruebas") + " (" + ", ".join(etapas[:10]) + ")" + \
        (". Avisos: " + "; ".join(avisos) if avisos else "")


def mensaje_revision(pedido, autor, codigo, informe, objecion=""):
    return (f"Pedido del usuario: {pedido}\n\nVersión de {autor}:\n```python\n{codigo.strip()}\n```\n\n"
            f"Laboratorio: {informe}" + (f"\n\nLo que se objetó antes: {objecion}" if objecion else ""))


# =====================================================================================
#  NEGOCIAR
# =====================================================================================
def negociar(proponer, probar, revisar=None, autor="local", revisor=None, intentos=5, rondas=RONDAS):
    """Hasta dar con un código que pase el laboratorio y en el que estén de acuerdo los dos.
      proponer(aviso) -> (nombre, codigo)        el AUTOR escribe (aviso = lo que tiene que corregir); puede lanzar
                                                Reintentar(motivo) o Parar(motivo)
      probar(nombre, codigo) -> (ok, motivo, dato)   el laboratorio; puede lanzar Parar
      revisar(quien, nombre, codigo, dato, objecion) -> interpretar_revision(...) | None
                                                quien = 'revisor' (el otro mira la versión del autor) o 'autor'
                                                (el autor mira la versión que trajo el otro)
    Devuelve {'ok', 'nombre', 'codigo', 'dato', 'de': 'local'|'claude', 'acuerdo': True|False|None, 'historial',
              'intentos', 'error'}. acuerdo=None: no había con quién acordar (o no respondió)."""
    A = NOMBRES.get(autor, str(autor))
    B = NOMBRES.get(revisor, str(revisor)) if revisor else ""
    hist, aviso, mejor, rondas_hechas, i = [], "", None, 0, 0

    def fin(acuerdo, error=""):
        r = {"ok": mejor is not None, "acuerdo": acuerdo, "historial": hist, "intentos": i, "error": error,
             "nombre": None, "codigo": None, "dato": None, "de": None}
        if mejor is not None:
            r.update(nombre=mejor[0], codigo=mejor[1], dato=mejor[2], de=mejor[3])
        return r

    while i < intentos:
        i += 1
        try:
            nombre, codigo = proponer(aviso)
        except Reintentar as e:
            aviso = "El intento anterior falló: " + str(e)
            hist.append(f"{A}: lo intenta otra vez ({str(e)[:120]})")
            continue
        except Parar as e:
            hist.append(f"{A}: no puede seguir ({e})")
            return fin(None, str(e))
        try:
            ok, motivo, dato = probar(nombre, codigo)
        except Reintentar as e:
            aviso = "El intento anterior falló: " + str(e)
            hist.append(f"Revisión previa: {str(e)[:160]}")
            continue
        except Parar as e:
            hist.append(f"Laboratorio: no disponible ({e})")
            return fin(None, str(e))
        if not ok:
            aviso = "El intento anterior falló: " + str(motivo)
            hist.append(f"Laboratorio: la versión de {A} no pasa ({str(motivo)[:160]})")
            continue
        hist.append(f"Laboratorio: la versión de {A} pasa las pruebas.")
        mejor = (nombre, codigo, dato, autor)
        if not revisor or revisar is None:
            return fin(None)
        v = revisar("revisor", nombre, codigo, dato, "")
        if not v or v.get("acuerdo") is None:
            hist.append(f"{B}: no pudo revisarla ahora (sin respuesta clara). Se queda la versión de {A}.")
            return fin(None)
        rondas_hechas += 1
        if v["acuerdo"]:
            hist.append(f"{B}: de acuerdo." + (f" {v['motivos']}" if v.get("motivos") else ""))
            return fin(True)
        hist.append(f"{B}: no está de acuerdo. {v.get('motivos') or ''}".strip())
        aviso = (f"{B} revisó tu versión y no está de acuerdo: {v.get('motivos') or 'no explica el motivo'}. "
                 "Corrígela teniendo en cuenta lo que dice.")
        if v.get("codigo"):
            n2 = v.get("nombre") or nombre
            try:
                ok2, motivo2, dato2 = probar(n2, v["codigo"])
            except (Reintentar, Parar) as e:
                ok2, motivo2, dato2 = False, str(e), None
            if ok2:
                hist.append(f"Laboratorio: la versión de {B} pasa las pruebas.")
                w = revisar("autor", n2, v["codigo"], dato2, v.get("motivos", ""))
                if not w or w.get("acuerdo") is None or w["acuerdo"]:
                    hist.append(f"{A}: acepta la versión de {B}." if w and w.get("acuerdo") else
                                f"{A}: no pone pegas a la versión de {B}.")
                    mejor = (n2, v["codigo"], dato2, revisor)
                    return fin(True)
                hist.append(f"{A}: no acepta la versión de {B}: {w.get('motivos') or 'sin motivo'}")
                aviso += f" Su versión no te convenció ({w.get('motivos') or 'sin motivo'}): haz una que resuelva las dos cosas."
            else:
                hist.append(f"Laboratorio: la versión de {B} no pasa ({str(motivo2)[:160]}).")
        if rondas_hechas >= rondas:
            break
    if mejor is not None and revisor and rondas_hechas:
        hist.append(f"Sin acuerdo tras {rondas_hechas} ronda(s): decides tú con lo que dijo cada uno.")
    return fin(False if (mejor is not None and revisor and rondas_hechas) else None)


def texto_historial(r):
    """Lo que se enseña al usuario: cómo fue la conversación entre Kira y Claude."""
    if not r.get("historial"):
        return ""
    cab = {True: "ACUERDO entre Kira y Claude.", False: "SIN ACUERDO entre Kira y Claude: decides tú.",
           None: ""}[r.get("acuerdo")]
    return ((cab + "\n") if cab else "") + "\n".join("· " + h for h in r["historial"])
