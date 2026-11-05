# -*- coding: utf-8 -*-
"""v2.87: el SISTEMA NERVIOSO entre la Kira del móvil y KiraOS (sincronia_kira, ordenes_kira, mando_kira.es_trabajo,
tablero_kira) y el núcleo de verdad en los dos lados, con un servidor de verdad en 127.0.0.1."""
import json
import os
import socket
import sys
import tempfile
import threading
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp()
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
os.environ.pop("KIRA_API_KEY", None)

import recuerdos_kira as rk
import sincronia_kira as sc
import ordenes_kira as okr
import pensador_kira as pn
import investigar_kira as iv

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


def textos(rec):
    return [(rec.leer(i) or {}).get("texto", "") for i in range(1, rec.total() + 1)]


# =====================================================================================
#  1) LA SINCRONÍA PURA: dos carpetas, dos baúles
# =====================================================================================
M, K = os.path.join(T, "m"), os.path.join(T, "k")
rm, rkos = rk.Recuerdos(os.path.join(M, "recuerdos")), rk.Recuerdos(os.path.join(K, "recuerdos"))
rkos.guardar("Nací el sábado en un Packard Bell.", tema="mi nacimiento", fuente="nacimiento")
for i in range(5):
    rm.guardar(f"Lo que estudié en el móvil, ficha {i}.", tema=f"python {i}", fuente="estudio")
pe = pn._vacio() if hasattr(pn, "_vacio") else {"notas": [], "vistas": [], "soluciones": {}}
pe["notas"].append({"pregunta": "¿cómo funciona un trie?", "respuesta": "Por prefijos.", "cuando": 100,
                    "seguridad": "alta", "semilla": "trie"})
pe["soluciones"]["trie"] = {"tema": "trie", "resumen": "árbol de prefijos", "cuando": 101, "veces": 1}
pn.guardar(pe, os.path.join(M, "pensamientos.json"))
iv.anadir(M, "qué es un compilador")
json.dump({"tema": "un buscador", "activo": True}, open(os.path.join(M, "foco.json"), "w"))

paq, marcas = sc.paquete_movil(M, rm, maximo=3)
ok(len(paq["recuerdos"]) == 3 and paq["hay_mas"], "va por viajes (como mucho `maximo` recuerdos)")
ok("api_key" not in json.dumps(paq) and "token" not in json.dumps(paq), "en el paquete no viaja ninguna clave")
res, resp = sc.aplicar_en_kiraos(K, rkos, paq)
ok(res["recuerdos"] == 3 and res["notas"] == 1 and res["soluciones"] == 1 and res["preguntas"] == 1 and res["foco"] == 1,
   "KiraOS recibe recuerdos, pensamientos, soluciones, tus encargos y el foco: " + str(res))
ok("Nací el sábado en un Packard Bell." in textos(rkos), "y NO borra lo suyo (se suma)")
r = sc.aplicar_en_movil(M, rm, resp, marcas)
ok(r["recuerdos"] == 1 and "Nací el sábado en un Packard Bell." in textos(rm), "el móvil recibe lo de KiraOS")
for _ in range(5):                                     # los viajes que faltan
    paq, marcas = sc.paquete_movil(M, rm, maximo=3)
    _res, resp = sc.aplicar_en_kiraos(K, rkos, paq, maximo=3)
    sc.aplicar_en_movil(M, rm, resp, marcas)
    if not paq["hay_mas"] and not resp["hay_mas"]:
        break
ok(sum("ficha" in t for t in textos(rkos)) == 5, "al final llegan todos los recuerdos del móvil")
ok(textos(rkos).count("Nací el sábado en un Packard Bell.") == 1, "lo que vino de KiraOS no se le devuelve")
tot_k, tot_m = rkos.total(), rm.total()
for _ in range(2):                                     # IDEMPOTENTE: otra vez lo mismo no duplica nada
    paq, marcas = sc.paquete_movil(M, rm)
    _res, resp = sc.aplicar_en_kiraos(K, rkos, paq)
    sc.aplicar_en_movil(M, rm, resp, marcas)
ok(rkos.total() == tot_k and rm.total() == tot_m, "sincronizar dos veces no duplica nada")
paq_mismo, _m = sc.paquete_movil(M, rm)
ok(not paq_mismo["recuerdos"] and not paq_mismo["notas"], "si no hay nada nuevo, no se manda nada")
# un paquete repetido (se perdió la respuesta): KiraOS no duplica
viejo = {"v": 1, "recuerdos": [{"texto": "Lo que estudié en el móvil, ficha 0.", "tema": "python 0"}], "notas": [],
         "soluciones": {}, "preguntas": [], "cursor": {}}
sc.aplicar_en_kiraos(K, rkos, viejo)
ok(rkos.total() == tot_k, "un paquete que llega dos veces no duplica (el baúl reconoce lo idéntico)")
est_k = pn.cargar(os.path.join(K, "pensamientos.json"))
ok(len(est_k["notas"]) == 1 and "trie" in est_k["soluciones"], "los pensamientos se suman sin repetirse")
ok(json.load(open(os.path.join(K, "foco.json")))["tema"] == "un buscador", "KiraOS adopta el foco (no tenía uno)")
try:
    sc.aplicar_en_kiraos(K, rkos, {"v": 99})
    ok(False, "versión rara")
except ValueError:
    ok(True, "un paquete de otra versión se rechaza")
ok("Envié" in sc.estado_movil(M)["resumen"], "el móvil apunta qué envió y qué recibió")

# =====================================================================================
#  2) EL ASPECTO que KiraOS le pone al móvil (solo datos validados)
# =====================================================================================
t = sc.poner_tema_movil(K, "verde")
ok(t["nombre"] == "bosque" and t["v"] == 1, "«verde» = el tema bosque")
try:
    sc.poner_tema_movil(K, "arcoíris")
    ok(False, "tema desconocido")
except ValueError:
    ok(True, "un aspecto que no conoce se rechaza")
for malo in ({"v": 1, "colores": {"fondo": "url(http://x)", "neon": "#fff", "acento": "#000000", "texto": "#000000"}},
             {"v": 1, "colores": {"fondo": "#000000"}}, {"v": 0, "colores": sc.TEMAS["noche"]}, "rojo", None):
    ok(sc.tema_valido(malo) is None, f"tema raro rechazado: {malo!r}")
paq, marcas = sc.paquete_movil(M, rm)
_res, resp = sc.aplicar_en_kiraos(K, rkos, paq)
ok(resp["tema"] and resp["tema"]["nombre"] == "bosque", "el tema viaja al móvil")
sc.aplicar_en_movil(M, rm, resp, marcas)
ok(sc.tema_del_movil(M)["colores"]["neon"] == sc.TEMAS["bosque"]["neon"], "y el móvil lo guarda para el próximo arranque")
paq, marcas = sc.paquete_movil(M, rm)
_res, resp = sc.aplicar_en_kiraos(K, rkos, paq)
ok(resp["tema"] is None, "el mismo tema no se vuelve a mandar")

# =====================================================================================
#  3) MEJORAS de KiraOS para el móvil: llegan, pero NUNCA se instalan solas
# =====================================================================================
MOD = ("def hora(texto):\n    return 'Son las tantas.'\n\n\ndef registrar():\n    return {'hora de kiraos': hora}\n")
try:
    sc.guardar_para_movil(K, "mala", "print('sin registrar')")
    ok(False, "sin registrar")
except ValueError:
    ok(True, "una mejora sin registrar() no se prepara")
try:
    sc.guardar_para_movil(K, "../fuera", MOD)
    ok(False, "nombre raro")
except ValueError:
    ok(True, "un nombre con ruta no vale")
sc.guardar_para_movil(K, "hora_kiraos", MOD, descripcion="dice la hora")
paq, marcas = sc.paquete_movil(M, rm)
_res, resp = sc.aplicar_en_kiraos(K, rkos, paq)
ok(len(resp["mejoras"]) == 1, "la mejora va en la respuesta")
r = sc.aplicar_en_movil(M, rm, resp, marcas)
ok(r["mejoras"] == 1 and sc.mejoras_recibidas(M)[0]["estado"] == "recibida", "llega como «recibida»")
ok(not os.path.exists(os.path.join(M, "modulos")) or not os.listdir(os.path.join(M, "modulos")),
   "y NO se instala nada (laboratorio + tus dos toques)")
paq, marcas = sc.paquete_movil(M, rm)
_res, resp = sc.aplicar_en_kiraos(K, rkos, paq)
ok(resp["mejoras"] == [], "la misma mejora no se vuelve a mandar")
trampa = dict(resp, mejoras=[{"nombre": "trampa", "codigo": MOD + "# cambiado\n", "hash": sc._hash(MOD)}])
ok(sc.guardar_mejoras_recibidas(M, trampa["mejoras"]) == 0, "una mejora cuyo código no cuadra con su huella se tira")
ok(sc.marcar_mejora(M, "hora_kiraos", "rechazada") and not sc.mejoras_recibidas(M), "descartarla la quita del panel")

# =====================================================================================
#  4) ÓRDENES: historial y cola para KiraOS
# =====================================================================================
O = os.path.join(T, "o")
a = okr.apuntar(O, "hazme un juego de carreras", "kiraos", "pendiente")
b = okr.apuntar(O, "hola", "movil")
ok([o["id"] for o in okr.pendientes_kiraos(O)] == [a], "la orden de trabajo espera a KiraOS")
okr.actualizar(O, a, estado="enviada", tarea="t1")
ok([o["id"] for o in okr.en_kiraos(O)] == [a] and not okr.pendientes_kiraos(O), "enviada: ahora se pregunta cómo va")
ok(okr.cerrar_huerfanas(O) == 1 and okr.ultimas(O)[0]["estado"] == "cancelada", "la que se cortó al cerrar se cierra")
ok(not okr.actualizar(O, "no-existe", estado="hecha"), "una orden que no existe no se inventa")
okr.actualizar(O, a, estado="raro")
ok(okr.ultimas(O)[-1]["estado"] == "enviada", "un estado raro no se guarda")
for i in range(okr.MAX + 20):
    okr.apuntar(O, f"o{i}", "movil", "hecha")
ok(len(okr.ultimas(O, 10_000)) == okr.MAX, "el historial tiene tope")

# =====================================================================================
#  5) QUÉ ES TRABAJO PARA KiraOS (fuera de casa se apunta)
# =====================================================================================
import mando_kira as mdk
for f in ("Kira, hazme un juego de carreras", "escríbeme un programa que sume", "experimenta con grafos",
          "pinta un gato", "hazme una foto de un gato", "diséñame una web", "crea una calculadora",
          "enciende tu máquina", "instala la librería numpy", "quiero una app de notas", "conviértelo en una app"):
    ok(mdk.es_trabajo(f), f"«{f}» es trabajo de KiraOS")
for f in ("hazme una foto", "qué es una app", "estudia python", "piensa", "abre whatsapp", "hola", "tu cuaderno",
          "modo completo", "modo mando", "para"):
    ok(not mdk.es_trabajo(f), f"«{f}» NO es trabajo de KiraOS")
ok(mdk.orden_modo_app("pon las pantallas antiguas") == "completo" and mdk.orden_modo_app("modo sencillo") == "sencillo",
   "«modo completo» / «modo sencillo»")
ok(mdk.orden_de_mejora("que diga la hora") == "prepara una mejora para el móvil: que diga la hora",
   "una mejora para el móvil se la pide a KiraOS")

# =====================================================================================
#  6) EL PANEL (puro)
# =====================================================================================
import tablero_kira as tbk
eq = tbk.equipo_movil(T, "Xiaomi Redmi")
ok(eq["modelo"] == "Xiaomi Redmi" and eq["nucleos"] >= 1 and eq["disco_libre_gb"] is not None, "info del móvil")
secs = tbk.secciones({"movil": {"pensando": True, "pausada": True, "pensamientos": 7, "soluciones": 2},
                      "tarea": "", "kiraos": {"version": "2.87", "recuerdos": 40, "ocupada": True, "haciendo": "un juego",
                                              "actividad": {"pensando": True, "maquina": True},
                                              "equipo": {"procesador": "Intel Core i5", "ram_mb": 8192,
                                                         "disco_libre_gb": 180}},
                      "sinc": {"ultima": time.time() - 120, "resumen": "Envié 3."}, "pendiente": 4,
                      "ordenes": okr.ultimas(O, 3), "mejoras": [{"nombre": "x", "descripcion": "d", "estado": "probada"}],
                      "charla": [("tu", "hola"), ("kira", "Hola, ¿qué hacemos?")], "equipo_movil": eq,
                      "ultimo": {"orden": "un juego", "respuesta": "Hecho", "codigo": "print(1)\n" * 50}})
ids = [x["id"] for x in secs]
ok(ids[:2] == ["movil", "kiraos"] and {"cerebro", "charla", "ordenes", "sinc", "mejoras", "ultimo", "ajustes"} <= set(ids),
   "tarjetas: móvil, KiraOS, cerebro, conversaciones, órdenes, sincronía, mejoras, último trabajo, ajustes")
txt = {x["id"]: x["texto"] for x in secs}
ok("pensando (en pausa" in txt["movil"] and "Xiaomi Redmi" in txt["movil"], "qué hace el móvil y su equipo")
ok("un juego" in txt["kiraos"] and "máquina virtual" in txt["kiraos"] and "8 GB" in txt["kiraos"],
   "qué hace KiraOS y su portátil")
ok("hace 2 min" in txt["sinc"] and "4 cosa" in txt["sinc"], "cuándo se sincronizó y cuánto falta por enviar")
ok("líneas más" in txt["ultimo"], "el código largo se recorta")
bot = [b for x in secs for b in x["botones"]]
ok(("Instalar «x» (2 toques)", "aplicar:x") in bot, "una mejora probada se instala con dos toques")
sin = tbk.secciones({})
ok(any("No la veo" in x["texto"] for x in sin), "sin KiraOS, lo dice claro")
ok(all(sym not in json.dumps([x["texto"] for x in secs], ensure_ascii=False) for sym in ("⏳", "✓", "✗")),
   "sin iconos que la letra del móvil no tiene")

# =====================================================================================
#  7) DE VERDAD: KiraOS (nucleo_portatil) con su servidor y el núcleo del MÓVIL hablando por la red
# =====================================================================================
import nucleo_portatil as npo
import casa_kira as ck
import pasarela_cliente as pcl


def libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


TOKEN = "t" * 32
DATOS = os.path.join(T, "kira_datos")
npo.preparar_datos(DATOS, TOKEN, cerebro_url="http://127.0.0.1:9")
nucleo = npo.Nucleo(DATOS)
nucleo.core.recuerdos.guardar("Soy KiraOS y vivo en el portátil.", tema="quién soy", fuente="nacimiento")
P = libre()
srv = npo.crear_servidor("127.0.0.1", P, TOKEN, nucleo)
threading.Thread(target=srv.serve_forever, daemon=True).start()
h = npo.ClienteNucleo(f"http://127.0.0.1:{P}", TOKEN)._pedir("/hola")
ok("actividad" in h and "equipo" in h and "sincronia" in h, "/hola cuenta qué hace KiraOS y su equipo")

MOVIL = os.path.join(T, "movil")
os.environ["KIRA_DATA_DIR"] = MOVIL
import kira_god
core = kira_god.KiraGodCore()
core.recuerdos.guardar("Aprendí en el móvil qué es un grafo.", tema="grafos", fuente="estudio")
ck.PUERTO_NUCLEO = P
pcl.guardar_config("http://127.0.0.1:8765", TOKEN, portatil_url="http://127.0.0.1:9")
casa = ck.Casa()
casa.disponible = lambda forzar=False: True
core._casa = lambda: casa
txt = core.sincronizar()
ok(txt.startswith("Envié") and "recibí" in txt, "el móvil se sincroniza con KiraOS: " + txt)
ok("Aprendí en el móvil qué es un grafo." in textos(nucleo.core.recuerdos), "KiraOS ya sabe lo del móvil")
ok("Soy KiraOS y vivo en el portátil." in textos(core.recuerdos), "y el móvil lo de KiraOS")
antes = nucleo.core.recuerdos.total()
core.sincronizar()
ok(nucleo.core.recuerdos.total() == antes, "otra sincronía no duplica nada")

# una orden de trabajo apuntada fuera de casa: al volver, el móvil se la da a KiraOS y recoge el resultado
oid = okr.apuntar(MOVIL, "cambia el aspecto del móvil a violeta", "kiraos", "pendiente")
core.ordenes_a_kiraos()
o = next(x for x in okr.ultimas(MOVIL, 50) if x["id"] == oid)
ok(o["estado"] == "enviada" and o["tarea"], "al llegar a casa le da la orden apuntada")
for _ in range(60):
    core.ordenes_a_kiraos()
    o = next(x for x in okr.ultimas(MOVIL, 50) if x["id"] == oid)
    if o["estado"] not in ("enviada", "en curso"):
        break
    time.sleep(0.05)
ok(o["estado"] == "hecha" and "violeta" in o["respuesta"], "y recoge cómo acabó: " + str(o))
avisos = []
core.al_sincronia = avisos.append
core.sincronizar()
ok(sc.tema_del_movil(MOVIL)["nombre"] == "violeta" and avisos, "el aspecto que le puso KiraOS llega al móvil (y avisa)")

# KiraOS ocupada: la orden se queda en la cola, no se pierde
nucleo.trabajos.actual = "x"
nucleo.trabajos.tareas["x"] = {"estado": "en curso", "orden": "otra", "inicio": time.time(), "avance": []}
oid2 = okr.apuntar(MOVIL, "cambia el aspecto del móvil a fuego", "kiraos", "pendiente")
core.ordenes_a_kiraos()
ok(next(x for x in okr.ultimas(MOVIL, 50) if x["id"] == oid2)["estado"] == "pendiente", "si KiraOS está ocupada, espera")
nucleo.trabajos.tareas["x"]["estado"] = "hecho"

# la mejora para el móvil: KiraOS la escribe (aquí, con un cerebro de mentira) y la prueba en SU laboratorio
nucleo.core.generar_mejora = lambda pedido, quien=None: ("hora_movil", MOD)
r = npo.ejecutar(nucleo.core, "prepara una mejora para el móvil: que diga la hora", lambda fr, t: None)
ok(r.get("ok") and "dos toques" in r["texto"], "KiraOS prepara la mejora y la prueba en su laboratorio: " + str(r))
nucleo.core.generar_mejora = lambda pedido, quien=None: ("rota", "def registrar():\n    return {'x': lambda a: 1/0\n")
r = npo.ejecutar(nucleo.core, "prepara una mejora para el móvil: algo roto", lambda fr, t: None)
ok(not r.get("ok") and "no pasa" in r["texto"], "si no pasa su laboratorio, no se la manda al móvil")
core.sincronizar()
ms = sc.mejoras_recibidas(MOVIL)
ok([m["nombre"] for m in ms] == ["hora_movil"], "al móvil llega solo la buena, como «recibida»")
ok(not os.path.exists(os.path.join(MOVIL, "modulos", "hora_movil.py")), "y no se instala sola")
r = npo.ejecutar(nucleo.core, "Kira, cambia el aspecto del móvil a arcoíris.", lambda fr, t: None)
ok("No conozco ese aspecto" in r["texto"], "un aspecto desconocido se dice claro")

# sin KiraOS en casa: lo dice y no rompe
casa_mal = ck.Casa()
casa_mal.disponible = lambda forzar=False: False
core._casa = lambda: casa_mal
ok("No veo a KiraOS" in core.sincronizar(), "fuera de casa, lo guarda para luego")
srv.shutdown()

# vigilar casa: al LLEGAR a casa se sincroniza sola
llamadas = []


class CasaSi:
    def nucleo_disponible(self): return True


core._casa = lambda: CasaSi()
core.sincronizar = lambda *a, **k: llamadas.append("sinc") or "ok"
vueltas = []


def dormir(s):
    vueltas.append(s)
    if len(vueltas) >= 3:
        core._vigilando_casa = False


core._hilo_casa = None
core.vigilar_casa(True, cada_seg=0, dormir=dormir)
for _ in range(100):
    if core._hilo_casa is None:
        break
    time.sleep(0.02)
ok(llamadas.count("sinc") == 1, "al llegar a casa se sincroniza sola (una vez, no en cada vuelta)")
act = core.actividad()
ok({"pensando", "estudiando", "foco", "pensamientos", "soluciones"} <= set(act), "el móvil cuenta qué está haciendo")

print("\nTODO BIEN", n)
