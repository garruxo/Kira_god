# El cerebro de casa de Kira (portátil)

Un portátil con Linux y tarjeta NVIDIA le presta a Kira (en el móvil) un **cerebro grande** y un **pintor de verdad**
por la WiFi de casa. Fuera de casa, Kira sigue con su cerebro del móvil.

Pensado para: MSI Cyborg A15 AI (Ryzen 9 270, 64 GB, RTX 5060 8 GB, 1 TB).

| Qué | Modelo | Dónde corre |
|---|---|---|
| Cerebro rápido | Qwen3.5 9B (Q4_K_M, 6,2 GB) + ojos | Entero en la gráfica |
| Cerebro grande | Qwen3.5 35B-A3B (Q4_K_M, 22 GB) + ojos | Lo común en la gráfica, los «expertos» en la RAM |
| Pintor | SDXL-Turbo (6,9 GB) + VAE | En la gráfica (el cerebro se aparta mientras pinta) |

Descarga total: unos 38 GB (23 GB menos con `--sin-grande`). SDXL-Turbo es de uso **no comercial** (licencia de Stability AI).

## Instalar (una vez)

1. Instala **Ubuntu 24.04 LTS** en el portátil (desde un USB). Conéctalo a la WiFi de casa.
2. Abre una terminal y escribe:

   ```
   sudo apt install -y git
   git clone https://github.com/garruxo/Kira_god
   cd Kira_god/kira_portatil
   bash instalar_portatil.sh
   ```
3. La primera vez instala el driver de NVIDIA y pide **reiniciar**. Reinicia y vuelve a lanzar `bash instalar_portatil.sh`
   (en la carpeta `Kira_god/kira_portatil`). Sigue donde iba: compila, baja los modelos y lo deja arrancando solo.
4. En el móvil: «Kira, conéctate al ordenador» y escríbele el código de 6 cifras que sale en la pantalla del
   portátil (o escribe `kira-codigo` en el portátil para verlo).

Opcional: `bash instalar_portatil.sh --sin-escritorio` hace que el portátil arranque sin escritorio, con todo para Kira.

### Portátil viejo sin gráfica NVIDIA (p. ej. el Packard Bell: 8 GB de RAM, i5 de 1.ª generación)
Instala **Xubuntu 24.04 LTS** (más ligero) y usa el modo ligero (cerebro pequeño en el procesador, sin pintor, con
memoria de intercambio). No pide reiniciar a mitad (no hay driver de NVIDIA):

```
sudo apt install -y git
git clone https://github.com/garruxo/Kira_god
cd Kira_god/kira_portatil
bash instalar_portatil.sh --ligero
```
Al terminar, **reinicia**: Kira nace (la primera vez) y después aparece sola al encender. Para usarla desde el móvil:
«Kira, conéctate al ordenador» + el código de `kira-codigo`, y luego «pasa tu memoria al portátil».

## El escritorio de KiraOS (como Windows)
Después del saludo entras en el **escritorio**: iconos (Hablar con Kira, Buscador, WiFi, Mi red, Mapa de ataques,
Máquina virtual, Cuaderno, Programando, Móvil, Ajustes) y una **barra abajo** con el botón **K** (menú: las apps, volver al
orbe, reiniciar y apagar con dos toques), la ventana abierta, la **barra para hablar con Kira**, el botón **Texto**, el
altavoz, la WiFi y la hora. Cada ventana tiene arriba el botón **‹ Escritorio** para volver a la pantalla principal
(también la tecla Esc).

**Hablar con Kira desde cualquier sitio:** escribe en la barra de abajo (o empieza a teclear en cualquier parte) o
pulsa el **micrófono** y habla. Kira te contesta **con su voz**; si quieres leerlo, pulsa **Texto**. El altavoz de la
barra quita o pone la voz. El oído es Vosk (sin internet; el audio no se guarda).

## El buscador y su máquina virtual (v2.91)
En el escritorio, el icono **Buscador** es un buscador como Google: escribes, salen los resultados (pestañas Todo,
Código y Documentos) y, al pulsar uno, Kira te trae la página como **texto limpio** (sin anuncios ni nada que se
ejecute), con **Resúmelo** y **Guárdalo en mi baúl**. También vale decir o escribir en la barra «busca …».

Todo lo de investigar (buscar, leer páginas, vídeos de YouTube, la Wikipedia) y sus **experimentos** al pensar salen
**desde su máquina virtual**:
- la máquina va con la red de QEMU aislada; su única salida es **la puerta** (`proxy_maquina.py`), que corre fuera,
  en el portátil, y solo deja ir a **webs de internet**: nunca a tu router, a este portátil ni a nada de tu casa;
- sus experimentos corren dentro como el usuario **prueba**, sin permisos, con tope de tiempo y memoria; al acabar se
  borra todo lo que dejó; si la máquina se cuelga, vuelve sola a su foto limpia;
- lo que lleva una clave (la de Claude, la de GitHub) nunca entra en la máquina: eso sale directo;
- en el icono **Máquina virtual**, «Últimas visitas» enseña a qué sitios fue (solo el nombre, nunca el contenido);
- si la máquina no puede (no está preparada, falta KVM o no contesta), lo hace el portátil y el buscador lo dice.
Para encenderla sin internet: «arranca tu máquina sin internet» o `kira-maquina --encender --sin-internet`.

## Los sentidos de Kira en el portátil (v2.93)
Kira tiene sentidos también en el ordenador, y usa los de cada máquina:
- **oído** (desde la v2.90): micrófono + Vosk, le hablas y te entiende;
- **cámara** (webcam): «mira con tu cámara», «hazme una foto», «¿qué tengo delante?»;
- **pantalla**: «lee la pantalla», «¿qué pone en la pantalla?».

Kira **lee el texto** de lo que ve (OCR). La foto o captura se **borra en cuanto la lee** (solo se queda el texto).
Honestidad: en el portátil en modo ligero no caben sus «ojos» (el modelo de visión), así que **lee letras** pero no
te dice «eso es un gato»: para describir lo que hay están sus ojos del **móvil** (pídeselo desde allí). El móvil
también tiene su cámara, oído y pantalla; cada uno usa lo suyo.

## La WiFi (la maneja Kira)
Conéctalo a la WiFi de casa al instalar Xubuntu (el instalador de Kira necesita internet). Después, desde Kira:
- en su ventana, botón **«WiFi»**: ver redes, conectar (la clave sale con puntitos y no se queda en la memoria de
  Kira; la guarda Linux), arreglar, desconectar, apagar/encender;
- escribiendo «busca redes wifi», «conéctate a la wifi NOMBRE», «arregla la wifi», «qué wifi tienes»;
- en una terminal: `kira-wifi` (estado), `kira-wifi --redes`, `kira-wifi --conectar "NOMBRE"`, `kira-wifi --arreglar`.
Si la WiFi se cae, Kira intenta volver a conectarse sola cada 2 minutos a una red que ya conozca (salvo que la hayas
apagado tú). Desde el móvil se puede mirar, buscar y arreglar; apagar, desconectar, olvidar o dar una clave, solo en
el portátil.

## Para ver cómo va
- `journalctl -u kira-portatil -f` (lo que hace el cerebro de casa)
- `nvidia-smi` (cuánta gráfica usa)
- `sudo systemctl restart kira-portatil` (reiniciarlo)

## Sin probar todavía
Se ha probado con modelos pequeños en un ordenador sin gráfica (GitHub, `probar_portatil.yml`) y con un cerebro de
mentira (`tests/test_portatil.py`). En el portátil real falta comprobar: el driver y CUDA con la RTX 5060, la velocidad
de cada cerebro y del pintor, y que la gráfica (8 GB) aguante los tamaños elegidos.

## Defensa de tu red (Nmap y Wireshark)

El portátil trae `red_defensa_kira.py`, para que Kira vigile y proteja **tu propia red de casa** (SOLO defensa):
- **inventario:** qué aparatos hay conectados (por si aparece uno que no reconoces).
- **puertos:** qué puertos tiene abiertos uno de tus aparatos (puertas que podrían sobrar).
- **tráfico:** un resumen de quién habla con quién en tu red (para detectar algo raro).

Candado real en el código (`en_mi_red`): todo se limita a tu red local privada; cualquier objetivo de fuera se
rechaza. Nmap se usa solo para descubrir y ver puertos (sin exploits) y tshark solo para mirar. No se incluye ninguna
herramienta de ataque.

## Hablar con Kira en el propio portátil (sin móvil)

Tras instalar, escribe en una terminal:

```
kira
```

Se abre la consola de Kira: escribes y te responde con el cerebro grande, en el mismo portátil. Dentro:
`/rapido` · `/grande` (cambiar de cerebro), `/red` (aparatos de tu red), `/puertos <ip>`, `/trafico`, `/estado`, `/salir`.
Una sola pregunta: `kira -p "tu pregunta"`.

## La ventana de Kira (modo escritorio)

Tras instalar, abre la app **Kira** desde el menú de aplicaciones, o escribe `kira-ventana`. Es una ventana donde
escribes y Kira responde con el cerebro grande. Botones para cambiar de cerebro y ver tu red. A pantalla completa
(modo «KiraOS»): `kira-ventana --pantalla` (sales con Escape). La terminal sigue estando: `kira`.
