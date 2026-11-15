# -*- coding: utf-8 -*-
"""v3.84: Programando ▸ «Mis programas»: aprendidos en la web (Instalar), aprendidos por su cuenta (Instalar) e
instalados (Abrir · Mejorar con su barra · Desinstalar)."""
import json, os, shutil, subprocess, sys, tempfile, types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATA_DIR"] = T
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
os.environ["KIRA_DATOS_NUCLEO"] = T
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import catalogo_programas_kira as cpk
import accesos_kira as ak
import pensador_kira as pn

fallos = n = 0
def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1

# ---------- qué páginas son programas ----------
ok(cpk.es_programa({"url": "https://github.com/yt-dlp/yt-dlp"})["nombre"] == "yt-dlp", "un repositorio de GitHub")
ok(cpk.es_programa({"url": "https://github.com/yt-dlp/yt-dlp/releases"})["fuente"] == "https://github.com/yt-dlp/yt-dlp",
   "sus releases = el mismo repositorio")
ok(cpk.es_programa({"url": "https://github.com/topics/python"}) is None, "una página general de GitHub no")
pag = {"url": "https://obsproject.com/download", "titulo": "OBS Studio - Descargas", "texto": "OBS graba la pantalla",
       "descargas": [{"url": "https://x/obs.AppImage", "archivo": "obs.AppImage"}, {"url": "https://x/o.exe", "archivo": "o.exe"}]}
p = cpk.es_programa(pag)
ok(p and p["nombre"] == "OBS Studio" and p["archivos"] == ["obs.AppImage"], "una web con descargas para Linux")
ok(cpk.es_programa({"url": "https://x.com", "titulo": "X", "descargas": [{"archivo": "x.exe"}]}) is None,
   "solo .exe: no (no es para tu portátil)")
ok(cpk.es_programa({"url": "https://es.wikipedia.org/wiki/Python", "titulo": "Python"}) is None, "un artículo no")

# ---------- se apunta al ESTUDIAR (guardar_pagina) ----------
import kira_god
class Rec:
    def guardar(self, *a, **k): return 1
falso = types.SimpleNamespace(dir=T, recuerdos=Rec(), resumir_pagina=lambda p_, t_="": ("resumen " * 10, None))
kira_god.KiraGodCore.guardar_pagina(falso, pag, "grabar la pantalla")
kira_god.KiraGodCore.guardar_pagina(falso, pag, "grabar la pantalla")
kira_god.KiraGodCore.guardar_pagina(falso, {"url": "https://github.com/ggml-org/llama.cpp", "texto": "LLM en C++"}, "ia")
w = cpk.web(T)
ok(len(w) == 2 and w[0]["nombre"] == "llama.cpp" and w[1]["nombre"] == "OBS Studio", "al estudiar los apunta, sin repetir")

# ---------- lo que sacó por su cuenta ----------
est = {"soluciones": {"calculadora de propinas": {"semilla": "Calculadora de propinas", "codigo": "print(5)",
                                                  "respuesta": "calcula", "veces": 2, "cuando": 5},
                      "una idea": {"semilla": "una idea", "codigo": "", "respuesta": "sin código"}}}
pn.guardar(est, os.path.join(T, "pensamientos.json"))
mios = cpk.propios(est)
ok(len(mios) == 1 and mios[0]["tema"] == "Calculadora de propinas", "solo las soluciones con código")
# ya no se instala sola (v3.26 la ponía directamente en el escritorio)
nucleo_falso = types.SimpleNamespace(dir=T, es_kiraos=True, _ruta_pensar=lambda: os.path.join(T, "p2.json"))
kira_god.KiraGodCore._guardar_solucion(nucleo_falso, "sale sola", codigo="print(1)")
ok(not ak.existe(T, "sale sola"), "lo que saca por su cuenta ya NO se instala solo")

# ---------- filas / botones ----------
ak.anadir(T, "Mi juego", "print('hola')")
f = cpk.filas(w, mios, ak.listar(T))
ok([b["texto"] for b in f["web"][0]["botones"]] == ["Instalar", "Quitar de la lista"]
   and f["web"][0]["botones"][0]["accion"] == "decir:instala https://github.com/ggml-org/llama.cpp",
   "web: Instalar le dice a Kira «instala <fuente>»")
ok(f["propios"][0]["botones"][0]["accion"].startswith("hacer:prog:instalar:"), "por su cuenta: Instalar")
bi = f["instalados"][0]["botones"]
ok([b["texto"] for b in bi] == ["Abrir", "Mejorar", "Desinstalar"] and bi[1]["pedir"] and bi[2]["dos"],
   "instalados: Abrir · Mejorar (con barra) · Desinstalar (dos toques)")
ok(cpk.orden_mejorar(bi[1]["accion"].replace("decir:", "").replace("{texto}", "que tenga colores")) ==
   ("Mi juego", "que tenga colores"), "la barra de Mejorar da la orden de ESE programa")
ok(cpk.orden_mejorar("mejora el programa x: a") is None and cpk.orden_mejorar("mejora tu sistema: algo") is None,
   "no se confunde con otras órdenes")

# ---------- el puente de la pantalla ----------
import escritorio_kira as ek
esc = ek.EscritorioMixin(); esc.cli = None; esc.nucleo_cli = None
a = esc.app("programas")
ok([p_["id"] for p_ in a["pestanas"]] == ["web", "propios", "instalados"], "tres pestañas")
r = esc.app_hacer("programas", "prog:instalar:" + mios[0]["id"])
ok(r["refrescar"] and ak.existe(T, "Calculadora de propinas"), "Instalar lo suyo: icono en el escritorio")
a2 = esc.app("programas")
ok(not a2["pestanas"][1]["filas"] and len(a2["pestanas"][2]["filas"]) == 2, "pasa de «por mi cuenta» a «Instalados»")
iid = ak.buscar(T, "mi juego")["id"]
ok(esc.app_hacer("programas", "prog:quitar:" + iid)["refrescar"] and not ak.existe(T, "Mi juego")
   and not os.path.exists(os.path.join(T, "apps", iid + ".py")), "Desinstalar: icono y archivos fuera")
ok(esc.app_hacer("programas", "prog:olvidar:" + w[1]["id"]) and len(cpk.web(T)) == 1, "Quitar de la lista")

# ---------- Mejorar de verdad (núcleo) ----------
import nucleo_portatil as npk
calc = ak.buscar(T, "calculadora de propinas")
ok(ak.codigo_de(T, calc["id"]) == "print(5)", "guarda su código para poder mejorarlo")
pedidos = []
core = types.SimpleNamespace(dir=T, ultimo_codigo="")
def acordado(pedido, al_paso=None, al_codigo=None):
    pedidos.append(pedido)
    return {"ok": True, "codigo": "print(5 * 1.21)", "nombre": "x"}
core.programa_acordado = acordado
r = npk.ejecutar(core, "mejora el programa «Calculadora de propinas»: que sume el IVA", lambda *a_: None)
ok(r["ok"] and "mejorado" in r["texto"], "Mejorar: " + r["texto"][:60])
ok("print(5)" in pedidos[0] and "que sume el IVA" in pedidos[0], "el cerebro recibe SU código y lo que pides")
ok(ak.codigo_de(T, calc["id"]) == "print(5 * 1.21)" and "5 * 1.21" in open(os.path.join(T, "apps", calc["id"] + ".html")).read(),
   "su icono abre ya la versión mejorada")
core.programa_acordado = lambda *a_, **k_: {"ok": False, "texto": "falló la prueba"}
r = npk.ejecutar(core, "mejora el programa «Calculadora de propinas»: rómpelo", lambda *a_: None)
ok(not r["ok"] and ak.codigo_de(T, calc["id"]) == "print(5 * 1.21)", "si no sale, lo deja como estaba")
r = npk.ejecutar(core, "mejora el programa «Nada»: algo", lambda *a_: None)
ok(not r["ok"] and "No tengo" in r["texto"], "uno que no existe")
# app de fuera
ext = ak.anadir_externa(T, "Hola App", ["/x/hola"], os.path.join(T, "apps_externas", "hola"), fuente="https://github.com/a/hola")
llam = []
viejo = npk._instalar_app
npk._instalar_app = lambda core_, fuente, paso, **k: llam.append(fuente) or {"texto": "reinstalada"}
r = npk.ejecutar(core, "mejora el programa «Hola App»: actualízala a la última versión", lambda *a_: None)
npk._instalar_app = viejo
ok(llam == ["https://github.com/a/hola"], "app de fuera: «actualízala» la reinstala desde su fuente")

import wifi_kira
ok(wifi_kira.orden_wifi("mejora el programa «Calculadora wifi»: que sea verde") is None,
   "un programa con «wifi» en el nombre no se confunde con la WiFi")

# ---------- la pantalla (Chromium) ----------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    fd = os.path.join(T, "d.json")
    open(fd, "w", encoding="utf-8").write(json.dumps(esc.app("programas"), ensure_ascii=False))
    js = r"""
const { chromium } = require('playwright'); const fs = require('fs');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(500);
  const d = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
  await pg.evaluate(d => { FAKE.app = function(n){ return Promise.resolve(d); }; window.ENVIADO=[];
    window.enviar = function(t){ window.ENVIADO.push(t); }; }, d);
  await pg.click('.icono[data-app="programando"]'); await pg.waitForTimeout(400);
  const hayBoton = await pg.$('[data-misprog]') !== null;
  await pg.click('[data-misprog]'); await pg.waitForTimeout(400);
  const titulo = await pg.$eval('#vtitulo', x => x.textContent);
  const pes = await pg.$$eval('[data-pest]', l => l.map(x => x.textContent));
  const bweb = await pg.$$eval('.fila .fbot button', l => l.map(x => x.textContent));
  await pg.click('.fila .fbot button'); await pg.waitForTimeout(100);
  await pg.click('[data-pest="instalados"]'); await pg.waitForTimeout(150);
  const binst = await pg.$$eval('.fila .fbot button', l => l.map(x => x.textContent));
  await pg.click('[data-pedir]'); await pg.waitForTimeout(150);
  const barra = await pg.$('.pedir input') !== null;
  await pg.fill('.pedir input', 'que tenga modo oscuro'); await pg.keyboard.press('Enter'); await pg.waitForTimeout(100);
  await pg.screenshot({path: process.argv[3]});
  const env = await pg.evaluate(() => window.ENVIADO);
  console.log(JSON.stringify({errs, hayBoton, titulo, pes, bweb, binst, barra, env}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    f = os.path.join(T, "c.js"); open(f, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, f, html, os.path.join(T, "programas.png"), fd], capture_output=True, text=True,
                       timeout=120, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(d["hayBoton"] and d["titulo"] == "Mis programas", "Chromium: botón «Mis programas» en Programando")
        ok(len(d["pes"]) == 3 and d["pes"][0].startswith("Aprendidos en la web"), "Chromium: las tres pestañas")
        ok("Instalar" in d["bweb"], "Chromium: Instalar en lo aprendido")
        ok(d["binst"][:3] == ["Abrir", "Mejorar", "Desinstalar"], "Chromium: Abrir · Mejorar · Desinstalar")
        ok(d["barra"] and d["env"][-1].startswith("mejora el programa «") and d["env"][-1].endswith("»: que tenga modo oscuro")
           and d["env"][0].startswith("instala https://github.com/ggml-org/llama.cpp"),
           "Chromium: Instalar y la barra de Mejorar le dan la orden a Kira " + str(d["env"]))
        print("  captura:", os.path.join(T, "programas.png"))
    else:
        print("  (sin Chromium)", out[:300], r.stderr[-300:])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
