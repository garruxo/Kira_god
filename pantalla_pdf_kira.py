# -*- coding: utf-8 -*-
"""
pantalla_pdf_kira.py - Pantalla «Mis PDF» (Kivy): pega un enlace y Kira descarga el PDF; la lista de tus PDF; leer
página a página; resumir, preguntar, buscar, estudiar, guardar en Descargas y borrar.
La lógica está en pdf_kira.py y en el núcleo (KiraGodCore.orden_pdf).
"""


def montar_pdf(sm, p):
    from kivy.metrics import dp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView

    import estilo_kira as est
    tam = est.tam
    boton, entrada, texto_largo, pantalla, en_hilo = p["boton"], p["entrada"], p["texto_largo"], p["pantalla"], p["en_hilo"]
    TXT, TENUE, GRIS, VERDE, ROJO, FUENTE = (p[k] for k in ("TXT", "TENUE", "GRIS", "VERDE", "ROJO", "FUENTE"))
    core = p["core"]

    _, c = pantalla("pdf", "MIS PDF")
    st = {"doc": None, "pagina": 1, "ocupado": False}

    campo = entrada("Pega aquí el enlace del PDF (o una pregunta sobre el que estás leyendo)")
    c.add_widget(campo)
    fila = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
    fila.add_widget(boton("Descargar", lambda: descargar(), VERDE, alto=44))
    fila.add_widget(boton("Preguntar", lambda: preguntar(), GRIS, alto=44))
    fila.add_widget(boton("Buscar", lambda: buscar(), GRIS, alto=44))
    c.add_widget(fila)
    estado = est.ajustar(Label(text="", size_hint_y=None, height=dp(36), color=TENUE, font_size=tam(12.5),
                               halign="left", **FUENTE), minimo=10, lineas=2)
    c.add_widget(estado)

    hueco = BoxLayout()
    c.add_widget(hueco)
    sv_lista = ScrollView(do_scroll_x=False)
    lista = GridLayout(cols=1, size_hint_y=None, spacing=dp(6), padding=(0, dp(2)))
    lista.bind(minimum_height=lista.setter("height"))
    sv_lista.add_widget(lista)

    sv_pag, lbl_pag = texto_largo("")
    nav = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
    nav.add_widget(boton("‹ Lista", lambda: ver_lista(), GRIS, alto=44))
    nav.add_widget(boton("◀", lambda: pasar(-1), GRIS, alto=44))
    lbl_num = Label(text="", color=TXT, font_size=tam(13), size_hint_x=0.6, **FUENTE)
    nav.add_widget(lbl_num)
    nav.add_widget(boton("▶", lambda: pasar(1), GRIS, alto=44))
    acc = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
    acc.add_widget(boton("Resumir", lambda: orden("resume el pdf {n}"), GRIS, alto=44))
    acc.add_widget(boton("Estudiar", lambda: orden("estudia el pdf {n}"), VERDE, alto=44))
    acc.add_widget(boton("A Descargas", lambda: orden("guarda el pdf {n} en descargas"), GRIS, alto=44))
    acc.add_widget(boton("Borrar", lambda: borrar(), ROJO, alto=44))
    caja_pag = BoxLayout(orientation="vertical", spacing=dp(4))
    caja_pag.add_widget(sv_pag)
    caja_pag.add_widget(nav)
    caja_pag.add_widget(acc)

    def ocupar(t):
        st["ocupado"] = True
        estado.text = t

    def libre(t=None):
        st["ocupado"] = False
        if t is not None:
            estado.text = t

    def limpio(t):
        return str(t).replace("[OK] ", "").replace("[x] ", "").replace("[i] ", "")

    def tarjeta(e):
        texto = (f"[b]{e['n']}. {_esc(e['nombre'])}[/b]\n[color=0f8fbf]{e['paginas']} páginas · {e['bytes'] / 1e6:.1f} MB"
                 + (" · estudiado" if e.get("estudiado") else "") + "[/color]")
        b = Button(text=texto, markup=True, size_hint_y=None, height=dp(72), background_normal="", background_down="",
                   background_color=(0, 0, 0, 0), color=TXT, font_size=tam(13.5), halign="left", valign="middle", **FUENTE)
        est.fondo_redondeado(b, (1, 1, 1, 1), radio=12)
        b.bind(size=lambda w, s: setattr(w, "text_size", (s[0] - dp(20), s[1] - dp(10))))
        b.shorten, b.max_lines = True, 3
        b.bind(on_release=lambda *_: abrir(e["n"], 1))
        return b

    def ver_lista():
        lista.clear_widgets()
        bib = core.pdfs
        for e in reversed(bib.lista):
            lista.add_widget(tarjeta(e))
        if not bib.lista:
            lista.add_widget(Label(text="Aún no tienes PDF. Pega un enlace arriba y pulsa «Descargar», o comparte un "
                                        "PDF con Kira desde otra app.", color=TENUE, size_hint_y=None, height=dp(80),
                                   font_size=tam(13), halign="center", **FUENTE))
        hueco.clear_widgets()
        hueco.add_widget(sv_lista)
        st["doc"] = None

    def abrir(n, pagina=1):
        bib = core.pdfs
        e = bib.buscar_doc(str(n))
        if e is None:
            estado.text = "No tengo ese PDF."
            return False
        st["doc"], st["pagina"] = e, max(1, min(int(pagina), max(1, e["paginas"])))
        try:
            txt = bib.pagina(e, st["pagina"])
        except Exception as ex:
            txt = f"[x] No puedo leer esta página: {ex}"
        lbl_pag.text = f"{e['nombre']}\n\n" + (txt or "(Esta página no tiene texto: puede ser una imagen.)")
        lbl_num.text = f"Página {st['pagina']} de {e['paginas']}"
        hueco.clear_widgets()
        hueco.add_widget(caja_pag)
        sv_pag.scroll_y = 1
        estado.text = f"«{e['nombre']}». Escribe arriba una pregunta y pulsa «Preguntar» o «Buscar»."
        return True

    def pasar(d):
        e = st["doc"]
        if e is not None:
            abrir(e["n"], st["pagina"] + d)

    def orden(plantilla, mostrar=True, al_terminar=None):
        e = st["doc"]
        if st["ocupado"] or (e is None and "{n}" in plantilla):
            return False
        texto = plantilla.format(n=e["n"] if e else "")
        ocupar("Trabajando…")

        def fin(r):
            libre("" if not isinstance(r, Exception) else f"[x] {r}")
            if not isinstance(r, Exception):
                r = str(r)
                if r.startswith("[OK] ABRIR_PDF"):
                    partes = r.split("\n", 1)[0].split()
                    abrir(partes[2], partes[3])
                elif mostrar:
                    if st["doc"] is not None and hueco.children and hueco.children[0] is caja_pag:
                        lbl_pag.text = limpio(r) + "\n\n— — —\n\n" + lbl_pag.text
                        sv_pag.scroll_y = 1
                    else:
                        ver_lista()
                    estado.text = limpio(r)[:160]
            if al_terminar:
                al_terminar(r)
        en_hilo(lambda: core.orden_pdf(texto, al_progreso=lambda f, t: p["avance"](t)), fin)
        return True

    def descargar(url=None, al_terminar=None):
        import pdf_kira as pk
        u = pk.url_de(url if url is not None else campo.text)
        if not u:
            estado.text = "Pega el enlace del PDF (empieza por https://)."
            return False
        campo.text = ""
        ocupar("Descargando el PDF…")

        def fin(r):
            libre()
            ver_lista()
            estado.text = limpio(r)[:200] if not isinstance(r, Exception) else f"[x] {r}"
            if al_terminar:
                al_terminar(r)
        en_hilo(lambda: core.orden_pdf(f"descarga el pdf {u}", al_progreso=lambda f, t: p["avance"](t)), fin)
        return True

    def preguntar():
        q = " ".join(campo.text.split())
        if not q or st["doc"] is None:
            estado.text = "Abre un PDF y escribe tu pregunta arriba."
            return
        campo.text = ""
        orden("qué dice el pdf {n} sobre " + q.replace("{", "(").replace("}", ")"))

    def buscar():
        q = " ".join(campo.text.split())
        if not q or st["doc"] is None:
            estado.text = "Abre un PDF y escribe arriba qué buscas."
            return
        orden("busca " + q.replace("{", "(").replace("}", ")") + " en el pdf {n}")

    def borrar():
        e = st["doc"]
        if e is None:
            return
        if st.get("borrar") != e["n"]:                  # dos toques: el primero avisa
            st["borrar"] = e["n"]
            estado.text = "Pulsa «Borrar» otra vez para borrar este PDF."
            return
        st["borrar"] = None
        orden("borra el pdf {n}", al_terminar=lambda r: ver_lista())

    def al_entrar(*_):
        if st["doc"] is None:
            ver_lista()
    sm.get_screen("pdf").bind(on_pre_enter=al_entrar)
    ver_lista()
    return {"descargar": descargar, "abrir": abrir, "ver_lista": ver_lista, "orden": orden}


def _esc(t):
    return str(t).replace("&", "&amp;").replace("[", "&bl;").replace("]", "&br;")
