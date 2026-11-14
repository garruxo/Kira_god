"""v3.61: estudiar_interruptor.sh — en Xubuntu, mira cómo enciende Linux la radio (EC + rfkill acer-wireless)."""
import os, subprocess, sys, tempfile, threading, time
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUION = os.path.join(RAIZ, "kira_portatil", "estudiar_interruptor.sh")
fallos = 0
def ok(c, m):
    global fallos
    print(("OK   " if c else "FALLA ") + m)
    if not c: fallos += 1

def montar(t, con_acer=True):
    sysd = os.path.join(t, "sys"); dbg = os.path.join(t, "dbg"); dest = os.path.join(t, "kernel")
    os.makedirs(os.path.join(sysd, "class", "dmi", "id"))
    for k, v in {"sys_vendor": "Packard Bell", "product_name": "EasyNote TM86", "bios_version": "V1.14"}.items():
        open(os.path.join(sysd, "class", "dmi", "id", k), "w").write(v + "\n")
    def rf(n, name, tipo):
        d = os.path.join(sysd, "class", "rfkill", n); os.makedirs(d)
        for k, v in {"name": name, "type": tipo, "hard": "0", "soft": "0", "state": "1"}.items():
            open(os.path.join(d, k), "w").write(v + "\n")
        return d
    rf("rfkill0", "phy0", "wlan")
    acer = rf("rfkill1", "acer-wireless", "wlan") if con_acer else None
    os.makedirs(os.path.join(dbg, "ec", "ec0"))
    ec = bytearray(256); ec[0x3B] = 0x15
    open(os.path.join(dbg, "ec", "ec0", "io"), "wb").write(bytes(ec))
    a9 = os.path.join(dbg, "ieee80211", "phy0", "ath9k"); os.makedirs(a9)
    open(os.path.join(a9, "regidx"), "w").write("0x0")
    open(os.path.join(a9, "regval"), "w").write("0x0037f800\n")
    return sysd, dbg, dest, acer, a9

def correr(sysd, dbg, dest, extra=None):
    env = dict(os.environ, KIRA_PRUEBA="1", KIRA_SUDO="", KIRA_SYS=sysd, KIRA_DEBUGFS=dbg, KIRA_KERNEL=dest, KIRA_ESPERA="1")
    return subprocess.run(["bash", GUION], env=env, capture_output=True, text=True, timeout=60)

with tempfile.TemporaryDirectory() as t:
    sysd, dbg, dest, acer, a9 = montar(t)
    parar = []
    def ec_que_sigue():                         # el «controlador»: el byte 0x3B sigue al interruptor
        io = os.path.join(dbg, "ec", "ec0", "io")
        while not parar:
            st = open(os.path.join(acer, "state")).read().strip()
            ec = bytearray(open(io, "rb").read())
            ec[0x3B] = 0x15 if st == "1" else 0x14
            open(io, "wb").write(bytes(ec))
            open(os.path.join(a9, "regval"), "w").write("0x0037f800\n" if st == "1" else "0x0037f000\n")
            time.sleep(0.05)
    h = threading.Thread(target=ec_que_sigue); h.start()
    r = correr(sysd, dbg, dest)
    parar.append(1); h.join()
    s = r.stdout
    inf = open(os.path.join(dest, "interruptor.txt")).read()
    ok("EasyNote TM86" in s and "V1.14" in s, "dice el modelo y la BIOS")
    ok("acer-wireless" in s and "phy0" in s, "enseña los interruptores de radio de Linux")
    ok("0x3B: 15 -> 14 -> 15" in s, "encuentra el byte del controlador que sigue al interruptor: " + s[-400:])
    ok("0x0037f800" in s and "0x0037f000" in s, "lee la entrada GPIO de la tarjeta en las tres fases")
    ok(open(os.path.join(acer, "state")).read().strip() == "1", "la WiFi queda ENCENDIDA al acabar")
    ok(open(os.path.join(sysd, "class", "rfkill", "rfkill0", "state")).read().strip() == "1", "no toca el interruptor phy0")
    ok(oct(os.stat(os.path.join(dest, "interruptor.txt")).st_mode & 0o777) == "0o600", "el informe es solo tuyo (0600)")
    ok("#EC_ANTES" in inf and "#EC_APAGADA" in inf, "el informe guarda los volcados")

with tempfile.TemporaryDirectory() as t:
    sysd, dbg, dest, _, _ = montar(t, con_acer=False)
    r = correr(sysd, dbg, dest)
    ok("No hay interruptor acer-wireless" in r.stdout, "sin acer-wireless lo dice y no apaga nada")

g = open(GUION).read()
ok("write_support=0" in g and "> \"$EC\"" not in g, "el controlador del portátil SOLO se lee")
ok("regval\" 2>/dev/null" in g and "> \"$p/regval\"" not in g, "en la tarjeta solo se escribe el índice, nunca un valor")
env = dict(os.environ); env.pop("KIRA_PRUEBA", None)
if os.geteuid() == 0:
    r = subprocess.run(["bash", GUION], env=env, capture_output=True, text=True)
    ok("No lo lances con sudo" in r.stdout, "se niega a correr con sudo delante")
print("TODO BIEN" if not fallos else f"{fallos} FALLOS"); sys.exit(1 if fallos else 0)
