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

## Estudio: Kira aprende sola, sin la API (nuevo)
- `estudio_kira.py`: `estudia: tema` lee los resúmenes de la Wikipedia en español que mejor encajan y los guarda en el
  baúl con su fuente. `estudia python` / `estudia python: json` guarda la documentación de Python que trae el propio
  móvil (sin internet; solo módulos de una lista segura). `aprende sola` recorre un plan de 40 temas (programación,
  sistemas, redes, ciberseguridad, IA, vídeo…) a razón de uno cada 10 minutos mientras la app está abierta.
- Lo aprendido se responde desde el baúl sin preguntar a ninguna IA. Lo bajado de internet nunca se pasa a una IA.
- `red_kira.py`: https con los certificados de `certifi` (en Android Python a veces no encuentra los del sistema).
- Pruebas: `tests/test_estudio.py`.

## Portada clara, botón de neón y escucha permanente (nuevo)
- `portada_kira.py`: fondo blanco con «Kira» repetido por todo el fondo y un botón redondo de neón en el centro
  (tocarlo = menú). El neón brilla más cuando Kira te escucha de verdad (tras oír su nombre) y late cuando habla.
- `escucha_kira.py` (lógica pura): escucha permanente mientras la portada está en pantalla. Solo contesta cuando oye
  «Kira» («Kira, ¿qué hora es?», o «Kira» y luego la orden). Lo que oye sin su nombre queda en un borrador en la RAM
  que se borra a los 10 segundos; nunca se guarda ni sale del móvil. No escucha mientras habla, piensa o estás en otra
  pantalla. Se apaga con el botón «Escucha» o en Configuración.
- Conversaciones: las NUEVAS se guardan en el baúl («lo hablamos»); las que Kira ya tenía reconocidas no se duplican.
- Menú claro y sencillo: 8 apartados principales y «Más apartados» para el resto. Las salas inmersivas siguen oscuras.
- Pruebas: `tests/test_escucha.py`, `tests/test_cableado_escucha.py` (micrófono simulado).
- **Mejoras por voz**: «Kira, mejora…», «Kira, aprende a…», «Kira, añade…» (`inicio_kira.pedido_mejora`) abre la
  terminal de mejoras, envía el pedido al laboratorio y lee el resultado en voz alta. Aplicar sigue necesitando dos
  toques: la voz puede pedir, nunca aprobar (así una tele o cualquiera que hable cerca no puede instalar código).

## Programación avanzada, editor, juegos y salas más bonitas (nuevo)
- `curso_avanzado_kira.py`: 16 lecciones avanzadas (clases, herencia, dataclasses, decoradores, generadores, `with`,
  excepciones propias, hilos, asyncio, regex, SQLite, complejidad, grafos, programación dinámica, patrones, pruebas)
  y 10 programas completos (juego de la vida, A*, Huffman, intérprete de expresiones, Vigenère, perceptrón, sudoku,
  máquina de estados, inventario, Markov). Todos se comprueban ejecutándolos. En la terminal: Básico / Avanzado / Códigos.
- `ejecutor_kira.py` + `pantallas_codigo_kira.py`: **editor de código** (menú «Editor de código»): escribir, comprobar,
  ejecutar, guardar y abrir programas. Modo seguro: sin archivos, red ni sistema, lista de módulos permitidos, corta a los
  5 s (también hilos) y recorta la salida. Es una protección contra errores, no una caja fuerte: no ejecutes código ajeno.
- `motor_juegos_kira.py` + `juegos_kira.py`: **motor de juegos 2D** y 5 juegos (Rompeladrillos, Serpiente, Esquiva,
  Saltarín, Pong contra Kira) escritos como programas que se abren y cambian en el editor; plantilla para juegos nuevos.
  Cada fotograma tiene límite de tiempo: un juego colgado se para sin colgar la app.
- `api_modulos_kira.py`: las mejoras ahora pueden guardar sus datos, usar los recuerdos, programar avisos que Kira dice
  en voz alta y añadir juegos (`{"juego nombre": crear(motor)}`). El laboratorio tiene un test fijo nuevo
  (`tests_fijos/test_juegos.py`) que JUEGA esos juegos antes de aprobarlos. Tras actualizar el laboratorio, vuelve a
  sellarlo (`sellar SELLAR NUCLEO`) porque cambió un test fijo.
- `luz3d_kira.py`: las 4 salas 3D con lámparas de colores reales (detectadas solas), degradados, sombras bajo los
  muebles, autoexposición, resplandor, viñeta y luces que parpadean. Sala Hacker con armario de servidores, tira LED,
  planta y silla; búnker con rejilla luminosa en el suelo.
- Pruebas: `test_codigo.py`, `test_cableado_codigo.py`, `test_api_modulos.py`, `test_luz3d.py`.

## Cerebro y oído propios: Kira sin Termux, sin API y sin el reconocedor de Android (nuevo)
- `herramientas_pc/compilar_cerebro_android.sh`: GitHub compila **llama-server** (llama.cpp b11742) para Android
  arm64 en dos versiones (rápida ARMv8.2+dotprod y genérica) y las mete en el APK como `libkira_cerebro*.so`
  (`android.add_libs_arm64_v8a`). Android las deja ejecutables en la carpeta de librerías nativas de la app.
- `cerebro_propio_kira.py`: descarga UNA vez el modelo (Qwen3.5 2B 1,4 GB o 4B 3 GB, licencia Apache 2.0) con
  progreso, comprobación de espacio y reanudación; enciende el motor (prueba el rápido y, si el móvil no puede, el
  genérico) en `127.0.0.1:8080` y lo apaga al cerrar Kira. Se enciende solo al abrir la app.
- Respuestas que **van apareciendo** mientras piensa (streaming) con el cerebro propio y con Claude.
- `oido_kira.py`: **oído propio** con Vosk (`vosk-android`, modelo español de 39 MB): escucha continua, sin pitidos
  y sin internet, en todas las pantallas (se pausa mientras Kira habla o piensa, y en los juegos). Como el
  reconocedor sin conexión puede no conocer «Kira», se acepta por cómo SUENA la primera palabra («quiera…»), pero no
  «quiero» ni «mira». Si no está, Kira usa el reconocedor de Android.
- Pantalla «Cerebro y oído» en el menú. Órdenes: `cerebro propio`, `descarga cerebro ligero|listo`,
  `enciende cerebro`, `apaga cerebro`. Pruebas: `test_cerebro_propio.py`, `test_flujo.py`, `test_oido.py`,
  `test_cableado_cerebro.py`.

## Sin ordenador y en equipo con Claude (nuevo, v2.17)
- **Ya no hace falta el ordenador para las mejoras.** «Kira, aprende a…», «Kira, mejora…» o «Kira, añade…»: Kira la
  programa y la prueba en su **laboratorio del móvil** (`laboratorio_movil_kira.py`): solo módulos seguros (sin
  archivos, red ni sistema), tiempo máximo, el contrato de los módulos, los juegos se juegan 20 s simulados y cada orden
  se prueba con frases de ejemplo. Si el laboratorio del ordenador está conectado, se prueba **también** allí y los dos
  tienen que dar OK. Instalarla sigue siendo **solo con tus dos toques** en «Aplicar». Al instalarla, Kira la apunta en
  su baúl y en la charla sabe que tiene esa orden nueva.
- **Kira y Claude se ponen de acuerdo** (`acuerdo_kira.py`), si están los dos (su cerebro encendido y la clave de
  Claude): propone Kira y revisa Claude; si Claude no está de acuerdo, dice por qué y puede traer su versión (que
  también se prueba), y Kira la acepta o hace otra que resuelva las dos cosas. Como mucho 3 rondas. Te enseñan la
  conversación y decides tú. «cerebro mejoras claude» = propone Claude y revisa Kira. «acuerdo con claude» lo explica;
  «desactiva el acuerdo con claude» (o Configuración) para no gastar a Claude.
- **Programas por voz**: «Kira, escríbeme un programa que…» o «Kira, hazme un juego de…» → lo escribe con lo que ha
  estudiado, lo prueba en modo seguro (los juegos, jugándolos) y te lo deja en el **editor**. No se instala nada.
- **Diseño por voz**: «Kira, diséñame una web para…», «hazme una maqueta de app de…», «crea un videoclip de…» → va al
  ordenador de diseño y lo crea **con lo que ha estudiado del tema**; si está Claude, lo repasa y lo mejora.
- **Estudiar en equipo**: «Kira, estudia …» lee la Wikipedia y, si está Claude, él repasa las fichas, corrige lo que
  esté mal y añade lo que falte (la ficha repasada queda en el baúl).
- Honesto: el laboratorio del móvil corre dentro de la propia app (Android no deja abrir otro Python aparte). Protege
  contra errores y accidentes, pero no es una caja fuerte contra código hecho para saltársela: por eso decides tú.
  Cada revisión de Claude gasta de tu clave. Nada de esto se ha probado aún en tu móvil.
- Pruebas: `tests/test_laboratorio_movil.py`, `tests/test_acuerdo.py`, `tests/test_equipo_voz.py`.

## Kira más ágil y más fácil de leer (nuevo, v2.16)
- **Habla antes y en español**: la voz ya no crea un motor nuevo en cada frase (la librería plyer lo hacía, y en
  inglés). Ahora hay una sola voz de Android (`android_src/org/kira/servicio/VozKira.java`), en español, creada una
  vez. Kira dice la respuesta **frase a frase mientras la piensa** (`HablaEnVivo` en `inicio_kira.py`): empieza a hablar
  con la primera frase, sin esperar a tenerla entera. Y sabe de verdad cuándo ha terminado de hablar (para no
  escucharse a sí misma). Si esa voz no está, usa la de antes.
- **Responde antes**: el cerebro del móvil guarda lo ya leído y solo lee lo nuevo. Antes los recuerdos iban dentro de
  las instrucciones fijas, cambiaban en cada pregunta y le obligaban a releerlo todo; ahora van con la pregunta. Además:
  sin «razonamiento oculto», una sola conversación en el motor (`-np 1`), algo menos de historial y respuestas cortas.
- **Más fluida**: cambio de pantalla al instante (el fundido iba a tirones), 30 fotogramas como máximo, el botón de la
  portada ya no se reconstruye entero en cada fotograma, las salas 3D quietas solo repintan lo que brilla (no toda la
  sala) y la lluvia de código va más ligera. El texto nunca tarda más de 2 s en escribirse.
- **Se lee todo**: letra normal (Roboto) en la interfaz (la de máquina de escribir solo para código), tamaño que
  respeta la letra del sistema pero con tope, y `estilo_kira.ajustar()`: si un texto no cabe, se parte en dos líneas o
  la letra baja un poco (medido sin dibujar, para que las pantallas abran rápido). Menú con tarjetas de colores y
  descripción, paneles de las salas opacos, tarjeta blanca para lo que dice Kira.
- **Pantalla de carga limpia**: solo el fondo de Kira con su botón de neón y, abajo, una línea («Descargando el
  cerebro… 41 % · quedan 4 min», «Despertando el cerebro de Kira…»), una barra y «Entrar ya». El tiempo se calcula con
  la velocidad real de la descarga. Al terminar entra sola y ya puedes hablarle.
- Pruebas: `tests/test_voz.py` (frases, cola de voz, recuerdos fuera de las instrucciones), `tests/test_arranque.py`.
- Honesto: nada de esto se ha probado todavía en tu móvil. La voz nueva necesita una voz en español instalada en
  Android (Ajustes › Texto a voz); si no la hay, Kira lo dirá.

## Kira se mueve y se conecta sola al laboratorio (nuevo, v2.15)
- **Moverse por la app** (`navegar_kira.py`): «Kira, abre la sala hacker», «ve a los juegos», «llévame al editor»,
  «enséñame mis notas», «juega a la serpiente», «atrás», «ve al menú». Por voz funciona desde cualquier pantalla (ya
  no vuelve antes al botón). Antes estas frases llegaban a su IA, que contestaba que no podía moverse.
- **Fuera de la app**: «abre WhatsApp» (cualquier app instalada, por su nombre aunque se oiga mal), «ve al inicio del
  móvil» / «minimízate», «abre los ajustes del wifi / bluetooth / batería…», «busca en internet…», «abre youtube.com»,
  «marca el 600 123 456» (abre el teléfono con el número; **no llama sola**), «vuelve» (desde otra app). Por nombre no
  llama: tendría que leer tus contactos y no lo hace.
- Desde **otra app** (con «Siempre activa»), Android solo deja abrir cosas con el permiso **«Mostrar sobre otras apps»**:
  «Kira, permiso para abrir apps» o Configuración › «Que abra apps aunque esté en segundo plano». Sin él, lo dice.
- Honesto: **no pulsa botones dentro de otras apps** (haría falta el permiso de accesibilidad, que lo ve todo). Abrir
  apps desde segundo plano depende de la versión de Android: no está probado en tu móvil.
- **Pasarela sin líos** (`enlace_lab_kira.py` + `kira_laboratorio/lab_enlace.py`): ya no hay que copiar la IP ni el token.
  1. En el PC: doble clic en `kira_laboratorio/Arrancar laboratorio.bat` (Windows; si pregunta el cortafuegos, «Permitir»).
     `Arrancar con Windows.bat` hace que arranque solo al encender el PC.
  2. En el móvil: «Kira, conéctate al ordenador». Kira lo encuentra en la WiFi (el laboratorio tiene un «faro» UDP en el
     puerto 8766; si el router lo bloquea, recorre la red).
  3. Le dices el código de 6 cifras que sale en la ventana del PC (de palabra o escrito). Kira guarda la conexión.
  Después se conecta sola y, si el PC cambia de dirección, lo vuelve a encontrar con el mismo token cuando lo necesita.
  Seguridad: el faro nunca da el token; el código caduca a los 10 min, 5 intentos por código y, tras 3 códigos
  fallados, se cierra hasta reiniciar el laboratorio. «Kira, desconéctate del laboratorio» lo olvida; borrar
  `token_lab.txt` en el PC echa a todos los móviles.
- Pruebas: `tests/test_navegar.py`, `tests/test_enlace.py` (laboratorio real en la máquina, faro, código, cambio de dirección).
- El APK lleva ahora `<queries>` (para ver las apps instaladas) y el permiso `SYSTEM_ALERT_WINDOW`; la compilación lo
  comprueba en el manifiesto. Como cambió código del laboratorio, vuelve a sellarlo (`python kira_master.py` →
  `sellar SELLAR NUCLEO`).

## Ingeniería informática avanzada (nuevo, v2.14)
- `recetas_ingenieria_kira.py`: **57 recetas** de algoritmos y programación avanzada, cada una un módulo completo de Kira
  que se prueba solo. Áreas: estructuras de datos (Union-Find, trie, montículo, caché LRU, Fenwick, árbol de segmentos,
  Bloom, AVL, árbol B), técnicas (ventana deslizante, Kadane, búsqueda binaria sobre la respuesta, Newton), grafos
  (Dijkstra, Bellman-Ford, Floyd-Warshall, Kruskal, orden topológico, Tarjan, flujo máximo, emparejamiento), cadenas
  (KMP, Aho-Corasick, Levenshtein, diff, array de sufijos), programación dinámica (mochila, LIS, monedas, viajante con
  máscaras de bits), matemáticas (criba, Miller-Rabin y Pollard, RSA didáctico, FFT, exponenciación rápida, Gauss),
  sistemas operativos (planificador de CPU, reemplazo de páginas, banquero, productor-consumidor, filósofos),
  distribuidos (relojes vectoriales, hash consistente, limitador de peticiones), compiladores (mini compilador a
  bytecode con máquina de pila, expresiones regulares con autómatas de Thompson y **KiraLang**, un lenguaje propio con
  funciones y recursión), compresión (LZW, Burrows-Wheeler, Hamming y CRC-32), IA (minimax alfa-beta, recocido
  simulado, algoritmo genético, k-means++, red neuronal con retropropagación, regresión) y lógica (N reinas, SAT/DPLL,
  ordenaciones comparadas).
- Cuando Kira programa una mejora, recibe la receta más parecida (o solo su idea y su coste si el código es largo
  para el modelo del móvil).
- **Teoría**: 49 fichas (complejidad, P y NP, memoria y CPU, procesos e hilos, memoria virtual, redes, TLS, bases de
  datos, CAP, Raft, compiladores, tipos, SOLID, patrones, pruebas, git, CI/CD, seguridad DEFENSIVA, LLM, cuantización…).
  «estudia ingeniería» las guarda en el baúl **sin internet** y desde ahí Kira responde sola («qué es el teorema CAP»,
  «cómo funciona Dijkstra»). «aprende sola» también lo hace la primera vez.
- Órdenes: «recetas de ingeniería», «recetas de grafos», «receta dijkstra», «abre la receta kmp» (se abre en el editor
  con sus pruebas: pulsa «Ejecutar»). En la terminal de la Sala Hacker hay un nivel nuevo: **Ingeniería**.
- Pruebas: `tests/test_ingenieria.py` (cada receta pasa el laboratorio de verdad y se ejecuta en el editor seguro con
  sus pruebas; el baúl responde; la terminal y el editor funcionan) y `tests/test_saber.py`.
- Honesto: el RSA es para aprender (claves de juguete, sin relleno). No probado aún en el móvil real: cuánto tarda en
  abrirse la lista larga de lecciones.

## Lector de capturas: texto y código, sin internet (nuevo)
- `lector_kira.py`: Tesseract (Tesseract4Android 4.9.0, Apache 2.0, desde JitPack) dentro del APK; idiomas español e
  inglés (`tessdata_fast`) se descargan una vez. Para CÓDIGO reconstruye la sangría con la posición de cada palabra
  (TSV) y las líneas en blanco con el interlineado: en las pruebas con capturas reales de un editor, el código sale
  idéntico y se puede ejecutar.
- Órdenes: `lee la última captura`, `abre lo leído en el editor`, `guarda lo leído`, `explícame lo leído`.
  Pantalla «Lector» en el menú. Permiso nuevo: `READ_MEDIA_IMAGES` (para ver tus capturas).
- La compilación en GitHub ahora COMPRUEBA qué lleva el APK (cerebro, oído, lector) y lo apunta en las notas.
