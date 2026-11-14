"""v3.47: etapa 16 del kernel — WiFi Atheros AR9287, W1 (despertar el chip y LEER su EEPROM).
QEMU no imita esta tarjeta, así que se compila wifi.c DE VERDAD (gcc del contenedor) contra un chip simulado que se
porta como la AR9287 de Linux (ath9k): RTC, SREV y la ventana de la EEPROM. Se comprueba que lee bien la MAC, la región,
las antenas y la suma, que se las arregla con un chip apagado y una EEPROM girada, que no se cuelga si la EEPROM no
contesta y, sobre todo, que NUNCA escribe en la ventana de la EEPROM."""
import os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import saber_so_kira as so

FALLOS = []
def ok(c, m):
    print(("OK   " if c else "FALLA ") + m)
    if not c: FALLOS.append(m)

E = so.etapa(16)
ok(E and E["n"] == 16 and "wifi.c" in E["archivos"] and "wifi.h" in E["archivos"], "etapa 16 con wifi.c y wifi.h")
W = E["archivos"]["wifi.c"]
ok("wifi_probar" in E["archivos"]["kernel.c"] and 'shell_orden("wifi"' in E["archivos"]["kernel.c"],
   "el kernel la prueba al arrancar y tiene la orden «wifi»")
ok(E["entrada"] == "wifi\n" and "WIFI W1:" in E["espera"], "en QEMU escribe «wifi» y espera «WIFI W1:»")
ok(so.etapa_para("que lea la eeprom de la wifi atheros")["n"] == 16, "«la wifi atheros» → etapa 16")
# seguridad leyendo el código
ok(not re.search(r"escribe\s*\(\s*EEPROM_VENTANA", W) and not re.search(r"escribe\s*\(\s*0x2[0-9a-fA-F]{3}\b", W),
   "ninguna escritura en la ventana de la EEPROM")
ok("& ~0x04u" in W, "no activa el bus master (sin DMA)")
for prohibido in ("AR_PHY", "TXDP", "AR_CR", "0x0008", "AR_DIAG", "AR_STA_ID"):
    ok(prohibido not in W, f"no toca registros de radio/envío ({prohibido})")
ok("wifi.c" not in so.etapa(15)["archivos"], "las etapas anteriores no cambian")
ok(any("W2" in s for s in so.SIGUIENTES), "lo siguiente (W2 escuchar redes) está apuntado")

SIM = r'''
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
static uint32_t regs[0x10000 / 4];
static uint16_t eep[2048];
static int modo = 0;              /* 0 normal, 1 apagado, 2 girada, 3 eeprom muda, 4 sin tarjeta, 5 nunca despierta */
static int rtc_on = 0, reset_bajo = 0, escrituras_eeprom = 0, lecturas = 0;
static uint32_t dato_eep = 0;
int sim_buscar(uint16_t *a) { if (modo == 4) return 0; *a = 0x002e; return 1; }
uint32_t sim_lee(uint32_t r) {
    lecturas++;
    if (lecturas > 5000000) { printf("BUCLE_INFINITO\n"); exit(3); }
    if (r >= 0x2000 && r < 0x3000) { uint16_t v = eep[(r - 0x2000) >> 2]; dato_eep = modo == 2 ? (uint16_t)((v >> 8) | (v << 8)) : v; return 0; }
    if (r == 0x407C) return modo == 3 ? 0x00010000 : dato_eep;
    if (r == 0x7044) return modo == 5 ? 0x1 : (rtc_on ? 0x2 : 0x1);
    if (r == 0x4020) return (0x180u << 18) | (2u << 8) | 0xFF;
    return regs[r / 4];
}
void sim_escribe(uint32_t r, uint32_t v) {
    if (r >= 0x2000 && r < 0x3000) escrituras_eeprom++;
    if (r == 0x704C && (v & 1) && modo != 1) rtc_on = 1;
    if (r == 0x7040) { if (v == 0) reset_bajo = 1; else if (reset_bajo) rtc_on = 1; }
    regs[r / 4] = v;
}
void kputc(char c) { putchar(c); }
void kprint(const char *s) { fputs(s, stdout); }
void kprint_dec(uint32_t n) { printf("%u", n); }
void kprint_hex(uint32_t n) { printf("%x", n); }
#include "wifi.h"
int main(int argc, char **argv) {
    modo = atoi(argv[1]);
    uint8_t *b = (uint8_t *)(eep + 128);
    int n = 360;                                    /* palabras de la EEPROM simulada */
    eep[0] = 0xA55A;
    for (int i = 0; i < n; i++) eep[128 + i] = (uint16_t)(i * 37 + 11);
    eep[128] = (uint16_t)(n * 2);                    /* largo en bytes */
    eep[129] = 0;                                    /* suma (se calcula abajo) */
    eep[130] = 0xE003;                               /* versión 14.3 */
    b[6] = 0x02; b[7] = 0; b[8] = 0x37; b[9] = 0; b[10] = 0x1F; b[11] = 0;
    uint8_t mac[6] = {0x00, 0x26, 0x5e, 0x12, 0x34, 0x56};
    memcpy(b + 12, mac, 6);
    b[18] = 0x03; b[19] = 0x03; b[30] = 5;
    uint16_t x = 0;
    for (int i = 0; i < n; i++) x ^= eep[128 + i];
    eep[129] = x ^ 0xFFFF;
    if (modo == 2) { eep[0] = 0x5AA5; for (int i = 0; i < n; i++) eep[128 + i] = (uint16_t)((eep[128+i] >> 8) | (eep[128+i] << 8)); }
    wifi_probar();
    printf("ESCRITURAS_EEPROM=%d\n", escrituras_eeprom);
    return 0;
}
'''

gcc = shutil.which("gcc")
ok(gcc is not None, "hay gcc para compilar el driver de verdad")
if gcc:
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "wifi.c"), "w").write(W)
        open(os.path.join(d, "wifi.h"), "w").write(E["archivos"]["wifi.h"])
        open(os.path.join(d, "consola.h"), "w").write(
            "#include <stdint.h>\nvoid kputc(char);\nvoid kprint(const char*);\nvoid kprint_dec(uint32_t);\nvoid kprint_hex(uint32_t);\n")
        open(os.path.join(d, "sim.c"), "w").write(SIM)
        prog = os.path.join(d, "sim")
        c = subprocess.run([gcc, "-DWIFI_SIMULADA", "-Wall", "-Werror", "-O1", "-o", prog,
                            os.path.join(d, "sim.c"), os.path.join(d, "wifi.c")], capture_output=True, text=True)
        ok(c.returncode == 0, "wifi.c compila sin avisos con el chip simulado " + c.stderr[:300])
        def corre(m):
            r = subprocess.run([prog, str(m)], capture_output=True, text=True, timeout=60)
            return r.stdout
        if c.returncode == 0:
            s = corre(0)
            print(s)
            ok("version 0x180 revision 2 (AR9287)" in s, "lee la versión del chip: AR9287")
            ok("MAC 00:26:5e:12:34:56" in s, "lee la MAC de la EEPROM en su orden")
            ok("magia 0xa55a (correcta)" in s and "largo 720 bytes, version 14.3" in s, "magia, largo y versión")
            ok("suma de control correcta" in s, "comprueba la suma de control (XOR = 0xFFFF)")
            ok("region 0x0037 (ETSI (Europa))" in s, "la región")
            ok("recibir 2, para emitir 2, banda 2,4 GHz\n" in s, "antenas y banda")
            ok("WIFI W1 OK" in s and "ESCRITURAS_EEPROM=0" in s, "W1 OK sin escribir NADA en la EEPROM")
            s = corre(1)
            ok("WIFI W1 OK" in s and "ESCRITURAS_EEPROM=0" in s, "chip apagado del todo: lo enciende como Linux y lee")
            s = corre(2)
            ok("MAC 00:26:5e:12:34:56" in s and "suma de control correcta" in s, "EEPROM con los bytes girados")
            s = corre(3)
            ok("no he podido leer su EEPROM" in s and "BUCLE_INFINITO" not in s, "EEPROM muda: lo dice y no se cuelga")
            s = corre(4)
            ok("WIFI W1: sin tarjeta" in s, "sin tarjeta (QEMU): lo dice")
            s = corre(5)
            ok("el chip no despierta" in s and "BUCLE_INFINITO" not in s and "ESCRITURAS_EEPROM=0" in s,
               "chip que no despierta: para y no toca nada más")

print("\n" + ("TODO BIEN" if not FALLOS else f"{len(FALLOS)} FALLOS"))
sys.exit(1 if FALLOS else 0)
