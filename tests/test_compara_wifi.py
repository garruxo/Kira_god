"""v3.54: copiar los registros de la WiFi con Linux funcionando (copiar_regs_wifi.sh) y compararlos en el kernel
de Kira (orden «compara» de la etapa 17)."""
import os, re, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import saber_so_kira as so

FALLOS = []
N = 0


def ok(c, t):
    global N
    N += 1
    print(("  ok  " if c else "FALLA ") + t)
    if not c:
        FALLOS.append(t)


GUION = os.path.join(RAIZ, "kira_portatil", "copiar_regs_wifi.sh")


def lanzar(tmp, iw_salida, con_ath9k=True, con_analogicos=True):
    dbg = os.path.join(tmp, "dbg")
    d = os.path.join(dbg, "ieee80211", "phy0", "ath9k")
    os.makedirs(os.path.join(dbg, "ieee80211"), exist_ok=True)
    if con_ath9k:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "regdump"), "w") as f:
            f.write("0x000008 0x00000004\n0x009864 0x1fff3a5c\n0x009968 0x12345678\n0x00a20c 0x0001f000\n"
                    "0x00b4fc 0x00000001\n0x00b500 0x00000002\n")
        if con_analogicos:
            open(os.path.join(d, "regidx"), "w").close()
            with open(os.path.join(d, "regval"), "w") as f:
                f.write("0xabcdef01\n")
        with open(os.path.join(d, "dump_nfcal"), "w") as f:
            f.write("Channel Noise Floor : -95\n")
    iw = os.path.join(tmp, "iw")
    with open(iw, "w") as f:
        f.write("#!/bin/bash\ncat <<'X'\n" + iw_salida + "\nX\n")
    os.chmod(iw, 0o755)
    dest = os.path.join(tmp, "kernel")
    env = dict(os.environ, KIRA_PRUEBA="1", KIRA_KERNEL=dest, KIRA_DEBUGFS=dbg, KIRA_SUDO="",
               KIRA_IW=iw, KIRA_NMCLI=os.path.join(tmp, "no_hay_nmcli"))
    r = subprocess.run(["bash", GUION], env=env, capture_output=True, text=True, timeout=60)
    return r, dest


IW_BIEN = ("phy#0\n\tInterface wlp2s0\n\t\tifindex 3\n\t\taddr 1c:65:9d:53:b0:95\n\t\ttype managed\n"
           "\t\tchannel 6 (2437 MHz), width: 20 MHz, center1: 2437 MHz\n\t\ttxpower 20.00 dBm")

print("== el guion de Xubuntu ==")
with tempfile.TemporaryDirectory() as tmp:
    r, dest = lanzar(tmp, IW_BIEN)
    ok(r.returncode == 0, "con la WiFi conectada termina bien: " + (r.stdout + r.stderr)[-300:])
    txt = open(os.path.join(dest, "regs_linux.txt")).read() if os.path.exists(os.path.join(dest, "regs_linux.txt")) else ""
    ok(txt.startswith("# canal 6 ancho 20"), "apunta el canal y el ancho de Linux")
    ok("0x009864 0x1fff3a5c" in txt and "0x00a20c 0x0001f000" in txt and "0x00b4fc 0x00000001" in txt,
       "guarda los registros de la radio (0x9800-0xB4FF)")
    ok("0x000008" not in txt and "0x00b500" not in txt, "no guarda los de fuera de la radio")
    ok("0x007800 0xabcdef01" in txt and "0x0078fc 0xabcdef01" in txt and txt.count("0x0078") == 64,
       "lee los 64 analógicos 0x7800-0x78FC con regidx/regval")
    ok(os.path.exists(os.path.join(dest, "regs_linux_completo.txt")), "guarda el volcado completo para Claude")
    ok("-95" in open(os.path.join(dest, "regs_linux_ruido.txt")).read(), "guarda la calibración del ruido")
    ok("compara" in r.stdout, "dice qué escribir en el kernel")
    ok(open(os.path.join(tmp, "dbg/ieee80211/phy0/ath9k/regidx")).read().strip() == "0x78fc",
       "solo escribe el ÍNDICE para leer (regidx), nunca regval")

with tempfile.TemporaryDirectory() as tmp:
    r, dest = lanzar(tmp, "phy#0\n\tInterface wlp2s0\n\t\ttype managed")
    ok(r.returncode == 1 and "no esta conectada" in r.stdout, "sin WiFi conectada lo dice y no copia nada")
    ok(not os.path.exists(os.path.join(dest, "regs_linux.txt")), "  ...y no deja archivo")

with tempfile.TemporaryDirectory() as tmp:
    r, dest = lanzar(tmp, IW_BIEN, con_ath9k=False)
    ok(r.returncode == 1 and "modo de depuracion" in r.stdout, "sin la depuración de ath9k lo explica")

with tempfile.TemporaryDirectory() as tmp:
    r, dest = lanzar(tmp, IW_BIEN.replace("width: 20", "width: 40"), con_analogicos=False)
    t = open(os.path.join(dest, "regs_linux.txt")).read()
    ok(t.startswith("# canal 6 ancho 40") and "0x0078" not in t, "ancho 40 y sin regidx: sigue con lo que hay")

g = open(GUION).read()
ok("regval" in g and "> \"$d/regval\"" not in g, "el guion nunca escribe en regval (cambiaría un registro)")
r = subprocess.run(["bash", "-n", GUION], capture_output=True, text=True)
ok(r.returncode == 0, "el guion es bash válido")

print("== compara.c en el kernel ==")
e17 = [e for e in so.ETAPAS if e["n"] == 17][0]
ok("compara.c" in e17["archivos"] and "compara.h" in e17["archivos"], "la etapa 17 lleva compara.c")
ok('shell_orden("compara"' in e17["archivos"]["kernel.c"], "la consola tiene la orden «compara»")
RC = e17["archivos"]["radio.c"]
sint = RC[RC.index("int radio_sintonizar"):RC.index("uint32_t radio_reg")]
ok("AR_CR_RXE" not in sint and "wifi_dma" not in sint and "escuchar" not in sint,
   "sintonizar NO enciende la recepción ni da permiso de DMA")
ok("n + n / 8 + 1" in RC, "las esperas: 1 io_wait por microsegundo (+12 %), el reloj del kernel corre de más")

SIM = r"""
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
void kputc(char c) { putchar(c); }
void kprint(const char *s) { fputs(s, stdout); }
void kprint_dec(uint32_t n) { printf("%u", n); }
void kprint_hex(uint32_t n) { printf("0x%08X", n); }
void *kmalloc(size_t t) { return malloc(t); }
void kfree(void *p) { free(p); }
static const char *ARCH = 0;
int ext4_nombres(const char *ruta, char nombres[][32], int max) {
    (void)max; if (strcmp(ruta, "/home")) return 0; strcpy(nombres[0], "otro"); strcpy(nombres[1], "papi"); return 2; }
int ext4_existe(const char *ruta) { return ARCH && !strcmp(ruta, "/home/papi/kira_portatil/kernel/regs_linux.txt"); }
int ext4_leer(const char *ruta, void *b, uint32_t max, uint32_t *tam) {
    if (!ext4_existe(ruta)) return -1; uint32_t n = strlen(ARCH); if (tam) *tam = n;
    memcpy(b, ARCH, n < max ? n : max); return 0; }
int canal_pedido = -1, hay_tarjeta = 1;
int radio_sintonizar(int c) { canal_pedido = c; return hay_tarjeta ? 1 : -1; }
uint32_t radio_reg(uint32_t r) { return r == 0x9864 ? 0x1FFF3A00u : (r >= 0xA000 && r < 0xA040) ? r : 0x11111111u; }
void compara_orden(const char *a);
int main(int argc, char **argv) {
    static char buf[200000];
    int modo = atoi(argv[1]);
    if (modo == 1) {
        int n = sprintf(buf, "# canal 6 ancho 20\n# copiado\n0x009864 0x1fff3a5c\n0x009868 0x11111111\n0x000008 0x4\n");
        for (int i = 0; i < 50; i++) n += sprintf(buf + n, "0x%06x 0x%08x\n", 0xA100 + 4 * i, 0x22222222);
        ARCH = buf; compara_orden(argc > 2 ? argv[2] : "");
        printf("\nCANAL=%d\n", canal_pedido);
    } else if (modo == 2) { compara_orden("");
    } else if (modo == 3) { ARCH = "# canal 11 ancho 40\n0x009864 0x1fff3a00\n"; compara_orden("");
    } else { ARCH = "# canal 1\n0x009864 0x0\n"; hay_tarjeta = 0; compara_orden(""); }
    return 0;
}
"""
with tempfile.TemporaryDirectory() as tmp:
    for k in ("compara.c", "compara.h", "radio.h", "consola.h", "ext4.h", "memoria.h"):
        with open(os.path.join(tmp, k), "w") as f:
            f.write(e17["archivos"][k])
    with open(os.path.join(tmp, "sim.c"), "w") as f:
        f.write(SIM)
    exe = os.path.join(tmp, "sim")
    r = subprocess.run(["gcc", "-O1", "-Wall", "-o", exe, "sim.c", "compara.c"], cwd=tmp, capture_output=True, text=True)
    ok(r.returncode == 0, "compara.c compila en el simulador: " + r.stderr[:400])
    if r.returncode == 0:
        s1 = subprocess.run([exe, "1"], capture_output=True, text=True).stdout
        ok("CANAL=6" in s1, "pone la radio en el mismo canal que tenía Linux")
        ok("miro 52 registros, distintos 51" in s1, "compara solo la radio y cuenta los distintos: " + s1[:300])
        ok("9864 L 1FFF3A5C K 1FFF3A00" in s1, "enseña dirección, valor de Linux y el mío")
        ok("9868" not in s1, "los iguales no salen")
        ok("pagina 1 de 2" in s1 and "compara 2" in s1, "39 por página y dice cómo ver la siguiente")
        s2 = subprocess.run([exe, "1", "2"], capture_output=True, text=True).stdout
        ok("pagina 2 de 2" in s2 and "A1C4 L" in s2 and "9864 L" not in s2, "«compara 2» enseña la página 2")
        ok(sum(1 for l in s1.splitlines() if " L " in l and " K " in l) == 13, "13 filas de 3: cabe en la pantalla")
        s3 = subprocess.run([exe, "2"], capture_output=True, text=True).stdout
        ok("no encuentro" in s3 and "bash copiar_regs_wifi" in s3, "sin el archivo dice cómo hacerlo en Xubuntu")
        s4 = subprocess.run([exe, "3"], capture_output=True, text=True).stdout
        ok("ancho 40" in s4 and "OJO" in s4 and "distintos 0" in s4, "avisa si Linux iba a 40 MHz")
        s5 = subprocess.run([exe, "4"], capture_output=True, text=True).stdout
        ok("sin tarjeta" in s5, "sin tarjeta (QEMU) lo dice")

print("\n" + ("TODO BIEN (%d)" % N if not FALLOS else "FALLAN %d de %d" % (len(FALLOS), N)))
sys.exit(1 if FALLOS else 0)
