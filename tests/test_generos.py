# -*- coding: utf-8 -*-
"""Géneros de juego de nivel experto: se eligen por la frase, se cargan en modo seguro y se juegan de verdad (con
pilotos automáticos que comprueban que se puede ganar y que el rival hace daño). Si hay Chromium, también en la web."""
import math
import os
import sys
import tempfile
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ejecutor_kira as ej
import generos_juegos_kira as gj
import juego_realista_kira as jr
import juegos_kira as jk
import pintor_kira as pk
import programar_kira as prk
import sprites_kira as spk
import web_juegos_kira as w

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


for frase, g in [("carreras de coches", "carreras"), ("un juego de motos", "carreras"), ("plataformas de un ninja",
                 "plataformas"), ("naves espaciales contra marcianos", "naves"), ("combate de karate", "combate"),
                 ("lucha entre samuráis", "combate"), ("un comecocos retro", "retro"), ("laberinto", "retro"),
                 ("un caballero que esquiva dragones", "esquivar")]:
    ok(gj.genero_de(frase) == g, f"«{frase}» -> {g}")

planes = {}
for frase in ("carreras de motos en el desierto", "plataformas de un ninja en una cueva", "naves espaciales",
              "combate de karate", "retro"):
    p = jr.plan_simple(frase, pk.traducir_simple)
    planes[p["tipo"]] = p
    cod = jr.codigo(p)
    ok(ej.revisar(cod) is None, f"{p['tipo']}: pasa el modo seguro")
    g, e = jk.cargar(cod, semilla=1)
    ok(e is None, f"{p['tipo']}: se carga ({e})")
ok(planes["carreras"]["protagonista"] == "una moto de carreras" and planes["carreras"]["escenario"] == "desierto",
   "el vehículo y el sitio salen de la frase")
d = jr.dibujos(planes["carreras"])
ok("top-down" in d["jugador"] and "no shadow" in d["jugador"] and set(d) == {"fondo", "jugador", "enemigo", "premio"},
   "carreras: los coches se pintan vistos desde arriba")
ok("plataforma" in jr.dibujos(planes["plataformas"]) and "facing left" in jr.dibujos(planes["combate"])["enemigo"],
   "plataformas pide su plataforma; el rival mira hacia ti")
ok(jr.dibujos(planes["retro"]) == {}, "lo retro no necesita dibujos")
ok(jr.plan_desde_ia('{"tipo": "naves", "titulo": "X"}', "carreras de coches")["tipo"] == "carreras"
   and jr.plan_desde_ia('{"tipo": "naves", "titulo": "X"}', "una aventura")["tipo"] == "naves",
   "si la frase nombra el género, manda la frase; si no, lo que diga el cerebro")
ok(prk.pedido_programa("hazme un juego de carreras de coches") == "juego de carreras de coches",
   "«hazme un juego de carreras…» llega como juego (la interfaz lo manda a la plantilla)")
src = open(os.path.join(os.path.dirname(w.AQUI), os.path.basename(w.AQUI), "interfaz_kira.py"), encoding="utf-8").read()
ok("gj_.genero_de(prog) != \"esquivar\"" in src, "la interfaz usa la plantilla para «juego de <género>»")


def jugar(tipo, frames, piloto, semilla=1):
    g, _ = jk.cargar(jr.codigo(planes[tipo]), semilla=semilla)
    for i in range(frames):
        piloto(g, i)
        g.paso(1 / 60)
        if g.estado != "jugando":
            break
    return g


def piloto_carreras(g, i):
    if i % 6:
        return

    def peligro(c):
        return min([r.y for r in g.con_etiqueta("rival") if r.datos["carril"] == c and r.y > g.coche.y - 40] + [9999])
    if peligro(g.carril) < 330:
        g.carril = max((c for c in (g.carril - 1, g.carril + 1) if 0 <= c <= 2), key=peligro)


g = jugar("carreras", 60 * 200, piloto_carreras)
ok(g.estado == "ganado", f"carreras: un buen piloto llega a la meta ({g.marcador()[:50]})")
g = jugar("carreras", 60 * 200, lambda g, i: None)
ok(g.estado == "fin" and 0 < g.metros < 5000, "carreras: sin hacer nada, te estrellas")


def piloto_saltos(g, i):
    j = g.jugador
    pies = j.x + j.w * 0.75
    hueco = not [s for s in g.con_etiqueta("suelo") if s.x <= pies + 45 <= s.x + s.w]
    alto = [s for s in g.con_etiqueta("suelo") if s.x <= pies + 40 <= s.x + s.w and s.y + s.h > j.y + 5]
    enem = [e for e in g.con_etiqueta("enemigo") if 0 < e.x - j.x < 90]
    if g.en_suelo and (hueco or alto or enem):
        g.tocar(100, 300)
    elif not g.en_suelo and g.vy < -50 and g.saltos < 2 and not [
            s for s in g.con_etiqueta("suelo") if s.x <= pies + 30 <= s.x + s.w]:
        g.tocar(100, 300)


g = jugar("plataformas", 60 * 60, piloto_saltos)
ok(g.distancia > 4000 and g.puntos > 100, f"plataformas: se corre, se salta y se recogen monedas ({g.marcador()})")
g = jugar("plataformas", 60 * 60, lambda g, i: None)
ok(g.estado == "fin", "plataformas: sin saltar, te caes")
g = jugar("naves", 60 * 60 * 6, lambda g, i: (setattr(g, "invencible", 5), setattr(g, "dedo", (180 + 150 * math.sin(i / 40), 120))))
ok(g.estado == "ganado" and g.jefes_vencidos == 3, f"naves: hay oleadas y 3 jefes ({g.marcador()[:50]})")


def piloto_lucha(g, i):
    d, g.dedo = g.distancia(), None
    if g.p2.datos["golpe"] and d < 120 and i % 2 == 0:
        g.dedo = (4 + 2 * 71.2 + 30, 40)
    elif d > 70:
        g.dedo = (4 + 71.2 + 30, 40)
    elif i % 12 == 0:
        g.tocar(4 + 3 * 71.2 + 30, 40)
        g.dedo = None


g = jugar("combate", 60 * 300, piloto_lucha)
ok(g.estado == "ganado", f"combate: luchando bien se gana ({g.marcador()[:40]})")
g = jugar("combate", 60 * 300, lambda g, i: None)
ok(g.estado == "fin", "combate: si no haces nada, el rival te gana (ataca de verdad)")


def bfs(g):
    ini = g.casilla(g.pac["pos"])
    vis, q = {ini: None}, deque([ini])
    while q:
        c = q.popleft()
        if c in g.puntos_mapa and c != ini:
            while vis[c] != ini and vis[c] is not None:
                c = vis[c]
            return (c[0] - ini[0], ini[1] - c[1])
        for d_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + d_[0], c[1] - d_[1])
            if n not in vis and g.libre(*n):
                vis[n] = c
                q.append(n)


def come(g, i):
    g.vidas = 99
    d_ = bfs(g)
    if d_:
        g.pac["quiere"] = d_


g = jugar("retro", 60 * 600, come)
ok(g.estado == "ganado" and g.nivel == 3, "retro: se pueden limpiar los 3 laberintos")
g = jugar("retro", 60 * 120, lambda g, i: None)
ok(g.estado == "fin", "retro: los fantasmas persiguen y atrapan")

# ---------- recortar mejor los dibujos ----------
W = H = 40
px = bytearray()
for y in range(H):
    for x in range(W):
        if 10 <= x < 30 and 10 <= y < 30:
            px += bytes((200, 30, 30, 255))                     # el personaje
        elif 2 <= x < 5 and 33 <= y < 36:
            px += bytes((150, 150, 150, 255))                   # un resto de sombra suelto
        elif (x in (9, 30) and 10 <= y < 30) or (y in (9, 30) and 10 <= x < 30):
            px += bytes((235, 235, 232, 255))                   # halo blanquecino
        else:
            px += bytes((255, 255, 255, 255))
r, f = spk.quitar_fondo(W, H, px)
ok(r[(34 * W + 3) * 4 + 3] == 0, "los restos sueltos se quitan")
ok(r[(9 * W + 20) * 4 + 3] == 0 and r[(20 * W + 20) * 4 + 3] == 255, "el halo blanco se quita y el personaje queda")

# ---------- en el navegador ----------
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
if sync_playwright:
    with tempfile.TemporaryDirectory() as d, sync_playwright() as p:
        b = p.chromium.launch()
        for tipo, plan in planes.items():
            ruta = os.path.join(d, tipo + ".html")
            open(ruta, "w", encoding="utf-8").write(w.html_juego(jr.codigo(plan)))
            pg = b.new_page(locale="es-ES", viewport={"width": 390, "height": 760})
            errores = []
            pg.on("pageerror", lambda e: errores.append(str(e)))
            pg.goto("file://" + ruta)
            pg.wait_for_function("document.getElementById('marcador').textContent != 'Cargando…' || "
                                 "document.getElementById('aviso').textContent != ''", timeout=20000)
            for k in range(6):
                pg.mouse.click(60 + k * 50, 700)
                pg.wait_for_timeout(250)
            aviso = pg.inner_text("#aviso")
            ok(not aviso and not errores, f"{tipo}: se juega en el navegador" + (f": {aviso or errores[:1]}" if aviso or errores else ""))
            pg.close()
        b.close()

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
