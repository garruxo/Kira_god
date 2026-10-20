#!/usr/bin/env bash
# Compila el PINTOR de Kira: sd-cli de stable-diffusion.cpp (imágenes con IA, sin internet y sin servicios de terceros)
# para Android arm64 y lo deja en libs_android/arm64-v8a/ con nombre de librería (lib*.so) para que vaya dentro del APK
# y Android lo deje ejecutable en la carpeta de librerías nativas de la app (igual que el cerebro).
# Dos versiones: _dp (más rápida, móviles de 2018 en adelante: ARMv8.2 + dotprod + fp16) y la genérica (cualquier arm64).
# Uso: NDK=/ruta/al/ndk bash herramientas_pc/compilar_pintor_android.sh
#      PARA_PC=1 bash herramientas_pc/compilar_pintor_android.sh     (versión para este ordenador, para probar)
set -euo pipefail
VERSION="${SD_VERSION:-master-929-3f8527a}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
SALIDA="$RAIZ/libs_android/arm64-v8a"
TRABAJO="${TRABAJO:-$RAIZ/.cerebro_build}"
mkdir -p "$TRABAJO"
if [ ! -d "$TRABAJO/sd.cpp/ggml/src" ]; then
  rm -rf "$TRABAJO/sd.cpp"
  git clone --depth 1 --branch "$VERSION" https://github.com/leejet/stable-diffusion.cpp "$TRABAJO/sd.cpp"
  git -C "$TRABAJO/sd.cpp" submodule update --init --depth 1 ggml      # solo ggml (sin webp/webm ni la web)
fi
COMUN=(-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DSD_BUILD_SHARED_LIBS=OFF -DSD_SERVER_BUILD_FRONTEND=OFF
       -DSD_WEBP=OFF -DSD_WEBM=OFF -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF)

if [ "${PARA_PC:-}" = "1" ]; then
  cmake -S "$TRABAJO/sd.cpp" -B "$TRABAJO/pintor_pc" "${COMUN[@]}" -DGGML_NATIVE=ON   # en el PC, lo más rápido
  cmake --build "$TRABAJO/pintor_pc" --target sd-cli -j "$(nproc)"
  mkdir -p "$RAIZ/libs_pc"
  cp "$TRABAJO/pintor_pc/bin/sd-cli" "$RAIZ/libs_pc/kira_pintor"
  ls -la "$RAIZ/libs_pc/kira_pintor"
  echo "PINTOR_PC_OK"
  exit 0
fi

NDK="${NDK:-${ANDROID_NDK_LATEST_HOME:-${ANDROID_NDK_HOME:-}}}"
[ -d "$NDK" ] || { echo "No encuentro el NDK de Android (define NDK=...)"; exit 1; }
mkdir -p "$SALIDA"
STRIP="$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip"
compilar () {   # $1 = sufijo, $2 = arquitectura ARM
  local dir="$TRABAJO/pintor$1"
  cmake -S "$TRABAJO/sd.cpp" -B "$dir" -G "Unix Makefiles" \
    -DCMAKE_TOOLCHAIN_FILE="$NDK/build/cmake/android.toolchain.cmake" \
    -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-24 -DANDROID_STL=c++_static \
    "${COMUN[@]}" -DGGML_CPU_ARM_ARCH="$2"
  cmake --build "$dir" --target sd-cli -j "$(nproc)"
  cp "$dir/bin/sd-cli" "$SALIDA/libkira_pintor$1.so"
  "$STRIP" "$SALIDA/libkira_pintor$1.so" || true
  ls -la "$SALIDA/libkira_pintor$1.so"
}
compilar "_dp" "armv8.2-a+dotprod+fp16"
compilar "" "armv8-a"
echo "PINTOR_OK"
