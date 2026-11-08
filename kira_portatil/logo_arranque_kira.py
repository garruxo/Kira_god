# -*- coding: utf-8 -*-
"""logo_arranque_kira.py - v3.05: el orbe de Kira para la pantalla de ARRANQUE del portátil (Plymouth), la que sale
mientras Linux se carga (antes salía la de Xubuntu). Python puro: un PNG con fondo transparente, el orbe y los dos
arcos finos (cian y rosa) que se cruzan, como en el arranque de KiraOS. También el guion del tema de Plymouth.

  python3 logo_arranque_kira.py CARPETA     escribe CARPETA/orbe.png, kira.script y kira.plymouth
"""
import math
import os
import struct
import sys
import zlib

CIAN = (0, 229, 255)
ROSA = (255, 61, 154)
FONDO = "0.02, 0.027, 0.06"          # el mismo azul casi negro del escritorio de KiraOS (#05070f)


def _png(ancho, alto, filas):
    def trozo(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
    crudo = b"".join(b"\x00" + bytes(f) for f in filas)
    return (b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 6, 0, 0, 0))
            + trozo(b"IDAT", zlib.compress(crudo, 9)) + trozo(b"IEND", b""))


def png_orbe(tam=260):
    """El orbe: un brillo suave en el centro y dos arcos (cian de 200° a 340°+…, rosa enfrente) que se cruzan."""
    c = (tam - 1) / 2.0
    r_orbe, r_arco = tam * 0.30, tam * 0.43
    filas = []
    for y in range(tam):
        fila = bytearray()
        for x in range(tam):
            dx, dy = x - c, y - c
            d = math.hypot(dx, dy)
            ang = (math.degrees(math.atan2(dy, dx)) + 360) % 360
            r = g = b = a = 0.0
            if d < r_orbe:                                   # el orbe: oscuro con brillo cian hacia el borde
                t = d / r_orbe
                r, g, b = 8 + 20 * t, 18 + 90 * t ** 3, 34 + 120 * t ** 3
                a = 255
            elif d < r_orbe + 3:                             # el aro del orbe
                r, g, b, a = 120, 240, 255, 255 * (1 - (d - r_orbe) / 3)
            halo = max(0.0, 1 - abs(d - r_orbe) / (tam * 0.09))
            if halo and d >= r_orbe:                         # halo suave alrededor
                r, g, b, a = CIAN[0], CIAN[1], CIAN[2], max(a, 70 * halo ** 2)
            for col, desde, hasta, rad in ((CIAN, 200, 340, r_arco), (ROSA, 20, 160, r_arco - 6),
                                           (CIAN, 30, 95, r_arco - 14), (ROSA, 215, 280, r_arco + 6)):
                if desde <= ang <= hasta and abs(d - rad) < 2.2:
                    k = 1 - abs(d - rad) / 2.2
                    r, g, b, a = col[0], col[1], col[2], max(a, 255 * k)
            fila += bytes((int(min(255, r)), int(min(255, g)), int(min(255, b)), int(min(255, a))))
        filas.append(fila)
    return _png(tam, tam, filas)


GUION = """# Kira: pantalla de arranque (v3.05). El orbe late suave mientras Linux se carga.
Window.SetBackgroundTopColor(%(f)s);
Window.SetBackgroundBottomColor(%(f)s);
orbe = Image("orbe.png");
s = Sprite(orbe);
s.SetX(Window.GetX() + Window.GetWidth() / 2 - orbe.GetWidth() / 2);
s.SetY(Window.GetY() + Window.GetHeight() / 2 - orbe.GetHeight() / 2);
s.SetZ(10);
texto = Image.Text("KIRA", 0.86, 0.97, 1, 1, "Sans Bold 26");
if (texto) {
  t = Sprite(texto);
  t.SetX(Window.GetX() + Window.GetWidth() / 2 - texto.GetWidth() / 2);
  t.SetY(Window.GetY() + Window.GetHeight() / 2 - texto.GetHeight() / 2);
  t.SetZ(20);
}
paso = 0;
fun refresco() {
  paso++;
  s.SetOpacity(0.78 + 0.22 * Math.Sin(paso / 14));
}
Plymouth.SetRefreshFunction(refresco);

# Si algún día el disco va cifrado, que se vea dónde escribir la clave (con puntos, nunca la clave).
fun pide_clave(prompt, puntos) {
  linea = "";
  for (i = 0; i < puntos; i++) linea += "*";
  global.aviso = Sprite(Image.Text(prompt + "  " + linea, 1, 1, 1));
  global.aviso.SetX(Window.GetX() + Window.GetWidth() / 2 - global.aviso.GetImage().GetWidth() / 2);
  global.aviso.SetY(Window.GetY() + Window.GetHeight() * 0.75);
}
Plymouth.SetDisplayPasswordFunction(pide_clave);
fun normal() { global.aviso = NULL; }
Plymouth.SetDisplayNormalFunction(normal);
""" % {"f": FONDO}

TEMA = """[Plymouth Theme]
Name=Kira
Description=Kira al encender el portatil
ModuleName=script

[script]
ImageDir=%(d)s
ScriptFile=%(d)s/kira.script
"""


def escribir(carpeta, destino="/usr/share/plymouth/themes/kira"):
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, "orbe.png"), "wb") as f:
        f.write(png_orbe())
    with open(os.path.join(carpeta, "kira.script"), "w", encoding="utf-8") as f:
        f.write(GUION)
    with open(os.path.join(carpeta, "kira.plymouth"), "w", encoding="utf-8") as f:
        f.write(TEMA % {"d": destino})
    return carpeta


if __name__ == "__main__":
    escribir(sys.argv[1] if len(sys.argv) > 1 else ".")
