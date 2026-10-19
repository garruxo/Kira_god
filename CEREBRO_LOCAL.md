# Cerebro local: Kira sin internet ni API (móvil dedicado a Kira)

Kira puede usar un **modelo de IA pequeño que corre en el propio móvil** en lugar de la API de Claude. Va con
**llama.cpp** dentro de **Termux** y Kira le habla por `http://127.0.0.1:8080`. Con 8 GB de RAM caben modelos de
2 a 4 mil millones de parámetros (2-3,5 GB).

**Lo que hay que saber antes:**
- Es **más lento** que Claude (unas pocas palabras por segundo) y **menos listo**: para charlar, explicar y resúmenes va
  bien; para programar mejoras se equivocará más (el laboratorio lo prueba igual, puede necesitar varios intentos).
- Calienta el móvil y gasta batería mientras piensa. Para un móvil dedicado, mejor **enchufado**.
- Ocupa: llama.cpp ~1 GB compilado + el modelo (2-3,5 GB).

---

## 1. Instalar Termux (una vez)
Instala **Termux desde F-Droid** (<https://f-droid.org>), **no** la de Google Play (es una versión experimental).

## 2. Compilar llama.cpp en Termux (una vez, 10-20 minutos)
Abre Termux y escribe, una línea cada vez:
```
pkg update && pkg upgrade -y
```
```
pkg install -y git cmake clang wget
```
```
git clone https://github.com/ggml-org/llama.cpp
```
```
cd llama.cpp && cmake -B build && cmake --build build --config Release -j4
```

## 3. Descargar un modelo (una vez)
En <https://huggingface.co> busca un modelo **«Instruct»** en formato **GGUF** y cuantización **Q4_K_M**. Para 8 GB:
- **Qwen 3.5 4B Instruct** (~3,4 GB): el mejor equilibrio en calidad.
- **Qwen 3.5 2B Instruct** (~1,9 GB): más rápido, si el 4B va lento o se cierra.

Los nombres cambian a menudo: en la página del modelo, pestaña *Files*, mantén pulsado el archivo `…Q4_K_M.gguf` y
copia el enlace de descarga. Luego, en Termux:
```
wget -O ~/kira.gguf "PEGA_AQUÍ_EL_ENLACE"
```

## 4. Encender el cerebro
```
cd ~/llama.cpp && ./build/bin/llama-server -m ~/kira.gguf -c 4096 --host 127.0.0.1 --port 8080
```
- `--host 127.0.0.1`: solo Kira (en el mismo móvil) puede usarlo; nadie más de tu WiFi.
- Si el móvil va justo de memoria, baja el contexto: `-c 2048`.
- Déjalo abierto. Para que Android no lo cierre: en Termux desliza la notificación y pulsa **Acquire wakelock**
  (o escribe `termux-wake-lock`), y en **Ajustes > Apps > Termux > Batería** elige **Sin restricciones**.

## 5. Decirle a Kira que lo use
En Kira (orbe o consola) escribe **`cerebro`**. Debe decir **«Modelo local: ENCENDIDO»**.
- `cerebro auto` (lo normal): usa el local si está encendido y, si no, Claude si tienes clave.
- `cerebro local`: solo el local (nunca usa internet para la IA).
- `cerebro claude`: solo Claude.
- `cerebro url: http://192.168.1.50:8080`: si el modelo corre en otro equipo de casa en vez de en el móvil
  (entonces arráncalo con `--host 0.0.0.0` en ese equipo).

## 6. (Opcional) Que se encienda solo al arrancar el móvil
Instala **Termux:Boot** desde F-Droid, ábrelo una vez y en Termux:
```
mkdir -p ~/.termux/boot
```
```
printf '#!/data/data/com.termux/files/usr/bin/sh\ntermux-wake-lock\ncd ~/llama.cpp && ./build/bin/llama-server -m ~/kira.gguf -c 4096 --host 127.0.0.1 --port 8080\n' > ~/.termux/boot/cerebro_kira.sh
```
```
chmod +x ~/.termux/boot/cerebro_kira.sh
```

## Más rápido y más listo

**Lo que ya hace Kira sola:**
- **Reparte el trabajo** (modo `cerebro auto`): charla, explicaciones y resúmenes con el modelo del móvil; las
  **mejoras de código con Claude** si tienes clave, porque programa mucho mejor. Sin clave, también en local.
  Cámbialo con `cerebro mejoras local` (todo en el móvil) o `cerebro mejoras claude`.
- Al modelo pequeño le da **instrucciones cortas con ejemplos** de módulos que funcionan.
- **Revisa el código en el propio móvil** (sintaxis, que exista `registrar()`, nada prohibido) antes de mandarlo al
  laboratorio; si falla, le explica el error al modelo y lo vuelve a intentar.
- Con el modelo local tiene **5 intentos** (con Claude, 3) y si se equivoca de formato **reintenta** en vez de rendirse.
- Lo que ya sabe (lo que le enseñaste, cálculos, la bitácora…) lo responde **al instante, sin usar el modelo**.

**Lo que puedes ajustar tú al encenderlo:**
- **Hilos del procesador:** añade `-t 4` (prueba también `-t 6`) y quédate con el más rápido:
  `./build/bin/llama-server -m ~/kira.gguf -c 2048 -t 4 --host 127.0.0.1 --port 8080`
- **Contexto más corto** (`-c 2048`): va más rápido y gasta menos memoria; a Kira le basta.
- **Cuantización Q4_K_M** (no Q8 ni F16): casi igual de lista y bastante más rápida.
- **Tamaño:** el 4B entiende y escribe mejor; el 2B responde más rápido. Puedes tener los dos y cambiar el `-m`.
- **Móvil frío y enchufado**, sin otras apps abiertas: al calentarse, el móvil se frena solo.
- **Más potencia:** si algún día tienes un PC mejor en casa, arranca allí `llama-server` con un modelo más grande
  (`--host 0.0.0.0`) y en Kira `cerebro url: http://IP_DEL_PC:8080`. Kira usará ese cerebro por la WiFi.

## Si algo falla
| Síntoma | Qué hacer |
|---|---|
| Kira dice «el cerebro local no responde» | ¿Está Termux abierto con `llama-server` en marcha? Mira `cerebro` en Kira |
| Termux se cierra solo | Wakelock + batería «Sin restricciones» (paso 4); prueba el modelo 2B o `-c 2048` |
| Responde en inglés o raro | Usa un modelo «Instruct» (no «Base»); el 4B entiende mejor el español |
| Muy lento | Modelo 2B, `-c 2048`, móvil enchufado y frío |
