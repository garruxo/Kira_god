# -*- coding: utf-8 -*-
"""
sala_hacker_kira.py - Pantallas de la SALA HACKER inmersiva (Kivy). Se montan dentro de interfaz_kira.py.

  sala_hacker : la habitación 3D (habitacion_kira.py). Caminas hasta la mesa y miras alrededor.
  terminal    : el ordenador. Dos modos:  APRENDER (mini-curso, lecciones, comprobar sintaxis)
                                          MEJORAR  (pedir un módulo a Kira -> laboratorio del móvil -> tú decides)
  biblioteca  : tus libros (lecciones, apuntes), los módulos instalados y lo que Kira ha aprendido.

Honesto: las mejoras se instalan como MÓDULOS (comandos nuevos) y solo tras la prueba del laboratorio y tu
confirmación. No modifican el núcleo ni la aplicación en sí. Aquí no se ejecuta código.
La lógica está en programacion_kira.py y habitacion_kira.py (sin Kivy); esto son pantallas finas.
"""
import os


def montar_sala_hacker(sm, ctx):
    """Añade las pantallas al ScreenManager 'sm'. ctx: ayudas de interfaz_kira (ver abajo).
    Devuelve {'detener': fn, 'volver_a_sala': fn} para que la interfaz gestione la navegación."""
    import estilo_kira as _est
    _tam = _est.tam
    from kivy.clock import Clock
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
    from kivy.uix.screenmanager import Screen
    from kivy.uix.scrollview import ScrollView
    from kivy.metrics import dp, sp

    import habitacion_kira as hk
    import inicio_kira as ik
    import programacion_kira as pk
    import curso_avanzado_kira as ca
    import explicacion_codigo_kira as exc

    boton, entrada, texto_largo, en_hilo = ctx["boton"], ctx["entrada"], ctx["texto_largo"], ctx["en_hilo"]
    TXT, NEON, TENUE, GRIS, VERDE, ROJO = (ctx[k] for k in ("TXT", "NEON", "TENUE", "GRIS", "VERDE", "ROJO"))
    FUENTE, ir, ctl, core, cerebro, voz = ctx["FUENTE"], ctx["ir"], ctx["ctl"], ctx["core"], ctx["cerebro"], ctx["voz"]
    ganchos = ctx["ganchos"]
    biblioteca = pk.Biblioteca(os.path.join(ctx["dir_datos"], "biblioteca.json"))
    estado = {"volver": False, "escuchando": None}

    def etiqueta(texto="", alto=24, color=TENUE, **kw):
        lb = Label(text=texto, size_hint_y=None, height=dp(alto), color=color, font_size=_tam(13), halign="left",
                   valign="middle", **FUENTE, **kw)
        return _est.ajustar(lb, minimo=10, lineas=max(1, int(alto // 17)))

    def barra(titulo, destino_texto, accion):
        b = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        b.add_widget(boton(destino_texto, accion, GRIS, alto=44, size_hint_x=None, width=dp(100)))
        b.add_widget(_est.ajustar(Label(text=titulo, color=NEON, font_size=_tam(16), bold=True, halign="left", **FUENTE), lineas=1))
        return b

    # =================================================================================
    #  SALA (habitación 3D)
    # =================================================================================
    HabitacionWidget = hk.crear_widgets()
    p_sala = Screen(name="sala_hacker")
    raiz = BoxLayout(orientation="vertical")
    raiz.add_widget(barra("SALA HACKER", "‹ Menú", lambda: salir_al_menu()))
    habitacion = HabitacionWidget(size_hint_y=1)
    raiz.add_widget(habitacion)
    kira_dice = etiqueta("", alto=40, color=TXT)
    raiz.add_widget(kira_dice)
    fila_ir = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4), padding=(dp(6), 0))
    for txt_b, destino in (("< Biblioteca", "biblioteca"), ("Ordenador", "ordenador"), ("Salida >", "salida")):
        fila_ir.add_widget(boton(txt_b, lambda d=destino: ordenar(d), GRIS, alto=44))
    raiz.add_widget(fila_ir)
    campo = entrada("Di o escribe: hackear, programar, biblioteca, salir…")
    fila_in = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6), padding=(dp(6), dp(2)))
    fila_in.add_widget(campo)
    fila_in.add_widget(boton("Mic", lambda: escuchar(), VERDE, alto=48, size_hint_x=None, width=dp(64)))
    fila_in.add_widget(boton("Ir", lambda: enviar(), VERDE, alto=48, size_hint_x=None, width=dp(64)))
    raiz.add_widget(fila_in)
    p_sala.add_widget(raiz)
    sm.add_widget(p_sala)

    def decir(texto, hablar=False):
        kira_dice.text = texto
        if hablar and ctx["ajustes"].voz_hablar:
            voz.hablar(texto)

    def ordenar(destino):
        if habitacion.rec.ordenar(destino):
            decir({"ordenador": "Me acerco al ordenador…", "biblioteca": "Vamos a la biblioteca…",
                   "salida": "Vamos hacia la salida…"}[destino])
        else:
            decir("Espera un momento…")

    def enviar():
        texto = ik.limpiar_entrada(campo.text)
        if not texto:
            return
        campo.text = ""
        destino = hk.intencion_sala(texto)
        if destino:
            ordenar(destino)
        else:
            decir("Prueba con «hackear», «programar», «biblioteca» o «salir».")

    def escuchar():
        if estado["escuchando"] is not None:
            return
        ok, msg = voz.iniciar_escucha()
        decir(msg)
        if not ok:
            return
        t = {"s": 0.0}

        def sondeo(dt):
            t["s"] += dt
            est, txt = voz.sondear()
            if est == "escuchando" and t["s"] < 12:
                return
            estado["escuchando"].cancel()
            estado["escuchando"] = None
            if est == "listo" and txt:
                campo.text = txt
                enviar()
            else:
                voz.parar_escucha()
                decir("No te he oído. Prueba otra vez o escríbeme.")
        estado["escuchando"] = Clock.schedule_interval(sondeo, 0.4)

    def al_evento(ev):
        if ev == "ordenador":
            decir("Conectando con el ordenador…", hablar=True)
            Clock.schedule_once(lambda _dt: ir("terminal"), 0.4)
        elif ev == "biblioteca":
            ir("biblioteca")
        elif ev == "salida":
            salir_al_menu()

    def al_tocar(hot):
        if hot is None and habitacion.rec.estado == "libre":
            decir("Toca el ordenador, la biblioteca o la puerta. Arrastra para mirar alrededor.")

    habitacion.al_evento, habitacion.al_tocar = al_evento, al_tocar

    def salir_al_menu():
        habitacion.rec.reiniciar()
        ir("menu")

    def entrar_sala():
        if estado["volver"]:
            estado["volver"] = False
            habitacion.rec.volver()
            decir("De vuelta en la mesa. Arrastra para mirar alrededor.")
        else:
            habitacion.rec.reiniciar()
            decir("Entrando en la sala…")
        habitacion.iniciar()

    def detener():
        habitacion.detener()
        if estado["escuchando"] is not None:
            estado["escuchando"].cancel()
            estado["escuchando"] = None
            voz.parar_escucha()

    def volver_a_sala():
        estado["volver"] = True
        ir("sala_hacker")
    ganchos["sala_hacker"] = entrar_sala

    # =================================================================================
    #  TERMINAL (aprender / mejorar)
    # =================================================================================
    p_term = Screen(name="terminal")
    r_term = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
    r_term.add_widget(barra("KIRA//TERMINAL [conectado]", "‹ Sala", volver_a_sala))
    pestanas = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    cuerpo = BoxLayout(orientation="vertical", spacing=dp(6))
    btn_apr = boton("APRENDER", lambda: modo("aprender"), VERDE)
    btn_mej = boton("MEJORAR", lambda: modo("mejorar"), GRIS)
    btn_trab = boton("TRABAJO", lambda: modo("trabajo"), GRIS)
    pestanas.add_widget(btn_apr)
    pestanas.add_widget(btn_mej)
    pestanas.add_widget(btn_trab)
    r_term.add_widget(pestanas)
    r_term.add_widget(cuerpo)
    p_term.add_widget(r_term)
    sm.add_widget(p_term)

    # ---- APRENDER ----
    c_apr = BoxLayout(orientation="vertical", spacing=dp(6))
    fila_niv = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
    niveles = {"Básico": pk.CURSO, "Avanzado": ca.CURSO_AVANZADO, "Códigos": ca.CODIGOS,
               "Ingeniería": ca.CURSO_INGENIERIA, "Diseño": ca.CURSO_DISENO}
    botones_niv = {}
    for nombre_n in niveles:
        botones_niv[nombre_n] = boton(nombre_n, lambda n_=nombre_n: pintar_lecciones(n_), GRIS, alto=40)
        fila_niv.add_widget(botones_niv[nombre_n])
    c_apr.add_widget(fila_niv)
    sv_lecc = ScrollView(size_hint_y=0.26, do_scroll_x=False)
    rej = GridLayout(cols=2, spacing=dp(6), size_hint_y=None, row_default_height=dp(42), row_force_default=True)
    rej.bind(minimum_height=rej.setter("height"))
    sv_lecc.add_widget(rej)
    c_apr.add_widget(sv_lecc)
    sv_vista, vista = texto_largo("Elige una lección del mini-curso o pídele una a Kira.")
    c_apr.add_widget(sv_vista)
    est_apr = etiqueta("", alto=40, color=TXT)
    c_apr.add_widget(est_apr)
    actual = {"titulo": "", "texto": "", "codigo": ""}

    def mostrar_leccion(titulo, explicacion, codigo):
        actual.update(titulo=titulo, texto=explicacion, codigo=codigo)
        vista.text = f"{titulo}\n\n{explicacion}\n\nEjemplo:\n{codigo}"
        est_apr.text = ""

    def pintar_lecciones(nivel="Básico"):
        rej.clear_widgets()
        rej.cols = 1 if max(len(l["titulo"]) for l in niveles[nivel]) > 26 else 2   # títulos largos: uno por fila
        for n_, b_ in botones_niv.items():
            b_.background_color = VERDE if n_ == nivel else GRIS
        for l in niveles[nivel]:
            rej.add_widget(boton(l["titulo"], lambda l_=l: mostrar_leccion(l_["titulo"], l_["texto"], l_["codigo"]), GRIS, alto=42))
    pintar_lecciones("Básico")

    def abrir_editor():
        if not actual["codigo"]:
            est_apr.text = "Elige una lección primero."
            return
        if ctx.get("abrir_en_editor"):
            ctx["abrir_en_editor"](actual["codigo"], f"{actual['titulo']}: pulsa «Ejecutar» y cámbialo a tu gusto.")

    def comprobar():
        if not actual["codigo"]:
            est_apr.text = "Elige una lección primero."
            return
        est_apr.text = pk.comprobar_sintaxis(actual["codigo"])[1]

    def guardar():
        if not actual["titulo"]:
            est_apr.text = "Elige una lección primero."
            return
        try:
            est_apr.text = pk.guardar_leccion(biblioteca, cerebro.conocimiento, actual["titulo"],
                                              f"{actual['texto']}\n\nEjemplo:\n{actual['codigo']}")[1]
        except OSError as e:
            est_apr.text = f"No se pudo guardar: {e}"
    fila_a = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    fila_a.add_widget(boton("Comprobar sintaxis", comprobar, GRIS))
    fila_a.add_widget(boton("Abrir en el editor", abrir_editor, GRIS))
    fila_a.add_widget(boton("Guardar en biblioteca", guardar, VERDE))
    c_apr.add_widget(fila_a)
    campo_tema = entrada("Pídele a Kira una lección sobre…")
    c_apr.add_widget(campo_tema)
    btn_pedir = boton("Pedir lección a Kira (usa la API)", lambda: pedir_leccion(), GRIS)
    c_apr.add_widget(btn_pedir)

    def pedir_leccion():
        tema = ik.limpiar_entrada(campo_tema.text)
        if not tema or btn_pedir.disabled:
            return
        btn_pedir.disabled = True
        est_apr.text = "Kira está preparando la lección…"

        def terminado(r):
            btn_pedir.disabled = False
            if isinstance(r, Exception):
                est_apr.text = f"[x] {r}"
            else:
                mostrar_leccion(*r)
                est_apr.text = "Lección lista. Revísala; guárdala si te sirve."
        en_hilo(lambda: core.generar_leccion(tema), terminado)

    # ---- MEJORAR ----
    c_mej = BoxLayout(orientation="vertical", spacing=dp(6))
    alcances = {"Kira": "una función nueva para Kira (un comando de texto)",
                "Sistema": "un comando que informe sobre el sistema o el dispositivo (solo lectura)",
                "Aplicación": "un comando que mejore el uso de la aplicación"}
    alcance = {"v": "Kira"}
    fila_al = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
    botones_al = {}

    def elegir(nombre):
        alcance["v"] = nombre
        for n, b in botones_al.items():
            b.background_color = VERDE if n == nombre else GRIS
    for n in alcances:
        botones_al[n] = boton(n, lambda n_=n: elegir(n_), VERDE if n == "Kira" else GRIS, alto=40)
        fila_al.add_widget(botones_al[n])
    c_mej.add_widget(fila_al)
    import version_kira
    c_mej.add_widget(etiqueta(f"Kira {version_kira.VERSION}: la programa (o usa una receta probada: «receta de …»), la "
                              "prueba en su laboratorio del móvil y se instala como orden nueva solo con tus dos toques.",
                              alto=52))
    campo_mej = entrada("Qué quieres que Kira aprenda a hacer…")
    c_mej.add_widget(campo_mej)
    btn_env = boton("Pedir mejora", lambda: enviar_mejora(), VERDE)
    c_mej.add_widget(btn_env)
    sv_res, res = texto_largo("")
    c_mej.add_widget(sv_res)
    btn_aplicar = boton("Aplicar", lambda: aplicar(), VERDE, disabled=True)
    btn_rechazar = boton("Rechazar", lambda: rechazar(), ROJO, disabled=True)
    fila_d = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
    fila_d.add_widget(btn_aplicar)
    fila_d.add_widget(btn_rechazar)
    c_mej.add_widget(fila_d)
    confirmacion = {"reloj": None}

    def decision(activas):
        btn_aplicar.disabled = btn_rechazar.disabled = not activas
        if not activas:
            reiniciar_confirmacion()

    def reiniciar_confirmacion(*_):
        if confirmacion["reloj"] is not None:
            confirmacion["reloj"].cancel()
        confirmacion["reloj"] = None
        btn_aplicar.text = "Aplicar"

    def mostrar_codigo_explicado():
        """Enseña el CÓDIGO que Kira escribió y lo explica línea por línea (técnico, para aprender)."""
        pend = getattr(ctl, "pendiente", None)
        cod = getattr(pend, "codigo", "") if pend is not None else ""
        if not cod:
            return
        try:
            expl = exc.texto_plano(cod)
        except Exception:
            expl = ""
        res.text += ("\n\n——— EL CÓDIGO QUE ESCRIBIÓ ———\n" + cod.rstrip() +
                     ("\n\n——— CÓMO FUNCIONA (técnico) ———\n" + expl if expl else ""))

    def enviar_mejora(al_terminar=None, codigo=None):
        pedido = ik.limpiar_entrada(campo_mej.text)
        if not pedido or btn_env.disabled:
            if al_terminar is not None:                  # quien lo pidió por voz tiene que enterarse
                al_terminar({"ok": False, "aprobable": False,
                             "texto": "[x] Ya estoy con otra mejora." if pedido else "[x] No hay pedido."})
            return
        btn_env.disabled = True
        decision(False)
        res.text = "Kira está trabajando… (generar, probar y reintentar puede tardar un minuto)"
        completo = f"Mejora para {alcances[alcance['v']]}: {pedido}"

        def terminado(r):
            btn_env.disabled = False
            if isinstance(r, Exception):
                res.text = f"[x] {r}"
                if al_terminar is not None:
                    al_terminar({"ok": False, "aprobable": False, "texto": f"[x] {r}"})
                return
            res.text = r["texto"] + (f"\n\n(Intentos: {r['intentos']})" if r.get("intentos") else "")
            mostrar_codigo_explicado()
            decision(bool(r.get("aprobable")))
            if al_terminar is not None:
                al_terminar(r)
        if codigo is not None:
            en_hilo(lambda: ctl.probar_codigo(codigo, pedido=pedido), terminado)
        else:
            en_hilo(lambda: ctl.enviar_orden(completo), terminado)

    if getattr(ctl, "pendiente", None) is not None and getattr(ctl, "recuperada", False):
        # Kira se cerró con una mejora ya probada esperando tus dos toques: sigue aquí
        res.text = ("Tenías esta mejora esperando tu decisión (de antes de que se cerrara Kira):\n\n"
                    + ctl.pendiente.resumen())
        Clock.schedule_once(lambda _dt: decision(True), 0)

    def aplicar():
        pend = ctl.pendiente
        if pend is None:
            res.text = "[x] No hay ninguna mejora pendiente."
            return
        if confirmacion["reloj"] is None:                       # primer toque: pide confirmar y enseña los avisos
            avisos = pend.resultado.get("avisos", [])
            extra = ("\n\nATENCIÓN, este código usa:\n- " + "\n- ".join(str(a) for a in avisos)) if avisos else ""
            res.text += (f"\n\n¿Instalar el módulo '{pend.nombre}'? Se guarda copia y se revierte solo si falla al cargar. "
                         f"Corre dentro de Kira con sus mismos permisos.{extra}\nToca «Aplicar» otra vez (6 s) para confirmar.")
            btn_aplicar.text = "¿Seguro? Toca otra vez"
            confirmacion["reloj"] = Clock.schedule_once(reiniciar_confirmacion, 6)
            return
        reiniciar_confirmacion()
        btn_aplicar.disabled = btn_rechazar.disabled = True
        def aplicado(r):
            res.text = res.text + "\n\n" + (r["texto"] if isinstance(r, dict) else f"[x] {r}")
            voz_ = ctx.get("voz")
            if isinstance(r, dict) and r.get("ok") and voz_ is not None and "Úsala diciendo" in r["texto"]:
                try:
                    voz_.hablar("Instalada. Úsala diciendo " + r["texto"].split("Úsala diciendo:", 1)[1].strip()[:200])
                except Exception:
                    pass
        en_hilo(lambda: ctl.aplicar(True), aplicado)

    def rechazar():
        if ctl.pendiente is None:
            return
        r = ctl.rechazar("rechazada desde la terminal")
        res.text += "\n\n" + r["texto"]
        decision(False)

    # ---- TRABAJO (la consola en vivo: código escribiéndose + pruebas, y Detener/Corregir/Borrar) ----
    con_trab = ctx.get("consola")
    c_trab = BoxLayout(orientation="vertical", spacing=dp(6))
    c_trab.add_widget(etiqueta("Lo que Kira está haciendo en vivo: el código según lo escribe y sus pruebas (✓/✗). "
                               "Puedes pararla, corregir (lo recuerda) o borrar el proceso.", alto=52))
    sv_trab, res_trab = texto_largo("Aquí me verás trabajar cuando me des una orden: escribir un programa, un "
                                    "experimento o entrenar mis defensas. Dímelo y empiezo.")
    c_trab.add_widget(sv_trab)
    campo_corr = entrada("Corrige algo para que lo recuerde la próxima vez…")
    c_trab.add_widget(campo_corr)
    fila_t = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
    fila_t.add_widget(boton("Detener", lambda: detener_trabajo(), ROJO))
    fila_t.add_widget(boton("Corregir", lambda: corregir_trabajo(), VERDE))
    fila_t.add_widget(boton("Borrar proceso", lambda: borrar_proceso(), GRIS))
    c_trab.add_widget(fila_t)
    estado_trab = {"v": -1, "cod": "", "expl": ""}

    def detener_trabajo():
        if con_trab is not None:
            con_trab.pedir_detener()
        try:
            core.cancelar()
        except Exception:
            pass

    def borrar_proceso():
        detener_trabajo()
        if con_trab is not None:
            con_trab.terminar("Proceso borrado. Lista para otra cosa.")

    def corregir_trabajo():
        txt = ik.limpiar_entrada(campo_corr.text)
        if not txt:
            return
        pedido = getattr(con_trab, "pedido", "") if con_trab is not None else ""
        try:
            guardado = core.recordar_correccion(pedido, txt)
        except Exception:
            guardado = False
        campo_corr.text = ""
        if con_trab is not None:
            con_trab.linea(("✎ Corrección guardada: " + txt) if guardado else "✎ No pude guardar la corrección")

    def refrescar_trabajo(_dt=None):
        if con_trab is None or sm.current != "terminal" or estado.get("modo") != "trabajo":
            return
        v = con_trab.version()
        if v == estado_trab["v"]:
            return
        estado_trab["v"] = v
        cod = con_trab.ultimo_codigo()
        expl = ""
        if cod and not con_trab.codigo_vivo_txt:          # solo explico el bloque ya terminado
            if cod != estado_trab["cod"]:
                estado_trab["cod"] = cod
                try:
                    estado_trab["expl"] = exc.texto_plano(cod)
                except Exception:
                    estado_trab["expl"] = ""
            expl = estado_trab["expl"]
        try:
            res_trab.text = con_trab.texto(expl)
        except Exception:
            res_trab.text = con_trab.texto()
        try:
            sv_trab.scroll_y = 0
        except Exception:
            pass
    Clock.schedule_interval(refrescar_trabajo, 0.4)

    def abrir_trabajo(*_):
        estado["modo_siguiente"] = "trabajo"
        ir("terminal")
        modo("trabajo")
        estado_trab["v"] = -1
        refrescar_trabajo()

    def modo(nombre):
        cuerpo.clear_widgets()
        cuerpo.add_widget(c_apr if nombre == "aprender" else c_trab if nombre == "trabajo" else c_mej)
        btn_apr.background_color = VERDE if nombre == "aprender" else GRIS
        btn_mej.background_color = VERDE if nombre == "mejorar" else GRIS
        btn_trab.background_color = VERDE if nombre == "trabajo" else GRIS
        estado["modo"] = nombre
        if nombre == "trabajo":
            refrescar_trabajo()

    def al_entrar_terminal():
        siguiente = estado.pop("modo_siguiente", None)
        modo(siguiente or "aprender")
    ganchos["terminal"] = al_entrar_terminal

    def preparar_mejora(texto, nombre_alcance="Kira"):
        """Abre la terminal en MEJORAR con el pedido ya escrito (lo usa el Taller). No envía nada: lo envías tú."""
        elegir(nombre_alcance if nombre_alcance in alcances else "Kira")
        campo_mej.text = str(texto)
        res.text = "Pedido preparado por el Taller. Revísalo y pulsa «Pedir mejora»."
        estado["modo_siguiente"] = "mejorar"
        ir("terminal")

    def pedir_mejora(texto, al_terminar=None, codigo=None):
        """Por VOZ: abre la terminal en MEJORAR, escribe el pedido y lo envía al laboratorio. Aplicar sigue
        necesitando tus dos toques: la voz puede pedir, pero no aprobar. codigo: «implementa este código»."""
        elegir("Kira")
        campo_mej.text = str(texto)
        estado["modo_siguiente"] = "mejorar"
        ir("terminal")
        enviar_mejora(al_terminar, codigo)

    # =================================================================================
    #  BIBLIOTECA
    # =================================================================================
    p_bib = Screen(name="biblioteca")
    r_bib = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
    r_bib.add_widget(barra("BIBLIOTECA", "‹ Sala", volver_a_sala))
    fila_est = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
    estantes = (("leccion", "Lecciones"), ("apunte", "Apuntes"), ("modulo", "Módulos"), ("aprendido", "Aprendido"))
    btn_est = {}
    for clave, nombre in estantes:
        btn_est[clave] = boton(nombre, lambda c=clave: elegir_estante(c), GRIS, alto=42)
        fila_est.add_widget(btn_est[clave])
    r_bib.add_widget(fila_est)
    sv_libros = ScrollView(size_hint_y=0.3, do_scroll_x=False)
    lista = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
    lista.bind(minimum_height=lista.setter("height"))
    sv_libros.add_widget(lista)
    r_bib.add_widget(sv_libros)
    sv_lectura, lectura = texto_largo("Elige un estante y un libro.")
    r_bib.add_widget(sv_lectura)
    form = BoxLayout(orientation="vertical", size_hint_y=None, height=0, spacing=dp(4), opacity=0)
    campo_titulo, campo_texto = entrada("Título del apunte"), entrada("Texto o código")
    form.add_widget(campo_titulo)
    form.add_widget(campo_texto)
    form.add_widget(boton("Guardar apunte", lambda: guardar_apunte(), VERDE))
    r_bib.add_widget(form)
    est_bib = etiqueta("", alto=24)
    r_bib.add_widget(est_bib)
    btn_borrar = boton("Borrar este libro", lambda: pedir_borrado(), ROJO)
    r_bib.add_widget(btn_borrar)
    p_bib.add_widget(r_bib)
    sm.add_widget(p_bib)
    sel = {"estante": "leccion", "id": None, "reloj": None}

    def leer_estante(clave):
        """[(id, título, texto)]"""
        if clave in ("leccion", "apunte"):
            return [(i["id"], i["titulo"], i["texto"]) for i in biblioteca.listar(clave)]
        if clave == "modulo":
            return [(m["nombre"], m["nombre"], None) for m in ctl.modulos()]
        return [(i["id"], i["tema"], f"{i['texto']}\n\nFuente: {i.get('fuente', '')}") for i in cerebro.conocimiento.listar()]

    def elegir_estante(clave):
        sel.update(estante=clave, id=None)
        for c, b in btn_est.items():
            b.background_color = VERDE if c == clave else GRIS
        form.height, form.opacity = (dp(150), 1) if clave == "apunte" else (0, 0)
        btn_borrar.disabled = clave in ("modulo",)
        lista.clear_widgets()
        libros = leer_estante(clave)
        for id_, titulo, texto in libros[:80]:
            lista.add_widget(boton(titulo[:60], lambda i=id_, t=titulo, x=texto: abrir(i, t, x), GRIS, alto=40))
        lectura.text = "(estante vacío)" if not libros else "Elige un libro."
        est_bib.text = ""

    def abrir(id_, titulo, texto):
        sel["id"] = id_
        if texto is None:                                      # módulo instalado: se lee su código
            r = ctl.ver_modulo(id_)
            texto = r["texto"]
        lectura.text = f"{titulo}\n\n{texto}"

    def guardar_apunte():
        ok, msg, _ = biblioteca.anadir("apunte", campo_titulo.text, campo_texto.text)
        est_bib.text = msg
        if ok:
            campo_titulo.text = campo_texto.text = ""
            elegir_estante("apunte")
            est_bib.text = msg

    def pedir_borrado():
        if sel["id"] is None or sel["estante"] == "modulo":
            return
        if sel["reloj"] is None:
            btn_borrar.text = "¿Seguro? Toca otra vez"
            sel["reloj"] = Clock.schedule_once(restablecer, 4)
            return
        sel["reloj"].cancel()
        if sel["estante"] in ("leccion", "apunte"):
            biblioteca.borrar(sel["id"])
        else:
            cerebro.conocimiento.descartar(sel["id"])
        restablecer()
        elegir_estante(sel["estante"])
        est_bib.text = "Borrado."

    def restablecer(*_):
        sel["reloj"] = None
        btn_borrar.text = "Borrar este libro"
    ganchos["biblioteca"] = lambda: elegir_estante(sel["estante"])

    return {"detener": detener, "volver_a_sala": volver_a_sala, "biblioteca": biblioteca, "habitacion": habitacion,
            "preparar_mejora": preparar_mejora, "pedir_mejora": pedir_mejora,
            "trabajo_abrir": abrir_trabajo, "consola": con_trab}
