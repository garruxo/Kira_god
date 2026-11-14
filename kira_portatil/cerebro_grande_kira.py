# -*- coding: utf-8 -*-
"""
cerebro_grande_kira.py — v3.45 (SOLO KiraOS): «aumenta tu cerebro».

El dueño: «como tiene bastante RAM, aumentar su cerebro… aunque vaya lento, que tenga un buen cerebro para hacerlo
bien». El Packard Bell tiene 8 GB: cabe el 4B (unos 3 GB) además del 2B. El servidor del cerebro (modo ligero) ya
usa el 4B como «grande» en cuanto el archivo está (pensar, programar, el taller del kernel, estudiar); charlar sigue
con el 2B. Esto solo lo DESCARGA (con reanudación, sin administrador, a ~/kira_portatil/modelos) y dice cómo va.
`abrir` se inyecta para probar sin internet.
"""
import os
import re
import shutil
import urllib.request

import servidor_portatil as sp

MODELOS = os.environ.get("KIRA_MODELOS") or os.path.expanduser("~/kira_portatil/modelos")


def _plano(t):
    import unicodedata
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip(" .!¡?¿")


def es_orden(texto):
    """'bajar' («aumenta/mejora/amplía tu cerebro», «descarga tu cerebro grande», «ponte el cerebro de 4B»),
    'estado' («qué cerebro tienes», «cómo va tu cerebro grande») o None."""
    t = re.sub(r"^(?:oye\s+|hola\s+)?kira\b[\s,:;]*", "", _plano(texto))
    if re.match(r"^(?:aumenta|amplia|agranda|mejora|sube|cambia)\s+(?:tu\s+|el\s+|de\s+)?cerebro(?:\s+(?:al|a)\s+(?:de\s+)?4\s*b)?$", t) \
            or re.match(r"^(?:descarga(?:te)?|baja(?:te)?|ponte|instalate|pon(?:te)?)\s+(?:tu\s+|el\s+)?cerebro\s+"
                        r"(?:grande|de\s+4\s*b|4\s*b|mas\s+grande|mas\s+listo)$", t) \
            or re.match(r"^(?:usa|ponte)\s+un\s+cerebro\s+mas\s+(?:grande|listo)$", t):
        return "bajar"
    if re.match(r"^(?:que|cual)\s+cerebros?\s+(?:tienes|usas)$|^como\s+va\s+(?:tu\s+|el\s+)?cerebro(?:\s+grande)?$", t):
        return "estado"
    return None


def objetivo(ram=None):
    cf, _ = sp.config(ligero=True, ram=ram)
    return cf["grande"], cf["rapido"]


def ruta(archivo, modelos=None):
    return os.path.join(modelos or MODELOS, archivo)


def estado(ram=None, modelos=None):
    g, r = objetivo(ram)
    ram_v = sp.ram_mb() if ram is None else ram
    tiene_g = os.path.isfile(ruta(g["archivo"], modelos))
    tiene_r = os.path.isfile(ruta(r["archivo"], modelos))
    if g["archivo"] == r["archivo"]:
        return (f"Tengo el cerebro 2B para todo. Con {ram_v} MB de RAM no cabe bien el 4B "
                f"(hacen falta unos {sp.RAM_PARA_GRANDE_MB} MB).")
    if tiene_g:
        return ("Tengo dos cerebros: el 2B para charlar (rápido) y el 4B para pensar, programar, estudiar y mi kernel "
                "(más lento, pero piensa mejor).")
    parte = ruta(g["archivo"], modelos) + ".part"
    hecho = os.path.getsize(parte) if os.path.isfile(parte) else 0
    return ("Ahora solo tengo el 2B" + ("" if tiene_r else " (y ni eso: falta instalarlo)") + ". Cabe el 4B (unos 3 GB): "
            "dime «aumenta tu cerebro» y lo descargo" + (f" (ya llevo {hecho // 1_000_000} MB)." if hecho else "."))


def descargar(al_paso=None, parar=None, abrir=None, ram=None, modelos=None, trozo=1 << 20):
    """Baja el 4B con reanudación. Devuelve el texto para decírtelo."""
    paso = al_paso or (lambda f, t: None)
    g, r = objetivo(ram)
    if g["archivo"] == r["archivo"]:
        return estado(ram, modelos)
    destino = ruta(g["archivo"], modelos)
    if os.path.isfile(destino):
        return "Ya tengo el cerebro 4B: lo uso para pensar, programar, estudiar y el kernel; para charlar, el 2B."
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    total = int(g.get("bytes") or 0)
    parte = destino + ".part"
    hecho = os.path.getsize(parte) if os.path.isfile(parte) else 0
    libre = shutil.disk_usage(os.path.dirname(destino)).free
    if total and libre < (total - hecho) + 500_000_000:
        return f"No tengo sitio: hacen falta unos {(total - hecho) // 1_000_000 + 500} MB libres en el disco."
    peticion = urllib.request.Request(g["url"], headers={"User-Agent": "KiraOS"})
    if hecho:
        peticion.add_header("Range", f"bytes={hecho}-")
    abrir = abrir or (lambda req: urllib.request.urlopen(req, timeout=60))
    paso(hecho / total if total else 0.0, "Descargo mi cerebro 4B…")
    try:
        resp = abrir(peticion)
    except Exception as e:                            # noqa: BLE001
        return f"No he podido empezar la descarga ({e}). Mira la conexión y vuelve a decirme «aumenta tu cerebro»."
    codigo = getattr(resp, "status", None) or getattr(resp, "code", 200)
    if hecho and codigo != 206:                       # el servidor no reanuda: desde el principio
        hecho = 0
    with open(parte, "ab" if hecho else "wb") as f:
        while True:
            if parar and parar():
                return (f"Paro la descarga (llevo {(hecho) // 1_000_000} MB). Cuando quieras, «aumenta tu cerebro» "
                        "y sigo donde lo dejé.")
            bloque = resp.read(trozo)
            if not bloque:
                break
            f.write(bloque)
            hecho += len(bloque)
            if total:
                paso(min(0.99, hecho / total), f"Descargo mi cerebro 4B: {hecho // 1_000_000} de {total // 1_000_000} MB")
    if total and hecho != total:
        return (f"La descarga se cortó ({hecho // 1_000_000} de {total // 1_000_000} MB). Dime otra vez «aumenta tu "
                "cerebro» y sigo donde lo dejé.")
    os.replace(parte, destino)
    paso(1.0, "Cerebro 4B listo")
    return ("¡Listo! Ya tengo el cerebro 4B. Desde ahora pienso, programo, estudio y trabajo en mi kernel con él: "
            "iré más lenta, pero lo haré mejor. Para charlar sigo usando el 2B, que es rápido. No hace falta reiniciar.")


def hacer(que, al_paso=None, parar=None, abrir=None):
    if que == "estado":
        return estado()
    return descargar(al_paso=al_paso, parar=parar, abrir=abrir)
