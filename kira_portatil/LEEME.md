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

## Para ver cómo va
- `journalctl -u kira-portatil -f` (lo que hace el cerebro de casa)
- `nvidia-smi` (cuánta gráfica usa)
- `sudo systemctl restart kira-portatil` (reiniciarlo)

## Sin probar todavía
Se ha probado con modelos pequeños en un ordenador sin gráfica (GitHub, `probar_portatil.yml`) y con un cerebro de
mentira (`tests/test_portatil.py`). En el portátil real falta comprobar: el driver y CUDA con la RTX 5060, la velocidad
de cada cerebro y del pintor, y que la gráfica (8 GB) aguante los tamaños elegidos.
