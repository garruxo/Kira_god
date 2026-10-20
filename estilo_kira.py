# -*- coding: utf-8 -*-
"""
estilo_kira.py - Piezas de ESTILO comunes para que todo se lea bien en el móvil.

Problema que arregla: los textos de botones y rótulos tenían tamaño fijo y fuente de máquina de escribir (muy
ancha). En un móvil estrecho, o con la letra del sistema grande, se salían del botón y se pisaban unos con otros.
Ahora:
  - fuente normal (Roboto) en toda la interfaz; la de máquina de escribir solo para código;
  - letra que respeta el tamaño de letra del sistema, pero con tope (no rompe los diseños);
  - ajustar(): el texto se parte en 2 líneas si hace falta y, si aun así no cabe, la letra se encoge un poco.
Las funciones que necesitan Kivy lo importan dentro: este módulo se puede importar en el PC sin Kivy.
"""
import os

TOPE_ESCALA = 1.2          # la letra del sistema puede agrandar los textos como mucho un 20 %


def tam(valor):
    """Tamaño de letra: como sp() (respeta la letra grande del sistema) pero con tope."""
    from kivy.metrics import dp, sp
    return min(sp(valor), dp(valor) * TOPE_ESCALA)


def fuente_mono():
    """{'font_name': ruta} de RobotoMono para el CÓDIGO ({} si no está)."""
    try:
        from kivy import kivy_data_dir
        ruta = os.path.join(kivy_data_dir, "fonts", "RobotoMono-Regular.ttf")
        return {"font_name": ruta} if os.path.exists(ruta) else {}
    except Exception:
        return {}


_MEDIDORES = {}


def _medidor(w, tam_letra):
    from kivy.core.text import Label as CoreLabel
    clave = (getattr(w, "font_name", "Roboto"), bool(getattr(w, "bold", False)), bool(getattr(w, "italic", False)))
    cl = _MEDIDORES.get(clave)
    if cl is None:
        cl = _MEDIDORES[clave] = CoreLabel(text="", font_name=clave[0], bold=clave[1], italic=clave[2])
    cl.options["font_size"] = tam_letra
    cl.resolve_font_name()
    return cl


def ancho_texto(w, tam_letra):
    """Ancho que ocuparía el texto de 'w' en una línea con esa letra, SIN dibujarlo (solo mide con la fuente)."""
    return _medidor(w, tam_letra).get_extents(str(w.text))[0]


def alto_texto(w, tam_letra, ancho):
    """Alto que ocuparía el texto de 'w' partido en líneas de 'ancho' (como hace Kivy), SIN dibujarlo."""
    cl = _medidor(w, tam_letra)
    medir = cl.get_extents
    espacio = medir(" ")[0]
    alto_linea = medir("Ág")[1] * float(getattr(w, "line_height", 1.0) or 1.0)
    n = 0
    for parrafo in str(w.text).split("\n"):
        n += 1
        usado = 0.0
        for palabra in parrafo.split(" "):
            a = medir(palabra)[0] if palabra else 0.0
            if usado and usado + espacio + a > ancho:
                n += 1
                usado = a
            else:
                usado += (espacio if usado else 0.0) + a
            while usado > ancho and a > ancho:          # palabra más larga que la línea: Kivy la parte
                n += 1
                usado -= ancho
    return n * alto_linea


def ajustar(w, minimo=11, lineas=2, margen=8):
    """Hace que el texto de un botón o rótulo de ALTO FIJO quepa siempre:
      - lineas=1: si la frase no cabe en el ancho, la letra baja (hasta 'minimo', en dp); si aun así no cabe, se
        corta con «…».
      - lineas>1: se parte en líneas; si ocupan más que el alto, la letra baja; si aun así no caben, se recorta.
    El tamaño se calcula MIDIENDO con la fuente, sin dibujar: el texto se dibuja una sola vez (las pantallas abren
    antes). Si no se puede medir así (texto con marcas [b]…[/b]), se prueba dibujando, como antes.
    Alineado al centro si no se indicó otra alineación."""
    from kivy.metrics import dp
    if getattr(w, "halign", "auto") in ("auto", None):
        w.halign = "center"
    w.valign = "middle"
    st = {"base": getattr(w, "font_size", 15), "fase": "medir", "esperando": False}
    m, menor = dp(margen), dp(minimo)

    def disponible():
        return max(1, w.width - m)

    def poner(font_size=None, text_size=None, shorten=None):
        """Cambia solo lo que cambia (cada cambio obliga a Kivy a volver a dibujar el texto)."""
        if shorten is not None and bool(getattr(w, "shorten", False)) != shorten:
            w.shorten = shorten
            if shorten:
                w.shorten_from = "right"
        if font_size is not None and getattr(w, "font_size", None) != font_size:
            w.font_size = font_size
        if text_size is not None and list(getattr(w, "text_size", (None, None)) or (None, None)) != list(text_size):
            w.text_size = text_size

    def empezar(*_, forzar=False):
        if w.width < 4:
            return
        if not forzar and w.width == 100 and getattr(w, "size_hint_x", None) is not None:
            # aún sin colocar (100 es el ancho por defecto de Kivy): medir ahora sería trabajo tirado
            if not st["esperando"]:
                st["esperando"] = True
                try:
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda _dt: (st.update(esperando=False), empezar(forzar=True)), 0)
                    return
                except Exception:
                    st["esperando"] = False
            else:
                return
        st["fase"] = "medir"
        if not getattr(w, "markup", False) and rapido():
            return
        poner(font_size=st["base"], shorten=False, text_size=(None, None) if lineas == 1 else (disponible(), None))

    def rapido():
        """Calcula la letra que cabe midiendo con la fuente (sin dibujar) y la pone de una vez."""
        try:
            disp, f = disponible(), st["base"]
            alto = w.height - dp(2)
            for _ in range(5):
                if lineas == 1:
                    ancho = ancho_texto(w, f)
                    if ancho <= disp or f <= menor:
                        break
                    f = max(menor, min(f - dp(1), f * disp / max(1.0, ancho) * 0.98))
                else:
                    h = alto_texto(w, f, disp)
                    if h <= alto or f <= menor:
                        break
                    f = max(menor, min(f - dp(1), f * (alto / max(1.0, h)) ** 0.5 * 0.98))
            cabe = lineas == 1 or alto_texto(w, f, disp) <= alto
        except Exception:
            return False                                   # sin medidor (o en las pruebas): el método de siempre
        st["fase"] = "listo"
        if lineas == 1:                                    # si ni con la letra mínima cabe, con «…»
            poner(font_size=f, shorten=True, text_size=(disp, None))
        else:
            poner(font_size=f, shorten=False, text_size=(disp, None if cabe else max(1, alto)))
        return True

    def revisar(*_):
        if st["fase"] != "medir" or w.width < 4:
            return
        tw, th = getattr(w, "texture_size", (0, 0))
        if lineas == 1:
            cabe = tw <= disponible() + 1
        else:
            cabe = th <= w.height - dp(2)
        if not cabe and getattr(w, "font_size", 0) > menor:
            # salto directo al tamaño que debería caber; si aun así no cabe, la siguiente vuelta baja de 1 en 1
            if lineas == 1:
                ideal = w.font_size * disponible() / max(1.0, tw) * 0.97
            else:
                ideal = w.font_size * ((w.height - dp(2)) / max(1.0, th)) ** 0.5 * 0.97
            w.font_size = max(menor, min(w.font_size - dp(1), ideal))   # Kivy vuelve a medir y llama a revisar
            return
        st["fase"] = "listo"
        if lineas == 1:                                     # alineado y, si ni con la letra mínima cabe, con «…»
            poner(shorten=True, text_size=(disponible(), None))
        elif not cabe:
            poner(text_size=(disponible(), max(1, w.height - dp(2))))   # recorta lo que sobre por abajo
    w.bind(width=empezar, texture_size=revisar, text=empezar, height=lambda *_: lineas > 1 and empezar())
    empezar()
    return w


def fondo_redondeado(w, color, radio=12):
    """Fondo con esquinas redondeadas detrás de un widget (los botones planos se ven más limpios)."""
    from kivy.graphics import Color, RoundedRectangle
    from kivy.metrics import dp
    with w.canvas.before:
        c = Color(*color)
        r = RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(radio)])
    w.bind(pos=lambda _w, v: setattr(r, "pos", v), size=lambda _w, v: setattr(r, "size", v))
    return c
