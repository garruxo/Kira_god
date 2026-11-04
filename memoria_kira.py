# -*- coding: utf-8 -*-
"""
memoria_kira.py - Pasar la MEMORIA de Kira de un sitio a otro (del móvil al portátil). VA EN EL APK; solo estándar.

Lo que Kira ha aprendido vive en su carpeta de datos (KIRA_DATA_DIR): el baúl de recuerdos, lo estudiado, su
cuaderno de pensamientos y soluciones, el foco, tus encargos, los experimentos, las mejoras aprobadas, las apps…
Esto lo EMPAQUETA en un .zip (en el móvil) y lo IMPORTA en otro sitio (en el portátil).

Qué NO viaja nunca (por seguridad o porque es de cada aparato): la clave de Claude (api_key.txt), la de GitHub
(github_token.txt), la conexión (pasarela.json), los modelos del cerebro/pintor/lector (pesan GB y cada equipo tiene
los suyos), registros, cachés, fotos/capturas y vídeos.

  empaquetar(dir_datos, "memoria.zip")      -> resumen {archivos, bytes, saltados}
  importar("memoria.zip", dir_datos)        -> resumen {archivos, respaldo}; guarda antes una copia de lo que había
"""
import json
import os
import shutil
import time
import zipfile

# Lo que viaja: archivos sueltos y carpetas enteras (dentro de la carpeta de datos)
ARCHIVOS = (
    "kira_memory.json", "kira_memoria.json", "kira_vocabulario_aprendido.json", "kira_diseno_conocimiento.json",
    "conocimiento.json", "ciber_aprendizaje.json", "estudio.json", "pensamientos.json", "pensar_sola.json",
    "foco.json", "preguntas_mias.json", "experimentos.json", "defensa.json", "notas.json", "auto_mejoras_hechas.json",
)
CARPETAS = ("recuerdos", "modulos", "apps", "entrenamiento", "pdf", "datos_modulos")
# Lo que NUNCA viaja aunque esté dentro de una carpeta que sí
NUNCA = ("api_key.txt", "github_token.txt", "pasarela.json", "token_lab.txt")
EXT_NUNCA = (".gguf", ".bin.part", ".parte", ".log", ".pid", ".tmp")
MAX_ARCHIVO = 60 * 1024 * 1024          # un PDF enorme no se lleva (avisa)
MAX_TOTAL = 400 * 1024 * 1024
MARCA = "kira_memoria.json"             # dentro del zip: de dónde viene y cuándo


class MemoriaError(ValueError):
    pass


def _permitido(rel):
    """¿Este nombre (relativo, con «/») puede viajar? Rechaza rutas absolutas, «..» y lo prohibido."""
    rel = str(rel or "").replace("\\", "/")
    if not rel or rel.startswith("/") or ":" in rel.split("/")[0]:
        return False
    partes = rel.split("/")
    if any(p in ("", ".", "..") for p in partes):
        return False
    base = partes[-1]
    if base in NUNCA or base.lower().endswith(EXT_NUNCA):
        return False
    if len(partes) == 1:
        return base in ARCHIVOS
    return partes[0] in CARPETAS


def _recorrer(dir_datos):
    """[(rel, ruta, bytes)] de lo que viajaría, en orden."""
    sal = []
    for nombre in ARCHIVOS:
        r = os.path.join(dir_datos, nombre)
        if os.path.isfile(r):
            sal.append((nombre, r, os.path.getsize(r)))
    for carpeta in CARPETAS:
        base = os.path.join(dir_datos, carpeta)
        if not os.path.isdir(base):
            continue
        for raiz, dirs, archivos in os.walk(base):
            dirs[:] = sorted(d for d in dirs if not os.path.islink(os.path.join(raiz, d)))
            for a in sorted(archivos):
                r = os.path.join(raiz, a)
                if os.path.islink(r) or not os.path.isfile(r):
                    continue
                rel = os.path.relpath(r, dir_datos).replace(os.sep, "/")
                if _permitido(rel):
                    sal.append((rel, r, os.path.getsize(r)))
    return sal


def empaquetar(dir_datos, destino, origen="móvil", max_total=MAX_TOTAL, max_archivo=MAX_ARCHIVO):
    """Mete en `destino` (.zip) todo lo que Kira ha aprendido. Devuelve {archivos, bytes, saltados:[(rel, motivo)]}."""
    total, n, saltados = 0, 0, []
    tmp = destino + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, ruta, tam in _recorrer(dir_datos):
            if tam > max_archivo:
                saltados.append((rel, f"muy grande ({tam // 1048576} MB)"))
                continue
            if total + tam > max_total:
                saltados.append((rel, "no cabe en el paquete"))
                continue
            try:
                z.write(ruta, rel)
            except OSError as e:
                saltados.append((rel, str(e)))
                continue
            total += tam
            n += 1
        z.writestr(MARCA, json.dumps({"origen": origen, "momento": int(time.time()), "archivos": n},
                                     ensure_ascii=False))
    os.replace(tmp, destino)
    return {"archivos": n, "bytes": total, "saltados": saltados}


def importar(zip_ruta, dir_datos, respaldo=True, max_total=MAX_TOTAL * 2):
    """Mete la memoria del .zip en `dir_datos`. Antes guarda lo que había (lo que se va a pisar) en
    antes_de_importar_<fecha>/. Rechaza cualquier nombre raro (rutas fuera, claves, modelos). Devuelve
    {archivos, origen, respaldo, rechazados}."""
    if not zipfile.is_zipfile(zip_ruta):
        raise MemoriaError("Eso no es un paquete de memoria (.zip).")
    os.makedirs(dir_datos, exist_ok=True)
    with zipfile.ZipFile(zip_ruta) as z:
        info = [i for i in z.infolist() if not i.is_dir()]
        if sum(i.file_size for i in info) > max_total:
            raise MemoriaError("El paquete es demasiado grande.")
        try:
            marca = json.loads(z.read(MARCA).decode("utf-8")) if MARCA in z.namelist() else {}
        except (KeyError, ValueError):
            marca = {}
        buenos = [i for i in info if i.filename != MARCA and _permitido(i.filename)]
        rechazados = [i.filename for i in info if i.filename != MARCA and not _permitido(i.filename)]
        if not buenos:
            raise MemoriaError("El paquete no trae nada que pueda importar.")
        destino_resp = None
        if respaldo:
            destino_resp = os.path.join(dir_datos, "antes_de_importar_" + time.strftime("%Y%m%d_%H%M%S"))
            tocados = {i.filename.split("/")[0] for i in buenos}
            for t in sorted(tocados):
                src = os.path.join(dir_datos, t)
                if os.path.exists(src):
                    os.makedirs(destino_resp, exist_ok=True)
                    if os.path.isdir(src):
                        shutil.copytree(src, os.path.join(destino_resp, t))
                    else:
                        shutil.copy2(src, os.path.join(destino_resp, t))
        # las carpetas que vienen se sustituyen enteras (así el baúl queda coherente con su llave)
        for c in sorted({i.filename.split("/")[0] for i in buenos if "/" in i.filename}):
            shutil.rmtree(os.path.join(dir_datos, c), ignore_errors=True)
        base = os.path.realpath(dir_datos)
        escritos = 0
        for i in buenos:
            final = os.path.realpath(os.path.join(dir_datos, *i.filename.split("/")))
            if not final.startswith(base + os.sep):
                rechazados.append(i.filename)
                continue
            os.makedirs(os.path.dirname(final), exist_ok=True)
            with z.open(i) as fuente, open(final + ".tmp", "wb") as f:
                shutil.copyfileobj(fuente, f)
            os.replace(final + ".tmp", final)
            escritos += 1
            try:
                os.chmod(final, 0o600)
            except OSError:
                pass
    return {"archivos": escritos,
            "origen": marca.get("origen", "?"), "momento": marca.get("momento"), "respaldo": destino_resp,
            "rechazados": rechazados}


def texto_resumen(r, accion="pasado"):
    mb = r.get("bytes")
    t = f"He {accion} {r.get('archivos', 0)} archivos de memoria" + (f" ({mb / 1048576:.1f} MB)" if mb else "") + "."
    if r.get("saltados"):
        t += " Me dejé " + ", ".join(f"{a} ({m})" for a, m in r["saltados"][:4]) + \
             ("…" if len(r["saltados"]) > 4 else "") + "."
    if r.get("respaldo"):
        t += " Lo que había antes quedó guardado aparte, por si acaso."
    return t
