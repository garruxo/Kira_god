# -*- coding: utf-8 -*-
"""
explicacion_codigo_kira.py - Explica un código Python LÍNEA POR LÍNEA, de forma técnica (para aprender a programar).

Lo usan la Sala Hacker del móvil y KiraOS del portátil para enseñar lo que Kira va escribiendo mientras programa.
Es DETERMINISTA y sin internet: lee el código con `ast` (el analizador de Python) y, por cada línea con código,
dice qué es con los términos de verdad (función, argumento, bucle, condición, variable, return, import…). Si el
código aún no es válido (se está escribiendo), cae a una explicación por patrones, para poder ir explicando en vivo.

  explicar(codigo) -> {"lineas": [{"n", "codigo", "nota"}], "resumen": "..."}

Solo librería estándar. Se prueba en tests/test_explicacion.py.
"""
import ast
import re


def _nombre_destino(nodo):
    try:
        if isinstance(nodo, ast.Name):
            return nodo.id
        if isinstance(nodo, ast.Attribute):
            return _nombre_destino(nodo.value) + "." + nodo.attr
        if isinstance(nodo, ast.Subscript):
            return _nombre_destino(nodo.value) + "[...]"
        if isinstance(nodo, (ast.Tuple, ast.List)):
            return ", ".join(_nombre_destino(e) for e in nodo.elts)
    except Exception:
        pass
    return "…"


def _fuente(nodo):
    try:
        return ast.unparse(nodo)
    except Exception:
        return "…"


def _nota_nodo(nodo):
    """La nota TÉCNICA de una sentencia (por su tipo)."""
    if isinstance(nodo, (ast.Import, ast.ImportFrom)):
        mods = ", ".join(a.name for a in nodo.names)
        if isinstance(nodo, ast.ImportFrom):
            return f"import: trae {mods} del módulo «{nodo.module}» para poder usarlo."
        return f"import: carga el módulo «{mods}» (una caja de herramientas ya hecha)."
    if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = [a.arg for a in nodo.args.args]
        return (f"def: define la función «{nodo.name}» con argumentos ({', '.join(args) or 'sin argumentos'}). "
                "Es un bloque reutilizable; no se ejecuta hasta que se la llama.")
    if isinstance(nodo, ast.ClassDef):
        return f"class: define la clase «{nodo.name}» (un molde para crear objetos con datos y funciones)."
    if isinstance(nodo, ast.Return):
        return f"return: la función termina y devuelve {_fuente(nodo.value) if nodo.value else 'nada'}."
    if isinstance(nodo, (ast.For, ast.AsyncFor)):
        return (f"for: bucle. Repite el bloque de dentro una vez por cada «{_nombre_destino(nodo.target)}» "
                f"de {_fuente(nodo.iter)}.")
    if isinstance(nodo, ast.While):
        return f"while: bucle. Repite el bloque mientras se cumpla que {_fuente(nodo.test)}."
    if isinstance(nodo, ast.If):
        return f"if: condición. Ejecuta el bloque solo si {_fuente(nodo.test)}."
    if isinstance(nodo, (ast.Try,)):
        return "try: intenta el bloque y, si da error, salta al «except» en vez de romper."
    if isinstance(nodo, (ast.ExceptHandler,)):
        return "except: aquí se atrapa el error para que el programa no se caiga."
    if isinstance(nodo, ast.With):
        return "with: abre algo (un archivo, un recurso) y lo cierra solo al terminar."
    if isinstance(nodo, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        destinos = (", ".join(_nombre_destino(t) for t in nodo.targets) if isinstance(nodo, ast.Assign)
                    else _nombre_destino(nodo.target))
        val = _fuente(nodo.value) if getattr(nodo, "value", None) is not None else "…"
        return f"variable: guarda en «{destinos}» el valor {val}."
    if isinstance(nodo, ast.Expr):
        v = nodo.value
        if isinstance(v, ast.Call):
            return f"llamada: ejecuta {_nombre_destino(v.func)}(…) (usa una función)."
        if isinstance(v, (ast.Constant,)) and isinstance(getattr(v, "value", None), str):
            return "texto de ayuda (docstring): explica para qué sirve esto; no hace nada."
        return "expresión: calcula un valor."
    if isinstance(nodo, ast.Raise):
        return "raise: lanza un error a propósito (para avisar de que algo no vale)."
    if isinstance(nodo, (ast.Break,)):
        return "break: corta el bucle y sale de él."
    if isinstance(nodo, (ast.Continue,)):
        return "continue: salta a la siguiente vuelta del bucle."
    return ""


# ---- reserva por patrones (cuando el código aún no es válido, para ir explicando en vivo) ----
_PATRONES = [
    (re.compile(r"^\s*#"), lambda l: "comentario: una nota para las personas; Python la ignora."),
    (re.compile(r"^\s*(from|import)\s"), lambda l: "import: trae herramientas ya hechas de otro módulo."),
    (re.compile(r"^\s*def\s+(\w+)"), lambda l: f"def: define la función «{re.search(r'def\s+(\w+)', l).group(1)}»."),
    (re.compile(r"^\s*class\s+(\w+)"), lambda l: f"class: define la clase «{re.search(r'class\s+(\w+)', l).group(1)}»."),
    (re.compile(r"^\s*return\b"), lambda l: "return: la función devuelve un valor y termina."),
    (re.compile(r"^\s*for\b"), lambda l: "for: bucle, repite para cada elemento."),
    (re.compile(r"^\s*while\b"), lambda l: "while: bucle, repite mientras se cumpla la condición."),
    (re.compile(r"^\s*if\b"), lambda l: "if: condición, solo si se cumple."),
    (re.compile(r"^\s*elif\b"), lambda l: "elif: otra condición si la anterior no se cumplió."),
    (re.compile(r"^\s*else\b"), lambda l: "else: lo que se hace si no se cumplió la condición."),
    (re.compile(r"^\s*try\b"), lambda l: "try: intenta algo que podría fallar."),
    (re.compile(r"^\s*except\b"), lambda l: "except: atrapa el error para no romper."),
    (re.compile(r"^\s*with\b"), lambda l: "with: abre y cierra solo un recurso."),
    (re.compile(r"^\s*\w[\w\.\[\]]*\s*="), lambda l: "variable: guarda un valor con un nombre."),
    (re.compile(r"\w+\s*\("), lambda l: "llamada: usa una función."),
]


def _nota_patron(linea):
    for rx, fn in _PATRONES:
        if rx.search(linea):
            try:
                return fn(linea)
            except Exception:
                return ""
    return ""


def explicar(codigo):
    """Devuelve la explicación técnica línea por línea. Siempre funciona (si el código no es válido aún, por patrones)."""
    codigo = (codigo or "").rstrip("\n")
    lineas_txt = codigo.split("\n")
    notas = {}
    resumen = ""
    try:
        arbol = ast.parse(codigo)
        # nota por cada sentencia, en su línea
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.stmt) and getattr(nodo, "lineno", None):
                n = _nota_nodo(nodo)
                if n and nodo.lineno not in notas:
                    notas[nodo.lineno] = n
        funcs = [n.name for n in ast.walk(arbol) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        clases = [n.name for n in ast.walk(arbol) if isinstance(n, ast.ClassDef)]
        partes = []
        if clases:
            partes.append(f"{len(clases)} clase(s): {', '.join(clases)}")
        if funcs:
            partes.append(f"{len(funcs)} función(es): {', '.join(funcs)}")
        resumen = "Este código define " + (" y ".join(partes) + "." if partes else "unas instrucciones.")
    except SyntaxError:
        resumen = "Código a medio escribir; te lo voy explicando por lo que se ve."

    salida = []
    for i, texto in enumerate(lineas_txt, start=1):
        if not texto.strip():
            salida.append({"n": i, "codigo": texto, "nota": ""})
            continue
        if texto.lstrip().startswith("#"):
            salida.append({"n": i, "codigo": texto, "nota": "comentario: una nota para las personas; Python la ignora."})
            continue
        nota = notas.get(i) or _nota_patron(texto)
        salida.append({"n": i, "codigo": texto, "nota": nota})
    return {"lineas": salida, "resumen": resumen}


def texto_plano(codigo):
    """La explicación como texto corrido (para la charla o la voz)."""
    r = explicar(codigo)
    out = [r["resumen"], ""]
    for l in r["lineas"]:
        if l["nota"]:
            out.append(f"Línea {l['n']}: {l['nota']}")
    return "\n".join(out)
