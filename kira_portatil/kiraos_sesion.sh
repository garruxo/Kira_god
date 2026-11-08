#!/usr/bin/env bash
# kiraos_sesion.sh — v3.05: la SESIÓN PROPIA de KiraOS. Al encender, LightDM entra directo aquí (no en el escritorio
# de Xubuntu): fondo oscuro, lo justo de Xubuntu para que vayan el teclado español y las ventanas, y Kira a pantalla
# completa. No se ve el escritorio de Xubuntu.
#   · «Ir a Xubuntu» (menú K) o cerrar Kira (Alt+F4)  ->  se abre el escritorio de Xubuntu, como antes.
#   · Si Kira se cierra de golpe (un fallo), se vuelve a abrir sola; si falla 3 veces seguidas, va a Xubuntu
#     (así nunca te quedas con la pantalla negra).
# Lo instala solo_kira.sh en /usr/local/bin/kiraos-sesion. Para pruebas: KIRA_KIRAOS, KIRA_ESCRITORIO, KIRA_MARCA.
KIRAOS="${KIRA_KIRAOS:-/usr/local/bin/kiraos}"
MARCA="${KIRA_MARCA:-$HOME/.kira_ir_a_xubuntu}"
export KIRA_SESION_PROPIA=1

if [ -z "${KIRA_KIRAOS:-}" ]; then
  xsetroot -solid "#05070f" >/dev/null 2>&1 || true
  # teclado (español), letra, ratón: lo que Xubuntu tiene guardado, sin abrir su escritorio
  command -v xfsettingsd >/dev/null 2>&1 && xfsettingsd --daemon >/dev/null 2>&1
  # quien coloca las ventanas (para la pantalla completa y la ventanita de la clave de la WiFi)
  command -v xfwm4 >/dev/null 2>&1 && xfwm4 --compositor=off --daemon >/dev/null 2>&1
  # v3.06: esperar a que el gestor de ventanas esté listo (si Kira se abre antes, no ocupa toda la pantalla)
  for _ in $(seq 1 20); do
    if command -v xprop >/dev/null 2>&1; then
      xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null | grep -q "window id" && break
    else
      sleep 1; break
    fi
    sleep 0.25
  done
fi
rm -f "$MARCA"

fallos=0
while true; do
  inicio=$(date +%s)
  "$KIRAOS"
  rc=$?
  if [ -f "$MARCA" ]; then rm -f "$MARCA"; break; fi     # «Ir a Xubuntu»
  [ "$rc" -eq 0 ] && break                                 # la cerraste tú (Alt+F4)
  if [ $(( $(date +%s) - inicio )) -lt 60 ]; then fallos=$((fallos + 1)); else fallos=1; fi
  [ "$fallos" -ge 3 ] && break                             # falla una y otra vez: mejor Xubuntu que negro
  sleep 1
done

if [ -n "${KIRA_ESCRITORIO:-}" ]; then exec $KIRA_ESCRITORIO; fi
pkill -x xfwm4 >/dev/null 2>&1; pkill -x xfsettingsd >/dev/null 2>&1; sleep 0.5
export KIRA_DESDE_KIRA=1                                   # para que Xubuntu no vuelva a abrir Kira él solo
for e in xfce4-session startlxqt startlxde xterm; do
  command -v "$e" >/dev/null 2>&1 && exec "$e"
done
exec sleep infinity
