# -*- coding: utf-8 -*-
"""v3.74: KiraOS le ENCARGA diseños (icono, logo, fondo, salvapantallas, tema, ventanas) a la Kira del móvil; el móvil
los hace, se los manda en la sincronía y KiraOS los enseña ANTES de aplicarlos (visto bueno del dueño)."""
import base64
import os
import struct
import sys
import tempfile
import zlib

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp()
os.environ["KIRA_SISTEMA"] = os.path.join(T, "sistema.json")
os.environ["KIRA_AVISOS"] = os.path.join(T, "avisos.json")
os.environ["KIRA_DATOS_NUCLEO"] = os.path.join(T, "k")
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")

import disenos_kira as dz
import recuerdos_kira as rk
import sincronia_kira as sc
import sistema_kira as sis

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


def png(color=(10, 200, 240)):
    fila = b"\x00" + bytes(color) * 4
    raw = zlib.compress(fila * 4)

    def trozo(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0)) + trozo(b"IDAT", raw) + \
        trozo(b"IEND", b"")


# ---------------------------------------------------------------- 1) reconocer la orden
o = dz.orden("pídele al móvil un icono de un escudo azul para el mapa")
ok(o and o[0] == "pedir" and o[1]["tipo"] == "icono", f"icono: {o}")
ok(o[1]["destino"] == "mapa" and "escudo azul" in o[1]["descripcion"], f"destino/desc: {o}")
o = dz.orden("Kira, pide a kira app un fondo de pantalla de un bosque de noche")
ok(o and o[1]["tipo"] == "fondo" and "bosque de noche" in o[1]["descripcion"], f"fondo: {o}")
o = dz.orden("encárgale al móvil un tema en tonos violeta")
ok(o and o[1]["tipo"] == "tema" and "violeta" in o[1]["descripcion"], f"tema: {o}")
o = dz.orden("pídele al móvil un estilo de ventanas muy redondeadas")
ok(o and o[1]["tipo"] == "ventana", f"ventana: {o}")
o = dz.orden("dile al móvil que me haga un salvapantallas con estrellas")
ok(o and o[1]["tipo"] == "salvapantallas", f"salva: {o}")
o = dz.orden("pídele al móvil un logo para kiraos")
ok(o and o[1]["tipo"] == "logo" and o[1]["destino"] == "", f"logo: {o}")
ok(dz.orden("enséñame los diseños del móvil") == ("ver", None), "ver")
ok(dz.orden("tus diseños") == ("ver", None), "tus diseños")
for frase in ("cambia el fondo", "pon de fondo la última del móvil", "crea un icono nuevo con la hora",
              "hola", "pon el tema bosque", "pide un taxi"):
    ok(dz.orden(frase) is None, f"no es encargo: {frase}")
ok(sis.orden("pídele al móvil un fondo de un río") is None, "sistema_kira no se lo come")
ok(sis.orden("pon de fondo la última del móvil") is not None, "sistema_kira sigue con lo suyo")

# ---------------------------------------------------------------- 2) datos sin cerebro
ok(dz.colores_de_texto("tonos violeta")["neon"] == "#a78bfa", "violeta por palabra")
c = dz.colores_de_texto("algo rarísimo sin colores")
ok(dz.colores_validos(c) is not None, f"colores derivados válidos: {c}")
ok(dz.ventana_de_texto("muy redondeadas")["radio"] == 26, "radio")
ok(dz.ventana_de_texto("cuadradas y transparentes") == {"radio": 0, "borde": 1, "opacidad": 0.85, "sombra": True},
   "cuadradas transparentes")
ok(dz.colores_de_respuesta('Aquí: {"fondo":"#000000","neon":"#11aaff","acento":"#ff00aa","texto":"#ffffff"}')
   == {"fondo": "#000000", "neon": "#11aaff", "acento": "#ff00aa", "texto": "#ffffff"}, "JSON del cerebro")
ok(dz.colores_de_respuesta("no sé") is None, "cerebro sin colores")
ok(dz.ventana_valida({"radio": 99, "borde": -4, "opacidad": 3}) == {"radio": 28, "borde": 0, "opacidad": 1.0,
                                                                     "sombra": True}, "ventana acotada")

# ---------------------------------------------------------------- 3) el viaje completo: KiraOS → móvil → KiraOS
K, M = os.path.join(T, "k"), os.path.join(T, "m")
rkos, rm = rk.Recuerdos(os.path.join(K, "recuerdos")), rk.Recuerdos(os.path.join(M, "recuerdos"))
e_ic = dz.pedir(K, "icono", "un escudo", "mapa")
e_fo = dz.pedir(K, "fondo", "un bosque")
e_te = dz.pedir(K, "tema", "violeta")
e_ve = dz.pedir(K, "ventana", "muy redondeadas")
e_sa = dz.pedir(K, "salvapantallas", "estrellas")
ok(len(dz.para_movil(K, [])) == 5, "cinco encargos para el móvil")

paq, marcas = sc.paquete_movil(M, rm)
res, resp = sc.aplicar_en_kiraos(K, rkos, paq)
ok(len(resp["encargos_diseno"]) == 5, "viajan al móvil")
ok(all(e["estado"] == "entregado" for e in dz.encargos(K)), "marcados entregados")
r = sc.aplicar_en_movil(M, rm, resp, marcas)
ok(r["disenos"] == 5 and dz.pendientes_movil(M) == 5, "el móvil los guarda")
# repetir la sincronía no los duplica (cursor)
paq, marcas = sc.paquete_movil(M, rm)
res, resp = sc.aplicar_en_kiraos(K, rkos, paq)
ok(resp["encargos_diseno"] == [], "no se repiten")
sc.aplicar_en_movil(M, rm, resp, marcas)
ok(len(dz.encargos_movil(M)) == 5, "sin duplicar en el móvil")

# el móvil los hace (núcleo del móvil de verdad, con pintor de mentira)
import kira_god


class Pinta:
    pass


core = kira_god.KiraGodCore.__new__(kira_god.KiraGodCore)
core.dir = M
core.cancelado = lambda: False
img_dir = os.path.join(T, "pintado")
os.makedirs(img_dir, exist_ok=True)
pintadas = []


def pintar_imagen(desc, formato=None, al_progreso=None):
    pintadas.append((desc, formato))
    ruta = os.path.join(img_dir, f"p{len(pintadas)}.png")
    with open(ruta, "wb") as f:
        f.write(png())
    return {"ruta": ruta, "aviso": ""}


core.pintar_imagen = pintar_imagen
core.cerebro_ia = None
core.sincronizar = lambda *a, **k: "ok"
hechos = core.hacer_disenos(en_hilo=False)
ok(hechos == 5, f"hechos los cinco: {hechos}")
ok(len(pintadas) == 3, f"tres imágenes pintadas: {pintadas}")
ok(any(f == "horizontal" for _d, f in pintadas) and any(f == "cuadrado" for _d, f in pintadas), "formatos")
ok(dz.pendientes_movil(M) == 0, "nada pendiente")

# vuelven a KiraOS: 2 imágenes por viaje
paq, marcas = sc.paquete_movil(M, rm)
ok(len([d for d in paq["disenos"] if "imagen" in d]) == 2 and paq["hay_mas"], "2 imágenes por viaje")
res, resp = sc.aplicar_en_kiraos(K, rkos, paq)
sc.aplicar_en_movil(M, rm, resp, marcas)
ok(res["disenos"] == len(paq["disenos"]), "KiraOS los guarda")
paq, marcas = sc.paquete_movil(M, rm)
res2, resp = sc.aplicar_en_kiraos(K, rkos, paq)
sc.aplicar_en_movil(M, rm, resp, marcas)
ok(len(dz.listos(K)) == 5, f"cinco listos: {[e['estado'] for e in dz.encargos(K)]}")
paq, _m = sc.paquete_movil(M, rm)
ok(paq["disenos"] == [], "ya no se reenvían")
ok(dz.ruta_imagen(K, dz.uno(K, e_ic["id"])), "imagen del icono guardada")
ok(oct(os.stat(dz.ruta_imagen(K, dz.uno(K, e_ic["id"]))).st_mode & 0o777) == "0o600", "imagen 0600")
ok(dz.uno(K, e_te["id"])["colores"]["neon"] == "#a78bfa", "tema con colores")

# NADA se ha aplicado solo
p = sis.para_pantalla()
ok(p["tema"] == "noche" and p["fondo"] is None and not p["iconos_img"] and not p["ventanas"], "nada aplicado solo")

# basura: una imagen falsa o un encargo inventado no entran
ok(dz.guardar_resultados(K, [{"id": "ffffffff", "tipo": "icono", "imagen": base64.b64encode(png()).decode()}]) == 0,
   "encargo inventado")
e_x = dz.pedir(K, "icono", "x", "mapa")
ok(dz.guardar_resultados(K, [{"id": e_x["id"], "tipo": "icono", "imagen": base64.b64encode(b"<html>").decode()}]) == 0,
   "no es imagen")
ok(dz.guardar_resultados(K, [{"id": e_x["id"], "tipo": "tema", "colores": {"fondo": "red"}}]) == 0, "tipo cambiado")

# ---------------------------------------------------------------- 4) el visto bueno en la pantalla de KiraOS
import escritorio_kira as ek


class Pantalla(ek.EscritorioMixin):
    ruta_sistema = None

    def ventanas_extra(self):
        return []


pa = Pantalla()
d = pa.disenos()
ok(len([x for x in d["lista"] if x["estado"] == "listo"]) == 5 and "visto bueno" in d["texto"], "la lista")
ok(any(x["mini"].startswith("data:image/") for x in d["lista"] if x["tipo"] == "icono"), "miniatura")
for e in (e_ic, e_fo, e_te, e_ve, e_sa):
    r = pa.diseno_hacer(e["id"], "aplicar")
    ok(r["texto"].startswith("Listo"), f"aplicar {e['tipo']}: {r}")
p = sis.para_pantalla()
ok(p["iconos_img"].get("mapa"), "icono del mapa con imagen")
ok(p["fondo"] and p["fondo"]["id"], "fondo puesto")
ok(p["tema"] == "medida" and p["colores"]["neon"] == "#a78bfa", f"tema a medida: {p['tema']}")
ok(p["ventanas"]["radio"] == 26, "ventanas")
ok(p["salvapantallas"]["estilo"] == "imagen" and p["salvapantallas"]["imagen"], "salvapantallas imagen")
ok(pa.salva_datos().startswith("data:image/"), "imagen del salvapantallas")
ok(dz.uno(K, e_ic["id"])["estado"] == "aplicado", "marcado aplicado")
ok("no está listo" in pa.diseno_hacer(e_ic["id"], "aplicar")["texto"], "no se aplica dos veces")
sis.deshacer()
ok(sis.para_pantalla()["salvapantallas"]["estilo"] != "imagen", "deshacer")
# rechazar y pedir otro
e_r = dz.pedir(K, "logo", "orbe")
dz.guardar_resultados(K, [{"id": e_r["id"], "tipo": "logo", "imagen": base64.b64encode(png()).decode()}])
ok("Rechazado" in pa.diseno_hacer(e_r["id"], "rechazar")["texto"], "rechazar")
antes = len(dz.encargos(K))
ok("vuelvo a encargar" in pa.diseno_hacer(e_r["id"], "otro")["texto"], "pedir otro")
ok(len(dz.encargos(K)) == antes + 1 and dz.encargos(K)[-1]["estado"] == "pedido", "otro pedido")
# logo sin destino → icono de Hablar
e_l = dz.pedir(K, "logo", "orbe")
dz.guardar_resultados(K, [{"id": e_l["id"], "tipo": "logo", "imagen": base64.b64encode(png()).decode()}])
ok(pa.diseno_hacer(e_l["id"], "aplicar")["texto"].startswith("Listo"), "logo aplicado")
ok(sis.para_pantalla()["iconos_img"].get("hablar"), "logo en el icono de Hablar")

# ---------------------------------------------------------------- 5) la orden por la pantalla y por el núcleo
t = {"respuesta": "", "lineas": [], "estado": "pensando", "pedir_clave": None}
pa.cli = None
pa.voz_activa = False
pa._contestar(t, "pídele al móvil un fondo de pantalla de una playa")
ok("encargado" in t["respuesta"] and t["estado"] == "hecho", f"pantalla pide: {t}")
t = {"respuesta": "", "lineas": [], "estado": "pensando", "pedir_clave": None}
pa._contestar(t, "enséñame los diseños")
ok(t.get("abrir") == "disenos", "pantalla abre la ventana")
import nucleo_portatil as npo


class C:
    dir = K

    def registrar_actividad(self):
        pass

    def nueva_tarea(self):
        pass


r = npo.ejecutar(C(), "pídele al móvil un tema en tonos de fuego", lambda *a: None)
ok("encargado" in r["texto"], f"núcleo pide: {r}")
ok(dz.encargos(K)[-1]["tipo"] == "tema", "apuntado en el núcleo")
r = npo.ejecutar(C(), "tus diseños", lambda *a: None)
ok("Diseños que le he encargado" in r["texto"], "núcleo lista")

# ---------------------------------------------------------------- 6) la página tiene la ventana y la aplica
html = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html"), encoding="utf-8").read()
ok("function pintaDisenos" in html and 'id==="disenos"' in html and "salva_datos" in html, "html")
ok("ASPECTO.ventanas" in html, "ventanas en ponAspecto")
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        errores = []
        pg.on("pageerror", lambda e: errores.append(str(e)))
        pg.goto("file://" + os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html"))
        pg.wait_for_timeout(800)
        pg.evaluate("abrir('disenos')")
        pg.wait_for_timeout(500)
        ok(pg.evaluate("window.KIRA_DISENOS && window.KIRA_DISENOS.n") == 3, "tres diseños en la ventana")
        ok(pg.locator(".dtema").count() == 1 and pg.locator(".dvent").count() == 1, "vistas de tema y ventana")
        btn = pg.locator('[data-dz="aplicar"][data-id="a2"]')
        btn.click()
        ok("Seguro" in btn.inner_text(), "dos toques")
        btn.click()
        pg.wait_for_timeout(700)
        ok("aplicado" in pg.locator("#vcuerpo").inner_text().lower(), "aplicado en la ventana")
        pg.evaluate("ponAspecto({colores:{fondo:'#05070f',neon:'#22d3ee',acento:'#f472d0',texto:'#e7ecf5'},ventanas:{radio:0,borde:3,opacidad:0.9,sombra:false}})")
        ok(pg.evaluate("document.getElementById('ventana').style.borderRadius") == "0px", "radio aplicado")
        pg.evaluate("ponAspecto({salvapantallas:{activo:true,minutos:10,estilo:'imagen',imagen:{id:'x',v:1}}}); mostrarSalva()")
        pg.wait_for_timeout(300)
        ok("data:image" in pg.evaluate("document.getElementById('salva').style.background"), "salvapantallas imagen")
        ok(not errores, f"sin errores JS: {errores}")
        b.close()
except ImportError:
    print("(sin playwright: la página no se prueba en Chromium)")

print(f"test_disenos: {n} comprobaciones OK")
