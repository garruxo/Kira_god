# Kira_god: contexto para Claude

Lee esto antes de empezar. El dueño del proyecto habla **español**: contesta siempre en español, claro y sin tecnicismos innecesarios.

## Qué es
Kira es un asistente personal para Android, hecho con Python y Kivy y compilado como APK. Tiene:
- su propio cerebro dentro del móvil: llama.cpp compilado como `libkira_cerebro*.so`, con modelos Qwen3.5 2B/4B y «ojos» (mmproj);
- su propio oído: Vosk, escucha sin parar y solo responde cuando oye «Kira». Lo oído sin su nombre se borra a los 15 s;
- lector de capturas: Tesseract;
- ver la pantalla, con lista de apps privadas;
- cámara: Camera2, la foto se borra al momento;
- servicio «siempre activa»;
- salas 3D, juegos (`motor_juegos_kira.py`), editor de código y estudio con baúl de recuerdos;
- mejoras que se prueban en un laboratorio.

## Reglas que el dueño pidió (no romperlas)
- **Las mejoras nunca se aplican solas.** La voz puede pedirlas, pero aplicar exige su aprobación (dos toques).
- **Laboratorio (cambiado por el dueño en la v2.17):** ya NO hace falta el ordenador. Las mejoras se prueban en el laboratorio del móvil (`laboratorio_movil_kira.py`: lista segura de módulos, sin archivos/red/sistema, tiempo máximo, contrato, juegos y prueba de uso) y, si el del PC está conectado, también allí (`LaboratorioDoble`: los dos tienen que dar OK). El del PC (`kira_laboratorio/`) sigue siendo opcional y nunca envía código al móvil. Si cambias `tests_fijos/` o el código del laboratorio del PC, recuérdale volver a sellar (`python kira_master.py` → `sellar SELLAR NUCLEO`).
- **Kira y Claude en equipo** (`acuerdo_kira.py`): si están los dos (cerebro del móvil + clave), uno propone y el otro revisa hasta ponerse de acuerdo en mejoras, programas, diseños y estudio. **Cambiado por el dueño en la v2.26: viene APAGADO** (las mejoras, solo con su criterio y el de Kira: el laboratorio y sus dos toques). Se enciende con «activa el acuerdo con claude» o en Configuración; lo guardado antes de la v2.26 no cuenta (`Ajuste.VERSION`). Aunque esté encendido, la opinión de Claude nunca bloquea una mejora que pasa el laboratorio.
- **La sala de ciberseguridad es solo defensiva.**
- **Termux NO para hablar con Kira.** Solo se acepta para el laboratorio en el móvil.
- **Nada de reconocedor de Android** (pitidos) si hay oído propio.
- **Privacidad:** capturas y fotos se borran tras leerlas; el borrador de escucha vive solo en la RAM.
- Sé sincero sobre lo que no funciona o no se ha probado en el móvil.

## Cómo se trabaja
- **Pruebas:** `for t in tests/test_*.py; do python3 $t || echo FALLA $t; done`. Todas deben pasar antes de subir nada.
- **Compilar el APK:** cada push a `main` lanza `.github/workflows/compilar_apk.yml`.
  - Seguimiento: `gh run list -R garruxo/Kira_god`.
  - El APK sale en el artefacto **kira-apk**, un .zip. El dueño lo descarga, lo extrae con la app Archivos y pulsa Actualizar.
  - El repositorio debe estar en **público** para compilar; en privado falla por facturación.
- **Versión:** subir `version` en `buildozer.spec` en cada entrega.
- **Código Java:** va en `android_src/` (`ServicioKira`, `CamaraKira`). Usa clases anónimas, sin lambdas, y compila con `--release 8`.
- **Clases de Java desde Python:** búscalas con `autoclass` en el hilo principal, no en hilos secundarios.

## Estado y pendiente
- **Hecho hasta la v2.13:**
  - pantalla «Preparando a Kira» al abrir;
  - el cerebro se reutiliza si sigue cargado;
  - cámara y ojos;
  - líneas y polígonos en el motor;
  - 17 recetas de gráficos en `recetas_graficos_kira.py`;
  - `saber_mejoras_kira.py` da la receta más parecida y lo estudiado al cerebro cuando programa una mejora.
- **Hecho en la v2.14 (ingeniería informática avanzada):**
  - `recetas_ingenieria_kira.py`: 57 recetas probadas en 12 áreas (estructuras de datos, técnicas, grafos, cadenas, programación dinámica, matemáticas, sistemas operativos, distribuidos, compiladores, compresión, IA, búsqueda/lógica) y 49 fichas de teoría (`CONCEPTOS`);
  - cada receta: su `"prueba"`, `area` y `complejidad`; `tests/test_ingenieria.py` las pasa por el laboratorio real (`servidor_lab.probar`) y por el editor seguro;
  - «estudia ingeniería» guarda las fichas en el baúl sin internet (y «aprende sola» lo hace la primera vez); Kira las responde sola;
  - nivel «Ingeniería» en la terminal y en los ejemplos del editor; «recetas de ingeniería» / «recetas de grafos»; «abre la receta X» la abre con sus pruebas;
  - la búsqueda de recetas ignora palabras vacías y, en el baúl, a igualdad de puntos gana el recuerdo cuyo tema nombra lo preguntado.
- **Hecho en la v2.15 (moverse y pasarela sin líos):**
  - `navegar_kira.py`: pantallas por voz/texto («abre la sala hacker», «juega a la serpiente», «atrás») y fuera de la app (abrir apps por nombre, inicio del móvil, ajustes, web, marcar sin llamar). La interfaz lo intercepta antes de la IA; el núcleo hace lo de fuera por consola;
  - desde segundo plano solo con el permiso «Mostrar sobre otras apps» (`SYSTEM_ALERT_WINDOW`); `<queries>` del lanzador en `p4a.extra_args` (`--extra-manifest-xml`);
  - `enlace_lab_kira.py` (móvil) + `kira_laboratorio/lab_enlace.py` (PC): faro UDP 8766, código de 6 cifras con límites, `/hola`, `/emparejar`, `/emparejar/pedir`; `PasarelaCliente` relee `pasarela.json` y `reubicar()` busca el PC si cambia de IP;
  - `iniciar_laboratorio.py` escucha por la WiFi por defecto; `Arrancar laboratorio.bat` y `Arrancar con Windows.bat` (CRLF, `.gitattributes`);
  - pruebas: `tests/test_navegar.py`, `tests/test_enlace.py`. Se cambió código del laboratorio: hay que volver a sellar.
- **Hecho en la v2.16 (rapidez y legibilidad):**
  - voz propia `android_src/org/kira/servicio/VozKira.java` (un motor, es-ES, cola) usada por `inicio_kira.Voz` (plyer de reserva); `HablaEnVivo` dice la respuesta frase a frase mientras llega;
  - cerebro local: recuerdos en el último mensaje (no en el system, para reutilizar la caché), `cache_prompt`, `enable_thinking: False`, `-np 1`, 6 turnos;
  - `estilo_kira.py` (`tam`, `ajustar`, `fondo_redondeado`): Roboto, letra con tope, textos que caben; menú en tarjetas; `NoTransition`; `maxfps` 30; portada y salas 3D más ligeras;
  - pantalla de carga: fondo de Kira + barra abajo con texto y tiempo restante (`arranque_kira.Preparacion.progreso`);
  - pruebas: `tests/test_voz.py`. Capturas con Kivy real en el contenedor: compilado desde el código fuente (pip está bloqueado).
- **Hecho en la v2.17 (sin ordenador y en equipo con Claude):**
  - `laboratorio_movil_kira.py` (prueba dentro de la app) + `LaboratorioDoble`; la voz ya no exige el PC; aplicar sigue con dos toques; al instalar, Kira apunta la habilidad en el baúl y la charla conoce sus órdenes nuevas;
  - `acuerdo_kira.negociar`: propone Kira y revisa Claude (con «cerebro mejoras claude», al revés), hasta 3 rondas; Claude puede traer su versión, que también se prueba;
  - `programar_kira.py`: «escríbeme un programa que…» / «hazme un juego de…» → probado en modo seguro → editor (no instala nada);
  - `diseno_kira.pedido_diseno`: «diséñame una web / maqueta de app / videoclip…» desde cualquier pantalla; el diseño usa lo estudiado y Claude lo repasa;
  - «estudia X»: Claude repasa las fichas de Wikipedia y deja una ficha corregida en el baúl;
  - el tope de tiempo (editor y laboratorio del móvil) ya no afecta a otros hilos de Kira;
  - pruebas: `tests/test_acuerdo.py`, `tests/test_laboratorio_movil.py`, `tests/test_equipo_voz.py`.
- **Hecho en la v2.18 (pintor e internet):**
  - `pintor_kira.py` + `pantalla_pintor_kira.py`: stable-diffusion.cpp (`sd-cli`, versión `master-929-3f8527a`) como `libkira_pintor(_dp).so` (`herramientas_pc/compilar_pintor_android.sh`, caché propia en el workflow); pinceles SDXS-512 Q8 (rápido) y tiny-sd-turbo Q8 (realista) de Hugging Face, ampliador Real-ESRGAN ×4; prompt en inglés con el cerebro; progreso leyendo la salida; vista previa `--preview proj`; aparta el cerebro si falta RAM; `GaleriaKira.java` (MediaStore);
  - `internet_kira.py` + `pantalla_internet_kira.py`: DuckDuckGo HTML (+lite), Wikipedia, Stack Overflow (gzip), GitHub; HTML→texto con el código aparte, PDF sencillo con zlib; órdenes en el núcleo (`_orden_internet`, `resumir_pagina`, `guardar_pagina`, `estudiar_en_internet`); «busca en internet» ya no abre el navegador (solo «busca en google»);
  - `descargas_kira.py` (descargas con reanudación); menú con «Pintor» e «Internet»;
  - pruebas: `tests/test_pintor.py`, `tests/test_internet.py`; prueba real en GitHub: `.github/workflows/probar_pintor.yml` (artefacto «pruebas-pintor»).
- **v2.19–2.21 (arreglos tras probar en el móvil):** pincel realista con TAESD aparte; caja negra de cierres (`main.py`: faulthandler + `ExceptionManager` que esquiva errores de Python y los anota en `kira_errores.log`; la portada enseña el motivo del último cierre); `VozKira` se crea en el hilo principal de Android; «implementa este código» (`inicio_kira.pedido_con_codigo` → `PanelControl.probar_codigo`: un módulo con `registrar()` se prueba tal cual, un programa se convierte); al decir «Kira» en otra pantalla contesta AHÍ con un bocadillo flotante (`bocadillo()` en la interfaz), ya no lleva a la portada.
- **Hecho en la v2.22:** «juego realista» (`juego_realista_kira.py`: plan → `pintar_dibujos` en el núcleo → programa con `imagen()`; `sprites_kira.py`: PNG en Python puro, fondo transparente; `dibujos_de` lee «sprites»/«dibujos» del código; «pinta los dibujos del juego»); el motor tiene `FORMAS` con «imagen» (se cambió `tests_fijos/test_juegos.py`: hay que volver a sellar); siempre activa por defecto + `ServicioKira.pedirSinAhorro` (REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, se pide una vez). Pruebas: `tests/test_juego_realista.py`.
- **Hecho en la v2.25 (saber avanzado y experimentos):** `saber_avanzado_kira.py` (18 recetas de programación avanzada y diseño con pruebas + 24 fichas; «estudia diseño» / «estudia programación avanzada», `FUENTE_AVANZADO`; nivel «Diseño» en el curso); `experimentos_kira.py` + `KiraGodCore.experimentar` (hipótesis → `generar_programa(..., con_recetas=False)` → `probar_programa` → puntuar → acuerdo con Claude → `Cuaderno` en `experimentos.json` + lección en el baúl); voz: `experimento_por_voz` (se mira ANTES que `pedido_programa`). Pruebas: `tests/test_saber_avanzado.py`, `tests/test_experimentos.py`.
- **v2.26 (firma fija):** cada compilación de GitHub creaba una firma nueva y Android no dejaba actualizar (había que desinstalar). Ahora `compilar_apk.yml` copia `herramientas_pc/firma/kira_debug.keystore` (o el secreto `KIRA_KEYSTORE_B64`) a `~/.android/debug.keystore` y, tras compilar, vuelve a firmar el APK con `apksigner sign` (Gradle firmaba con otra de usar y tirar) y lo comprueba. **No borres ni cambies esa firma**: obligaría a desinstalar otra vez. El paso de la firma antigua a esta exige desinstalar UNA última vez. También en la v2.26: el acuerdo con Claude viene apagado y, si el laboratorio del PC rechaza lo que el del móvil aprueba, se dice claro (resellar o «desconéctate del ordenador»).
- **Hecho en la v2.27:** redes neuronales (`saber_redes_kira.py`, sumado a `saber_avanzado_kira`; `fichas("redes")`; «estudia redes neuronales»); biblioteca de PDF (`pdf_kira.py`, `pantalla_pdf_kira.py`, `KiraGodCore.orden_pdf`/`pdfs`, pypdf 5.9.0 metido DENTRO del proyecto por `herramientas_pc/incluir_pypdf.py` en el workflow (como plyer; en requirements no aparecía en el APK — v2.28), `ArchivosKira.java`, `android.manifest.intent_filters` para compartir con Kira); «para»/«cancela» (`escucha_kira.orden_control`, el oído no se pausa al hablar/pensar, `KiraGodCore.cancelar/nueva_tarea/cancelado`, `leer_sse(parar=…)`); `cierres_kira.py` (trabajo en curso con `@_con_trabajo`, motivo de cierre de Android con `ServicioKira.ultimoCierre`, mejora pendiente guardada en `mejora_pendiente.json`); WakeLock en `ServicioKira`. Pruebas: `tests/test_control_voz.py`, `tests/test_pdf.py`.
- **Pendiente:**
  - nada de lo de moverse fuera de la app ni el faro se ha probado en el móvil real ni en la WiFi de casa;
  - pulsar botones dentro de otras apps (necesitaría servicio de accesibilidad: pedir permiso al dueño antes);
  - el pintor y el buscador no se han probado en el móvil real (el pintor sí con modelos reales en el PC de GitHub); pintar en el ordenador del laboratorio con modelos grandes (SDXL/Flux) si tiene GPU;
  - nada de lo de cámara, ojos, pantalla y siempre activa se ha confirmado todavía en el móvil real;
  - la voz nueva y la rapidez (v2.16) no se han medido en el móvil real;
  - el laboratorio del móvil y el acuerdo con Claude (v2.17) no se han probado en el móvil real; el laboratorio del móvil corre dentro de la app: protege contra errores y accidentes, no es una caja fuerte;
  - los experimentos (v2.25) no se han probado con el cerebro real del móvil (solo con un cerebro simulado);
  - v2.27 sin probar en el móvil: que pypdf entre bien en el APK, compartir con Kira, Descargas, el WakeLock, el motivo de cierre y si el eco de su voz dispara «para» por error.
