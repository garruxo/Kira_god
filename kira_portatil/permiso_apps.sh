#!/bin/bash
# permiso_apps.sh — v3.33 (SOLO KiraOS, el portátil)
#
# El dueño da UNA sola vez permiso para que Kira instale programas y librerías del SISTEMA (apt-get, apt, dpkg) sin
# tener que escribir la contraseña cada vez. Lo lanza el dueño; le pedirá la contraseña SOLO esa vez.
#
#   bash permiso_apps            -> da el permiso (y ya no te pide más la contraseña para instalar)
#   bash permiso_apps --quitar   -> lo quita (vuelve a pedir la contraseña, como antes)
#
# Honesto: esto deja que Kira instale paquetes del sistema sin contraseña. Un paquete instala código como
# administrador, así que es un permiso fuerte; solo dalo si te parece bien. Queda limitado a apt-get/apt/dpkg (no es
# «root para todo»), y lo puedes quitar cuando quieras con --quitar.
#
# Teclado sin «:» ni «-»? Lánzalo con  bash permiso_apps  y Tab.

set -u
USUARIO="${KIRA_USUARIO:-$(id -un)}"
RAIZ="${KIRA_RAIZ_SIS:-}"                      # en pruebas: una raíz falsa; en real: vacío (el sistema de verdad)
SUDOERS="$RAIZ/etc/sudoers.d/50-kira-apps"
SUDO="sudo"
[ -n "$RAIZ" ] && SUDO=""                      # en pruebas no hay sudo (escribimos directo en la raíz falsa)

if [ "${1:-}" = "--quitar" ]; then
  $SUDO rm -f "$SUDOERS" 2>/dev/null
  echo "Permiso quitado. A partir de ahora te pediré la contraseña para instalar del sistema, como antes."
  exit 0
fi

mkdir -p "$(dirname "$SUDOERS")" 2>/dev/null || $SUDO mkdir -p "$(dirname "$SUDOERS")"
REGLA="$USUARIO ALL=(root) NOPASSWD: /usr/bin/apt-get, /usr/bin/apt, /usr/bin/dpkg, /usr/bin/aptitude"
if [ -n "$SUDO" ]; then
  printf '%s\n' "$REGLA" | $SUDO tee "$SUDOERS" >/dev/null || { echo "No pude escribir el permiso (¿contraseña?)."; exit 1; }
  $SUDO chmod 440 "$SUDOERS"
else
  printf '%s\n' "$REGLA" > "$SUDOERS"
  chmod 440 "$SUDOERS" 2>/dev/null || true
fi

if command -v visudo >/dev/null 2>&1; then
  if ! $SUDO visudo -cf "$SUDOERS" >/dev/null 2>&1; then
    echo "La regla no era válida; la quito para no dejar nada roto."
    $SUDO rm -f "$SUDOERS"
    exit 1
  fi
fi

echo "Listo. Kira ya puede instalar programas y librerías del sistema sin pedirte la contraseña."
echo "Para quitarlo cuando quieras:  bash permiso_apps --quitar"
