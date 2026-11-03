# -*- coding: utf-8 -*-
"""
app_web_kira.py — convierte un PROGRAMA cualquiera de Kira en una APP WEB instalable (un solo .html, sin internet,
sin compilar). Lo pidió el dueño (v2.79): «que pueda hacer app de verdad, que ahora solo hace maquetas» → eligió
«app web instalable (sin compilar)».

Reusa toda la maquinaria de `web_juegos_kira` (Brython + stdlib metidos dentro del .html, VFS, escapado). La página
ejecuta el programa Python con Brython y muestra lo que imprime (`print`) en pantalla; se puede «añadir a la pantalla
de inicio» como los juegos (AppsKira). Pura (sin Kivy): se prueba sin pantalla.
"""
import json

import web_juegos_kira as wj

WebError = wj.WebError


def titulo_de(codigo, por_defecto="Programa de Kira"):
    import re
    m = re.search(r"#\s*(?:titulo|t[ií]tulo)\s*[:=]\s*(.{1,60})", codigo or "")
    if m:
        return m.group(1).strip()
    m = re.search(r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", codigo or "", re.M)
    return (m.group(1).replace("_", " ").strip().capitalize() if m else por_defecto)


def biblioteca_para(codigo):
    """'stdlib_base.js' o 'stdlib_ampliada.js' según lo que importe el programa (WebError si usa algo que no va)."""
    mods = wj.importaciones(codigo)
    raros = sorted(mods - wj.AMPLIADA)
    if raros:
        raise WebError("El programa usa " + ", ".join(f"«{r}»" for r in raros) + ", que todavía no funciona en la "
                       "versión web. Puede usar: " + ", ".join(sorted(wj.AMPLIADA - {"motor_juegos_kira"})) + ".")
    return "stdlib_base.js" if mods <= wj.BASE else "stdlib_ampliada.js"


def nombre_archivo(titulo):
    import re
    t = re.sub(r"[^a-z0-9]+", "_", wj._plano(titulo)).strip("_")[:40]
    return (t or "app") + ".html"


def html_app(codigo, titulo=None):
    """La página completa (un solo .html, sin internet) que EJECUTA este programa y muestra lo que imprime."""
    codigo = str(codigo or "").strip("\n") + "\n"
    if len(codigo.strip()) < 5:
        raise WebError("No hay programa que convertir en app.")
    wj.importaciones(codigo)                       # valida que no tenga errores de escritura (SyntaxError -> WebError)
    lib = biblioteca_para(codigo)
    titulo = titulo or titulo_de(codigo)
    modulos = {"$timestamp": 1, "programa_kira": [".py", codigo, sorted(wj.importaciones(codigo))]}
    return (PLANTILLA
            .replace("@@TITULO@@", _esc(titulo))
            .replace("@@BRYTHON@@", wj._js(wj._leer("brython.js")))
            .replace("@@STDLIB@@", wj._js(wj._leer(lib)))
            .replace("@@MODULOS@@", wj._js(json.dumps(modulos, ensure_ascii=False))))


def _esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


PLANTILLA = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0f172a">
<title>@@TITULO@@</title>
<style>
html,body{margin:0;min-height:100%;background:#0f172a;color:#e2e8f0;font-family:Roboto,system-ui,sans-serif}
#arriba{display:flex;align-items:center;gap:8px;padding:10px 12px;position:sticky;top:0;background:#0f172a}
#titulo{flex:1;font-size:16px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
button{background:#334155;color:#fff;border:0;border-radius:8px;padding:8px 12px;font-size:14px}
#salida{white-space:pre-wrap;word-break:break-word;padding:12px 14px;font-family:ui-monospace,Menlo,Consolas,monospace;
  font-size:14px;line-height:1.5}
</style>
<script>window.__BRYTHON__ = {brython_path: location.href.split("#")[0].split("?")[0].replace(/[^\/]*$/, "")};</script>
<script>@@BRYTHON@@</script>
<script>@@STDLIB@@</script>
<script>__BRYTHON__.update_VFS(@@MODULOS@@);</script>
</head><body onload="brython(1)">
<div id="arriba"><div id="titulo">@@TITULO@@</div><button onclick="location.reload()">Reiniciar</button></div>
<div id="salida"></div>
<script type="text/python">
import sys, traceback
from browser import document

class _Salida:
    def write(self, t):
        document["salida"].text += str(t)
    def flush(self):
        pass

sys.stdout = _Salida()
sys.stderr = _Salida()
try:
    import programa_kira
except Exception as e:
    document["salida"].text += "\n[se paró] " + "".join(traceback.format_exception_only(type(e), e))
</script>
</body></html>
"""
