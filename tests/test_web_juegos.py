# -*- coding: utf-8 -*-
"""Tus juegos como app: la orden, la página web (Brython dentro) y, si hay Chromium, que se juegue de verdad."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import juegos_kira as jk
import web_juegos_kira as w

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


# ---------- la orden ----------
for f, esperado in [("Kira, conviértelo en una app", "app"), ("convierte el juego en una app", "app"),
                    ("haz una app del juego", "app"), ("pon el juego en la pantalla de inicio", "inicio"),
                    ("ponlo en el inicio", "inicio"), ("exporta el juego a web", "web"),
                    ("guarda el juego como página web", "web"), ("conviértelo en una app de verdad", "apk"),
                    ("hazme una app de recetas", None), ("diséñame una app de tareas", None),
                    ("hazme un juego de coches", None), ("crea una app", None), ("pon música", None)]:
    ok(w.pedido_app(f) == esperado, f"«{f}» -> {esperado}")

src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "interfaz_kira.py"),
           encoding="utf-8").read()
i = src.index("wj_.pedido_app(orden)")
ok(i < src.index("ex_.pedido_experimento(orden)") < src.index("pk_.pedido_programa(orden)")
   < src.index("dk_.pedido_diseno(orden)"), "la orden de app se mira antes que programas, experimentos y diseños")
ok('"kira_juego"' in src and "AppsKira" in src, "el icono abre Kira en ese juego (extra kira_juego)")
java = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "android_src", "org", "kira",
                         "servicio", "AppsKira.java"), encoding="utf-8").read()
ok("->" not in java and "requestPinShortcut" in java, "AppsKira.java: sin lambdas y con icono fijado")

# ---------- la página ----------
ok(w.biblioteca_para(jk.JUEGOS[0]["codigo"]) == "stdlib_base.js", "un juego con math/random lleva la biblioteca pequeña")
ok(w.biblioteca_para("import collections\nfrom motor_juegos_kira import Juego\n") == "stdlib_ampliada.js",
   "con collections, la ampliada")
try:
    w.biblioteca_para("import sqlite3\n")
    ok(False, "sqlite3 debería avisar")
except w.WebError as e:
    ok("sqlite3" in str(e), "un módulo que no va en la web se dice claro")
ok(w.titulo_de(jk.JUEGOS[0]["codigo"]) == "Rompeladrillos" and w.nombre_archivo("¡Pong contra Kira!") == "pong_contra_kira.html",
   "título y nombre de archivo")
pagina = w.html_juego(jk.JUEGOS[0]["codigo"], {"heroe": b"\x89PNG\r\n\x1a\nxx"})
ok(pagina.startswith("<!DOCTYPE html>") and "Rompeladrillos" in pagina and "data:image/png;base64," in pagina,
   "la página lleva el juego y sus dibujos")
cuerpo = pagina.split("<body>", 1)[1]
ok(cuerpo.count("</script>") == cuerpo.count("<script"), "nada cierra un <script> antes de tiempo")
ok(len(pagina) < 2_500_000, f"la página pesa {len(pagina) // 1024} KB (sin internet)")
try:
    w.html_juego("print('hola')")
    ok(False, "un programa que no es juego debería avisar")
except w.WebError:
    ok(True, "un programa que no es un juego no se convierte")
with tempfile.TemporaryDirectory() as d:
    open(os.path.join(d, "heroe.png"), "wb").write(b"\x89PNG..")
    open(os.path.join(d, "notas.txt"), "w").write("x")
    ok(list(w.dibujos_png(d)) == ["heroe"] and w.dibujos_png(os.path.join(d, "no")) == {}, "dibujos de la carpeta")

# ---------- jugar de verdad en Chromium (si está) ----------
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
if sync_playwright is None:
    print("[i] Sin playwright: no pruebo la página en un navegador.")
else:
    with tempfile.TemporaryDirectory() as d, sync_playwright() as p:
        b = p.chromium.launch()
        for j in jk.JUEGOS:
            ruta = os.path.join(d, j["id"] + ".html")
            open(ruta, "w", encoding="utf-8").write(w.html_juego(j["codigo"]))
            pg = b.new_page(locale="es-ES", viewport={"width": 390, "height": 760})
            errores = []
            pg.on("pageerror", lambda e: errores.append(str(e)))
            pg.goto("file://" + ruta)
            pg.wait_for_function("document.getElementById('marcador').textContent != 'Cargando…' || "
                                 "document.getElementById('aviso').textContent != ''", timeout=20000)
            pg.mouse.move(195, 600)
            pg.mouse.down()
            pg.mouse.move(80, 600, steps=6)
            pg.mouse.up()
            pg.wait_for_timeout(600)
            aviso = pg.inner_text("#aviso")
            ok(not aviso and not errores, f"«{j['titulo']}» se juega en el navegador ({pg.inner_text('#marcador')[:40]})"
               + (f": {aviso or errores[:1]}" if aviso or errores else ""))
            pg.close()
        malo = jk.PLANTILLA.replace("def actualizar(self, dt):", "def actualizar(self, dt):\n        1 / 0")
        ruta = os.path.join(d, "malo.html")
        open(ruta, "w", encoding="utf-8").write(w.html_juego(malo))
        pg = b.new_page(locale="es-ES")
        pg.goto("file://" + ruta)
        pg.wait_for_function("document.getElementById('aviso').textContent != ''", timeout=20000)
        ok("ZeroDivisionError" in pg.inner_text("#aviso") and "línea" in pg.inner_text("#aviso"), "si el juego falla, la página lo dice (con la línea): " + pg.inner_text("#aviso"))
        b.close()

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
