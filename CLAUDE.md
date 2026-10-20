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
- **Pendiente:**
  - `recetas_ingenieria_kira.py`: algoritmos y estructuras de datos, en el mismo formato que `recetas_graficos_kira.py`, con su `"prueba"`. `saber_mejoras_kira` lo carga solo si existe y `tests/test_saber.py` lo verifica;
  - motor local para generar imágenes (stable-diffusion.cpp), siendo honesto sobre lo lento que es en un móvil;
  - nada de lo de cámara, ojos, pantalla y siempre activa se ha confirmado todavía en el móvil real.
