# -*- coding: utf-8 -*-
"""
mejoras_ia_kira.py - Ayudas para que la IA (sobre todo un modelo LOCAL pequeño) escriba bien las mejoras de Kira.
Lógica PURA (sin red, sin Kivy). No ejecuta el código que revisa: solo lo analiza con 'ast'.

  - SISTEMA_MEJORA / SISTEMA_MEJORA_LOCAL: instrucciones completas (Claude) y cortas con EJEMPLOS (modelo pequeño).
  - extraer_modulo(texto): saca NOMBRE y código de la respuesta aunque el modelo no respete el formato al 100 %.
  - precomprobar(codigo): revisión rápida EN EL MÓVIL antes de gastar un viaje al laboratorio (sintaxis, registrar(),
    importaciones y llamadas prohibidas). Si falla, el motivo se le devuelve a la IA para que lo corrija.
El laboratorio sigue siendo quien prueba de verdad, y tú quien decide.
"""
import ast
import re

MAX_CODIGO = 200_000
IMPORTS_PROHIBIDOS = {"subprocess", "socket", "ctypes", "shutil", "os", "pickle", "importlib", "urllib", "requests",
                      "http", "multiprocessing", "sys"}
LLAMADAS_PROHIBIDAS = {"eval", "exec", "compile", "__import__", "open", "input"}

API_KIRA = (
    "Para audio, vídeo y archivos la función recibe (texto, kira): kira.medios(tipo=None) -> lista de dicts (titulo, tipo, "
    "estado, ruta); kira.importar(titulo) -> nombre de archivo en la carpeta de trabajo; kira.ffmpeg(entradas, salida, args) "
    "(nombres simples sin rutas; args solo opciones como -af -vf -filter_complex -ss -to -c:a -c:v -b:a); "
    "kira.escribir(nombre, texto) / kira.leer(nombre) para .txt .json .md .csv; kira.exportar(nombre) -> (ok, mensaje).")

SISTEMA_MEJORA = (
    "Eres el generador de mejoras de KiraOS. Responde SOLO con este formato:\n"
    "NOMBRE: <identificador_en_minusculas_con_guion_bajo>\n"
    "```python\n<modulo completo>\n```\n"
    "Reglas del módulo: debe definir registrar() que devuelva un diccionario "
    "{prefijo_de_comando_en_minusculas: funcion}. La función puede ser funcion(texto)->str o, para trabajar con "
    "audio, vídeo y archivos, funcion(texto, kira)->str. " + API_KIRA + " Filtros de ffmpeg habituales: volume, afade, amix, "
    "adelay, pan, atrim, atempo, aecho, bass, treble, loudnorm, scale, crop, trim, setpts, concat, fade. "
    "Si hay que hacer cosas con audio o vídeo, usa SIEMPRE 'kira' y no subprocess. Lanza ValueError con un mensaje claro "
    "cuando la orden del usuario no se entienda. Solo librería estándar. "
    "No uses subprocess, socket, eval, exec, os, shutil, open, ni borres archivos, ni leas claves. "
    "Código corto y comentado. No escribas nada fuera del formato."
)

EJEMPLOS = '''Ejemplo 1 (orden de texto):
NOMBRE: contar_palabras
```python
def registrar():
    def contar(texto):
        # cuenta las palabras que escribe el usuario
        return f"Tu texto tiene {len(texto.split())} palabras."
    return {"contar palabras": contar}
```
Ejemplo 2 (audio con kira):
NOMBRE: subir_volumen
```python
def registrar():
    def subir(texto, kira):
        nombre = kira.importar(texto.strip())
        kira.ffmpeg([nombre], "mas_alto.mp3", ["-af", "volume=1.5"])
        return kira.exportar("mas_alto.mp3")[1]
    return {"subir volumen": subir}
```'''

SISTEMA_MEJORA_LOCAL = (
    "Escribe un módulo de Python para KiraOS. Responde SOLO con:\n"
    "NOMBRE: nombre_en_minusculas\n```python\n...código...\n```\n"
    "Reglas:\n1) Define registrar() que devuelve {\"orden en minúsculas\": funcion}.\n"
    "2) La función recibe (texto) o (texto, kira) y devuelve un texto.\n"
    "3) Solo librería estándar. Prohibido: os, subprocess, shutil, socket, open, eval, exec.\n"
    "4) " + API_KIRA + "\n" + EJEMPLOS + "\nAhora escribe SOLO el módulo pedido, con el mismo formato."
)


def extraer_modulo(texto):
    """(nombre, codigo) a partir de la respuesta de la IA. Tolera ```py, falta de NOMBRE o falta de las comillas.
    Lanza ValueError si no hay ningún código reconocible."""
    t = str(texto or "")
    m_nombre = re.search(r"NOMBRE\s*:\s*`?([A-Za-z][A-Za-z0-9_]{0,30})", t)
    m_codigo = re.search(r"```(?:python|py|python3)?[ \t]*\n(.*?)```", t, re.S | re.I)
    if m_codigo:
        codigo = m_codigo.group(1)
    elif "def registrar" in t:                              # sin bloque de código: desde el primer import/def
        i = min([p for p in (t.find("import "), t.find("from "), t.find("def ")) if p >= 0] or [0])
        codigo = t[i:]
    else:
        raise ValueError("La respuesta de la IA no trae el código del módulo (falta el bloque ```python … ```).")
    codigo = codigo.strip("\n") + "\n"
    if m_nombre:
        nombre = m_nombre.group(1).lower()
    else:                                                    # sin NOMBRE: se saca de la primera orden registrada
        m = re.search(r"return\s*\{\s*[\"']([a-z][a-z0-9 _]{0,30})[\"']", codigo)
        nombre = re.sub(r"[^a-z0-9_]+", "_", m.group(1)).strip("_") if m else "mejora"
    nombre = (nombre if re.match(r"^[a-z]", nombre) else "m_" + nombre)[:31]
    return nombre, codigo


def precomprobar(codigo):
    """None si el código pasa la revisión rápida; si no, un texto con el motivo (para devolvérselo a la IA)."""
    if not codigo or not codigo.strip():
        return "El módulo está vacío."
    if len(codigo) > MAX_CODIGO:
        return "El módulo es demasiado largo."
    try:
        arbol = ast.parse(codigo)
    except SyntaxError as e:
        return f"Error de sintaxis en la línea {e.lineno}: {e.msg}. Corrige el código."
    reg = [n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == "registrar"]
    if not reg:
        return "Falta la función registrar() a nivel de módulo (no dentro de otra función ni clase)."
    if reg[0].args.args:
        return "registrar() no debe recibir parámetros."
    if not any(isinstance(n, ast.Return) and n.value is not None for n in ast.walk(reg[0])):
        return "registrar() debe terminar con return {\"orden\": funcion}."
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] in IMPORTS_PROHIBIDOS:
                    return f"No se permite importar '{a.name}' (línea {n.lineno}). Usa las funciones de 'kira' en su lugar."
        elif isinstance(n, ast.ImportFrom) and n.module and n.module.split(".")[0] in IMPORTS_PROHIBIDOS:
            return f"No se permite importar de '{n.module}' (línea {n.lineno}). Usa las funciones de 'kira' en su lugar."
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in LLAMADAS_PROHIBIDAS:
            return f"No se permite llamar a {n.func.id}() (línea {n.lineno})."
    return None
