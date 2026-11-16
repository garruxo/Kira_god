# -*- coding: utf-8 -*-
"""v3.93: Kira superadministradora CON TU CONTRASEÑA (pkexec/polkit): reconocer la orden, candados, la línea que se
ejecuta (ventana o permiso de paquetes), cancelar, registro, el ayudante de verdad con bash, el guion de activar sobre
una raíz falsa, y que desde el núcleo/móvil no se hace."""
import os, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATOS_NUCLEO"] = T
os.environ["KIRA_ADMIN_LOG"] = os.path.join(T, "admin.log")
os.environ["KIRA_ADMIN_AYUDANTE"] = os.path.join(T, "no_hay_kira_admin")
os.environ["KIRA_ADMIN_POLITICA"] = os.path.join(T, "no_hay.policy")
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import admin_kira as ad

fallos = n = 0
def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1

# ---------- reconocer la orden ----------
o = ad.orden("ejecuta como administrador apt-get update")
ok(o == ("ejecutar", [["apt-get", "update"]]), "«ejecuta como administrador apt-get update» " + str(o))
o = ad.orden("Kira, como root: ls -la /root")
ok(o == ("ejecutar", [["ls", "-la", "/root"]]), "«como root: ls -la /root» " + str(o))
o = ad.orden("instala vlc como administrador")
ok(o == ("ejecutar", [["apt-get", "install", "-y", "vlc"]]), "«instala vlc como administrador» " + str(o))
o = ad.orden("instala el programa gimp y inkscape como admin")
ok(o == ("ejecutar", [["apt-get", "install", "-y", "gimp", "inkscape"]]), "varios paquetes " + str(o))
o = ad.orden("actualiza el sistema como administrador")
ok(o == ("ejecutar", [["apt-get", "update"], ["apt-get", "upgrade", "-y"]]), "actualizar el sistema " + str(o))
o = ad.orden("reinicia el servicio ssh como administrador")
ok(o == ("ejecutar", [["systemctl", "restart", "ssh"]]), "reiniciar un servicio " + str(o))
o = ad.orden("sudo apt-get install -y htop")
ok(o == ("ejecutar", [["apt-get", "install", "-y", "htop"]]), "«sudo …» " + str(o))
ok(ad.orden("qué has hecho como administrador") == ("ver", None), "ver el registro")
ok(ad.orden("estado del modo administrador") == ("estado", None), "estado")
ok(ad.orden("estudia linux como administrador") is None, "frase normal con «como administrador» al final: no es orden")
ok(ad.orden("hola kira") is None and ad.orden("instala vlc") is None, "sin «administrador» no es orden")
o = ad.orden("ejecuta como administrador programaquenoexiste123 --x")
ok(o and o[0] == "desconocida", "programa que no existe → lo dice " + str(o))
ok("no encuentro el programa" in ad.hacer(o).lower(), "texto de programa desconocido")

# ---------- candados ----------
for mala, por in ((["bash", "-c", "rm -rf /"], "intérprete"), (["python3", "x.py"], "intérprete"),
                  (["env", "X=1", "ls"], "envoltorio"), (["dd", "if=/dev/zero", "of=/dev/sda"], "disco"),
                  (["mkfs.ext4", "/dev/sdb1"], "disco"), (["parted", "/dev/sda"], "disco"),
                  (["passwd", "papi"], "contraseña"), (["userdel", "papi"], "cuenta"),
                  (["rm", "-rf", "/"], "borrar /"), (["rm", "-r", "/etc"], "borrar /etc"), (["rm", "-rf", "/home/papi"], "borrar home"),
                  (["chmod", "-R", "777", "/"], "permisos de /"), (["apt-get", "install", "a;b"], "signos de shell"),
                  (["ls", "$(id)"], "signos de shell")):
    try:
        ad.validar(mala)
        ok(False, "debería rechazar: " + " ".join(mala))
    except ad.AdminError as e:
        ok(True, f"rechaza ({por}): {' '.join(mala)} → {e}")
for buena in (["apt-get", "install", "-y", "vlc"], ["systemctl", "restart", "ssh"], ["rm", "/etc/kira_prueba.conf"],
              ["chown", "papi", "/home/papi/x"], ["ufw", "allow", "22"]):
    try:
        ad.validar(buena)
        ok(True, "permite: " + " ".join(buena))
    except ad.AdminError as e:
        ok(False, f"no debería rechazar {buena}: {e}")

# ---------- la línea que se ejecuta ----------
llamadas = []
def correr_sin_permiso(args, timeout=0):
    llamadas.append(list(args))
    if args[:3] == ["sudo", "-n", "true"]:
        return 1, "hace falta contraseña"
    return 0, "hecho\n"
os.environ["KIRA_PKEXEC"] = "pkexec"
linea, como = ad.linea_de_orden(["apt-get", "update"], correr_sin_permiso)
ok(como == "ventana" and linea[0] == "pkexec" and linea[-1] == "update", "sin permiso de paquetes → pkexec " + str(linea))
def correr_con_permiso(args, timeout=0):
    llamadas.append(list(args))
    return 0, "ok"
linea, como = ad.linea_de_orden(["apt-get", "install", "-y", "vlc"], correr_con_permiso)
ok(como == "permiso" and linea[:2] == ["sudo", "-n"], "con el permiso de paquetes (v3.33) → sudo -n, sin ventana")
linea, como = ad.linea_de_orden(["systemctl", "restart", "ssh"], correr_con_permiso)
ok(como == "ventana" and linea[0] == "pkexec", "el permiso de paquetes NO vale para otras cosas → ventana")
ay = os.path.join(T, "kira-admin"); po = os.path.join(T, "org.kira.admin.policy")
open(ay, "w").write("#!/bin/sh\n"); os.chmod(ay, 0o755); open(po, "w").write("<x/>")
ad.AYUDANTE, ad.POLITICA = ay, po
linea, como = ad.linea_de_orden(["systemctl", "restart", "ssh"], correr_sin_permiso)
ok(linea[:2] == ["pkexec", ay] and linea[2].endswith("systemctl"), "con el ayudante activado → pkexec kira-admin … " + str(linea))
ok(ad.ayudante_activo(), "ayudante_activo")

# ---------- ejecutar ----------
llamadas.clear()
r = ad.ejecutar([["apt-get", "update"], ["apt-get", "upgrade", "-y"]], correr=correr_sin_permiso)
ok(r["ok"] and r["hechas"] == 2, "ejecuta las dos órdenes " + r["texto"][:80])
ok(sum(1 for c in llamadas if c[0] == "pkexec") == 2, "cada una por la ventana de la contraseña")
def correr_cancela(args, timeout=0):
    if args[:3] == ["sudo", "-n", "true"]:
        return 1, ""
    return 126, "Error executing command as another user: Not authorized"
r = ad.ejecutar([["apt-get", "update"], ["apt-get", "upgrade", "-y"]], correr=correr_cancela)
ok(not r["ok"] and r["cancelada"] and r["hechas"] == 0 and "no lo he hecho" in r["texto"].lower(),
   "cancelar la ventana → no hace nada y para: " + r["texto"])
def correr_sin_agente(args, timeout=0):
    if args[:3] == ["sudo", "-n", "true"]:
        return 1, ""
    return 127, "Error executing command as another user: No authentication agent found."
r = ad.ejecutar([["apt-get", "update"]], correr=correr_sin_agente)
ok(not r["ok"] and "agente" in r["texto"], "sin agente de polkit → lo explica")
r = ad.ejecutar([["dd", "if=/dev/zero", "of=/dev/sda"]], correr=correr_sin_permiso)
ok(not r["ok"] and "no lo hago" in r["texto"].lower(), "orden prohibida → ni se intenta")
reg = open(os.environ["KIRA_ADMIN_LOG"]).read()
ok("apt-get update" in reg and "rc=126" in reg and "dd" not in reg, "registro: lo hecho y lo cancelado (lo prohibido ni llega)")
ok(oct(os.stat(os.environ["KIRA_ADMIN_LOG"]).st_mode & 0o777) == "0o600", "registro 0600")
ok("administrador" in ad.leer_registro(), "leer_registro")

# ---------- hacer: solo en la pantalla ----------
os.environ.pop("KIRA_ADMIN_PANTALLA", None)
txt = ad.hacer(("ejecutar", [["apt-get", "update"]]), correr=correr_sin_permiso)
ok("pantalla del portátil" in txt, "fuera de la pantalla no lo hace: " + txt[:60])
os.environ["KIRA_ADMIN_PANTALLA"] = "1"; os.environ["DISPLAY"] = ":0"
bin_ = os.path.join(T, "bin"); os.makedirs(bin_, exist_ok=True)
open(os.path.join(bin_, "pkexec"), "w").write("#!/bin/sh\nexit 0\n"); os.chmod(os.path.join(bin_, "pkexec"), 0o755)
os.environ["PATH"] = bin_ + os.pathsep + os.environ["PATH"]
ok(ad.puede_preguntar(), "en la pantalla con DISPLAY y pkexec → puede preguntar")
txt = ad.hacer(("ejecutar", [["apt-get", "update"]]), correr=correr_sin_permiso)
ok(txt.startswith("Hecho como administrador"), "en la pantalla lo hace: " + txt[:60])

# ---------- el ayudante de verdad (bash) ----------
ayu = os.path.join(RAIZ, "kira_portatil", "kira_admin.sh")
env = dict(os.environ, KIRA_ADMIN_PRUEBA="1", KIRA_ADMIN_SIS_LOG=os.path.join(T, "sis.log"))
p = subprocess.run(["bash", ayu, "echo", "hola", "mundo"], capture_output=True, text=True, env=env)
ok(p.returncode == 0 and p.stdout.strip() == "hola mundo", "ayudante: ejecuta la orden tal cual " + p.stdout)
ok("echo hola mundo" in open(os.path.join(T, "sis.log")).read(), "ayudante: lo apunta en su registro")
for mala in (["bash", "-c", "id"], ["dd", "if=/dev/zero"], ["mkfs.ext4", "/dev/x"], ["passwd"], ["rm", "-rf", "/"],
             ["echo", "a;b"]):
    p = subprocess.run(["bash", ayu] + mala, capture_output=True, text=True, env=env)
    ok(p.returncode != 0, "ayudante rechaza: " + " ".join(mala) + " → " + p.stdout.strip())
p = subprocess.run(["bash", ayu, "echo", "x"], capture_output=True, text=True,
                   env={k: v for k, v in env.items() if k != "KIRA_ADMIN_PRUEBA"})
ok(p.returncode != 0 or os.getuid() == 0, "ayudante sin root (sin pkexec) no hace nada")

# ---------- el guion de activar (raíz falsa) ----------
falsa = os.path.join(T, "raiz")
act = os.path.join(RAIZ, "kira_portatil", "modo_admin.sh")
p = subprocess.run(["bash", act], capture_output=True, text=True, env=dict(os.environ, KIRA_RAIZ_SIS=falsa))
ok(p.returncode == 0 and os.access(os.path.join(falsa, "usr/local/bin/kira-admin"), os.X_OK)
   and os.path.isfile(os.path.join(falsa, "usr/share/polkit-1/actions/org.kira.admin.policy")),
   "modo_admin instala el ayudante y la regla " + p.stdout[-80:])
pol = open(os.path.join(falsa, "usr/share/polkit-1/actions/org.kira.admin.policy")).read()
ok("auth_admin_keep" in pol and "yes" not in pol and "/usr/local/bin/kira-admin" in pol and "$(command_line)" in pol,
   "la regla SIEMPRE pide la contraseña (auth_admin_keep, nunca «yes») y enseña la orden")
p = subprocess.run(["bash", act, "--quitar"], capture_output=True, text=True, env=dict(os.environ, KIRA_RAIZ_SIS=falsa))
ok(not os.path.exists(os.path.join(falsa, "usr/local/bin/kira-admin")), "--quitar lo quita")
try:
    import xml.dom.minidom as md
    md.parse(os.path.join(RAIZ, "kira_portatil", "org.kira.admin.policy"))
    ok(True, "la regla de polkit es XML válido")
except Exception as e:
    ok(False, f"XML de la regla: {e}")

# ---------- cableado ----------
src = open(os.path.join(RAIZ, "kira_portatil", "escritorio_kira.py"), encoding="utf-8").read()
ok("admin_kira.orden(texto)" in src and "admin_activar" in src and "KIRA_ADMIN_PANTALLA" in src,
   "la pantalla atiende las órdenes de administrador y tiene el botón de activar")
nuc = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("adm_.orden(o)" in nuc and "solo lo hago desde la PANTALLA" in nuc, "el núcleo (móvil/red) no lo hace: lo explica")
ses = open(os.path.join(RAIZ, "kira_portatil", "kiraos_sesion.sh"), encoding="utf-8").read()
ok("polkit-gnome-authentication-agent-1" in ses, "la sesión de Kira lanza el agente de polkit (la ventana)")
ok(subprocess.run(["bash", "-n", os.path.join(RAIZ, "kira_portatil", "kiraos_sesion.sh")]).returncode == 0, "sesión: sintaxis")
ins = open(os.path.join(RAIZ, "kira_portatil", "instalar_portatil.sh"), encoding="utf-8").read()
ok("kira-admin-activar" in ins and "org.kira.admin.policy" in ins, "el instalador lo deja preparado")
import apps_externas_kira as aex
ok("instala X como administrador" in aex._PERMISO_UNA_VEZ and "permiso_apps" in aex._PERMISO_UNA_VEZ,
   "el aviso de instalar del sistema menciona la ventana")
os.environ.pop("KIRA_ADMIN_PANTALLA", None)
r = aex.instalar("vlc", base=os.path.join(T, "apps"), correr=correr_sin_permiso)
ok(not r["ok"] and r["admin"], "fuera de la pantalla, instalar del sistema sigue pidiendo la Terminal")
os.environ["KIRA_ADMIN_PANTALLA"] = "1"
llamadas.clear()
r = aex.instalar("vlc", base=os.path.join(T, "apps"), correr=correr_sin_permiso)
ok(r["ok"] and any(c[:1] == ["pkexec"] and c[-1] == "vlc" for c in llamadas),
   "en la pantalla, instalar del sistema pide la contraseña en la ventana: " + r["mensaje"][:60])
sys.path.insert(0, RAIZ)
import kira_god
core = kira_god.KiraGodCore.__new__(kira_god.KiraGodCore)
core.es_kiraos = True
ok("contraseña" in core._orden_superadmin("hazte superadmin"), "«hazte superadmin» lo explica con la contraseña")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
