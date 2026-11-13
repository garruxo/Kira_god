# -*- coding: utf-8 -*-
"""v3.35: el TALLER DE KERNEL de KiraOS y el saber de sistemas operativos por dentro.

Aquí: las órdenes, las fichas, las plantillas COMPILADAS DE VERDAD (si hay gcc y nasm), el bucle con un cerebro de
mentira (falla, corrige, acierta; o falla siempre y deja el kernel como estaba) y un «QEMU» de mentira que imprime
las marcas que el kernel lleva dentro. Con --qemu-real (en el flujo probar_kernel.yml) usa QEMU de verdad.
"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATA_DIR"] = T
os.environ["KIRA_KERNEL"] = os.path.join(T, "kernel_nucleo")
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import saber_so_kira as so          # noqa: E402
import taller_kernel_kira as tk     # noqa: E402

QEMU_REAL = "--qemu-real" in sys.argv
fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ---------------- el saber ----------------
ok(len(so.fichas()) >= 15 and all(len(x) > 150 for _t, x in so.fichas()), "fichas de SO por dentro, con chicha")
ok([e["n"] for e in so.ETAPAS] == [1, 2, 3, 4, 5], "5 etapas")
ok(all("KERNEL_LISTO" in e["espera"] for e in so.ETAPAS), "todas esperan KERNEL_LISTO")
ok(all({"boot.s", "linker.ld", "kernel.c"} <= set(e["archivos"]) for e in so.ETAPAS), "cada etapa trae su base")
ok(so.etapa_para("añade la GDT")["n"] == 2 and so.etapa_para("pon las interrupciones")["n"] == 3 and
   so.etapa_para("que funcione el teclado")["n"] == 4 and so.etapa_para("activa la paginación")["n"] == 5,
   "lo pedido → su etapa")
ok(so.etapa_para("que imprima mi nombre") is None, "algo que no es una etapa → None (lo hace el cerebro)")
ok("GDT" in so.fichas_para("añade la gdt")[0][0], "la ficha que toca")
ok("[✓] 2." in so.texto_etapas(2) and "[ ] 3." in so.texto_etapas(2), "texto de etapas con las hechas")

# ---------------- órdenes ----------------
O = tk.orden
ok(O("programa el kernel: añade una función que cuente segundos.") ==
   ("programar", "añade una función que cuente segundos"), "programa el kernel: … (con tildes intactas)")
ok(O("Kira, kernel: que el teclado escriba en mayúsculas") == ("programar", "que el teclado escriba en mayúsculas"),
   "«Kira, kernel: …»")
ok(O("compila el kernel") == ("compilar", "") and O("prueba tu kernel") == ("probar", "") and
   O("enséñame el kernel funcionando") == ("ver", "") and O("estado del kernel") == ("estado", "") and
   O("pon la etapa 3 del kernel") == ("etapa", "3") and O("deshaz el último cambio del kernel") == ("deshacer", "") and
   O("empieza el kernel de cero") == ("cero", "") and O("etapas del kernel") == ("etapas", "") and
   O("enséñame el archivo gdt.c del kernel") == ("leer", "gdt.c") and O("archivos del kernel") == ("archivos", ""),
   "las demás órdenes")
for t in ("qué es un kernel", "estudia kernels", "abre la terminal", "instala el kernel de linux 6.8"):
    ok(O(t) is None, f"«{t}» NO es del taller")

# ---------------- piezas puras ----------------
A = tk.extraer_archivos("Aquí va:\nARCHIVO: reloj.c\n```c\nint x;\n```\nARCHIVO: `reloj.h`\n```c\nint y;\n```")
ok(A == {"reloj.c": "int x;\n", "reloj.h": "int y;\n"}, "extrae varios archivos")
ok(tk.extraer_archivos("```c\nvoid kernel_main(void){}\n```") == {"kernel.c": "void kernel_main(void){}\n"},
   "un solo bloque con kernel_main → kernel.c")
ok(tk.extraer_archivos("no sé") == {}, "sin archivos → vacío")
reinicio, exc = tk.excepciones_de_registro(
    "     0: v=20 e=0000 i=0 cpl=0 IP=0008:00100000\ncheck_exception old: 0xffffffff new 0xd\n"
    "     1: v=0d e=0010 i=0 cpl=0 IP=0008:0010012a pc=0010012a\nTriple fault\nCPU Reset (CPU 0)\n")
ok(reinicio and exc and exc[-1].startswith("v=0d protección general"), "lee el triple fallo y la excepción")
ok(tk.excepciones_de_registro("v=20 x\nv=21 y")[1] == [], "las IRQ (v>=0x20) no son excepciones")
ok(not tk.excepciones_de_registro("CPU Reset (CPU 0)\nEAX=0\n     0: v=20 e=0000")[0],
   "el «CPU Reset» del encendido NO es un cuelgue (visto con QEMU de verdad)")
ok(tk.errores_cortos("a.c:1: warning: x\na.c:2: error: y").startswith("a.c:2: error"), "los errores primero")

# ---------------- QEMU de mentira: imprime las marcas que el kernel lleva dentro ----------------
MARCAS = ["Hola desde mi SO!", "Multiboot OK", "GDT OK", "IDT OK", "punto de ruptura", "Excepciones OK", "PIC OK",
          "Teclado OK", "TIMER OK", "MARCOS OK", "PAGINACION OK", "HEAP OK", "KERNEL_LISTO", "SEGUNDOS OK"]
FALSO = r'''
import sys, os
args = sys.argv[1:]
binario = args[args.index("-kernel") + 1]
log = args[args.index("-D") + 1] if "-D" in args else None
datos = open(binario, "rb").read()
if b"CUELGATE" in datos:
    if log:
        open(log, "w").write("     0: v=0d e=0010 i=0 cpl=0 IP=0008:00100abc\nTriple fault\nCPU Reset (CPU 0)\n")
    sys.exit(0)
for m in MARCAS:
    if m.encode() in datos:
        print(m, flush=True)
import time; time.sleep(30)
'''.replace("MARCAS", repr(MARCAS))
RUTA_FALSO = os.path.join(T, "qemu_falso.py")
with open(RUTA_FALSO, "w") as f:
    f.write(FALSO)


def popen_falso(args, **kw):
    if args and args[0] == "qemu-system-i386":
        args = [sys.executable, RUTA_FALSO] + list(args[1:])
    return subprocess.Popen(args, **kw)


hay_compilador = bool(shutil.which("gcc") and shutil.which("nasm") and shutil.which("ld"))
if QEMU_REAL:
    which = shutil.which
    popen = subprocess.Popen
else:
    which = (lambda h: "/usr/bin/" + h if h == "qemu-system-i386" else shutil.which(h))
    popen = popen_falso

if not hay_compilador:
    print("  (sin gcc/nasm aquí: me salto las pruebas que compilan)")
else:
    base = os.path.join(T, "kernel")
    t = tk.Taller(base=base, popen=popen, which=which)
    ok("Aún no he empezado" in t.texto_estado(), "estado sin empezar")
    for e in so.ETAPAS:
        t.poner_etapa(e["n"], copiar=False)
        c, sal = t.compilar()
        ok(c and "error" not in sal.lower(), f"la etapa {e['n']} COMPILA de verdad (gcc + nasm + ld)")
        r = t.probar(e["espera"])
        ok(r["ok"], f"la etapa {e['n']} arranca y saca sus marcas ({'QEMU real' if QEMU_REAL else 'QEMU falso'}): "
           + r["texto"][:120])
    # nunca escribe fuera de .c/.h/.s
    for malo in ("Makefile", "../fuera.c", "linker.ld", "a b.c"):
        try:
            t.escribir(malo, "x")
            ok(False, f"no debía escribir «{malo}»")
        except tk.TallerError:
            ok(True, f"no escribe «{malo}»")
    ok(not os.path.exists(os.path.join(T, "fuera.c")), "nada fuera de la carpeta del kernel")

    # ---- plantilla: «añade la IDT» desde la etapa 1 ----
    shutil.rmtree(base)
    t = tk.Taller(base=base, popen=popen, which=which)
    r = tk.hacer(t, "programar", "añade la IDT para las excepciones", preguntar=None)
    ok(r.get("ok") is not False and "plantilla probada" in r["texto"] and t.estado()["etapa"] == 3,
       "«añade la IDT» usa la plantilla probada (sin cerebro) y la prueba")
    r = tk.hacer(t, "programar", "pon la GDT")
    ok("ya lo tiene" in r["texto"], "lo que ya está → lo dice")

    # ---- cerebro de mentira: 1.º no compila, 2.º arranca y saca su marca ----
    K_MALO = so.etapa(3)["archivos"]["kernel.c"].replace("kprint(\"KERNEL_LISTO\\n\");", "kprint(\"KERNEL_LISTO\\n\") ERROR;")
    K_BUENO = so.etapa(3)["archivos"]["kernel.c"].replace(
        "kprint(\"KERNEL_LISTO\\n\");", "kprint(\"SEGUNDOS OK\\n\");\n    kprint(\"KERNEL_LISTO\\n\");")
    pedidos = []

    def cerebro(respuestas):
        it = iter(respuestas)

        def preguntar(system, usuario):
            pedidos.append(usuario)
            return next(it)
        return preguntar

    antes = t.leer("kernel.c")
    r = t.programar("que imprima SEGUNDOS OK", preguntar=cerebro([
        "ARCHIVO: kernel.c\n```c\n" + K_MALO + "```", "ARCHIVO: kernel.c\n```c\n" + K_BUENO + "```"]))
    ok(r["ok"] and "intento 2" in r["texto"] and "SEGUNDOS OK" in r.get("serie", ""),
       "falla al compilar, corrige con el error y acierta en el 2.º intento")
    ok("No compila" in pedidos[1] and "error" in pedidos[1].lower(), "al cerebro le llega el error del compilador")
    ok("Así está ahora kernel.c" in pedidos[0] and "Archivos del proyecto" in pedidos[0], "y el código de ahora")
    ok("SEGUNDOS OK" in t.leer("kernel.c"), "el cambio queda puesto")

    # ---- falla siempre (se cuelga) → vuelve a como estaba ----
    bueno = t.leer("kernel.c")
    K_CUELGA = bueno.replace("kprint(\"KERNEL_LISTO\\n\");", "kprint(\"CUELGATE\\n\"); __asm__ volatile(\"ud2\");")
    r = t.programar("algo que se cuelga", preguntar=cerebro(["ARCHIVO: kernel.c\n```c\n" + K_CUELGA + "```"] * 3),
                    intentos=3)
    ok(not r["ok"] and "3 veces" in r["texto"] and t.leer("kernel.c") == bueno,
       "si no lo logra, deja el kernel como estaba (funcionando)")
    ok("triple fallo" in pedidos[-1] or "reinici" in pedidos[-1] or "falta" in pedidos[-1],
       "al cerebro le llega por qué se colgó")

    # ---- archivos con mal nombre se ignoran ----
    r = t.programar("x", preguntar=cerebro(["ARCHIVO: Makefile\n```\nall:\n\trm -rf /\n```"] * 2), intentos=2)
    ok(not r["ok"] and not os.path.exists(os.path.join(base, "Makefile")), "un Makefile del cerebro se ignora")

    # ---- deshacer, cero, archivos, leer, estado ----
    ok("Deshecho" in tk.hacer(t, "deshacer")["texto"], "deshacer")
    ok("gdt.c" in tk.hacer(t, "archivos")["texto"] and "gdt_init" in tk.hacer(t, "leer", "gdt.c")["texto"],
       "lista y lee archivos")
    ok("etapa" in tk.hacer(t, "estado")["texto"], "estado")
    ok("de cero" in tk.hacer(t, "cero")["texto"] and t.estado()["etapa"] == 1, "empezar de cero (lo de antes, guardado)")
    ok(t.deshacer() is not None and t.estado()["etapa"] == 3, "…y se recupera con deshacer")
    if not QEMU_REAL:
        rr = tk.hacer(t, "probar")
        ok(rr.get("ok") is not False and "compila y arranca" in rr["texto"], "«prueba el kernel»")

    # ---- sin QEMU: lo dice con cómo instalarlo ----
    t2 = tk.Taller(base=os.path.join(T, "k2"), which=lambda h: None if h == "qemu-system-i386" else shutil.which(h))
    t2.asegurar()
    ok(t2.compilar()[0] and "sudo apt install qemu-system-x86" in t2.arrancar()["motivo"],
       "sin QEMU: compila y explica cómo instalarlo")

# ---------------- cableado ----------------
fuente = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("tk_.orden(o)" in fuente and "_preguntar_cerebro(core)" in fuente, "el núcleo de KiraOS atiende las órdenes del kernel")
ast.parse(fuente)
import estudio_kira as est  # noqa: E402
ok(est.es_estudia_general("estudia sistemas operativos por dentro") is None and
   est.es_estudia_general("estudia kernels") is None and
   est.es_estudia_general("estudia sistemas operativos") == "sistemas operativos",
   "«estudia sistemas operativos por dentro» = fichas propias; a secas, el estudio general")
import mando_kira as mk  # noqa: E402
ok(mk.es_trabajo("programa el kernel: añade la IDT") and mk.es_trabajo("kernel: hola") and
   not mk.es_trabajo("qué es un kernel"), "desde el móvil, las órdenes del kernel van a KiraOS")
import kira_god  # noqa: E402
core = kira_god.KiraGodCore()
r = core.procesar_orden("estudia sistemas operativos por dentro")
ok("[OK]" in r and "GDT" in r, "el núcleo guarda las fichas: " + r[:60])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
