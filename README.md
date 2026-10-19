# Kira_god (APK)

Núcleo + panel local (Kivy, móvil y PC). Las mejoras se piden desde el panel, el laboratorio las prueba y
solo se aplican con tu confirmación explícita ("APLICAR <id>" o el botón del panel).

**Va en el APK:** main.py, kira_god.py, panel_kira.py, sala_kira.py, pasarela_cliente.py.
**No va en el APK** (`extras/`, `legacy/`): cerebro auxiliar, pasarela_extra, ciberseguridad por patrones, material antiguo.

## Compilar
`buildozer -v android debug` (arm64-v8a, permiso INTERNET). Con 4 GB de RAM usa swap.

## Importante
- Tokens antiguos que estuvieron en el código (`KIRA-SECURE-TOKEN-9928-XYZ`, `KIRA_MASTER_2026`): considéralos comprometidos y no los reutilices.
- Clave de Claude: `config clave: ...` desde el panel; se guarda en el dispositivo, nunca en el código.
- La auditoría ya no finge: muestra el estado real. El análisis de ciberseguridad es por patrones (avisa, no bloquea).
- No probado aquí: renderizado real de Kivy y ejecución en Android/Termux.

## Interfaz inmersiva (nueva)
- **Inicio:** un orbe vivo (reposo / escuchando / pensando / hablando). Kira te saluda; le escribes o le hablas (botón Mic).
  Lo que no es una orden del núcleo lo contesta con la API (hace falta la clave); las órdenes conocidas se ejecutan.
  **Tocar el orbe entra al menú.**
- **Menú:** Sala Hacker, Mejoras, Pasarela, Módulos, Búsqueda (local), Notas, Memoria, Estado, Consola, Configuración, Ayuda.
- Atrás de Android / Esc: del apartado al menú, del menú al orbe.
- **Voz:** usa `plyer` (añadido a `requirements`) y el permiso `RECORD_AUDIO`. Hablar en voz alta suele funcionar; escuchar
  (voz a texto) depende del móvil y NO está probado. Si no funciona, Kira lo dice y se escribe igual.
  Si no quieres micrófono, quita `,RECORD_AUDIO` de `android.permissions` en buildozer.spec.
- Privacidad: el historial (`conversacion.json`) se guarda solo en el dispositivo, sin claves ni tokens; se borra en Memoria.
- Tests (PC, sin Kivy real): `python tests/test_logica.py` y `python tests/test_cableado.py`.

## Cerebro local, aprendizaje y lienzo (nuevo)
- **Orden de respuesta:** órdenes del núcleo → `cerebro_local.py` (en el dispositivo) → API de Claude (solo si hace falta y hay clave).
- **Aprende:** «aprende que mi gato se llama Miko». Pregunta algo que no sabe («qué es un agujero negro») → busca en la
  Wikipedia en español, te muestra el resumen y su fuente, y **solo lo guarda si dices «sí»**. «Eso está mal» lo descarta; «olvida X» lo borra.
  Se ve y se borra en el apartado **Conocimiento**. El texto de internet se guarda como texto inerte y no se mezcla en los prompts de la API.
  Solo se envía a la Wikipedia el tema de la pregunta (no tu conversación). **No probado con la red real** (el entorno de pruebas no tenía acceso).
- **Lienzo:** «dibuja una playa al atardecer con palmeras» (playa, montañas, bosque, desierto, ciudad, lago, espacio; día/atardecer/amanecer/noche).
  Dibuja por código: estilizado, no es una IA de imágenes. «Guardar PNG» lo deja en la carpeta privada de la app (aún sin exportar a la galería).
- No es un modelo de lenguaje local: sin clave de API la charla libre es limitada. Un modelo pequeño dentro del móvil (8 GB lo permiten) queda como paso opcional.
- Tests: `python tests/test_cerebro.py`.

## Sala Hacker inmersiva (nueva)
- **Habitación 3D de verdad** (`habitacion_kira.py`): perspectiva, recorte y muebles en 3D (~375 caras; solo se dibujan las visibles).
  Entras, caminas hasta la mesa del ordenador y **arrastras para mirar**: izquierda = BIBLIOTECA, derecha = SALIDA.
  Tocar un objeto te acerca a él; también puedes decir/escribir «hackear», «programar», «aprender programación», «biblioteca», «salir».
- **Terminal del ordenador:** APRENDER (mini-curso de Python de 8 lecciones que funciona sin internet, comprobar sintaxis sin ejecutar,
  pedirle una lección a Kira con la API, guardar en la biblioteca y que Kira la recuerde) y MEJORAR (pides un módulo a Kira ->
  laboratorio -> tú confirmas con doble toque). Alcance: Kira / Sistema / Aplicación. **Las mejoras son módulos nuevos**; no cambian el núcleo.
- **Biblioteca:** Lecciones, Apuntes (tuyos), Módulos instalados (solo lectura) y lo Aprendido por Kira.
- No es OpenGL ni modelos: geometría simple y estilizada. **No medido en un móvil real** (fluidez); el motor solo redibuja cuando algo se mueve.
- Tests: `python tests/test_sala.py`.

## Sala de Diseño y Sala de Cine (nuevas)
Menú → **Sala de Diseño** (habitación playera en 3D con una ventana panorámica a la playa).
- **Al fondo**: el ordenador de diseño. **Izquierda**: la mediateca (tus vídeos y tu música) y la puerta de regreso (al menú). **Derecha**: la puerta del CINE. Botón **Salir** arriba.
- **Ordenador → estudio**: 
  - WEB: genera una página `.html` de una sola página (sin JavaScript). Con clave de API la IA propone textos y colores en JSON y la plantilla los pinta (la IA nunca escribe el HTML); sin clave usa plantillas locales y lo dice.
  - APP: maqueta (wireframe) de 1 a 3 pantallas.
  - VIDEOCLIP: guion de escenas + storyboard animado, y **«Crear vídeo MP4»: genera un MP4 real** (ver «Motor de vídeo»).
  - Lo creado queda dentro de la app (`diseno/`) y se intenta copiar a Descargas; si Android lo impide, lo dice.
- **Mediateca**: Vídeos / Música / Creados / En desarrollo. «Buscar en el móvil» pide permiso de archivos y busca en Movies, DCIM, Music, Download y Recordings (2 niveles). «Quitar de la lista» NO borra el archivo.
- **Sala de Cine**: butacas frente a una pantalla. A la izquierda vuelves a la sala de diseño; a la derecha, salida; botón **Salir** arriba. Tocar la pantalla abre el reproductor.
- **Reproductor**: videoclips creados (siempre), música (SDL: mp3/ogg/wav…) y vídeo del móvil **solo si el APK incluye un proveedor de vídeo** (`ffpyplayer`, ver `buildozer.spec`; compilarlo en Android es pesado y no está probado). Si no, lo dice.
- Todavía NO edita vídeos ajenos ni tiene mesa de mezcla de audio: son los siguientes pasos.

Archivos: `salas_kira.py` (3D de las dos salas), `diseno_kira.py` (lógica), `sala_diseno_kira.py` (pantallas). Tests: `tests/test_diseno.py`, `tests/test_cableado_diseno.py`.
Sin probar aquí: renderizado real de Kivy, rendimiento en el móvil, permisos de Android, reproducción real de audio/vídeo.

## Motor de vídeo (nuevo)
`motor_video_kira.py` convierte un guion en un **MP4 H.264 de verdad**: cada escena se dibuja por código (Pillow), se anima con zoom/paneo, hay fundidos encadenados, títulos, entrada/salida a negro y, si quieres, música con fundidos (AAC). Formatos 16:9, 9:16 y 4:3; calidades borrador/normal/alta. Lo codifica ffmpeg (sin shell, con límites).
- **Dónde se crea** (`video_cliente_kira.py`): 1) aquí, si el equipo tiene Pillow + ffmpeg (el PC); 2) si no, en el **laboratorio del PC** (`kira_laboratorio/servidor_lab.py`, mismo `pasarela.json` y token), que recibe solo el guion (y la música) y devuelve el MP4; 3) si ninguno puede, lo explica.
- En el PC: `pip install pillow` y tener ffmpeg (o `pip install imageio-ffmpeg`); arranca `servidor_lab.py`. Uso suelto: `python motor_video_kira.py guion.clip.json salida.mp4 16:9 normal musica.mp3`.
- El móvil **no incluye ffmpeg**: crea el vídeo por el laboratorio. Verlo dentro de Kira requiere además `ffpyplayer` en el APK; si no, se abre desde Descargas.
- Medido aquí: un clip de 24 s en 360p tarda ~3 s. El rendimiento en tu PC y por WiFi no está medido.
- Tests: `tests/test_video.py` (genera MP4 reales, prueba el servidor HTTP y el cliente).

## Kira se prepara sola: Taller, capacidades y herramientas (nuevo)
- **Taller** (menú) o por texto «capacidades» / «preparar mesa de mezcla»: lista lo que Kira sabe hacer y lo que le falta (mesa de mezcla, editor de vídeo, conversor, extraer audio, efectos de audio…). Para cada cosa dice si puede **programarla ya** o qué falta antes (casi siempre ffmpeg).
- **Programar**: «Programarla con Kira» deja el pedido escrito en la terminal de mejoras; de ahí sigue el camino de siempre (Kira escribe el módulo → laboratorio → tú lo apruebas con doble toque).
- **Descargar**: si arrancas el laboratorio con `python servidor_lab.py --permitir-instalar`, el Taller puede pedir al PC que instale paquetes de una **lista blanca** (pillow, numpy, imageio-ffmpeg, pydub, mutagen, soundfile, scipy) con pip, tras tu confirmación. Desactivado por defecto. En el móvil no se instala nada.
- **Herramientas para módulos** (`herramientas_kira.py`): un comando de módulo puede ser `def comando(texto, kira)`. `kira` da carpeta de trabajo (nombres simples, sin rutas), acceso a la mediateca (importar/exportar) y **ffmpeg restringido** (`ffmpeg_seguro.py`: opciones y filtros de lista blanca, sin red, sin shell, con límites). Si el móvil no tiene ffmpeg, el trabajo se hace en el laboratorio del PC (`/archivo`, `/ffmpeg`).
- Así Kira puede programar la mesa de mezcla o el editor sin usar `subprocess`. **Los módulos los escribe la IA**: cada uno hay que probarlo y aprobarlo; lo que salga dependerá de la API y no está garantizado.
- Tests: `tests/test_taller.py` (mezclas, recortes y uniones reales con ffmpeg; filtros peligrosos rechazados; laboratorio por HTTP), `tests/test_cableado_taller.py`.

## Bitácora: Kira recuerda los pasos y diagnostica fallos (nuevo)
`bitacora_kira.py` es la memoria de trabajo de Kira (local, sin red):
- **Guías de pasos** con dónde y cómo: instalar ffmpeg, arrancar el laboratorio, conectar la pasarela, la clave de la API, compilar el APK, ver vídeo en el móvil, permisos, módulos. Di «cómo instalar ffmpeg», «cómo arranco el laboratorio»…
- **Mapa del proyecto**: qué hace cada archivo (para saber qué tocar).
- **Registro de fallos reales**: cada vez que algo falla (vídeo, laboratorio, mejoras, instalar, módulos) se apunta **sin claves ni tokens** (se redactan). Di «diagnosticar» y Kira relaciona los fallos recientes con su arreglo conocido; «fallos resueltos» los cierra; «apunta: …» deja una nota.
- El contexto de la bitácora (mapa de archivos + fallos recientes) se le pasa al generador de mejoras, así que **cuando algo falla, Kira puede proponer la corrección** mejor informada (y, como siempre, la mejora pasa por el laboratorio y tu aprobación).
- Tests: `tests/test_bitacora.py`.

## Sala de Ciberseguridad: un búnker de SOLO defensa y aprendizaje (nuevo)
Menú → **Ciberseguridad**. Habitación 3D oscura tipo búnker/matrix: al fondo la pantalla con la **silueta de Kira** (se anima cuando habla), a la izquierda el **panel del dispositivo**, y la puerta de salida. La consola central tiene tres pestañas:
- **ESTUDIAR**: biblioteca de amenazas conocidas (malware, phishing, ransomware, contraseñas, WiFi pública, permisos de apps, ingeniería social, actualizaciones, copias, APK de fuera de la tienda) explicadas de forma **defensiva**: qué son, señales de alarma y cómo protegerte. Marcas tu progreso (por estudiar / estudiado / ya lo aplico).
- **REVISIÓN**: comprueba hábitos de seguridad del propio Kira y del aparato con lo que ya sabe (permisos del archivo de la clave, si el laboratorio está expuesto, token corto, módulos con avisos, espacio, recordatorios de copias). Solo lee.
- **DISPOSITIVO**: estado real del aparato (RAM, CPU, disco, red, batería, sistema). Solo lee.

**Blindaje (importante):** esta sala es de **solo lectura y aprendizaje**. Kira **no ejecuta, no descarga, no analiza ni guarda código malicioso, no hace ataques ni escanea redes**. Lo único que se guarda es tu progreso de estudio. Es, a propósito, educación defensiva y monitorización del propio dispositivo: no un laboratorio de malware ni una herramienta de ataque.
Archivos: `ciber_kira.py` (lógica), `sala_ciber_kira.py` (pantallas), `salas_kira.py` (construir_ciber). Tests: `tests/test_ciber.py`, `tests/test_cableado_ciber.py`.

## Revisión y compilación (nuevo)
- **Antes de compilar**: `python herramientas_pc/comprobar_antes_de_compilar.py` comprueba en segundos la sintaxis de
  todos los archivos, que los imports del proyecto existen, que **nada importa al arrancar una librería que no va en el
  APK** (eso cierra la app al abrirla) y lo básico de `buildozer.spec`.
- **Compilar**: lee `COMPILAR_PACKARD_BELL.md`. Recomendado: en la nube con GitHub Actions
  (`.github/workflows/compilar_apk.yml`, Ubuntu 24.04 + Python 3.12 + `cython==0.29.34`). Alternativa: WSL con
  **Ubuntu-24.04** (no la última) y un `venv`.
- Versión **2.6**; `android.api = 33`, `android.minapi = 24`.

## Bitácora y Ciberseguridad en profundidad (nuevo)
- Bitácora: pantalla propia en el menú (resumen, fallos con su arreglo, guías, notas). Cuando algo falla en vídeo,
  mezcla/editor o instalar, el arreglo conocido aparece **debajo del error**. Guías nuevas: compilar en la nube, WSL en
  PC antiguo, poca RAM, instalar/actualizar el APK, mesa de mezcla y editor. «arregla el módulo X» prepara la mejora
  con el error.
- Ciberseguridad (solo defensa): 18 amenazas explicadas, pestaña **SI TE PASA** (cuenta robada, enlace pulsado, móvil
  raro, móvil perdido, llamada del «banco») con pasos en orden, **preguntas libres** a Kira en modo estrictamente
  defensivo (con la API; sin ella, biblioteca local), y la revisión detecta claves guardadas por error en tus notas o
  historial y lista los módulos instalados.
- Arreglado: la mediateca ahora se comparte bien entre pantallas (antes la mesa de mezcla no veía lo escaneado hasta
  reiniciar y podía pisar cambios); los resultados de mezcla/editor se guardan en una carpeta permanente.

## Cerebro local: Kira independiente de la API (nuevo)
Kira puede pensar con un **modelo de IA pequeño en el propio móvil** (llama.cpp «llama-server» en Termux, en
`http://127.0.0.1:8080`, formato OpenAI) en vez de con la API de Claude: sin internet y sin pagar. Pensado para un
móvil dedicado a Kira (8 GB → modelos de 2-4B en Q4). Guía paso a paso: **`CEREBRO_LOCAL.md`**.
- Órdenes: `cerebro` (estado), `cerebro auto` (por defecto: local si está encendido, si no Claude), `cerebro local`,
  `cerebro claude`, `cerebro url: http://IP:8080` (si el modelo corre en otro equipo de casa).
- Todo lo que usaba la API usa el cerebro elegido: charla, lecciones, diseño, preguntas de ciberseguridad y mejoras.
  Las mejoras siguen pasando por el laboratorio y tu doble confirmación.
- Honesto: más lento y menos listo que Claude; para programar mejoras fallará más (el laboratorio lo filtra).
- Archivo: `cerebro_ia_kira.py`. Tests: `tests/test_cerebro_ia.py` (con un servidor llama simulado).
- Para que un modelo pequeño programe mejor (`mejoras_ia_kira.py`): en modo auto las mejoras de código van a Claude si
  hay clave (`cerebro mejoras auto|local|claude`); con el modelo local, instrucciones cortas con ejemplos, revisión
  previa del código en el móvil antes del laboratorio, reintentos ante formato incorrecto y 5 intentos.
  Tests: `tests/test_mejoras_ia.py`.

## Baúl de recuerdos: memoria en disco que no llena la RAM (nuevo)
- `recuerdos_kira.py`: una carpeta privada de Kira (`<datos>/recuerdos/`) donde va guardando recuerdos sin límite
  de 500 (hasta 200 MB, unos 300.000 recuerdos). Funciona como un libro con índice: para recordar algo mira el índice
  (4096 trozos pequeños), abre solo los trozos de esas palabras y lee solo las líneas que encajan.
  En la prueba con 3000 recuerdos: búsqueda en menos de 1 ms usando unos 7 KB de RAM.
- **Solo ella la reconoce**: cada recuerdo va firmado con una llave propia (HMAC). Una línea cambiada a mano, o
  copiada de otra Kira, se ignora. Las claves se tapan antes de guardar. Es texto: nunca se ejecuta.
- **Antes de preguntar a nadie busca en el baúl**: lo que le enseñaste («aprende que…», «guarda recuerdo: …») y lo
  que le explicó Claude (si preguntas casi lo mismo) lo responde ella sola, sin internet ni API.
- **Aprende de Claude**: cada explicación de Claude se guarda con su pregunta. Las del modelo local NO (se equivoca
  más). Cuando sí pregunta a la IA, le pasa los recuerdos que vienen al caso (nunca lo bajado de internet).
- Órdenes: `guarda recuerdo: …`, `qué recuerdas de …`, `olvida recuerdo N`, `recuerdos`. «Eso está mal» olvida el
  último recuerdo que usó. Pruebas: `tests/test_recuerdos.py`.
- **Busca por significado**: lista de sinónimos de serie (minino/gato, medicina/pastilla, móvil/teléfono…) y sinónimos
  que aprende: tú con `parecido: minino = gato, felino`, o el **modelo del móvil** cuando no encuentra una palabra
  en una pregunta sobre tus cosas (nunca gasta Claude para esto). Cada palabra se pregunta una sola vez y se guarda.
