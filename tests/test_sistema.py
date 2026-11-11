# -*- coding: utf-8 -*-
"""v3.21: el dueño le cambia a KiraOS lo que quiera de SU sistema con una frase: aspecto (tema), iconos, salvapantallas,
lo que dice al encender y al apagar, la voz, el brillo, el sonido, la pantalla y el bluetooth. Las ventanas, iconos y
funciones NUEVAS siguen siendo mejoras (laboratorio + dos toques)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
RUTA = os.path.join(T, "sistema.json")
os.environ["KIRA_SISTEMA"] = RUTA
os.environ["KIRA_DATOS_NUCLEO"] = T
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import sistema_kira as sk

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ---------- 1) reconocer las órdenes ----------
casos = {
    "cambia el tema a bosque": ("tema", "bosque"), "pon kiraos en azul": ("tema", "oceano"),
    "Kira, pon el tema violeta": ("tema", "violeta"), "cambia el diseño de kiraos a claro": ("tema", "claro"),
    "oculta el icono del mapa": ("ocultar", "mapa"), "vuelve a poner el icono del mapa": ("mostrar", "mapa"),
    "pon el salvapantallas de estrellas": ("salva_estilo", "estrellas"),
    "salvapantallas a los 5 minutos": ("salva_minutos", 5), "quita el salvapantallas": ("salva_activo", False),
    "enséñame el salvapantallas": ("salva_ver", None),
    "al encender dime: Buenos días, Papi": ("saludo", "Buenos días, Papi"),
    "al apagar di hasta mañana jefe": ("despedida", "hasta mañana jefe"),
    "habla más despacio": ("voz_velocidad", -20), "voz más grave": ("voz_tono", -20), "voz normal": ("voz", (0, 0)),
    "sube el brillo": ("brillo", ("+", 20)), "brillo al 60": ("brillo", ("=", 60)),
    "baja un poco el brillo": ("brillo", ("-", 10)), "apaga la pantalla": ("pantalla_apagar", None),
    "apaga la pantalla a los 15 minutos": ("pantalla_minutos", 15),
    "sube el volumen": ("volumen", ("+", 20)), "volumen al 40": ("volumen", ("=", 40)),
    "silencio": ("silencio", True), "quita el silencio": ("silencio", False),
    "enciende el bluetooth": ("bt_poder", True), "apaga el bluetooth": ("bt_poder", False),
    "busca aparatos bluetooth": ("bt_buscar", None), "mis aparatos bluetooth": ("bt_lista", None),
    "conecta el bluetooth a mis cascos JBL": ("bt_conectar", "mis cascos JBL"),
    "desconecta el bluetooth de mis cascos JBL": ("bt_desconectar", "mis cascos JBL"),
    "deshaz el último cambio": ("deshacer", None), "¿qué puedo cambiar?": ("estado", None),
}
mal = [(f, sk.orden(f), e) for f, e in casos.items() if sk.orden(f) != e]
ok(not mal, f"reconoce las {len(casos)} órdenes de sistema " + str(mal[:3]))
nada = ["cambia el aspecto del móvil a verde", "crea una ventana con un botón", "lee la pantalla", "apaga el portátil",
        "busca python", "estudia bluetooth", "qué es el brillo", "hazme un juego de coches", "oculta el icono de ajustes"]
ok(all(sk.orden(f) is None for f in nada), "no se come otras órdenes (móvil, ventanas, leer pantalla, buscar, estudiar…)")

# ---------- 2) los ajustes: guardar, deshacer ----------
ok(sk.para_pantalla()["tema"] == "noche" and sk.para_pantalla()["salvapantallas"]["activo"], "por defecto: noche, con salvapantallas")
r = sk.responder("cambia el tema a fuego")
ok("fuego" in r and sk.para_pantalla()["colores"]["neon"] == "#fb923c", "cambiar el tema guarda sus colores")
ok(oct(os.stat(RUTA).st_mode & 0o777) == "0o600", "el archivo de ajustes es solo tuyo (0600)")
sk.responder("oculta el icono de la terminal")
ok(sk.para_pantalla()["ocultos"] == ["terminal"], "oculta un icono")
sk.responder("pon el salvapantallas de reloj")
sk.responder("salvapantallas a los 3 minutos")
s = sk.para_pantalla()["salvapantallas"]
ok(s == {"activo": True, "minutos": 3, "estilo": "reloj"}, "salvapantallas: estilo y minutos")
sk.responder("al encender dime: Buenos días, Papi")
sk.responder("al apagar di: Hasta mañana")
ok(sk.saludo() == "Buenos días, Papi" and sk.despedida() == "Hasta mañana", "saludo y despedida, tal cual los dijiste")
sk.responder("habla más despacio")
sk.responder("voz más aguda")
ok(sk.opciones_voz() == (-20, 20), "la voz: más despacio y más aguda")
r = sk.responder("deshaz el último cambio")
ok("deshecho" in r and sk.opciones_voz() == (-20, 0), "deshacer vuelve atrás un paso")
for _ in range(30):
    if "No hay" in sk.responder("deshaz el último cambio"):
        break
ok(sk.para_pantalla()["tema"] == "noche" and not sk.para_pantalla()["ocultos"], "deshaciendo todo, vuelve a como estaba")
ok("No hay ningún cambio" in sk.responder("deshaz el último cambio"), "sin más cambios, lo dice")
ok("Puedes cambiarme" in sk.responder("qué puedo cambiar"), "«qué puedo cambiar» explica todo")
open(RUTA, "w").write('{"tema": "<script>", "ocultos": ["ajustes", "mapa"], "salvapantallas": {"estilo": "x", "minutos": 9999}}')
p = sk.para_pantalla()
ok(p["tema"] == "noche" and p["ocultos"] == ["mapa"] and p["salvapantallas"]["estilo"] == "orbe"
   and p["salvapantallas"]["minutos"] == 120, "un archivo tocado a mano no rompe nada (se limpia)")
os.remove(RUTA)


# ---------- 3) el hardware: solo programas de la lista, sin shell ----------
class Falso:
    def __init__(self, hay, resp=None):
        self.hay, self.resp, self.llamadas = set(hay), resp or {}, []

    def which(self, p):
        return "/usr/bin/" + p if p in self.hay else None

    def correr(self, args):
        self.llamadas.append(args)
        for k, v in self.resp.items():
            if " ".join(args).startswith(k):
                return v
        return (0, "")


f = Falso({"brightnessctl"}, {"brightnessctl -m": (0, "intel_backlight,backlight,600,60%,1000")})
r = sk.hacer("brillo", ("=", 60), equipo=sk.Equipo(correr=f.correr, which=f.which))
ok(r == "Brillo al 60 %." and ["brightnessctl", "-q", "set", "60%"] in f.llamadas, "brillo con brightnessctl")
f = Falso({"brightnessctl"}, {"brightnessctl -m": (0, "x,backlight,50,5%,1000")})
sk.hacer("brillo", ("=", 0), equipo=sk.Equipo(correr=f.correr, which=f.which))
ok(["brightnessctl", "-q", "set", "5%"] in f.llamadas, "nunca a 0 (la pantalla se quedaría negra)")
f = Falso({"xrandr"}, {"xrandr --query": (0, "Screen 0: minimum\nLVDS-1 connected primary 1366x768\nVGA-1 disconnected")})
r = sk.hacer("brillo", ("-", 20), equipo=sk.Equipo(correr=f.correr, which=f.which))
ok("80 %" in r and ["xrandr", "--output", "LVDS-1", "--brightness", "0.8"] in f.llamadas, "sin brightnessctl: xrandr (y lo dice)")
f = Falso(set())
ok(sk.hacer("brillo", ("+", 20), equipo=sk.Equipo(correr=f.correr, which=f.which)).startswith("[x]"), "sin herramientas: lo dice claro")
f = Falso({"pactl"}, {"pactl get-sink-volume": (0, "Volume: front-left: 26214 /  40% / -23.88 dB")})
r = sk.hacer("volumen", ("=", 40), equipo=sk.Equipo(correr=f.correr, which=f.which))
ok(r == "Volumen al 40 %." and ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "40%"] in f.llamadas, "volumen con pactl")
f = Falso({"pactl"}, {"pactl get-sink-volume": (0, "Volume: 120%")})
r = sk.hacer("volumen", ("+", 20), equipo=sk.Equipo(correr=f.correr, which=f.which))
ok("100 %" in r and ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "100%"] in f.llamadas, "el volumen no pasa del 100 %")
f = Falso({"amixer"}, {"amixer get": (0, "Mono: Playback 30 [47%] [on]")})
ok(sk.hacer("volumen", ("-", 20), equipo=sk.Equipo(correr=f.correr, which=f.which)) == "Volumen al 47 %.", "sin pactl: amixer")
f = Falso({"xset"})
sk.hacer("pantalla_apagar", None, equipo=sk.Equipo(correr=f.correr, which=f.which))
sk.hacer("pantalla_minutos", 15, equipo=sk.Equipo(correr=f.correr, which=f.which))
ok(["xset", "dpms", "force", "off"] in f.llamadas and ["xset", "dpms", "900", "900", "900"] in f.llamadas
   and sk.cargar().get("apagar_pantalla_min") == 15, "apagar la pantalla ya, o a los 15 min (y se recuerda)")
f2 = Falso({"xset"})
sk.reaplicar(equipo=sk.Equipo(correr=f2.correr, which=f2.which))
ok(["xset", "dpms", "900", "900", "900"] in f2.llamadas, "al arrancar se vuelve a poner")

BT = {"bluetoothctl devices Paired": (0, "Device 11:22:33:44:55:66 Altavoz Salon\n"),
      "bluetoothctl devices Connected": (0, ""),
      "bluetoothctl devices": (0, "Device AA:BB:CC:DD:EE:FF JBL Tune 510BT\nDevice 11:22:33:44:55:66 Altavoz Salon\n"),
      "bluetoothctl connect": (0, "Connection successful")}
f = Falso({"bluetoothctl", "rfkill"}, BT)
eq = sk.Equipo(correr=f.correr, which=f.which)
ok(sk.hacer("bt_poder", True, equipo=eq) == "Bluetooth encendido." and ["rfkill", "unblock", "bluetooth"] in f.llamadas,
   "encender el bluetooth")
r = sk.hacer("bt_lista", None, equipo=eq)
ok("JBL Tune 510BT — visto" in r and "Altavoz Salon — emparejado" in r, "lista sus aparatos con su estado")
r = sk.hacer("bt_conectar", "mis cascos JBL", equipo=eq)
ok("JBL Tune 510BT" in r and ["bluetoothctl", "pair", "AA:BB:CC:DD:EE:FF"] in f.llamadas
   and ["bluetoothctl", "trust", "AA:BB:CC:DD:EE:FF"] in f.llamadas and ["bluetoothctl", "connect", "AA:BB:CC:DD:EE:FF"] in f.llamadas,
   "conectar «mis cascos JBL»: lo encuentra por palabras, lo empareja y conecta")
f.llamadas.clear()
sk.hacer("bt_conectar", "altavoz", equipo=eq)
ok(["bluetoothctl", "pair", "11:22:33:44:55:66"] not in f.llamadas, "si ya estaba emparejado, no lo vuelve a emparejar")
r = sk.hacer("bt_conectar", "nevera", equipo=eq)
ok(r.startswith("[x]") and "modo de emparejar" in r, "uno que no está: explica qué hacer")
f = Falso({"bluetoothctl"}, {"bluetoothctl devices": (0, "Device ;rm -rf / Raro\n")})
ok(sk.hacer("bt_conectar", "raro", equipo=sk.Equipo(correr=f.correr, which=f.which)).startswith("[x]"), "direcciones raras: no se tocan")
f = Falso(set())
ok("bluez" in sk.hacer("bt_poder", True, equipo=sk.Equipo(correr=f.correr, which=f.which)), "sin bluetoothctl: dice cómo ponerlo")
src = open(os.path.join(RAIZ, "kira_portatil", "sistema_kira.py"), encoding="utf-8").read()
ok("shell=True" not in src and "os.system" not in src, "nunca usa la shell")

# ---------- 4) la voz, el saludo y la despedida ----------
import kiraos
sk.responder("habla más rápido")
sk.responder("voz más grave")
orden_voz = []
import shutil as _sh
_w = _sh.which
kiraos.shutil.which = lambda p: "/usr/bin/spd-say" if p == "spd-say" else None
kiraos.voz_portatil("hola", correr=orden_voz.append)
kiraos.shutil.which = _w
ok(orden_voz and orden_voz[0][:7] == ["spd-say", "-l", "es", "-r", "20", "-p", "-20"], "la voz usa la velocidad y el tono elegidos")
sk.responder("voz normal")
sk.responder("al encender dime: Buenos días, Papi")
dicho = []
api = kiraos.Api(cli=None, hablar=dicho.append, ruta_pin=os.path.join(T, "pin"))
api.voz("Sistema Kira activado")
time.sleep(0.3)
ok(dicho == ["Buenos días, Papi"], "al encender dice tu saludo")
sk.responder("al apagar di: Hasta mañana, Papi")
api.pausa_despedida = 0
dicho.clear()
r = api.sistema("apagar", correr=lambda o: None)
ok(dicho == ["Hasta mañana, Papi"] and r["texto"] == "Hasta mañana, Papi", "al apagar dice tu despedida")

# ---------- 5) la pantalla de KiraOS: lo hace al momento (sin esperar a la cola) ----------
b = api.barra()
ok(b["aspecto"]["tema"] == "noche" and "colores" in b["aspecto"], "la barra lleva el aspecto")
api.equipo_sis = sk.Equipo(correr=lambda a: (0, ""), which=lambda p: None)
cid = api.hablar("cambia el tema a bosque")["id"]
for _ in range(50):
    t = api.tarea_hablar(cid)
    if t["estado"] == "hecho":
        break
    time.sleep(0.05)
ok(t["estado"] == "hecho" and "bosque" in t["respuesta"] and t.get("aspecto"), "en la barra: lo cambia aunque no haya cerebro")
ok(api.barra()["aspecto"]["tema"] == "bosque", "…y la pantalla se repinta con el tema nuevo")
cid = api.hablar("enséñame el salvapantallas")["id"]
time.sleep(0.4)
ok(api.tarea_hablar(cid).get("salvapantallas"), "«enséñame el salvapantallas» lo enseña")
aj = api.app("ajustes")
ok("MI SISTEMA" in aj["texto"] and any(x["accion"] == "decir:cambia el tema a bosque" for x in aj["botones"]),
   "Ajustes enseña tu sistema y botones para cambiarlo")
import escritorio_kira as ek
ok(api.es_busqueda("busca aparatos bluetooth") is None if hasattr(api, "es_busqueda") else True,
   "«busca aparatos bluetooth» no abre el buscador")

# ---------- 6) el núcleo (órdenes desde el móvil en casa) y fuera de casa ----------
import nucleo_portatil as npk
core = type("C", (), {"registrar_actividad": lambda s: None, "nueva_tarea": lambda s: None})()
r = npk.ejecutar(core, "Kira, cambia el tema a oceano", lambda f, t: None)
ok("oceano" in r["texto"] and sk.para_pantalla()["tema"] == "oceano", "el núcleo también lo hace (órdenes del móvil en casa)")
import mando_kira as mk
ok(all(not mk.permitida_fuera(x)[0] for x in ("sube el brillo", "apaga el bluetooth", "cambia el tema a bosque",
                                              "apaga la pantalla", "silencio", "al apagar di: adiós")),
   "fuera de casa (Tailscale) no se pasan")

# ---------- 7) iconos nuevos para las ventanas de sus mejoras ----------
import ventanas_kira as vk
v = vk.validar("mi musica", {"en": "escritorio", "texto": "x", "icono": "Música"})
ok(v["icono"] == "musica", "una ventana nueva puede elegir su dibujo")
try:
    vk.validar("x", {"texto": "x", "icono": "<svg>"})
    ok(False, "icono raro")
except vk.VentanaError as e:
    ok("«icono» debe ser" in str(e), "solo dibujos de la lista")
ok("icono" not in vk.validar("y", {"texto": "x"}), "sin icono, como antes")
ok('"icono"' in vk.EJEMPLO_VENTANA or "icono" in vk.EJEMPLO_VENTANA, "el cerebro sabe que puede elegir icono")

# ---------- 8) en la pantalla de verdad (Chromium) ----------
node = shutil.which("node")
html = os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html")
if node:
    js = r"""
const { chromium } = require('playwright');
let b; (async () => { b = await chromium.launch(); const pg = await b.newPage({viewport:{width:1366,height:768}});
  const errs=[]; pg.on('pageerror', e => errs.push(String(e)));
  await pg.goto('file://' + process.argv[2]); await pg.waitForTimeout(300);
  await pg.evaluate(() => { FAKE._extras=[{id:"mi musica",en:"escritorio",titulo:"Mi música",icono:"musica"}];
    FAKE._aspecto={tema:"bosque",colores:{fondo:"#06110b",neon:"#4ade80",acento:"#facc15",texto:"#e6f4ea"},
      ocultos:["mapa","terminal"],salvapantallas:{activo:true,minutos:1,estilo:"estrellas"}}; refrescaBarra(); });
  await pg.waitForTimeout(500);
  const cian = await pg.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--cian').trim());
  const iconos = await pg.$$eval('.icono', l => l.map(x => x.dataset.app));
  const dibujo = await pg.$eval('.icono[data-app="extra:mi musica"] svg', x => x.innerHTML);
  await pg.screenshot({path: process.argv[3]});
  await pg.evaluate(() => mostrarSalva()); await pg.waitForTimeout(500);
  const salva1 = await pg.evaluate(() => ({on: document.getElementById('salva').classList.contains('on'), est: document.getElementById('salva').dataset.estilo, cv: !!document.querySelector('#salva canvas')}));
  await pg.screenshot({path: process.argv[4]});
  await pg.mouse.move(300, 300); await pg.mouse.move(320, 330); await pg.waitForTimeout(200);
  const salva2 = await pg.evaluate(() => document.getElementById('salva').classList.contains('on'));
  await pg.evaluate(() => { ultimoToque = Date.now() - 61000; }); await pg.waitForTimeout(5600);
  const solo = await pg.evaluate(() => document.getElementById('salva').classList.contains('on'));
  await pg.keyboard.press('a'); await pg.waitForTimeout(200);
  const salva3 = await pg.evaluate(() => document.getElementById('salva').classList.contains('on'));
  await pg.evaluate(() => { FAKE._aspecto={tema:"claro",colores:{fondo:"#f4f6fb",neon:"#0e7490",acento:"#be185d",texto:"#111827"},ocultos:[],salvapantallas:{activo:true,minutos:10,estilo:"reloj"}}; refrescaBarra(); });
  await pg.waitForTimeout(400);
  const panel = await pg.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--panel').trim());
  const n2 = await pg.$$eval('.icono', l => l.length);
  console.log(JSON.stringify({errs, cian, iconos, dibujo, salva1, salva2, solo, salva3, panel, n2}));
  await b.close(); })().catch(async e => { console.log('ERR ' + e); if (b) await b.close(); });
"""
    fjs = os.path.join(T, "s.js")
    open(fjs, "w").write(js)
    env = dict(os.environ)
    try:
        env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
    except Exception:
        pass
    r = subprocess.run([node, fjs, html, os.path.join(T, "tema.png"), os.path.join(T, "salva.png")],
                       capture_output=True, text=True, timeout=180, env=env)
    out = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if out.startswith("{"):
        d = json.loads(out)
        ok(not d["errs"], "Chromium: sin errores " + str(d["errs"]))
        ok(d["cian"] == "#4ade80", "Chromium: el tema cambia los colores")
        ok("mapa" not in d["iconos"] and "terminal" not in d["iconos"] and "hablar" in d["iconos"], "Chromium: oculta los iconos pedidos")
        ok("M9 18V5" in d["dibujo"], "Chromium: la ventana nueva lleva su dibujo")
        ok(d["salva1"] == {"on": True, "est": "estrellas", "cv": True}, "Chromium: salvapantallas de estrellas")
        ok(d["salva2"] is False, "Chromium: al mover el ratón se quita")
        ok(d["solo"] is True and d["salva3"] is False, "Chromium: sale solo tras los minutos sin tocar, y una tecla lo quita")
        ok(d["panel"].startswith("rgba(255"), "Chromium: con el tema claro, las ventanas se vuelven claras (se lee)")
        ok(d["n2"] == 12, "Chromium: «vuelve a poner» los iconos")
        print("  capturas:", os.path.join(T, "tema.png"), os.path.join(T, "salva.png"))
    else:
        print("  (sin Chromium)", r.stdout[-800:], r.stderr[-300:])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
