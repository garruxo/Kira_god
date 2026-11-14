"""v3.49: etapa 17 del kernel — WiFi W2: encender la radio de la AR9287 SOLO PARA ESCUCHAR y listar las redes.
QEMU no imita esta tarjeta, así que radio.c y wifi.c se compilan DE VERDAD (gcc) contra un chip simulado: reinicio
del RTC, calibración, el canal en AR_PHY_SYNTH_CONTROL y una recepción por DMA que escribe balizas (beacons) en los
descriptores ar5416 del anillo. Se comprueba que oye las redes (nombre, canal, señal, seguridad, red oculta), que
no se cuelga si el chip no se deja reiniciar o la calibración no acaba, y sobre todo que NUNCA transmite: ni cola
de envío, ni descriptor de envío, ni EEPROM, y con las respuestas automáticas (ACK/CTS) apagadas al escuchar."""
import os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import saber_so_kira as so
import wifi_tablas_kira as wt

FALLOS = []
def ok(c, m):
    print(("OK   " if c else "FALLA ") + m)
    if not c: FALLOS.append(m)

E = so.etapa(17)
ok(E and {"radio.c", "radio.h", "ar9287_tablas.h", "wifi.c", "wifi.h"} <= set(E["archivos"]), "etapa 17 con radio.c y las tablas")
RC = E["archivos"]["radio.c"]
K = E["archivos"]["kernel.c"]
ok("radio_probar" in K and 'shell_orden("redes"' in K and 'shell_orden("wifi"' in K, "la consola tiene «wifi» y «redes»")
ok(E["entrada"] == "redes\n" and "WIFI W2:" in E["espera"], "en QEMU escribe «redes» y espera «WIFI W2:»")
ok(so.etapa_para("escanea las redes wifi")["n"] == 17 and so.etapa_para("que lea la eeprom de la wifi atheros")["n"] == 16,
   "«escanea las redes wifi» → 17; «la eeprom de la wifi» → 16")
ok(so.etapa(16)["archivos"]["wifi.c"] == so._WIFI_C and "radio.c" not in so.etapa(16)["archivos"],
   "la etapa 16 (la que ya funcionó en tu portátil) no cambia")
# seguridad leyendo el código
ok("0x0840" not in RC and "AR_Q_TXE" not in RC.split("*/", 1)[1] and "TXDP" not in RC.split("*/", 1)[1],
   "radio.c no toca la cola de envío ni descriptores de envío")
ok("AR_DIAG_ACK_DIS | AR_DIAG_CTS_DIS" in RC, "apaga las respuestas automáticas (ACK y CTS)")
ok("wifi_dma(0)" in RC and "wifi_dma(1)" in RC, "permiso de DMA solo mientras escucha")
ok("0x180" in RC, "solo enciende la radio si es una AR9287")
ok("cargar_ruido()" in RC and "NF_NOMINAL_9287" in RC and "(-50)" in RC, "carga el ruido de fondo como Linux (loadnf: -112 y luego -50)")
# las tablas de Linux
regs = [int(a, 16) for a in re.findall(r"\{0x([0-9a-f]{8}), 0x", wt.AR9287_TABLAS_H)]
ok(len(regs) == 714 and "Atheros Communications" in wt.AR9287_TABLAS_H, "714 ajustes de Linux, con su aviso de licencia ISC")
vals = dict(re.findall(r"\{0x(0000084[0-9a-f]), 0x([0-9a-f]{8})\}", wt.AR9287_TABLAS_H))
ok("00000840" not in vals, "las tablas no encienden ninguna cola de envío (AR_Q_TXE)")
txdp = re.findall(r"\{0x(000008[0-3][0-9a-f]), 0x([0-9a-f]{8})\}", wt.AR9287_TABLAS_H)
ok(all(v == "00000000" for _, v in txdp), "lo que las tablas escriben en los punteros de envío es todo cero (los borran)")
ok(any("W3" in s for s in so.SIGUIENTES), "lo siguiente (W3, conectarse) apuntado")

SIM = r'''
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
extern uintptr_t radio_base_sim;
static uint32_t regs[0x10000 / 4];
static uint16_t eep[2048];
static int modo = 0;   /* 0 normal, 1 sin tarjeta, 2 otra version, 3 calibracion que no acaba, 4 RTC atascado */
static int rtc_on = 0, rxe = 0;
static uint32_t rxdp = 0, dato_eep = 0, ahora = 0, ultimo = 0;
static long lecturas = 0;
static int escritura_eeprom = 0, escritura_txe = 0, escritura_txdp = 0, rxe_sin_ack_dis = 0, veces_rxe = 0;
static uint32_t synth = 0;
int sim_buscar(uint16_t *a) { if (modo == 1) return 0; *a = 0x002e; return 1; }
static int canal_actual(void) {
    uint32_t sel = synth & 0x3FFFFFF;
    uint32_t freq = (uint32_t)(((uint64_t)sel * 15 + 32768) / 65536);
    return (int)((freq - 2407 + 2) / 5);
}
uint32_t sim_lee(uint32_t r) {
    if (++lecturas > 60000000L) { printf("BUCLE_INFINITO\n"); exit(3); }
    if (r >= 0x2000 && r < 0x3000) { dato_eep = eep[(r - 0x2000) >> 2]; return 0; }
    if (r == 0x407C) return dato_eep;
    if (r == 0x7044) return rtc_on ? 0x2 : 0x1;
    if (r == 0x4020) return modo == 2 ? ((0x0C0u << 12) | 0xFF) : ((0x180u << 12) | (2u << 8) | 0xFF);
    if (r == 0x7000) return modo == 4 ? 0x1 : 0;
    if (r == 0x9860) return modo == 3 ? regs[r / 4] : (regs[r / 4] & ~3u);   /* CAL y NF acaban */
    if (r == 0x0008) return rxe ? 4 : 0;
    if (r == 0x80F8) return 9680000;                       /* ciclos: el reloj de la radio va */
    return regs[r / 4];
}
void sim_escribe(uint32_t r, uint32_t v) {
    if (r >= 0x2000 && r < 0x3000) escritura_eeprom++;
    if (r == 0x0840 && v) escritura_txe++;
    if (r >= 0x0800 && r < 0x0840 && v) escritura_txdp++;
    if (r == 0x704C && (v & 1)) rtc_on = 1;
    if (r == 0x000C) rxdp = v;
    if (r == 0x9874) synth = v;
    if (r == 0x0008) {
        if (v & 0x20) rxe = 0;
        if (v & 0x4) {
            rxe = 1; veces_rxe++;
            if ((regs[0x8048 / 4] & 0x6) != 0x6) rxe_sin_ack_dis++;
        }
    }
    regs[r / 4] = v;
}
void kputc(char c) { putchar(c); }
void kprint(const char *s) { fputs(s, stdout); }
void kprint_dec(uint32_t n) { printf("%u", n); }
void kprint_hex(uint32_t n) { printf("0x%08X", n); }

struct ap { const char *ssid; int canal; int rssi; int seg; uint8_t mac; };
static const struct ap aps[] = {
    {"HUAWEI-2.4G-DGG", 6, 50, 3, 0x11},
    {"Vecino", 1, 20, 0, 0x22},
    {"", 11, 30, 3, 0x33},            /* red oculta */
    {"Viejo", 3, 15, 2, 0x44},        /* WPA (elemento del fabricante) */
    {"Casa WEP", 9, 10, 1, 0x55},
};

static void recibir(const uint8_t *f, int n, int rssi, int ok) {
    volatile uint32_t *d = (volatile uint32_t *)(radio_base_sim + rxdp);
    uint8_t *b = (uint8_t *)(radio_base_sim + d[1]);
    memcpy(b, f, (size_t)n);
    d[4 + 1] = (uint32_t)n;
    d[4 + 4] = (uint32_t)(uint8_t)rssi << 24;
    d[4 + 8] = ok ? 0x3 : 0x1 | 0x4;
    rxdp = d[0];
}

static int baliza(uint8_t *f, const struct ap *a, int canal_ds) {
    int n = 0;
    f[n++] = 0x80; f[n++] = 0;  f[n++] = 0; f[n++] = 0;
    for (int i = 0; i < 6; i++) f[n++] = 0xff;
    for (int k = 0; k < 2; k++) for (int i = 0; i < 6; i++) f[n++] = i == 5 ? a->mac : 0x02;
    f[n++] = 0; f[n++] = 0;
    for (int i = 0; i < 8; i++) f[n++] = 0;
    f[n++] = 0x64; f[n++] = 0;
    f[n++] = a->seg ? 0x11 : 0x01; f[n++] = 0;
    int l = (int)strlen(a->ssid);
    f[n++] = 0; f[n++] = (uint8_t)(l ? l : 8);
    if (l) { memcpy(f + n, a->ssid, (size_t)l); n += l; } else { memset(f + n, 0, 8); n += 8; }
    f[n++] = 1; f[n++] = 4; f[n++] = 0x82; f[n++] = 0x84; f[n++] = 0x8b; f[n++] = 0x96;
    f[n++] = 3; f[n++] = 1; f[n++] = (uint8_t)canal_ds;
    if (a->seg == 3) { uint8_t rsn[] = {48, 20, 1,0, 0,0x0f,0xac,4, 1,0, 0,0x0f,0xac,4, 1,0, 0,0x0f,0xac,2, 0,0};
                       memcpy(f + n, rsn, sizeof rsn); n += (int)sizeof rsn; }
    if (a->seg == 2) { uint8_t wpa[] = {221, 6, 0x00,0x50,0xf2,1, 1,0}; memcpy(f + n, wpa, sizeof wpa); n += (int)sizeof wpa; }
    for (int i = 0; i < 4; i++) f[n++] = 0;      /* FCS */
    return n;
}

void sim_paso(uint32_t us) {
    ahora += us;
    if (!rxe || (regs[0x8048 / 4] & 0x20) || ahora - ultimo < 20000) return;
    if ((regs[0x9864 / 4] & 0x1FF) == 0) return;           /* sin cargar el ruido, la radio real queda sorda */
    if (modo == 5) return;                                 /* chip sordo */
    if (modo == 6) {                                       /* oye, pero no entiende nada: solo errores de radio */
        ultimo = ahora;
        volatile uint32_t *d = (volatile uint32_t *)(radio_base_sim + rxdp);
        d[4 + 1] = 0; d[4 + 8] = 0x1 | 0x10 | (25u << 8);
        rxdp = d[0];
        return;
    }
    ultimo = ahora;
    int ch = canal_actual();
    uint8_t f[512];
    for (unsigned i = 0; i < sizeof aps / sizeof aps[0]; i++) {
        int dif = aps[i].canal - ch;
        if (dif < -1 || dif > 1) continue;                 /* se oye también en los canales de al lado */
        int n = baliza(f, &aps[i], aps[i].canal);
        recibir(f, n, aps[i].rssi - (dif ? 12 : 0), 1);
    }
    uint8_t datos[60] = {0x08, 0x01};                      /* una trama de datos: no es una baliza */
    recibir(datos, 60, 40, 1);
    recibir(datos, 60, 40, 0);                             /* y una con la suma mal */
}

#include "wifi.h"
#include "radio.h"
int main(int argc, char **argv) {
    modo = atoi(argv[1]);
    uint8_t *b = (uint8_t *)(eep + 128);
    int n = 360;
    eep[0] = 0xA55A;
    for (int i = 0; i < n; i++) eep[128 + i] = 0;
    eep[128] = (uint16_t)(n * 2);
    eep[130] = 0xE004;
    b[6] = 0x02; b[8] = 0x65;
    uint8_t mac[6] = {0x1c, 0x65, 0x9d, 0x53, 0xb0, 0x95};
    memcpy(b + 12, mac, 6);
    b[18] = 0x03; b[19] = 0x03;
    uint8_t *m = b + 96;                                   /* modalHeader */
    m[0] = 0x10; m[4] = 0x20; m[8] = 0x78; m[9] = 0x56; m[10] = 0x34; m[11] = 0x12;   /* antCtrlCommon 0x12345678 */
    m[14] = 0x2d; m[23] = 0x38;
    uint16_t x = 0;
    for (int i = 0; i < n; i++) x ^= eep[128 + i];
    eep[129] = x ^ 0xFFFF;
    int r = radio_escanear();
    printf("RESULTADO=%d\n", r);
    printf("SWITCH_COM=0x%08x\n", regs[0x9964 / 4]);
    printf("STA_ID0=0x%08x\n", regs[0x8000 / 4]);
    printf("RUIDO=0x%03x,0x%03x\n", regs[0x9864 / 4] & 0x1FF, regs[0xA864 / 4] & 0x1FF);
    printf("EEPROM=%d TXE=%d TXDP=%d SIN_ACK_DIS=%d VECES_RXE=%d RXE_AL_FINAL=%d DIAG_RX_DIS=%d\n", escritura_eeprom,
           escritura_txe, escritura_txdp, rxe_sin_ack_dis, veces_rxe, rxe, (regs[0x8048 / 4] & 0x20) ? 1 : 0);
    return 0;
}
'''

gcc = shutil.which("gcc")
ok(gcc is not None, "hay gcc para compilar el driver de verdad")
if gcc:
    with tempfile.TemporaryDirectory() as d:
        for nombre in ("wifi.c", "wifi.h", "radio.c", "radio.h", "ar9287_tablas.h"):
            open(os.path.join(d, nombre), "w").write(E["archivos"][nombre])
        open(os.path.join(d, "consola.h"), "w").write(
            "#include <stdint.h>\nvoid kputc(char);\nvoid kprint(const char*);\nvoid kprint_dec(uint32_t);\nvoid kprint_hex(uint32_t);\n")
        open(os.path.join(d, "sim.c"), "w").write(SIM)
        prog = os.path.join(d, "sim")
        c = subprocess.run([gcc, "-DWIFI_SIMULADA", "-Wall", "-Werror", "-O1", "-o", prog,
                            os.path.join(d, "sim.c"), os.path.join(d, "wifi.c"), os.path.join(d, "radio.c")],
                           capture_output=True, text=True)
        ok(c.returncode == 0, "radio.c + wifi.c compilan sin avisos con el chip simulado " + c.stderr[:400])
        def corre(m):
            return subprocess.run([prog, str(m)], capture_output=True, text=True, timeout=300).stdout
        if c.returncode == 0:
            s = corre(0)
            print(s)
            ok("WIFI W2 OK: 5 redes encontradas" in s, "oye las 5 redes (y no repite las que se cuelan en los canales de al lado)")
            lineas = [l for l in s.splitlines() if l.startswith("  canal")]
            ok(len(lineas) == 5 and "HUAWEI-2.4G-DGG" in lineas[0], "la más fuerte primero: tu HUAWEI")
            ok(re.search(r"canal 6\s+-45 dBm\s+WPA2\s+HUAWEI-2\.4G-DGG\s+\(02:02:02:02:02:11\)", s),
               "HUAWEI: canal 6, -45 dBm, WPA2 y su dirección")
            ok(re.search(r"canal 1\s+-75 dBm\s+abierta\s+Vecino", s), "red abierta en el canal 1")
            ok(re.search(r"canal 11\s+-65 dBm\s+WPA2\s+\(red oculta\)", s), "red oculta")
            ok(re.search(r"canal 3\s+-80 dBm\s+WPA\s+Viejo", s) and re.search(r"canal 9\s+-85 dBm\s+WEP\s+Casa WEP", s),
               "WPA (fabricante) y WEP")
            ok("canales calibrados 13 de 13" in s and "con errores" in s, "calibra los 13 canales y cuenta los errores")
            ok("WiFi diag:" in s and "RXDP" in s.split("WiFi diag:")[1].splitlines()[0], "línea de diagnóstico (contadores, ruido, ISR, DIAG, CR, RXDP)")
            ok("RUIDO=0x19c,0x19c" in s, "ruido cargado en las dos cadenas: -112 y después el tope -50, como Linux")
            ok("SWITCH_COM=0x12345678" in s, "pone los valores de antena de TU EEPROM (set_board_values)")
            ok("STA_ID0=0x539d651c" in s, "usa tu MAC de la EEPROM")
            ok("EEPROM=0 TXE=0 TXDP=0 SIN_ACK_DIS=0" in s, "NUNCA: escribir la EEPROM, cola de envío, descriptor de envío, ni escuchar con ACK/CTS encendidos")
            ok("VECES_RXE=13" in s and "RXE_AL_FINAL=0 DIAG_RX_DIS=1" in s, "escucha una vez por canal y al acabar deja la recepción parada")
            s = corre(5)
            ok("La radio esta sorda" in s and "recibiendo 0% del tiempo" in s and "RESULTADO=0" in s,
               "chip sordo: el diagnóstico lo dice (no nota nada en el aire)")
            s0 = corre(0)
            ok("RESULTADO=5" in s0 and re.search(r"errores: 0 de radio, \d+ con la suma mal", s0),
               "cuenta aparte los errores de radio y las tramas con la suma mal")
            s = corre(6)
            ok("todo con errores" in s and "codigos: 25x" in s and "RESULTADO=0" in s,
               "solo errores de radio: dice que SÍ llega a la memoria y qué códigos de error ve")
            s = corre(1)
            ok("WIFI W2: sin tarjeta" in s and "RESULTADO=-1" in s, "sin tarjeta (QEMU): lo dice y no enciende nada")
            s = corre(2)
            ok("no es una AR9287" in s and "VECES_RXE=0" in s, "otra versión del chip: no enciende la radio")
            s = corre(3)
            ok("canales calibrados 0 de 13" in s and "BUCLE_INFINITO" not in s, "calibración que no acaba: lo dice y sigue, sin colgarse")
            s = corre(4)
            ok("no se dejo reiniciar" in s and "BUCLE_INFINITO" not in s and "VECES_RXE=0" in s,
               "chip que no se deja reiniciar: para, sin colgarse ni escuchar")

# ---- v3.51: la cadena de PUENTES PCI (tu WiFi va en el bus 2, detrás de un puente del chipset) ----
W = E["archivos"]["wifi.c"]
ok("buscar_puente" in W and "pu_antes" in W, "wifi.c busca los puentes PCI de la cadena y guarda cómo estaban")
ok(re.search(r"#define AR9280_PHY_MINCCA|>> 20\) & 0x1FF", RC) is not None, "el ruido se lee en los bits 20-28 (AR9280_PHY_MINCCA_PWR)")
ok("0x100" in RC and "AR_RXCFG_ZLFDMA" in RC, "pide también los errores de radio (diagnóstico), sin dejar de solo escuchar")
PUENTE = r'''
#include <stdio.h>
#include <stdint.h>
struct pci_disp { uint8_t bus, disp, func; uint16_t vendedor, aparato; uint8_t clase, subclase, irq; uint32_t bar0; };
static uint32_t cfg[4][32][8][64];
static int escrituras_fuera = 0;
uint32_t pci_leer(uint8_t b, uint8_t d, uint8_t f, uint8_t o) { return b < 4 ? cfg[b][d][f][o / 4] : 0xFFFFFFFFu; }
void pci_escribir(uint8_t b, uint8_t d, uint8_t f, uint8_t o, uint32_t v) {
    if (o != 0x04) escrituras_fuera++;
    if (b < 4) cfg[b][d][f][o / 4] = v;
}
static struct pci_disp disp; static int hay_disp = 1;
CODIGO
int main(void) {
    for (int b = 0; b < 4; b++) for (int d = 0; d < 32; d++) for (int f = 0; f < 8; f++) cfg[b][d][f][0] = 0xFFFFFFFFu;
    cfg[0][0][0][0] = 0x00448086; cfg[0][0][0][3] = 0;                       /* el chipset */
    cfg[0][0x1c][0][0] = 0x3b428086; cfg[0][0x1c][0][3] = 0x00810000;        /* puente del bus 1 (multifunción) */
    cfg[0][0x1c][0][6] = 0x00010100; cfg[0][0x1c][0][1] = 0x00100006;
    cfg[0][0x1c][1][0] = 0x3b448086; cfg[0][0x1c][1][3] = 0x00010000;        /* puente del bus 2: SIN bus master */
    cfg[0][0x1c][1][6] = 0x00020200; cfg[0][0x1c][1][1] = 0x20100002;        /* (y un «master abort» viejo) */
    cfg[2][0][0][0] = 0x002e168c; cfg[2][0][0][3] = 0; cfg[2][0][0][1] = 0x20100002;
    disp.bus = 2; disp.disp = 0; disp.func = 0;
    wifi_dma(1);
    int on = 0, n = wifi_puentes(&on);
    printf("PUENTES=%d ENCENDIDOS=%d PUENTE=%08x TARJETA=%08x\n", n, on, cfg[0][0x1c][1][1], cfg[2][0][0][1]);
    cfg[2][0][0][1] |= 0x20000000u;                                          /* la tarjeta recibió un «no» */
    wifi_dma(0);
    printf("DESPUES PUENTE=%08x TARJETA=%08x ESTADO=%08x FUERA=%d\n", cfg[0][0x1c][1][1], cfg[2][0][0][1],
           wifi_estado_pci(), escrituras_fuera);
    return 0;
}
'''
if gcc:
    ini = W.index("#define MAX_PUENTES"); fin = W.index("uint32_t wifi_estado_pci(void)")
    fin = W.index("\n", fin) + 1
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "p.c"), "w").write(PUENTE.replace("CODIGO", W[ini:fin]))
        prog = os.path.join(d, "p")
        c = subprocess.run([gcc, "-Wall", "-Werror", "-Wno-unused-variable", "-O1", "-o", prog, os.path.join(d, "p.c")],
                           capture_output=True, text=True)
        ok(c.returncode == 0, "la búsqueda de puentes compila " + c.stderr[:300])
        if c.returncode == 0:
            s = subprocess.run([prog], capture_output=True, text=True, timeout=30).stdout
            print(s)
            ok("PUENTES=1 ENCENDIDOS=1" in s, "encuentra el puente del bus 2 (00:1c.1) y ve que NO tenía permiso de DMA")
            ok("PUENTE=20100006" in s or "PUENTE=00000006" in s or re.search(r"PUENTE=[0-9a-f]{4}0006 ", s),
               "le da memoria + bus master mientras escucha")
            ok("DESPUES PUENTE=00000002" in s, "al acabar el puente vuelve a quedar como estaba (sin bus master)")
            ok(re.search(r"TARJETA=[0-9a-f]{4}0002 ESTADO=2", s) is not None,
               "al acabar la tarjeta pierde el permiso y guarda el «rechazo» para el diagnóstico")
            ok("FUERA=0" in s, "solo toca el registro de órdenes (0x04), nada más de la configuración PCI")

print("\n" + ("TODO BIEN" if not FALLOS else f"{len(FALLOS)} FALLOS"))
sys.exit(1 if FALLOS else 0)
