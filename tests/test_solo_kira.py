# -*- coding: utf-8 -*-
"""v3.05: al encender el portátil, SOLO Kira: su pantalla de arranque (el orbe, en vez del logo de Xubuntu) y su
propia sesión (kiraos-sesion) sin cargar el escritorio de Xubuntu; «Ir a Xubuntu» o Alt+F4 abren el escritorio; si
Kira se cae, se reabre (y a los 3 fallos seguidos, Xubuntu: nunca pantalla negra). Aquí se prueban los guiones de
verdad con bash sobre una raíz falsa."""
import os
import struct
import subprocess
import sys
import tempfile
import zlib

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POR = os.path.join(RAIZ, "kira_portatil")
sys.path.insert(0, POR)
T = tempfile.mkdtemp()
n = 0


def ok(c, m):
    global n
    n += 1
    print(("[OK] " if c else "[X] ") + m)
    if not c:
        sys.exit(1)


# ---------- el logo de arranque ----------
import logo_arranque_kira as lg  # noqa: E402
png = lg.png_orbe(120)
ok(png[:8] == b"\x89PNG\r\n\x1a\n", "el orbe es un PNG de verdad")
ancho, alto = struct.unpack(">II", png[16:24])
ok((ancho, alto) == (120, 120), "del tamaño pedido")
idat = png[png.index(b"IDAT") + 4: png.index(b"IEND") - 8]
crudo = zlib.decompress(idat)
fila = 1 + 120 * 4


def pix(x, y):
    return tuple(crudo[y * fila + 1 + x * 4: y * fila + 1 + x * 4 + 4])


ok(pix(60, 60)[3] == 255 and pix(0, 0)[3] == 0, "orbe opaco en el centro y fondo transparente en las esquinas")
d = lg.escribir(os.path.join(T, "tema"))
scr = open(os.path.join(d, "kira.script"), encoding="utf-8").read()
ok('Image("orbe.png")' in scr and "SetRefreshFunction" in scr and "if (texto)" in scr,
   "el tema de arranque: el orbe que late (y «KIRA» encima si se puede)")
ok("SetDisplayPasswordFunction" in scr, "si algún día pide clave del disco, se ve dónde escribirla")
ok("ScriptFile=/usr/share/plymouth/themes/kira/kira.script" in open(os.path.join(d, "kira.plymouth")).read(),
   "el archivo del tema apunta a su sitio")

# ---------- la sesión de Kira ----------
ses = os.path.join(POR, "kiraos_sesion.sh")
ok(subprocess.run(["bash", "-n", ses]).returncode == 0, "kiraos_sesion.sh sin errores de sintaxis")


def sesion(cuerpo_kiraos):
    k = os.path.join(T, "kiraos_falso")
    cuenta = os.path.join(T, "cuenta")
    marca = os.path.join(T, "marca")
    for f in (cuenta, marca):
        if os.path.exists(f):
            os.remove(f)
    open(k, "w").write("#!/bin/bash\necho x >> " + cuenta + "\n" + cuerpo_kiraos.replace("MARCA", marca) + "\n")
    os.chmod(k, 0o755)
    env = dict(os.environ, KIRA_KIRAOS=k, KIRA_MARCA=marca, KIRA_ESCRITORIO="echo ESCRITORIO")
    r = subprocess.run(["bash", ses], capture_output=True, text=True, env=env, timeout=60)
    veces = len(open(cuenta).read().split()) if os.path.exists(cuenta) else 0
    return r.stdout, veces


out, veces = sesion("exit 0")
ok("ESCRITORIO" in out and veces == 1, "si cierras Kira (Alt+F4), se abre el escritorio de Xubuntu")
out, veces = sesion('[ $(wc -l < "$(dirname $0)/cuenta") -ge 2 ] && echo 1 > MARCA; exit 1')
ok("ESCRITORIO" in out and veces == 2, "«Ir a Xubuntu» (la marca) lleva al escritorio")
out, veces = sesion("exit 1")
ok("ESCRITORIO" in out and veces == 3, "si Kira se cae, se reabre; a los 3 fallos seguidos, Xubuntu (nunca negro)")
src = open(ses, encoding="utf-8").read()
ok("xfsettingsd" in src and "xfwm4" in src and "KIRA_DESDE_KIRA=1" in src,
   "carga lo justo de Xubuntu (teclado español y ventanas) y avisa al escritorio de que viene de Kira")

# ---------- solo_kira.sh sobre una raíz falsa ----------
R = os.path.join(T, "raiz")
for c in ("etc/lightdm/lightdm.conf.d", "usr/share/xsessions", "usr/share/plymouth/themes", "etc/default"):
    os.makedirs(os.path.join(R, c), exist_ok=True)
open(os.path.join(R, "etc/lightdm/lightdm.conf"), "w").write("[Seat:*]\nautologin-user=\n")
open(os.path.join(R, "usr/share/xsessions/xubuntu.desktop"), "w").write("[Desktop Entry]\nName=Xubuntu\n")
open(os.path.join(R, "etc/default/grub"), "w").write('GRUB_DEFAULT=0\nGRUB_CMDLINE_LINUX_DEFAULT=""\n')
CASA = os.path.join(T, "casa")
os.makedirs(CASA)
env = dict(os.environ, KIRA_RAIZ_SIS=R, KIRA_USUARIO="papi", HOME=CASA)
sh = os.path.join(POR, "solo_kira.sh")
ok(subprocess.run(["bash", "-n", sh]).returncode == 0, "solo_kira.sh sin errores de sintaxis")
r = subprocess.run(["bash", sh], capture_output=True, text=True, env=env, timeout=120)
ok(r.returncode == 0 and "[OK] Listo" in r.stdout, "solo_kira.sh termina bien")
tk = os.path.join(R, "usr/share/plymouth/themes/kira")
ok(all(os.path.exists(os.path.join(tk, f)) for f in ("orbe.png", "kira.script", "kira.plymouth")),
   "pone el tema de arranque de Kira")
ok("update-alternatives --set default.plymouth /usr/share/plymouth/themes/kira/kira.plymouth" in r.stdout
   and "update-initramfs -u" in r.stdout, "y lo deja como el de por defecto (y rehace el arranque)")
grub = open(os.path.join(R, "etc/default/grub")).read()
ok('GRUB_CMDLINE_LINUX_DEFAULT="quiet splash' in grub and os.path.exists(os.path.join(R, "etc/default/grub.kira-copia")),
   "si el arranque no tenía «splash», se lo pone (con copia)")
x = os.path.join(R, "usr/local/bin/kiraos-sesion")
ok(os.access(x, os.X_OK) and "Exec=/usr/local/bin/kiraos-sesion" in open(
    os.path.join(R, "usr/share/xsessions/kiraos.desktop")).read(), "crea la sesión «KiraOS»")
conf = open(os.path.join(R, "etc/lightdm/lightdm.conf.d/50-kira.conf")).read()
ok("autologin-user=papi" in conf and "autologin-session=kiraos" in conf,
   "al encender entra directo en la sesión de Kira (no en la de Xubuntu)")
ok("# (Kira) autologin-user=" in open(os.path.join(R, "etc/lightdm/lightdm.conf")).read(),
   "y sigue anulando lo que lo estropeaba (v2.99)")
auto = open(os.path.join(CASA, ".config/autostart/kira-arranque.desktop")).read()
ok("KIRA_DESDE_KIRA" in auto and "/usr/local/bin/kiraos" in auto,
   "en el escritorio de Xubuntu, Kira no se vuelve a abrir sola si vienes de Kira")
r = subprocess.run(["bash", sh, "--deshacer"], capture_output=True, text=True, env=env, timeout=60)
conf = open(os.path.join(R, "etc/lightdm/lightdm.conf.d/50-kira.conf")).read()
ok(r.returncode == 0 and "autologin-session=xubuntu" in conf, "--deshacer: vuelve a la sesión de Xubuntu")
ok("update-alternatives --remove default.plymouth" in r.stdout, "y quita el tema de arranque de Kira")
ok("KIRA_DESDE_KIRA" not in open(os.path.join(CASA, ".config/autostart/kira-arranque.desktop")).read(),
   "y Kira se abre otra vez encima de Xubuntu, como antes")
ok(sorted(x for x in os.listdir(POR) if x.startswith("sol")) == ["solo_kira.sh"], "«bash solo» + Tab lo completa")

# ---------- «Ir a Xubuntu» deja la marca para la sesión ----------
os.environ["HOME"] = CASA
import escritorio_kira as esk  # noqa: E402


class Api(esk.EscritorioMixin):
    pass


res = Api().salir_a_linux(cerrar=lambda: None)
ok(res["ok"] and os.path.exists(os.path.join(CASA, ".kira_ir_a_xubuntu")),
   "«Ir a Xubuntu» deja la marca para que la sesión abra el escritorio")
ok("solo_kira.sh" in open(os.path.join(POR, "instalar_portatil.sh"), encoding="utf-8").read(),
   "el instalador lo deja así en las instalaciones nuevas")
print("\nTODO BIEN", n)
