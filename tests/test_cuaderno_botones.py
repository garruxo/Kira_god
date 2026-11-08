# -*- coding: utf-8 -*-
"""v3.12: botones del Cuaderno de KiraOS. Pensamiento: «Viable para mejorar» (pasa a Mejoras, con su tipo: sistema,
app por hacer, seguridad). Mejoras: «Implementar» (laboratorio + tus dos toques; nunca sola) y «Repensar y
experimentar». Conocimiento: «Pasar a mejorar» (si tiene código lo prueba en la máquina virtual; si pasa, mejora
esperando tus dos toques; si no, vuelve a Pensamiento)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["KIRA_DATA_DIR"] = T
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
os.environ["KIRA_DATOS_NUCLEO"] = T
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import cuaderno_clases_kira as cc
import nucleo_portatil as npk
import pensador_kira as pn

fallos = 0
n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


DUDA = {"semilla": "la caché", "pregunta": "¿por qué la caché funciona así por dentro?", "respuesta": "No lo sé bien",
        "seguridad": "media", "duda": True, "fuente": "lo que sé", "tipo": "idea"}
SEGU = {"semilla": "las contraseñas", "pregunta": "¿para qué sirve guardar contraseñas cifradas?",
        "respuesta": "Para que no se lean si roban el disco; habría que hacerlo", "seguridad": "media", "duda": True}
MEJ = {"semilla": "una cola", "pregunta": "¿hay algo de una cola que pueda MEJORAR en mi propio código?",
       "respuesta": "En KiraOS va lento: debería usar deque.", "seguridad": "media"}
SABE = {"semilla": "el cifrado", "pregunta": "¿por qué el cifrado funciona así?", "respuesta": "Por matemáticas.",
        "seguridad": "alta", "duda": False, "fuente": "estudiado", "tipo": "experimento",
        "experimento": {"ok": True, "resultado": "bien"}}
ruta = os.path.join(T, "pensamientos.json")
est = {"notas": [dict(DUDA), dict(SEGU), dict(MEJ), dict(SABE)], "vistas": [],
       "soluciones": {"suma rápida": {"respuesta": "sum() es la mejor", "codigo": "print(sum([1, 2, 3]))", "veces": 2,
                                      "cuando": 5},
                      "algo roto": {"respuesta": "así", "codigo": "print(1/0)", "cuando": 4}}}
pn.guardar(est, ruta)

# ---------- filas ----------
fp = cc.filas_pensamiento(est)
ok([f["texto"] for f in fp] == [SEGU["pregunta"], DUDA["pregunta"]], "Pensamiento: sus apuntes, el más nuevo arriba")
ok(all(f["botones"][0]["texto"] == "Viable para mejorar" for f in fp), "Pensamiento: botón «Viable para mejorar»")
fc = cc.filas_conocimiento(est)
ok({f["seccion"] for f in fc} == {"soluciones", "comprobado"} and all(f["botones"][0]["texto"] == "Pasar a mejorar"
                                                                    for f in fc), "Conocimiento: «Pasar a mejorar»")
ok(any(f["etiqueta"] == "Con código" and "mejorada 2 veces" in f["detalle"] for f in fc), "Conocimiento: con código")
fm = cc.filas_mejoras(est, {"kiraos_pendiente": {"nombre": "decir_hora"}})
mej = [f for f in fm if f["seccion"] != "permiso"]
ok(mej and [b["texto"] for b in mej[0]["botones"]] == ["Implementar", "Repensar y experimentar"]
   and mej[0]["botones"][0].get("dos"), "Mejoras: «Implementar» (dos toques) y «Repensar y experimentar»")
ok(mej[0]["seccion"] == "kiraos" and mej[0]["etiqueta"] == "Sistema · SE DEBE", "Mejoras: dónde, de qué y si urge")
ok(fm[0]["seccion"] == "permiso" and fm[0]["botones"][0]["accion"] == "app:mejoras", "Mejoras: la que espera permiso")
ok(cc.tipo_mejora(SEGU) == "Seguridad" and cc.tipo_mejora({"pregunta": "una app de notas"}) == "App por hacer",
   "tipo: seguridad / app por hacer")
p = cc.pestanas(est)
ok(all(x.get("secciones") for x in p) and p[0]["filas"] and p[1]["filas"], "las pestañas llevan filas y secciones")

# ---------- el núcleo ----------
hechas = []
probadas = []


def probar(codigo):
    probadas.append(codigo)
    return (False, "ZeroDivisionError: division by zero", None) if "1/0" in codigo else (True, "ok", "6")


panel = types.SimpleNamespace(pedidos=[], resp={"aprobable": True},
                              pendiente=types.SimpleNamespace(nombre="mejora_x", codigo="def registrar(): ..."))
panel.enviar_orden = lambda pedido: (panel.pedidos.append(pedido), panel.resp)[1]
core = types.SimpleNamespace(dir=T, _ruta_pensar=lambda: ruta, _probar_experimento=probar, _panel=panel,
                             registrar_actividad=lambda: None, nueva_tarea=lambda: None,
                             es_estudia_general=lambda o: None,
                             ciclo_una=lambda semilla=None: (hechas.append(("ciclo", semilla)), "di 3 vueltas")[1])
nuc = npk.Nucleo.__new__(npk.Nucleo)
nuc.core = core
nuc.trabajos = npk.Trabajos(lambda o, paso: npk.ejecutar(core, o, paso))


def espera(cond, s=8):
    lim = time.time() + s
    while time.time() < lim and not cond():
        time.sleep(0.03)
    return cond()


def ultima(tid):
    espera(lambda: nuc.trabajos.tareas.get(tid, {}).get("estado") in ("hecho", "error"))
    return nuc.trabajos.tareas[tid]


i_segu = cc.id_nota(SEGU)
r = npk.cuaderno_accion(nuc, "viable", i_segu)
e2 = pn.cargar(ruta)
ok(r["ok"] and "Seguridad" in r["texto"] and cc.clase(cc.buscar(e2, i_segu)[1]) == "mejora",
   "«Viable para mejorar»: pasa a Mejoras con su tipo")
r = npk.cuaderno_accion(nuc, "implementar", i_segu)
t = ultima(r["id"])
ok(r["ok"] and t["resultado"] == "Preparado (espera tu permiso)" and "contraseñas" in panel.pedidos[-1],
   "«Implementar»: la escribe y la pasa por el laboratorio; ESPERA tus dos toques")
nt = cc.buscar(pn.cargar(ruta), i_segu)[1]
ok(nt["en_marcha"] == "" and "dos toques" in nt["intento"], "la nota apunta cómo fue")
panel.resp = {"aprobable": False, "texto": "no pasó: falta registrar"}
r = npk.cuaderno_accion(nuc, "implementar", cc.id_nota(MEJ))
t = ultima(r["id"])
ok(t["resultado"] == "Falló" and "no pasó el laboratorio" in cc.buscar(pn.cargar(ruta), cc.id_nota(MEJ))[1]["intento"],
   "si no pasa el laboratorio: Falló, y queda apuntado")
r = npk.cuaderno_accion(nuc, "repensar", cc.id_nota(MEJ))
t = ultima(r["id"])
ok(("ciclo", "una cola") in hechas and t["respuesta"] == "di 3 vueltas" and
   cc.buscar(pn.cargar(ruta), cc.id_nota(MEJ))[1]["en_marcha"] == "", "«Repensar y experimentar»: el ciclo sobre su tema")

panel.resp = {"aprobable": True}
r = npk.cuaderno_accion(nuc, "amejora", cc.id_sol("suma rápida"))
t = ultima(r["id"])
ok("print(sum([1, 2, 3]))" in probadas and t["resultado"] == "Preparado (espera tu permiso)",
   "«Pasar a mejorar» con código: lo prueba (en la máquina) y, si pasa, mejora esperando tus dos toques")
r = npk.cuaderno_accion(nuc, "amejora", cc.id_sol("algo roto"))
t = ultima(r["id"])
e3 = pn.cargar(ruta)
ok(t["resultado"] == "Falló" and "algo roto" not in e3["soluciones"] and
   any("algo roto" in x["pregunta"] and cc.clase(x) == "pensamiento" for x in e3["notas"]),
   "si NO pasa las pruebas, vuelve a Pensamiento con el motivo")
panel.resp = {"aprobable": False, "texto": "no pasa"}
r = npk.cuaderno_accion(nuc, "amejora", cc.id_nota(SABE))
t = ultima(r["id"])
x = cc.buscar(pn.cargar(ruta), cc.id_nota(SABE))[1]
ok(t["resultado"] == "Falló" and cc.clase(x) == "pensamiento" and "no pasó las pruebas" in x["respuesta"],
   "un conocimiento sin código que no pasa el laboratorio también vuelve a Pensamiento")
npk.cuaderno_accion(nuc, "viable", cc.id_nota(SABE))
ok(cc.clase(cc.buscar(pn.cargar(ruta), cc.id_nota(SABE))[1]) == "mejora", "y desde Pensamiento se puede volver a Mejoras")
ok(not npk.cuaderno_accion(nuc, "viable", "n0000000000")["ok"], "un apunte que ya no está: lo dice")
ok(not npk.cuaderno_accion(nuc, "borrar_disco", i_segu)["ok"], "botones raros no")

# ---------- servidor solo en el portátil ----------
import threading
import urllib.error
srv = npk.crear_servidor("127.0.0.1", 0, "tok", nuc)
threading.Thread(target=srv.serve_forever, daemon=True).start()
cli = npk.ClienteNucleo(f"http://127.0.0.1:{srv.server_address[1]}", "tok")
ok(cli.cuaderno_accion("viable", cc.id_nota(DUDA))["ok"], "por el servidor")
viejo = npk.es_local
npk.es_local = lambda ip: False
try:
    cli.cuaderno_accion("implementar", cc.id_nota(DUDA))
    ok(False, "desde fuera no")
except urllib.error.HTTPError as e:
    ok(e.code == 403, "desde el móvil: 403")
finally:
    npk.es_local = viejo
srv.shutdown()

# ---------- el puente ----------
import escritorio_kira as ek


class CliN:
    def __init__(self):
        self.h = []

    def cuaderno_accion(self, a, i):
        self.h.append((a, i))
        return {"ok": True, "texto": "hecho"}

    def estado(self):
        return {}

    def mejoras(self):
        return {}


esc = ek.EscritorioMixin()
esc.cli = None
esc.nucleo_cli = CliN()
ok(esc.app_hacer("cuaderno", "nota:implementar:" + i_segu)["refrescar"] and esc.nucleo_cli.h[-1] == ("implementar", i_segu),
   "el botón llega al núcleo")
ok(esc.app_hacer("cuaderno", "sol:amejora:" + cc.id_sol("x"))["texto"] == "hecho", "Pasar a mejorar llega al núcleo")
a = esc.app("cuaderno")
ok([bool(p_.get("filas")) for p_ in a["pestanas"]][:3] == [True, True, True], "la ventana trae las filas")

node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    datos = json.dumps(a, ensure_ascii=False)
    js = r"""
const { chromium } = require('playwright'); const fs = require('fs');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(500);
  const d = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
  await pg.click('.icono[data-app="cuaderno"]'); await pg.waitForTimeout(300);
  await pg.evaluate(d => pintaApp("cuaderno", d), d);
  const s1 = await pg.$$eval('.secc h4', l => l.map(x => x.textContent));
  const b1 = await pg.$$eval('.fila .fbot button', l => l.map(x => x.textContent));
  await pg.click('[data-pest="conocimiento"]'); await pg.waitForTimeout(100);
  const b2 = await pg.$$eval('.fila .fbot button', l => l.map(x => x.textContent));
  await pg.click('[data-pest="mejoras"]'); await pg.waitForTimeout(100);
  const s3 = await pg.$$eval('.secc h4', l => l.map(x => x.textContent));
  const b3 = await pg.$$eval('.fila .fbot button', l => l.map(x => x.textContent));
  await pg.screenshot({path: process.argv[3]});
  console.log(JSON.stringify({errs, s1, b1, b2, s3, b3}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    f = os.path.join(T, "c.js")
    open(f, "w").write(js)
    fd = os.path.join(T, "d.json")
    open(fd, "w", encoding="utf-8").write(datos)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, f, html, os.path.join(T, "mejoras.png"), fd], capture_output=True, text=True,
                       timeout=120, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(d["s1"][0].startswith("Lo que estoy pensando") and set(d["b1"]) == {"Viable para mejorar"},
           "Chromium: Pensamiento con «Viable para mejorar»")
        ok(set(d["b2"]) == {"Pasar a mejorar"}, "Chromium: Conocimiento con «Pasar a mejorar»")
        ok(any(x.startswith("KiraOS") for x in d["s3"]) and "Implementar" in d["b3"]
           and "Repensar y experimentar" in d["b3"], "Chromium: Mejoras con Implementar y Repensar")
        print("  captura:", os.path.join(T, "mejoras.png"))
    else:
        print("  (sin Chromium)", out[:300])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
