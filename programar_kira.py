# -*- coding: utf-8 -*-
"""
programar_kira.py - Kira te ESCRIBE PROGRAMAS para el editor (sin ordenador y sin instalar nada).

«Kira, escríbeme un programa que calcule mi media de notas», «hazme un juego de naves»:
  1. Kira escribe el programa con lo que ha estudiado (recetas probadas + su baúl);
  2. lo prueba en MODO SEGURO (el del editor: sin archivos, red ni sistema, con tiempo máximo); si es un juego, lo
     juega unos segundos simulados;
  3. si está Claude, lo revisa y se ponen de acuerdo (acuerdo_kira);
  4. te lo deja abierto en el editor: TÚ pulsas «Ejecutar» o «Jugar», y lo guardas si te gusta.
No toca a Kira ni se instala: por eso no pide los dos toques de las mejoras. Lógica pura (sin Kivy).
"""
import re

import ejecutor_kira as ej

ENTRADA_PRUEBA = "3\n5\n7\nhola\n10\n"     # por si el programa usa input(): la prueba le da unas líneas

REGLAS_PROGRAMA = (
    "es un programa de Python para el EDITOR de Kira en MODO SEGURO: sin archivos (open), sin red, sin os ni sys, sin "
    "eval/exec/getattr/setattr; solo módulos de esta lista: math, random, statistics, datetime, time, calendar, "
    "collections, itertools, functools, string, textwrap, re, json, heapq, bisect, decimal, fractions, dataclasses, "
    "enum, typing, copy, hashlib, base64, uuid, unittest y motor_juegos_kira. Muestra los resultados con print(). "
    "input() lee líneas de la caja de entrada del editor (úsalo solo si hace falta pedir datos). Debe terminar en menos "
    "de 5 segundos. Si es un JUEGO: «from motor_juegos_kira import Juego» y una clase que herede de Juego con titulo, "
    "instrucciones, preparar(), actualizar(dt) y al_tocar(x, y); piezas con self.rect(x, y, w, h, color), "
    "self.circulo(x, y, r, color), self.texto(x, y, texto, tam, color), self.linea(...), self.poligono([...], color); "
    "self.azar(a, b), self.dedo, self.chocan(a, b), self.con_etiqueta(t), self.puntos, self.vidas, self.fin(msg); "
    "pantalla 360x640 con la y hacia arriba. Código corto, claro y comentado en español.")

SISTEMA_PROGRAMA = ("Escribes programas para el editor de Kira. Responde SOLO con:\nNOMBRE: <nombre_corto_en_minusculas>\n"
                    "```python\n<programa completo>\n```\nReglas: " + REGLAS_PROGRAMA)

SISTEMA_PROGRAMA_LOCAL = (
    "Escribe un programa corto de Python. Responde SOLO con:\nNOMBRE: nombre_en_minusculas\n```python\n...\n```\n"
    "Reglas: usa print() para mostrar el resultado; solo math, random, datetime, re, json, collections, statistics; "
    "nada de open, os, sys, eval ni exec; que termine rápido.\n"
    "Ejemplo:\nNOMBRE: media_notas\n```python\nnotas = [7, 8.5, 6]\n# la media es la suma entre cuántas hay\n"
    "media = sum(notas) / len(notas)\nprint(f\"Tu media es {media:.2f}\")\n```")

_PIDE = re.compile(
    r"^(?:por\s+favor\s+)?(?:escr[ií]be(?:me)?|hazme|haz|cr[eé]a(?:me)?|progr[aá]mame|prep[aá]rame|monta(?:me)?)\s+"
    r"(?:un|el|otro)\s+(?P<que>programa|script|c[oó]digo|juego|jueguito)\b\s*(?P<resto>.*)$", re.I | re.S)


def pedido_programa(texto):
    """Si la frase pide un PROGRAMA o un JUEGO para el editor, devuelve el pedido ('juego de naves', 'programa que…');
    si no, None. («programa un juego…» sigue siendo una MEJORA de Kira: se instala en Juegos con tus dos toques.)"""
    t = " ".join(str(texto or "").split()).strip(" .!¡?¿")
    m = _PIDE.match(t)
    if not m:
        return None
    resto = m.group("resto").strip(" ,.:")
    if len(resto) < 3:
        return None
    que = m.group("que").lower()
    return ("juego " if que.startswith("juego") else "programa ") + resto


def extraer_programa(texto):
    """(nombre, codigo) de la respuesta de la IA. Lanza ValueError si no trae código."""
    t = str(texto or "")
    m_c = re.search(r"```(?:python|py|python3)?[ \t]*\n(.*?)```", t, re.S | re.I)
    if not m_c:
        if re.search(r"^\s*(?:print|def |import |from |class |for |while |\w+\s*=)", t, re.M):
            codigo = t[re.search(r"^\s*(?:print|def |import |from |class |for |while |\w+\s*=)", t, re.M).start():]
        else:
            raise ValueError("La respuesta no trae el programa (falta el bloque ```python … ```).")
    else:
        codigo = m_c.group(1)
    m_n = re.search(r"NOMBRE\s*:\s*`?([A-Za-z][A-Za-z0-9_]{0,39})", t)
    nombre = ej.nombre_valido(m_n.group(1) if m_n else "") or "programa_de_kira"
    return nombre, codigo.strip("\n") + "\n"


def es_juego(codigo):
    return "motor_juegos_kira" in codigo and re.search(r"class\s+\w+\s*\(\s*(?:\w+\.)?Juego\s*\)", codigo) is not None


def probar_programa(codigo):
    """(ok, motivo, dato). dato = {'ok', 'etapas', 'avisos', 'salida', 'juego'}: lo mismo que se le enseña a Claude."""
    dato = {"ok": False, "etapas": [], "avisos": [], "salida": "", "juego": es_juego(codigo)}
    motivo = ej.revisar(codigo)
    if motivo:
        dato["etapas"].append({"nombre": "modo_seguro", "ok": False, "detalle": motivo})
        return False, motivo, dato
    dato["etapas"].append({"nombre": "modo_seguro", "ok": True})
    if dato["juego"]:
        import juegos_kira as jk
        juego, error = jk.cargar(codigo, semilla=1)
        if juego is None:
            dato["etapas"].append({"nombre": "juego", "ok": False, "detalle": error})
            return False, error, dato
        try:
            for i in range(60 * 8):                          # 8 segundos de juego simulado, con toques
                if i % 30 == 0:
                    ej.con_limite(juego.tocar, 0.5, 40 + (i * 7) % 280, 60 + (i * 11) % 500)
                if i % 45 == 0:
                    ej.con_limite(juego.mover_dedo, 0.5, 180, 300, 25, 0)
                ej.con_limite(juego.paso, 0.5, 1 / 60)
                if juego.estado in ("fin", "ganado"):
                    juego.tocar(10, 10)
        except ej.TiempoAgotado:
            motivo = "El juego se queda colgado en un fotograma (¿un bucle infinito en actualizar?)."
        except Exception as e:
            motivo = f"El juego falla al jugar: {type(e).__name__}: {e}"
        if motivo:
            dato["etapas"].append({"nombre": "juego", "ok": False, "detalle": motivo})
            return False, motivo, dato
        dato["etapas"].append({"nombre": "juego", "ok": True, "detalle": "8 s jugados con toques"})
        dato["ok"] = True
        return True, "", dato
    r = ej.ejecutar(codigo, entrada=ENTRADA_PRUEBA, limite=5)
    dato["salida"] = r["salida"][:600]
    if not r["ok"]:
        if r["error"].startswith("EOFError"):                # pide más datos de los que le dimos: no es un fallo
            dato["avisos"].append("pide más datos por input() de los que se le dieron en la prueba")
        else:
            dato["etapas"].append({"nombre": "ejecucion", "ok": False, "detalle": r["error"]})
            return False, r["error"], dato
    if not r["salida"].strip() and not dato["avisos"]:
        dato["avisos"].append("no muestra nada con print()")
    dato["etapas"].append({"nombre": "ejecucion", "ok": True, "detalle": f"{r['segundos']} s"})
    dato["ok"] = True
    return True, "", dato


def informe(dato):
    """Para quien revisa: cómo fue la prueba y qué mostró."""
    import acuerdo_kira as ak
    txt = ak.informe_lab(dato)
    if dato.get("salida"):
        txt += "\nLo que mostró en la prueba (con la entrada «3, 5, 7, hola, 10» si pedía datos):\n" + dato["salida"][:400]
    return txt
