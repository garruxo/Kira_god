# kira_laboratorio (PC o Termux; NO va en el APK)

1. `python kira_diagnostico.py` — comprobaciones reales (código de salida 0 = todo bien).
2. **Windows: doble clic en `Arrancar laboratorio.bat`** (o `python iniciar_laboratorio.py`). Escucha por la WiFi y
   enseña un código de 6 cifras. En el móvil: «Kira, conéctate al ordenador» y el código. Ya no hay que copiar el token
   (`token_lab.txt`): Kira lo recibe al emparejarse. `Arrancar con Windows.bat` lo deja arrancando solo al encender.
   `--solo-este-equipo` para que nadie más lo vea; `--sin-windows` quita el arranque automático.
3. `python kira_master.py` — consola del laboratorio (`ayuda`). Atajo: `python kira_cli.py <orden>`.
4. Tras revisar el código, sella el núcleo con la orden `sellar SELLAR NUCLEO`; `verificar` detecta cambios.

El sandbox limita tiempo/memoria y limpia el entorno, pero **no es una máquina virtual**: no ejecutes código en el que no confíes con tus archivos al alcance.
Para enlazar con Kira_god deja ambas carpetas juntas o define `KIRA_GOD_DIR`.
Se eliminaron `lab_core.py` y `kira.lock` (ejecutaban código sin control y llevaban una clave escrita).

## Vídeo (nuevo)
`servidor_lab.py` también atiende trabajos de vídeo (`lab_video.py`): `POST /video` (guion + formato/calidad), `GET /video/estado?id=`, `GET /video/archivo?id=`, `POST /audio?nombre=x.mp3`, `GET /video/capacidad`. Todas exigen el token. Necesita Pillow y ffmpeg en el PC y la carpeta `Kira_god` al lado (o `KIRA_GOD_DIR`). Máx. 2 vídeos a la vez, 20 guardados (caducan a la hora), audio ≤ 40 MB. Solo recibe datos (guion/audio), nunca código.

## Trabajos de ffmpeg e instalación (nuevo)
- `POST /archivo?nombre=x.mp4` (≤150 MB, solo audio/vídeo) → `archivo_id`; `POST /ffmpeg {entradas:[ids], args:[...], salida:"mp3"}` → trabajo; estado y descarga como el vídeo. Las opciones pasan por `ffmpeg_seguro.py` (de Kira_god): lista blanca de opciones y filtros, sin red, sin rutas.
- `POST /instalar {paquetes:[...]}` y `GET /instalar/lista`: SOLO si arrancas con `--permitir-instalar`; lista blanca en `lab_instalar.py`; usa `python -m pip install` sin shell. Recomendado: arrancar el servidor dentro de un entorno virtual.
- `tests_fijos/test_contrato.py` comprueba ahora que `registrar()` devuelve comandos de 1 parámetro (texto) o 2 (texto, kira).
