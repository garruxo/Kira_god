# -*- coding: utf-8 -*-
"""
sala_diseno_kira.py - Pantallas de la SALA DE DISEÑO y la SALA DE CINE (Kivy). Se montan en interfaz_kira.py.

  sala_diseno : habitación playera 3D (salas_kira.py). Ordenador al fondo, mediateca a la izquierda,
                puerta de regreso a la izquierda, puerta del cine a la derecha.
  estudio     : el ordenador de diseño: WEB (genera un .html), APP (maqueta de pantallas), VIDEOCLIP (guion + storyboard).
  mediateca   : tus vídeos y tu música (del móvil, creados o en desarrollo).
  sala_cine   : cine 3D con butacas. Tocar la pantalla abre el reproductor.
  reproductor : reproduce audio (SDL), vídeo (solo si el dispositivo tiene proveedor de vídeo de Kivy) y los videoclips
                de storyboard creados en el estudio.

Honesto: no edita vídeo real ni compone música; el vídeo del móvil solo se reproduce si Kivy tiene un proveedor de
vídeo (ffpyplayer) en el APK; si no, lo dice. La lógica está en diseno_kira.py y salas_kira.py (sin Kivy).
"""
import os


def montar_sala_diseno(sm, ctx):
    """Añade las pantallas. Devuelve {'detener', 'volver_diseno', 'volver_cine', 'atras': {pantalla: fn}, ...}."""
    import estilo_kira as _est
    _tam = _est.tam
    from kivy.clock import Clock
    from kivy.metrics import dp, sp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
    from kivy.uix.screenmanager import Screen
    from kivy.uix.scrollview import ScrollView

    import threading

    import diseno_kira as dk
    import video_cliente_kira as vc
    import habitacion_kira as hk
    import inicio_kira as ik
    import salas_kira as sk
    import escena_kira as ek

    boton, entrada, texto_largo, en_hilo = ctx["boton"], ctx["entrada"], ctx["texto_largo"], ctx["en_hilo"]
    TXT, NEON, TENUE, GRIS, VERDE, ROJO = (ctx[k] for k in ("TXT", "NEON", "TENUE", "GRIS", "VERDE", "ROJO"))
    FUENTE, ir, core, voz, ganchos = ctx["FUENTE"], ctx["ir"], ctx["core"], ctx["voz"], ctx["ganchos"]
    mediateca = dk.Mediateca(os.path.join(ctx["dir_datos"], "mediateca.json"))
    proyectos = dk.Proyectos(ctx["dir_datos"])
    HabitacionWidget = hk.crear_widgets()
    EscenaWidget = ek.crear_widgets()[0]

    def etiqueta(texto="", alto=24, color=TENUE, **kw):
        lb = Label(text=texto, size_hint_y=None, height=dp(alto), color=color, font_size=_tam(13), halign="left",
                   valign="middle", **FUENTE, **kw)
        return _est.ajustar(lb, minimo=10, lineas=max(1, int(alto // 17)))

    def barra(titulo, texto_boton, accion):
        b = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        b.add_widget(boton(texto_boton, accion, GRIS, alto=44, size_hint_x=None, width=dp(100)))
        b.add_widget(_est.ajustar(Label(text=titulo, color=NEON, font_size=_tam(16), bold=True, halign="left", **FUENTE), lineas=1))
        return b

    # =================================================================================
    #  HABITACIÓN GENÉRICA (diseño y cine comparten la mecánica)
    # =================================================================================
    def crear_habitacion(nombre, titulo, rec, botones, ayuda, intencion, frases, al_destino, salir):
        """botones: [(texto, destino)]. al_destino(destino): qué hacer al llegar. Devuelve dict con control."""
        est = {"volver": False, "escuchando": None}
        pantalla = Screen(name=nombre)
        raiz = BoxLayout(orientation="vertical")
        raiz.add_widget(barra(titulo, "Salir", salir))
        hab = HabitacionWidget(recorrido=rec, size_hint_y=1)
        raiz.add_widget(hab)
        dice = etiqueta("", alto=40, color=TXT)
        raiz.add_widget(dice)
        fila = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4), padding=(dp(6), 0))
        campo = entrada(ayuda)
        fila_in = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6), padding=(dp(6), dp(2)))

        def decir(texto, hablar=False):
            dice.text = texto
            if hablar and ctx["ajustes"].voz_hablar:
                voz.hablar(texto)

        def ordenar(destino):
            if hab.rec.ordenar(destino):
                decir(frases.get(destino, "Vamos…"))
            else:
                decir("Espera un momento…")

        def enviar():
            texto = ik.limpiar_entrada(campo.text)
            if not texto:
                return
            campo.text = ""
            destino = intencion(texto)
            if destino:
                ordenar(destino)
            else:
                decir("No te he entendido. " + ayuda)

        def escuchar():
            if est["escuchando"] is not None:
                return
            ok, msg = voz.iniciar_escucha()
            decir(msg)
            if not ok:
                return
            t = {"s": 0.0}

            def sondeo(dt):
                t["s"] += dt
                e, txt = voz.sondear()
                if e == "escuchando" and t["s"] < 12:
                    return
                est["escuchando"].cancel()
                est["escuchando"] = None
                if e == "listo" and txt:
                    campo.text = txt
                    enviar()
                else:
                    voz.parar_escucha()
                    decir("No te he oído. Prueba otra vez o escríbeme.")
            est["escuchando"] = Clock.schedule_interval(sondeo, 0.4)

        for txt_b, destino in botones:
            fila.add_widget(boton(txt_b, lambda d=destino: ordenar(d), GRIS, alto=44))
        raiz.add_widget(fila)
        fila_in.add_widget(campo)
        fila_in.add_widget(boton("Mic", escuchar, VERDE, alto=48, size_hint_x=None, width=dp(64)))
        fila_in.add_widget(boton("Ir", enviar, VERDE, alto=48, size_hint_x=None, width=dp(64)))
        raiz.add_widget(fila_in)
        pantalla.add_widget(raiz)
        sm.add_widget(pantalla)

        def al_evento(ev):
            al_destino(ev, decir)

        def al_tocar(hot):
            if hot is None and hab.rec.estado == "libre":
                decir("Toca un objeto o una puerta. Arrastra para mirar alrededor.")
        hab.al_evento, hab.al_tocar = al_evento, al_tocar

        def entrar(texto_vuelta="De vuelta. Arrastra para mirar alrededor."):
            if est["volver"]:
                est["volver"] = False
                hab.rec.volver()
                decir(texto_vuelta)
            else:
                hab.rec.reiniciar()
                decir("Entrando en la sala…")
            hab.iniciar()

        def detener():
            hab.detener()
            if est["escuchando"] is not None:
                est["escuchando"].cancel()
                est["escuchando"] = None
                voz.parar_escucha()
        return {"hab": hab, "entrar": entrar, "detener": detener, "est": est, "decir": decir}

    def a_menu():
        diseno_hab["hab"].rec.reiniciar()
        cine_hab["hab"].rec.reiniciar()
        ir("menu")

    # ---- eventos de la sala de diseño ----
    def destino_diseno(ev, decir):
        if ev == "ordenador":
            decir("Encendiendo el ordenador de diseño…", hablar=True)
            Clock.schedule_once(lambda _dt: ir("estudio"), 0.4)
        elif ev == "biblioteca":
            ir("mediateca")
        elif ev == "cine":
            decir("Abriendo la puerta del cine…")
            diseno_hab["hab"].rec.reiniciar()
            ir("sala_cine")
        elif ev == "regreso":
            a_menu()

    diseno_hab = crear_habitacion(
        "sala_diseno", "SALA DE DISEÑO", sk.recorrido_diseno(),
        [("< Mediateca", "biblioteca"), ("Diseñar", "ordenador"), ("Cine >", "cine")],
        "Di o escribe: diseñar, mediateca, cine, salir…", sk.intencion_diseno,
        {"ordenador": "Me acerco al ordenador de diseño…", "biblioteca": "Vamos a la mediateca…",
         "cine": "Vamos a la puerta del cine…", "regreso": "Vamos a la puerta de regreso…"},
        destino_diseno, a_menu)

    # ---- eventos de la sala de cine ----
    def destino_cine(ev, decir):
        if ev == "pantalla":
            decir("Que empiece la sesión…")
            Clock.schedule_once(lambda _dt: ir("reproductor"), 0.3)
        elif ev == "regreso":
            cine_hab["hab"].rec.reiniciar()
            ir("sala_diseno")
        elif ev == "salida":
            a_menu()

    cine_hab = crear_habitacion(
        "sala_cine", "SALA DE CINE", sk.recorrido_cine(),
        [("< Diseño", "regreso"), ("Pantalla", "pantalla"), ("Salir >", "salida")],
        "Di o escribe: ver, pantalla, diseño, salir…", sk.intencion_cine,
        {"pantalla": "Nos sentamos frente a la pantalla…", "regreso": "Volvemos a la sala de diseño…",
         "salida": "Vamos hacia la salida…"},
        destino_cine, a_menu)

    def volver_diseno():
        diseno_hab["est"]["volver"] = True
        ir("sala_diseno")

    def volver_cine():
        cine_hab["est"]["volver"] = True
        ir("sala_cine")
    ganchos["sala_diseno"] = lambda: diseno_hab["entrar"]("De vuelta en la mesa de diseño.")
    ganchos["sala_cine"] = lambda: cine_hab["entrar"]("De vuelta en tu butaca.")

    # =================================================================================
    #  ESTUDIO (ordenador de diseño)
    # =================================================================================
    p_est = Screen(name="estudio")
    r_est = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
    r_est.add_widget(barra("KIRA//DISEÑO", "< Sala", volver_diseno))
    fila_t = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    modos = (("web", "WEB"), ("app", "APP"), ("clip", "VIDEOCLIP"))
    btn_modo = {}
    for clave, nombre in modos:
        btn_modo[clave] = boton(nombre, lambda c=clave: elegir_modo(c), GRIS)
        fila_t.add_widget(btn_modo[clave])
    r_est.add_widget(fila_t)
    guia = etiqueta("", alto=44, color=TENUE)
    r_est.add_widget(guia)
    campo_d = entrada("Describe lo que quieres crear…")
    r_est.add_widget(campo_d)
    btn_crear = boton("Crear", lambda: crear(), VERDE)
    r_est.add_widget(btn_crear)
    vista_escena = EscenaWidget(size_hint_y=0.4)
    r_est.add_widget(vista_escena)
    sv_res, res = texto_largo("")
    r_est.add_widget(sv_res)
    est_est = etiqueta("", alto=40, color=TXT)
    r_est.add_widget(est_est)
    fila_g = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
    btn_g1 = boton("Guardar", lambda: guardar(False), VERDE, disabled=True)
    btn_g2 = boton("Guardar como terminado", lambda: guardar(True), GRIS, disabled=True)
    btn_ver = boton("Ver en el cine", lambda: ver_en_cine(), GRIS, disabled=True)
    for b in (btn_g1, btn_g2, btn_ver):
        fila_g.add_widget(b)
    r_est.add_widget(fila_g)
    # ---- crear el MP4 real (solo en el modo VIDEOCLIP) ----
    fila_v = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
    opc = {"formato": "16:9", "calidad": "normal", "musica": None, "cancelar": None}
    btn_fmt = boton("16:9", lambda: rotar("formato"), GRIS, alto=42)
    btn_cal = boton("normal", lambda: rotar("calidad"), GRIS, alto=42)
    btn_mus = boton("Sin música", lambda: rotar("musica"), GRIS, alto=42)
    btn_vid = boton("Crear vídeo MP4", lambda: crear_video(), VERDE, alto=42, disabled=True)
    for b in (btn_fmt, btn_cal, btn_mus, btn_vid):
        fila_v.add_widget(b)
    r_est.add_widget(fila_v)
    p_est.add_widget(r_est)
    sm.add_widget(p_est)
    GUIAS = {"web": "WEB: crea una página (.html de una sola página, sin JavaScript). Ej.: «web de una cafetería junto a la playa».",
             "app": "APP: dibuja 1 a 3 pantallas de una aplicación como maqueta. Ej.: «app de notas y tareas».",
             "clip": "VIDEOCLIP: guion de escenas + storyboard animado; «Crear vídeo MP4» lo convierte en un MP4 REAL "
                     "(escenas dibujadas por código, con movimiento, fundidos, títulos y música opcional). "
                     "Ej.: «videoclip de una playa del amanecer a la noche»."}
    sel = {"modo": "web", "contenido": None, "ruta": None}

    def elegir_modo(clave):
        sel.update(modo=clave, contenido=None, ruta=None)
        for c, b in btn_modo.items():
            b.background_color = VERDE if c == clave else GRIS
        guia.text = GUIAS[clave]
        res.text = ""
        est_est.text = ""
        vista_escena.opacity = 0 if clave == "web" else 1
        vista_escena.size_hint_y = 0.0001 if clave == "web" else 0.4
        vista_escena.poner([])
        btn_g1.disabled = btn_g2.disabled = btn_ver.disabled = True
        btn_g2.opacity = 1 if clave == "clip" else 0
        btn_ver.opacity = 1 if clave == "clip" else 0
        fila_v.opacity = 1 if clave == "clip" else 0
        fila_v.height = dp(42) if clave == "clip" else 0
        btn_vid.disabled = True
        btn_g1.text = "Guardar" if clave != "clip" else "Guardar (en desarrollo)"

    def mostrar(tipo, contenido):
        sel["contenido"] = contenido
        if tipo == "web":
            res.text = dk.html_desde_spec(contenido)
        elif tipo == "app":
            res.text = dk.texto_maqueta(contenido)
            vista_escena.poner(dk.maqueta_formas(contenido))
        else:
            res.text = dk.texto_guion(contenido)
            vista_escena.poner(dk.formas_escena(contenido["escenas"][0]))
        btn_g1.disabled = False
        btn_g2.disabled = tipo != "clip"
        btn_vid.disabled = tipo != "clip"

    def crear():
        desc = ik.limpiar_entrada(campo_d.text)
        if not desc or btn_crear.disabled:
            return
        btn_crear.disabled = True
        modo = sel["modo"]
        est_est.text = "Kira está diseñando…"

        def terminado(r):
            btn_crear.disabled = False
            if isinstance(r, Exception):
                est_est.text = f"[x] {r}"
                return
            contenido, origen = r
            mostrar(modo, contenido)
            est_est.text = ("Diseñado con la IA (contenido validado por Kira)." if origen == "ia" else
                            "Diseñado con plantillas locales (sin IA: falta la clave o no hay red).") + " Revísalo y guárdalo."
        en_hilo(lambda: core.generar_diseno(modo, desc), terminado)

    def guardar(terminado_):
        c, modo = sel["contenido"], sel["modo"]
        if c is None:
            est_est.text = "Primero crea algo."
            return
        try:
            if modo == "web":
                ruta = proyectos.guardar_web(c)
            elif modo == "app":
                ruta = proyectos.guardar_app(c)
            else:
                ruta = proyectos.guardar_clip(c)
                ok, msg, _ = mediateca.anadir(c["titulo"], ruta, "clip", "creado" if terminado_ else "desarrollo")
                est_est.text = f"Guardado ({msg})"
                btn_ver.disabled = False
                sel["ruta"] = ruta
                return
            sel["ruta"] = ruta
            ok, msg = proyectos.exportar(ruta)
            est_est.text = f"Guardado dentro de Kira. {msg}"
        except (OSError, ValueError) as e:
            est_est.text = f"[x] No se pudo guardar: {e}"

    def rotar(que):
        if que == "formato":
            lista_ = list(dk_motor_formatos())
            opc["formato"] = lista_[(lista_.index(opc["formato"]) + 1) % len(lista_)]
            btn_fmt.text = opc["formato"]
        elif que == "calidad":
            lista_ = ["borrador", "normal", "alta"]
            opc["calidad"] = lista_[(lista_.index(opc["calidad"]) + 1) % 3]
            btn_cal.text = opc["calidad"]
        else:
            audios = mediateca.listar(tipo="audio")
            idx = next((k for k, a in enumerate(audios) if a["ruta"] == opc["musica"]), -1)
            nuevo = audios[idx + 1] if idx + 1 < len(audios) else None
            opc["musica"] = nuevo["ruta"] if nuevo else None
            btn_mus.text = ("Música: " + nuevo["titulo"][:14]) if nuevo else "Sin música"

    def dk_motor_formatos():
        return ("16:9", "9:16", "4:3")

    def crear_video():
        """Crea el MP4 real: aquí si hay ffmpeg, si no en el laboratorio del PC. Con un segundo toque se cancela."""
        if opc["cancelar"] is not None:
            opc["cancelar"].set()
            est_est.text = "Cancelando…"
            return
        guion = sel["contenido"]
        if guion is None or sel["modo"] != "clip":
            est_est.text = "Primero crea el guion del videoclip."
            return
        opc["cancelar"] = threading.Event()
        cancelar = opc["cancelar"]
        btn_vid.text = "Cancelar"
        destino = proyectos.ruta_video(guion["titulo"])

        def avance(f, texto):
            Clock.schedule_once(lambda _dt: setattr(est_est, "text", f"{texto} {int(f * 100)} %"), 0)

        def hecho(r):
            opc["cancelar"] = None
            btn_vid.text = "Crear vídeo MP4"
            if isinstance(r, Exception):
                est_est.text = f"[x] {r}"
                if callable(getattr(core, "registrar_error", None)):
                    consejo = core.registrar_error("vídeo", str(r))
                    if consejo:
                        est_est.text += "\n" + consejo
                return
            donde, info = r
            ok, msg, _ = mediateca.anadir(guion["titulo"] + " (MP4)", destino, "video", "creado")
            copiado = proyectos.exportar(destino)[1]
            est_est.text = (f"Vídeo creado {'aquí' if donde == 'local' else 'en el laboratorio'}: {os.path.basename(destino)} "
                            f"({os.path.getsize(destino) // 1024} KB). {copiado} Está en la mediateca; para verlo dentro de Kira "
                            "hace falta reproductor de vídeo en el APK, si no ábrelo desde Descargas.")
        en_hilo(lambda: vc.crear_video(guion, destino, opc["formato"], opc["calidad"], opc["musica"], avance, cancelar), hecho)

    def ver_en_cine():
        if not sel.get("ruta"):
            return
        repro["abrir_ruta"](sel["ruta"])
        ir("reproductor")
    ganchos["estudio"] = lambda: elegir_modo(sel["modo"])

    # =================================================================================
    #  MEDIATECA
    # =================================================================================
    p_med = Screen(name="mediateca")
    r_med = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
    r_med.add_widget(barra("MEDIATECA", "< Sala", volver_diseno))
    fila_e = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(4))
    estantes = (("video", "Vídeos"), ("audio", "Música"), ("creado", "Creados"), ("desarrollo", "En desarrollo"))
    btn_est = {}
    for clave, nombre in estantes:
        btn_est[clave] = boton(nombre, lambda c=clave: elegir_estante(c), GRIS, alto=42)
        fila_e.add_widget(btn_est[clave])
    r_med.add_widget(fila_e)
    sv_l = ScrollView(size_hint_y=0.45, do_scroll_x=False)
    lista = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
    lista.bind(minimum_height=lista.setter("height"))
    sv_l.add_widget(lista)
    r_med.add_widget(sv_l)
    est_med = etiqueta("", alto=48, color=TXT)
    r_med.add_widget(est_med)
    fila_a = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
    btn_rep = boton("Reproducir", lambda: reproducir_sel(), VERDE, disabled=True)
    btn_est2 = boton("Cambiar estado", lambda: cambiar_estado(), GRIS, disabled=True)
    btn_quitar = boton("Quitar de la lista", lambda: quitar(), ROJO, disabled=True)
    for b in (btn_rep, btn_est2, btn_quitar):
        fila_a.add_widget(b)
    r_med.add_widget(fila_a)
    btn_scan = boton("Buscar vídeos y música en el móvil", lambda: escanear(), GRIS)
    r_med.add_widget(btn_scan)
    campo_ruta = entrada("O escribe la ruta de un archivo…")
    r_med.add_widget(campo_ruta)
    r_med.add_widget(boton("Añadir esa ruta", lambda: anadir_ruta(), GRIS))
    p_med.add_widget(r_med)
    sm.add_widget(p_med)
    msel = {"estante": "video", "item": None, "reloj": None}
    ICONO = {"video": "[V]", "audio": "[M]", "clip": "[C]"}

    def items_estante(clave):
        if clave in ("video", "audio"):
            return mediateca.listar(tipo=clave)
        return mediateca.listar(estado=clave)

    def elegir_estante(clave):
        msel.update(estante=clave, item=None)
        for c, b in btn_est.items():
            b.background_color = VERDE if c == clave else GRIS
        lista.clear_widgets()
        items = items_estante(clave)
        for it in items[:80]:
            lista.add_widget(boton(f"{ICONO[it['tipo']]} {it['titulo'][:50]}", lambda i=it: elegir_item(i), GRIS, alto=40))
        est_med.text = "(vacío: usa «Buscar en el móvil» o crea algo en el estudio)" if not items else "Elige un elemento."
        btn_rep.disabled = btn_est2.disabled = btn_quitar.disabled = True

    def elegir_item(it):
        msel["item"] = it
        est_med.text = f"{it['titulo']}\nTipo: {it['tipo']}  ·  Estado: {it['estado']}\n{it['ruta'][-60:]}"
        btn_rep.disabled = btn_est2.disabled = btn_quitar.disabled = False

    def reproducir_sel():
        if msel["item"] is None:
            return
        repro["abrir"](msel["item"])
        ir("reproductor")

    def cambiar_estado():
        it = msel["item"]
        if it is None:
            return
        siguiente = {"personal": "desarrollo", "desarrollo": "creado", "creado": "personal"}.get(it["estado"], "personal")
        mediateca.cambiar_estado(it["id"], siguiente)
        elegir_estante(msel["estante"])
        est_med.text = f"Estado cambiado a «{siguiente}»."

    def quitar():
        it = msel["item"]
        if it is None:
            return
        if msel["reloj"] is None:
            btn_quitar.text = "¿Seguro? Toca otra vez"
            msel["reloj"] = Clock.schedule_once(restablecer, 4)
            return
        msel["reloj"].cancel()
        mediateca.borrar(it["id"])
        restablecer()
        elegir_estante(msel["estante"])
        est_med.text = "Quitado de la lista (el archivo no se borra)."

    def restablecer(*_):
        msel["reloj"] = None
        btn_quitar.text = "Quitar de la lista"

    def escanear():
        if btn_scan.disabled:
            return
        btn_scan.disabled = True
        pedido = dk.pedir_permisos_medios()
        est_med.text = ("Buscando en el móvil… (si Android pide permiso, acéptalo y vuelve a pulsar)" if pedido
                        else "Buscando en el móvil…")

        def terminado(r):
            btn_scan.disabled = False
            if isinstance(r, Exception):
                est_med.text = f"[x] {r}"
                return
            nuevos, vistos = r
            elegir_estante(msel["estante"])
            est_med.text = f"Encontrados {vistos} archivos; {nuevos} nuevos añadidos." + \
                ("" if vistos else " Si esperabas más, concede el permiso de archivos a la app.")
        en_hilo(lambda: mediateca.escanear(), terminado)

    def anadir_ruta():
        ruta = ik.limpiar_entrada(campo_ruta.text)
        if not ruta:
            return
        ok, msg, _ = mediateca.anadir("", ruta)
        est_med.text = msg
        if ok:
            campo_ruta.text = ""
            elegir_estante(msel["estante"])
            est_med.text = msg
    ganchos["mediateca"] = lambda: elegir_estante(msel["estante"])

    # =================================================================================
    #  REPRODUCTOR (audio, vídeo si hay proveedor, storyboard)
    # =================================================================================
    p_rep = Screen(name="reproductor")
    r_rep = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
    r_rep.add_widget(barra("REPRODUCTOR", "< Cine", volver_cine))
    zona = BoxLayout(size_hint_y=0.42)
    escena_rep = EscenaWidget()
    zona.add_widget(escena_rep)
    r_rep.add_widget(zona)
    titulo_rep = etiqueta("Elige qué ver o escuchar.", alto=60, color=TXT)
    r_rep.add_widget(titulo_rep)
    fila_c = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
    btn_play = boton("Play", lambda: alternar(), VERDE, disabled=True)
    btn_stop = boton("Parar", lambda: parar(), GRIS, disabled=True)
    fila_c.add_widget(btn_play)
    fila_c.add_widget(btn_stop)
    r_rep.add_widget(fila_c)
    sv_r = ScrollView(size_hint_y=0.4, do_scroll_x=False)
    lista_r = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
    lista_r.bind(minimum_height=lista_r.setter("height"))
    sv_r.add_widget(lista_r)
    r_rep.add_widget(sv_r)
    p_rep.add_widget(r_rep)
    sm.add_widget(p_rep)
    rp = {"item": None, "modo": None, "sonido": None, "pos": 0.0, "video": None, "clip": None, "reloj": None, "formas": {}}

    def parar_todo():
        if rp["reloj"] is not None:
            rp["reloj"].cancel()
            rp["reloj"] = None
        if rp["sonido"] is not None:
            try:
                rp["sonido"].stop()
                rp["sonido"].unload()
            except Exception:
                pass
            rp["sonido"] = None
        if rp["video"] is not None:
            try:
                rp["video"].state = "stop"
                zona.remove_widget(rp["video"])
            except Exception:
                pass
            rp["video"] = None
        rp.update(item=None, modo=None, pos=0.0, clip=None, formas={})
        btn_play.disabled = btn_stop.disabled = True
        btn_play.text = "Play"

    def preparar():
        parar_todo()
        lista_r.clear_widgets()
        escena_rep.poner([])
        todos = mediateca.listar()
        for it in [i for i in todos if i["tipo"] in ("clip", "video")] + [i for i in todos if i["tipo"] == "audio"]:
            lista_r.add_widget(boton(f"{ICONO[it['tipo']]} {it['titulo'][:50]}", lambda i=it: abrir(i), GRIS, alto=40))
        if not todos:
            titulo_rep.text = "La mediateca está vacía. Crea un videoclip en el estudio o añade archivos en la mediateca."
        else:
            titulo_rep.text = "Elige qué ver o escuchar."

    def al_entrar_reproductor():
        if rp.pop("pendiente", False):                     # ya se abrió un elemento concreto: no reiniciar
            return
        preparar()
    ganchos["reproductor"] = al_entrar_reproductor

    def abrir(it):
        parar_todo()
        titulo_rep.text = f"{it['titulo']}"
        if not os.path.isfile(it["ruta"]):
            titulo_rep.text = f"{it['titulo']}\nEl archivo ya no está en esa ruta. Quítalo de la mediateca."
            return
        rp["item"] = it
        if it["tipo"] == "clip":
            try:
                rp["clip"] = dk.ReproductorClip(dk.Proyectos.leer_clip(it["ruta"]))
            except (OSError, ValueError) as e:
                titulo_rep.text = f"[x] No se pudo leer el videoclip: {e}"
                rp["item"] = None
                return
            rp["modo"] = "clip"
            tick_clip(0)                                   # muestra la primera escena
        elif it["tipo"] == "audio":
            try:
                from kivy.core.audio import SoundLoader
                s = SoundLoader.load(it["ruta"])
            except Exception:
                s = None
            if s is None:
                titulo_rep.text = f"{it['titulo']}\n[x] Este dispositivo no pudo cargar el audio (formato no admitido)."
                rp["item"] = None
                return
            rp["sonido"], rp["modo"] = s, "audio"
            escena_rep.poner(dk.formas_escena({"escena": "dibuja el espacio de noche"}))
        else:                                              # vídeo real
            try:
                from kivy.core.video import Video as NucleoVideo
                if NucleoVideo is None:
                    raise RuntimeError("sin proveedor")
                from kivy.uix.video import Video
                v = Video(source=it["ruta"], state="pause", options={"eos": "stop"})
            except Exception:
                titulo_rep.text = (f"{it['titulo']}\nEste APK no incluye un reproductor de vídeo (hace falta ffpyplayer). "
                                   "Los videoclips creados en el estudio y la música sí funcionan.")
                rp["item"] = None
                return
            rp["video"], rp["modo"] = v, "video"
            zona.add_widget(v)
        btn_play.disabled = btn_stop.disabled = False
        btn_play.text = "Play"

    def abrir_desde_fuera(it):
        """Abre un elemento y marca que al entrar en la pantalla no hay que reiniciarla."""
        preparar()
        abrir(it)
        rp["pendiente"] = True

    def abrir_ruta(ruta):
        for it in mediateca.listar():
            if it["ruta"] == ruta:
                abrir_desde_fuera(it)
                return
    repro = {"abrir": abrir_desde_fuera, "abrir_ruta": abrir_ruta}

    def tick_clip(dt):
        c = rp["clip"]
        if c is None:
            return
        i, cambio, fin = c.tick(dt)
        e = c.guion["escenas"][i]
        if cambio:
            if i not in rp["formas"]:
                rp["formas"][i] = dk.formas_escena(e, i)
            escena_rep.poner(rp["formas"][i])
        titulo_rep.text = (f"{c.guion['titulo']}  [{int(c.t)}/{int(dk.duracion_total(c.guion))} s]\n"
                           f"{e['titulo']} - {e['plano']}: {e['texto']}")
        if fin and rp["reloj"] is not None:
            rp["reloj"].cancel()
            rp["reloj"] = None
            btn_play.text = "Play"

    def alternar():
        m = rp["modo"]
        if m == "clip":
            c = rp["clip"]
            if c.reproduciendo:
                c.pausa()
                btn_play.text = "Play"
                if rp["reloj"] is not None:
                    rp["reloj"].cancel()
                    rp["reloj"] = None
            else:
                c.play()
                btn_play.text = "Pausa"
                if rp["reloj"] is None:
                    rp["reloj"] = Clock.schedule_interval(tick_clip, 1 / 15.0)
        elif m == "audio":
            s = rp["sonido"]
            if btn_play.text == "Play":
                s.play()
                if rp["pos"]:
                    try:
                        s.seek(rp["pos"])
                    except Exception:
                        pass
                btn_play.text = "Pausa"
            else:
                try:
                    rp["pos"] = s.get_pos()
                except Exception:
                    rp["pos"] = 0.0
                s.stop()
                btn_play.text = "Play"
        elif m == "video":
            v = rp["video"]
            if btn_play.text == "Play":
                v.state = "play"
                btn_play.text = "Pausa"
            else:
                v.state = "pause"
                btn_play.text = "Play"

    def parar():
        m = rp["modo"]
        if m == "clip":
            rp["clip"].parar()
            if rp["reloj"] is not None:
                rp["reloj"].cancel()
                rp["reloj"] = None
            tick_clip(0)
        elif m == "audio":
            rp["sonido"].stop()
            rp["pos"] = 0.0
        elif m == "video":
            rp["video"].state = "stop"
        btn_play.text = "Play"

    def detener_todo():
        """Se llama al salir de las salas: para sonido, vídeo y relojes."""
        diseno_hab["detener"]()
        cine_hab["detener"]()

    def detener_si_sale(nombre):
        """ir() lo llama con la pantalla a la que se va: apaga lo que no corresponda."""
        if nombre != "sala_diseno":
            diseno_hab["detener"]()
        if nombre != "sala_cine":
            cine_hab["detener"]()
        if nombre != "reproductor":
            parar_todo()

    return {"detener": detener_todo, "detener_si_sale": detener_si_sale, "volver_diseno": volver_diseno,
            "volver_cine": volver_cine, "mediateca": mediateca, "proyectos": proyectos,
            "atras": {"estudio": volver_diseno, "mediateca": volver_diseno, "reproductor": volver_cine,
                      "sala_cine": lambda: (cine_hab["hab"].rec.reiniciar(), ir("sala_diseno"))},
            "diseno": diseno_hab["hab"], "cine": cine_hab["hab"], "reproductor": repro}
