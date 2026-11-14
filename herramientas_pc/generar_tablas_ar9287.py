#!/usr/bin/env python3
"""Genera wifi_tablas_kira.py a partir de las tablas de la WiFi Atheros AR9287 que trae Linux (ath9k,
drivers/net/wireless/ath/ath9k/ar9002_initvals.h, licencia ISC de Atheros: se pueden usar y copiar
conservando el aviso).

De las tablas «Modes» se queda SOLO con la columna de 2,4 GHz HT20 (la única que usa el kernel de Kira
para escuchar redes); las «Common» van enteras.

Uso:  python3 herramientas_pc/generar_tablas_ar9287.py <ruta a ar9002_initvals.h> [salida.py]
"""
import os
import re
import sys

TABLAS = [
    # (nombre en Linux, nombre en C, columna: 4 = 2G HT20 en las Modes, 1 = la única en las Common)
    ("ar9287Modes_9287_1_1", "ar9287_modes", 4),
    ("ar9287Common_9287_1_1", "ar9287_common", 1),
    ("ar9287Modes_rx_gain_9287_1_1", "ar9287_rx_gain", 4),
    ("ar9287Modes_tx_gain_9287_1_1", "ar9287_tx_gain", 4),
    ("ar9287Common_normal_cck_fir_coeff_9287_1_1", "ar9287_cck_fir", 1),
]

AVISO = """/*
 * Copyright (c) 2010-2011 Atheros Communications Inc.
 *
 * Permission to use, copy, modify, and/or distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 * OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */
"""


def tabla(texto, nombre):
    m = re.search(r"static const u32 " + re.escape(nombre) + r"\[\]\[(\d+)\] = \{(.*?)\n\};", texto, re.S)
    if not m:
        raise SystemExit("No encuentro la tabla " + nombre)
    cols = int(m.group(1))
    filas = []
    for f in re.findall(r"\{([^{}]*)\}", m.group(2)):
        nums = [int(x, 16) for x in re.findall(r"0x[0-9a-fA-F]+", f)]
        if len(nums) != cols:
            raise SystemExit(f"Fila rara en {nombre}: {f}")
        filas.append(nums)
    return cols, filas


def generar(texto):
    partes = [AVISO, "/* ar9287_tablas.h — tablas de ajuste de la radio AR9287 (de Linux ath9k, solo 2,4 GHz HT20)."
              "\n   Generado por herramientas_pc/generar_tablas_ar9287.py: no lo cambies a mano. */",
              "#ifndef AR9287_TABLAS_H", "#define AR9287_TABLAS_H", "#include <stdint.h>", ""]
    for linux, c, col in TABLAS:
        _, filas = tabla(texto, linux)
        partes.append(f"static const uint32_t {c}[][2] = {{   /* {linux}, columna {col} */")
        for f in filas:
            partes.append(f"    {{0x{f[0]:08x}, 0x{f[col]:08x}}},")
        partes.append("};")
        partes.append(f"#define {c.upper()}_N {len(filas)}")
        partes.append("")
    partes.append("#endif")
    return "\n".join(partes) + "\n"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    texto = open(sys.argv[1], encoding="utf-8").read()
    c = generar(texto)
    salida = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wifi_tablas_kira.py")
    with open(salida, "w", encoding="utf-8") as f:
        f.write('"""Tablas de la radio WiFi Atheros AR9287 para el kernel de Kira (etapa 17).\n'
                'Generado por herramientas_pc/generar_tablas_ar9287.py desde Linux v6.8 (ath9k, licencia ISC).\n'
                'No lo cambies a mano: vuelve a generarlo."""\n\n')
        f.write("AR9287_TABLAS_H = r'''" + c + "'''\n")
    print("Escrito", salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
