#!/bin/bash
# estudiar_acpi_wifi.sh — lee las instrucciones de la BIOS (tablas ACPI) para ver QUÉ hace Linux al encender la
# radio WiFi del Packard Bell. El kernel de Kira ya cambia el bit del controlador (EC 0xBB) como Linux, pero la
# radio no se enciende: el método de la BIOS que usa Linux (acer-wmi) hace algo más, y está escrito aquí.
#
# Qué hace (SOLO LEE, no cambia nada del portátil):
#   1. copia las tablas ACPI (DSDT y SSDT) de /sys/firmware/acpi/tables (pide la contraseña UNA vez);
#   2. las desmonta a texto con iasl (paquete acpica-tools; si no lo tienes, te pregunta si lo instala);
#   3. busca el campo del EC del byte 0xBB bit 0, los métodos que lo usan y quién los llama, y te los enseña.
# Deja el informe en ~/kira_portatil/kernel/acpi_wifi.txt y las tablas en ~/kira_portatil/kernel/acpi/
#
#   cd kira_god/kira_portatil
#   bash estudiar_acpi_wifi
set -u

if [ "$(id -u)" = 0 ] && [ -z "${KIRA_PRUEBA:-}" ]; then
    echo "No lo lances con sudo: lanzalo normal (bash estudiar_acpi_wifi) y ya te pedira la contrasena."
    exit 1
fi

AQUI="$(cd "$(dirname "$0")" && pwd)"
DEST="${KIRA_KERNEL:-$HOME/kira_portatil/kernel}"
SUDO="${KIRA_SUDO-sudo}"
TABLAS="${KIRA_ACPI:-/sys/firmware/acpi/tables}"
IASL="${KIRA_IASL:-iasl}"
mkdir -p "$DEST/acpi" || exit 1
chmod 700 "$DEST/acpi" 2>/dev/null
INF="$DEST/acpi_wifi.txt"

echo "Leo las instrucciones de la BIOS para la WiFi (solo leer; te pedira la contrasena una vez)."

if ! command -v "$IASL" >/dev/null 2>&1; then
    echo "Me falta el programa iasl (paquete acpica-tools) para pasar las tablas a texto."
    printf "Escribe SI para que lo instale ahora (pide la contrasena): "
    read -r resp
    if [ "$resp" = "SI" ] || [ "$resp" = "si" ] || [ "$resp" = "Si" ]; then
        $SUDO apt-get install -y acpica-tools || { echo "No he podido instalarlo."; exit 1; }
    else
        echo "Vale, no instalo nada. Sin iasl no puedo leer las tablas."
        exit 1
    fi
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
YO="$(id -un)"
# copiar las tablas (solo leer; hace falta la contrasena porque /sys/firmware/acpi/tables es solo de root)
$SUDO sh -c 'for f in "$1"/DSDT "$1"/SSDT*; do [ -f "$f" ] && cp "$f" "$2/$(basename "$f").dat"; done; chown -R "$3" "$2"' \
    _ "$TABLAS" "$TMP" "$YO" || { echo "No he podido leer las tablas ACPI."; exit 1; }
if [ ! -f "$TMP/DSDT.dat" ]; then
    echo "No encuentro la tabla DSDT en $TABLAS."
    exit 1
fi
N=$(ls "$TMP"/*.dat | wc -l)
echo "Tablas copiadas: $N. Las paso a texto..."
(
    cd "$TMP" || exit 1
    SSDT=$(ls SSDT*.dat 2>/dev/null | tr '\n' ',' | sed 's/,$//')
    if [ -n "$SSDT" ]; then "$IASL" -e $(echo "$SSDT" | tr ',' ' ') -d DSDT.dat >/dev/null 2>&1 || "$IASL" -d DSDT.dat >/dev/null 2>&1
    else "$IASL" -d DSDT.dat >/dev/null 2>&1; fi
    for f in SSDT*.dat; do [ -f "$f" ] && "$IASL" -d "$f" >/dev/null 2>&1; done
)
if [ ! -f "$TMP/DSDT.dsl" ]; then
    echo "iasl no ha podido pasar la tabla DSDT a texto."
    exit 1
fi
cp "$TMP"/*.dsl "$DEST/acpi/" 2>/dev/null
chmod 600 "$DEST"/acpi/*.dsl 2>/dev/null

KIRA_TODO=1 python3 "$AQUI/acpi_wifi_kira.py" "$TMP" > "$INF" 2>&1
chmod 600 "$INF" 2>/dev/null
echo
python3 "$AQUI/acpi_wifi_kira.py" "$TMP"
echo
echo "Guardado en $INF (y las tablas en $DEST/acpi). Mandame una foto de esta pantalla."
