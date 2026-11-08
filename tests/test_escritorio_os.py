# -*- coding: utf-8 -*-
"""v2.90: el ESCRITORIO de KiraOS (como Windows): iconos + barra abajo, ventanas con «‹ Escritorio», y hablar con Kira
desde cualquier punto (escribes o hablas; contesta POR VOZ; botón «Texto» para leerlo). Puente Python sin ventana +
la pantalla de verdad en Chromium (si hay playwright)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp()
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
os.environ["KIRA_DATOS_NUCLEO"] = os.path.join(T, "kira_datos")
os.makedirs(os.environ["KIRA_DATOS_NUCLEO"], exist_ok=True)
import escritorio_kira as ek
import kiraos
import oido_portatil as op

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


def esperar(cond, seg=5):
    t0 = time.time()
    while time.time() - t0 < seg:
        if cond():
            return True
        time.sleep(0.02)
    return False


# ---------- lo que se DICE en voz alta ----------
ok(ek.para_voz("Hola. ```python\nprint(1)\n``` Listo.") == "Hola. (te dejo el código en el texto) Listo.",
   "el código no se lee en voz alta")
ok("http" not in ek.para_voz("Mira https://ejemplo.com/x ya"), "los enlaces tampoco")
largo = ek.para_voz("Una frase. " * 80)
ok(len(largo) < 480 and largo.endswith("El resto lo tienes en el texto."), "lo largo se corta: el resto, en el texto")
dichas = []
ok(ek.callar_voz(correr=lambda o: dichas.append(o)) and ["spd-say", "-C"] in dichas, "callar para la voz")


# ---------- el puente (Api de KiraOS = arranque + escritorio) ----------
class CliFalso:
    grande = False
    url, token = "http://127.0.0.1:8770", "x" * 32

    def hola(self):
        return {"nombre": "el Packard Bell"}

    def charla(self, texto, al_trozo=None, **k):
        for t in ("Hola, ", "Jefe. ", "Te escucho."):
            al_trozo(t)
        return "Hola, Jefe. Te escucho."

    def defensa(self, accion, **k):
        return {"ok": True, "aparatos": [{"ip": "192.168.1.5", "nombre": "móvil"}]} if accion == "inventario" \
            else {"ok": True, "avisos": []}


class WifiFalso:
    class WifiError(Exception):
        pass

    def resumen_corto(self):
        return {"ssid": "MiCasa", "senal": 72, "internet": "full"}

    def estado(self):
        return {"conectada": "MiCasa"}

    def texto_estado(self, e):
        return "Conectada a «MiCasa»."

    def redes(self):
        return [{"ssid": "MiCasa", "senal": 72, "segura": True, "guardada": True, "en_uso": True, "banda": "2,4 GHz"}]

    def conectar(self, ssid, clave=None):
        self.ultima = (ssid, clave)
        return f"Conectada a «{ssid}»."

    def desconectar(self):
        return "Desconectada."

    def radio(self, si):
        return "encendida" if si else "apagada"

    def reparar(self):
        return "Arreglado."

    def olvidar(self, s):
        return "olvidada"

    def orden_wifi(self, t):
        return None

    def trae_clave(self, t):
        return False


voz = []
api = kiraos.Api(cli=CliFalso(), hablar=voz.append, ruta_pin=os.path.join(T, "pin"))
api.wifi_mod = WifiFalso()
api.nucleo_cli = None
ok(api.entrar() is True and api.entrado, "entrar sigue funcionando (y prepara el escritorio)")
b = api.barra()
ok(b["wifi"]["ssid"] == "MiCasa" and b["voz"] is True and len(b["iconos"]) == 10, "la barra: WiFi, voz e iconos")
ids = [i["id"] for i in ek.ICONOS]
ok(ids == ["hablar", "buscador", "wifi", "red", "mapa", "maquina", "cuaderno", "programando", "movil", "ajustes"],
   "los 10 iconos del escritorio (v2.91: con el Buscador)")


# ---------- v2.91: el BUSCADOR tipo Google (lo busca y lo lee desde su máquina) ----------
class NetFalsa:
    avisos = []

    def __init__(self):
        self.buscadas = []

    def buscar(self, consulta, tipo="web", n=8):
        self.buscadas.append((consulta, tipo))
        if consulta == "nada":
            raise RuntimeError("No he encontrado nada.")
        return [{"titulo": "Python (lenguaje)", "url": "https://es.wikipedia.org/wiki/Python", "resumen": "Un lenguaje.",
                 "fuente": "Wikipedia"},
                {"titulo": "Python.org", "url": "https://www.python.org/", "resumen": "La web oficial.", "fuente": "web"}]

    def leer(self, url):
        return {"url": url, "titulo": "Python", "texto": "Python es un lenguaje muy legible. " * 50,
                "codigos": ["print(1)"], "tipo": "web"}


class RedFalsa:
    def estado(self):
        return "desde mi máquina virtual (por su puerta, sin ver tu casa)"


api.internet_obj, api.red_web = NetFalsa(), RedFalsa()
for frase, esp in (("busca recetas de tortilla", ("recetas de tortilla", "web")),
                   ("Kira, busca en internet cómo plantar tomates", ("cómo plantar tomates", "web")),
                   ("búscame código de un servidor web en python", ("un servidor web en python", "codigo")),
                   ("busca en google el tiempo en Madrid", ("el tiempo en Madrid", "web"))):
    b = api.es_busqueda(frase)
    ok(b and (b["consulta"], b["tipo"]) == esp, f"«{frase}» abre el buscador con «{esp[0]}» ({esp[1]})")
for frase in ("hola Kira", "resume https://es.wikipedia.org/wiki/Python", "guarda https://a.org/x", "piensa",
              # v2.92 (revisión de la v2.91): órdenes de Kira que empiezan por «busca» NO abren el buscador
              "busca redes wifi", "Kira, busca la wifi", "busca redes", "busca aparatos en mi red",
              "busca aparatos nuevos", "busca puertos abiertos", "busca en mis pdf la palabra lógica",
              "busca en tus recuerdos la receta", "busca tus recetas de grafos", "busca recetas de ingeniería",
              "busca el código de emparejar", "busca en tu máquina el archivo"):
    ok(api.es_busqueda(frase) is None, f"«{frase}» no es una búsqueda en internet (va a Kira como siempre)")
for frase in ("busca redes neuronales", "busca recetas de tortilla", "busca el tiempo en Sevilla"):
    ok(api.es_busqueda(frase) is not None, f"«{frase}» sí es buscar en internet")
r = api.buscar_web("python", "web")
ok(r["ok"] and len(r["resultados"]) == 2 and r["resultados"][0]["dominio"] == "es.wikipedia.org",
   "buscar: resultados con título, web y resumen (como Google)")
ok("máquina virtual" in r["via"], "y dice desde dónde se buscó (su máquina)")
ok(api.buscar_web("python", "raro")["tipo"] == "web" and api.internet_obj.buscadas[-1] == ("python", "web"),
   "un tipo raro se queda en «Todo»")
ok(not api.buscar_web("nada")["ok"], "si no encuentra, lo dice (sin inventar)")
p2 = api.leer_web("https://es.wikipedia.org/wiki/Python")
ok(p2["ok"] and p2["titulo"] == "Python" and p2["codigos"] == 1 and "legible" in p2["texto"],
   "leer: la página como texto limpio")


# hablar desde cualquier sitio: contesta y lo DICE
r = api.hablar("hola Kira")
ok(esperar(lambda: api.tarea_hablar(r["id"])["estado"] == "hecho"), "Kira contesta")
ok(api.tarea_hablar(r["id"])["respuesta"] == "Hola, Jefe. Te escucho.", "la respuesta va llegando (texto)")
ok(esperar(lambda: voz) and voz[-1] == "Hola, Jefe. Te escucho.", "y la dice en voz alta")
api.voz_activa_poner(False)
voz.clear()
r = api.hablar("otra")
ok(esperar(lambda: api.tarea_hablar(r["id"])["estado"] == "hecho") and not voz, "sin voz: solo texto")
api.voz_activa_poner(True)
ok(api.hablar("   ").get("error"), "una frase vacía no se manda")
ok(api.tarea_hablar("nope")["estado"] == "no existe", "una charla que no existe")
sin_cerebro = kiraos.Api(cli=None, hablar=lambda t: None)
r = sin_cerebro.hablar("hola")
ok(esperar(lambda: sin_cerebro.tarea_hablar(r["id"])["estado"] == "hecho") and
   "No encuentro mi cerebro" in sin_cerebro.tarea_hablar(r["id"])["respuesta"], "sin cerebro, lo dice claro")

# el código que escribe Kira pasa a «Programando»
api._recordar_codigo("hazme un programa", ["· escribiendo", "── código (suma) ──\ndef suma(a, b):\n    return a + b\n"])
ok(api.hay_programa() and api.programando_datos()["archivo"] == "suma.py" and api.programando_datos()["lineas"],
   "el último código de Kira se ve en «Programando»")

# el oído
api.oido = lambda: "qué tal estás"
ok(api.escuchar() == {"ok": True, "texto": "qué tal estás", "error": ""}, "el micrófono: lo que dijiste")
api.oido = lambda: ""
ok(not api.escuchar()["ok"], "si no oye nada, lo dice")


def oido_roto():
    raise op.OidoError("Me falta el oído (Vosk).")


api.oido = oido_roto
ok("Vosk" in api.escuchar()["error"], "sin oído instalado, lo dice")


class RecFalso:
    def __init__(self, frases):
        self.frases, self.i = frases, 0

    def AcceptWaveform(self, trozo):
        self.i += 1
        return self.i == 3

    def Result(self):
        return json.dumps({"text": "enciende la wifi"})

    def FinalResult(self):
        return json.dumps({"text": ""})


ok(op.escuchar(fuente=iter([b"\0" * 4000] * 10), reconocedor=RecFalso([])) == "enciende la wifi",
   "Vosk: en cuanto acabas la frase, ya está")


class RecMudo(RecFalso):
    def AcceptWaveform(self, trozo):
        return False


ok(op.escuchar(fuente=iter([b"\0"] * 5), reconocedor=RecMudo([])) == "", "si no dices nada: vacío")

# WiFi desde la ventana
ok(api.wifi_datos()["redes"][0]["ssid"] == "MiCasa", "la ventana WiFi lista las redes")
ok(api.wifi_hacer("conectar", "Vecino", "clave1234")["texto"] == "Conectada a «Vecino»." and
   api.wifi_mod.ultima == ("Vecino", "clave1234"), "conectar con la clave escrita en el portátil")
ok(api.wifi_hacer("arreglar")["texto"] == "Arreglado." and not api.wifi_hacer("raro")["ok"], "arreglar; acción rara no")

# las demás ventanas: texto + botones
for nombre in ("red", "cuaderno", "maquina", "movil", "ajustes"):
    d = api.app(nombre)
    ok(d["titulo"] and isinstance(d["texto"], str) and isinstance(d["botones"], list), f"ventana «{nombre}»")
ok(api.app("nada")["texto"] == "Esta ventana aún no existe.", "una ventana desconocida no rompe")
ok("192.168.1.5" in api.app_hacer("red", "inventario")["texto"], "Mi red: buscar aparatos")
api.app_hacer("ajustes", "grande")
ok(api.cli.grande is True, "Ajustes: cerebro grande")
ok("quitada" in api.app_hacer("ajustes", "voz_no")["texto"] and api.voz_activa is False, "Ajustes: sin voz")
api.voz_activa_poner(True)
salida = "nov 07 11:00 pc python3[123456]:   CÓDIGO PARA CONECTAR A KIRA:   482 913\nnov 07 11:00 …"
ok("482 913" in ek.codigo_movil(correr=lambda: salida), "Móvil: el código para emparejar (no el número del proceso)")
ok("No veo un código" in ek.codigo_movil(correr=lambda: ""), "sin código: cómo pedirlo")
orden = []
ok(api.sistema("apagar", correr=orden.append)["ok"] and orden == [["systemctl", "poweroff"]], "apagar el portátil")
ok(not api.sistema("formatear", correr=orden.append)["ok"], "nada de órdenes raras")

# kiraos: al entrar, la MISMA ventana pasa al escritorio
src = open(os.path.join(RAIZ, "kira_portatil", "kiraos.py"), encoding="utf-8").read()
ok("class Api(EscritorioMixin)" in src and 'api.web = True' in src, "kiraos usa el escritorio en la misma ventana")
arr = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "arranque.html"), encoding="utf-8").read()
ok('location.href="escritorio.html"' in arr, "el arranque lleva al escritorio")
sh = open(os.path.join(RAIZ, "kira_portatil", "instalar_portatil.sh"), encoding="utf-8").read()
ok("vosk" in sh and "alsa-utils" in sh and "vosk-model-small-es" in sh, "el instalador pone el oído del portátil")

# ---------- la pantalla de verdad (Chromium) ----------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(700);
  const iconos = await pg.$$eval('.icono', l => l.length);
  await pg.keyboard.type('hola'); await pg.keyboard.press('Enter'); await pg.waitForTimeout(1600);
  const aviso = await pg.textContent('#aviso');
  await pg.click('#btnTexto'); await pg.waitForTimeout(200);
  const texto = await pg.$$eval('#charlaCajon .m', l => l.map(x => x.textContent));
  await pg.click('#cajonCerrar');
  const apps = ['buscador','wifi','red','cuaderno','maquina','movil','ajustes','mapa','programando','hablar']; const vuelve = [];
  for (const a of apps) { await pg.click('.icono[data-app="'+a+'"]'); await pg.waitForTimeout(250);
    const v = await pg.isVisible('#volver'); await pg.click('#volver'); await pg.waitForTimeout(100);
    vuelve.push(v && !(await pg.evaluate(() => document.getElementById('ventana').classList.contains('on')))); }
  await pg.click('#btnKira'); const menu = await pg.$$eval('#menu .op', l => l.length);
  await pg.click('#menu [data-sis="apagar"]'); const conf = await pg.textContent('#menu [data-sis="apagar"]');
  await pg.keyboard.press('Escape');
  // v2.91: «busca …» en la barra abre el BUSCADOR con los resultados; pulsar uno lo lee; «‹ Resultados» vuelve
  await pg.click('#entrada'); await pg.keyboard.type('busca python'); await pg.keyboard.press('Enter');
  await pg.waitForTimeout(1200);
  const busTitulo = await pg.textContent('#vtitulo');
  const busCampo = await pg.inputValue('#busCampo');
  const res = await pg.$$eval('.res .tit', l => l.map(x => x.textContent));
  const via = await pg.textContent('.via');
  await pg.screenshot({path: process.argv[3]});
  await pg.click('.res .tit'); await pg.waitForTimeout(400);
  const lectura = await pg.textContent('.lectura h3'); const botones = await pg.$$eval('#busCuerpo .b', l => l.map(x => x.textContent));
  await pg.click('#busAtras'); await pg.waitForTimeout(200);
  const otraVez = await pg.$$eval('.res .tit', l => l.length);
  await pg.click('.pest[data-t="codigo"]'); await pg.waitForTimeout(800);
  const pest = await pg.textContent('.pest.on');
  console.log(JSON.stringify({errs, iconos, aviso, texto, vuelve, menu, conf, busTitulo, busCampo, res, via, lectura,
                              botones, otraVez, pest}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    f = os.path.join(T, "e.js")
    open(f, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, f, html, os.path.join(T, "buscador.png")], capture_output=True, text=True, timeout=120,
                       env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(d["iconos"] == 10, "Chromium: 10 iconos en el escritorio")
        ok("voz" in d["aviso"] and "ver texto" in d["aviso"], "Chromium: contesta por voz, con «ver texto»")
        ok(len(d["texto"]) == 2 and "hola" in d["texto"][0], "Chromium: el botón «Texto» enseña la conversación")
        ok(all(d["vuelve"]), "Chromium: TODAS las ventanas tienen «‹ Escritorio» y vuelven a la pantalla principal")
        ok(d["menu"] >= 12, "Chromium: el menú KIRA con apps, volver al orbe, reiniciar y apagar")
        ok("Seguro" in d["conf"], "Chromium: apagar pide un segundo toque")
        ok(d["busTitulo"] == "Buscador" and d["busCampo"] == "python" and len(d["res"]) == 3,
           "Chromium: «busca python» en la barra abre el Buscador con los resultados")
        ok("máquina virtual" in d["via"], "Chromium: dice que lo buscó desde su máquina")
        ok(d["lectura"] and "Resúmelo" in d["botones"] and "Guárdalo en mi baúl" in d["botones"],
           "Chromium: al pulsar un resultado lo lee, con «Resúmelo» y «Guárdalo en mi baúl»")
        ok(d["otraVez"] == 3 and d["pest"] == "Código", "Chromium: «‹ Resultados» vuelve y hay pestañas (Todo/Código/…)")
    else:
        print("(sin Chromium utilizable: me salto la pantalla)", out[:200])
print("\nTODO BIEN", n)
