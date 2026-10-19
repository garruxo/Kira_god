# -*- coding: utf-8 -*-
"""
pantalla_lector_kira.py - Pantalla «Lector» (Kivy): Kira lee el texto y el código de tus capturas (lector_kira).
"""
import threading

import lector_kira as lk


def pedir_permiso_fotos():
    """En Android pide permiso para ver las capturas. True si ya lo tiene (o no hace falta)."""
    try:
        from kivy.utils import platform
        if platform != "android":
            return True
        from android.permissions import Permission, check_permission, request_permissions
        nombres = [n for n in ("READ_MEDIA_IMAGES", "READ_EXTERNAL_STORAGE") if hasattr(Permission, n)]
        if any(check_permission(getattr(Permission, n)) for n in nombres):
            return True
        request_permissions([getattr(Permission, n) for n in nombres])
        return False
    except Exception:
        return True


def montar_lector(sm, p):
    from kivy.clock import Clock
    from kivy.metrics import dp, sp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label

    boton, texto_largo, pantalla, en_hilo = p["boton"], p["texto_largo"], p["pantalla"], p["en_hilo"]
    TXT, GRIS, VERDE, FUENTE = p["TXT"], p["GRIS"], p["VERDE"], p["FUENTE"]
    core = p["core"]
    lector = core.lector

    _, c = pantalla("lector", "LECTOR DE CAPTURAS")
    estado = Label(text="", size_hint_y=None, height=dp(44), color=TXT, font_size=sp(13), halign="left",
                   valign="middle", **FUENTE)
    estado.bind(width=lambda w, a: setattr(w, "text_size", (a, None)))
    c.add_widget(estado)
    btn_bajar = boton("Descargar el lector (6 MB)", lambda: descargar(), VERDE)
    c.add_widget(btn_bajar)
    fila = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
    fila.add_widget(boton("Leer la última captura", lambda: leer_ultima(), VERDE))
    fila.add_widget(boton("Elegir imagen…", lambda: elegir(), GRIS))
    c.add_widget(fila)
    sv, resultado = texto_largo("Haz una captura de pantalla de un texto o de un código y pulsa «Leer la última "
                                "captura». Todo se hace en el móvil, sin internet.")
    c.add_widget(sv)
    fila2 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    fila2.add_widget(boton("Abrir en el editor", lambda: abrir_editor(), GRIS, alto=44))
    fila2.add_widget(boton("Guardar en el baúl", lambda: orden("guarda lo leído"), GRIS, alto=44))
    fila2.add_widget(boton("Explicármelo", lambda: orden("explícame lo leído"), GRIS, alto=44))
    c.add_widget(fila2)

    def pintar():
        if lector.estado == "descargando":
            estado.text = f"Descargando idiomas… {lector.progreso * 100:.0f} %"
        elif lector.disponible():
            estado.text = "Lector listo (español e inglés, sin internet)."
        elif lector.idiomas_instalados():
            estado.text = "Idiomas descargados, pero esta versión de la app no trae el lector."
        else:
            estado.text = "Falta descargar el lector (una vez, unos 6 MB)."
        btn_bajar.disabled = lector.idiomas_instalados() or lector.estado == "descargando"

    def descargar():
        def fin(r):
            if isinstance(r, Exception):
                resultado.text = f"[x] {r}"
            pintar()
        en_hilo(lector.descargar_idiomas, fin)
        Clock.schedule_once(lambda _dt: pintar(), 0.2)

    def leer(ruta):
        resultado.text = "Leyendo…"

        def fin(r):
            resultado.text = f"[x] {r}" if isinstance(r, Exception) else r
            pintar()
        en_hilo(lambda: lector.leer(ruta), fin)

    def leer_ultima():
        if not pedir_permiso_fotos():
            resultado.text = "Necesito permiso para ver tus capturas. Concédelo y vuelve a pulsar."
            return
        ruta = lk.ultima_captura()
        if ruta is None:
            resultado.text = "[x] No encuentro capturas de pantalla en el móvil."
            return
        leer(ruta)

    def elegir():
        if not pedir_permiso_fotos():
            resultado.text = "Necesito permiso para ver tus fotos. Concédelo y vuelve a pulsar."
            return
        try:
            from plyer import filechooser
            filechooser.open_file(filters=[["Imágenes", "*.png", "*.jpg", "*.jpeg", "*.webp"]],
                                  on_selection=lambda sel: sel and Clock.schedule_once(lambda _dt: leer(sel[0]), 0))
        except Exception as e:
            resultado.text = f"[x] No puedo abrir el selector de imágenes aquí ({e}). Usa «Leer la última captura»."

    def abrir_editor():
        if not lector.ultimo:
            resultado.text = "Primero lee una captura."
            return
        p["abrir_en_editor"](lector.ultimo, "Texto leído de una captura: revísalo y pulsa «Ejecutar».")

    def orden(texto):
        resultado.text = "Un momento…"
        en_hilo(lambda: core.procesar_orden(texto), lambda r: setattr(resultado, "text", f"[x] {r}" if isinstance(r, Exception) else str(r)))

    p["ganchos"]["lector"] = pintar
    return {"leer": leer, "pintar": pintar}
