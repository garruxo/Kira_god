# -*- coding: utf-8 -*-
"""
sala_ciber_kira.py - Pantallas de la SALA DE CIBERSEGURIDAD (Kivy). Búnker de SOLO lectura y aprendizaje.

  sala_ciber : la habitación 3D (salas_kira.construir_ciber). Caminas hasta la consola y miras alrededor.
  centro     : la "pantalla matrix" con la silueta de Kira (se anima cuando habla). Tres pestañas:
                 ESTUDIAR   - biblioteca de conceptos de amenazas explicados de forma DEFENSIVA, con tu progreso.
                 REVISIÓN   - comprueba hábitos de seguridad del propio Kira y del aparato (solo lee).
                 DISPOSITIVO- estado real del aparato (RAM, CPU, disco, red, batería).

Blindaje: aquí Kira SOLO lee e informa. No ejecuta, no descarga, no analiza ni guarda código malicioso, no hace
ataques ni escanea redes. Lo único que se guarda es tu progreso de estudio (qué conceptos has visto). La lógica
está en ciber_kira.py (sin Kivy).
"""
import os


def montar_sala_ciber(sm, ctx):
    import estilo_kira as _est
    _tam = _est.tam
    from kivy.clock import Clock
    from kivy.graphics import Color, Rectangle
    from kivy.metrics import dp, sp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.screenmanager import Screen
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.widget import Widget

    import ciber_kira as ck
    import habitacion_kira as hk
    import inicio_kira as ik
    import salas_kira as sk

    boton, entrada, texto_largo, en_hilo = ctx["boton"], ctx["entrada"], ctx["texto_largo"], ctx["en_hilo"]
    TXT, NEON, TENUE, GRIS, VERDE, ROJO = (ctx[k] for k in ("TXT", "NEON", "TENUE", "GRIS", "VERDE", "ROJO"))
    FUENTE, ir, core, voz, ganchos, dir_datos = ctx["FUENTE"], ctx["ir"], ctx["core"], ctx["voz"], ctx["ganchos"], ctx["dir_datos"]
    aprend = ck.Aprendizaje(os.path.join(dir_datos, "ciber_aprendizaje.json"))
    HabitacionWidget = hk.crear_widgets()
    estado = {"escuchando": None, "volver": False, "tab": "estudiar"}

    def etiqueta(texto="", alto=24, color=TENUE, **kw):
        lb = Label(text=texto, size_hint_y=None, height=dp(alto), color=color, font_size=_tam(13), halign="left", valign="middle", **FUENTE, **kw)
        return _est.ajustar(lb, minimo=10, lineas=max(1, int(alto // 17)))

    def barra(titulo, texto_boton, accion):
        b = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        b.add_widget(boton(texto_boton, accion, GRIS, alto=44, size_hint_x=None, width=dp(100)))
        b.add_widget(_est.ajustar(Label(text=titulo, color=NEON, font_size=_tam(16), bold=True, halign="left", **FUENTE), lineas=1))
        return b

    # ---- silueta de Kira que "habla" (pulsos verdes) ----
    class SiluetaKira(Widget):
        def __init__(self, **kw):
            super().__init__(**kw)
            self._f, self._reloj = 0.0, None
            self.bind(size=self._pintar, pos=self._pintar)

        def hablar(self, segundos=1.6):
            self._f = segundos
            if self._reloj is None:
                self._reloj = Clock.schedule_interval(self._tick, 1 / 15.0)

        def _tick(self, dt):
            self._f -= dt
            self._pintar()
            if self._f <= 0 and self._reloj is not None:
                self._reloj.cancel()
                self._reloj = None
                self._pintar()

        def _pintar(self, *_):
            import math
            w, h = self.width, self.height
            self.canvas.clear()
            with self.canvas:
                Color(0.01, 0.05, 0.03, 1)
                Rectangle(pos=self.pos, size=self.size)
                cx = self.x + w / 2
                activo = self._f > 0
                Color(0.15, 0.95, 0.45, 1)
                cuerpo_w = w * 0.12
                Rectangle(pos=(cx - cuerpo_w, self.y + h * 0.15), size=(cuerpo_w * 2, h * 0.45))   # torso
                Rectangle(pos=(cx - w * 0.06, self.y + h * 0.6), size=(w * 0.12, h * 0.22))          # cabeza
                for k in range(7):                                                                    # barras de voz
                    bx = cx - w * 0.3 + k * w * 0.1
                    amp = (0.5 + 0.5 * math.sin((self._f + k) * 9)) if activo else 0.1
                    bh = h * 0.05 + h * 0.22 * amp
                    Rectangle(pos=(bx, self.y + h * 0.02), size=(w * 0.05, bh))

    # =================================================================================
    #  SALA (habitación 3D)
    # =================================================================================
    p_sala = Screen(name="sala_ciber")
    raiz = BoxLayout(orientation="vertical")
    raiz.add_widget(barra("CIBERSEGURIDAD", "Salir", lambda: salir_al_menu()))
    hab = HabitacionWidget(recorrido=sk.recorrido_ciber(), size_hint_y=1)
    raiz.add_widget(hab)
    dice = etiqueta("", alto=40, color=TXT)
    raiz.add_widget(dice)
    fila = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4), padding=(dp(6), 0))
    for txt_b, destino in (("< Dispositivo", "dispositivo"), ("Kira (centro)", "centro"), ("Salir >", "regreso")):
        fila.add_widget(boton(txt_b, lambda d=destino: ordenar(d), GRIS, alto=44))
    raiz.add_widget(fila)
    campo = entrada("Di o escribe: estudiar, revisar, dispositivo, salir…")
    fila_in = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6), padding=(dp(6), dp(2)))
    fila_in.add_widget(campo)
    fila_in.add_widget(boton("Mic", lambda: escuchar(), VERDE, alto=48, size_hint_x=None, width=dp(64)))
    fila_in.add_widget(boton("Ir", lambda: enviar(), VERDE, alto=48, size_hint_x=None, width=dp(64)))
    raiz.add_widget(fila_in)
    p_sala.add_widget(raiz)
    sm.add_widget(p_sala)

    def decir(texto, hablar=False):
        dice.text = texto
        silueta.hablar()
        if hablar and ctx["ajustes"].voz_hablar:
            voz.hablar(texto)

    def ordenar(destino):
        if hab.rec.ordenar(destino):
            decir({"centro": "Voy a la consola central…", "dispositivo": "Veamos el dispositivo…", "regreso": "Vamos a la salida…"}[destino])
        else:
            decir("Espera un momento…")

    def enviar():
        texto = ik.limpiar_entrada(campo.text)
        if not texto:
            return
        campo.text = ""
        d = sk.intencion_ciber(texto)
        if d:
            ordenar(d)
        else:
            decir("Prueba con «estudiar», «revisar», «dispositivo» o «salir».")

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
            e, txt = voz.sondear()
            if e == "escuchando" and t["s"] < 12:
                return
            estado["escuchando"].cancel()
            estado["escuchando"] = None
            if e == "listo" and txt:
                campo.text = txt
                enviar()
            else:
                voz.parar_escucha()
                decir("No te he oído. Prueba otra vez o escríbeme.")
        estado["escuchando"] = Clock.schedule_interval(sondeo, 0.4)

    def al_evento(ev):
        if ev == "centro":
            decir("Consola lista.", hablar=True)
            Clock.schedule_once(lambda _dt: abrir_centro("estudiar"), 0.3)
        elif ev == "dispositivo":
            Clock.schedule_once(lambda _dt: abrir_centro("dispositivo"), 0.2)
        elif ev == "regreso":
            salir_al_menu()

    def al_tocar(hot):
        if hot is None and hab.rec.estado == "libre":
            decir("Toca la pantalla de Kira, el panel del dispositivo o la puerta. Arrastra para mirar.")
    hab.al_evento, hab.al_tocar = al_evento, al_tocar

    def salir_al_menu():
        hab.rec.reiniciar()
        ir("menu")

    def abrir_centro(tab):
        estado["tab"] = tab
        ir("centro")

    def entrar_sala():
        if estado["volver"]:
            estado["volver"] = False
            hab.rec.volver()
            decir("De vuelta en la consola.")
        else:
            hab.rec.reiniciar()
            decir("Entrando en el búnker. Aquí solo leo y enseño: nada de aquí puede dañar nada.")
        hab.iniciar()

    def detener():
        hab.detener()
        if estado["escuchando"] is not None:
            estado["escuchando"].cancel()
            estado["escuchando"] = None
            voz.parar_escucha()
    ganchos["sala_ciber"] = entrar_sala

    def volver_a_sala():
        estado["volver"] = True
        ir("sala_ciber")

    # =================================================================================
    #  CENTRO (consola: estudiar / revisión / dispositivo)
    # =================================================================================
    p_centro = Screen(name="centro")
    r_centro = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
    r_centro.add_widget(barra("KIRA // CIBER [solo lectura]", "< Sala", volver_a_sala))
    silueta = SiluetaKira(size_hint_y=None, height=dp(90))
    r_centro.add_widget(silueta)
    pest = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    btn_est = boton("ESTUDIAR", lambda: modo("estudiar"), VERDE)
    btn_rev = boton("REVISIÓN", lambda: modo("revision"), GRIS)
    btn_dis = boton("DISPOSITIVO", lambda: modo("dispositivo"), GRIS)
    btn_cas = boton("SI TE PASA", lambda: modo("casos"), GRIS)
    for b in (btn_est, btn_cas, btn_rev, btn_dis):
        pest.add_widget(b)
    r_centro.add_widget(pest)
    cuerpo = BoxLayout(orientation="vertical", spacing=dp(6))
    r_centro.add_widget(cuerpo)
    p_centro.add_widget(r_centro)
    sm.add_widget(p_centro)

    # ---- ESTUDIAR ----
    c_est = BoxLayout(orientation="vertical", spacing=dp(6))
    prog = etiqueta("", alto=24, color=NEON)
    c_est.add_widget(prog)
    sv_lista = ScrollView(size_hint_y=0.32, do_scroll_x=False)
    rej = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
    rej.bind(minimum_height=rej.setter("height"))
    sv_lista.add_widget(rej)
    c_est.add_widget(sv_lista)
    sv_txt, vista = texto_largo("Elige una amenaza para aprender a defenderte. Kira solo explica la defensa.")
    c_est.add_widget(sv_txt)
    fila_m = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
    btn_estud = boton("Marcar estudiado", lambda: marcar("estudiado"), GRIS, disabled=True)
    btn_aplico = boton("Ya lo aplico", lambda: marcar("aplicado"), VERDE, disabled=True)
    fila_m.add_widget(btn_estud)
    fila_m.add_widget(btn_aplico)
    c_est.add_widget(fila_m)
    fila_p = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
    campo_p = entrada("Pregúntale a Kira cómo protegerte de…")
    btn_p = boton("Preguntar", lambda: preguntar(), VERDE, alto=48, size_hint_x=None, width=dp(110))
    fila_p.add_widget(campo_p)
    fila_p.add_widget(btn_p)
    c_est.add_widget(fila_p)
    sel = {"id": None}

    def preguntar():
        q = ik.limpiar_entrada(campo_p.text)
        if not q or btn_p.disabled:
            return
        btn_p.disabled = True
        vista.text = "Kira está pensando cómo explicártelo (solo defensa)…"
        silueta.hablar(3.0)

        def hecho(r):
            btn_p.disabled = False
            if isinstance(r, Exception):
                vista.text = f"[x] {r}"
                return
            texto, origen = r
            vista.text = texto + ("" if origen == "ia" else "\n\n(Respuesta de la biblioteca local.)")
            silueta.hablar(2.5)
            if ctx["ajustes"].voz_hablar and origen == "ia":
                voz.hablar(texto.split("\n\n")[0][:400])
        en_hilo(lambda: core.explicar_defensa(q), hecho)
    MARCA = {"por_estudiar": "[ ]", "estudiado": "[OK]", "aplicado": "[*]"}

    def pintar_lista():
        rej.clear_widgets()
        for c in ck.CONCEPTOS:
            e = aprend.estado(c["id"])
            rej.add_widget(boton(f"{MARCA[e]} {c['nombre'][:42]}", lambda i=c['id']: abrir_concepto(i),
                                 VERDE if e == "aplicado" else GRIS, alto=42))
        prog.text = aprend.resumen()

    def abrir_concepto(id_):
        sel["id"] = id_
        vista.text = ck.texto_concepto(ck.POR_ID[id_])
        silueta.hablar()
        btn_estud.disabled = btn_aplico.disabled = False

    def marcar(estado_):
        if sel["id"]:
            aprend.marcar(sel["id"], estado_)
            pintar_lista()

    # ---- SI TE PASA (qué hacer ante un incidente) ----
    c_cas = BoxLayout(orientation="vertical", spacing=dp(6))
    c_cas.add_widget(etiqueta("¿Ya te ha pasado algo? Elige qué y Kira te dice qué hacer, paso a paso.", alto=40))
    sv_cas = ScrollView(size_hint_y=0.35, do_scroll_x=False)
    lst_cas = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
    lst_cas.bind(minimum_height=lst_cas.setter("height"))
    sv_cas.add_widget(lst_cas)
    c_cas.add_widget(sv_cas)
    sv_cas_t, vista_cas = texto_largo("Elige una situación.")
    c_cas.add_widget(sv_cas_t)
    for caso in ck.CASOS:
        lst_cas.add_widget(boton(caso["titulo"][:46], lambda c_=caso: (setattr(vista_cas, "text", ck.texto_caso(c_)), silueta.hablar()), GRIS, alto=42))
    lst_cas.add_widget(boton("Aprender más (INCIBE, 017)", lambda: (setattr(vista_cas, "text", ck.texto_recursos()), silueta.hablar()), VERDE, alto=42))

    # ---- REVISIÓN ----
    c_rev = BoxLayout(orientation="vertical", spacing=dp(6))
    c_rev.add_widget(etiqueta("Comprueba hábitos de seguridad del propio Kira y del aparato. Solo lee; no cambia nada.", alto=48))
    sv_rev, vista_rev = texto_largo("Pulsa «Revisar ahora».")
    c_rev.add_widget(sv_rev)
    btn_rev2 = boton("Revisar ahora", lambda: revisar(), VERDE)
    c_rev.add_widget(btn_rev2)

    def revisar():
        btn_rev2.disabled = True
        vista_rev.text = "Revisando…"
        silueta.hablar()

        def hecho(r):
            btn_rev2.disabled = False
            vista_rev.text = r if isinstance(r, str) else f"[x] {r}"
        en_hilo(lambda: ck.texto_revision(ck.revision(dir_datos, getattr(core, "errores_modulos", None))), hecho)

    # ---- DISPOSITIVO ----
    c_dis = BoxLayout(orientation="vertical", spacing=dp(6))
    c_dis.add_widget(etiqueta("El aparato que Kira gobierna. Datos reales, solo lectura.", alto=40))
    sv_dis, vista_dis = texto_largo("Pulsa «Actualizar».")
    c_dis.add_widget(sv_dis)
    btn_dis2 = boton("Actualizar", lambda: refrescar_dispositivo(), VERDE)
    c_dis.add_widget(btn_dis2)

    def refrescar_dispositivo():
        btn_dis2.disabled = True
        vista_dis.text = "Leyendo el dispositivo…"
        silueta.hablar()

        def hecho(r):
            btn_dis2.disabled = False
            vista_dis.text = "\n".join(f"{k}: {v}" for k, v in r) if isinstance(r, list) else f"[x] {r}"
        en_hilo(lambda: ck.info_dispositivo(), hecho)

    def modo(nombre):
        estado["tab"] = nombre
        cuerpo.clear_widgets()
        cuerpo.add_widget({"estudiar": c_est, "casos": c_cas, "revision": c_rev, "dispositivo": c_dis}[nombre])
        btn_est.background_color = VERDE if nombre == "estudiar" else GRIS
        btn_cas.background_color = VERDE if nombre == "casos" else GRIS
        btn_rev.background_color = VERDE if nombre == "revision" else GRIS
        btn_dis.background_color = VERDE if nombre == "dispositivo" else GRIS
        silueta.hablar()
        if nombre == "estudiar":
            pintar_lista()
        elif nombre == "dispositivo":
            refrescar_dispositivo()

    ganchos["centro"] = lambda: modo(estado.get("tab", "estudiar"))

    return {"detener": detener, "volver_a_sala": volver_a_sala, "habitacion": hab, "aprendizaje": aprend,
            "atras": {"centro": volver_a_sala}}
