# -*- coding: utf-8 -*-
"""v2.99: arreglar_inicio.sh — entrar directo al encender (sin la pantalla de contraseña de Xubuntu). Se corre el guion
DE VERDAD con bash sobre una carpeta que hace de «/» y con groupadd/gpasswd/getent de mentira."""
import os
import stat
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUION = os.path.join(RAIZ, "kira_portatil", "arreglar_inicio.sh")
n = 0


def ok(c, m):
    global n
    n += 1
    print(("[OK] " if c else "[X] ") + m)
    if not c:
        sys.exit(1)


def escribir(ruta, texto):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w") as f:
        f.write(texto)


def sistema(principal=None, otros=None, sesiones=("xubuntu", "xfce"), gdm=False):
    """Una carpeta que hace de «/» con LightDM (o GDM) y unos comandos de grupos de mentira que apuntan lo que se pide."""
    r = tempfile.mkdtemp(prefix="kira_raiz_")
    if gdm:
        os.makedirs(os.path.join(r, "etc/gdm3"))
    else:
        os.makedirs(os.path.join(r, "etc/lightdm/lightdm.conf.d"))
        if principal is not None:
            escribir(os.path.join(r, "etc/lightdm/lightdm.conf"), principal)
        for nombre, texto in (otros or {}).items():
            escribir(os.path.join(r, "etc/lightdm/lightdm.conf.d", nombre), texto)
    for s in sesiones:
        escribir(os.path.join(r, "usr/share/xsessions", s + ".desktop"), "[Desktop Entry]\n")
    bin_ = os.path.join(r, "_bin")
    os.makedirs(bin_)
    for orden, cod in (("getent", 2), ("groupadd", 0), ("gpasswd", 0)):
        p = os.path.join(bin_, orden)
        escribir(p, f'#!/bin/sh\necho "{orden} $*" >> "{r}/_llamadas"\nexit {cod}\n')
        os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
    return r


def correr(r, usuario="papi"):
    env = dict(os.environ, KIRA_RAIZ_SIS=r, KIRA_USUARIO=usuario,
               PATH=os.path.join(r, "_bin") + os.pathsep + os.environ["PATH"])
    return subprocess.run(["bash", GUION], capture_output=True, text=True, env=env, timeout=30)


def leer(r, rel):
    p = os.path.join(r, rel)
    return open(p).read() if os.path.isfile(p) else None


# ---------- el caso del Packard Bell: el principal deja la entrada automática VACÍA y la anula ----------
PRINCIPAL = "[Seat:*]\ngreeter-session=lightdm-gtk-greeter\nautologin-user=\nautologin-session=\n"
r = sistema(principal=PRINCIPAL, otros={"70-otro.conf": "[Seat:*]\nautologin-user=invitado\n",
                                         "10-antes.conf": "[Seat:*]\nautologin-user=nadie\n"})
p = correr(r)
ok(p.returncode == 0 and "Listo" in p.stdout, "el guion termina bien " + p.stderr[-200:])
kira = leer(r, "etc/lightdm/lightdm.conf.d/50-kira.conf")
ok("[Seat:*]" in kira and "autologin-user=papi" in kira and "autologin-user-timeout=0" in kira,
   "escribe la entrada automática de Kira para tu usuario")
ok("autologin-session=xubuntu" in kira, "y dice qué sesión abrir (la de Xubuntu)")
pr = leer(r, "etc/lightdm/lightdm.conf")
ok("# (Kira) autologin-user=" in pr and "# (Kira) autologin-session=" in pr,
   "el archivo PRINCIPAL ya no anula la entrada automática (se comenta su línea vacía)")
ok("greeter-session=lightdm-gtk-greeter" in pr and not pr.count("# (Kira) greeter"), "lo demás del principal, intacto")
ok(leer(r, "etc/lightdm/lightdm.conf.kira-copia") == PRINCIPAL, "guarda una copia del principal tal como estaba")
ok("# (Kira) autologin-user=invitado" in leer(r, "etc/lightdm/lightdm.conf.d/70-otro.conf"),
   "un archivo que va DETRÁS del de Kira también se neutraliza")
ok(leer(r, "etc/lightdm/lightdm.conf.d/10-antes.conf") == "[Seat:*]\nautologin-user=nadie\n",
   "uno que va ANTES no se toca (no manda)")
llam = leer(r, "_llamadas")
ok("groupadd -r autologin" in llam and "gpasswd -a papi autologin" in llam, "te mete en el grupo autologin")

# segunda vez: no duplica nada
p = correr(r)
pr2 = leer(r, "etc/lightdm/lightdm.conf")
ok(p.returncode == 0 and pr2 == pr and "# (Kira) # (Kira)" not in pr2, "lanzarlo otra vez no estropea nada")
ok(leer(r, "etc/lightdm/lightdm.conf.kira-copia") == PRINCIPAL, "la copia sigue siendo la original")

# ---------- otros casos ----------
r = sistema(principal=None, sesiones=("xfce",))
p = correr(r)
ok(p.returncode == 0 and "autologin-session=xfce" in leer(r, "etc/lightdm/lightdm.conf.d/50-kira.conf"),
   "sin archivo principal y con Xfce: también vale")
r = sistema(principal=None, sesiones=())
p = correr(r)
kira = leer(r, "etc/lightdm/lightdm.conf.d/50-kira.conf")
ok(p.returncode == 0 and "autologin-user=papi" in kira and "autologin-session" not in kira,
   "si no encuentra la sesión, no se inventa una")
r = sistema(gdm=True)
p = correr(r)
ok(p.returncode == 0 and "AutomaticLogin=papi" in leer(r, "etc/gdm3/custom.conf"), "con GDM (Ubuntu normal) también")
r = sistema(principal=None)
p = correr(r, usuario="root")
ok(p.returncode == 1 and "root" in p.stdout, "no deja entrar como root sin contraseña")

# ---------- el instalador lo usa ----------
inst = open(os.path.join(RAIZ, "kira_portatil", "instalar_portatil.sh"), encoding="utf-8").read()
ok('bash "$AQUI/arreglar_inicio.sh"' in inst, "el instalador usa este mismo guion para LightDM")
ok(subprocess.run(["bash", "-n", GUION]).returncode == 0, "el guion no tiene errores de sintaxis")

print("\nTODO BIEN", n)
