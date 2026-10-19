#!/usr/bin/env bash
# Compila llama-server (llama.cpp) para Android arm64 y lo deja en libs_android/arm64-v8a/ con nombre de librería
# (lib*.so) para que vaya dentro del APK y Android lo deje ejecutable en la carpeta de librerías nativas de la app.
# Dos versiones: _dp (más rápida, móviles de 2018 en adelante: ARMv8.2 + dotprod) y la genérica (cualquier arm64).
# Uso: NDK=/ruta/al/ndk bash herramientas_pc/compilar_cerebro_android.sh
set -euo pipefail
VERSION="${LLAMA_VERSION:-b11742}"
NDK="${NDK:-${ANDROID_NDK_LATEST_HOME:-${ANDROID_NDK_HOME:-}}}"
[ -d "$NDK" ] || { echo "No encuentro el NDK de Android (define NDK=...)"; exit 1; }
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
SALIDA="$RAIZ/libs_android/arm64-v8a"
TRABAJO="${TRABAJO:-$RAIZ/.cerebro_build}"
mkdir -p "$SALIDA" "$TRABAJO"
if [ ! -d "$TRABAJO/llama.cpp" ]; then
  git clone --depth 1 --branch "$VERSION" https://github.com/ggml-org/llama.cpp "$TRABAJO/llama.cpp"
fi
STRIP="$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip"
compilar () {   # $1 = sufijo, $2 = arquitectura ARM
  local dir="$TRABAJO/build$1"
  cmake -S "$TRABAJO/llama.cpp" -B "$dir" -G "Unix Makefiles" \
    -DCMAKE_TOOLCHAIN_FILE="$NDK/build/cmake/android.toolchain.cmake" \
    -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-24 -DANDROID_STL=c++_static \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF \
    -DGGML_CPU_ARM_ARCH="$2" -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF \
    -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_TOOLS=ON -DLLAMA_BUILD_SERVER=ON
  cmake --build "$dir" --target llama-server -j "$(nproc)"
  cp "$dir/bin/llama-server" "$SALIDA/libkira_cerebro$1.so"
  "$STRIP" "$SALIDA/libkira_cerebro$1.so" || true
  ls -la "$SALIDA/libkira_cerebro$1.so"
}
compilar "_dp" "armv8.2-a+dotprod+fp16"
compilar "" "armv8-a"
echo "CEREBRO_OK"
