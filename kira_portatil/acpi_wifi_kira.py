"""acpi_wifi_kira.py — lee las instrucciones de la BIOS (tablas ACPI ya desmontadas con iasl, archivos .dsl) y
busca QUÉ hace Linux para encender la radio WiFi del Packard Bell.

Lo que ya sabemos (v3.61–v3.63): al encender/apagar la WiFi en Xubuntu cambia el bit 0 del byte 0xBB del
controlador del portátil (EC), pero escribir ese bit desde el kernel de Kira NO enciende la radio. Así que el
método de la BIOS que usa Linux (acer-wmi) hace ALGO MÁS. Aquí:
  1. se buscan las zonas del EC (OperationRegion ... EmbeddedControl) y sus campos (Field) para saber cómo se
     LLAMA el campo que está en el byte 0xBB bit 0;
  2. se buscan los métodos que usan ese campo, y quién los llama (un nivel más arriba);
  3. se enseña su texto y se marcan las líneas que tocan otras cosas (GPIO del chipset, puertos, otros campos).
Es SOLO LECTURA de unos archivos de texto: no toca el portátil.

    python3 acpi_wifi_kira.py <carpeta con los .dsl> [byte] [bit]
"""
import os
import re
import sys

_REGION = re.compile(r"OperationRegion\s*\(\s*([\\\w.^]+)\s*,\s*(\w+)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)")
_FIELD = re.compile(r"\b(Field|IndexField|BankField)\s*\(([^)]*)\)")
_METODO = re.compile(r"\bMethod\s*\(\s*([\\\w.^]+)")
_NUM = {"zero": 0, "one": 1, "ones": 0xFFFFFFFF}


def numero(t):
    t = (t or "").strip()
    if t.lower() in _NUM:
        return _NUM[t.lower()]
    try:
        return int(t, 0)
    except ValueError:
        return None


def _bloque(texto, desde):
    """Texto entre la primera '{' a partir de `desde` y su '}' pareja (o '' si no la hay)."""
    i = texto.find("{", desde)
    if i < 0:
        return "", desde
    nivel = 0
    for j in range(i, len(texto)):
        c = texto[j]
        if c == "{":
            nivel += 1
        elif c == "}":
            nivel -= 1
            if nivel == 0:
                return texto[i + 1:j], j + 1
    return texto[i + 1:], len(texto)


def regiones(texto, espacio="EmbeddedControl"):
    """{nombre corto: desplazamiento} de las zonas de ese tipo (EmbeddedControl, SystemIO, SystemMemory…)."""
    r = {}
    for m in _REGION.finditer(texto):
        if m.group(2).lower() == espacio.lower():
            nombre = m.group(1).split(".")[-1].lstrip("\\^")
            r[nombre] = numero(m.group(3)) or 0
    return r


def campos(texto, espacio="EmbeddedControl"):
    """Lista de campos de las zonas de ese tipo: {nombre, region, byte, bit, bits}."""
    regs = regiones(texto, espacio)
    out = []
    for m in _FIELD.finditer(texto):
        if m.group(1) != "Field":
            continue
        reg = m.group(2).split(",")[0].strip().split(".")[-1].lstrip("\\^")
        if reg not in regs:
            continue
        cuerpo, _ = _bloque(texto, m.end())
        trozos = [t.strip() for t in cuerpo.replace("\n", " ").split(",")]
        pos = regs[reg] * 8
        i = 0
        while i < len(trozos):
            t = trozos[i]
            mo = re.match(r"Offset\s*\(\s*([^)]+)\)", t)
            if mo:
                v = numero(mo.group(1))
                if v is not None:
                    pos = regs[reg] * 8 + v * 8
                i += 1
                continue
            if t.startswith("AccessAs") or t.startswith(")"):
                i += 1
                continue
            if re.match(r"^[\w]{0,4}$", t) and i + 1 < len(trozos) and numero(trozos[i + 1]) is not None:
                bits = numero(trozos[i + 1])
                if t:
                    out.append({"nombre": t, "region": reg, "byte": pos // 8, "bit": pos % 8, "bits": bits})
                pos += bits
                i += 2
                continue
            i += 1
    return out


def campo_en(lista, byte, bit=0):
    """Campos que cubren ese byte y ese bit."""
    obj = byte * 8 + bit
    return [c for c in lista if c["byte"] * 8 + c["bit"] <= obj < c["byte"] * 8 + c["bit"] + c["bits"]]


def metodos(texto):
    """{nombre: cuerpo} de todos los métodos (nombre corto; si se repite, se juntan)."""
    r = {}
    for m in _METODO.finditer(texto):
        nombre = m.group(1).split(".")[-1].lstrip("\\^")
        cuerpo, _ = _bloque(texto, m.end())
        r[nombre] = (r.get(nombre, "") + "\n" + cuerpo) if nombre in r else cuerpo
    return r


def usan(mets, nombre):
    pat = re.compile(r"(?<![\w])" + re.escape(nombre) + r"(?![\w])")
    return [m for m, cuerpo in mets.items() if m != nombre and pat.search(cuerpo)]


_OTRAS = re.compile(r"\bGP\w*|\bGL\w*|\bGIO\w*|\bGPIO\w*|\bIO\w*|SystemIO|\bPWR\w*|\bWL\w*|\bRF\w*|\bBT\w*|\bW3G\w*")


def analizar(textos, byte=0xBB, bit=0):
    """textos = {archivo: texto .dsl}. Devuelve un diccionario con lo encontrado."""
    todo = "\n".join(textos.values())
    lista = campos(todo)
    elegidos = campo_en(lista, byte, bit)
    mets = metodos(todo)
    res = {"campos_ec": len(lista), "campo": elegidos, "metodos": [], "llamadores": [],
           "wmi": [m for m in mets if m in ("WMAA", "WMAB", "WMBA", "WMBB", "WMBC", "WMBD", "WMBE", "_WED")],
           "gpio_regiones": regiones(todo, "SystemIO"), "texto": {}}
    vistos = []
    for c in elegidos:
        for m in usan(mets, c["nombre"]):
            if m not in vistos:
                vistos.append(m)
    res["metodos"] = vistos
    llam = []
    for m in vistos:
        for q in usan(mets, m):
            if q not in vistos and q not in llam:
                llam.append(q)
    res["llamadores"] = llam
    for m in vistos + llam:
        res["texto"][m] = mets.get(m, "")
    return res


def _limpia(cuerpo, maximo=30):
    lineas = [l.rstrip() for l in cuerpo.splitlines() if l.strip() and l.strip() not in ("{", "}")]
    # quitar la sangría común
    sang = min((len(l) - len(l.lstrip()) for l in lineas), default=0)
    lineas = [l[sang:] for l in lineas]
    if len(lineas) > maximo:
        lineas = lineas[:maximo] + ["... (%d lineas mas en el informe)" % (len(lineas) - maximo)]
    return lineas


def texto(res, byte=0xBB, bit=0, maximo=30):
    out = []
    if not res["campos_ec"]:
        out.append("No he encontrado campos del controlador (EC) en las tablas ACPI.")
        return "\n".join(out)
    if not res["campo"]:
        out.append("Hay %d campos del EC, pero ninguno en el byte 0x%X bit %d." % (res["campos_ec"], byte, bit))
        return "\n".join(out)
    for c in res["campo"]:
        out.append("Campo del EC en 0x%X bit %d: %s (zona %s, %d bit%s)" % (
            byte, bit, c["nombre"], c["region"], c["bits"], "" if c["bits"] == 1 else "s"))
    out.append("Metodos que lo usan: " + (", ".join(res["metodos"]) or "ninguno"))
    out.append("Quien los llama: " + (", ".join(res["llamadores"]) or "nadie"))
    if res["wmi"]:
        out.append("Metodos WMI (los que usa acer-wmi): " + ", ".join(res["wmi"]))
    if res["gpio_regiones"]:
        out.append("Zonas de puertos (SystemIO): " + ", ".join("%s=0x%X" % (k, v) for k, v in res["gpio_regiones"].items()))
    nombres = {c["nombre"] for c in res["campo"]}
    for m in res["metodos"] + res["llamadores"]:
        out.append("")
        out.append("== %s ==" % m)
        for l in _limpia(res["texto"].get(m, ""), maximo):
            marca = "  "
            if any(re.search(r"(?<![\w])%s(?![\w])" % re.escape(n), l) for n in nombres):
                marca = "> "
            elif _OTRAS.search(l):
                marca = "* "
            out.append(marca + l)
    out.append("")
    out.append("(> = el bit de la WiFi del EC; * = otra cosa que puede encender la radio)")
    return "\n".join(out)


def leer_carpeta(carpeta):
    t = {}
    for n in sorted(os.listdir(carpeta)):
        if n.lower().endswith(".dsl"):
            try:
                t[n] = open(os.path.join(carpeta, n), encoding="utf-8", errors="replace").read()
            except OSError:
                pass
    return t


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    byte = int(argv[2], 0) if len(argv) > 2 else 0xBB
    bit = int(argv[3], 0) if len(argv) > 3 else 0
    textos = leer_carpeta(argv[1])
    if not textos:
        print("No hay archivos .dsl en " + argv[1])
        return 1
    print(texto(analizar(textos, byte, bit), byte, bit, maximo=10000 if os.environ.get("KIRA_TODO") else 30))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
