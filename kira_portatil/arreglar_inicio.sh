#!/usr/bin/env bash
# arreglar_inicio.sh — v2.99: que al encender el portátil se entre DIRECTO (sin la pantalla de contraseña de Xubuntu)
# y arranque KiraOS. Lo usa el instalador y se puede lanzar a mano:   bash kira_portatil/arreglar_inicio.sh
#
# Por qué hacía falta (visto en el Packard Bell): el instalador dejaba la entrada automática en un archivo aparte de
# LightDM, pero (1) el archivo PRINCIPAL /etc/lightdm/lightdm.conf se lee el ÚLTIMO y, si el instalador de Xubuntu dejó
# ahí «autologin-user=» vacío, lo anula; (2) no decía qué sesión abrir («xubuntu») y en algunos equipos así no entra;
# (3) en algunos sistemas hace falta estar en el grupo «autologin». Este guion arregla las tres cosas, guarda una copia
# de lo que toca (*.kira-copia) y enseña cómo queda.
#
# Para las pruebas: KIRA_RAIZ_SIS (carpeta que hace de «/»), KIRA_USUARIO.
set -uo pipefail

R="${KIRA_RAIZ_SIS:-}"
U="${KIRA_USUARIO:-${SUDO_USER:-${USER:-$(id -un)}}}"
SUDO=""
[ "$(id -u)" -ne 0 ] && [ -z "$R" ] && SUDO="sudo"

if [ -z "$U" ] || [ "$U" = "root" ]; then
  echo "[x] No sé qué usuario eres (no lo lances como root; lánzalo con tu usuario: bash kira_portatil/arreglar_inicio.sh)"
  exit 1
fi

LDM="$R/etc/lightdm"
GDM="$R/etc/gdm3"

# ---------------- LightDM (Xubuntu, Lubuntu…) ----------------
if [ -d "$LDM" ]; then
  # la sesión que hay que abrir
  SES="${KIRA_SESION:-}"                       # v3.05: «kiraos» = la sesión propia de Kira (sin escritorio)
  [ -n "$SES" ] && [ ! -f "$R/usr/share/xsessions/$SES.desktop" ] && SES=""
  for s in xubuntu xfce lubuntu LXQt; do
    [ -n "$SES" ] && break
    if [ -f "$R/usr/share/xsessions/$s.desktop" ]; then SES="$s"; break; fi
  done
  if [ -z "$SES" ]; then
    SES="$(ls "$R/usr/share/xsessions" 2>/dev/null | sed -n 's/\.desktop$//p' | head -n 1)"
  fi
  echo "Usuario: $U · sesión: ${SES:-(no la encuentro)}"

  # 1) el grupo «autologin» (algunos sistemas lo exigen; no hace daño)
  if ! getent group autologin >/dev/null 2>&1; then
    $SUDO groupadd -r autologin >/dev/null 2>&1 || true
  fi
  $SUDO gpasswd -a "$U" autologin >/dev/null 2>&1 || true

  # 2) nuestro archivo de entrada automática
  contenido="# Kira: entrar directo en la sesión al encender (PIN opcional: kiraos --poner-pin)."$'\n'
  contenido+="[Seat:*]"$'\n'"autologin-user=$U"$'\n'"autologin-user-timeout=0"$'\n'
  [ -n "$SES" ] && contenido+="autologin-session=$SES"$'\n'
  $SUDO mkdir -p "$LDM/lightdm.conf.d"
  printf '%s' "$contenido" | $SUDO tee "$LDM/lightdm.conf.d/50-kira.conf" >/dev/null

  # 3) lo que se lee DESPUÉS y lo anularía: el archivo principal y los de lightdm.conf.d que van detrás del nuestro
  for f in "$LDM/lightdm.conf" "$LDM"/lightdm.conf.d/*.conf; do
    [ -f "$f" ] || continue
    [ "$(basename "$f")" = "50-kira.conf" ] && continue
    if [ "$f" != "$LDM/lightdm.conf" ] && [[ "$(basename "$f")" < "50-kira.conf" ]]; then
      continue                                   # los que van ANTES del nuestro no mandan
    fi
    if grep -Eq '^[[:space:]]*autologin-(user|session)[[:space:]]*=' "$f"; then
      [ -f "$f.kira-copia" ] || $SUDO cp -p "$f" "$f.kira-copia"
      $SUDO sed -i -E 's/^([[:space:]]*autologin-(user|session)[[:space:]]*=.*)$/# (Kira) \1/' "$f"
      echo "Arreglado: $f tenía su propia entrada automática y anulaba la de Kira (copia en $f.kira-copia)."
    fi
  done

  # 4) cómo queda de verdad (LightDM lo junta todo)
  if [ -z "$R" ] && command -v lightdm >/dev/null 2>&1; then
    echo "Cómo queda:"
    lightdm --show-config 2>/dev/null | grep -i autologin || echo "  (no he podido leerlo, pero ya está escrito)"
  fi
  echo "[OK] Listo. Reinicia para probarlo:  sudo reboot"
  exit 0
fi

# ---------------- GDM (Ubuntu normal) ----------------
if [ -d "$GDM" ]; then
  $SUDO tee "$GDM/custom.conf" >/dev/null <<GDMCONF
# Kira: entrar directo en la sesión al encender (PIN opcional: kiraos --poner-pin).
[daemon]
AutomaticLoginEnable=true
AutomaticLogin=$U
GDMCONF
  echo "[OK] Listo (GDM). Reinicia para probarlo:  sudo reboot"
  exit 0
fi

echo "[x] No reconozco la pantalla de entrada de este sistema (ni LightDM ni GDM)."
exit 1
