# -*- coding: utf-8 -*-
"""
bitacora_kira.py - La MEMORIA DE TRABAJO de Kira: qué hemos construido, dónde está cada código, cómo se instala y
arranca cada cosa, y qué ha fallado. Sirve para que Kira diagnostique un fallo y proponga cómo corregirlo.

Lógica PURA (sin Kivy ni red). Tres partes:
  1. PASOS: guías de instalación/arranque (ffmpeg, laboratorio, pasarela, clave, APK…), con dónde y cómo.
  2. MAPA: qué hace cada archivo del proyecto (para saber qué tocar).
  3. REGISTRO: errores reales que han pasado (sin claves ni tokens) + notas tuyas. diagnosticar() los relaciona con
     su arreglo conocido. texto_para_mejoras() resume todo para que el generador de mejoras lo tenga en cuenta.
Kira NO se repara sola sin ti: diagnostica, explica y, si hace falta código, prepara la mejora para que la apruebes.
"""
import json
import os
import re
import threading
import time
import unicodedata

PASOS = [
    {"id": "ffmpeg", "titulo": "Instalar ffmpeg (necesario para vídeo y audio)", "claves": ("ffmpeg", "crear video", "mezcla"),
     "donde": "En el PC del laboratorio (el móvil no lo trae).",
     "como": ["Opción fácil (cualquier sistema): pip install imageio-ffmpeg  (Kira lo encuentra solo).",
              "Windows: winget install Gyan.FFmpeg  y abre una terminal nueva.",
              "Ubuntu / WSL: sudo apt update && sudo apt install -y ffmpeg",
              "Termux: pkg install ffmpeg",
              "O, si arrancaste el laboratorio con --permitir-instalar: Taller > Instalar en el PC (imageio-ffmpeg)."],
     "comprobar": "ffmpeg -version   (o en Kira: «capacidades» debe decir que hay ffmpeg)",
     "archivos": ["motor_video_kira.py (ffmpeg_ruta)", "ffmpeg_seguro.py", "kira_laboratorio/lab_instalar.py"]},
    {"id": "laboratorio", "titulo": "Arrancar el laboratorio en el PC", "claves": ("laboratorio", "lab", "servidor", "pasarela", "no alcanzable"),
     "donde": "Carpeta kira_laboratorio del PC, con la carpeta Kira_god al lado (o KIRA_GOD_DIR).",
     "como": ["pip install pillow  (y ffmpeg, ver «Instalar ffmpeg»).",
              "Define un token largo: Windows  set KIRA_LAB_TOKEN=tu-token-largo-de-16-o-mas  |  Linux  export KIRA_LAB_TOKEN=...",
              "Solo este PC: python servidor_lab.py   |   Desde el móvil por WiFi: python servidor_lab.py --host 0.0.0.0",
              "Opcional: --permitir-instalar para que el Taller pueda pedir paquetes de la lista blanca.",
              "Si Windows pregunta por el cortafuegos, permite redes privadas (puerto 8765)."],
     "comprobar": "En el navegador del PC: http://127.0.0.1:8765/salud  -> {\"ok\": true}",
     "archivos": ["kira_laboratorio/servidor_lab.py", "kira_laboratorio/lab_video.py"]},
    {"id": "pasarela", "titulo": "Conectar el móvil con el laboratorio (pasarela.json)", "claves": ("pasarela", "token", "401", "sin configurar", "conectar"),
     "donde": "Archivo pasarela.json en la carpeta de datos de Kira en el móvil.",
     "como": ["Averigua la IP del PC: Windows  ipconfig  |  Linux  ip addr  (ej. 192.168.1.50).",
              "En Kira (Configuración / Pasarela) pon url http://IP_DEL_PC:8765 y el MISMO token que en el PC.",
              "Móvil y PC en la misma WiFi."],
     "comprobar": "Taller > Actualizar: debe decir «laboratorio: conectado».",
     "archivos": ["pasarela_cliente.py", "video_cliente_kira.py"]},
    {"id": "clave", "titulo": "Clave de la API (para que Kira programe y charle)", "claves": ("clave", "api", "falta la clave", "modelo"),
     "donde": "En Kira, se guarda en api_key.txt dentro de sus datos (nunca en el código).",
     "como": ["Escribe en Kira: config clave: TU_CLAVE", "Si la API responde 404, revisa el modelo en modelo.txt (por defecto claude-sonnet-5-5)."],
     "comprobar": "«estado» debe decir clave guardada.", "archivos": ["kira_god.py (_leer_clave, _llamar_api)"]},
    {"id": "apk", "titulo": "Compilar el APK en tu PC (buildozer en WSL, Ubuntu 24.04)", "claves": ("apk", "buildozer", "compilar", "zlib", "android", "externally-managed", "pep 668"),
     "donde": "Ubuntu 24.04 (WSL) en el PC, con Kira_god copiada a tu carpeta de Linux (~), NO en /mnt/c (es lentísimo).",
     "como": ["sudo apt update && sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv python3-virtualenv autoconf "
              "libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libltdl-dev libssl-dev automake autopoint gettext",
              "python3 -m venv ~/venv_kira && source ~/venv_kira/bin/activate   (en 24.04 «pip install --user» está bloqueado)",
              "pip install buildozer setuptools cython==0.29.34",
              "cp -r /mnt/c/Users/TU_USUARIO/Desktop/Kira_god ~/ && cd ~/Kira_god",
              "python herramientas_pc/comprobar_antes_de_compilar.py   y luego   buildozer -v android debug   (la 1ª vez, horas)",
              "El APK queda en bin/."],
     "comprobar": "ls bin/*.apk", "archivos": ["buildozer.spec", "main.py", "herramientas_pc/comprobar_antes_de_compilar.py"]},
    {"id": "video_movil", "titulo": "Ver vídeos dentro de Kira en el móvil", "claves": ("reproductor", "ffpyplayer", "ver video", "cine"),
     "donde": "buildozer.spec (requirements).",
     "como": ["Añade ffpyplayer a requirements y recompila (pesado y no probado).",
              "Mientras tanto: los MP4 se copian a Descargas y se abren con la galería del móvil."],
     "comprobar": "Cine > un vídeo: ya no sale «no incluye un reproductor de vídeo».", "archivos": ["sala_diseno_kira.py (reproductor)"]},
    {"id": "permisos", "titulo": "Permisos de archivos y micrófono en el móvil", "claves": ("permiso", "permission", "micro", "archivos"),
     "donde": "Ajustes de Android > Apps > Kira > Permisos.",
     "como": ["Concede Música y audio, Fotos y vídeos y Micrófono.", "Vuelve a pulsar «Buscar en el móvil» en la mediateca."],
     "comprobar": "La mediateca encuentra archivos.", "archivos": ["buildozer.spec (android.permissions)", "diseno_kira.py (pedir_permisos_medios)"]},
    {"id": "modulos", "titulo": "Dónde viven las mejoras y cómo deshacerlas", "claves": ("modulo", "mejora", "revertir", "no cargo", "fallo el modulo"),
     "donde": "Carpeta modulos/ dentro de los datos de Kira (con copias de seguridad al aplicar).",
     "como": ["«recargar modulos» vuelve a cargarlos.", "Un módulo roto se puede rechazar/revertir desde Mejoras, o pedir a Kira que lo "
              "arregle: «mejorar arregla el módulo NOMBRE: ERROR».", "Nada se aplica sin tu doble confirmación."],
     "comprobar": "«estado»: comandos de módulos cargados y fallos.", "archivos": ["pasarela_cliente.py (Promotor)", "kira_god.py (cargar_modulos)"]},
    {"id": "mezcla_editor", "titulo": "Usar la mesa de mezcla y el editor de vídeo", "claves": ("mesa de mezcla", "mezcla", "editor", "cortar", "unir", "faders"),
     "donde": "Menú > Mesa de mezcla / Editor de vídeo. El trabajo pesado lo hace ffmpeg (aquí o en el PC).",
     "como": ["Primero añade audios y vídeos a la mediateca (Sala de Diseño > Mediateca > Buscar en el móvil).",
              "Necesita ffmpeg: en el móvil no viene, así que arranca el laboratorio en el PC (ver «Arrancar el laboratorio»).",
              "Los resultados se guardan en la mediateca como «creados» y se intentan copiar a Descargas."],
     "comprobar": "Taller: «Mesa de mezcla» y «Editor de vídeo» salen con [OK].", "archivos": ["audio_kira.py", "editor_kira.py", "sala_av_kira.py"]},
    {"id": "terminal_linux", "titulo": "Los comandos de Ubuntu van en la ventana de Ubuntu, no en PowerShell", "claves": ("powershell", "cmdlet", "no se reconoce", "separador de instrucciones", "ps c:"),
     "donde": "Si la línea empieza por  PS C:\\Users\\...>  estás en PowerShell de Windows. Los comandos apt, python3, source, buildozer son de Linux.",
     "como": ["En PowerShell escribe  wsl -l -v  para ver si tienes Ubuntu instalado (y qué versión).",
              "Entra en Ubuntu escribiendo  wsl  (o abre «Ubuntu» desde el menú Inicio). La línea pasa a ser algo como  garru@PC:~$",
              "Solo entonces pega los comandos, de uno en uno (cada línea completa, sin la barra \\ del final).",
              "Para la revisión previa en Windows: abre la carpeta Kira_god en el Explorador, escribe  powershell  en la barra de "
              "direcciones y pulsa Enter (se abre ya dentro). O busca dónde está:  Get-ChildItem $HOME -Recurse -Filter buildozer.spec",
              "buildozer instalado en el Python de Windows NO compila Android: compila en Ubuntu (wsl) o en GitHub."],
     "comprobar": "La línea empieza por  tu_usuario@...:~$  y  lsb_release -a  dice Ubuntu.", "archivos": ["COMPILAR_PACKARD_BELL.md"]},
    {"id": "error_buildozer", "titulo": "Buildozer falló: encontrar el error de verdad", "claves": ("buildozer failed", "failed to execute the last command", "command failed", "error might be hidden"),
     "donde": "Ubuntu, carpeta ~/Kira_god. Lo que sale al final (# ENVIRONMENT, PATH…) NO es el error: el error está ANTES.",
     "como": ["Quita del PATH las carpetas de Windows (suelen romperlo):  export PATH=$(echo \"$PATH\" | tr ':' '\\n' | grep -v '^/mnt/' | paste -sd:)",
              "Vuelve a lanzar guardando el registro (no empieza de cero: lo ya compilado se reutiliza):  buildozer -v android debug 2>&1 | tee compilacion.log",
              "Si falla otra vez, enseña el error real:  grep -B 30 'Command failed' compilacion.log | head -n 40"],
     "comprobar": "La compilación pasa del punto donde se paró.", "archivos": ["buildozer.spec"]},
    {"id": "libffi_ltdl", "titulo": "Buildozer: libffi falla con LT_SYS_SYMBOL_USCORE (falta libltdl-dev)", "claves": ("lt_sys_symbol_uscore", "libffi", "autoreconf", "possibly undefined macro"),
     "donde": "Ubuntu (WSL) o GitHub. Falta un paquete del sistema que usa autoconf para preparar libffi.",
     "como": ["Instálalo:  sudo apt install -y libltdl-dev",
              "Borra lo que quedó a medias de libffi:  rm -rf .buildozer/android/platform/build-*/build/other_builds/libffi*",
              "Relanza:  buildozer -v android debug 2>&1 | tee compilacion.log"],
     "comprobar": "En el registro aparece «Building libffi» y sigue adelante sin «autoreconf: error».",
     "archivos": ["buildozer.spec", ".github/workflows/compilar_apk.yml"]},
    {"id": "p4a_rueda", "titulo": "Buildozer: «…android…whl is not a supported wheel on this platform»", "claves": ("not a supported wheel", "android_24", "charset_normalizer", "python modules with pip"),
     "donde": "buildozer.spec. Es un fallo de la versión «master» de python-for-android al instalar paquetes de Python.",
     "como": ["En buildozer.spec deja la línea:  p4a.branch = develop",
              "Borra la copia vieja de python-for-android para que baje la nueva:  rm -rf .buildozer/android/platform/python-for-android",
              "Relanza:  buildozer -v android debug 2>&1 | tee compilacion.log"],
     "comprobar": "Pasa de «Installing Python modules with pip» sin el error del .whl.",
     "archivos": ["buildozer.spec"]},
    {"id": "pip_roto", "titulo": "Buildozer: el pip interno quedó a medias (ImportError de pip._internal)", "claves": ("pip._internal", "builddependencyinstallerror", "pip install -u pip", "cannot import name"),
     "donde": "Ubuntu, ~/Kira_god. Es el entorno de Python que buildozer crea para compilar; si una actualización de pip se corta, queda mezclado.",
     "como": ["Bórralo (buildozer lo vuelve a crear solo; no se pierde lo ya compilado):  rm -rf .buildozer/android/platform/build-arm64-v8a/build/venv",
              "Limpia el PATH de Windows:  export PATH=$(echo \"$PATH\" | tr ':' '\\n' | grep -v '^/mnt/' | paste -sd:)",
              "Relanza:  buildozer -v android debug 2>&1 | tee compilacion.log",
              "Si vuelve a pasar: mete plyer dentro del proyecto (python herramientas_pc/incluir_plyer.py) y deja en buildozer.spec "
              "requirements = python3,kivy,pyjnius  — así ese pip interno ya no se usa."],
     "comprobar": "La compilación pasa del paso «pip install -U pip».", "archivos": ["herramientas_pc/incluir_plyer.py", "buildozer.spec"]},
    {"id": "cerebro_local", "titulo": "Cerebro local: Kira sin internet ni API (llama.cpp en Termux)", "claves": ("cerebro local", "modelo local", "llama", "termux", "sin api", "independiente", "sin internet"),
     "donde": "En el móvil de Kira, dentro de Termux (de F-Droid). Guía completa: CEREBRO_LOCAL.md.",
     "como": ["Termux: pkg install -y git cmake clang wget  y compila llama.cpp (git clone https://github.com/ggml-org/llama.cpp; cmake -B build; cmake --build build --config Release -j4).",
              "Descarga un modelo GGUF Instruct Q4_K_M de 2-4B (p. ej. Qwen 3.5 4B) a ~/kira.gguf.",
              "Enciéndelo:  cd ~/llama.cpp && ./build/bin/llama-server -m ~/kira.gguf -c 4096 --host 127.0.0.1 --port 8080",
              "Wakelock y batería «Sin restricciones» para Termux. En Kira:  cerebro  (debe decir ENCENDIDO) y  cerebro auto."],
     "comprobar": "En Kira, «cerebro» dice «Modelo local: ENCENDIDO».", "archivos": ["cerebro_ia_kira.py", "CEREBRO_LOCAL.md"]},
    {"id": "nube", "titulo": "Compilar el APK en la nube (recomendado para un PC antiguo)", "claves": ("nube", "github", "actions", "pc antiguo", "packard", "lento", "sin ram"),
     "donde": "GitHub (gratis): el APK se compila en sus servidores y tú solo lo descargas. Tu PC solo sube la carpeta.",
     "como": ["Crea una cuenta en github.com y un repositorio nuevo (privado) llamado kira_god.",
              "Sube la carpeta Kira_god tal cual (incluye .github/workflows/compilar_apk.yml).",
              "En el repositorio: pestaña Actions > «Compilar APK de Kira» > Run workflow (o se lanza solo al subir cambios).",
              "Tarda ~20-40 min la primera vez. Al terminar: entra en la ejecución > Artifacts > kira-apk (un .zip con el APK)."],
     "comprobar": "En Actions la ejecución sale en verde y hay un artefacto kira-apk.", "archivos": [".github/workflows/compilar_apk.yml", "buildozer.spec"]},
    {"id": "wsl_antiguo", "titulo": "Instalar Ubuntu (WSL) en un PC antiguo", "claves": ("wsl", "virtualizacion", "virtualization", "hyper-v", "0x80370102", "ubuntu"),
     "donde": "Windows del PC. WSL 2 necesita Windows 10 (2004 o más) u 11 y la virtualización activada en la BIOS.",
     "como": ["PowerShell como administrador: wsl --install -d Ubuntu-24.04  y reinicia (NO la última: 26.04 necesita la rama "
              "«develop» de buildozer y otra API).",
              "Si sale el error 0x80370102: entra en la BIOS (F2 al encender en Packard Bell) y activa «Intel Virtualization Technology».",
              "Si tu CPU o tu Windows no lo permiten, usa WSL 1:  wsl --set-default-version 1  (más lento, pero sirve), "
              "o mejor compila en la nube (ver «Compilar el APK en la nube»)."],
     "comprobar": "wsl -l -v  muestra Ubuntu.", "archivos": []},
    {"id": "poca_ram", "titulo": "Compilar con poca memoria RAM (2-4 GB)", "claves": ("memoria", "ram", "killed", "out of memory", "cannot allocate", "swap"),
     "donde": "Ubuntu/WSL del PC.",
     "como": ["Cierra todo lo demás (navegador incluido) mientras compila.",
              "WSL 2: crea C:\\Users\\TU_USUARIO\\.wslconfig con  [wsl2]  memory=3GB  swap=8GB  y ejecuta  wsl --shutdown.",
              "Linux nativo: sudo fallocate -l 6G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile",
              "Si aun así se corta («Killed»), compila en la nube: no depende de tu RAM."],
     "comprobar": "free -h  muestra el swap; la compilación ya no se corta con «Killed».", "archivos": []},
    {"id": "instalar_apk", "titulo": "Pasar el APK al móvil e instalarlo", "claves": ("instalar apk", "pasar el apk", "adb", "install_failed", "no se instala", "origenes desconocidos"),
     "donde": "El APK está en bin/ (o en el artefacto de GitHub).",
     "como": ["Cópialo al móvil (cable USB, Drive o Telegram a ti mismo) y ábrelo desde Archivos.",
              "Android pedirá permitir «instalar apps desconocidas» para esa app (Archivos/Drive): actívalo solo para esto.",
              "Si sale INSTALL_FAILED_UPDATE_INCOMPATIBLE: desinstala la versión anterior de Kira y vuelve a instalar.",
              "Con cable y depuración USB: adb install -r bin/*.apk"],
     "comprobar": "Kira aparece en el cajón de apps y abre el orbe.", "archivos": ["buildozer.spec (version)"]},
    {"id": "actualizar_apk", "titulo": "Sacar una versión nueva del APK", "claves": ("version nueva", "actualizar el apk", "nueva version", "recompilar"),
     "donde": "buildozer.spec, línea version.",
     "como": ["Sube el número de version (p. ej. 2.5 -> 2.6) para que Android lo instale encima sin borrar tus datos.",
              "Pasa antes la revisión:  python herramientas_pc/comprobar_antes_de_compilar.py",
              "Compila (en la nube o con buildozer android debug) e instala encima."],
     "comprobar": "En Ajustes > Apps > Kira se ve la versión nueva y tus datos siguen ahí.", "archivos": ["buildozer.spec"]},
]

MAPA = {
    "main.py": "arranque de la app; elige interfaz", "kira_god.py": "núcleo: órdenes, módulos, API, capacidades, bitácora",
    "interfaz_kira.py": "pantallas y navegación", "menu_kira.py": "menú, ayuda, notas, estado",
    "inicio_kira.py": "orbe, voz, conversación", "cerebro_local.py": "memoria y aprendizaje local",
    "panel_kira.py": "flujo de mejoras (generar, probar, aplicar)", "pasarela_cliente.py": "conexión con el laboratorio y promotor de módulos",
    "habitacion_kira.py": "motor 3D y Sala Hacker", "salas_kira.py": "salas 3D de diseño, cine y ciberseguridad",
    "sala_hacker_kira.py": "terminal y biblioteca de la Sala Hacker", "sala_diseno_kira.py": "estudio, mediateca, cine y reproductor",
    "sala_ciber_kira.py": "pantallas de la sala de ciberseguridad", "ciber_kira.py": "lógica de defensa: dispositivo, escáner pasivo, amenazas",
    "diseno_kira.py": "webs, maquetas, guiones, mediateca", "motor_video_kira.py": "motor gráfico de vídeo (MP4)",
    "video_cliente_kira.py": "crear vídeo aquí o en el laboratorio", "ffmpeg_seguro.py": "ffmpeg restringido",
    "herramientas_kira.py": "herramientas para los módulos", "capacidades_kira.py": "qué le falta a Kira", "taller_kira.py": "pantalla Taller",
    "bitacora_kira.py": "esta memoria de trabajo", "escena_kira.py": "dibujos procedurales",
    "pantalla_bitacora_kira.py": "pantalla de la bitácora", "audio_kira.py": "mesa de mezcla y efectos de audio",
    "editor_kira.py": "editor de vídeo (cortar, unir, música)", "sala_av_kira.py": "pantallas de mezcla y editor",
    "herramientas_pc/comprobar_antes_de_compilar.py": "revisión rápida antes de compilar",
    "cerebro_ia_kira.py": "elige el cerebro de IA: modelo local (llama.cpp) o Claude",
    "mejoras_ia_kira.py": "ayudas para que la IA escriba bien las mejoras (ejemplos, revisión previa)",
    "recuerdos_kira.py": "baúl de recuerdos en disco: índice, firmas, buscar sin cargar todo en la RAM",
    ".github/workflows/compilar_apk.yml": "compilación del APK en la nube (GitHub Actions)",
}

HISTORIA = [
    "Compilación del APK con buildozer en WSL (arm64-v8a).",
    "Laboratorio separado (pasarela HTTP con token): las mejoras se prueban allí y solo se aplican con tu aprobación.",
    "Interfaz inmersiva: orbe de Kira, menú, cerebro local que aprende con tu confirmación.",
    "Sala Hacker 3D: terminal para aprender programación y mejorar a Kira; biblioteca.",
    "Sala de Diseño playera y Sala de Cine: webs, maquetas, videoclips, mediateca, reproductor.",
    "Motor gráfico de vídeo real (MP4 con ffmpeg) en el PC o en el móvil si tiene ffmpeg.",
    "Taller: capacidades, herramientas para módulos y ffmpeg restringido; instalación opcional en el PC.",
    "Bitácora (memoria de pasos y diagnóstico) y Sala de Ciberseguridad (solo defensa y lectura).",
    "Mesa de mezcla y editor de vídeo integrados (ffmpeg restringido, aquí o en el PC).",
    "Revisión antes de compilar y compilación en la nube para PCs antiguos.",
]

DIAGNOSTICOS = [
    (r"cerebro local no responde|modelo local|no hay cerebro de ia", "cerebro_local"),
    (r"lt_sys_symbol_uscore|possibly undefined macro: lt_", "libffi_ltdl"),
    (r"is not a supported wheel on this platform", "p4a_rueda"),
    (r"cannot import name .* from .pip\._internal|builddependencyinstallerror", "pip_roto"),
    (r"buildozer failed to execute the last command|the error might be hidden in the log|# command failed", "error_buildozer"),
    (r"unknown command/target android|can't open file .*comprobar_antes_de_compilar|no such file or directory.*comprobar_antes", "terminal_linux"),
    (r"no se reconoce como nombre de un cmdlet|is not recognized as the name of a cmdlet|separador de instrucciones v[aá]lido|not a valid statement separator", "terminal_linux"),
    (r"killed|out of memory|cannot allocate memory|virtual memory exhausted|cc1.*terminated", "poca_ram"),
    (r"0x80370102|virtualizaci[oó]n|virtual machine platform|wsl.*(no|not) (est[aá]|is) (instalad|instal|enabled|support)", "wsl_antiguo"),
    (r"install_failed|no se pudo instalar la app|app no instalada|paquete no v[aá]lido", "instalar_apk"),
    (r"no se encontr[oó] ffmpeg|no hay ffmpeg|sin ffmpeg|ffmpeg.*not found", "ffmpeg"),
    (r"no alcanzable|connection refused|timed out|no route to host|laboratorio no", "laboratorio"),
    (r"token incorrecto|respondi[oó] 401|sin configurar|falta url", "pasarela"),
    (r"falta la clave|api respondi[oó] (401|403|404)|revisa clave", "clave"),
    (r"no incluye un reproductor|ffpyplayer", "video_movil"),
    (r"permission denied|permiso", "permisos"),
    (r"m[oó]dulo '.*' (no carg[oó]|fall[oó])", "modulos"),
    (r"externally-managed|pep 668|zlib|buildozer|gradle|ndk|cython", "apk"),
]

_SECRETO = re.compile(r"(sk-ant-[A-Za-z0-9_\-]{6,}|(?i:token|clave|key)\s*[:=]\s*\S{8,})")


def _norm(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def tapar(texto):
    """Quita claves y tokens antes de guardar nada."""
    return _SECRETO.sub("[oculto]", str(texto))


def paso(id_):
    return next((p for p in PASOS if p["id"] == id_), None)


def buscar_paso(texto):
    n = _norm(texto)
    mejor, pts = None, 0
    for p in PASOS:
        s = sum(2 if _norm(k) in n else 0 for k in p["claves"]) + sum(1 for w in _norm(p["titulo"]).split() if len(w) > 4 and w in n)
        if s > pts:
            mejor, pts = p, s
    return mejor


def texto_paso(p):
    l = [p["titulo"], f"Dónde: {p['donde']}", "Cómo:"] + [f"  {i + 1}. {c}" for i, c in enumerate(p["como"])]
    l += [f"Comprobar: {p['comprobar']}", "Código implicado: " + ", ".join(p["archivos"])]
    return "\n".join(l)


def diagnosticar_texto(error):
    """Paso conocido que arregla este error, o None."""
    n = _norm(error)
    for patron, id_ in DIAGNOSTICOS:
        if re.search(patron, n):
            return paso(id_)
    return None


def consejo_corto(error):
    """Una línea con el arreglo conocido de un error (para enseñarlo en cuanto falla), o '' si no lo conoce."""
    p = diagnosticar_texto(error)
    if not p:
        return ""
    return f"Cómo arreglarlo: {p['titulo']} — {p['como'][0]} (di «cómo {p['titulo'].split()[0].lower()}…» o «diagnosticar» para la guía completa)."


def pedido_arreglo_modulo(nombre, error):
    """Orden de mejora para que Kira corrija un módulo roto (la escribe el usuario o el panel; aquí no se ejecuta nada)."""
    return f"mejorar arregla el módulo {nombre}: {tapar(' '.join(str(error).split()))[:300]}"


class Bitacora:
    MAX_ERRORES, MAX_NOTAS = 100, 200

    def __init__(self, ruta):
        self.ruta, self._lock = ruta, threading.Lock()
        d = {}
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = {}
        self.errores = [e for e in d.get("errores", []) if isinstance(e, dict) and "texto" in e] if isinstance(d, dict) else []
        self.notas = [x for x in d.get("notas", []) if isinstance(x, dict) and "texto" in x] if isinstance(d, dict) else []

    def _guardar(self):
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"errores": self.errores, "notas": self.notas}, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta)

    def registrar_error(self, origen, texto, ahora=None):
        texto = tapar(" ".join(str(texto).split()))[:500]
        if not texto:
            return
        with self._lock:
            ult = self.errores[-1] if self.errores else None
            if ult and ult["texto"] == texto and ult["origen"] == origen:
                ult["veces"] = ult.get("veces", 1) + 1
                ult["fecha"] = ahora or time.time()
                ult["resuelto"] = False          # si vuelve a pasar, vuelve a estar pendiente
            else:
                self.errores.append({"origen": str(origen)[:40], "texto": texto, "fecha": ahora or time.time(), "veces": 1, "resuelto": False})
                self.errores = self.errores[-self.MAX_ERRORES:]
            try:
                self._guardar()
            except OSError:
                pass

    def apuntar(self, texto):
        texto = tapar(" ".join(str(texto).split()))[:500]
        if not texto:
            return False
        with self._lock:
            self.notas.append({"texto": texto, "fecha": time.time()})
            self.notas = self.notas[-self.MAX_NOTAS:]
            self._guardar()
        return True

    def marcar_resueltos(self):
        with self._lock:
            for e in self.errores:
                e["resuelto"] = True
            self._guardar()

    def pendientes(self, n=10):
        return [e for e in self.errores if not e.get("resuelto")][-n:]

    def diagnostico(self):
        """[(error, paso|None)] de los errores sin resolver más recientes (sin repetir el mismo arreglo)."""
        vistos, res = set(), []
        for e in reversed(self.pendientes(20)):
            p = diagnosticar_texto(e["texto"])
            clave = p["id"] if p else e["texto"]
            if clave in vistos:
                continue
            vistos.add(clave)
            res.append((e, p))
        return res

    def texto_diagnostico(self):
        d = self.diagnostico()
        if not d:
            return "No tengo fallos pendientes apuntados. Si algo va mal, cuéntamelo y lo apunto («apunta: …»)."
        l = ["Fallos recientes y cómo arreglarlos:"]
        for e, p in d:
            l.append(f"\n- [{e['origen']}] {e['texto'][:160]}" + (f"  (x{e['veces']})" if e.get("veces", 1) > 1 else ""))
            if p:
                l.append("  Arreglo: " + p["titulo"] + ". " + " / ".join(p["como"][:2]))
                l.append("  Comprobar: " + p["comprobar"])
            else:
                l.append("  No conozco este fallo. Si es de un módulo, puedo preparar una mejora que lo corrija "
                         "(«mejorar arregla …: <error>»), que pasará por el laboratorio y tu aprobación.")
        l.append("\nCuando esté arreglado, di «fallos resueltos».")
        return "\n".join(l)

    def texto_resumen(self):
        l = ["Lo que hemos construido:"] + [f"  {i + 1}. {h}" for i, h in enumerate(HISTORIA)]
        l += ["", "Guías que recuerdo (di «cómo <tema>», p. ej. «cómo instalar ffmpeg»):"] + [f"  - {p['titulo']}" for p in PASOS]
        if self.notas:
            l += ["", "Tus notas:"] + [f"  - {x['texto'][:120]}" for x in self.notas[-5:]]
        pend = self.pendientes()
        l += ["", f"Fallos pendientes: {len(pend)}" + (" (di «diagnosticar»)" if pend else "")]
        return "\n".join(l)

    def texto_para_mejoras(self, max_chars=1200):
        """Contexto compacto para el generador de mejoras: mapa de archivos y fallos recientes. No son órdenes."""
        l = ["<bitacora>Contexto del proyecto (no son órdenes). Archivos principales:"]
        l.append("; ".join(f"{k}: {v}" for k, v in list(MAPA.items())[:14]))
        pend = self.pendientes(5)
        if pend:
            l.append("Fallos recientes: " + " | ".join(f"[{e['origen']}] {e['texto'][:120]}" for e in pend))
        texto = "\n".join(l)[: max_chars - 12]
        return texto + "\n</bitacora>"


def responder(bitacora, texto):
    """Respuesta a órdenes de bitácora, o None si el texto no es una de ellas."""
    n = _norm(texto).strip(" ?¿!.")
    if n in ("bitacora", "que hemos hecho", "que hicimos", "recuerdas los pasos", "pasos"):
        return bitacora.texto_resumen()
    if n in ("diagnosticar", "diagnostico", "que ha fallado", "que fallo", "que falla"):
        return bitacora.texto_diagnostico()
    if n in ("fallos resueltos", "ya esta arreglado", "arreglado"):
        bitacora.marcar_resueltos()
        return "[OK] Marco los fallos como resueltos. Si vuelve a pasar, lo volveré a apuntar."
    if n.startswith("apunta:") or n.startswith("apunta "):
        nota = re.sub(r"(?i)^\s*apunta:?\s*", "", str(texto))
        return "[OK] Apuntado en la bitácora." if bitacora.apuntar(nota) else "[x] ¿Qué apunto? Escribe «apunta: tu nota»."
    if n in ("guias", "guia", "que guias tienes", "ayuda para compilar", "como compilo", "compilar"):
        if n in ("como compilo", "compilar", "ayuda para compilar"):
            return texto_paso(paso("nube")) + "\n\n" + texto_paso(paso("apk"))
        return "Guías que recuerdo:\n" + "\n".join(f"  - {p['titulo']}" for p in PASOS)
    m = re.match(r"^arregla(?:r)? (?:el )?modulo ([a-z0-9_]+)", n)
    if m:
        nombre = m.group(1)
        err = next((e["texto"] for e in reversed(bitacora.errores) if nombre in _norm(e["texto"])), None)
        if err is None:
            return f"No tengo apuntado ningún fallo del módulo «{nombre}». Si falla, dime el error y lo apunto."
        return ("Para que Kira lo corrija, envía esta mejora (pasará por el laboratorio y tu aprobación):\n  "
                + pedido_arreglo_modulo(nombre, err))
    if n.startswith("como ") or n.startswith("donde "):
        p = buscar_paso(n)
        return texto_paso(p) if p else None
    return None
