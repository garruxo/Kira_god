# -*- coding: utf-8 -*-
"""
taller_kernel_kira.py — v3.35 (SOLO KiraOS): el TALLER DE KERNEL. Kira programa un sistema operativo de verdad.

Lo pidió el dueño: que Kira sepa programar un SO desde cero. El bucle es el de cualquier programadora de kernels:
    cambia el código → compila → lo ARRANCA en un ordenador de mentira (QEMU) → lee lo que sale por el puerto serie
    (y, si se cuelga, qué excepción lo tiró) → corrige … hasta que funcione o se acaben los intentos.

Dónde y por qué es seguro:
  - El proyecto vive en ~/kira_portatil/kernel (o KIRA_KERNEL). Es SU proyecto: no toca KiraOS ni tus archivos.
  - El kernel corre DENTRO de QEMU (un ordenador emulado aparte): sin red (-nic none), sin discos, sin carpetas
    compartidas, sin pantalla (-display none) y con tiempo máximo. Es su propia máquina virtual de pruebas; no se mete
    dentro de la máquina Debian de Kira porque una máquina dentro de otra en un i5 de 2010 iría lentísima.
  - El cerebro SOLO escribe archivos .c, .h y .s con nombres sencillos. La forma de compilar es FIJA (aquí, en listas
    de argumentos, sin shell ni Makefile que el cerebro pueda tocar): compilar no ejecuta nada de lo escrito.
  - Antes de cada cambio se guarda una copia: si tras los intentos no funciona, vuelve como estaba; y «deshaz el
    último cambio del kernel» cuando quieras.
  - Con el cerebro pequeño (2B del Packard Bell) lo que mejor funciona son las PLANTILLAS PROBADAS por etapas
    (saber_so_kira.ETAPAS): si lo pedido es una etapa («añade la IDT», «el teclado»), pone la plantilla y la prueba;
    para lo demás, el cerebro ADAPTA el código que ya funciona.

Órdenes (orden()): «programa el kernel: …» / «kernel: …», «compila el kernel», «prueba / arranca el kernel»,
«enséñame el kernel funcionando» (QEMU con pantalla), «estado del kernel», «archivos del kernel», «enséñame el archivo
X del kernel», «etapas del kernel», «pon la etapa N del kernel», «deshaz el último cambio del kernel», «empieza el
kernel de cero».

`correr`, `popen` y `which` se inyectan para probar sin herramientas reales.
"""
import json
import glob
import os
import re
import select
import shutil
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
import saber_so_kira as so  # noqa: E402

BASE = os.environ.get("KIRA_KERNEL") or os.path.expanduser("~/kira_portatil/kernel")
NOMBRE_OK = re.compile(r"^[A-Za-z0-9_]{1,40}\.(?:c|h|s)$")
FUENTES = (".c", ".h", ".s", ".ld")
CFLAGS = ["-m32", "-ffreestanding", "-fno-pic", "-fno-pie", "-fno-stack-protector", "-nostdlib", "-O2", "-Wall",
          "-Wextra", "-mno-sse", "-mno-sse2", "-mno-mmx", "-fno-asynchronous-unwind-tables"]
HERRAMIENTAS = {"gcc": "build-essential", "ld": "binutils", "nasm": "nasm", "qemu-system-i386": "qemu-system-x86"}
MAX_COPIAS = 15
ESPERA_QEMU = 8

SISTEMA = (
    "Eres una programadora experta de sistemas operativos. Trabajas en un kernel x86 de 32 bits, en C freestanding "
    "(sin libc: no hay printf ni malloc; usa kprint, kprint_dec y kprint_hex de consola.h) y NASM, cargado por "
    "Multiboot en QEMU. Para comprobar lo que hagas, imprime con kprint una línea que diga que funciona. El kernel "
    "debe seguir imprimiendo KERNEL_LISTO al final de kernel_main. Responde SOLO con los archivos que cambies o "
    "crees, COMPLETOS (nunca «...»), cada uno así:\n"
    "ARCHIVO: nombre.c\n```c\n<el archivo entero>\n```\n"
    "Nombres solo con letras, números y _, acabados en .c, .h o .s. No escribas Makefile ni linker.ld.")


class TallerError(Exception):
    pass


def _correr_defecto(args, cwd=None, timeout=120):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _ahora():
    return time.strftime("%Y-%m-%d %H:%M")


GRUB_PC = os.environ.get("KIRA_GRUB_PC") or "/usr/lib/grub/i386-pc"


SECTORES_AHCI = 8192                            # 4 MB cada disco de pruebas
DISCOS_VERSION = "3.41"                         # cambia si cambia lo que llevan los discos de pruebas


def _entrada_mbr(tipo, inicio, sectores):
    import struct
    return bytes([0, 0, 0, 0, tipo, 0, 0, 0]) + struct.pack("<II", inicio, sectores)


def disco_mbr():
    """Disco de pruebas con tabla MBR: Linux (2 MB) + Linux swap (1 MB). Puro."""
    mbr = bytearray(512)
    mbr[446:462] = _entrada_mbr(0x83, 2048, 4096)
    mbr[462:478] = _entrada_mbr(0x82, 6144, 2048)
    mbr[510:512] = b"\x55\xaa"
    return bytes(mbr) + b"\0" * (512 * (SECTORES_AHCI - 1))


def _guid(primero):
    import struct
    return struct.pack("<I", primero) + bytes(12)


def disco_gpt(linux=None):
    """Disco de pruebas con tabla GPT (MBR protector + cabecera «EFI PART» + entradas): EFI (1 MB) + Linux. Si se da
    `linux` (los bytes de un ext4), la partición Linux lo lleva dentro (v3.41). Las sumas CRC no se rellenan: el
    driver de Kira no las mira (es solo para leer la lista). Puro."""
    import struct
    sectores = SECTORES_AHCI if not linux else 4096 + (len(linux) + 511) // 512 + 34
    disco = bytearray(512 * sectores)
    disco[446:462] = _entrada_mbr(0xEE, 1, min(sectores - 1, 0xFFFFFFFF))
    disco[510:512] = b"\x55\xaa"
    cab = bytearray(512)
    cab[0:8] = b"EFI PART"
    struct.pack_into("<IIIIQQQQ", cab, 8, 0x00010000, 92, 0, 0, 1, sectores - 1, 34, sectores - 34)
    struct.pack_into("<QIII", cab, 72, 2, 128, 128, 0)
    disco[512:1024] = cab
    fin_linux = sectores - 35
    for i, (tipo, ini, fin) in enumerate(((0xC12A7328, 2048, 4095), (0x0FC63DAF, 4096, fin_linux))):
        e = bytearray(128)
        e[0:16] = _guid(tipo)
        e[16:32] = bytes([i + 1] * 16)
        struct.pack_into("<QQ", e, 32, ini, fin)
        e[56:64] = "Kira".encode("utf-16-le")
        disco[1024 + 128 * i:1024 + 128 * (i + 1)] = e
    if linux:
        disco[4096 * 512:4096 * 512 + len(linux)] = linux
    return bytes(disco)


def grub_cfg(espera=10):
    """El menú de arranque del USB. Puro."""
    return (f"set timeout={int(espera)}\nset default=0\nterminal_output console\n\n"
            "menuentry \"Kernel de Kira\" {\n    multiboot /boot/kernel.bin\n    boot\n}\n\n"
            "menuentry \"Reiniciar\" {\n    reboot\n}\n")


def usbs_de_lsblk(texto):
    """De `lsblk -J -d -o NAME,RM,TRAN,SIZE,MODEL,TYPE`: solo los discos USB extraíbles. Puro."""
    try:
        datos = json.loads(texto or "{}")
    except ValueError:
        return []
    fuera = []
    for d in datos.get("blockdevices") or []:
        rm = str(d.get("rm")).lower() in ("1", "true")
        if d.get("type") == "disk" and str(d.get("tran") or "").lower() == "usb" and rm and \
                re.fullmatch(r"sd[a-z]{1,2}", str(d.get("name") or "")):
            fuera.append({"dispositivo": "/dev/" + d["name"], "modelo": str(d.get("model") or "").strip(),
                          "tamano": str(d.get("size") or "?")})
    return fuera


def errores_cortos(salida, maximo=25):
    """De la salida del compilador, las líneas que importan (errores primero). Puro."""
    lineas = [l for l in str(salida or "").splitlines() if l.strip()]
    malas = [l for l in lineas if re.search(r"\berror\b|undefined reference|no such file|:\s*fatal", l, re.I)]
    resto = [l for l in lineas if l not in malas]
    return "\n".join((malas + resto)[:maximo])


def excepciones_de_registro(texto, maximo=12):
    """Del registro de QEMU (-d int,cpu_reset): las excepciones del procesador (vector < 0x20) y si hubo reinicio.
    Devuelve (reinicio: bool, [«v=0d protección general …»]). Puro."""
    nombres = {0x0: "división por cero", 0x6: "instrucción inválida", 0x8: "doble fallo", 0xa: "TSS inválida",
               0xb: "segmento no presente", 0xc: "fallo de pila", 0xd: "protección general", 0xe: "fallo de página",
               0x3: "punto de ruptura (int 3)"}
    t = str(texto or "")
    # ojo: QEMU apunta «CPU Reset» también AL ENCENDER; el cuelgue de verdad es «Triple fault»
    reinicio = bool(re.search(r"Triple fault", t, re.I))
    vistas = []
    for m in re.finditer(r"\bv=([0-9a-f]{2})\b[^\n]*", t):
        v = int(m.group(1), 16)
        if v < 0x20:
            linea = m.group(0)
            ip = re.search(r"(?:IP|pc)=([0-9a-f:]+)", linea)
            vistas.append(f"v={m.group(1)} {nombres.get(v, 'excepción')}" + (f" en {ip.group(1)}" if ip else ""))
    return reinicio, vistas[-maximo:]


def extraer_archivos(texto, tarea=""):
    """Saca los archivos de la respuesta del cerebro: «ARCHIVO: x.c» + bloque ```. Si solo hay un bloque de C con
    kernel_main y ningún «ARCHIVO:», es kernel.c. Devuelve {nombre: contenido}. Puro."""
    t = str(texto or "")
    fuera = {}
    for m in re.finditer(r"(?:ARCHIVO|Archivo|archivo|FILE|File)\s*:?\s*`?([\w.\-/]+?)`?\s*\n+\s*```[\w+]*\n(.*?)```",
                         t, re.S):
        nombre = os.path.basename(m.group(1).strip())
        fuera[nombre] = m.group(2).rstrip() + "\n"
    if not fuera:
        bloques = re.findall(r"```[\w+]*\n(.*?)```", t, re.S)
        if len(bloques) == 1 and "kernel_main" in bloques[0]:
            fuera["kernel.c"] = bloques[0].rstrip() + "\n"
    return fuera


def _palabras(t):
    return set(w for w in re.findall(r"[a-z0-9_]+", so._norm(t)) if len(w) > 2)


class Taller:
    def __init__(self, base=None, correr=None, popen=None, which=None):
        self.base = base or BASE
        self.correr = correr or _correr_defecto
        self.popen = popen or subprocess.Popen
        self.which = which or shutil.which

    # ---------------- rutas y estado ----------------
    @property
    def ruta_estado(self):
        return os.path.join(self.base, "kernel.json")

    def estado(self):
        try:
            with open(self.ruta_estado, encoding="utf-8") as f:
                e = json.load(f)
            return e if isinstance(e, dict) else {}
        except (OSError, ValueError):
            return {}

    def _guardar_estado(self, e):
        os.makedirs(self.base, exist_ok=True)
        tmp = self.ruta_estado + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(e, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta_estado)

    def _apuntar(self, **cambios):
        e = self.estado()
        e.update(cambios)
        self._guardar_estado(e)
        return e

    def archivos(self):
        try:
            return sorted(n for n in os.listdir(self.base)
                          if n.endswith(FUENTES) and os.path.isfile(os.path.join(self.base, n)))
        except OSError:
            return []

    def leer(self, nombre):
        nombre = os.path.basename(str(nombre or ""))
        if not nombre.endswith(FUENTES):
            raise TallerError(f"«{nombre}» no es un archivo del kernel.")
        try:
            with open(os.path.join(self.base, nombre), encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            raise TallerError(f"No tengo ningún «{nombre}» en el kernel.")

    def escribir(self, nombre, contenido):
        """Solo .c/.h/.s con nombre sencillo (el linker.ld y la forma de compilar no los toca el cerebro)."""
        nombre = str(nombre or "").strip()
        if not NOMBRE_OK.match(nombre):
            raise TallerError(f"No escribo «{nombre}»: solo archivos .c, .h o .s con nombre sencillo.")
        if len(contenido) > 60000:
            raise TallerError(f"«{nombre}» es demasiado grande.")
        os.makedirs(self.base, exist_ok=True)
        with open(os.path.join(self.base, nombre), "w", encoding="utf-8") as f:
            f.write(contenido)

    def asegurar(self):
        """Si el proyecto está vacío, empieza con la etapa 1 (arranca y saluda)."""
        if not self.archivos():
            self.poner_etapa(1, copiar=False)

    # ---------------- copias (deshacer) ----------------
    def copia(self, motivo=""):
        hist = os.path.join(self.base, "historial")
        os.makedirs(hist, exist_ok=True)
        previas = sorted(d for d in os.listdir(hist) if d.isdigit())
        n = (int(previas[-1]) + 1) if previas else 1
        dest = os.path.join(hist, f"{n:04d}")
        os.makedirs(dest)
        for a in self.archivos():
            shutil.copy2(os.path.join(self.base, a), os.path.join(dest, a))
        with open(os.path.join(dest, "motivo.txt"), "w", encoding="utf-8") as f:
            f.write(json.dumps({"motivo": motivo, "cuando": _ahora(), "etapa": self.estado().get("etapa", 0)},
                               ensure_ascii=False))
        for viejo in previas[:max(0, len(previas) + 1 - MAX_COPIAS)]:
            shutil.rmtree(os.path.join(hist, viejo), ignore_errors=True)
        return dest

    def deshacer(self):
        hist = os.path.join(self.base, "historial")
        try:
            previas = sorted(d for d in os.listdir(hist) if d.isdigit())
        except OSError:
            previas = []
        if not previas:
            return None
        org = os.path.join(hist, previas[-1])
        for a in self.archivos():
            os.remove(os.path.join(self.base, a))
        info = {}
        for a in os.listdir(org):
            if a == "motivo.txt":
                try:
                    with open(os.path.join(org, a), encoding="utf-8") as f:
                        info = json.loads(f.read() or "{}")
                except (OSError, ValueError):
                    info = {}
                continue
            shutil.copy2(os.path.join(org, a), os.path.join(self.base, a))
        shutil.rmtree(org, ignore_errors=True)
        if "etapa" in info:
            self._apuntar(etapa=info["etapa"])
        return info.get("motivo") or "el último cambio"

    def restaurar_copia(self):
        """Vuelve a la última copia SIN gastarla (para probar varias propuestas desde el mismo punto)."""
        hist = os.path.join(self.base, "historial")
        try:
            previas = sorted(d for d in os.listdir(hist) if d.isdigit())
        except OSError:
            return False
        if not previas:
            return False
        org = os.path.join(hist, previas[-1])
        for a in self.archivos():
            os.remove(os.path.join(self.base, a))
        for a in os.listdir(org):
            if a != "motivo.txt":
                shutil.copy2(os.path.join(org, a), os.path.join(self.base, a))
        return True

    def poner_etapa(self, n, copiar=True):
        e = so.etapa(n)
        if not e:
            raise TallerError(f"No tengo la etapa {n}. Tengo de la 1 a la {len(so.ETAPAS)}.")
        if copiar and self.archivos():
            self.copia(f"antes de poner la etapa {n}")
        os.makedirs(self.base, exist_ok=True)
        for a in self.archivos():
            os.remove(os.path.join(self.base, a))
        for nombre, contenido in e["archivos"].items():
            with open(os.path.join(self.base, nombre), "w", encoding="utf-8") as f:
                f.write(contenido)
        self._apuntar(etapa=n)
        return e

    # ---------------- herramientas, compilar y arrancar ----------------
    def faltan(self):
        return [h for h in HERRAMIENTAS if not self.which(h)]

    def texto_faltan(self, faltan):
        paquetes = sorted(set(HERRAMIENTAS[h] for h in faltan))
        return ("Me faltan herramientas para el kernel: " + ", ".join(faltan) + ". Ábreme la Terminal y escribe  "
                "sudo apt install " + " ".join(paquetes) + "  (te pedirá TU contraseña). Si ya me diste el permiso "
                "de administrador una vez, basta con decirme «instala " + paquetes[0] + "».")

    def compilar(self):
        """(ok, salida). Forma FIJA de compilar: nasm para .s, gcc freestanding para .c, ld con linker.ld."""
        self.asegurar()
        falt = [h for h in ("gcc", "ld", "nasm") if not self.which(h)]
        if falt:
            return False, self.texto_faltan(falt)
        obj = os.path.join(self.base, "build")
        shutil.rmtree(obj, ignore_errors=True)
        os.makedirs(obj)
        if not os.path.isfile(os.path.join(self.base, "linker.ld")):
            with open(os.path.join(self.base, "linker.ld"), "w", encoding="utf-8") as f:
                f.write(so.etapa(1)["archivos"]["linker.ld"])
        objetos, salidas = [], []
        for a in self.archivos():
            src = os.path.join(self.base, a)
            if a.endswith(".s"):
                o = os.path.join(obj, a[:-2] + "_s.o")
                args = ["nasm", "-f", "elf32", src, "-o", o]
            elif a.endswith(".c"):
                o = os.path.join(obj, a[:-2] + ".o")
                args = ["gcc"] + CFLAGS + ["-I", self.base, "-c", src, "-o", o]
            else:
                continue
            try:
                rc, sal = self.correr(args, cwd=self.base, timeout=120)
            except Exception as e:                   # noqa: BLE001
                return False, f"No pude compilar {a}: {e}"
            if sal.strip():
                salidas.append(sal.strip())
            if rc != 0:
                return False, errores_cortos("\n".join(salidas))
            objetos.append(o)
        if not objetos:
            return False, "No hay archivos .c ni .s que compilar."
        binario = os.path.join(self.base, "kernel.bin")
        args = ["ld", "-m", "elf_i386", "-T", os.path.join(self.base, "linker.ld"), "-nostdlib", "-z", "noexecstack",
                "-o", binario] + objetos
        try:
            rc, sal = self.correr(args, cwd=self.base, timeout=120)
        except Exception as e:                       # noqa: BLE001
            return False, f"No pude enlazar: {e}"
        if sal.strip():
            salidas.append(sal.strip())
        if rc != 0:
            return False, errores_cortos("\n".join(salidas))
        avisos = errores_cortos("\n".join(salidas), 8)
        try:
            self.compilar_programas()                # v3.41: hola.elf aparte (no va dentro del kernel)
        except Exception:                            # noqa: BLE001
            pass
        return True, ("Compila bien." + (" Avisos:\n" + avisos if avisos else ""))

    @property
    def carpeta_programas(self):
        return os.path.join(self.base, "programas")

    def compilar_programas(self):
        """v3.41: compila los programas de USUARIO (hola.c…) aparte, enlazados en la zona 8 MB, y los deja en
        <kernel>/programas/*.elf. Como esa carpeta está en tu disco (~/kira_portatil/kernel/programas), el kernel que
        arranca desde el USB los encuentra en tu SSD y los ejecuta. Devuelve la lista de .elf hechos."""
        if not (self.which("gcc") and self.which("ld")):
            return []
        os.makedirs(self.carpeta_programas, exist_ok=True)
        ld = os.path.join(self.carpeta_programas, "programa.ld")
        with open(ld, "w", encoding="utf-8") as f:
            f.write(so.PROGRAMA_LD)
        hechos = []
        for nombre, fuente in so.PROGRAMAS.items():
            src = os.path.join(self.carpeta_programas, nombre)
            with open(src, "w", encoding="utf-8") as f:
                f.write(fuente)
            obj, elf = src[:-2] + ".o", src[:-2] + ".elf"
            rc, _ = self.correr(["gcc"] + CFLAGS + ["-c", src, "-o", obj], cwd=self.carpeta_programas, timeout=60)
            if rc != 0:
                continue
            rc, _ = self.correr(["ld", "-m", "elf_i386", "-T", ld, "-nostdlib", "-z", "noexecstack", "-o", elf, obj],
                                cwd=self.carpeta_programas, timeout=60)
            if rc == 0:
                hechos.append(elf)
        return hechos

    @property
    def ruta_disco(self):
        return os.path.join(self.base, "disco.img")

    def asegurar_disco(self):
        """El disco de PRUEBAS (1 MB) que ve el kernel en QEMU, con la firma «KIRADISK» en el sector 0: es el único
        disco en el que su driver se atreve a escribir."""
        if os.path.isfile(self.ruta_disco) and os.path.getsize(self.ruta_disco) == 1024 * 1024:
            return self.ruta_disco
        os.makedirs(self.base, exist_ok=True)
        cab = "KIRADISK: el disco de pruebas de Kira (QEMU)".encode()
        with open(self.ruta_disco, "wb") as f:
            f.write(cab + b"\0" * (512 - len(cab)))
            f.write(b"\0" * (1024 * 1024 - 512))
        return self.ruta_disco

    def asegurar_discos_ahci(self):
        """v3.40: dos discos SATA de PRUEBAS para el driver AHCI (solo lectura): uno con tabla MBR y otro con GPT, con
        particiones de ejemplo (Linux, swap, EFI). Se crean una vez en la carpeta del kernel."""
        os.makedirs(self.base, exist_ok=True)
        rutas = [os.path.join(self.base, "disco_ahci_mbr.img"), os.path.join(self.base, "disco_ahci_gpt.img")]
        firma = self._firma_discos()
        ruta_firma = os.path.join(self.base, "discos.firma")
        try:
            with open(ruta_firma, encoding="utf-8") as f:
                igual = f.read() == firma
        except OSError:
            igual = False
        if igual and all(os.path.isfile(r) for r in rutas):
            return rutas
        for ruta, datos in zip(rutas, (disco_mbr(), disco_gpt(self.contenido_ext4()))):
            with open(ruta, "wb") as f:
                f.write(datos)
        with open(ruta_firma, "w", encoding="utf-8") as f:
            f.write(firma)
        return rutas

    def _firma_discos(self):
        import hashlib
        h = hashlib.sha256(DISCOS_VERSION.encode())
        for elf in sorted(glob.glob(os.path.join(self.carpeta_programas, "*.elf"))):
            with open(elf, "rb") as f:
                h.update(f.read())
        return h.hexdigest()

    def contenido_ext4(self):
        """v3.41: un ext4 DE VERDAD (hecho con mke2fs, con las mismas opciones que Ubuntu: 64 bits, extents, carpetas
        indexadas) con /kira.txt, /home/papi/notas.txt y /programas/*.elf. Sin mke2fs → None (disco sin archivos)."""
        mke2fs = self.which("mke2fs") or self.which("mkfs.ext4")
        if not mke2fs:
            return None
        if not glob.glob(os.path.join(self.carpeta_programas, "*.elf")):
            self.compilar_programas()
        raiz = os.path.join(self.base, "disco_raiz")
        shutil.rmtree(raiz, ignore_errors=True)
        os.makedirs(os.path.join(raiz, "home", "papi"))
        os.makedirs(os.path.join(raiz, "programas"))
        with open(os.path.join(raiz, "kira.txt"), "w", encoding="utf-8") as f:
            f.write("Hola desde el disco de Kira\n")
        with open(os.path.join(raiz, "home", "papi", "notas.txt"), "w", encoding="utf-8") as f:
            f.write("Notas de papi: el kernel de Kira lee este archivo de un ext4 de verdad.\n")
        for elf in glob.glob(os.path.join(self.carpeta_programas, "*.elf")):
            shutil.copy(elf, os.path.join(raiz, "programas"))
        img = os.path.join(self.base, "ext4.img")
        try:
            os.remove(img)
        except OSError:
            pass
        rc, sal = self.correr([mke2fs, "-q", "-F", "-t", "ext4", "-b", "4096", "-I", "256", "-L", "KIRA",
                               "-O", "64bit,metadata_csum,extent,flex_bg,dir_index", "-d", raiz, img, "16M"],
                              cwd=self.base, timeout=60)
        if rc != 0 or not os.path.isfile(img):
            return None
        with open(img, "rb") as f:
            return f.read()

    def _aparatos(self):
        """Lo que se le enchufa al ordenador de mentira: el disco de pruebas y una tarjeta de red e1000 con la red de
        QEMU AISLADA (restrict=on: ni internet ni tu casa; solo su router virtual 10.0.2.2)."""
        return ["-drive", f"file={self.asegurar_disco()},format=raw,if=ide,index=0,media=disk",
                "-netdev", "user,id=red0,restrict=on", "-device", "e1000,netdev=red0"] + self._sata()

    def _sata(self):
        mbr, gpt = self.asegurar_discos_ahci()
        return ["-device", "ahci,id=ahci0",
                "-drive", f"file={mbr},format=raw,if=none,id=sata0", "-device", "ide-hd,drive=sata0,bus=ahci0.0",
                "-drive", f"file={gpt},format=raw,if=none,id=sata1", "-device", "ide-hd,drive=sata1,bus=ahci0.1"]

    def orden_qemu(self, con_pantalla=False):
        args = ["qemu-system-i386", "-kernel", os.path.join(self.base, "kernel.bin"), "-m", "128",
                "-no-reboot"] + self._aparatos()
        if con_pantalla:
            return args + ["-serial", "null", "-name", "Kernel de Kira"]
        return args + ["-display", "none", "-serial", "stdio", "-monitor", "none",
                       "-d", "int,cpu_reset", "-D", os.path.join(self.base, "qemu.log")]

    def arrancar(self, espera=None, segundos=ESPERA_QEMU, entrada=None):
        """Arranca kernel.bin en QEMU sin pantalla y lee el puerto serie. Para en cuanto salen todas las marcas
        esperadas (o al acabar el tiempo). Devuelve {ok, serie, reinicio, excepciones, faltan, motivo}."""
        espera = list(espera or ["KERNEL_LISTO"])
        if not self.which("qemu-system-i386"):
            return {"ok": False, "serie": "", "reinicio": False, "excepciones": [], "faltan": espera,
                    "motivo": self.texto_faltan(["qemu-system-i386"])}
        if not os.path.isfile(os.path.join(self.base, "kernel.bin")):
            return {"ok": False, "serie": "", "reinicio": False, "excepciones": [], "faltan": espera,
                    "motivo": "No hay kernel.bin: compila antes."}
        return self._correr_qemu(self.orden_qemu(), espera, segundos, entrada)

    def _correr_qemu(self, args, espera, segundos, entrada=None):
        """entrada (v3.41): lo que se le «escribe» al kernel por el puerto serie cuando dice KERNEL_LISTO (para probar
        su consola «kira>» como si tecleara alguien)."""
        if not self.which("qemu-system-i386"):
            return {"ok": False, "serie": "", "reinicio": False, "excepciones": [], "faltan": espera,
                    "motivo": self.texto_faltan(["qemu-system-i386"])}
        log = os.path.join(self.base, "qemu.log")
        try:
            os.remove(log)
        except OSError:
            pass
        serie = ""
        try:
            p = self.popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           stdin=subprocess.PIPE if entrada else subprocess.DEVNULL, cwd=self.base)
        except Exception as e:                       # noqa: BLE001
            return {"ok": False, "serie": "", "reinicio": False, "excepciones": [], "faltan": espera,
                    "motivo": f"No pude arrancar QEMU: {e}"}
        fin = time.time() + segundos
        listo_en = None
        salio_solo = False                           # el kernel acaba en un bucle hlt: si QEMU se va solo, se cayó
        try:
            while time.time() < fin:
                if p.poll() is not None:
                    salio_solo = True
                    resto = p.stdout.read() or b""
                    serie += resto.decode("utf-8", "replace")
                    break
                r, _w, _x = select.select([p.stdout], [], [], 0.2)
                if r:
                    trozo = os.read(p.stdout.fileno(), 4096)
                    if not trozo:
                        break
                    serie += trozo.decode("utf-8", "replace")
                    if entrada and "KERNEL_LISTO" in serie:
                        try:
                            p.stdin.write(entrada.encode())
                            p.stdin.flush()
                        except Exception:            # noqa: BLE001
                            pass
                        entrada = None
                    if listo_en is None and all(m in serie for m in espera):
                        listo_en = time.time()
                if listo_en and time.time() - listo_en > 0.4:
                    break
        finally:
            if p.poll() is None:
                p.kill()
                try:
                    p.wait(timeout=5)
                except Exception:                    # noqa: BLE001
                    pass
        try:
            with open(log, encoding="utf-8", errors="replace") as f:
                registro = f.read()[-400000:]
        except OSError:
            registro = ""
        reinicio, exc = excepciones_de_registro(registro)
        reinicio = reinicio or salio_solo
        faltan = [m for m in espera if m not in serie]
        ok = not faltan and not reinicio
        if ok:
            motivo = "Arranca y funciona."
        elif reinicio:
            motivo = "Se colgó y el procesador se reinició (triple fallo)." + (
                " Últimas excepciones: " + "; ".join(exc[-4:]) if exc else "")
        else:
            motivo = "No salió lo esperado por el puerto serie: falta " + ", ".join(f"«{m}»" for m in faltan) + "."
        return {"ok": ok, "serie": serie.replace("\r", "")[-3000:], "reinicio": reinicio, "excepciones": exc,
                "faltan": faltan, "motivo": motivo}

    def probar(self, espera=None, entrada=None):
        """Compila y arranca. Devuelve {ok, fase: 'compilar'|'arrancar', texto, serie, ...}. `entrada`: órdenes para su
        consola (etapas 11+)."""
        ok, sal = self.compilar()
        if not ok:
            r = {"ok": False, "fase": "compilar", "texto": sal, "serie": ""}
        else:
            a = self.arrancar(espera, segundos=20 if entrada else ESPERA_QEMU, entrada=entrada)
            r = dict(a, fase="arrancar", texto=a["motivo"])
        self._apuntar(ultima={"ok": r["ok"], "cuando": _ahora(), "fase": r["fase"], "texto": r["texto"][:500],
                              "serie": r.get("serie", "")[-800:]})
        return r

    def ver(self):
        """QEMU CON pantalla para que el dueño vea su kernel (y teclee, si está la etapa del teclado)."""
        ok, sal = self.compilar()
        if not ok:
            return False, "No puedo enseñártelo: no compila.\n" + sal
        if not self.which("qemu-system-i386"):
            return False, self.texto_faltan(["qemu-system-i386"])
        env = dict(os.environ)
        env.setdefault("DISPLAY", ":0")
        try:
            self.popen(self.orden_qemu(con_pantalla=True), cwd=self.base, env=env, start_new_session=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:                       # noqa: BLE001
            return False, f"No pude abrir la ventana de QEMU: {e}"
        return True, ("Te abro mi kernel en una ventana de QEMU (un ordenador de mentira, sin red ni discos). "
                      "Ciérrala cuando quieras.")

    # ---------------- arrancar desde un USB (v3.36) ----------------
    @property
    def ruta_iso(self):
        return os.path.join(self.base, "kira_kernel.iso")

    def faltan_iso(self):
        falta = [h for h in ("grub-mkrescue", "xorriso") if not self.which(h)]
        if not os.path.isdir(GRUB_PC) and "grub-mkrescue" not in falta:
            falta.append("grub-pc-bin")
        return falta

    def hacer_iso(self, espera=10):
        """Mete el kernel en una imagen arrancable con GRUB (sirve para un pendrive USB o un CD). (ok, texto)."""
        ok, sal = self.compilar()
        if not ok:
            return False, "No compila, así que no hago el USB:\n" + sal
        falta = self.faltan_iso()
        if falta:
            paq = sorted({"grub-mkrescue": "grub-common", "xorriso": "xorriso", "grub-pc-bin": "grub-pc-bin"}[x]
                         for x in falta)
            return False, ("Para preparar el USB me falta: " + ", ".join(falta) + ". En la Terminal:  sudo apt install "
                           + " ".join(paq + ["mtools"]) + "  (o «instala " + paq[0] + "» si ya me diste el permiso).")
        carpeta = os.path.join(self.base, "iso")
        shutil.rmtree(carpeta, ignore_errors=True)
        os.makedirs(os.path.join(carpeta, "boot", "grub"))
        shutil.copy2(os.path.join(self.base, "kernel.bin"), os.path.join(carpeta, "boot", "kernel.bin"))
        with open(os.path.join(carpeta, "boot", "grub", "grub.cfg"), "w", encoding="utf-8") as f:
            f.write(grub_cfg(espera))
        try:
            rc, salida = self.correr(["grub-mkrescue", "-o", self.ruta_iso, carpeta], cwd=self.base, timeout=300)
        except Exception as e:                       # noqa: BLE001
            return False, f"No pude hacer la imagen: {e}"
        if rc != 0 or not os.path.isfile(self.ruta_iso):
            return False, "grub-mkrescue falló:\n" + errores_cortos(salida, 10)
        mb = os.path.getsize(self.ruta_iso) / 1024 / 1024
        return True, f"Imagen arrancable lista: {self.ruta_iso} ({mb:.1f} MB)."

    def probar_iso(self, espera=None, segundos=40, entrada=None):
        """Arranca la IMAGEN en QEMU como si fuera el USB (BIOS → GRUB → kernel): comprueba el camino real."""
        espera = list(espera or ["KERNEL_LISTO"])
        if not os.path.isfile(self.ruta_iso):
            return {"ok": False, "motivo": "No hay imagen: hazla antes.", "serie": ""}
        args = ["qemu-system-i386", "-cdrom", self.ruta_iso, "-boot", "d", "-m", "128", "-no-reboot",
                "-display", "none", "-serial", "stdio", "-monitor", "none"] + self._aparatos()
        return self._correr_qemu(args, espera, segundos, entrada)

    def usbs(self):
        """Los pendrives USB conectados (solo discos USB extraíbles). [] si no hay o no está lsblk."""
        try:
            rc, salida = self.correr(["lsblk", "-J", "-d", "-o", "NAME,RM,TRAN,SIZE,MODEL,TYPE"], timeout=20)
        except Exception:                            # noqa: BLE001
            return []
        return usbs_de_lsblk(salida) if rc == 0 else []

    def texto_usb(self, ok_iso, texto_iso):
        if not ok_iso:
            return "[x] " + texto_iso
        usbs = self.usbs()
        lin = [texto_iso + " Dentro va tu kernel con un menú de GRUB: «Kernel de Kira» o «Reiniciar».", ""]
        if usbs:
            lin.append("Pendrives que veo conectados: " + "; ".join(
                f"{u['dispositivo']} ({u['modelo'] or 'sin nombre'}, {u['tamano']})" for u in usbs) + ".")
        else:
            lin.append("No veo ningún pendrive conectado. Conéctalo y dime «busca mi USB».")
        lin += ["",
                "Para GRABARLO en el pendrive (¡BORRA todo lo que tenga!) lo haces TÚ, no yo: yo nunca escribo en un "
                "disco. En la Terminal escribe  cd kira_god/kira_portatil  (Intro) y luego  bash grabar_usb  (Intro; "
                "con Tab se completa). Te enseña los pendrives, eliges el número, escribes SI y te pide TU contraseña.",
                "",
                "Para arrancarlo: reinicia, pulsa F12 al encender, elige el USB y luego «Kernel de Kira». Con Esc se "
                "reinicia y vuelves a KiraOS. Linux y tus archivos no se tocan.",
                "Si al arrancar la pantalla se queda en negro: tu portátil está arrancando en modo UEFI; en la BIOS "
                "(F2) pon el arranque en «Legacy». Así se ve la pantalla de texto del kernel."]
        return "\n".join(lin)

    # ---------------- programar con el cerebro ----------------
    def _relevantes(self, tarea, maximo=2600):
        """kernel.c + el archivo que más se parece a lo pedido, recortados (el cerebro pequeño lee poco)."""
        pal = _palabras(tarea)
        puntos = []
        for a in self.archivos():
            if a in ("linker.ld", "kernel.c"):
                continue
            try:
                txt = self.leer(a)
            except TallerError:
                continue
            p = len(pal & _palabras(a + " " + txt[:3000])) + (3 if any(w in a.lower() for w in pal) else 0)
            puntos.append((p, a, txt))
        puntos.sort(key=lambda x: -x[0])
        trozos, usado = [], 0
        try:
            k = self.leer("kernel.c")
            trozos.append(("kernel.c", k))
            usado += len(k)
        except TallerError:
            pass
        for p, a, txt in puntos[:1]:
            if p > 0 and usado + len(txt) <= maximo:
                trozos.append((a, txt))
                usado += len(txt)
        return trozos

    def pedido_cerebro(self, tarea, error_previo=""):
        partes = [f"Lo que hay que hacer en el kernel: {tarea}", "Archivos del proyecto: " + ", ".join(self.archivos())]
        for t, x in so.fichas_para(tarea, n=1):
            partes.append(f"Lo que sabes de esto ({t}): {x[:500]}")
        for a, txt in self._relevantes(tarea):
            partes.append(f"Así está ahora {a}:\n```c\n{txt.strip()}\n```")
        if error_previo:
            partes.append("Tu intento anterior falló así (corrígelo):\n" + error_previo[:900])
        return "\n\n".join(partes)

    def _con_ayuda(self, ayuda, tarea, error, paso):
        """v3.35: tras dos fallos seguidos, pregunta a OTRAS IA (ayuda_ias_kira) y prueba cada propuesta en QEMU desde
        el punto de partida. Devuelve el resultado de la ayuda (con 'archivos' si alguna funcionó)."""
        codigo = "\n\n".join(f"// ---- {a} ----\n{txt}" for a, txt in self._relevantes(tarea, maximo=6000))
        puestos = {}

        def probar(texto):
            nuevos = {n: c for n, c in extraer_archivos(texto, tarea).items() if NOMBRE_OK.match(n)}
            if not nuevos:
                return False, "no trajo archivos con el formato «ARCHIVO: nombre.c» + bloque de código"
            self.restaurar_copia()
            for n, c in nuevos.items():
                self.escribir(n, c)
            r = self.probar()
            if r["ok"]:
                puestos.clear()
                puestos.update(nuevos)
                return True, "compila y arranca en QEMU"
            return False, ("no compila: " + r["texto"][:600]) if r["fase"] == "compilar" else r["texto"][:600]

        res = ayuda(tarea=tarea, codigo=codigo, error=error, probar=probar, system=SISTEMA, formato="c",
                    al_paso=lambda t: paso(None, t))
        res["archivos"] = sorted(puestos)
        if not res.get("ok"):
            self.restaurar_copia()
        return res

    def programar(self, tarea, preguntar=None, al_paso=None, intentos=4, parar=None, ayuda=None):
        """Hace lo pedido en el kernel. Devuelve {ok, texto, serie?}. Nunca deja el kernel roto: si no lo logra,
        vuelve a la copia de antes. v3.35: `ayuda(tarea, codigo, error, probar, system, formato, al_paso)` = preguntar
        a otras IA tras DOS fallos seguidos (solo si no sabe)."""
        paso = al_paso or (lambda fr, t: None)
        parar = parar or (lambda: False)
        self.asegurar()
        actual = int(self.estado().get("etapa", 0) or 0)
        e = so.etapa_para(tarea)
        if e and e["n"] <= actual:
            return {"ok": True, "texto": (f"Eso ya lo tiene mi kernel: es la etapa {e['n']} ({e['titulo']}) y la "
                                          "llevo puesta. Di «prueba el kernel» para verlo funcionar, o pídeme algo "
                                          "más concreto (por ejemplo «programa el kernel: que el temporizador "
                                          "cuente segundos»).")}
        if e:
            paso(0.2, f"Lo tengo en mis plantillas probadas: etapa {e['n']} ({e['titulo']}).")
            self.poner_etapa(e["n"])
            paso(0.5, "Compilo y lo arranco en QEMU…")
            r = self.probar(e["espera"], e.get("entrada"))
            if r["ok"]:
                self._cambio(tarea, True)
                return {"ok": True, "serie": r.get("serie", ""),
                        "texto": (f"Hecho con mi plantilla probada (etapa {e['n']}: {e['titulo']}). Compila y arranca "
                                  f"en QEMU. Esto salió por el puerto serie:\n{r.get('serie', '').strip()[-900:]}\n\n"
                                  "Di «enséñame el kernel funcionando» para verlo en una ventana.")}
            self.deshacer()
            return {"ok": False, "texto": (f"[x] Puse la plantilla de la etapa {e['n']}, pero aquí no funcionó "
                                           f"({r['fase']}): {r['texto'][:700]}\nHe vuelto a como estaba.")}
        if preguntar is None:
            return {"ok": False, "texto": "[x] Para programar eso necesito mi cerebro, y no lo tengo listo."}
        falt = self.faltan()
        if falt:
            return {"ok": False, "texto": "[x] " + self.texto_faltan(falt)}
        self.copia(f"antes de: {tarea[:80]}")
        error = ""
        for i in range(1, intentos + 1):
            if parar():
                self.deshacer()
                return {"ok": False, "texto": "Parado. He dejado el kernel como estaba."}
            paso((i - 1) / intentos, f"Intento {i} de {intentos}: escribo el código…")
            try:
                resp = preguntar(SISTEMA, self.pedido_cerebro(tarea, error))
            except Exception as ex:                  # noqa: BLE001 - sin cerebro, cancelado…
                self.deshacer()
                return {"ok": False, "texto": f"[x] No pude pensar el código: {ex}. He dejado el kernel como estaba."}
            nuevos = extraer_archivos(resp, tarea)
            malos = [n for n in nuevos if not NOMBRE_OK.match(n)]
            for n in malos:
                nuevos.pop(n)
            if not nuevos:
                error = ("No me diste ningún archivo con el formato «ARCHIVO: nombre.c» y el bloque ```c."
                         + (f" (Ignoré {', '.join(malos)}: solo .c/.h/.s.)" if malos else ""))
                continue
            for n, c in nuevos.items():
                self.escribir(n, c)
            paso((i - 0.5) / intentos, f"Intento {i}: compilo y lo arranco en QEMU…")
            r = self.probar()
            if r["ok"]:
                self._cambio(tarea, True)
                return {"ok": True, "serie": r.get("serie", ""), "archivos": sorted(nuevos),
                        "texto": (f"Hecho en el intento {i}: he cambiado {', '.join(sorted(nuevos))}. Compila y "
                                  f"arranca en QEMU. Puerto serie:\n{r.get('serie', '').strip()[-900:]}")}
            if r["fase"] == "compilar":
                error = "No compila:\n" + r["texto"]
            else:
                error = r["texto"] + ("\nPuerto serie:\n" + r.get("serie", "")[-500:] if r.get("serie") else "")
            if i == 2 and ayuda is not None:          # v3.35: dos fallos seguidos → pregunto a otras IA
                res = self._con_ayuda(ayuda, tarea, error, paso)
                if res.get("ok"):
                    self._cambio(tarea + f" (con ayuda de {res['ia']})", True)
                    hist = self.estado().get("ultima", {})
                    return {"ok": True, "serie": hist.get("serie", ""), "archivos": res["archivos"], "ia": res["ia"],
                            "texto": (f"No me salía sola (2 intentos), así que pregunté a otras IA. La propuesta de "
                                      f"{res['ia']} compila y arranca en QEMU: la he puesto "
                                      f"({', '.join(res['archivos'])}). Lo que me recomendó queda en mi baúl para "
                                      f"aprenderlo. Preguntas: {_txt_hist(res['historial'])}.\nPuerto serie:\n"
                                      f"{hist.get('serie', '').strip()[-700:]}")}
                if not res.get("sin_ias"):
                    paso(None, "Ninguna otra IA dio con ello; sigo intentándolo yo.")
                    error += "\n(Otras IA tampoco lo resolvieron: " + _txt_hist(res.get("historial", []))[:400] + ")"
        self.deshacer()
        self._cambio(tarea, False)
        return {"ok": False, "texto": (f"[x] Lo intenté {intentos} veces y no me salió. Lo último que falló:\n"
                                       f"{error[:800]}\nHe dejado el kernel como estaba (funcionando). Puedes "
                                       "pedírmelo más concreto o por partes.")}

    def _cambio(self, tarea, ok):
        e = self.estado()
        cambios = (e.get("cambios") or [])[-29:]
        cambios.append({"tarea": tarea[:200], "ok": ok, "cuando": _ahora()})
        self._apuntar(cambios=cambios)

    # ---------------- textos ----------------
    def texto_estado(self):
        e = self.estado()
        arch = self.archivos()
        if not arch:
            return ("Aún no he empezado mi kernel. Dime «pon la etapa 1 del kernel» o «programa el kernel: …» y "
                    "empiezo (" + so.etapa(1)["titulo"].lower() + ").")
        et = int(e.get("etapa", 0) or 0)
        lineas = [f"Mi kernel está en la etapa {et}" + (f" ({so.etapa(et)['titulo']})" if so.etapa(et) else "") +
                  f", con {len(arch)} archivos en {self.base}."]
        u = e.get("ultima") or {}
        if u:
            lineas.append(f"Última prueba ({u.get('cuando', '')}): " + ("funciona ✓" if u.get("ok") else
                                                                      "falló ✗ — " + str(u.get("texto", ""))[:200]))
        for c in (e.get("cambios") or [])[-5:]:
            lineas.append(f" · {c.get('cuando', '')} {'✓' if c.get('ok') else '✗'} {c.get('tarea', '')}")
        sig = so.etapa(et + 1)
        if sig:
            lineas.append(f"Siguiente etapa: {sig['n']}. {sig['titulo']} («pon la etapa {sig['n']} del kernel»).")
        falt = self.faltan()
        if falt:
            lineas.append(self.texto_faltan(falt))
        return "\n".join(lineas)

    def texto_archivos(self):
        arch = self.archivos()
        if not arch:
            return "Mi kernel aún no tiene archivos."
        lin = ["Archivos de mi kernel:"]
        for a in arch:
            try:
                n = len(self.leer(a).splitlines())
            except TallerError:
                n = 0
            lin.append(f" · {a} ({n} líneas)")
        lin.append("Di «enséñame el archivo X del kernel» para leer uno.")
        return "\n".join(lin)


# ---------------------------------------------------------------- órdenes
_K = r"(?:el|mi|tu|del|de\s+mi|de\s+tu)\s+kernel"


def orden(texto):
    """(accion, carga) o None. Puro."""
    t = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", str(texto or ""), flags=re.I).strip()
    # v3.39: faltas típicas al escribir «kernel» (visto en el Packard Bell: «kermel»)
    t = re.sub(r"\b(?:kermel|kernell?|kernal|kenel|kernerl|kenrel|kernerl|kenrnel|kerne|kermnel|kernle|cernel|kernelk)\b",
               "kernel", t, flags=re.I)
    low = so._norm(t).rstrip(" .!?¿¡")
    if re.match(r"^(?:busca|ve|mira|que|cuales\s+son)\s+(?:mi|mis|el|los|tengo)?\s*(?:usb|pendrives?|memorias?\s+usb)"
                r"(?:\s+(?:tengo|hay|conectados?))?$", low):
        return ("usbs", "")
    if "kernel" not in low:
        return None
    m = re.match(r"^(?:programa(?:me)?|mejora|cambia|modifica|anade|haz|ponle|arregla)\s+(?:en\s+)?" + _K +
                 r"\s*[:,]?\s*(.+)$", low)
    if not m:
        m = re.match(r"^(?:en\s+)?" + r"(?:el\s+|mi\s+|tu\s+)?kernel\s*[:,]\s*(.+)$", low)
    if m:
        t2 = t.rstrip(" .!?¿¡")
        carga = t2[m.start(1):].strip() if len(t2) == len(low) else m.group(1)
        return ("programar", carga)
    if re.match(r"^(?:prepara|haz|crea|graba|pon)(?:me)?\s+(?:el\s+|un\s+)?(?:usb|pendrive|iso)\s+(?:del|de\s+tu|de\s+mi|con\s+el|para\s+el)\s+"
                r"kernel$|^(?:prepara|pon)(?:me)?\s+" + _K + r"\s+(?:en|para\s+(?:arrancar\s+(?:desde|en|con)\s+)?)\s*(?:un\s+|el\s+)?"
                r"(?:usb|pendrive)$|^(?:haz|crea)(?:me)?\s+la\s+iso\s+" + _K + r"$", low):
        return ("usb", "")
    if re.match(r"^compila(?:me)?\s+" + _K + r"$", low):
        return ("compilar", "")
    if re.match(r"^(?:ensename|muestrame|abre|ensenamelo)\s+" + _K + r"\s+(?:funcionando|en\s+(?:una\s+)?ventana|en\s+qemu)$",
                low) or re.match(r"^(?:quiero\s+)?ver\s+" + _K + r"(?:\s+funcionando)?$", low):
        return ("ver", "")
    if re.match(r"^(?:prueba|arranca|ejecuta|lanza|comprueba)(?:me)?\s+" + _K + r"$", low):
        return ("probar", "")
    m = re.match(r"^(?:ensename|muestrame|lee(?:me)?|abre)\s+(?:el\s+)?archivo\s+([\w.]+)\s+(?:del|de\s+tu|de\s+mi)\s+kernel$",
                 low)
    if m:
        return ("leer", m.group(1))
    if re.match(r"^(?:los\s+)?archivos\s+" + _K + r"$|^(?:ensename|muestrame)\s+" + _K + r"$", low):
        return ("archivos", "")
    if re.match(r"^(?:las\s+|que\s+|cuales\s+son\s+las\s+)?etapas\s+" + _K + r"$", low):
        return ("etapas", "")
    m = re.match(r"^(?:pon|aplica|pasa\s+a|ve\s+a)\s+(?:la\s+)?etapa\s+(\d)\s*(?:" + _K + r")?$", low)
    if m:
        return ("etapa", m.group(1))
    if re.match(r"^(?:deshaz|deshacer)\s+(?:el\s+)?(?:ultimo\s+cambio|lo\s+ultimo)\s+" + _K + r"$", low):
        return ("deshacer", "")
    if re.match(r"^(?:empieza|reinicia|borra|vuelve\s+a\s+empezar)\s+" + _K + r"\s+(?:de|desde)\s+cero$", low):
        return ("cero", "")
    if re.match(r"^(?:estado|como\s+va|que\s+tal\s+va)\s+" + _K + r"$", low) or re.match(r"^(?:tu|mi|el)\s+kernel$", low):
        return ("estado", "")
    return None


def _txt_hist(hist):
    return "; ".join(f"{ia} {'✓' if ok else '✗'}" for ia, ok, _m in hist) or "ninguna contestó"


def hacer(taller, accion, carga="", preguntar=None, al_paso=None, parar=None, ayuda=None):
    """Hace la orden. Devuelve {texto, ok?}."""
    paso = al_paso or (lambda fr, t: None)
    try:
        if accion == "programar":
            return taller.programar(carga, preguntar=preguntar, al_paso=paso, parar=parar, ayuda=ayuda)
        if accion == "compilar":
            paso(0.3, "Compilo el kernel…")
            ok, sal = taller.compilar()
            return {"texto": ("✓ " if ok else "[x] No compila:\n") + sal, **({} if ok else {"ok": False})}
        if accion == "probar":
            paso(0.3, "Compilo y lo arranco en QEMU…")
            e = so.etapa(int(taller.estado().get("etapa", 0) or 0))
            r = taller.probar(e["espera"] if e else None, e.get("entrada") if e else None)
            if r["ok"]:
                return {"texto": "✓ Mi kernel compila y arranca. Puerto serie:\n" + r.get("serie", "").strip()[-1200:]}
            return {"ok": False, "texto": f"[x] Falla al {r['fase']}: {r['texto'][:900]}" +
                    ("\nPuerto serie:\n" + r["serie"][-600:] if r.get("serie") else "")}
        if accion == "ver":
            ok, msg = taller.ver()
            return {"texto": msg if ok else "[x] " + msg, **({} if ok else {"ok": False})}
        if accion == "leer":
            return {"texto": f"{carga}:\n```\n{taller.leer(carga)}\n```"}
        if accion == "archivos":
            return {"texto": taller.texto_archivos()}
        if accion == "etapas":
            return {"texto": so.texto_etapas(int(taller.estado().get("etapa", 0) or 0))}
        if accion == "etapa":
            e = taller.poner_etapa(int(carga))
            paso(0.5, "Compilo y lo arranco en QEMU…")
            r = taller.probar(e["espera"], e.get("entrada"))
            return {"texto": (f"Puesta la etapa {e['n']} ({e['titulo']}). " +
                              ("Funciona ✓. Puerto serie:\n" + r.get("serie", "").strip()[-900:] if r["ok"] else
                               f"Pero aquí falla ({r['fase']}): {r['texto'][:600]}"))}
        if accion == "usb":
            falta = [h for h in ("gcc", "ld", "nasm") if not taller.which(h)] + taller.faltan_iso()
            if falta:                                # v3.37: TODO lo que falta de una vez (no a trozos)
                paq = sorted({"gcc": "build-essential", "ld": "binutils", "nasm": "nasm", "grub-mkrescue": "grub-common",
                              "xorriso": "xorriso", "grub-pc-bin": "grub-pc-bin"}[x] for x in falta)
                paq = sorted(set(paq + (["mtools", "grub-pc-bin"] if set(falta) & {"grub-mkrescue", "xorriso",
                                                                                  "grub-pc-bin"} else [])))
                return {"ok": False, "texto": (
                    "Para preparar el USB me faltan programas: " + ", ".join(falta) + ". Ábreme la Terminal y escribe "
                    "esta línea entera (te pedirá TU contraseña):\n\n  sudo apt install " + " ".join(paq) +
                    "\n\nLuego vuelve a decirme «prepara el USB del kernel».")}
            paso(0.3, "Meto el kernel en una imagen arrancable con GRUB…")
            ok, txt = taller.hacer_iso()
            return {"texto": taller.texto_usb(ok, txt), **({} if ok else {"ok": False})}
        if accion == "usbs":
            us = taller.usbs()
            return {"texto": ("Pendrives conectados: " + "; ".join(f"{u['dispositivo']} ({u['modelo'] or 'sin nombre'}, "
                                                                  f"{u['tamano']})" for u in us) + "."
                              if us else "No veo ningún pendrive USB conectado.")}
        if accion == "deshacer":
            q = taller.deshacer()
            return {"texto": f"Deshecho: he vuelto a como estaba {q}." if q else "No tengo cambios que deshacer."}
        if accion == "cero":
            if taller.archivos():
                taller.copia("antes de empezar de cero")
            taller.poner_etapa(1, copiar=False)
            return {"texto": ("Kernel empezado de cero (etapa 1: arranca y saluda). Lo de antes queda guardado: "
                              "«deshaz el último cambio del kernel» lo recupera.")}
        return {"texto": taller.texto_estado()}
    except TallerError as e:
        return {"ok": False, "texto": f"[x] {e}"}


def probar_etapas(base, salida=None, probar_usb=False):
    """Para el flujo de GitHub: pone cada etapa, la compila y la arranca de verdad en QEMU. Devuelve True si todas
    funcionan. Escribe un informe en `salida` si se da."""
    t = Taller(base=base)
    informe, todo = [], True
    for e in so.ETAPAS:
        t.poner_etapa(e["n"], copiar=False)
        r = t.probar(e["espera"], e.get("entrada"))
        todo = todo and r["ok"]
        informe.append(f"== Etapa {e['n']}: {e['titulo']} → {'OK' if r['ok'] else 'FALLA'} ({r['fase']}: "
                       f"{r['texto'][:300]})\n{r.get('serie', '').strip()}\n" +
                       ("Excepciones: " + "; ".join(r.get("excepciones", [])) + "\n" if r.get("excepciones") else ""))
    if probar_usb:
        ok_i, txt_i = t.hacer_iso(espera=0)
        r = t.probar_iso(so.ETAPAS[-1]["espera"], entrada=so.ETAPAS[-1].get("entrada")) if ok_i else {"ok": False, "motivo": txt_i, "serie": ""}
        todo = todo and r["ok"]
        informe.append(f"== USB (BIOS → GRUB → kernel): {'OK' if r['ok'] else 'FALLA'} ({r.get('motivo', '')[:300]})\n"
                       f"{r.get('serie', '').strip()[-1500:]}\n")
    texto = "\n".join(informe)
    if salida:
        with open(salida, "w", encoding="utf-8") as f:
            f.write(texto)
    print(texto)
    return todo


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Taller de kernel de Kira")
    ap.add_argument("--base", default=None)
    ap.add_argument("--probar-etapas", action="store_true")
    ap.add_argument("--informe", default=None)
    ap.add_argument("--usb", action="store_true", help="con --probar-etapas: también la imagen USB en QEMU")
    ap.add_argument("--etapa", type=int)
    ap.add_argument("--probar", action="store_true")
    ap.add_argument("--ver", action="store_true")
    ap.add_argument("--usbs", action="store_true", help="lista los pendrives USB (para grabar_usb.sh)")
    a = ap.parse_args()
    if a.usbs:
        if os.environ.get("KIRA_LSBLK_JSON"):
            with open(os.environ["KIRA_LSBLK_JSON"], encoding="utf-8") as f:
                lista = usbs_de_lsblk(f.read())
        else:
            lista = Taller(base=a.base).usbs()
        for i, u in enumerate(lista, 1):
            print(f"{i}) {u['dispositivo']}  {u['modelo'] or 'sin nombre'}  {u['tamano']}")
        sys.exit(0)
    if a.probar_etapas:
        sys.exit(0 if probar_etapas(a.base or BASE, a.informe, probar_usb=a.usb) else 1)
    tl = Taller(base=a.base)
    if a.etapa:
        print(hacer(tl, "etapa", str(a.etapa))["texto"])
    elif a.probar:
        print(hacer(tl, "probar")["texto"])
    elif a.ver:
        print(hacer(tl, "ver")["texto"])
    else:
        print(tl.texto_estado())
