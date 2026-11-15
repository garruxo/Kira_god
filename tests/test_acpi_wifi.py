"""v3.64: estudiar_acpi_wifi.sh + acpi_wifi_kira.py — leer las tablas ACPI (ya desmontadas) y encontrar qué hace
la BIOS al encender la WiFi (el campo del EC en 0xBB bit 0, los métodos que lo usan y quién los llama)."""
import os, stat, subprocess, sys, tempfile
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import acpi_wifi_kira as aw
GUION = os.path.join(RAIZ, "kira_portatil", "estudiar_acpi_wifi.sh")
fallos = 0
def ok(c, m):
    global fallos
    print(("OK   " if c else "FALLA ") + m)
    if not c: fallos += 1

DSL = r'''
DefinitionBlock ("", "DSDT", 2, "ACRSYS", "ACRPRDCT", 0x00000001)
{
    Scope (\_SB.PCI0.LPCB)
    {
        OperationRegion (GPIO, SystemIO, 0x0500, 0x40)
        Field (GPIO, ByteAcc, NoLock, Preserve)
        {
            Offset (0x0C),
            GL00,   8,
            GL01,   8,
                ,   4,
            GP28,   1
        }
    }
    Scope (\_SB.PCI0.LPCB.EC0)
    {
        OperationRegion (ERAM, EmbeddedControl, Zero, 0xFF)
        Field (ERAM, ByteAcc, Lock, Preserve)
        {
            Offset (0x60),
            SMPR,   8,
            Offset (0xBB),
            WLEX,   1,
            BTEX,   1,
                ,   2,
            W3GE,   1,
            Offset (0xBE),
            CNT2,   8
        }
        Field (ERAM, ByteAcc, Lock, Preserve)
        {
            Offset (0xB6),
            CNT1,   8
        }
        Method (_REG, 2, NotSerialized)
        {
            If ((Arg0 == 0x03))
            {
                ECOK = Arg1
                OSTY = 0x07
            }
        }
        Method (SWLS, 1, Serialized)
        {
            If ((Arg0 == One))
            {
                WLEX = One
                \_SB.PCI0.LPCB.GP28 = One
            }
            Else
            {
                WLEX = Zero
                \_SB.PCI0.LPCB.GP28 = Zero
            }
        }
    }
    Device (WMID)
    {
        Name (_HID, "PNP0C14")
        Method (WMBA, 3, NotSerialized)
        {
            If ((Arg1 == 0x07))
            {
                \_SB.PCI0.LPCB.EC0.SWLS (Arg2)
            }
            Return (Zero)
        }
    }
}
'''

FACP = """
[0B0h 0176   4]           SMI Command Port : 000000B2
[0B4h 0180   1]          ACPI Enable Value : F0
[0B5h 0181   1]         ACPI Disable Value : F1
[040h 0064   4]     PM1A Control Block Address : 00000404
"""
lista = aw.campos(DSL)
nombres = {c["nombre"]: c for c in lista}
ok(nombres.get("WLEX", {}).get("byte") == 0xBB and nombres["WLEX"]["bit"] == 0, "WLEX está en el EC 0xBB bit 0")
ok(nombres.get("BTEX", {}).get("bit") == 1 and nombres.get("W3GE", {}).get("bit") == 4, "cuenta bits sueltos y huecos sin nombre")
ok(nombres.get("CNT1", {}).get("byte") == 0xB6, "un segundo Field empieza otra vez desde el principio de la zona")
ok("GP28" not in nombres, "los campos de puertos (SystemIO) no se cuentan como del EC")
ok([c["nombre"] for c in aw.campo_en(lista, 0xBB, 0)] == ["WLEX"], "campo_en(0xBB, 0) = WLEX")
r = aw.analizar({"DSDT.dsl": DSL})
ok(r["metodos"] == ["SWLS"] and r["llamadores"] == ["WMBA"], "método que lo usa (SWLS) y quién lo llama (WMBA)")
ok("WMBA" in r["wmi"] and r["gpio_regiones"].get("GPIO") == 0x500, "ve el método WMI y la zona de puertos 0x500")
t = aw.texto(r)
print(t)
ok("Campo del EC en 0xBB bit 0: WLEX" in t, "dice el nombre del campo")
ok(any(l.startswith(">") and "WLEX = One" in l for l in t.splitlines()) and any(l.startswith("*") and "GP28 = One" in l for l in t.splitlines()), "marca el bit del EC (>) y lo otro que enciende la radio (*)")
r2 = aw.analizar({"DSDT.dsl": DSL, "FACP.dsl": FACP})
ok(r2["fadt"] == {"smi": 0xB2, "activar": 0xF0, "desactivar": 0xF1, "pm1a": 0x404}, "lee de la FACP cómo pasar a modo ACPI")
t2 = aw.texto(r2)
ok("puerto SMI 0xB2, activar 0xF0, desactivar 0xF1, PM1a 0x404" in t2, "lo enseña")
ok("BTEX=0xBB.1" in t2 and "CNT2=0xBE.0" in t2, "enseña los campos del EC de alrededor")
ok("== _REG (al arrancar) ==" in t2 and "OSTY = 0x07" in t2, "enseña lo que hace la BIOS al arrancar (_REG)")
ok("No he encontrado" in aw.texto(aw.analizar({"x.dsl": "DefinitionBlock () { }"})), "sin campos del EC lo dice")
ok("ninguno en el byte" in aw.texto(aw.analizar({"x.dsl": DSL}, 0xC0, 0), 0xC0, 0), "sin campo en ese byte lo dice")
src = open(os.path.join(RAIZ, "kira_portatil", "acpi_wifi_kira.py")).read()
ok("open(" in src and "\"w\"" not in src and "subprocess" not in src, "el analizador solo lee archivos")

# --- el guion, con tablas, sudo e iasl de mentira ---
def montar(t, con_dsdt=True):
    tab = os.path.join(t, "tablas"); os.makedirs(tab)
    if con_dsdt:
        open(os.path.join(tab, "DSDT"), "wb").write(b"AML")
    open(os.path.join(tab, "SSDT1"), "wb").write(b"AML")
    open(os.path.join(tab, "FACP"), "wb").write(b"FAC")
    open(os.path.join(t, "facp.dsl"), "w").write(FACP)
    bin_ = os.path.join(t, "bin"); os.makedirs(bin_)
    iasl = os.path.join(bin_, "iasl")
    dsl = os.path.join(t, "fuente.dsl"); open(dsl, "w").write(DSL)
    open(iasl, "w").write('#!/bin/bash\necho "$@" >> "%s/iasl.log"\nfor a in "$@"; do case "$a" in DSDT.dat) cp "%s" DSDT.dsl;; SSDT*.dat) echo "DefinitionBlock () { }" > "${a%%.dat}.dsl";; FACP.dat) cp "%s/facp.dsl" FACP.dsl;; esac; done\n' % (t, dsl, t))
    os.chmod(iasl, 0o755)
    return tab, iasl, os.path.join(t, "kernel")

with tempfile.TemporaryDirectory() as t:
    tab, iasl, dest = montar(t)
    env = dict(os.environ, KIRA_PRUEBA="1", KIRA_SUDO="", KIRA_ACPI=tab, KIRA_IASL=iasl, KIRA_KERNEL=dest)
    r = subprocess.run(["bash", GUION], env=env, capture_output=True, text=True, timeout=60)
    s = r.stdout
    print(s, r.stderr)
    ok(r.returncode == 0 and "Tablas copiadas: 3" in s, "copia DSDT, SSDT y FACP")
    ok("Campo del EC en 0xBB bit 0: WLEX" in s and "== SWLS ==" in s and "== WMBA ==" in s, "enseña el campo y los métodos")
    ok("puerto SMI 0xB2" in s, "el guion también lee la FACP")
    inf = os.path.join(dest, "acpi_wifi.txt")
    ok(os.path.exists(inf) and stat.S_IMODE(os.stat(inf).st_mode) == 0o600, "informe guardado con permisos 0600")
    ok(os.path.exists(os.path.join(dest, "acpi", "DSDT.dsl")), "guarda las tablas en texto")
    ok("-d DSDT.dat" in open(os.path.join(t, "iasl.log")).read(), "desmonta la DSDT con iasl -d")
    ok(open(os.path.join(tab, "DSDT"), "rb").read() == b"AML", "no toca las tablas originales")

with tempfile.TemporaryDirectory() as t:
    tab, iasl, dest = montar(t, con_dsdt=False)
    env = dict(os.environ, KIRA_PRUEBA="1", KIRA_SUDO="", KIRA_ACPI=tab, KIRA_IASL=iasl, KIRA_KERNEL=dest)
    r = subprocess.run(["bash", GUION], env=env, capture_output=True, text=True, timeout=60)
    ok(r.returncode != 0 and "No encuentro la tabla DSDT" in r.stdout, "sin DSDT lo dice")

with tempfile.TemporaryDirectory() as t:
    tab, iasl, dest = montar(t)
    env = dict(os.environ, KIRA_PRUEBA="1", KIRA_SUDO="", KIRA_ACPI=tab, KIRA_IASL="no_existe_iasl", KIRA_KERNEL=dest)
    r = subprocess.run(["bash", GUION], env=env, input="no\n", capture_output=True, text=True, timeout=60)
    ok(r.returncode != 0 and "no instalo nada" in r.stdout, "sin iasl pregunta y, si no dices SI, no instala nada")

if os.getuid() != 0:
    r = subprocess.run(["bash", GUION], capture_output=True, text=True, timeout=30,
                       env={k: v for k, v in os.environ.items() if k != "KIRA_PRUEBA"})
    ok(r.returncode == 1 or "contrasena" in r.stdout, "se lanza sin sudo")
src = open(GUION).read()
ok("apt-get install -y acpica-tools" in src and "SI" in src, "instalar iasl solo si escribes SI")
ok("> /sys" not in src and "write_support" not in src, "el guion no escribe en /sys ni en el EC")

print("\n" + ("TODO BIEN" if not fallos else f"{fallos} FALLOS"))
sys.exit(1 if fallos else 0)
