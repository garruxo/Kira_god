# -*- coding: utf-8 -*-
"""v3.44: Kira estudia el hardware y los drivers del portátil (solo lectura) y deja un aviso prioritario."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
TMP = tempfile.mkdtemp()
os.environ["KIRA_AVISOS"] = os.path.join(TMP, "avisos.json")
os.environ["KIRA_HARDWARE"] = os.path.join(TMP, "hardware.json")

import avisos_kira as av          # noqa: E402
import hardware_kira as hw        # noqa: E402
import mando_kira as mk           # noqa: E402
import estudio_kira as ek         # noqa: E402

N = 0


def ok(c, msg):
    global N
    if not c:
        print("FALLA:", msg)
        sys.exit(1)
    N += 1


LSPCI = """00:00.0 Host bridge [0600]: Intel Corporation Core Processor DRAM Controller [8086:0044] (rev 02)
\tSubsystem: Acer Incorporated [ALI] Device [1025:0347]
\tKernel driver in use: agpgart-intel
00:02.0 VGA compatible controller [0300]: Intel Corporation Core Processor Integrated Graphics Controller [8086:0046] (rev 02)
\tKernel driver in use: i915
\tKernel modules: i915
00:1a.0 USB controller [0c03]: Intel Corporation 5 Series/3400 Series Chipset USB2 Enhanced Host Controller [8086:3b3c] (rev 05)
\tKernel driver in use: ehci-pci
00:1b.0 Audio device [0403]: Intel Corporation 5 Series/3400 Series Chipset High Definition Audio [8086:3b56] (rev 05)
\tKernel driver in use: snd_hda_intel
\tKernel modules: snd_hda_intel
00:1f.2 SATA controller [0106]: Intel Corporation 5 Series/3400 Series Chipset 4 port SATA AHCI Controller [8086:3b29] (rev 05)
\tKernel driver in use: ahci
\tKernel modules: ahci
02:00.0 Ethernet controller [0200]: Broadcom Inc. and subsidiaries NetLink BCM57780 Gigabit Ethernet PCIe [14e4:1692] (rev 01)
\tSubsystem: Acer Incorporated [ALI] Device [1025:0347]
\tKernel driver in use: tg3
\tKernel modules: tg3
03:00.0 Network controller [0280]: Qualcomm Atheros AR9287 Wireless Network Adapter (PCI-Express) [168c:002e] (rev 01)
\tKernel driver in use: ath9k
\tKernel modules: ath9k
"""
LSUSB = """Bus 002 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
Bus 001 Device 003: ID 064e:a219 Suyin Corp. 1.3M WebCam
Bus 001 Device 004: ID 0781:5567 SanDisk Corp. Cruzer Blade
"""
MODINFO = {
    "tg3": "filename: /lib/modules/6.8/tg3.ko\nfirmware: tigon/tg3_tso5.bin\nfirmware: tigon/tg3.bin\n"
           "license: GPL\ndescription: Broadcom Tigon3 ethernet driver\n",
    "ath9k": "filename: /lib/modules/6.8/ath9k.ko\nlicense: Dual BSD/GPL\n"
             "description: Support for Atheros 802.11n wireless LAN cards.\n",
}
LLAMADAS = []


def correr(args):
    LLAMADAS.append(list(args))
    if args[0] == "lspci":
        return 0, LSPCI
    if args[0] == "lsusb":
        return 0, LSUSB
    if args[0] == "lsmod":
        return 0, "Module Size Used by\ntg3 200000 0\nath9k 100000 0\n"
    if args[0] == "uname":
        return 0, "6.8.0-48-generic\n"
    if args[0] == "modinfo":
        return (0, MODINFO[args[1]]) if args[1] in MODINFO else (1, "not found")
    return 127, ""


# --- leer lspci / lsusb / modinfo ---
p = hw.leer_lspci(LSPCI)
ok(len(p) == 7, "siete piezas PCI")
red = [x for x in p if x["clase_id"] == "0200"][0]
ok(red["id"] == "14e4:1692" and red["driver"] == "tg3" and red["rev"] == "01", "la red por cable con su chip y driver")
ok(red["subsistema"].startswith("Acer"), "subsistema")
wifi = [x for x in p if x["clase_id"] == "0280"][0]
ok(wifi["id"] == "168c:002e" and wifi["modulos"] == ["ath9k"], "la WiFi Atheros")
u = hw.leer_lsusb(LSUSB)
ok(len(u) == 2 and u[0]["id"] == "064e:a219", "USB sin los hubs de raíz")
mi = hw.leer_modinfo(MODINFO["tg3"])
ok(mi["descripcion"].startswith("Broadcom") and mi["firmware"] == ["tigon/tg3_tso5.bin", "tigon/tg3.bin"], "modinfo")

# --- qué sabe el kernel de Kira (honesto) ---
ok(hw.para_kira({"clase_id": "0106"}).startswith("sí"), "AHCI: sí")
ok(hw.para_kira({"clase_id": "0200", "id": "14e4:1692"}).startswith("no"), "tg3: todavía no")
ok(hw.para_kira({"clase_id": "0200", "id": "8086:100e"}).startswith("sí"), "e1000: sí")
ok("WPA2" in hw.para_kira({"clase_id": "0280"}), "WiFi: dice que es muy difícil")
ok(hw.para_kira({"clase_id": "0300"}).startswith("en parte"), "gráfica: solo texto")

# --- estudio completo, solo lectura ---


class Baul:
    def __init__(self):
        self.g = []

    def guardar(self, texto, tema="", fuente="usuario", pregunta=""):
        self.g.append((tema, texto, fuente))
        return len(self.g)


class Core:
    recuerdos = Baul()


pasos = []
r = hw.hacer(Core, correr=correr, al_paso=lambda f, t: pasos.append((f, t)))
ok(all(a[0] in ("lspci", "lsusb", "lsmod", "uname", "modinfo") for a in LLAMADAS), "solo órdenes de mirar")
ok(not any(a[0] in ("modprobe", "rmmod", "insmod", "sudo") for a in LLAMADAS), "nunca carga/quita drivers ni usa sudo")
ok(["modinfo", "tg3"] in LLAMADAS and ["modinfo", "ath9k"] in LLAMADAS, "estudia cada driver con modinfo")
ok(pasos and pasos[0][0] < pasos[-1][0], "avanza la barra")
t = r["texto"]
ok("7 piezas" in t and "2 por USB" in t, "resumen: cuántas piezas")
ok("14e4:1692" in t and "tg3" in t and "ath9k" in t, "dice los chips y los drivers de Xubuntu")
ok("Host bridge" not in t and "puente del procesador" not in t, "no aburre con los puentes")
ok("hardware.json" in t, "dice dónde lo guardó")
ok(os.path.exists(os.environ["KIRA_HARDWARE"]), "informe guardado")
ok(oct(os.stat(os.environ["KIRA_HARDWARE"]).st_mode & 0o777) == "0o600", "informe 0600")
inf = hw.cargar()
ok(inf["nucleo_linux"] == "6.8.0-48-generic" and inf["drivers"]["tg3"]["firmware"], "informe con el Linux y el firmware")
ok(len(Core.recuerdos.g) == 8 and all(g[2] == "hardware" for g in Core.recuerdos.g), "fichas en el baúl (7 + USB)")
ok(any("tigon/tg3.bin" in g[1] for g in Core.recuerdos.g), "la ficha de la red dice su firmware")

# --- aviso prioritario ---
a = av.pendiente()
ok(a and "estudiado tu portátil" in a["texto"] and "14e4:1692" in a["texto"] and "pendrive" in a["texto"],
   "aviso prioritario con la red por cable y el pendrive")
ok(oct(os.stat(os.environ["KIRA_AVISOS"]).st_mode & 0o777) == "0o600", "avisos 0600")
av.visto(a["id"])
ok(av.pendiente() is None, "«Visto» lo quita")

# sin lspci no inventa
r2 = hw.hacer(None, correr=lambda a: (127, ""), avisar=True)
ok("pciutils" in r2["texto"] and av.pendiente() is None, "sin lspci lo dice y no avisa")

# --- reconocer la orden ---
for f in ("estudia tu hardware", "Kira, estudia los drivers del portátil", "estudia tus controladores",
          "analiza las piezas del portátil", "estudia todo el sistema xubuntu", "estudia todo tu sistema",
          "qué drivers tienes", "estudia el packard bell"):
    ok(hw.es_orden(f.replace("Kira, ", "")), "reconoce: " + f)
    if "tu sistema" in f:              # en el móvil «tu sistema» sería el del móvil: ahí no se manda
        continue
    ok(mk.es_trabajo(f), "desde el móvil va a KiraOS: " + f)
    ok(ek.es_estudia_general(f) is None, "no es el estudio general por internet: " + f)
for f in ("estudia python", "estudia redes neuronales", "dime la hora", "estudia la historia de roma"):
    ok(not hw.es_orden(f), "no se come: " + f)
ok(ek.es_estudia_general("estudia python") == "python", "estudia python sigue igual")

# --- cableado ---
src = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("hw_.es_orden(o)" in src and src.index("hw_.es_orden(o)") < src.index("tk_.orden(o)"), "el núcleo lo atiende")
es = open(os.path.join(RAIZ, "kira_portatil", "escritorio_kira.py"), encoding="utf-8").read()
ok('"prioritario": self._prioritario()' in es and "def aviso_visto" in es, "la barra lleva el aviso")
html = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html"), encoding="utf-8").read()
ok('id="prio"' in html and "pintaPrio(d.prioritario)" in html and 'llama("aviso_visto"' in html, "franja en el escritorio")
ok("textContent=PRIO.texto" in html, "el aviso se pinta como texto (no HTML)")

# --- el puente del escritorio dice el aviso una vez ---
import escritorio_kira as esk     # noqa: E402


class Api(esk.EscritorioMixin):
    def __init__(self):
        self.dichos = []

    def _hablar(self, t):
        self.dichos.append(t)


av.prioritario("Prueba de aviso", titulo="T", notificar=False)
api = Api()
api.voz_activa = True
d1 = api._prioritario()
d2 = api._prioritario()
import time as _t  # noqa: E402
_t.sleep(0.2)
ok(d1 and d1["texto"] == "Prueba de aviso" and d2, "el puente devuelve el aviso")
ok(api.dichos == ["Prueba de aviso"], "lo dice en voz alta UNA vez")
api.aviso_visto(d1["id"])
ok(api._prioritario() is None, "visto desde el escritorio")

# --- en Chromium: la franja sale y «Visto» la quita ---
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
if sync_playwright:
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        pg.goto("file://" + os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html") + "#quedarse")
        pg.wait_for_timeout(400)
        pg.evaluate("pintaBarra({prioritario:{id:'1',titulo:'Kira ha estudiado tu portátil',"
                    "texto:'<b>x</b> Ya he estudiado tu portátil'}})")
        ok(pg.is_visible("#prio") and "<b>x</b>" in pg.inner_text("#prioTxt"), "Chromium: franja visible, como texto")
        pg.click("#prioVisto")
        ok(not pg.is_visible("#prio"), "Chromium: «Visto» la quita")
        b.close()

print(f"TODO BIEN ({N})")
