# -*- coding: utf-8 -*-
"""
pantalla_internet_kira.py - Pantalla «Internet» (Kivy): Kira busca en la web, en código o en documentos, lee la página
que elijas (solo el texto y el código), la resume, la aprende (a su baúl) o lleva su código al editor.
La lógica está en internet_kira.py y en el núcleo (resumir_pagina, guardar_pagina, estudiar_en_internet).
"""
import internet_kira as ik


def montar_internet(sm, p):
    from kivy.clock import Clock
    from kivy.metrics import dp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView

    import estilo_kira as est
    tam = est.tam
    boton, entrada, texto_largo, pantalla, en_hilo = p["boton"], p["entrada"], p["texto_largo"], p["pantalla"], p["en_hilo"]
    TXT, TENUE, GRIS, VERDE, NEON, FUENTE = (p[k] for k in ("TXT", "TENUE", "GRIS", "VERDE", "NEON", "FUENTE"))
    core = p["core"]
    net = core.internet

    _, c = pantalla("internet", "INTERNET")
    st = {"tipo": "web", "pagina": None, "n": None, "ocupado": False}

    campo = entrada("¿Qué busco? (ej.: cómo plantar tomates)")
    c.add_widget(campo)
    fila_t = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
    btn_tipo = {}
    for clave, nombre in (("web", "Web"), ("codigo", "Código"), ("docs", "Docs")):
        btn_tipo[clave] = boton(nombre, lambda k=clave: elegir_tipo(k), GRIS, alto=44)
        fila_t.add_widget(btn_tipo[clave])
    fila_t.add_widget(boton("Buscar", lambda: buscar(), VERDE, alto=44))
    c.add_widget(fila_t)
    estado = est.ajustar(Label(text="", size_hint_y=None, height=dp(36), color=TENUE, font_size=tam(12.5),
                               halign="left", **FUENTE), minimo=10, lineas=2)
    c.add_widget(estado)

    hueco = BoxLayout()                                   # aquí va la lista de resultados o la página que lees
    c.add_widget(hueco)
    sv_lista = ScrollView(do_scroll_x=False)
    lista = GridLayout(cols=1, size_hint_y=None, spacing=dp(6), padding=(0, dp(2)))
    lista.bind(minimum_height=lista.setter("height"))
    sv_lista.add_widget(lista)
    sv_pag, lbl_pag = texto_largo("")
    acciones = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
    acciones.add_widget(boton("‹ Lista", lambda: ver_lista(), GRIS, alto=44))
    acciones.add_widget(boton("Resumir", lambda: resumir(), GRIS, alto=44))
    acciones.add_widget(boton("Aprender", lambda: aprender(), VERDE, alto=44))
    btn_editor = boton("Al editor", lambda: al_editor(), GRIS, alto=44)
    acciones.add_widget(btn_editor)
    acciones.add_widget(boton("Navegador", lambda: navegador(), GRIS, alto=44))
    caja_pag = BoxLayout(orientation="vertical", spacing=dp(4))
    caja_pag.add_widget(sv_pag)
    caja_pag.add_widget(acciones)
    pie = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
    pie.add_widget(boton("Estudiar el tema (leer y aprender)", lambda: estudiar(), VERDE, alto=44))
    c.add_widget(pie)

    def elegir_tipo(k):
        st["tipo"] = k
        for clave, b in btn_tipo.items():
            b.background_color = VERDE if clave == k else GRIS
            b.color = (1, 1, 1, 1) if clave == k else TXT

    def ver_lista():
        hueco.clear_widgets()
        hueco.add_widget(sv_lista)
        st["pagina"] = None

    def ver_pagina():
        hueco.clear_widgets()
        hueco.add_widget(caja_pag)
        sv_pag.scroll_y = 1

    def tarjeta(i, r):
        texto = f"[b]{i}. {_esc(r['titulo'])}[/b]\n[color=0f8fbf]{_esc(r['fuente'])}[/color]" + \
                (f"\n{_esc(r['resumen'])}" if r.get("resumen") else "")
        b = Button(text=texto, markup=True, size_hint_y=None, height=dp(96), background_normal="", background_down="",
                   background_color=(0, 0, 0, 0), color=TXT, font_size=tam(13.5), halign="left", valign="top", **FUENTE)
        est.fondo_redondeado(b, (1, 1, 1, 1), radio=12)
        b.bind(size=lambda w, s: setattr(w, "text_size", (s[0] - dp(20), s[1] - dp(14))))
        b.shorten, b.max_lines = True, 4
        b.bind(on_release=lambda *_: leer(i))
        return b

    def pintar_lista(res):
        lista.clear_widgets()
        for i, r in enumerate(res, 1):
            lista.add_widget(tarjeta(i, r))
        ver_lista()

    def ocupar(texto):
        st["ocupado"] = True
        estado.text = texto

    def libre(texto=None):
        st["ocupado"] = False
        if texto is not None:
            estado.text = texto

    # ---------- acciones ----------
    def buscar(consulta=None, tipo=None, al_terminar=None):
        if st["ocupado"]:
            return False
        consulta = " ".join(str(consulta if consulta is not None else campo.text).split())
        if len(consulta) < 2:
            estado.text = "Escribe qué quieres que busque."
            return False
        if tipo:
            elegir_tipo(tipo)
        campo.text = consulta
        ocupar(f"Buscando «{consulta}»…")

        def fin(r):
            if isinstance(r, Exception):
                libre(f"[x] {r}")
                lista.clear_widgets()
                ver_lista()
            else:
                pintar_lista(r)
                libre(f"{len(r)} resultado(s). Toca uno para leerlo." + (f" ({net.avisos[0]})" if net.avisos else ""))
            if al_terminar:
                al_terminar(r)
        en_hilo(lambda: net.buscar(consulta, st["tipo"]), fin)
        return True

    def leer(n, al_terminar=None):
        if st["ocupado"]:
            return False
        try:
            r = net.resultado(n)
        except ik.InternetError as e:
            estado.text = f"[x] {e}"
            return False
        ocupar(f"Leyendo {r['fuente']}…")

        def fin(pag):
            if isinstance(pag, Exception):
                libre(f"[x] {pag}")
            else:
                st["pagina"], st["n"] = pag, n
                lbl_pag.text = ik.Internet.texto_pagina(pag, maximo=12000)
                btn_editor.disabled = not pag["codigos"]
                ver_pagina()
                libre(f"«{pag['titulo'][:60]}» · {ik.dominio(pag['url'])}")
            if al_terminar:
                al_terminar(pag)
        en_hilo(lambda: core.leer_resultado(n), fin)
        return True

    def resumir():
        pag = st["pagina"]
        if pag is None or st["ocupado"]:
            return
        ocupar("Resumiendo…")

        def fin(r):
            if isinstance(r, Exception):
                libre(f"[x] {r}")
                return
            texto, con = r
            lbl_pag.text = f"RESUMEN de «{pag['titulo']}»\n\n{texto}" + (
                "" if con else "\n\n(Sin cerebro encendido no sé resumir: es el principio de la página.)") + \
                "\n\n— — —\n\n" + ik.Internet.texto_pagina(pag, maximo=8000)
            sv_pag.scroll_y = 1
            libre("Resumen hecho." if con else "Sin cerebro: te enseño el principio.")
        en_hilo(lambda: core.resumir_pagina(pag, campo.text), fin)

    def aprender():
        pag = st["pagina"]
        if pag is None or st["ocupado"]:
            return
        ocupar("Aprendiéndolo…")
        en_hilo(lambda: core.guardar_pagina(pag, campo.text),
                lambda r: libre(f"[x] {r}" if isinstance(r, Exception) else
                                ("Aprendido: está en mi baúl con su fuente." if r[0] else "Eso ya lo tenía aprendido.")))

    def al_editor():
        pag = st["pagina"]
        if pag is None:
            return
        codigo = net.codigo_de(pag)
        if not codigo:
            estado.text = "Esta página no tiene código."
            return
        p["abrir_en_editor"](codigo, f"Código de {ik.dominio(pag['url'])}: revísalo y pulsa «Ejecutar» "
                                     "(modo seguro). Lo de internet nunca se ejecuta solo.")

    def navegador():
        pag = st["pagina"]
        movil = getattr(core, "movil", None)
        if pag is None:
            return
        if movil is None:
            estado.text = pag["url"]
            return
        hecho, texto = movil.hacer({"tipo": "web", "url": pag["url"]})
        estado.text = ("" if hecho else "[x] ") + texto

    def estudiar(consulta=None, al_terminar=None):
        consulta = " ".join(str(consulta if consulta is not None else campo.text).split())
        if len(consulta) < 2 or st["ocupado"]:
            estado.text = "Escribe el tema que quieres que estudie."
            return False
        campo.text = consulta
        ocupar(f"Estudiando «{consulta}»: busco, leo las mejores páginas y lo guardo…")

        def paso(texto):
            Clock.schedule_once(lambda _dt: setattr(estado, "text", texto), 0)

        def fin(r):
            libre(f"[x] {r}" if isinstance(r, Exception) else str(r))
            if not isinstance(r, Exception) and net.ultimos:
                pintar_lista(net.ultimos)
            if al_terminar:
                al_terminar(r)
        en_hilo(lambda: core.estudiar_en_internet(consulta, al_paso=paso), fin)
        return True

    def al_entrar():
        if not lista.children and net.ultimos:
            pintar_lista(net.ultimos)
        if not hueco.children:
            ver_lista()
        if not estado.text:
            estado.text = "Busca lo que quieras: Kira lee las páginas por ti (solo el texto y el código)."

    elegir_tipo("web")
    ver_lista()
    p["ganchos"]["internet"] = al_entrar
    return {"buscar": buscar, "leer": leer, "estudiar": estudiar}


def _esc(t):
    """Texto seguro para el formato [b]…[/b] de Kivy."""
    return str(t or "").replace("&", "&amp;").replace("[", "&bl;").replace("]", "&br;")
