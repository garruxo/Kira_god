#!/bin/bash
# modo_admin.sh — v3.93 (SOLO KiraOS): activa el MODO ADMINISTRADOR de Kira, con TU contraseña.
#
# Después de esto, cuando le pidas a Kira algo de administrador («ejecuta como administrador apt update», «instala vlc
# como administrador»), Xubuntu te enseña una ventana con la orden EXACTA y te pide TU contraseña; la recuerda unos
# minutos. Sin tu contraseña, Kira no puede hacer nada de administrador.
#
#   bash modo_admin            -> lo activa (te pide la contraseña esta vez, para instalarlo)
#   bash modo_admin --quitar   -> lo quita
#
# Lo que instala: el ayudante /usr/local/bin/kira-admin (de root) y la regla de polkit
# /usr/share/polkit-1/actions/org.kira.admin.policy. No es «sudo sin contraseña»: siempre pregunta.
set -u
if [ "$(id -u)" -eq 0 ] && [ -z "${KIRA_RAIZ_SIS:-}" ]; then
  echo "Lánzalo SIN sudo delante:  bash modo_admin   (te pediré la contraseña yo)."; exit 1
fi
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="${KIRA_RAIZ_SIS:-}"
SUDO="sudo"; [ -n "$RAIZ" ] && SUDO=""
AYU="$RAIZ/usr/local/bin/kira-admin"
POL="$RAIZ/usr/share/polkit-1/actions/org.kira.admin.policy"

if [ "${1:-}" = "--quitar" ]; then
  $SUDO rm -f "$AYU" "$POL"
  echo "Modo administrador quitado. Kira ya no puede pedirte la contraseña para hacer cosas de administrador."
  exit 0
fi

$SUDO mkdir -p "$(dirname "$AYU")" "$(dirname "$POL")" || { echo "No pude crear las carpetas (¿contraseña?)."; exit 1; }
$SUDO install -m 0755 "$AQUI/kira_admin.sh" "$AYU" || { echo "No pude instalar el ayudante (¿contraseña?)."; exit 1; }
$SUDO install -m 0644 "$AQUI/org.kira.admin.policy" "$POL" || { echo "No pude instalar la regla de polkit."; exit 1; }
if [ -z "$RAIZ" ]; then
  $SUDO chown root:root "$AYU" "$POL" 2>/dev/null
  # el «agente» que enseña la ventana de la contraseña (en la sesión de Kira hay que lanzarlo; ver kiraos_sesion.sh)
  if ! ls /usr/lib/policykit-1-gnome/polkit-gnome-authentication-agent-1 /usr/libexec/polkit-gnome-authentication-agent-1 \
       /usr/bin/xfce-polkit /usr/libexec/xfce-polkit /usr/bin/lxpolkit /usr/lib/x86_64-linux-gnu/polkit-mate/polkit-mate-authentication-agent-1 \
       >/dev/null 2>&1; then
    echo "Instalando el agente que enseña la ventana de la contraseña…"
    $SUDO apt-get install -y policykit-1-gnome >/dev/null 2>&1 || $SUDO apt-get install -y lxpolkit >/dev/null 2>&1 || \
      echo "(No pude instalar el agente: la ventana podría no salir en la sesión de Kira; en Xubuntu sí sale.)"
  fi
fi
echo "Listo: modo administrador activado."
echo "Ahora, cuando me pidas algo de administrador, Xubuntu te enseñará la orden y te pedirá tu contraseña (la recuerda unos minutos)."
echo "Para quitarlo:  bash modo_admin --quitar"
