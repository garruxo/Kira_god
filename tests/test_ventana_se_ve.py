# -*- coding: utf-8 -*-
"""v3.75: «crea un botón en la wifi / en el cuaderno…» — lo programaba pero NO se veía nada. El cerebro pequeño solía
escribir una orden normal sin «ventana …», así que no había nada que pintar. Ahora la ventana (solo datos) se arma
DIRECTAMENTE de la frase, pasa por el laboratorio de verdad, espera los dos toques y, al instalarla, SALE en la
pantalla. Si el cerebro escribe un módulo sin ventana, se rechaza y se dice."""
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["KIRA_DATA_DIR"] = T
os.environ["KIRA_DATOS_NUCLEO"] = T
os.environ["HOME"] = T
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import ventanas_kira as vk

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ---------- armar la ventana de la frase ----------
C = vk.construir
r = C("crea un botón en la ventana de WiFi que muestre las redes guardadas")
ok(r and r[2]["en"] == "wifi" and r[2]["botones"][0]["orden"] == "enséñame las redes guardadas", "botón en la WiFi")
r = C("en la ventana de la máquina pon un botón para encenderla")
ok(r and r[2]["en"] == "maquina" and r[2]["botones"][0]["orden"] == "enciende tu máquina", "botón en la máquina («encenderla»)")
r = C("crea un botón en el cuaderno llamado Resumen que me haga un resumen de lo pensado")
ok(r and r[2]["en"] == "cuaderno" and r[2]["titulo"] == "Resumen" and r[2]["botones"][0]["orden"] == "haz un resumen de lo pensado",
   "botón con nombre en el cuaderno")
r = C('ponte en el escritorio una ventana "Mi día" con tres botones: la hora, el tiempo y mis tareas')
ok(r and r[2]["en"] == "escritorio" and [b["texto"] for b in r[2]["botones"]] == ["La hora", "El tiempo", "Mis tareas"],
   "ventana del escritorio con varios botones")
r = C("crea en la wifi una sección con un botón que diga qué redes tengo guardadas")
ok(r and r[2].get("lugar") == "arriba", "una SECCIÓN sale como tarjeta dentro de la sala")
r = C("crea una ventana nueva con estas funciones: estudiar python, pensar, buscar noticias")
ok(r and [b["orden"] for b in r[2]["botones"]] == ["estudia python", "piensa", "busca noticias"], "funciones → botones")
ok(C("crea un botón en la wifi") is None, "sin decir qué hace: no se inventa nada (va al cerebro)")
ok(C("hola") is None, "lo que no es una ventana: nada")
for frase in ("crea un botón en la ventana de WiFi que muestre las redes guardadas",
              'ponte en el escritorio una ventana "Mi día" con tres botones: la hora, el tiempo y mis tareas'):
    nombre, codigo, datos = C(frase)
    d = {}
    exec(codigo, d)
    ok(vk.probar(d["registrar"]()) is None and vk.tiene_ventana(codigo), f"el módulo armado es válido: {nombre}")
ok(not vk.tiene_ventana('def registrar():\n    return {"redes": lambda t: "x"}'), "una orden normal NO es una ventana")

# ---------- de punta a punta con el núcleo, el laboratorio y la instalación de verdad ----------
import kira_god
import nucleo_portatil as npo
core = kira_god.KiraGodCore()
core.es_kiraos = True
pasos = []
r = npo.ejecutar(core, "crea un botón en la ventana de WiFi que muestre las redes guardadas", lambda f, t: pasos.append(t))
ok(r.get("ok") and "wifi" in r["texto"] and "dos toques" in r["texto"], "preparada y aprobada por el laboratorio: " + r["texto"][:120])
ok(core.ventanas_lista() == [], "…y NO se ha puesto sola")
res = npo.mejora_hacer(core, "aplicar", confirmado=True)
ok(res.get("ok") or res.get("aplicada") or "aplic" in str(res).lower() or "instal" in str(res).lower(), "tus dos toques: se instala")
lv = core.ventanas_lista()
ok(len(lv) == 1 and lv[0]["en"] == "wifi" and lv[0]["botones"][0]["orden"] == "enséñame las redes guardadas",
   f"y YA ESTÁ en la WiFi: {lv}")
r = npo.ejecutar(core, "crea un botón en el cuaderno llamado Resumen que me haga un resumen de lo pensado", lambda f, t: None)
npo.mejora_hacer(core, "aplicar", confirmado=True)
ok(any(v["en"] == "cuaderno" and v["titulo"] == "Resumen" for v in core.ventanas_lista()), "y en el Cuaderno también")

# la pantalla la recibe por el núcleo (la vuelve a validar)
import escritorio_kira as ek


class NucleoDeVerdad:
    def ventanas(self):
        return core.ventanas_lista()

    def estado(self):
        return {}


esc = ek.EscritorioMixin()
esc.cli = None
esc.nucleo_cli = NucleoDeVerdad()
ex = esc.barra()["extras"]
ok({"wifi", "cuaderno"} <= {x["en"] for x in ex}, f"la barra se las pasa a la pantalla: {ex}")

# ---------- si el cerebro escribe un módulo SIN ventana, no se guarda ----------


class PanelSinVentana:
    pendiente = type("P", (), {"codigo": 'def registrar():\n    return {"redes": lambda t: "x"}\n', "nombre": "redes"})()
    rechazada = False

    def probar_modulo(self, *a, **k):
        return {"aprobable": False, "texto": "no"}

    def enviar_orden(self, pedido, nombre=None, extra=""):
        return {"aprobable": True}

    def rechazar(self, motivo=""):
        PanelSinVentana.rechazada = True
        return {}


core2 = kira_god.KiraGodCore.__new__(kira_god.KiraGodCore)
core2._panel = PanelSinVentana()
r = npo.ejecutar(core2, "crea un botón en la wifi", lambda f, t: None)
ok(not r.get("ok") and "NINGUNA ventana" in r["texto"] and PanelSinVentana.rechazada,
   "el cerebro hizo una orden sin ventana: se rechaza y se dice cómo pedirlo")

# ---------- en la pantalla de verdad: sale en la WiFi y en el Cuaderno ----------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
try:
    from playwright.sync_api import sync_playwright
    import json
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        errores = []
        pg.on("pageerror", lambda e: errores.append(str(e)))
        pg.goto("file://" + html)
        pg.wait_for_timeout(700)
        pg.evaluate("x => { FAKE._extras = x; refrescaBarra(); }", ex)
        pg.wait_for_timeout(600)
        pg.evaluate("abrir('wifi')")
        pg.wait_for_timeout(600)
        ok(any("Enséñame" in t for t in pg.eval_on_selector_all("#vextras button", "l => l.map(x => x.textContent)")),
           "en la WiFi sale el botón nuevo arriba")
        pg.evaluate("abrir('cuaderno')")
        pg.wait_for_timeout(600)
        ok(any("Resumen" in t for t in pg.eval_on_selector_all("#vextras button", "l => l.map(x => x.textContent)")),
           "en el Cuaderno también")
        ok(not errores, f"sin errores JS: {errores}")
        b.close()
except ImportError:
    print("(sin playwright)")

print(f"\n{'TODO BIEN' if not fallos else str(fallos) + ' FALLOS'} ({n})")
sys.exit(1 if fallos else 0)
