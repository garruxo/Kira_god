# -*- coding: utf-8 -*-
"""
parche_kira.py — v3.30: parchear en vez de reescribir todo.

Lo pidió el dueño: «cuando programe una mejora, que no cambie entero el código, sino que vaya a la línea que tiene que
cambiar o agregar nuevos códigos y lo haga; programar desde cero cuando haga falta, pero la cuestión es que sea
EFICIENTE».

Cuando hay que CAMBIAR un módulo que YA existe, el cerebro no reescribe todo (lento, y con el 2B del Packard Bell se
corta a media): dice SOLO las líneas que cambia, añade o quita, y aquí se aplican sobre el código de ahora. Si el parche
no encaja, quien llama vuelve a reescribir el módulo entero (siempre hay red de seguridad: laboratorio + dos toques; el
parche solo cambia CÓMO se escribe el código nuevo, no cómo se instala).

Puro: sin red, sin Kivy. No ejecuta nada; solo manipula texto.

Formato que el cerebro debe emitir (uno o varios bloques, cada palabra clave en su propia línea):

    CAMBIA:
    <las líneas de ahora, tal cual>
    POR:
    <las líneas nuevas>

    AÑADE DESPUÉS DE:
    <una línea que ya existe, tal cual>
    NUEVO:
    <las líneas a añadir>

    AÑADE AL FINAL:
    <las líneas a añadir>

    QUITA:
    <las líneas de ahora, tal cual>
"""
import re
import unicodedata


class ParcheError(ValueError):
    """El parche no se pudo aplicar (formato raro o las líneas de ahora no se encontraron)."""


def _sin_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")


def _clave(linea):
    """Si la línea es SOLO una palabra clave del formato (sin más), devuelve su tipo; si no, None."""
    t = _sin_acentos(linea).strip().lower().rstrip(":").strip()
    if t in ("cambia", "reemplaza", "sustituye", "modifica"):
        return "cambia"
    if t in ("por", "por esto", "por este", "nuevo", "esto", "por:"):
        return "nuevo"
    if t in ("quita", "borra", "elimina", "quitar"):
        return "quita"
    if t in ("anade al final", "agrega al final", "al final", "anadir al final"):
        return "final"
    if t in ("anade despues de", "anade tras", "inserta despues de", "agrega despues de",
             "despues de", "tras", "anadir despues de"):
        return "despues"
    if t in ("anade antes de", "inserta antes de", "antes de", "agrega antes de"):
        return "antes"
    return None


def _quitar_vallas(texto):
    """Quita las líneas que son solo ``` o ```python (por si el cerebro envuelve el parche en un bloque)."""
    fuera = []
    for linea in str(texto or "").splitlines():
        if re.match(r"^\s*```[ \t]*(?:python3?|py)?[ \t]*$", linea):
            continue
        fuera.append(linea)
    return fuera


def _recortar(bloque):
    """Quita líneas en blanco al principio y al final de un bloque (listas de líneas). Lo de dentro se respeta."""
    i, j = 0, len(bloque)
    while i < j and not bloque[i].strip():
        i += 1
    while j > i and not bloque[j - 1].strip():
        j -= 1
    return bloque[i:j]


def _operaciones(respuesta):
    """Lee la respuesta del cerebro y devuelve una lista de operaciones:
    {"tipo": "cambia"|"quita"|"final"|"despues"|"antes", "viejo": [...], "nuevo": [...], "ancla": [...]}"""
    lineas = _quitar_vallas(respuesta)
    ops = []
    i = 0
    n = len(lineas)
    while i < n:
        tipo = _clave(lineas[i])
        if tipo == "cambia":
            i += 1
            viejo, nuevo, en_nuevo = [], [], False
            while i < n:
                k = _clave(lineas[i])
                if k == "nuevo":
                    en_nuevo = True
                    i += 1
                    continue
                if k in ("cambia", "quita", "final", "despues", "antes") and (en_nuevo or viejo):
                    break
                (nuevo if en_nuevo else viejo).append(lineas[i])
                i += 1
            ops.append({"tipo": "cambia", "viejo": _recortar(viejo), "nuevo": _recortar(nuevo)})
        elif tipo == "quita":
            i += 1
            viejo = []
            while i < n and _clave(lineas[i]) is None:
                viejo.append(lineas[i])
                i += 1
            ops.append({"tipo": "quita", "viejo": _recortar(viejo)})
        elif tipo == "final":
            i += 1
            nuevo = []
            while i < n and _clave(lineas[i]) is None:
                nuevo.append(lineas[i])
                i += 1
            ops.append({"tipo": "final", "nuevo": _recortar(nuevo)})
        elif tipo in ("despues", "antes"):
            i += 1
            ancla, nuevo, en_nuevo = [], [], False
            while i < n:
                k = _clave(lineas[i])
                if k == "nuevo":
                    en_nuevo = True
                    i += 1
                    continue
                if k in ("cambia", "quita", "final", "despues", "antes") and (en_nuevo or ancla):
                    break
                (nuevo if en_nuevo else ancla).append(lineas[i])
                i += 1
            ops.append({"tipo": tipo, "ancla": _recortar(ancla), "nuevo": _recortar(nuevo)})
        else:
            i += 1
    return ops


def _encajar(lineas, bloque):
    """Índice de la primera línea donde `bloque` encaja dentro de `lineas` (comparando sin espacios al final),
    o -1 si no está. Para evitar cambiar lo que no es, exige que encaje UNA sola vez cuando el bloque es corto."""
    if not bloque:
        return -1
    objetivo = [b.rstrip() for b in bloque]
    hallados = []
    for i in range(len(lineas) - len(objetivo) + 1):
        if [lineas[i + k].rstrip() for k in range(len(objetivo))] == objetivo:
            hallados.append(i)
    if not hallados:
        return -1
    # un bloque de 1 línea muy corta que aparece varias veces es ambiguo: no tocamos nada
    if len(hallados) > 1 and len(objetivo) == 1 and len(objetivo[0].strip()) < 8:
        return -2
    return hallados[0]


def aplicar(codigo, respuesta):
    """Aplica el parche de `respuesta` sobre `codigo`. Devuelve el código nuevo.
    Lanza ParcheError si no hay operaciones o alguna no encaja."""
    ops = _operaciones(respuesta)
    if not ops:
        raise ParcheError("no encontré cambios con el formato CAMBIA/POR, AÑADE o QUITA.")
    lineas = str(codigo or "").splitlines()
    cambios = 0
    for op in ops:
        tipo = op["tipo"]
        if tipo in ("cambia", "quita"):
            viejo = op["viejo"]
            if not viejo:
                raise ParcheError("un bloque CAMBIA/QUITA venía sin las líneas de ahora.")
            i = _encajar(lineas, viejo)
            if i == -2:
                raise ParcheError("«%s» aparece varias veces; no sé cuál cambiar." % viejo[0].strip())
            if i < 0:
                raise ParcheError("no encontré estas líneas para cambiarlas: «%s»" % viejo[0].strip()[:60])
            lineas[i:i + len(viejo)] = (op["nuevo"] if tipo == "cambia" else [])
            cambios += 1
        elif tipo == "final":
            if op["nuevo"]:
                if lineas and lineas[-1].strip():
                    lineas.append("")
                lineas.extend(op["nuevo"])
                cambios += 1
        elif tipo in ("despues", "antes"):
            ancla = op["ancla"]
            if not ancla or not op["nuevo"]:
                raise ParcheError("un bloque AÑADE venía sin la línea de referencia o sin lo que añadir.")
            i = _encajar(lineas, ancla)
            if i == -2:
                raise ParcheError("«%s» aparece varias veces; no sé dónde añadir." % ancla[0].strip())
            if i < 0:
                raise ParcheError("no encontré la línea de referencia: «%s»" % ancla[0].strip()[:60])
            pos = i if tipo == "antes" else i + len(ancla)
            lineas[pos:pos] = op["nuevo"]
            cambios += 1
    if not cambios:
        raise ParcheError("el parche no cambió nada.")
    nuevo = "\n".join(lineas)
    if not nuevo.endswith("\n"):
        nuevo += "\n"
    return nuevo


def aplicar_seguro(codigo, respuesta):
    """Como aplicar(), pero devuelve None en vez de lanzar (para que quien llama caiga a reescribir entero)."""
    try:
        return aplicar(codigo, respuesta)
    except ParcheError:
        return None


# ---------- detectar que un pedido es un CAMBIO con código de ahora ----------
def codigo_de_pedido(pedido):
    """Si el pedido trae «Código actual: ```python …```» (lo produce ventanas_kira.pedido_cambio al CAMBIAR un
    módulo que ya existe), devuelve (nombre|None, codigo_actual). Si no, None.
    No se dispara con «convierte este código en una mejora» (ahí el código es un PROGRAMA, no el módulo de ahora)."""
    t = str(pedido or "")
    m = re.search(r"c[oó]digo\s+actual\s*:\s*```[ \t]*(?:python3?|py)?[ \t]*\n(.*?)```", t, re.S | re.I)
    if not m:
        return None
    codigo = m.group(1).strip("\n")
    if "def registrar" not in codigo:
        return None
    mn = re.search(r"NOMBRE\s*:\s*`?([A-Za-z][A-Za-z0-9_]{0,30})", t)
    return (mn.group(1).lower() if mn else None), codigo + "\n"


def nombre_de(codigo):
    """Un nombre de módulo sacado de la orden que registra (por si no venía NOMBRE). La busca en el return de
    registrar(): {"orden": funcion} (el valor es una función, no un texto), para no confundirla con un dict de datos."""
    m = re.search(r"return\s*\{\s*[\"']([a-z][a-z0-9 _]{0,30})[\"']\s*:\s*[A-Za-z_]", str(codigo or ""))
    if m:
        return re.sub(r"[^a-z0-9_]+", "_", m.group(1)).strip("_") or "mejora"
    return "mejora"


# ---------- instrucciones para el cerebro ----------
_FORMATO = (
    "Responde SOLO con los cambios, con este formato (cada palabra clave en su propia línea; copia las líneas de ahora "
    "EXACTAS, con su sangría):\n\n"
    "CAMBIA:\n<las líneas de ahora>\nPOR:\n<las líneas nuevas>\n\n"
    "AÑADE DESPUÉS DE:\n<una línea que ya existe>\nNUEVO:\n<las líneas a añadir>\n\n"
    "AÑADE AL FINAL:\n<las líneas a añadir>\n\n"
    "QUITA:\n<las líneas de ahora>\n\n"
    "Puedes poner varios bloques. No pongas ```; no expliques nada; no reescribas el módulo entero.")

_EJEMPLO_PARCHE = (
    "Ejemplo (cambiar el título de una ventana y añadir un botón):\n"
    "CAMBIA:\n"
    "        return {\"en\": \"wifi\", \"titulo\": \"Mis redes\",\n"
    "POR:\n"
    "        return {\"en\": \"wifi\", \"titulo\": \"Redes de casa\",\n"
    "AÑADE DESPUÉS DE:\n"
    "                    {\"texto\": \"Redes guardadas\", \"orden\": \"redes guardadas\"},\n"
    "NUEVO:\n"
    "                    {\"texto\": \"Apaga la wifi\", \"orden\": \"apaga la wifi\"},")

SISTEMA_PARCHE = (
    "Eres el editor de mejoras de KiraOS. El usuario quiere CAMBIAR un módulo que YA existe (ves su «Código actual»). "
    "NO reescribas todo el módulo: cambia SOLO lo que haga falta. " + _FORMATO + "\n" + _EJEMPLO_PARCHE)

SISTEMA_PARCHE_LOCAL = (
    "Vas a CAMBIAR un módulo de Python que ya existe (ves su «Código actual»). NO reescribas todo. " + _FORMATO +
    "\n" + _EJEMPLO_PARCHE + "\nAhora escribe SOLO los cambios pedidos, con ese formato.")


def sistema_parche(local=True):
    return SISTEMA_PARCHE_LOCAL if local else SISTEMA_PARCHE
