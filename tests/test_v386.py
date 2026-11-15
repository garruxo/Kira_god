"""v3.86: visto en el Packard Bell: un programa salía con el nombre «274c0e1e2d4785a76ef7» y Kira intentó arrancar
.git/hooks/update.sample como si fuera el programa."""
import os, sys, stat, tempfile
sys.path[:0] = [os.path.join(os.path.dirname(__file__), ".."), os.path.join(os.path.dirname(__file__), "..", "kira_portatil")]
import apps_externas_kira as a

ok = mal = 0
def mira(c, t):
    global ok, mal
    if c: ok += 1
    else: mal += 1; print("FALLA:", t)

# nombres
for url, esperado in [
    ("https://github.com/yt-dlp/yt-dlp/tree/274c0e1e2d4785a76ef7", "yt dlp"),
    ("https://github.com/o/mi_juego/archive/274c0e1e2d4785a76ef7.zip", "mi juego"),
    ("https://codeload.github.com/o/repo/zip/refs/heads/main", "repo"),
    ("https://ejemplo.com/descargas/programa-1.2.3-linux.tar.gz", "programa"),
    ("https://ejemplo.com/Super_App.AppImage", "Super App"),
    ("o/r", "r"), ("https://github.com/o/r", "r"),
]:
    mira(a._nombre_de(url) == esperado, f"nombre {url} -> {a._nombre_de(url)!r}")
mira(not any(c in a._nombre_de("https://x.org/dl/274c0e1e2d4785a76ef7") for c in "0123456789"), "hash suelto")
# clonar siempre la raíz del repositorio
mira(a._url_github("https://github.com/o/r/tree/274c0e1e2d4785a76ef7") == "https://github.com/o/r.git", "url tree")
mira(a._url_github("https://github.com/o/r/commit/abc1234") == "https://github.com/o/r.git", "url commit")
mira(a._url_github("https://codeload.github.com/o/r/zip/refs/heads/main") == "https://github.com/o/r.git", "codeload")
mira(a.metodo("https://github.com/o/r/releases/download/v1/r.AppImage") == "appimage", "release appimage")
mira(a.metodo("https://github.com/o/r/releases/download/v1/r.tar.gz") == "descarga", "release tar")
mira(a.metodo("https://github.com/o/r") == "github", "repo github")

# lanzadores: nunca dentro de .git ni ejemplos
def ejecutable(p, txt="#!/bin/sh\necho hola\n"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(txt); os.chmod(p, 0o755)

with tempfile.TemporaryDirectory() as d:
    ejecutable(os.path.join(d, ".git", "hooks", "update.sample"))
    ejecutable(os.path.join(d, ".git", "hooks", "pre-commit"))
    open(os.path.join(d, "README.md"), "w").write("# Programa\n")
    mira(a.buscar_lanzador(d) is None, f"no coge .git: {a.buscar_lanzador(d)}")
    mira(a.como_arrancar(d) is None, "como_arrancar sin nada")
    ejecutable(os.path.join(d, "configure"))
    ejecutable(os.path.join(d, "algo.sample"))
    mira(a.como_arrancar(d) is None, f"configure/sample no son el programa: {a.como_arrancar(d)}")
    mira(a.buscar_lanzador(d) is None, f"buscar: configure no: {a.buscar_lanzador(d)}")
    ejecutable(os.path.join(d, "build", "miprograma"))
    r = a.buscar_lanzador(d)
    mira(r and r[0].endswith("miprograma"), f"encuentra el de verdad: {r}")
    ejecutable(os.path.join(d, "miprog"))
    mira(a.como_arrancar(d) == [os.path.join(d, "miprog")], "como_arrancar el de verdad")

print(f"test_v386: {ok} bien, {mal} mal")
sys.exit(1 if mal else 0)
