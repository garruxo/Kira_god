#!/bin/bash
# estudiar_interruptor.sh — averigua CÓMO enciende Linux la radio WiFi de tu Packard Bell, para que el kernel de
# Kira pueda hacer lo mismo. El kernel de Kira vio (v3.60) que la tarjeta tiene la radio APAGADA por el
# interruptor del portátil (entrada GPIO 0 = 0), mientras que con Linux está ENCENDIDA (GPIO 0 = 1).
# En los Acer / Packard Bell ese interruptor lo maneja el controlador interno del portátil (el «EC») y Linux se
# lo pide con su módulo acer-wmi.
#
# Qué hace (SOLO MIRA, no cambia ningún ajuste guardado):
#   1. apunta el modelo del portátil, los interruptores de radio que ve Linux (rfkill) y los módulos cargados;
#   2. LEE la memoria del controlador del portátil (256 bytes, con el módulo ec_sys en modo SOLO LECTURA) y la
#      entrada GPIO de la tarjeta WiFi (con la depuración de ath9k: solo se escribe el ÍNDICE, nunca un valor);
#   3. si existe el interruptor «acer-wireless», APAGA la WiFi con él 3 segundos, vuelve a leer, y la ENCIENDE
#      otra vez (te quedarás sin internet esos segundos). Así se ve qué byte del controlador cambia.
# Pide tu contraseña UNA vez. Deja el informe en ~/kira_portatil/kernel/interruptor.txt
#
#   cd kira_god/kira_portatil
#   bash estudiar_interruptor
set -u

if [ "$(id -u)" = 0 ] && [ -z "${KIRA_PRUEBA:-}" ]; then
    echo "No lo lances con sudo: lanzalo normal (bash estudiar_interruptor) y ya te pedira la contrasena."
    exit 1
fi

DEST="${KIRA_KERNEL:-$HOME/kira_portatil/kernel}"
SUDO="${KIRA_SUDO-sudo}"
SYS="${KIRA_SYS:-/sys}"
DBG="${KIRA_DEBUGFS:-/sys/kernel/debug}"
ESPERA="${KIRA_ESPERA:-3}"
mkdir -p "$DEST" || exit 1
INF="$DEST/interruptor.txt"

echo "Miro como enciende Linux la radio WiFi (te pedira la contrasena una vez)."
echo "Si hay interruptor acer-wireless, la WiFi se apagara unos $ESPERA segundos y se volvera a encender."

INTERNO="$(mktemp)"
trap 'rm -f "$INTERNO"' EXIT
cat > "$INTERNO" <<'FIN_INTERNO'
SYS="$1"; DBG="$2"; ESPERA="$3"
echo "#MODELO"
for f in sys_vendor product_name product_version board_name bios_vendor bios_version bios_date; do
    printf '%s=%s\n' "$f" "$(cat "$SYS/class/dmi/id/$f" 2>/dev/null)"
done
echo "#MODULOS"
grep -E '^(acer|wmi|ath9k|ath|cfg80211|mac80211|rfkill|ec_sys|sparse_keymap|video)[_a-z0-9]* ' /proc/modules 2>/dev/null | cut -d' ' -f1
echo "#RFKILL"
for d in "$SYS"/class/rfkill/rfkill*; do
    [ -d "$d" ] || continue
    printf '%s nombre=%s tipo=%s duro=%s blando=%s\n' "$(basename "$d")" "$(cat "$d/name" 2>/dev/null)" \
        "$(cat "$d/type" 2>/dev/null)" "$(cat "$d/hard" 2>/dev/null)" "$(cat "$d/soft" 2>/dev/null)"
done
echo "#MENSAJES"
(dmesg 2>/dev/null || journalctl -k -b --no-pager 2>/dev/null) | grep -i -E 'acer|wmi|rfkill|ath9k|ec:' | tail -n 40

# memoria del controlador (EC), en SOLO LECTURA
[ -d "$DBG/ec" ] || mount -t debugfs none "$DBG" 2>/dev/null
if [ ! -e "$DBG/ec/ec0/io" ]; then modprobe ec_sys write_support=0 2>/dev/null; fi
EC="$DBG/ec/ec0/io"
ec() { if [ -r "$EC" ]; then od -An -tx1 -v "$EC" | tr -s ' \n' ' ' | sed 's/^ //'; echo; else echo "SIN_EC"; fi; }
# entrada GPIO de la tarjeta (0x4048) con la depuración de ath9k: se escribe solo el índice
gpio() {
    for p in "$DBG"/ieee80211/phy*/ath9k; do
        if [ -e "$p/regidx" ] && [ -e "$p/regval" ]; then
            printf '0x4048' > "$p/regidx" 2>/dev/null && cat "$p/regval" 2>/dev/null && return
        fi
    done
    echo "SIN_GPIO"
}
echo "#EC_ANTES"; ec
echo "#GPIO_ANTES"; gpio

# el interruptor de acer (si lo hay): apagar, leer, encender, leer
idx=""
for d in "$SYS"/class/rfkill/rfkill*; do
    [ -d "$d" ] || continue
    n="$(cat "$d/name" 2>/dev/null)"
    case "$n" in acer-wireless|acer*wireless*|*wireless*) [ "$(cat "$d/type" 2>/dev/null)" = wlan ] && idx="$d" ;; esac
done
if [ -n "$idx" ]; then
    echo "#INTERRUPTOR $(cat "$idx/name")"
    echo 0 > "$idx/state" 2>/dev/null || echo 1 > "$idx/soft" 2>/dev/null
    sleep "$ESPERA"
    echo "#EC_APAGADA"; ec
    echo "#GPIO_APAGADA"; gpio
    echo 1 > "$idx/state" 2>/dev/null || echo 0 > "$idx/soft" 2>/dev/null
    sleep "$ESPERA"
    echo "#EC_ENCENDIDA"; ec
    echo "#GPIO_ENCENDIDA"; gpio
else
    echo "#SIN_INTERRUPTOR_ACER"
fi
FIN_INTERNO

$SUDO bash "$INTERNO" "$SYS" "$DBG" "$ESPERA" > "$INF" 2>&1
chmod 600 "$INF" 2>/dev/null

# ---- resumen para ti (y para Claude) ----
seccion() { sed -n "/^#$1\$/,/^#/p" "$INF" | sed '1d;/^#/d'; }
echo
echo "Modelo: $(sed -n 's/^product_name=//p' "$INF" | head -n1)   BIOS: $(sed -n 's/^bios_version=//p' "$INF" | head -n1)"
echo "Interruptores de radio que ve Linux:"
seccion RFKILL | sed 's/^/  /'
echo "Modulos: $(seccion MODULOS | tr '\n' ' ')"
if grep -q '^#SIN_INTERRUPTOR_ACER' "$INF"; then
    echo "No hay interruptor acer-wireless: Linux enciende la radio de otra forma. Mandame foto de esto."
else
    a="$(seccion EC_ANTES)"; b="$(seccion EC_APAGADA)"; c="$(seccion EC_ENCENDIDA)"
    if [ "$a" = SIN_EC ] || [ -z "$a" ]; then
        echo "No he podido leer la memoria del controlador (falta el modulo ec_sys)."
    else
        echo "Bytes del controlador que cambian al apagar y encender la WiFi (posicion: encendida -> apagada -> encendida):"
        set -- $a; A=("$@"); set -- $b; B=("$@"); set -- $c; C=("$@")
        hay=0
        for i in $(seq 0 255); do
            if [ "${A[$i]:-}" != "${B[$i]:-}" ] && [ "${B[$i]:-}" != "${C[$i]:-}" ]; then
                printf '  0x%02X: %s -> %s -> %s\n' "$i" "${A[$i]}" "${B[$i]}" "${C[$i]}"; hay=1
            fi
        done
        [ $hay = 0 ] && echo "  ninguno (el controlador no guarda el estado en su memoria normal)"
    fi
    echo "Entrada GPIO de la tarjeta: antes $(seccion GPIO_ANTES), apagada $(seccion GPIO_APAGADA), encendida $(seccion GPIO_ENCENDIDA)"
fi
echo
echo "Guardado en $INF. Mandame una foto de esta pantalla."
