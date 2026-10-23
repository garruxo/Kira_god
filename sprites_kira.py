# -*- coding: utf-8 -*-
"""
sprites_kira.py - Los DIBUJOS de los juegos (gráficos realistas pintados por el pintor de Kira).

  - leer_png / escribir_png: PNG de 8 bits (RGB o RGBA) en Python puro (en el móvil no hay librerías de imagen).
  - quitar_fondo: los personajes se pintan sobre un fondo liso; aquí ese fondo se vuelve TRANSPARENTE (se rellena
    desde los bordes lo que se parece al color del borde), y el personaje queda recortado.
  - reducir: los personajes se guardan a 256 px (en el juego se ven pequeños y así cargan rápido).
  - dibujos_de(codigo): lee del programa qué hay que pintar (atributos «sprites» y «dibujos» del juego).
Lógica pura (sin Kivy): se prueba en el PC.
"""
import ast
import os
import re
import struct
import zlib

FIRMA = b"\x89PNG\r\n\x1a\n"


class SpriteError(RuntimeError):
    pass


def carpeta_base():
    return os.path.join(os.environ.get("KIRA_DATA_DIR") or os.path.expanduser("~"), "sprites")


def nombre_valido(n):
    n = re.sub(r"[^a-z0-9_]+", "_", str(n or "").lower()).strip("_")[:40]
    return n


def ruta(carpeta, nombre):
    return os.path.join(carpeta_base(), nombre_valido(carpeta) or "juego", nombre_valido(nombre) + ".png")


# =====================================================================================
#  PNG en Python puro
# =====================================================================================
def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def leer_png(datos):
    """(ancho, alto, bytearray RGBA) de un PNG de 8 bits RGB/RGBA sin entrelazar."""
    if datos[:8] != FIRMA:
        raise SpriteError("no es un PNG")
    i, idat, cab = 8, [], None
    while i < len(datos):
        n = struct.unpack(">I", datos[i:i + 4])[0]
        tipo = datos[i + 4:i + 8]
        cuerpo = datos[i + 8:i + 8 + n]
        if tipo == b"IHDR":
            cab = struct.unpack(">IIBBBBB", cuerpo)
        elif tipo == b"IDAT":
            idat.append(cuerpo)
        elif tipo == b"IEND":
            break
        i += 12 + n
    if cab is None:
        raise SpriteError("PNG sin cabecera")
    w, h, prof, tipo_color, _c, _f, entrelazado = cab
    if prof != 8 or tipo_color not in (2, 6) or entrelazado:
        raise SpriteError("solo PNG de 8 bits RGB o RGBA")
    canales = 3 if tipo_color == 2 else 4
    crudo = zlib.decompress(b"".join(idat))
    fila = w * canales
    salida = bytearray(w * h * 4)
    previa = bytearray(fila)
    pos = 0
    for y in range(h):
        filtro = crudo[pos]
        linea = bytearray(crudo[pos + 1:pos + 1 + fila])
        pos += 1 + fila
        if filtro == 1:
            for x in range(canales, fila):
                linea[x] = (linea[x] + linea[x - canales]) & 255
        elif filtro == 2:
            for x in range(fila):
                linea[x] = (linea[x] + previa[x]) & 255
        elif filtro == 3:
            for x in range(fila):
                izq = linea[x - canales] if x >= canales else 0
                linea[x] = (linea[x] + ((izq + previa[x]) >> 1)) & 255
        elif filtro == 4:
            for x in range(fila):
                izq = linea[x - canales] if x >= canales else 0
                arr_izq = previa[x - canales] if x >= canales else 0
                linea[x] = (linea[x] + _paeth(izq, previa[x], arr_izq)) & 255
        elif filtro != 0:
            raise SpriteError(f"filtro PNG desconocido ({filtro})")
        base = y * w * 4
        if canales == 4:
            salida[base:base + w * 4] = linea
        else:
            salida[base:base + w * 4:4] = linea[0::3]
            salida[base + 1:base + w * 4:4] = linea[1::3]
            salida[base + 2:base + w * 4:4] = linea[2::3]
            salida[base + 3:base + w * 4:4] = b"\xff" * w
        previa = linea
    return w, h, salida


def escribir_png(w, h, rgba):
    """PNG RGBA de 8 bits."""
    filas = b"".join(b"\x00" + bytes(rgba[y * w * 4:(y + 1) * w * 4]) for y in range(h))

    def trozo(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
    return FIRMA + trozo(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + \
        trozo(b"IDAT", zlib.compress(filas, 6)) + trozo(b"IEND", b"")


# =====================================================================================
#  REDUCIR Y QUITAR EL FONDO
# =====================================================================================
def reducir(w, h, rgba, lado=256):
    """Reduce (promediando bloques) para que el lado mayor mida como mucho 'lado'."""
    f = 1
    while max(w, h) // f > lado:
        f += 1
    if f == 1:
        return w, h, bytearray(rgba)
    nw, nh = w // f, h // f
    salida = bytearray(nw * nh * 4)
    n = f * f
    for y in range(nh):
        for x in range(nw):
            s0 = s1 = s2 = s3 = 0
            for dy in range(f):
                base = ((y * f + dy) * w + x * f) * 4
                for dx in range(f):
                    j = base + dx * 4
                    s0 += rgba[j]
                    s1 += rgba[j + 1]
                    s2 += rgba[j + 2]
                    s3 += rgba[j + 3]
            k = (y * nw + x) * 4
            salida[k], salida[k + 1], salida[k + 2], salida[k + 3] = s0 // n, s1 // n, s2 // n, s3 // n
    return nw, nh, salida


def color_del_borde(w, h, rgba):
    """El color más repetido del borde (redondeado), que es el del fondo liso."""
    cuenta = {}
    for x in range(w):
        for y in (0, h - 1):
            j = (y * w + x) * 4
            c = (rgba[j] >> 4, rgba[j + 1] >> 4, rgba[j + 2] >> 4)
            cuenta[c] = cuenta.get(c, 0) + 1
    for y in range(h):
        for x in (0, w - 1):
            j = (y * w + x) * 4
            c = (rgba[j] >> 4, rgba[j + 1] >> 4, rgba[j + 2] >> 4)
            cuenta[c] = cuenta.get(c, 0) + 1
    c = max(cuenta, key=cuenta.get)
    return tuple(v * 16 + 8 for v in c)


def quitar_fondo(w, h, rgba, tolerancia=48):
    """Vuelve transparente el fondo liso que rodea al personaje (relleno desde los bordes). Devuelve rgba nuevo y
    la fracción quitada (si es casi todo o casi nada, el fondo no era liso)."""
    rgba = bytearray(rgba)
    fr, fg, fb = color_del_borde(w, h, rgba)
    tol2 = tolerancia * tolerancia * 3

    claro = fr + fg + fb > 600                          # fondo blanco: también vale el blanco grisáceo de las sombras

    def parecido(j):
        r, g, b = rgba[j], rgba[j + 1], rgba[j + 2]
        dr, dg, db = r - fr, g - fg, b - fb
        if dr * dr + dg * dg + db * db <= tol2:
            return True
        return claro and min(r, g, b) > 232 and max(r, g, b) - min(r, g, b) < 10
    visto = bytearray(w * h)
    pila = [y * w + x for x in range(w) for y in (0, h - 1)] + [y * w + x for y in range(h) for x in (0, w - 1)]
    quitados = 0
    while pila:
        i = pila.pop()
        if visto[i]:
            continue
        visto[i] = 1
        if not parecido(i * 4):
            continue
        rgba[i * 4 + 3] = 0
        quitados += 1
        x, y = i % w, i // w
        if x > 0:
            pila.append(i - 1)
        if x < w - 1:
            pila.append(i + 1)
        if y > 0:
            pila.append(i - w)
        if y < h - 1:
            pila.append(i + w)
    if claro:                                           # el halo blanquecino pegado al dibujo (2 pasadas)
        for _ in range(2):
            quitar = []
            for i in range(w * h):
                j = i * 4
                if rgba[j + 3] == 0:
                    continue
                r, g, b = rgba[j], rgba[j + 1], rgba[j + 2]
                if min(r, g, b) < 200 or max(r, g, b) - min(r, g, b) > 28:
                    continue
                x, y = i % w, i // w
                if (x > 0 and rgba[j - 1] == 0) or (x < w - 1 and rgba[j + 7] == 0) or \
                        (y > 0 and rgba[j - w * 4 + 3] == 0) or (y < h - 1 and rgba[j + w * 4 + 3] == 0):
                    quitar.append(j)
            for j in quitar:
                rgba[j + 3] = 0
            quitados += len(quitar)
    quitados += quitar_islas(w, h, rgba)
    # borde suave: lo que toca lo quitado queda medio transparente (sin dientes de sierra)
    for i in range(w * h):
        if rgba[i * 4 + 3] == 0:
            continue
        x, y = i % w, i // w
        vecinos = [j for j in ((i - 1) if x > 0 else -1, (i + 1) if x < w - 1 else -1,
                                (i - w) if y > 0 else -1, (i + w) if y < h - 1 else -1) if j >= 0]
        if any(rgba[j * 4 + 3] == 0 for j in vecinos) and parecido(i * 4) is False:
            rgba[i * 4 + 3] = 170
    return rgba, quitados / float(w * h)


def quitar_islas(w, h, rgba, minimo=0.12):
    """Quita los trocitos sueltos (restos de sombra o de fondo) que no están unidos al dibujo principal: se quedan
    las partes de al menos un 12 % del tamaño de la mayor. Cambia rgba; devuelve cuántos píxeles quitó."""
    grupo = [0] * (w * h)
    tam = [0]
    for inicio in range(w * h):
        if grupo[inicio] or rgba[inicio * 4 + 3] == 0:
            continue
        n = len(tam)
        tam.append(0)
        grupo[inicio] = n
        pila = [inicio]
        while pila:
            i = pila.pop()
            tam[n] += 1
            x, y = i % w, i // w
            for v in ((i - 1) if x > 0 else -1, (i + 1) if x < w - 1 else -1, (i - w) if y > 0 else -1,
                      (i + w) if y < h - 1 else -1):
                if v >= 0 and not grupo[v] and rgba[v * 4 + 3]:
                    grupo[v] = n
                    pila.append(v)
    if len(tam) <= 2:
        return 0
    corte = max(tam) * minimo
    quitados = 0
    for i in range(w * h):
        if grupo[i] and tam[grupo[i]] < corte:
            rgba[i * 4 + 3] = 0
            quitados += 1
    return quitados


def preparar_sprite(origen, destino, fondo=False, lado=256):
    """Del PNG que pinta el pintor al dibujo del juego: reducido y, si es un personaje, sin fondo.
    Devuelve un texto corto de lo hecho."""
    with open(origen, "rb") as f:
        w, h, rgba = leer_png(f.read())
    if not fondo:
        w, h, rgba = reducir(w, h, rgba, lado)
        rgba, quitado = quitar_fondo(w, h, rgba)
        nota = f"fondo quitado ({quitado * 100:.0f} %)"
        if quitado > 0.97 or quitado < 0.03:            # no era un fondo liso: mejor sin recortar
            with open(origen, "rb") as f:
                w, h, rgba = leer_png(f.read())
            w, h, rgba = reducir(w, h, rgba, lado)
            nota = "sin recortar (el fondo no era liso)"
    else:
        w, h, rgba = reducir(w, h, rgba, 640)
        nota = "escenario"
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    tmp = destino + ".tmp"
    with open(tmp, "wb") as f:
        f.write(escribir_png(w, h, rgba))
    os.replace(tmp, destino)
    return nota


# =====================================================================================
#  QUÉ DIBUJOS PIDE UN JUEGO
# =====================================================================================
def dibujos_de(codigo):
    """(carpeta, {nombre: descripción}) leídos del programa SIN ejecutarlo: los atributos «sprites» y «dibujos» de
    la clase del juego (o variables del módulo con ese nombre). ('', {}) si no tiene."""
    try:
        arbol = ast.parse(codigo)
    except SyntaxError:
        return "", {}
    carpeta, dibujos = "", {}

    def mirar(cuerpo):
        nonlocal carpeta, dibujos
        for n in cuerpo:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                nombre = n.targets[0].id
                try:
                    valor = ast.literal_eval(n.value)
                except (ValueError, SyntaxError):
                    continue
                if nombre == "sprites" and isinstance(valor, str):
                    carpeta = valor
                elif nombre == "dibujos" and isinstance(valor, dict):
                    dibujos = {str(k): str(v) for k, v in valor.items() if isinstance(v, str) and str(k).strip()}
    mirar(arbol.body)
    for n in arbol.body:
        if isinstance(n, ast.ClassDef):
            mirar(n.body)
    return nombre_valido(carpeta), {nombre_valido(k): v[:300] for k, v in list(dibujos.items())[:8] if nombre_valido(k)}
