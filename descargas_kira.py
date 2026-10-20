# -*- coding: utf-8 -*-
"""
descargas_kira.py - Descargar archivos grandes (modelos) con REANUDACIÓN: si se corta, sigue donde se quedó.
Lo usan el pintor (y lo puede usar cualquier pieza nueva). Solo librería estándar.
"""
import os
import shutil
import urllib.request

MARGEN_DISCO = 300 * 1024 * 1024
TROZO = 1024 * 1024


class DescargaError(RuntimeError):
    pass


def abrir_https(req, timeout=60):
    import red_kira
    return red_kira.abrir(req, timeout=timeout)


def bajar(url, final, total, nombre="el archivo", abrir=abrir_https, progreso=None, cancelado=None):
    """Descarga 'url' en 'final' (pasa por final + '.parte'). total = bytes esperados (comprueba que llegan todos);
    None = los que diga el servidor. progreso(fraccion, bajados, total). cancelado() -> True para pausar.
    Devuelve 'final'. Lanza DescargaError."""
    carpeta = os.path.dirname(final) or "."
    os.makedirs(carpeta, exist_ok=True)
    if os.path.isfile(final) and (total is None or os.path.getsize(final) == total):
        return final
    parcial = final + ".parte"
    ya = os.path.getsize(parcial) if os.path.isfile(parcial) else 0
    if total is not None and ya > total:
        os.remove(parcial)
        ya = 0
    libre = shutil.disk_usage(carpeta).free
    if total is not None and libre < (total - ya) + MARGEN_DISCO:
        raise DescargaError(f"No hay espacio: hacen falta {(total - ya + MARGEN_DISCO) / 1e9:.1f} GB libres y hay "
                            f"{libre / 1e9:.1f} GB.")
    req = urllib.request.Request(url, headers={"User-Agent": "KiraApp/1.0", **({"Range": f"bytes={ya}-"} if ya else {})})
    try:
        with abrir(req, timeout=60) as r:
            if ya and getattr(r, "status", 200) != 206:          # el servidor no reanuda: se empieza de cero
                ya = 0
            if total is None:
                try:
                    total = ya + int(r.headers.get("Content-Length"))
                except (TypeError, ValueError, AttributeError):
                    total = None
            with open(parcial, "ab" if ya else "wb") as f:
                bajados = ya
                while True:
                    if cancelado is not None and cancelado():
                        raise DescargaError("Descarga pausada. Pulsa otra vez para seguir donde se quedó.")
                    trozo = r.read(TROZO)
                    if not trozo:
                        break
                    f.write(trozo)
                    bajados += len(trozo)
                    if progreso:
                        progreso(min(1.0, bajados / max(1, total or bajados)), bajados, total)
    except DescargaError:
        raise
    except Exception as e:
        raise DescargaError(f"La descarga de {nombre} se cortó ({e}). Vuelve a pulsar: seguirá donde se quedó.")
    tam = os.path.getsize(parcial)
    if total is not None and tam != total:
        raise DescargaError(f"La descarga de {nombre} no está completa ({tam / 1e6:.0f} de {total / 1e6:.0f} MB). "
                            "Vuelve a pulsar para seguir.")
    os.replace(parcial, final)
    return final
