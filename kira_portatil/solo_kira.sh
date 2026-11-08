#!/usr/bin/env bash
# solo_kira.sh — v3.05: al encender el portátil, SOLO Kira: sin el logo de Xubuntu al arrancar y sin ver su escritorio.
# Uso:  cd kira_god/kira_portatil   y   bash solo + Tab          (bash solo_kira.sh)
#       bash solo_kira.sh --deshacer     (vuelve a como estaba: logo de Xubuntu y su escritorio con Kira encima)
#
# Qué hace:
#   1) la pantalla de ARRANQUE (mientras Linux se carga) pasa a ser el orbe de Kira en vez del logo de Xubuntu;
#   2) crea la sesión «KiraOS» (kiraos-sesion): entra directo en Kira, sin cargar el escritorio de Xubuntu;
#   3) la entrada automática abre esa sesión (no la de Xubuntu);
#   4) Xubuntu sigue ahí: menú K ▸ «Ir a Xubuntu» (o Alt+F4) te lleva a su escritorio de siempre.
# Para las pruebas: KIRA_RAIZ_SIS (carpeta que hace de «/»), KIRA_USUARIO.
set -uo pipefail
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
R="${KIRA_RAIZ_SIS:-}"
U="${KIRA_USUARIO:-${SUDO_USER:-${USER:-$(id -un)}}}"
SUDO=""
[ "$(id -u)" -ne 0 ] && [ -z "$R" ] && SUDO="sudo"
if [ -z "$U" ] || [ "$U" = "root" ]; then
  echo "[x] Lánzalo con tu usuario, no como root:  bash solo_kira.sh"
  exit 1
fi
CASA="$(getent passwd "$U" 2>/dev/null | cut -d: -f6)"
[ -n "$R" ] || [ -z "$CASA" ] && CASA="${HOME}"
AUTO="$CASA/.config/autostart/kira-arranque.desktop"
TEMAS="$R/usr/share/plymouth/themes"

sistema() {   # las órdenes que tocan el arranque de verdad; en pruebas solo se dicen
  if [ -n "$R" ]; then echo "(prueba) haría: $*"; else $SUDO "$@"; fi
}

autostart() {   # $1 = «guarda» (no abrir Kira si vienes de la sesión de Kira) | «normal»
  mkdir -p "$(dirname "$AUTO")"
  if [ "$1" = "guarda" ]; then
    EXEC="sh -c 'test -n \"\$KIRA_DESDE_KIRA\" || exec /usr/local/bin/kiraos'"
  else
    EXEC="/usr/local/bin/kiraos"
  fi
  cat > "$AUTO" <<AUTOF
[Desktop Entry]
Type=Application
Name=KiraOS
Comment=Arranca Kira a pantalla completa al encender
Exec=$EXEC
X-GNOME-Autostart-enabled=true
Terminal=false
AUTOF
}

if [ "${1:-}" = "--deshacer" ]; then
  echo "== Vuelvo a como estaba"
  KIRA_SESION=xubuntu KIRA_RAIZ_SIS="$R" KIRA_USUARIO="$U" bash "$AQUI/arreglar_inicio.sh" >/dev/null || true
  autostart normal
  if [ -f "$TEMAS/kira/kira.plymouth" ]; then
    sistema update-alternatives --remove default.plymouth /usr/share/plymouth/themes/kira/kira.plymouth
    sistema update-initramfs -u
  fi
  echo "[OK] Al reiniciar: logo de Xubuntu, su escritorio y Kira encima, como antes."
  exit 0
fi

echo "== 1. La pantalla de arranque: el orbe de Kira (en vez del logo de Xubuntu)"
if [ -n "$R" ] || command -v plymouth >/dev/null 2>&1 || [ -d "$TEMAS" ]; then
  if [ -z "$R" ] && command -v apt-get >/dev/null 2>&1; then
    $SUDO apt-get install -y plymouth-label >/dev/null 2>&1 || true      # para la palabra «KIRA» encima del orbe
  fi
  TMP="$(mktemp -d)"
  python3 "$AQUI/logo_arranque_kira.py" "$TMP" >/dev/null
  $SUDO mkdir -p "$TEMAS/kira"
  $SUDO cp "$TMP/orbe.png" "$TMP/kira.script" "$TMP/kira.plymouth" "$TEMAS/kira/"
  rm -rf "$TMP"
  sistema update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth \
    /usr/share/plymouth/themes/kira/kira.plymouth 300
  sistema update-alternatives --set default.plymouth /usr/share/plymouth/themes/kira/kira.plymouth
  # que se vea la pantalla de arranque (y no letras): «quiet splash» en el arranque
  G="$R/etc/default/grub"
  if [ -f "$G" ] && ! grep -Eq '^GRUB_CMDLINE_LINUX_DEFAULT=.*splash' "$G"; then
    [ -f "$G.kira-copia" ] || $SUDO cp -p "$G" "$G.kira-copia"
    $SUDO sed -i -E 's/^GRUB_CMDLINE_LINUX_DEFAULT="(.*)"/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash \1"/' "$G"
    sistema update-grub
  fi
  echo "   (esto tarda un poco: rehace el arranque)"
  sistema update-initramfs -u
else
  echo "   (este sistema no tiene pantalla de arranque gráfica; me lo salto)"
fi

echo "== 2. La sesión de Kira (sin el escritorio de Xubuntu)"
$SUDO mkdir -p "$R/usr/local/bin" "$R/usr/share/xsessions"
$SUDO cp "$AQUI/kiraos_sesion.sh" "$R/usr/local/bin/kiraos-sesion"
$SUDO chmod 755 "$R/usr/local/bin/kiraos-sesion"
$SUDO tee "$R/usr/share/xsessions/kiraos.desktop" >/dev/null <<SES
[Desktop Entry]
Name=KiraOS
Comment=Kira a pantalla completa, sin el escritorio de Xubuntu
Exec=/usr/local/bin/kiraos-sesion
Type=Application
DesktopNames=KiraOS
SES

echo "== 3. Al encender, entrar directo en la sesión de Kira"
KIRA_SESION=kiraos KIRA_RAIZ_SIS="$R" KIRA_USUARIO="$U" bash "$AQUI/arreglar_inicio.sh" | grep -v "^Cómo queda\|autologin" || true

echo "== 4. Que Xubuntu no vuelva a abrir Kira él solo cuando vayas a su escritorio"
autostart guarda

echo
echo "[OK] Listo. Reinicia:  sudo reboot"
echo "     Verás el orbe de Kira al arrancar y luego Kira, sin el escritorio de Xubuntu."
echo "     Para ir a Xubuntu: menú K ▸ «Ir a Xubuntu». Para deshacerlo todo: bash solo_kira.sh --deshacer"
