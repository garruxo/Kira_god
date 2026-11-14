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


# ---------- v3.45: estudio A FONDO («ingeniería inversa» de su propio portátil, solo leyendo) ----------
SYS_PCI = "/sys/bus/pci/devices"
SYS_MOD = "/sys/module"
ESTUDIO = os.environ.get("KIRA_ESTUDIO_DRIVERS", os.path.expanduser("~/kira_portatil/kernel/estudio"))
# el código ABIERTO de Linux de cada driver (para aprender cómo habla con su chip): lo que le sirve al kernel de Kira
FUENTES_LINUX = {
    "tg3": ["drivers/net/ethernet/broadcom/tg3.h", "drivers/net/ethernet/broadcom/tg3.c"],
    # v3.46: la WiFi Atheros AR9287 (168c:002e) del Packard Bell: ath9k NO necesita firmware cerrado; esto es lo que
    # hace falta para despertar el chip, leer su EEPROM (MAC, país, calibración), las tablas de la radio y recibir.
    "ath9k": ["drivers/net/wireless/ath/ath9k/reg.h", "drivers/net/wireless/ath/ath9k/hw.h",
              "drivers/net/wireless/ath/ath9k/mac.h", "drivers/net/wireless/ath/ath9k/eeprom.h",
              "drivers/net/wireless/ath/ath9k/eeprom_9287.c", "drivers/net/wireless/ath/ath9k/ar9287_initvals.h",
              "drivers/net/wireless/ath/ath9k/ar9002_phy.h", "drivers/net/wireless/ath/ath9k/ar9002_hw.c",
              "drivers/net/wireless/ath/ath9k/hw.c"],
    "ahci": ["drivers/ata/ahci.h"],
    "e1000e": ["drivers/net/ethernet/intel/e1000e/regs.h", "drivers/net/ethernet/intel/e1000e/defines.h"],
    "e1000": ["drivers/net/ethernet/intel/e1000/e1000_hw.h"],
    "snd_hda_intel": ["include/sound/hda_register.h"],
    "ehci-pci": ["drivers/usb/host/ehci.h"], "ehci_pci": ["drivers/usb/host/ehci.h"],
    "r8169": ["drivers/net/ethernet/realtek/r8169_main.c"],
}
MAX_FUENTE = 2_000_000


def recursos_pci(slot, raiz=SYS_PCI):
    """Las zonas de memoria/puertos que Linux le dio a la pieza (lo que un driver usa para hablar con ella)."""
    fuera = []
    try:
        with open(os.path.join(raiz, slot, "resource"), encoding="ascii") as f:
            for i, linea in enumerate(f):
                partes = linea.split()
                if len(partes) < 3:
                    continue
                ini, fin, flags = (int(x, 16) for x in partes[:3])
                if ini == 0 and fin == 0:
                    continue
                fuera.append({"bar": i, "inicio": hex(ini), "tam": fin - ini + 1,
                              "tipo": "puertos" if flags & 0x100 else "memoria"})
    except (OSError, ValueError):
        pass
    irq = ""
    try:
        with open(os.path.join(raiz, slot, "irq"), encoding="ascii") as f:
            irq = f.read().strip()
    except OSError:
        pass
    return {"zonas": fuera[:7], "irq": irq}


def parametros_modulo(mod, raiz=SYS_MOD):
    d = {}
    carpeta = os.path.join(raiz, mod.replace("-", "_"), "parameters")
    try:
        for n in sorted(os.listdir(carpeta))[:30]:
            try:
                with open(os.path.join(carpeta, n), encoding="utf-8", errors="replace") as f:
                    d[n] = f.read().strip()[:80]
            except OSError:
                continue
    except OSError:
        pass
    return d


def registro_kernel(driver, correr=None, maximo=12):
    """Lo que Linux apuntó al arrancar sobre ese driver (journalctl -k; si no deja, dmesg)."""
    correr = correr or _correr
    texto = _seguro(correr, ["journalctl", "-k", "-b", "-q", "--no-pager"]) or _seguro(correr, ["dmesg"])
    pat = re.compile(r"\b" + re.escape(driver.replace("_", "-")) + r"\b|\b" + re.escape(driver) + r"\b", re.I)
    return [l.strip()[:200] for l in texto.splitlines() if pat.search(l)][-maximo:]


def version_linux(nucleo):
    m = re.match(r"^(\d+)\.(\d+)", str(nucleo or ""))
    return f"v{m.group(1)}.{m.group(2)}" if m else "master"


def resumen_fuente(texto):
    """Puro: de un archivo de Linux saca lo que sirve para escribir un driver: los REGISTROS (#define … 0x…)."""
    regs = re.findall(r"^#define\s+([A-Z][A-Z0-9_]{2,})\s+(0x[0-9a-fA-F]+)\b", texto or "", re.M)
    return {"lineas": (texto or "").count("\n"), "registros": len(regs), "ejemplos": [f"{n} = {v}" for n, v in regs[:12]]}


def estudiar_codigo(driver, nucleo="", abrir=None, carpeta=None):
    """Baja el código abierto de Linux de ese driver (por la puerta de investigar: la máquina virtual en KiraOS) y lo
    deja en ~/kira_portatil/kernel/estudio/<driver>/ con un resumen. Solo LEE: nada se ejecuta."""
    rutas = FUENTES_LINUX.get(driver) or FUENTES_LINUX.get(driver.replace("-", "_"))
    if not rutas:
        return {"ok": False, "texto": f"Aún no sé dónde está el código de «{driver}» dentro de Linux."}
    if abrir is None:
        try:
            import red_kira
            abrir = red_kira.abrir_investigar
        except Exception:
            abrir = None
    if abrir is None:
        import urllib.request
        abrir = lambda req, timeout=60: urllib.request.urlopen(req, timeout=timeout)    # noqa: E731
    import urllib.request
    dest = os.path.join(carpeta or ESTUDIO, re.sub(r"[^A-Za-z0-9_.-]", "_", driver))
    os.makedirs(dest, exist_ok=True)
    tag, hechos = version_linux(nucleo), []
    for r in rutas:
        url = f"https://raw.githubusercontent.com/torvalds/linux/{tag}/{r}"
        try:
            resp = abrir(urllib.request.Request(url, headers={"User-Agent": "KiraOS"}), timeout=60)
            datos = resp.read(MAX_FUENTE + 1)
        except Exception as e:                        # noqa: BLE001
            hechos.append({"archivo": r, "error": str(e)[:120]})
            continue
        if len(datos) > MAX_FUENTE:
            datos = datos[:MAX_FUENTE]
        texto_f = datos.decode("utf-8", "replace")
        with open(os.path.join(dest, os.path.basename(r)), "w", encoding="utf-8") as f:
            f.write(texto_f)
        hechos.append(dict(resumen_fuente(texto_f), archivo=r))
    buenos = [h for h in hechos if "error" not in h]
    lineas = [f"Código de Linux ({tag}) del driver «{driver}», guardado en {dest}:"]
    for h in hechos:
        lineas.append(f"• {h['archivo']}: " + (f"no lo pude bajar ({h['error']})" if "error" in h else
                                               f"{h['lineas']} líneas, {h['registros']} registros del chip"
                                               + (" (p. ej. " + ", ".join(h["ejemplos"][:4]) + ")" if h["ejemplos"] else "")))
    with open(os.path.join(dest, "resumen.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    return {"ok": bool(buenos), "texto": "\n".join(lineas), "carpeta": dest, "archivos": hechos}


def a_fondo(informe, correr=None, raiz_pci=SYS_PCI, raiz_mod=SYS_MOD):
    """Añade a cada pieza sus zonas de memoria/puertos, su interrupción, los ajustes de su driver y lo que Linux
    apuntó de ella al arrancar."""
    for p in informe.get("pci", []):
        p.update(recursos_pci("0000:" + p["slot"] if p["slot"].count(":") == 1 else p["slot"], raiz_pci))
        drv = p.get("driver")
        if drv:
            p["parametros"] = parametros_modulo(drv, raiz_mod)
            p["registro"] = registro_kernel(drv, correr)
    informe["a_fondo"] = True
    return informe


def es_orden_fondo(texto_):
    """«haz ingeniería inversa (del portátil / de linux / de la red)», «estudia a fondo tu hardware»,
    «estudia el código del driver X», «estudia el driver de tu red (por cable)» → ('fondo', driver|'') o None."""
    t = str(texto_ or "").lower().strip(" .¡!¿?")
    t = t.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    t = re.sub(r"^(?:oye\s+|hola\s+)?kira\b[\s,:;]*", "", t)
    m = re.match(r"^(?:estudia|lee|aprende)\s+(?:el\s+)?codigo\s+(?:del\s+driver|del\s+controlador|de)\s+([a-z0-9_-]+)$", t)
    if m:
        return ("fondo", m.group(1))
    if re.search(r"\b(?:estudia|aprende)\b.*\bdriver\b.*\bred\b.*\bcable\b|\b(?:estudia|aprende)\s+(?:el\s+)?driver\s+de\s+"
                 r"(?:tu|la)\s+red(?:\s+por\s+cable)?$", t):
        return ("fondo", "red")
    if re.search(r"\bingenieria\s+inversa\b", t) or re.match(r"^estudia\s+a\s+fondo\s+(?:tu|el)\s+(?:hardware|portatil)", t):
        return ("fondo", "")
    return None


def hacer_fondo(core=None, driver="", correr=None, al_paso=None, abrir=None):
    """Estudio a fondo: el hardware con sus recursos + el código de Linux de los drivers que importan."""
    paso = al_paso or (lambda f, t: None)
    inf = estudiar(correr, lambda f, t: paso(f * 0.4, t))
    if not inf.get("pci"):
        return {"texto": texto(inf), "informe": inf}
    paso(0.45, "Miro las zonas de memoria, las interrupciones y los ajustes de cada driver…")
    a_fondo(inf, correr)
    guardar(inf)
    if driver == "red":
        objetivos = [p.get("driver") for p in inf["pci"] if p.get("clase_id") == "0200" and p.get("driver")]
    elif driver:
        objetivos = [driver]
    else:
        objetivos = [p.get("driver") for p in inf["pci"] if p.get("driver") in FUENTES_LINUX]
    objetivos = [d for i, d in enumerate(objetivos) if d and d not in objetivos[:i]]
    trozos = []
    for i, d in enumerate(objetivos):
        paso(0.5 + 0.45 * i / max(1, len(objetivos)), f"Leo el código de Linux del driver «{d}»…")
        r = estudiar_codigo(d, inf.get("nucleo_linux", ""), abrir=abrir)
        trozos.append(r["texto"])
        rec = getattr(core, "recuerdos", None)
        if rec is not None and r.get("ok"):
            try:
                rec.guardar(r["texto"][:1500], tema=f"driver {d} (código de Linux)", fuente="hardware")
            except Exception:
                pass
    rec = getattr(core, "recuerdos", None)
    if rec is not None:
        for p in inf["pci"]:
            if p.get("zonas") or p.get("registro"):
                t = (f"{p['que_es']} {p['nombre']} [{p['id']}]: zonas " +
                     ", ".join(f"{z['tipo']} {z['inicio']} ({z['tam']} bytes)" for z in p.get("zonas", [])[:3]) +
                     (f"; interrupción {p['irq']}" if p.get("irq") else "") +
                     ("; Linux dijo: " + " | ".join(p["registro"][-3:]) if p.get("registro") else ""))
                try:
                    rec.guardar(t[:1500], tema=f"hardware a fondo: {p['que_es']}", fuente="hardware")
                except Exception:
                    pass
    lin = [texto(inf), "", "A FONDO (zonas de memoria y puertos de cada pieza, sus interrupciones y lo que Linux "
           "apuntó al arrancar) — guardado en mi baúl y en hardware.json."]
    lin += trozos or ["(No había drivers cuyo código sepa buscar todavía.)"]
    lin.append("Todo leído, nada tocado. Con esto puedo preparar los drivers de mi kernel del pendrive.")
    try:
        import avisos_kira as av
        av.prioritario("He estudiado a fondo tu portátil y el código de sus drivers. Ya puedo preparar el siguiente "
                       "driver de mi kernel del pendrive.", titulo="Ingeniería inversa terminada")
    except Exception:
        pass
    return {"texto": "\n".join(lin), "informe": inf}


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
