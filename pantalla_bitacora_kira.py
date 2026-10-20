# -*- coding: utf-8 -*-
"""
pantalla_bitacora_kira.py - Pantalla BITÁCORA (Kivy): la memoria de trabajo de Kira a la vista.

  RESUMEN : qué hemos construido, guías que recuerda, tus notas y cuántos fallos hay pendientes.
  FALLOS  : los fallos reales apuntados (sin claves) con su arreglo conocido; «Ya está arreglado» los cierra.
  GUÍAS   : cada guía con dónde y cómo (instalar ffmpeg, laboratorio, compilar en la nube o en un PC antiguo…).
  Notas   : apunta algo para que Kira lo recuerde (la IP del PC, qué probaste…).
La lógica está en bitacora_kira.py (sin Kivy). Aquí no se ejecuta nada.
"""


def montar_bitacora(sm, ctx):
    from kivy.metrics import dp, sp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.screenmanager import Screen
    from kivy.uix.scrollview import ScrollView

    import bitacora_kira as bk

    boton, entrada, texto_largo = ctx["boton"], ctx["entrada"], ctx["texto_largo"]
    NEON, GRIS, VERDE, FUENTE, ir, core, ganchos = ctx["NEON"], ctx["GRIS"], ctx["VERDE"], ctx["FUENTE"], ctx["ir"], ctx["core"], ctx["ganchos"]
    bit = core.bitacora

    p = Screen(name="bitacora")
    raiz = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
    barra = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    barra.add_widget(boton("‹ Menú", lambda: ir("menu"), GRIS, alto=44, size_hint_x=None, width=dp(100)))
    import estilo_kira as _est
    barra.add_widget(_est.ajustar(Label(text="BITÁCORA DE KIRA", color=NEON, font_size=_est.tam(16), bold=True, halign="left", **FUENTE), lineas=1))
    raiz.add_widget(barra)
    pest = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    b_res = boton("RESUMEN", lambda: modo("resumen"), VERDE)
    b_fal = boton("FALLOS", lambda: modo("fallos"), GRIS)
    b_gui = boton("GUÍAS", lambda: modo("guias"), GRIS)
    for b in (b_res, b_fal, b_gui):
        pest.add_widget(b)
    raiz.add_widget(pest)
    sv_g = ScrollView(size_hint_y=None, height=0, do_scroll_x=False)
    lista = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
    lista.bind(minimum_height=lista.setter("height"))
    sv_g.add_widget(lista)
    raiz.add_widget(sv_g)
    sv, vista = texto_largo("")
    raiz.add_widget(sv)
    btn_ok = boton("Ya está arreglado", lambda: resueltos(), GRIS, disabled=True)
    raiz.add_widget(btn_ok)
    fila = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
    campo = entrada("Apunta una nota para Kira…")
    fila.add_widget(campo)
    fila.add_widget(boton("Apuntar", lambda: apuntar(), VERDE, alto=48, size_hint_x=None, width=dp(100)))
    raiz.add_widget(fila)
    p.add_widget(raiz)
    sm.add_widget(p)
    est = {"modo": "resumen"}

    def modo(nombre):
        est["modo"] = nombre
        for n_, b in (("resumen", b_res), ("fallos", b_fal), ("guias", b_gui)):
            b.background_color = VERDE if n_ == nombre else GRIS
        lista.clear_widgets()
        sv_g.height = dp(200) if nombre == "guias" else 0
        btn_ok.disabled = not (nombre == "fallos" and bit.pendientes())
        if nombre == "resumen":
            vista.text = bit.texto_resumen()
        elif nombre == "fallos":
            vista.text = bit.texto_diagnostico()
        else:
            for g in bk.PASOS:
                lista.add_widget(boton(g["titulo"][:48], lambda g_=g: setattr(vista, "text", bk.texto_paso(g_)), GRIS, alto=40))
            vista.text = "Elige una guía."

    def resueltos():
        bit.marcar_resueltos()
        modo("fallos")
        vista.text = "[OK] Fallos marcados como resueltos. Si vuelve a pasar, lo apuntaré otra vez.\n\n" + vista.text

    def apuntar():
        if bit.apuntar(campo.text):
            campo.text = ""
            modo("resumen")
            vista.text = "[OK] Apuntado.\n\n" + vista.text

    ganchos["bitacora"] = lambda: modo(est["modo"])
    return {"modo": modo}
