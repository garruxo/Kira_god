# Compilar el APK de Kira desde tu Packard Bell

Tu portátil (Packard Bell EasyNote, Intel Core i5 de 1.ª generación, ~2010) puede preparar y subir Kira, pero **compilar
el APK dentro de él es lo más delicado**: buildozer descarga y compila Python, Kivy y el NDK de Android. Necesita
unos **15 GB libres**, varias horas la primera vez y bastante RAM. Con el módulo de 2 GB que no se reconoce te quedan
~2 GB, y con eso la compilación se suele cortar a mitad («Killed»).

Por eso hay dos caminos. **Empieza por el A**: no depende de la potencia de tu PC.

---

## Antes de nada (5 minutos, en el PC)

1. Descomprime `Kira_god.zip` en el Escritorio.
2. Si tienes Python instalado en Windows, abre PowerShell **ya dentro de la carpeta** (así no hay que escribir rutas):
   abre la carpeta `Kira_god` en el Explorador de archivos (la que tiene dentro `buildozer.spec`), haz clic en la
   **barra de direcciones** de arriba, borra lo que pone, escribe `powershell` y pulsa Enter. Se abre una ventana azul
   que ya está en esa carpeta. Ahí:
   ```
   python herramientas_pc\comprobar_antes_de_compilar.py
   ```
   **Esta revisión es lo único que sirve en Windows.** Instalar buildozer en el Python de Windows no compila Android:
   eso solo se hace en Ubuntu (camino B) o en GitHub (camino A).
   Debe terminar con «0 error(es)… Listo para compilar». (Si no tienes Python en Windows no pasa nada: el camino A lo
   ejecuta solo en la nube.)

---

## Camino A (recomendado): compilar en la nube con GitHub — gratis

Tu PC solo necesita el navegador. GitHub compila en sus servidores y tú descargas el APK.

1. Crea una cuenta en <https://github.com> (si no tienes).
2. Arriba a la derecha **+ > New repository**. Nombre: `kira_god`. Márcalo **Private**. Pulsa **Create repository**.
3. En el repositorio vacío pulsa **uploading an existing file**. Arrastra **el contenido** de la carpeta `Kira_god`
   (los archivos y carpetas de dentro, no la carpeta en sí). Abajo, **Commit changes**.
4. Comprueba que existe `.github/workflows/compilar_apk.yml`. Algunos navegadores no suben las carpetas que empiezan
   por punto. Si no aparece: **Add file > Create new file**, escribe como nombre `.github/workflows/compilar_apk.yml`,
   pega dentro el contenido de ese archivo (ábrelo con el Bloc de notas) y **Commit changes**.
5. Pestaña **Actions** (si pide permiso, **I understand… enable them**) > **Compilar APK de Kira** > **Run workflow**.
6. Espera: la primera vez **20-40 minutos**; las siguientes, menos (guarda en caché el SDK). Un círculo amarillo =
   trabajando; verde = listo; rojo = fallo (entra y mira el paso en rojo).
7. Entra en la ejecución terminada > abajo, **Artifacts > kira-apk**. Se descarga un `.zip` con el `.apk` dentro.

Si sale en rojo: copia las últimas líneas del paso que falló y díselas a Kira («diagnosticar» o pégalas en la Bitácora
como nota) o a mí.

---

## Camino B: compilar en el propio Packard Bell (Ubuntu en WSL)

Solo si quieres hacerlo todo en local. Lento y exigente con este PC.

### B1. ¿Tu Windows lo permite?
- Pulsa `Win + R`, escribe `winver`. Necesitas **Windows 10 versión 2004 o superior** u 11.
- Virtualización: al encender, pulsa **F2** (BIOS de Packard Bell) y activa **Intel Virtualization Technology** si
  aparece. Sin ella, WSL 2 da el error `0x80370102`.
- Si tu Windows es 7 u 8, o no puedes activarla: vuelve al **camino A**.

### B2. Instalar Ubuntu 24.04 (no la última)
En **PowerShell como administrador**:
```
wsl --install -d Ubuntu-24.04
```
Reinicia y crea tu usuario de Ubuntu. **Importante:** pon `Ubuntu-24.04`. La versión más nueva (26.04) necesita otra
rama de buildozer y otra API de Android, y falla con la configuración de Kira.

### B3. Darle memoria (imprescindible con 2-4 GB)
Crea con el Bloc de notas el archivo `C:\Users\TU_USUARIO\.wslconfig` con:
```
[wsl2]
memory=3GB
swap=8GB
```
En PowerShell: `wsl --shutdown` y vuelve a abrir Ubuntu. Durante la compilación **cierra el navegador y todo lo demás**.

### B4. Preparar Ubuntu (una vez)

> **Atención:** estos comandos se escriben **dentro de Ubuntu**, no en PowerShell. Si tu línea empieza por
> `PS C:\Users\...>` estás en Windows: escribe `wsl` y pulsa Enter, y espera a que la línea cambie a algo como
> `garru@PC:~$`. Pega **cada línea completa de una en una**.

```
sudo apt update
```
```
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv python3-virtualenv autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libltdl-dev libssl-dev automake autopoint gettext
```
```
python3 -m venv ~/venv_kira
```
```
source ~/venv_kira/bin/activate
```
```
pip install buildozer setuptools cython==0.29.34
```
(En Ubuntu 24.04 `pip install --user` da el error «externally-managed-environment»: por eso se usa el entorno
`venv_kira`. Cada vez que abras Ubuntu para compilar, vuelve a hacer `source ~/venv_kira/bin/activate`.)

### B5. Compilar
```
cp -r /mnt/c/Users/TU_USUARIO/Desktop/Kira_god ~/
cd ~/Kira_god
python herramientas_pc/comprobar_antes_de_compilar.py
export PATH=$(echo "$PATH" | tr ':' '\n' | grep -v '^/mnt/' | paste -sd:)
buildozer -v android debug 2>&1 | tee compilacion.log
```
- La línea `export PATH=…` quita de Ubuntu las carpetas de Windows (`/mnt/c/Program Files/...`), que con sus espacios
  suelen romper la compilación. Hay que ponerla cada vez que abras Ubuntu (o desactívalas para siempre, ver abajo).
- Si falla, el error **no** es lo último que sale (eso es la lista `# ENVIRONMENT`): está antes. Míralo con
  `grep -B 30 'Command failed' compilacion.log | head -n 40`.
- Para quitar las carpetas de Windows para siempre: `sudo nano /etc/wsl.conf`, añade
  `[interop]` y debajo `appendWindowsPath=false`, guarda (Ctrl+O, Enter, Ctrl+X) y en PowerShell `wsl --shutdown`.
- Copia la carpeta a `~` (dentro de Linux). Compilar en `/mnt/c` es muchísimo más lento.
- La primera vez acepta las licencias y espera (en este PC, **de 2 a 5 horas**). El APK queda en `bin/`.
- Para sacarlo a Windows: `cp bin/*.apk /mnt/c/Users/TU_USUARIO/Desktop/`

### Si falla
| Mensaje | Qué hacer |
|---|---|
| `Killed` / `Cannot allocate memory` | Falta RAM: revisa B3, cierra todo y vuelve a lanzar; si sigue, camino A |
| `0x80370102` | Activa la virtualización en la BIOS (B1) o usa el camino A |
| `externally-managed-environment` | Te saltaste el `venv` (B4) |
| Se queda parado en una licencia | Escribe `y` y Enter |
| Cualquier otro | Copia las últimas 30 líneas y pásalas a Kira («diagnosticar») o a mí |

Para volver a empezar limpio: `rm -rf .buildozer bin` dentro de `~/Kira_god`.

---

## Instalar el APK en el móvil

1. Pasa el `.apk` al móvil (cable USB, Google Drive o enviándotelo por Telegram/WhatsApp).
2. Ábrelo desde **Archivos**. Android pedirá permitir **instalar apps desconocidas** para esa app: actívalo solo para
   esto.
3. Si ya tenías una versión anterior y sale `INSTALL_FAILED_UPDATE_INCOMPATIBLE`, desinstala la vieja y vuelve a
   instalar. (Esta versión es la **2.6**, así que normalmente se instala encima conservando tus datos.)
4. Al abrir Kira por primera vez, concede **micrófono** y **música y vídeos** cuando los pida.

## Lo que necesita el PC después (para vídeo, mezcla y editor)
El móvil no trae ffmpeg. Para crear vídeos, mezclar audio y editar, el PC hace de laboratorio:
`pip install pillow imageio-ffmpeg` y arranca `kira_laboratorio/servidor_lab.py` (ver su README). Esto sí lo aguanta
bien tu Packard Bell: es mucho más ligero que compilar.

## Nota sobre la RAM del Packard Bell
Si quieres recuperar los 4 GB: con el portátil apagado y sin batería, saca los dos módulos, limpia los contactos con
una goma de borrar, y prueba **un solo módulo cada vez en cada ranura**. Así sabrás si falla el módulo (no arranca en
ninguna ranura) o la ranura (el módulo funciona en la otra).
