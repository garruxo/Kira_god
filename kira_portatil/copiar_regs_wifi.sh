#!/bin/bash
# copiar_regs_wifi.sh — copia los registros de la WiFi Atheros (AR9287) MIENTRAS LINUX LA TIENE FUNCIONANDO,
# para que el kernel de Kira (etapa 17, orden «compara») vea en qué ajuste se diferencia su driver del de Linux.
#
# Solo LEE: usa el modo de depuración del driver ath9k de Linux (regdump, y regidx/regval para los registros
# analógicos que regdump se salta). No cambia ningún ajuste de la tarjeta ni de Linux.
# Pide tu contraseña UNA vez (leer la depuración del driver es solo para el administrador).
#
#   cd kira_god/kira_portatil
#   bash copiar_regs_wifi
#
# Deja en ~/kira_portatil/kernel/:
#   regs_linux.txt           lo que lee el kernel de Kira (canal + registros de la radio)
#   regs_linux_completo.txt  todo lo que da Linux (para Claude)
#   regs_linux_ruido.txt     la calibración del ruido de Linux (si la da)
set -u

if [ "$(id -u)" = 0 ] && [ -z "${KIRA_PRUEBA:-}" ]; then
    echo "No lo lances con sudo: lanzalo normal (bash copiar_regs_wifi) y ya te pedira la contrasena."
    exit 1
fi

DEST="${KIRA_KERNEL:-$HOME/kira_portatil/kernel}"
DBG="${KIRA_DEBUGFS:-/sys/kernel/debug}"
SUDO="${KIRA_SUDO-sudo}"
IW="${KIRA_IW:-iw}"
NMCLI="${KIRA_NMCLI:-nmcli}"
mkdir -p "$DEST" || exit 1

# ---- en qué canal está la WiFi de Linux ahora mismo ----
canal=""; ancho="20"
if command -v "$IW" >/dev/null 2>&1; then
    info="$("$IW" dev 2>/dev/null)"
    canal="$(printf '%s\n' "$info" | sed -n 's/.*channel \([0-9][0-9]*\) .*/\1/p' | head -n 1)"
    a="$(printf '%s\n' "$info" | sed -n 's/.*width: \([0-9][0-9]*\) MHz.*/\1/p' | head -n 1)"
    [ -n "$a" ] && ancho="$a"
fi
if [ -z "$canal" ] && command -v "$NMCLI" >/dev/null 2>&1; then
    canal="$("$NMCLI" -t -f IN-USE,CHAN dev wifi 2>/dev/null | sed -n 's/^\*:\([0-9][0-9]*\)$/\1/p' | head -n 1)"
fi
if [ -z "$canal" ]; then
    echo "La WiFi de Linux no esta conectada ahora mismo (no se en que canal esta)."
    echo "Conectate a tu WiFi en Xubuntu y vuelve a lanzarlo."
    exit 1
fi
if [ "$canal" -gt 13 ] 2>/dev/null; then
    echo "Tu WiFi esta en el canal $canal (5 GHz): la AR9287 solo va en 2,4 GHz. Algo no cuadra."
    exit 1
fi

echo "La WiFi de Linux esta en el canal $canal (ancho $ancho MHz). Copio sus registros (te pedira la contrasena)..."

TMP="$(mktemp)"
trap 'rm -f "$TMP" "$TMP.r"' EXIT

# ---- lo que hace falta como administrador: solo LEER la depuración del driver ----
$SUDO bash -c '
    DBG="$1"
    if [ ! -d "$DBG/ieee80211" ]; then mount -t debugfs none "$DBG" 2>/dev/null; fi
    if [ ! -d "$DBG/ieee80211" ]; then echo "#SIN_DEBUGFS"; exit 0; fi
    d=""
    for x in "$DBG"/ieee80211/phy*/ath9k; do
        if [ -r "$x/regdump" ]; then d="$x"; break; fi
    done
    if [ -z "$d" ]; then echo "#SIN_ATH9K"; exit 0; fi
    echo "#REGDUMP"
    cat "$d/regdump"
    if [ -w "$d/regidx" ] && [ -r "$d/regval" ]; then
        echo "#ANALOGICOS"
        i=$((0x7800))
        while [ $i -lt $((0x7900)) ]; do
            printf "0x%x" $i > "$d/regidx"
            printf "0x%06x %s\n" $i "$(cat "$d/regval")"
            i=$((i + 4))
        done
    fi
    if [ -r "$d/dump_nfcal" ]; then echo "#RUIDO"; cat "$d/dump_nfcal"; fi
' _ "$DBG" > "$TMP"

if grep -q "^#SIN_DEBUGFS" "$TMP"; then
    echo "No he podido abrir la depuracion del kernel de Linux (debugfs). Hazme una foto de esto."
    exit 1
fi
if grep -q "^#SIN_ATH9K" "$TMP" || ! grep -q "^#REGDUMP" "$TMP"; then
    echo "El driver ath9k de tu Linux no tiene el modo de depuracion (regdump), o la WiFi no es la Atheros."
    if [ -r "/boot/config-$(uname -r)" ]; then
        grep -E "CONFIG_ATH9K_DEBUGFS|CONFIG_ATH_DEBUG" "/boot/config-$(uname -r)" || true
    fi
    echo "Hazme una foto de esto y buscamos otra forma."
    exit 1
fi

cp "$TMP" "$DEST/regs_linux_completo.txt"
sed -n '/^#RUIDO/,$p' "$TMP" | sed '1d' > "$DEST/regs_linux_ruido.txt"
[ -s "$DEST/regs_linux_ruido.txt" ] || rm -f "$DEST/regs_linux_ruido.txt"

# ---- lo que lee el kernel de Kira: el canal y SOLO los registros de la radio (pequeño) ----
{
    echo "# canal $canal ancho $ancho"
    echo "# copiado por copiar_regs_wifi.sh el $(date '+%Y-%m-%d %H:%M')"
    sed '/^#RUIDO/,$d' "$TMP" | while read -r dir val _; do
        case "$dir" in 0x*) ;; *) continue ;; esac
        case "$val" in 0x*) ;; *) continue ;; esac
        n=$((dir))
        if { [ $n -ge $((0x7800)) ] && [ $n -lt $((0x7900)) ]; } || \
           { [ $n -ge $((0x9800)) ] && [ $n -lt $((0xB500)) ]; }; then
            echo "$dir $val"
        fi
    done
} > "$TMP.r"
cuantos=$(grep -c "^0x" "$TMP.r")
cp "$TMP.r" "$DEST/regs_linux.txt"

echo "Listo: $cuantos registros de la radio guardados en $DEST/regs_linux.txt"
echo "Ahora: arranca el USB del kernel (etapa 17) y escribe:  compara"
echo "(y compara 2, compara 3... para las demas paginas). Hazme una foto de cada pagina."
