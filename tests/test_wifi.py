# -*- coding: utf-8 -*-
"""v2.88: KiraOS controla la WiFi del portátil (kira_portatil/wifi_kira.py) con un `nmcli` DE MENTIRA que guarda su
estado en un archivo (redes que se ven, guardadas, conectada, radio). Y el enganche: núcleo, ventana, consola, móvil."""
import ast
import json
import os
import stat
import sys
import tempfile
import textwrap

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp()
ESTADO_NM = os.path.join(T, "nm.json")
LOG = os.path.join(T, "nm.log")
NMCLI = os.path.join(T, "nmcli")
open(NMCLI, "w").write("#!" + sys.executable + "\n" + textwrap.dedent(r'''
    import json, sys
    E, LOG = %r, %r
    a = sys.argv[1:]
    open(LOG, "a").write(json.dumps(a) + "\n")
    e = json.load(open(E))
    def fin(code=0, out="", err=""):
        json.dump(e, open(E, "w")); sys.stdout.write(out); sys.stderr.write(err); sys.exit(code)
    def esc(s): return s.replace("\\", "\\\\").replace(":", "\\:")
    if a == ["-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"]:
        st = "connected" if e["conectada"] else ("disconnected" if e["radio"] else "unavailable")
        fin(0, "lo:loopback:unmanaged:--\nwlp2s0:wifi:%%s:%%s\n" %% (st, esc(e["conectada"] or "--")))
    if a == ["radio", "wifi"]:
        fin(0, "enabled\n" if e["radio"] else "disabled\n")
    if a[:2] == ["radio", "wifi"]:
        e["radio"] = a[2] == "on"
        if not e["radio"]: e["conectada"] = None
        fin()
    if a == ["-t", "-f", "NAME,TYPE", "connection", "show"]:
        fin(0, "".join(esc(n) + ":802-11-wireless\n" for n in e["guardadas"]) + "Ethernet:802-3-ethernet\n")
    if a[:6] == ["-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY,CHAN", "device", "wifi", "list"]:
        if not e["radio"]: fin(0, "")
        fin(0, "".join(("*" if r["ssid"] == e["conectada"] else " ") + ":" + esc(r["ssid"]) + ":%%d:%%s:%%d\n"
                       %% (r["senal"], r["seg"] or "--", r["canal"]) for r in e["visibles"]))
    if a[:2] == ["networking", "connectivity"]:
        fin(0, "full\n" if e["conectada"] else "none\n")
    if a[:2] == ["-g", "IP4.ADDRESS"]:
        fin(0, "192.168.1.40/24\n" if e["conectada"] else "")
    vis = {r["ssid"]: r for r in e["visibles"]}
    if a[:3] == ["device", "wifi", "connect"]:
        ssid = a[3]
        if ssid not in vis: fin(10, "", "Error: No network with SSID '%%s' found.\n" %% ssid)
        clave = a[a.index("password") + 1] if "password" in a else None
        if vis[ssid]["seg"] and clave != vis[ssid]["clave"]:
            fin(4, "", "Error: Connection activation failed: Secrets were required, but not provided.\n")
        e["conectada"] = ssid
        if ssid not in e["guardadas"]: e["guardadas"].append(ssid)
        e["claves"][ssid] = clave
        fin(0, "Device 'wlp2s0' successfully activated.\n")
    if a[:3] == ["connection", "up", "id"]:
        ssid = a[3]
        if ssid not in e["guardadas"]: fin(10, "", "Error: unknown connection '%%s'.\n" %% ssid)
        if ssid not in vis: fin(4, "", "Error: Connection activation failed: No network with SSID found.\n")
        if vis[ssid]["seg"] and e["claves"].get(ssid) != vis[ssid]["clave"]:
            fin(4, "", "Error: Connection activation failed: Secrets were required, but not provided.\n")
        e["conectada"] = ssid
        fin(0, "Connection successfully activated\n")
    if a[:3] == ["connection", "modify", "id"]:
        if "wifi-sec.psk" in a: e["claves"][a[3]] = a[a.index("wifi-sec.psk") + 1]
        fin()
    if a[:3] == ["connection", "delete", "id"]:
        e["guardadas"].remove(a[3]); e["claves"].pop(a[3], None)
        if e["conectada"] == a[3]: e["conectada"] = None
        fin()
    if a[:2] == ["device", "disconnect"]:
        e["conectada"] = None
        fin()
    fin(2, "", "Error: argumento raro %%r\n" %% a)
''') % (ESTADO_NM, LOG))
os.chmod(NMCLI, os.stat(NMCLI).st_mode | stat.S_IEXEC)
os.environ["KIRA_NMCLI"] = NMCLI
os.environ["KIRA_WIFI_ESTADO"] = os.path.join(T, "kira_wifi.json")


def red_inicial(**k):
    e = {"radio": True, "conectada": None, "guardadas": [], "claves": {},
         "visibles": [{"ssid": "MiCasa", "senal": 78, "seg": "WPA2", "canal": 6, "clave": "secreto123"},
                      {"ssid": "MiCasa", "senal": 40, "seg": "WPA2", "canal": 44, "clave": "secreto123"},
                      {"ssid": "Bar: Pepe", "senal": 55, "seg": "", "canal": 11, "clave": None},
                      {"ssid": "Vecino", "senal": 30, "seg": "WPA2", "canal": 1, "clave": "otraclave9"}]}
    e.update(k)
    json.dump(e, open(ESTADO_NM, "w"))


def nm():
    return json.load(open(ESTADO_NM))


import wifi_kira as wk

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


# ---------- leer ----------
red_inicial()
ok(wk.interfaz() == "wlp2s0", "encuentra la tarjeta WiFi")
ok(wk._partir(r"*:Bar\: Pepe:55") == ["*", "Bar: Pepe", "55"], "los «:» de dentro de un nombre se respetan")
rs = wk.redes()
ok([r["ssid"] for r in rs] == ["MiCasa", "Bar: Pepe", "Vecino"], "lista sin repetir, la más fuerte primero: "
   + str([r["ssid"] for r in rs]))
ok(rs[0]["senal"] == 78 and rs[0]["segura"] and not rs[1]["segura"], "con su señal y si tiene clave")
e = wk.estado()
ok(e["radio"] and not e["conectada"], "encendida pero sin conectar")
ok("sin conectar" in wk.texto_estado(e), "lo dice claro")

# ---------- conectar ----------
try:
    wk.conectar("MiCasa")
    ok(False, "sin clave")
except wk.WifiError as ex:
    ok("tiene clave" in str(ex) and "portátil" in str(ex), "una red nueva con clave: pide la clave EN el portátil")
try:
    wk.conectar("MiCasa", "corta")
    ok(False, "clave corta")
except wk.WifiError as ex:
    ok("entre 8 y 63" in str(ex), "una clave de menos de 8 no vale")
try:
    wk.conectar("MiCasa", "malaclave1")
    ok(False, "clave mala")
except wk.WifiError as ex:
    ok("no es correcta" in str(ex), "clave equivocada: lo dice en cristiano")
txt = wk.conectar("MiCasa", "secreto123")
ok(nm()["conectada"] == "MiCasa" and "Conectada" in txt and "secreto123" not in txt, "conecta (y no repite la clave)")
ok("secreto123" not in open(os.environ["KIRA_WIFI_ESTADO"]).read(), "la clave NO se guarda en lo de Kira")
e = wk.estado()
ok(e["conectada"] == "MiCasa" and e["senal"] == 78 and e["ip"] == "192.168.1.40" and e["internet"] == "full",
   "estado: red, señal, dirección e internet")
ok("«MiCasa»" in wk.texto_estado(e) and "con internet" in wk.texto_estado(e), "y lo cuenta")
ok("la conozco" in wk.texto_redes(wk.redes()), "ya la recuerda")
ok("Conectada" in wk.conectar("Bar: Pepe"), "una red abierta, sin clave")
ok("Conectada" in wk.conectar("MiCasa") and nm()["conectada"] == "MiCasa", "volver a una conocida, sin clave")
try:
    wk.conectar("NoExiste")
    ok(False, "no existe")
except wk.WifiError as ex:
    ok("No veo la red" in str(ex), "una red que no se ve")
for malo in ("", "x" * 40, "mal\nnombre"):
    try:
        wk.validar_ssid(malo)
        ok(False, f"nombre malo {malo!r}")
    except wk.WifiError:
        ok(True, f"nombre de red rechazado: {malo!r}")

# ---------- la vigilanta ----------
red_inicial(conectada=None, guardadas=["MiCasa"], claves={"MiCasa": "secreto123"})
ok(wk.revisar() and nm()["conectada"] == "MiCasa", "si se cae, vuelve a conectar sola a una red guardada")
ok(wk.revisar() is None, "si está bien, no toca nada")
ok("desconectada" in wk.desconectar().lower() and nm()["conectada"] is None, "desconectar")
ok(wk.revisar() is None and nm()["conectada"] is None, "si la desconectaste TÚ, la vigilanta no la reconecta")
ok("Arreglado" in wk.reparar() and nm()["conectada"] == "MiCasa", "«arregla la wifi» la vuelve a conectar")
ok("apagada" in wk.radio(False).lower() and not nm()["radio"], "apagar la WiFi")
ok(wk.revisar() is None and not nm()["radio"], "apagada por ti: no la enciende sola")
ok("encendida" in wk.radio(True).lower() and nm()["radio"], "encender")
ok(wk.revisar() and nm()["conectada"] == "MiCasa", "y al encenderla vuelve a vigilar")
ok("olvidado" in wk.olvidar("MiCasa") and "MiCasa" not in nm()["guardadas"], "olvidar una red (y su clave)")
ok(len(wk.eventos(50)) >= 5, "apunta lo que pasa (sin claves)")
ok("secreto123" not in open(os.environ["KIRA_WIFI_ESTADO"]).read(), "en lo apuntado nunca hay claves")

# ---------- las órdenes ----------
casos = {"qué wifi tienes": ("estado", None), "Kira, busca redes wifi": ("redes", None),
         "conéctate a la wifi MiCasa": ("conectar", "MiCasa"), 'conéctate a la wifi "Bar: Pepe"': ("conectar", "Bar: Pepe"),
         "conecta la wifi del portátil a la red Vecino": ("conectar", "Vecino"), "apaga la wifi": ("apagar", None),
         "enciende la wifi": ("encender", None), "desconéctate de la wifi": ("desconectar", None),
         "olvida la wifi Vecino": ("olvidar", "Vecino"), "arregla la wifi": ("reparar", None),
         "no tengo internet": ("reparar", None), "redes wifi guardadas": ("guardadas", None),
         "tiene internet el portátil": ("estado", None)}
for frase, esp in casos.items():
    ok(wk.orden_wifi(frase) == esp, f"«{frase}» → {esp}, salió {wk.orden_wifi(frase)}")
for frase in ("hola", "qué es el wifi", "busca en internet gatos", "conéctate al portátil", "estudia redes neuronales"):
    ok(wk.orden_wifi(frase) is None, f"«{frase}» no es una orden de WiFi")
red_inicial()
r = wk.responder("conéctate a la wifi MiCasa con la clave secreto123")
ok("No me escribas la clave" in r and nm()["conectada"] is None, "una clave dentro de la frase no se usa")
ok(wk.ocultar_clave("con la clave secreto123") == "con la clave ••••", "y se tapa al enseñarla")
for frase in ("apaga la wifi", "desconéctate de la wifi", "olvida la wifi Vecino", "conéctate a la wifi X con la clave y"):
    ok(not wk.permitida_remota(frase)[0], f"desde el móvil NO: «{frase}»")
for frase in ("qué wifi tienes", "busca redes wifi", "arregla la wifi", "conéctate a la wifi MiCasa", "hola"):
    ok(wk.permitida_remota(frase)[0], f"desde el móvil sí: «{frase}»")
ok("Redes WiFi que veo" in wk.responder("busca redes wifi"), "responder: buscar")

# ---------- la ventana (la lógica, sin ventana) ----------
import kira_escritorio as ke


class CliFalso:
    grande = False
    def charla(self, t, al_trozo=None):
        al_trozo("charla")


lineas, ctx = [], {}
red_inicial()
r = ke.manejar(CliFalso(), "conéctate a la wifi MiCasa", lineas.append, lambda t: None, ctx=ctx)
ok(r == "wifi" and ctx.get("pedir_clave") == "MiCasa" and "puntitos" in lineas[-1],
   "en la ventana, una red con clave abre la ventanita de la clave: " + str(lineas))
r = ke.manejar(CliFalso(), "qué wifi tienes", lineas.append, lambda t: None)
ok(r == "wifi" and "sin conectar" in lineas[-1], "la ventana contesta la WiFi ella misma")
trozos = []
ok(ke.manejar(CliFalso(), "hola", lineas.append, trozos.append) == "charla" and trozos == ["charla"],
   "lo demás sigue siendo charla")
src = open(os.path.join(RAIZ, "kira_portatil", "kira_escritorio.py"), encoding="utf-8").read()
ok('("WiFi", lambda: abrir_wifi())' in src and 'show="*"' in src and "wk.ocultar_clave(t)" in src,
   "botón WiFi, la clave con puntitos y la frase sin la clave en pantalla")

# ---------- la consola ----------
import kira_consola as kc
red_inicial()
ok("Conectada" in kc.consola_wifi("/wifi conecta MiCasa", pedir_clave=lambda _p: "secreto123"),
   "consola: /wifi conecta (la clave se pide sin eco)")
ok("«MiCasa»" in kc.consola_wifi("/wifi") and kc.consola_wifi("hola") is None, "consola: /wifi y lo demás no")
ok("Usa:" in kc.consola_wifi("/wifi raro"), "consola: ayuda")

# ---------- el núcleo del portátil ----------
import nucleo_portatil as npo
ok(npo.es_local("127.0.0.1") and npo.es_local("::1") and not npo.es_local("192.168.1.33"), "sabe qué viene del portátil")
r = npo.ejecutar(type("C", (), {"registrar_actividad": lambda s: None, "nueva_tarea": lambda s: None})(),
                 "qué wifi tienes", lambda fr, t: None)
ok("«MiCasa»" in r["texto"], "una orden de WiFi la hace el núcleo")
srcn = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("es_local(self.client_address[0])" in srcn and "permitida_remota(orden)" in srcn, "desde el móvil, con candado")
ok("wk.vigilar" in srcn and "--sin-wifi" in srcn, "la vigilanta arranca con el núcleo")
ok("wifi" in npo.actividad(type("C", (), {"dir": T})()), "/hola cuenta la WiFi")
sh = open(os.path.join(RAIZ, "kira_portatil", "instalar_portatil.sh"), encoding="utf-8").read()
ok("kira-wifi" in sh and "50-kira-wifi.rules" in sh and "enable-disable-wifi" in sh, "el instalador pone el permiso")

# ---------- el móvil ----------
import mando_kira as mdk
for f in ("qué wifi tiene el portátil", "arregla la wifi de KiraOS", "tiene internet el portátil"):
    ok(mdk.es_wifi_kiraos(f) and not mdk.wifi_solo_en_portatil(f), f"móvil: «{f}» se lo pasa a KiraOS")
for f in ("apaga la wifi del portátil", "conecta el portátil a la wifi X con la clave y", "olvida la wifi del portátil"):
    ok(mdk.wifi_solo_en_portatil(f), f"móvil: «{f}» solo en el portátil")
ok(not mdk.es_wifi_kiraos("no tengo internet"), "«no tengo internet» habla del móvil, no del portátil")
import ordenes_kira as okr
O = os.path.join(T, "o")
okr.apuntar(O, "conecta el portátil a la wifi X con la clave secreto123", "kiraos")
ok("secreto123" not in json.dumps(okr.ultimas(O)), "una clave nunca queda en el historial de órdenes")
import tablero_kira as tbk
tx = tbk.tarjeta_kiraos({"kiraos": {"version": "2.88", "actividad": {"wifi": {"ssid": "MiCasa", "senal": 78,
                                                                              "internet": "full"}}}})["texto"]
ok("WiFi: «MiCasa» (78 %)" in tx, "el panel del móvil enseña la WiFi de KiraOS")
src_i = open(os.path.join(RAIZ, "interfaz_kira.py"), encoding="utf-8").read()
i_w, i_t = src_i.find("mdk_.es_wifi_kiraos(orden)"), src_i.find("es_t = mdk_.es_trabajo(orden)")
ok(0 < i_w < i_t, "en el móvil, la WiFi del portátil se mira antes que el trabajo")
ast.parse(src_i)
print("\nTODO BIEN", n)
