#!/usr/bin/env bash
# activar_fuera.sh — v3.00: que Kira app (el móvil) llegue a KiraOS también FUERA DE CASA, por Tailscale.
# Uso (una sola vez):  cd kira_god/kira_portatil   y   bash act  + Tab  (bash activar_fuera.sh)
#
# Qué hace:
#   1) instala Tailscale (red privada y cifrada entre TUS aparatos; no abre nada en el router);
#   2) lo conecta a tu cuenta: saca un código QR en esta terminal (o un enlace) para entrar con tu cuenta;
#   3) deja pasar a Kira SOLO por esa red privada (puertos 8770 y 8771 en la interfaz tailscale0);
#   4) te dice la dirección del portátil en Tailscale. El móvil la aprende solo la próxima vez que estéis en casa.
# En el móvil: instala la app «Tailscale» (Play Store) y entra con LA MISMA cuenta.
set -uo pipefail
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

echo "== 1. Tailscale"
if command -v tailscale >/dev/null 2>&1; then
  echo "   ya estaba instalado"
else
  if ! curl -fsSL https://tailscale.com/install.sh | $SUDO sh; then
    echo "[x] No he podido instalar Tailscale (¿hay internet?). Vuelve a intentarlo luego."
    exit 1
  fi
fi
$SUDO systemctl enable --now tailscaled >/dev/null 2>&1 || true

echo "== 2. Conectar a tu cuenta"
if tailscale ip -4 >/dev/null 2>&1; then
  echo "   ya estaba conectado"
else
  echo "   Escanea el código QR con el móvil (o abre el enlace) y entra con tu cuenta."
  echo "   Usa la MISMA cuenta en la app Tailscale del móvil."
  $SUDO tailscale up --qr || { echo "[x] No se completó la conexión. Lanza otra vez este guion."; exit 1; }
fi

echo "== 3. Dejar pasar a Kira solo por la red privada"
if command -v ufw >/dev/null 2>&1; then
  for p in 8770 8771; do
    $SUDO ufw allow in on tailscale0 to any port "$p" proto tcp >/dev/null 2>&1 || true
  done
  echo "   puertos 8770 y 8771 abiertos SOLO en tailscale0"
else
  echo "   (no hay cortafuegos ufw; nada que tocar)"
fi

IP="$(tailscale ip -4 2>/dev/null | head -n 1)"
echo
if [ -n "$IP" ]; then
  echo "[OK] Listo. El portátil en Tailscale es: $IP"
  echo "     En el móvil: instala «Tailscale», entra con la misma cuenta y deja Kira abierta un momento en casa"
  echo "     (aprende sola esta dirección). Desde entonces, fuera de casa se sincroniza y ves lo que hace KiraOS."
else
  echo "[x] Tailscale no ha dado dirección todavía. Espera un poco y lanza otra vez este guion."
  exit 1
fi
