# -*- coding: utf-8 -*-
"""
hardware_kira.py — v3.44 (SOLO KiraOS): Kira ESTUDIA el hardware del portátil y los programas de control
(drivers) que usa Xubuntu para cada pieza.

Lo pidió el dueño: «antes tiene que ser capaz Kira de estudiar todo el sistema Xubuntu, y los drivers y
controladores del Packard Bell, para luego mandar un mensaje prioritario».

SOLO LECTURA y sin administrador: lspci -nnk, lsusb, lsmod, modinfo, uname, /sys. No carga ni quita drivers,
no toca nada. Lo que aprende:
  * se guarda como fichas en el baúl (una por pieza),
  * se guarda entero en ~/kira_portatil/hardware.json (0600) — es lo que hace falta para escribir los drivers
    del kernel de Kira (el número exacto de cada chip),
  * y dice, pieza a pieza, si el kernel de Kira ya la sabe manejar o qué le faltaría.
Al acabar deja un AVISO PRIORITARIO (avisos_kira) para el dueño.
`correr` se inyecta para poder probarlo.
"""
import json
import os
import re
import subprocess
import time

RUTA = os.environ.get("KIRA_HARDWARE", os.path.expanduser("~/kira_portatil/hardware.json"))

# clase PCI (4 cifras hex) → qué es, en palabras
CLASES = {
    "0100": "controlador de disco SCSI", "0101": "controlador de disco IDE", "0104": "controlador RAID",
    "0106": "controlador de disco SATA (AHCI)", "0108": "disco NVMe", "0200": "red por cable",
    "0280": "red inalámbrica (WiFi)", "0300": "tarjeta gráfica", "0380": "tarjeta gráfica",
    "0403": "sonido", "0401": "sonido", "0480": "multimedia", "0600": "puente del procesador",
    "0601": "puente ISA (teclado, reloj…)", "0604": "puente PCI", "0700": "puerto serie",
    "0780": "comunicaciones", "0805": "lector de tarjetas SD", "0880": "periférico del sistema",
    "0c03": "controlador USB", "0c05": "bus SMBus (sensores)", "0d11": "Bluetooth",
    "1180": "sensores", "ff00": "otro",
}

# lo que el kernel de Kira ya sabe hacer, por pieza (lo que se comprueba es honesto: si no está aquí, no lo sabe)
_KIRA_POR_ID = {"8086:100e": "sí: driver e1000 (etapa 8 y 15)"}
_KIRA_POR_CLASE = {
    "0106": "sí: leer el disco y su ext4 (etapas 9 y 10, solo lectura)",
    "0101": "sí: disco IDE/ATA (etapa 7)",
    "0300": "en parte: solo modo texto (VGA), sin gráficos",
    "0380": "en parte: solo modo texto (VGA), sin gráficos",
    "0600": "no hace falta driver", "0604": "no hace falta driver",
    "0601": "sí: teclado PS/2, temporizador y reloj por los puertos clásicos",
}
# qué le faltaría y cómo de difícil es (lo dice tal cual al dueño)
_FALTA_POR_CLASE = {
    "0200": "no todavía: es lo SIGUIENTE (red por cable, posible)",
    "0280": "no: WiFi necesita el driver + todo el sistema WiFi y WPA2 (muy difícil)",
    "0c03": "no: USB necesita su propio sistema (difícil)",
    "0403": "no: sonido (posible más adelante)",
    "0401": "no: sonido (posible más adelante)",
}


def _correr(args, timeout=20):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _seguro(correr, args):
    try:
        rc, s = correr(args)
        return s if rc == 0 else ""
    except Exception:
        return ""


def leer_lspci(texto):
    """Puro: la salida de `lspci -nnk` → [{slot, clase, clase_id, nombre, id, subsistema, driver, modulos, rev}]."""
    piezas, act = [], None
    for linea in (texto or "").splitlines():
        if not linea.strip():
            continue
        if not linea[0].isspace():
            m = re.match(r"^(\S+)\s+(.*?)\s*\[([0-9a-fA-F]{4})\]:\s*(.*?)\s*\[([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\]"
                         r"(?:\s*\(rev\s*([0-9a-fA-F]+)\))?", linea)
            if not m:
                act = None
                continue
            act = {"slot": m.group(1), "clase": m.group(2), "clase_id": m.group(3).lower(),
                   "nombre": m.group(4), "id": m.group(5).lower(), "rev": m.group(6) or "",
                   "subsistema": "", "driver": "", "modulos": []}
            piezas.append(act)
        elif act is not None:
            l = linea.strip()
            if l.lower().startswith("subsystem:"):
                act["subsistema"] = l.split(":", 1)[1].strip()
            elif l.lower().startswith("kernel driver in use:"):
                act["driver"] = l.split(":", 1)[1].strip()
            elif l.lower().startswith("kernel modules:"):
                act["modulos"] = [x.strip() for x in l.split(":", 1)[1].split(",") if x.strip()]
    return piezas


def leer_lsusb(texto):
    """Puro: `lsusb` → [{id, nombre}] (sin los «hubs» de raíz, que no dicen nada)."""
    out = []
    for linea in (texto or "").splitlines():
        m = re.match(r"^Bus\s+\d+\s+Device\s+\d+:\s+ID\s+([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\s*(.*)$", linea.strip())
        if m and "root hub" not in m.group(2).lower():
            out.append({"id": m.group(1).lower(), "nombre": m.group(2).strip()})
    return out


def leer_modinfo(texto):
    """Puro: `modinfo` → {descripcion, archivo, licencia, firmware:[…], version}."""
    d = {"descripcion": "", "archivo": "", "licencia": "", "firmware": [], "version": ""}
    for linea in (texto or "").splitlines():
        if ":" not in linea:
            continue
        k, v = linea.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "description":
            d["descripcion"] = v
        elif k == "filename":
            d["archivo"] = v
        elif k == "license":
            d["licencia"] = v
        elif k == "firmware":
            d["firmware"].append(v)
        elif k == "version":
            d["version"] = v
    return d


def para_kira(pieza):
    """Puro: ¿el kernel de Kira sabe manejar esta pieza? → texto corto y honesto."""
    if pieza.get("id") in _KIRA_POR_ID:
        return _KIRA_POR_ID[pieza["id"]]
    c = pieza.get("clase_id", "")
    if c in _KIRA_POR_CLASE:
        return _KIRA_POR_CLASE[c]
    return _FALTA_POR_CLASE.get(c, "no")


def que_es(pieza):
    return CLASES.get(pieza.get("clase_id", ""), pieza.get("clase", "") or "pieza")


def estudiar(correr=None, al_paso=None):
    """Mira todo (solo lectura). Devuelve el informe como dict."""
    correr = correr or _correr
    paso = al_paso or (lambda f, t: None)
    paso(0.05, "Miro las piezas de dentro (PCI)…")
    pci = leer_lspci(_seguro(correr, ["lspci", "-nnk"]))
    paso(0.25, "Miro lo que hay enchufado por USB…")
    usb = leer_lsusb(_seguro(correr, ["lsusb"]))
    paso(0.35, "Miro qué drivers tiene cargados Xubuntu…")
    cargados = []
    for linea in _seguro(correr, ["lsmod"]).splitlines()[1:]:
        if linea.split():
            cargados.append(linea.split()[0])
    nucleo = _seguro(correr, ["uname", "-r"]).strip()
    drivers = {}
    nombres = sorted({p["driver"] for p in pci if p.get("driver")} |
                     {m for p in pci for m in p.get("modulos", [])})
    for i, nom in enumerate(nombres):
        paso(0.4 + 0.5 * i / max(1, len(nombres)), f"Estudio el driver «{nom}»…")
        drivers[nom] = leer_modinfo(_seguro(correr, ["modinfo", nom]))
    for p in pci:
        p["que_es"] = que_es(p)
        p["kira"] = para_kira(p)
        info = drivers.get(p.get("driver") or (p["modulos"][0] if p.get("modulos") else ""), {})
        p["driver_info"] = info.get("descripcion", "")
        p["firmware"] = info.get("firmware", [])
    paso(0.95, "Lo ordeno…")
    return {"cuando": time.strftime("%Y-%m-%d %H:%M"), "nucleo_linux": nucleo, "pci": pci, "usb": usb,
            "drivers": drivers, "cargados": len(cargados)}


def guardar(informe, ruta=None):
    ruta = ruta or RUTA
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(informe, f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o600)
    os.replace(tmp, ruta)
    return ruta


def cargar(ruta=None):
    try:
        with open(ruta or RUTA, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def fichas(informe):
    """Puro: una ficha por pieza para el baúl → [(tema, texto)]."""
    out = []
    for p in informe.get("pci", []):
        t = (f"En mi portátil hay {p['que_es']}: {p['nombre']} (número de chip {p['id']}"
             + (f", revisión {p['rev']}" if p.get("rev") else "") + "). ")
        if p.get("driver"):
            t += f"Xubuntu lo maneja con el driver «{p['driver']}»"
            t += f" ({p['driver_info']})." if p.get("driver_info") else "."
        else:
            t += "Xubuntu no tiene ningún driver cargado para esta pieza."
        if p.get("firmware"):
            t += " Necesita firmware: " + ", ".join(p["firmware"][:4]) + "."
        t += f" ¿Mi kernel la sabe manejar? {p['kira']}."
        out.append((f"hardware: {p['que_es']}", t))
    if informe.get("usb"):
        out.append(("hardware: USB", "Enchufado por USB: " +
                    "; ".join(f"{u['nombre']} ({u['id']})" for u in informe["usb"][:12]) + "."))
    return out


def texto(informe):
    """Puro: el resumen para el dueño."""
    pci = informe.get("pci", [])
    if not pci:
        return ("No he podido ver las piezas del portátil (falta la orden «lspci»). "
                "Instálala con «sudo apt install pciutils» en la Terminal y vuelve a decirme «estudia tu hardware».")
    sabe = [p for p in pci if p["kira"].startswith("sí")]
    parte = [p for p in pci if p["kira"].startswith("en parte")]
    falta = [p for p in pci if p["kira"].startswith("no") and "no hace falta" not in p["kira"]]
    lin = [f"He estudiado tu portátil: {len(pci)} piezas por dentro y {len(informe.get('usb', []))} por USB "
           f"(Linux {informe.get('nucleo_linux') or '?'})."]
    for p in pci:
        if p["clase_id"] in ("0600", "0604", "0c05", "0880"):
            continue
        lin.append(f"• {p['que_es']}: {p['nombre']} [{p['id']}] — driver de Xubuntu: "
                   f"{p.get('driver') or 'ninguno'}. Mi kernel: {p['kira']}.")
    lin.append(f"Mi kernel ya maneja {len(sabe)}, a medias {len(parte)}, y le faltan {len(falta)}.")
    lin.append("Lo he guardado en mi baúl y entero en ~/kira_portatil/hardware.json.")
    return "\n".join(lin)


def aviso(informe):
    """Puro: el texto del AVISO PRIORITARIO."""
    red = next((p for p in informe.get("pci", []) if p.get("clase_id") == "0200"), None)
    t = "Ya he estudiado tu portátil y sus drivers. "
    if red:
        t += (f"Tu red por cable es «{red['nombre']}» [{red['id']}], con el driver «{red.get('driver') or '?'}» "
              "de Xubuntu: es lo siguiente para mi kernel. ")
    t += "Cuando quieras, dime y preparamos el pendrive."
    return t


def es_orden(texto_):
    """«estudia tu hardware», «estudia los drivers (del portátil)», «estudia tus controladores», «qué piezas
    tienes», «estudia todo el sistema xubuntu / todo tu sistema», «tu hardware» → True o None."""
    t = str(texto_ or "").lower().strip(" .¡!¿?")
    t = t.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    if re.search(r"\b(?:estudia|analiza|mira|revisa|conoce|aprende)\b.*\b(?:hardware|drivers?|controladores?|"
                 r"piezas|componentes)\b", t):
        return True
    if re.search(r"\b(?:estudia|analiza|conoce)\b\s+(?:todo\s+)?(?:el\s+|tu\s+)?(?:sistema\s+)?"
                 r"(?:xubuntu|packard\s*bell|portatil)\b", t):
        return True
    if re.search(r"\bestudia\s+todo\s+(?:el|tu)\s+sistema\b", t):
        return True
    if re.match(r"^(?:tu\s+hardware|que\s+(?:piezas|drivers|controladores)\s+tienes)$", t):
        return True
    return None


def hacer(core=None, correr=None, al_paso=None, ruta=None, avisar=True):
    """Estudia, guarda (archivo + baúl) y deja el aviso prioritario. Devuelve {"texto", "informe"}."""
    inf = estudiar(correr, al_paso)
    if inf.get("pci"):
        guardar(inf, ruta)
        rec = getattr(core, "recuerdos", None)
        if rec is not None:
            for tema, t in fichas(inf):
                try:
                    rec.guardar(t, tema=tema, fuente="hardware")
                except Exception:
                    pass
        if avisar:
            try:
                import avisos_kira as av
                av.prioritario(aviso(inf), titulo="Kira ha estudiado tu portátil")
            except Exception:
                pass
    return {"texto": texto(inf), "informe": inf}
