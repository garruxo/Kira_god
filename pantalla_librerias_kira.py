# -*- coding: utf-8 -*-
"""
pantalla_librerias_kira.py - Pantalla «Librerías» (Kivy): escribe el nombre de una librería de Python, Kira te dice qué
es, qué más necesita y cuánto pesa, y SOLO tú la instalas (dos toques en «Instalar»). La lista de las instaladas, con
«Quitar». La lógica está en librerias_kira.py.
"""


def montar_librerias(sm, p):
    from kivy.clock import Clock
    from kivy.metrics import dp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView

    import estilo_kira as est
    import librerias_kira as lk
    tam = est.tam
    boton, entrada, texto_largo, pantalla, en_hilo = p["boton"], p["entrada"], p["texto_largo"], p["pantalla"], p["en_hilo"]
    TXT, TENUE, GRIS, VERDE, ROJO, FUENTE = (p[k] for k in ("TXT", "TENUE", "GRIS", "VERDE", "ROJO", "FUENTE"))
    core = p["core"]

    _, c = pantalla("librerias", "LIBRERÍAS DE PYTHON")
    st = {"ocupado": False, "reloj": None}
    campo = entrada("Nombre de la librería (ej.: kivymd, rich, sympy, networkx)")
    c.add_widget(campo)
    fila = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
    fila.add_widget(boton("Ver qué es", lambda: ver(), GRIS, alto=44))
    btn_inst = boton("Instalar", lambda: instalar(), VERDE, alto=44)
    btn_inst.disabled = True
    fila.add_widget(btn_inst)
    c.add_widget(fila)
    sv, lbl = texto_largo("Escribe el nombre de una librería de PyPI y pulsa «Ver qué es». Antes de instalar nada, te "
                          "digo qué es, qué más necesita y cuánto pesa. Instalar: dos toques.\n\nSolo valen las de "
                          "Python puro (las que llevan partes compiladas, como pandas o torch, no tienen versión para "
                          "el móvil; numpy ya lo llevo dentro).")
    sv.size_hint_y = 0.45
    c.add_widget(sv)
    c.add_widget(est.ajustar(Label(text="Instaladas", size_hint_y=None, height=dp(28), color=TENUE, font_size=tam(13),
                                   halign="left", **FUENTE), minimo=10))
    sv_l = ScrollView(do_scroll_x=False)
    lista = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
    lista.bind(minimum_height=lista.setter("height"))
    sv_l.add_widget(lista)
    c.add_widget(sv_l)

    def lib():
        return getattr(core, "librerias", None)

    def pintar_lista():
        lista.clear_widgets()
        L = lib()
        if L is None or not L.indice:
            lista.add_widget(Label(text="(ninguna todavía)", color=TENUE, size_hint_y=None, height=dp(36),
                                   font_size=tam(13), **FUENTE))
            return
        for n, e in sorted(L.indice.items()):
            f = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(4))
            f.add_widget(est.ajustar(Label(text=f"{e.get('nombre', n)} {e.get('version', '')} · "
                                                f"import {', '.join(e.get('importa', [])[:3])}",
                                           color=TXT, font_size=tam(13), halign="left", **FUENTE), minimo=10, lineas=2))
            f.add_widget(boton("Quitar", lambda n_=n: quitar(n_), ROJO, alto=42, size_hint_x=None, width=dp(84)))
            lista.add_widget(f)

    def reiniciar(*_):
        if st["reloj"] is not None:
            st["reloj"].cancel()
        st["reloj"] = None
        btn_inst.text = "Instalar"

    def ver(nombre=None, al_terminar=None):
        L = lib()
        nombre = " ".join(str(nombre if nombre is not None else campo.text).split())
        if L is None or not nombre or st["ocupado"]:
            return False
        campo.text = nombre
        st["ocupado"] = True
        btn_inst.disabled = True
        reiniciar()
        lbl.text = f"Mirando «{nombre}» en PyPI…"

        def fin(r):
            st["ocupado"] = False
            if isinstance(r, Exception):
                lbl.text = f"[x] {r}"
            else:
                lbl.text = L.texto_plan(r) + "\n\nToca «Instalar» dos veces para instalarla."
                btn_inst.disabled = False
            if al_terminar:
                al_terminar(r)
        en_hilo(lambda: L.preparar(nombre), fin)
        return True

    def instalar():
        L = lib()
        if L is None or L.pendiente is None or st["ocupado"]:
            return
        if st["reloj"] is None:                           # primer toque: pide confirmar
            btn_inst.text = "¿Seguro? Toca otra vez"
            st["reloj"] = Clock.schedule_once(reiniciar, 6)
            return
        reiniciar()
        st["ocupado"] = True
        btn_inst.disabled = True
        lbl.text = "Instalando…"

        def prog(f, t):
            p["avance"](t, f)

        def fin(r):
            st["ocupado"] = False
            if isinstance(r, Exception):
                lbl.text = f"[x] {r}"
            else:
                lbl.text = (f"[OK] Instalado: {', '.join(r)}.\n\nYa puedes importarla en el editor, en los programas que "
                            "te escriba y en las mejoras.")
                if callable(p.get("decir")):
                    p["decir"](f"Instalada: {r[-1]}. Ya la puedo usar al programar.")
            pintar_lista()
        en_hilo(lambda: L.instalar_pendiente(True, progreso=prog), fin)

    def quitar(nombre):
        L = lib()
        if L is None:
            return
        try:
            e = L.quitar(nombre)
            lbl.text = f"[OK] He quitado «{e.get('nombre', nombre)}»."
        except lk.LibreriaError as ex:
            lbl.text = f"[x] {ex}"
        pintar_lista()

    sm.get_screen("librerias").bind(on_pre_enter=lambda *_: pintar_lista())
    pintar_lista()
    return {"ver": ver, "pintar_lista": pintar_lista}
