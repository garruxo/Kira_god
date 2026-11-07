# -*- coding: utf-8 -*-
"""v3.00: KiraOS también FUERA DE CASA por Tailscale (decisión del dueño). Fuera de casa el móvil SOLO se sincroniza y
ve qué hace KiraOS (Parar/Pausar/Seguir); las órdenes de trabajo siguen esperando a casa (decisión de la v2.88) y el
cerebro de la charla sigue siendo el del móvil. Aquí: un portátil de mentira que responde por la dirección de casa o
por la de Tailscale según toque."""
import io
import json
import os
import subprocess
import sys
import urllib.error

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import casa_kira as ck  # noqa: E402
import fuera_kira as fk  # noqa: E402
import tablero_kira as tbk  # noqa: E402

n = 0


def ok(c, m):
    global n
    n += 1
    print(("[OK] " if c else "[X] ") + m)
    if not c:
        sys.exit(1)


# ---------- el portátil: su dirección de Tailscale ----------
ok(fk.es_ip_tailscale("100.101.102.103") and not fk.es_ip_tailscale("192.168.18.19")
   and not fk.es_ip_tailscale("8.8.8.8") and not fk.es_ip_tailscale("hola"), "reconoce las direcciones de Tailscale")
ok(fk.ip_tailscale(correr=lambda a: (0, "100.101.102.103\n") if a[0] == "tailscale" else (1, "")) == "100.101.102.103",
   "averigua su dirección con «tailscale ip»")
ok(fk.ip_tailscale(correr=lambda a: (127, "") if a[0] == "tailscale" else
                   (0, "5: tailscale0    inet 100.70.1.2/32 scope global tailscale0")) == "100.70.1.2",
   "y si no está el comando, la mira en la interfaz tailscale0")
ok(fk.ip_tailscale(correr=lambda a: (1, "")) is None, "sin Tailscale: None (no inventa)")
ok("desactivado" in fk.texto_estado(correr=lambda a: (1, "")) and "activar_fuera" in fk.texto_estado(correr=lambda a: (1, "")),
   "sin Tailscale, la ventana Móvil explica cómo activarlo")
ok("ACTIVADO" in fk.texto_estado(correr=lambda a: (0, "100.101.102.103")), "con Tailscale, dice que está activado")

src_n = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok('"fuera_ip": _ip_fuera()' in src_n, "KiraOS da su dirección de Tailscale en /hola (para que el móvil la aprenda)")
src_e = open(os.path.join(RAIZ, "kira_portatil", "escritorio_kira.py"), encoding="utf-8").read()
ok("fuera_kira.texto_estado()" in src_e, "la ventana Móvil de KiraOS dice si fuera de casa está activado")

sh = os.path.join(RAIZ, "kira_portatil", "activar_fuera.sh")
txt = open(sh, encoding="utf-8").read()
ok(subprocess.run(["bash", "-n", sh]).returncode == 0, "activar_fuera.sh sin errores de sintaxis")
ok("tailscale up --qr" in txt and "allow in on tailscale0" in txt and "8770" in txt and "8771" in txt,
   "activar_fuera.sh: conecta con QR y abre los puertos SOLO en la red privada (tailscale0)")
ok(sorted(x for x in os.listdir(os.path.join(RAIZ, "kira_portatil")) if x.startswith("act")) == ["activar_fuera.sh"],
   "«bash act» + Tab lo completa sin dudas (no hay otro que empiece igual)")

# ---------- el móvil: casa, Tailscale o nada ----------
CASA, FUERA, TOKEN = "192.168.18.19", "100.101.102.103", "T" * 32
cfg = {"url": f"http://{CASA}:8766", "token": TOKEN, "portatil_url": f"http://{CASA}:8770"}
ck.pc.leer_config = lambda: dict(cfg)


def guardar(url, token, **extra):
    cfg.update({k: v for k, v in extra.items() if v is not None})


ck.pc.guardar_config = guardar
ck.buscar = lambda *a, **k: []                      # sin faro UDP en la prueba
red = {"casa": True, "fuera": True}
pedidos = []


class Resp(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def getheader(self, *_a):
        return "application/json"


def abrir(req, timeout=None):
    url = req.full_url
    host = url.split("//", 1)[1].split("/", 1)[0].split(":")[0]
    if (host == CASA and not red["casa"]) or (host == FUERA and not red["fuera"]) or host not in (CASA, FUERA):
        raise urllib.error.URLError("no llego")
    pedidos.append((host, url.split(host, 1)[1]))
    ruta = url.split(":", 2)[2].split("/", 1)[1] if url.count(":") >= 2 else ""
    ruta = "/" + ruta
    if ruta.startswith("/hola") and ":8770" in url:
        return Resp(json.dumps({"ok": True}).encode())
    if ruta.startswith("/hola"):
        return Resp(json.dumps({"kira_nucleo": 1, "fuera_ip": FUERA, "ocupada": True, "haciendo": "estudia Python",
                                "en_cola": 2, "pausada": False, "version": "3.00", "recuerdos": 5}).encode())
    if ruta.startswith("/pausar"):
        return Resp(json.dumps({"pausada": True}).encode())
    if ruta.startswith("/seguir"):
        return Resp(json.dumps({"pausada": False}).encode())
    if ruta.startswith("/estado"):
        return Resp(json.dumps({"ocupada": False, "en_cola": 0, "pausada": False}).encode())
    return Resp(b"{}")


reloj = [0.0]
c = ck.Casa(abrir=abrir, reloj=lambda: reloj[0])
ok(c.url_fuera == "", "al principio el móvil no sabe la dirección de fuera")
ok(c.nucleo_disponible() and c.via == "casa", "en casa: llega por la WiFi")
ok(cfg.get("portatil_fuera") == f"http://{FUERA}:8770", "y APRENDE la dirección de Tailscale de KiraOS")

# fuera de casa
red["casa"] = False
reloj[0] += 30
ok(not c.nucleo_disponible(), "fuera de casa, para TRABAJO (por defecto) no la ve: las órdenes esperan a casa")
ok(c.nucleo_disponible(fuera=True) and c.via == "fuera", "pero para sincronizar/ver la encuentra por Tailscale")
ok(c.nucleo_url == f"http://{FUERA}:8771", "y habla con el núcleo por la dirección de Tailscale")
ok(c.pausar_nucleo(True) is True and c.pausar_nucleo(False) is True, "Pausar y Seguir funcionan desde fuera")
ok(c.estado_nucleo() == {"ocupada": False, "en_cola": 0, "pausada": False}, "y ve el estado")
ok(any(h == FUERA and "8771/pausar" in r for h, r in pedidos), "(de verdad por la dirección de Tailscale)")

# ni casa ni Tailscale
red["fuera"] = False
reloj[0] += 30
ok(not c.nucleo_disponible(fuera=True), "sin casa ni Tailscale: no la ve (y no revienta)")

# vuelve a casa
red["casa"] = red["fuera"] = True
reloj[0] += 30
ok(c.nucleo_disponible() and c.via == "casa" and c.nucleo_url == f"http://{CASA}:8771", "al volver, otra vez por casa")

# solo se aprende una dirección de Tailscale de verdad
antes = cfg["portatil_fuera"]
c._aprender_fuera({"fuera_ip": "8.8.8.8"})
c._aprender_fuera({"fuera_ip": "192.168.1.5"})
c._aprender_fuera({})
ok(cfg["portatil_fuera"] == antes, "no se guarda una dirección que no sea de Tailscale (ni de internet ni de casa)")

# ---------- el núcleo del móvil: fuera = solo sincronía ----------
kg = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
sinc = kg.split("def sincronizar(self, al_paso=None, viajes=50):", 1)[1].split("\n    def ", 1)[0]
ok("nucleo_disponible(fuera=True)" in sinc and "ordenes_a_kiraos(fuera=fuera)" in sinc,
   "sincronizar: también por Tailscale; fuera de casa solo pasa las órdenes tranquilas (v3.02)")
vig = kg.split("def vigilar_casa(", 1)[1].split("\n    def ", 1)[0]
ok("conectada = en_casa or" in vig and "ordenes_a_kiraos(fuera=not en_casa)" in vig,
   "vigilar_casa: sincroniza fuera por Tailscale y pasa las órdenes tranquilas (v3.02)")
ok("def mando_listo" in kg and "nucleo_disponible(fuera" not in kg.split("def _mirar_mando", 1)[1].split("\n    def ", 1)[0],
   "el modo mando (trabajo en directo) sigue siendo solo en casa")

# ---------- el panel ----------
base = {"version": "3.00", "recuerdos": 5, "actividad": {}}
t = tbk.tarjeta_kiraos({"kiraos": dict(base, ocupada=True, haciendo="estudia Python", en_cola=2, via="fuera")})
ok("OCUPADA: estudia Python" in t["texto"] and "2 tarea(s) en espera" in t["texto"], "el panel enseña lo que hace y la cola")
ok("Tailscale" in t["texto"] and "tranquilo" in t["texto"], "y que está conectada por Tailscale (fuera de casa)")
ok(("Parar lo que hace", "parar_kiraos") in t["botones"] and ("Pausar", "pausar_kiraos") in t["botones"],
   "botones Parar y Pausar")
t = tbk.tarjeta_kiraos({"kiraos": dict(base, pausada=True)})
ok("EN PAUSA" in t["texto"] and t["botones"] == [("Seguir", "seguir_kiraos")], "en pausa: sale «Seguir»")
t = tbk.tarjeta_kiraos({"kiraos": dict(base, via="casa")})
ok("Tailscale" not in t["texto"], "en casa no habla de Tailscale")
t = tbk.tarjeta_kiraos({"kiraos": None})
ok("Tailscale" in t["texto"], "sin verla, dice que no está ni en casa ni por Tailscale")
itf = open(os.path.join(RAIZ, "interfaz_kira.py"), encoding="utf-8").read()
ok('"pausar_kiraos", "seguir_kiraos"' in itf and "pausar_nucleo(si)" in itf and "nucleo_disponible(fuera=True)" in itf,
   "la pantalla: busca por Tailscale para el panel y los botones Pausar/Seguir funcionan")

print("\nTODO BIEN", n)
