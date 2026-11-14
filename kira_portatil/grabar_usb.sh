#!/usr/bin/env bash
# grabar_usb.sh — v3.36: graba el kernel de Kira en un PENDRIVE USB para arrancarlo en el portátil de verdad.
# Lo lanzas TÚ (Kira nunca escribe en un disco):  cd kira_god/kira_portatil  y  bash grabar_usb
# Solo ofrece discos USB EXTRAÍBLES, se niega con el disco del sistema y pide que escribas SI antes de borrar nada.
# Para pruebas: KIRA_KERNEL (carpeta del kernel), KIRA_LSBLK_JSON (lsblk de mentira), KIRA_DD (orden de grabar),
# KIRA_MONTAJES (lsblk de puntos de montaje de mentira), KIRA_PRUEBA (deja correrlo como root en las pruebas).
set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"
BASE="${KIRA_KERNEL:-$HOME/kira_portatil/kernel}"
ISO="$BASE/kira_kernel.iso"

if [ "$(id -u)" = "0" ] && [ -z "${KIRA_PRUEBA:-}" ]; then
  echo "No me lances con sudo: te pediré la contraseña solo para grabar."; exit 1
fi
if [ ! -f "$ISO" ]; then
  echo "Aún no hay imagen del kernel. Dile a Kira «prepara el USB del kernel» y vuelve a lanzarme."; exit 1
fi

echo "== Grabar el kernel de Kira en un pendrive =="
echo "Imagen: $ISO ($(du -h "$ISO" | cut -f1))"
LISTA="$(python3 "$AQUI/taller_kernel_kira.py" --usbs)"
if [ -z "$LISTA" ]; then
  echo "No veo ningún pendrive USB conectado. Conéctalo y vuelve a lanzarme."; exit 1
fi
echo "Pendrives USB conectados:"
echo "$LISTA"
printf "Escribe el NÚMERO del pendrive (o Intro para salir): "
read -r NUM
[ -z "$NUM" ] && { echo "Vale, no grabo nada."; exit 0; }
LINEA="$(echo "$LISTA" | awk -v n="$NUM" '$1==n")"{print; exit}')"
DEV="$(echo "$LINEA" | awk '{print $2}')"
case "$DEV" in
  /dev/sd[a-z]|/dev/sd[a-z][a-z]) ;;
  *) echo "Ese número no está en la lista. No grabo nada."; exit 1 ;;
esac
# nunca el disco donde está el sistema o tus archivos
if [ -n "${KIRA_MONTAJES:-}" ]; then MONTA="$(cat "$KIRA_MONTAJES")"; else MONTA="$(lsblk -nro MOUNTPOINT "$DEV" 2>/dev/null)"; fi
if echo "$MONTA" | grep -qE '^/$|^/home|^/boot'; then
  echo "¡$DEV tiene el sistema o tus archivos! No lo toco."; exit 1
fi
echo ""
echo "Vas a BORRAR TODO lo que hay en: $LINEA"
printf "Escribe SI (en mayúsculas) para grabar: "
read -r CONF
if [ "$CONF" != "SI" ] && [ "$CONF" != "SÍ" ]; then echo "Vale, no grabo nada."; exit 0; fi
for p in $(ls "${DEV}"?* 2>/dev/null); do
  ${KIRA_UMOUNT:-sudo umount} "$p" 2>/dev/null || true
done
echo "Grabando (te pedirá TU contraseña)…"
if ${KIRA_DD:-sudo dd} if="$ISO" of="$DEV" bs=4M status=progress conv=fsync; then
  sync
  echo ""
  echo "Listo. Para arrancarlo: reinicia, pulsa F12 al encender, elige el USB y luego «Kernel de Kira»."
  echo "Con Esc se reinicia y vuelves a KiraOS. Si la pantalla se queda negra, en la BIOS (F2) pon el arranque en «Legacy»."
else
  echo "No se pudo grabar (¿contraseña mal o pendrive protegido?)."; exit 1
fi
