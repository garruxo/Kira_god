#!/usr/bin/env bash
# Instala el «cerebro de casa» de Kira en un portátil con Ubuntu 24.04 y tarjeta NVIDIA (probado para RTX serie 50).
#
#   bash instalar_portatil.sh                  todo: drivers, CUDA, cerebro, pintor, modelos (~38 GB) y arranque solo
#   bash instalar_portatil.sh --sin-grande     sin el cerebro grande (ahorra 23 GB de descarga)
#   bash instalar_portatil.sh --sin-escritorio además, que el portátil arranque SIN escritorio (todo para Kira)
#   bash instalar_portatil.sh --prueba         sin gráfica y con modelos pequeños (para comprobarlo en otro equipo)
#   bash instalar_portatil.sh --sin-servicios  no dejarlo arrancando solo (para probar a mano)
#
# Se puede lanzar las veces que haga falta: lo que ya está hecho se salta (y las descargas siguen donde se quedaron).
set -euo pipefail

LLAMA_TAG="${LLAMA_TAG:-b11854}"                     # llama.cpp (el cerebro)
SD_TAG="${SD_TAG:-master-929-3f8527a}"               # stable-diffusion.cpp (el pintor), la misma que el móvil
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"
DATOS="${KIRA_PORTATIL:-$HOME/kira_portatil}"
BIN="$DATOS/bin"; MOD="$DATOS/modelos"; OBRA="$DATOS/obra"
PRUEBA=0; SIN_GRANDE=0; SIN_ESCRITORIO=0; SERVICIOS=1
for a in "$@"; do
  case "$a" in
    --prueba) PRUEBA=1 ;;
    --sin-grande) SIN_GRANDE=1 ;;
    --sin-escritorio) SIN_ESCRITORIO=1 ;;
    --sin-servicios) SERVICIOS=0 ;;
    *) echo "No conozco la opción $a"; exit 1 ;;
  esac
done
paso() { echo; echo "=== $* ==="; }
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
mkdir -p "$BIN" "$MOD" "$OBRA"

paso "1. Herramientas para compilar"
$SUDO apt-get update -qq
$SUDO apt-get install -y -qq build-essential cmake git curl python3 python3-tk pkg-config ca-certificates libcurl4-openssl-dev libssl-dev >/dev/null

GPU=0
if [ "$PRUEBA" = "0" ]; then
  paso "2. Tarjeta gráfica NVIDIA (driver y CUDA)"
  if ! command -v nvidia-smi >/dev/null || ! nvidia-smi >/dev/null 2>&1; then
    echo "Instalo el driver de NVIDIA (el que recomienda Ubuntu para tu tarjeta)…"
    $SUDO apt-get install -y -qq ubuntu-drivers-common >/dev/null
    $SUDO ubuntu-drivers install
    echo
    echo ">>> Driver instalado. REINICIA el portátil y vuelve a lanzar:  bash $0 $*"
    exit 0
  fi
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
  export PATH="/usr/local/cuda/bin:$PATH"
  if ! command -v nvcc >/dev/null; then
    echo "Instalo CUDA desde NVIDIA (la de Ubuntu es antigua y no conoce las RTX serie 50)…"
    curl -fsSL -o "$OBRA/cuda-keyring.deb" \
      https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
    $SUDO dpkg -i "$OBRA/cuda-keyring.deb" >/dev/null
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq cuda-toolkit >/dev/null
  fi
  nvcc --version | tail -n 1
  GPU=1
fi

compilar() {   # $1 = nombre, $2 = carpeta fuente, $3 = objetivo, $4.. = opciones de cmake
  local nombre="$1" src="$2" objetivo="$3"; shift 3
  local build="$OBRA/build-$nombre"
  rm -rf "$build"
  cmake -S "$src" -B "$build" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF "$@" >/dev/null
  cmake --build "$build" --target "$objetivo" -j "$(nproc)" >"$OBRA/$nombre.log" 2>&1
  cp "$build/bin/$objetivo" "$BIN/$objetivo"
}

paso "3. El cerebro (llama.cpp $LLAMA_TAG)"
if [ ! -x "$BIN/llama-server" ] || [ "$(cat "$BIN/.llama" 2>/dev/null)" != "$LLAMA_TAG-$GPU" ]; then
  [ -d "$OBRA/llama.cpp" ] || git clone -q --depth 1 --branch "$LLAMA_TAG" https://github.com/ggml-org/llama.cpp "$OBRA/llama.cpp"
  if [ "$GPU" = "1" ]; then
    if ! compilar llama "$OBRA/llama.cpp" llama-server -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=native -DLLAMA_CURL=OFF; then
      echo "Con CUDA no ha compilado (mira $OBRA/llama.log). Pruebo con Vulkan, que también usa la gráfica…"
      $SUDO apt-get install -y -qq libvulkan-dev glslc >/dev/null
      compilar llama "$OBRA/llama.cpp" llama-server -DGGML_VULKAN=ON -DLLAMA_CURL=OFF
    fi
  else
    compilar llama "$OBRA/llama.cpp" llama-server -DLLAMA_CURL=OFF -DGGML_NATIVE=ON
  fi
  echo "$LLAMA_TAG-$GPU" > "$BIN/.llama"
fi
echo "llama-server listo."

paso "4. El pintor (stable-diffusion.cpp $SD_TAG)"
if [ ! -x "$BIN/sd-cli" ] || [ "$(cat "$BIN/.sd" 2>/dev/null)" != "$SD_TAG-$GPU" ]; then
  if [ ! -d "$OBRA/sd.cpp/ggml/src" ]; then
    rm -rf "$OBRA/sd.cpp"
    git clone -q --depth 1 --branch "$SD_TAG" https://github.com/leejet/stable-diffusion.cpp "$OBRA/sd.cpp"
    git -C "$OBRA/sd.cpp" submodule update -q --init --depth 1 ggml
  fi
  SDOPC=(-DSD_BUILD_SHARED_LIBS=OFF -DSD_SERVER_BUILD_FRONTEND=OFF -DSD_WEBP=OFF -DSD_WEBM=OFF)
  if [ "$GPU" = "1" ]; then
    if ! compilar sd "$OBRA/sd.cpp" sd-cli "${SDOPC[@]}" -DSD_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=native; then
      echo "Con CUDA no ha compilado (mira $OBRA/sd.log). Pruebo con Vulkan…"
      $SUDO apt-get install -y -qq libvulkan-dev glslc >/dev/null
      compilar sd "$OBRA/sd.cpp" sd-cli "${SDOPC[@]}" -DSD_VULKAN=ON
    fi
  else
    compilar sd "$OBRA/sd.cpp" sd-cli "${SDOPC[@]}" -DGGML_NATIVE=ON
  fi
  echo "$SD_TAG-$GPU" > "$BIN/.sd"
fi
echo "sd-cli listo."

paso "5. Los modelos (se descargan una vez; si se corta, sigue donde iba)"
OPC=(); [ "$PRUEBA" = "1" ] && OPC+=(--prueba); [ "$SIN_GRANDE" = "1" ] && OPC+=(--sin-grande)
python3 "$AQUI/servidor_portatil.py" --lista-descargas "${OPC[@]}" | while read -r archivo url bytes; do
  destino="$MOD/$archivo"
  if [ -f "$destino" ] && { [ "$bytes" = "0" ] || [ "$(stat -c %s "$destino")" = "$bytes" ]; }; then
    echo "  ya está: $archivo"; continue
  fi
  echo "  bajando $archivo ($((bytes / 1000000)) MB)…"
  curl -fL --retry 10 --retry-delay 5 -C - -o "$destino.parte" "$url"
  if [ "$bytes" != "0" ] && [ "$(stat -c %s "$destino.parte")" != "$bytes" ]; then
    echo "  [x] $archivo no ha llegado entero: vuelve a lanzar el instalador."; exit 1
  fi
  mv "$destino.parte" "$destino"
done

paso "6b. Herramientas de defensa de red (Nmap y Wireshark, para vigilar TU red)"
if [ "$PRUEBA" = "0" ]; then
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq nmap tshark >/dev/null 2>&1 || \
    echo "  (no pude instalar nmap/tshark ahora; Kira te dirá cómo cuando los necesite)"
  if getent group wireshark >/dev/null; then
    $SUDO usermod -aG wireshark "$USER" || true          # para capturar tráfico sin ser administrador
    echo "  Nmap y Wireshark listos (solo se usan sobre TU red). Para capturar tráfico, vuelve a iniciar sesión una vez."
  fi
fi

paso "6. La llave (token) del laboratorio: la misma para el laboratorio y el cerebro de casa"
( cd "$RAIZ/kira_laboratorio" && python3 -c "import iniciar_laboratorio as i; i.token()" )
chmod 600 "$RAIZ/kira_laboratorio/token_lab.txt"

if [ "$SERVICIOS" = "1" ]; then
  paso "7. Que arranque solo al encender el portátil"
  OPC_SRV=""; [ "$PRUEBA" = "1" ] && OPC_SRV="--prueba"
  $SUDO tee /etc/systemd/system/kira-laboratorio.service >/dev/null <<EOF
[Unit]
Description=Laboratorio de Kira (prueba mejoras y empareja el móvil)
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
WorkingDirectory=$RAIZ/kira_laboratorio
ExecStart=/usr/bin/python3 $RAIZ/kira_laboratorio/iniciar_laboratorio.py
Restart=always
RestartSec=5
StandardOutput=journal+console

[Install]
WantedBy=multi-user.target
EOF
  $SUDO tee /etc/systemd/system/kira-portatil.service >/dev/null <<EOF
[Unit]
Description=Cerebro de casa de Kira (cerebro grande y pintor para el móvil)
After=network-online.target kira-laboratorio.service
Wants=network-online.target

[Service]
User=$USER
Environment=PATH=/usr/local/cuda/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 $AQUI/servidor_portatil.py --datos $DATOS $OPC_SRV
Restart=always
RestartSec=5
StandardOutput=journal+console

[Install]
WantedBy=multi-user.target
EOF
  $SUDO tee /usr/local/bin/kira-codigo >/dev/null <<'EOF'
#!/usr/bin/env bash
# Enseña el último código de 6 cifras para emparejar el móvil con Kira.
journalctl -u kira-laboratorio --no-pager -n 300 | grep -A1 "CÓDIGO PARA CONECTAR" | tail -n 2
EOF
  $SUDO chmod +x /usr/local/bin/kira-codigo
  $SUDO tee /usr/local/bin/kira >/dev/null <<KIRACLI
#!/usr/bin/env bash
# Hablar con Kira en el portátil, sin móvil.
exec /usr/bin/python3 "$AQUI/kira_consola.py" "\$@"
KIRACLI
  $SUDO chmod +x /usr/local/bin/kira
  $SUDO tee /usr/local/bin/kira-ventana >/dev/null <<KIRAWIN
#!/usr/bin/env bash
# La ventana de Kira (gráfica).
exec /usr/bin/python3 "$AQUI/kira_escritorio.py" "\$@"
KIRAWIN
  $SUDO chmod +x /usr/local/bin/kira-ventana
  $SUDO tee /usr/share/applications/kira.desktop >/dev/null <<KIRADESK
[Desktop Entry]
Name=Kira
Comment=Tu asistente Kira
Exec=/usr/local/bin/kira-ventana
Terminal=false
Type=Application
Categories=Utility;
KIRADESK
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable --now kira-laboratorio.service kira-portatil.service
  if command -v ufw >/dev/null && $SUDO ufw status | grep -q "Status: active"; then
    for red in 192.168.0.0/16 10.0.0.0/8 172.16.0.0/12; do
      for p in 8765/tcp 8766/udp 8767/udp 8770/tcp; do
        $SUDO ufw allow from "$red" to any port "${p%/*}" proto "${p#*/}" >/dev/null
      done
    done
    echo "Cortafuegos: abiertos los puertos de Kira solo para tu red de casa."
  fi
  if [ "$SIN_ESCRITORIO" = "1" ]; then
    $SUDO systemctl set-default multi-user.target
    echo "Al reiniciar arrancará SIN escritorio (todo para Kira). Para volver: sudo systemctl set-default graphical.target"
  fi
fi

paso "Listo"
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo "El cerebro de casa de Kira está en este portátil (${IP:-sin red})."
echo "Para HABLAR con Kira aquí mismo: abre la app «Kira» del menú, o escribe  kira-ventana  (ventana) o  kira  (terminal)."
echo "Si además quieres usarla desde el móvil: dile «Kira, conéctate al ordenador» y escríbele el código."
echo "Para ver el código aquí:  kira-codigo     ·  para ver cómo va:  journalctl -u kira-portatil -f"
