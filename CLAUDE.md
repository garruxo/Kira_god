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
- **El laboratorio** (`kira_laboratorio/`) es un búnker: solo prueba y devuelve un veredicto, nunca envía código al móvil. Si cambias `tests_fijos/`, recuérdale volver a sellar (`python kira_master.py` → `sellar SELLAR NUCLEO`).
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
- **Pendiente:**
  - nada de lo de moverse fuera de la app ni el faro se ha probado en el móvil real ni en la WiFi de casa;
  - pulsar botones dentro de otras apps (necesitaría servicio de accesibilidad: pedir permiso al dueño antes);
  - motor local para generar imágenes (stable-diffusion.cpp), siendo honesto sobre lo lento que es en un móvil;
  - nada de lo de cámara, ojos, pantalla y siempre activa se ha confirmado todavía en el móvil real;
  - la voz nueva y la rapidez (v2.16) no se han medido en el móvil real.
