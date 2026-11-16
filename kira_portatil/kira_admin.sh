#!/bin/bash
# kira_admin.sh — v3.93: el AYUDANTE de administrador de Kira. Se instala (por modo_admin.sh) en
# /usr/local/bin/kira-admin, propiedad de root. Solo se ejecuta con pkexec, DESPUÉS de que escribas tu contraseña en
# la ventana de Xubuntu (que enseña la orden exacta). Vuelve a comprobar lo prohibido (por si acaso) y lo apunta en
# /var/log/kira-admin.log. Argumentos en lista, sin shell.
set -u
LOG="${KIRA_ADMIN_SIS_LOG:-/var/log/kira-admin.log}"
if [ -z "${KIRA_ADMIN_PRUEBA:-}" ] && [ "$(id -u)" -ne 0 ]; then
  echo "kira-admin: esto solo se usa con pkexec (Xubuntu te pide la contraseña)."; exit 1
fi
[ $# -ge 1 ] || { echo "kira-admin: falta la orden"; exit 2; }
prog="$1"; shift
b="$(basename "$prog")"
case "$b" in
  bash|sh|dash|zsh|fish|ksh|csh|tcsh|su|sudo|pkexec|doas|env|xargs|nohup|setsid|nice|ionice|chroot|script|busybox|\
  python*|perl*|ruby*|node|nodejs|php*|lua*|tclsh|expect|screen|tmux|find|awk|gawk|mawk|sed|vim|vi|nano|less|more|man|\
  watch|timeout)
    echo "kira-admin: «$b» no lo ejecuto como administrador"; exit 3;;
  dd|mkfs|mkfs.*|wipefs|fdisk|sfdisk|cfdisk|parted|gparted|gdisk|sgdisk|cgdisk|shred|blkdiscard|mkswap|badblocks|\
  hdparm|sdparm|cryptsetup|mke2fs|tune2fs|e2fsck|fsck|fsck.*|losetup|mdadm|pvcreate|vgcreate|lvcreate|lvremove|\
  vgremove|pvremove|dmsetup|zpool|zfs|btrfs|nvme|flashrom|efibootmgr|grub-install)
    echo "kira-admin: «$b» toca discos y eso no lo hago"; exit 3;;
  passwd|chpasswd|userdel|deluser|usermod|chage|vipw|vigr|visudo)
    echo "kira-admin: «$b» toca contraseñas o cuentas y eso no lo hago"; exit 3;;
esac
for a in "$@"; do
  case "$a" in *';'*|*'&'*|*'|'*|*'`'*|*'$('*) echo "kira-admin: argumento raro"; exit 3;; esac
done
if [ "$b" = "rm" ]; then
  for a in "$@"; do
    case "$a" in /|/etc|/usr|/home|/boot|/bin|/sbin|/lib|/lib32|/lib64|/var|/opt|/root|/srv|/proc|/sys|/dev|/run|\
      /etc/|/usr/|/home/|/boot/|/var/|--no-preserve-root) echo "kira-admin: no borro carpetas del sistema"; exit 3;; esac
  done
fi
case "$prog" in /*) ;; *) prog="$(command -v "$prog")" || { echo "kira-admin: no encuentro «$b»"; exit 127; } ;; esac
printf '%s uid=%s: %s' "$(date '+%F %T')" "${PKEXEC_UID:-?}" "$prog" >> "$LOG" 2>/dev/null
for a in "$@"; do printf ' %q' "$a" >> "$LOG" 2>/dev/null; done
printf '\n' >> "$LOG" 2>/dev/null
chmod 600 "$LOG" 2>/dev/null
exec "$prog" "$@"
