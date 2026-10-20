# -*- coding: utf-8 -*-
"""
interfaz_kira.py - Interfaz inmersiva de Kira (Kivy, móvil y PC)

  INICIO : fondo blanco con «Kira» por todo el fondo y un botón redondo de neón en el centro (tocarlo = menú).
           Escucha permanente: Kira solo contesta cuando oye su nombre; el resto se borra a los 15 segundos.
  MENÚ   : claro y sencillo: los apartados principales y, al tocar «Más apartados», todos los demás.
  Las salas inmersivas (Hacker, Ciberseguridad, Diseño…) conservan su estilo oscuro.
  Las pantallas de Sala/Mejoras/Módulos/Consola/Ajustes son las del panel de siempre (panel_kira.py).

La lógica (conversación, búsqueda, notas, estado, voz) está en inicio_kira.py y menu_kira.py, sin Kivy.
Aquí solo hay pantallas finas. Botón "atrás" de Android / tecla Esc: vuelve al menú y luego al orbe.
"""
import datetime
import os
import re
import threading


def construir_interfaz(core, consola=None):
    from kivy import kivy_data_dir
    from kivy.animation import Animation
    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.metrics import dp, sp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.graphics import Color, Rectangle
    from kivy.uix.button import Button
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
    from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
    from kivy.uix.widget import Widget
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.textinput import TextInput
    from kivy.utils import platform

    import cerebro_local as cl
    import escena_kira as ek
    import escucha_kira as esk
    import portada_kira
    import inicio_kira as ik
    import menu_kira as mk
    import navegar_kira as nk
    import panel_kira
    from sala_hacker_kira import montar_sala_hacker
    from sala_diseno_kira import montar_sala_diseno
    from taller_kira import montar_taller
    from sala_ciber_kira import montar_sala_ciber
    from pantalla_bitacora_kira import montar_bitacora
    from pantallas_codigo_kira import montar_codigo
    from pantalla_cerebro_kira import montar_cerebro
    from pantalla_lector_kira import montar_lector, pedir_permiso_fotos
    from sala_av_kira import montar_av

    panel_raiz = panel_kira.construir_panel(core, consola=consola)   # si esto falla, main.py usa el plan B
    ctl = panel_raiz.control
    dir_datos = ctl.pc.carpeta_datos()

    ajustes = mk.AjustesInterfaz(os.path.join(dir_datos, "interfaz_ajustes.json"))
    notas = mk.Notas(os.path.join(dir_datos, "notas.json"))
    cerebro = cl.CerebroLocal(os.path.join(dir_datos, "conocimiento.json"), escena=lambda t: ek.interpretar(t),
                              recuerdos=getattr(core, "recuerdos", None))
    def guardar_turno(tu, kira):
        rec = getattr(core, "recuerdos", None)
        if rec is not None:
            rec.guardar_charla(tu, kira)          # solo lo NUEVO: lo que ya sabía no se duplica
    conv = ik.Conversacion(os.path.join(dir_datos, "conversacion.json"),
                           core.procesar_orden, core.conversar,
                           no_reconocida=getattr(core, "NO_RECONOCIDA", "[i] No reconozco la orden"),
                           cerebro=cerebro, al_turno=guardar_turno)
    voz = ik.Voz()
    import oido_kira
    oido = getattr(core, "oido", None) or oido_kira.Oido(dir_datos)
    core.oido = oido                                 # main.py lo apaga al cerrar

    try:
        Window.clearcolor = (0.015, 0.03, 0.03, 1)
        Window.softinput_mode = "below_target"
    except Exception:
        pass

    # Dos paletas: CLARA (portada, menú y pantallas sencillas) y OSCURA (salas inmersivas y panel).
    CLARA = {"TXT": (0.13, 0.16, 0.21, 1), "NEON": (0.0, 0.58, 0.82, 1), "TENUE": (0.44, 0.49, 0.56, 1),
             "GRIS": (0.90, 0.92, 0.95, 1), "VERDE": (0.0, 0.62, 0.62, 1), "ROJO": (0.88, 0.34, 0.40, 1),
             "CAMPO": (1, 1, 1, 1), "FONDO": (0.975, 0.98, 0.99, 1)}
    OSCURA = {"TXT": (0.72, 1.0, 0.82, 1), "NEON": (0.1, 0.9, 0.5, 1), "TENUE": (0.5, 0.7, 0.6, 1),
              "GRIS": (0.12, 0.2, 0.17, 1), "VERDE": (0.08, 0.45, 0.28, 1), "ROJO": (0.55, 0.15, 0.18, 1),
              "CAMPO": (0.05, 0.1, 0.09, 1), "FONDO": (0.015, 0.03, 0.03, 1)}
    import estilo_kira as est
    FUENTE = {}                                   # Roboto normal: se lee mejor y cabe más (antes, máquina de escribir)
    FUENTE_MONO = est.fuente_mono()               # la de máquina de escribir, solo para código
    tam = est.tam

    def _luminosidad(c):
        return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]

    # ---------- piezas (según la paleta) ----------
    def hacer_piezas(P):
        def boton(texto, accion, color=P["GRIS"], alto=48, **kw):
            kw.setdefault("color", P["TXT"] if _luminosidad(color) > 0.6 else (1, 1, 1, 1))
            kw.setdefault("font_size", tam(15))
            b = Button(text=texto, size_hint_y=None, height=dp(alto), background_normal="", background_color=color,
                       **FUENTE, **kw)
            b.bind(on_release=lambda *_: accion())
            return est.ajustar(b)                  # el texto se parte o encoge: nunca se sale del botón

        def entrada(hint, **kw):
            return TextInput(hint_text=hint, multiline=False, size_hint_y=None, height=dp(48), font_size=tam(15),
                             background_color=P["CAMPO"], foreground_color=P["TXT"],
                             hint_text_color=P["TENUE"], cursor_color=P["NEON"], padding=(dp(10), dp(12)), **kw)

        def texto_largo(inicial=""):
            sv = ScrollView(do_scroll_x=False)
            lb = Label(text=inicial, size_hint_y=None, halign="left", valign="top", color=P["TXT"],
                       font_size=tam(15), line_height=1.15, **FUENTE)
            lb.bind(width=lambda w, a: setattr(lb, "text_size", (a - dp(8), None)),
                    texture_size=lambda w, ts: setattr(lb, "height", ts[1] + dp(12)))
            sv.add_widget(lb)
            return sv, lb
        return boton, entrada, texto_largo

    boton, entrada, texto_largo = hacer_piezas(CLARA)
    boton_o, entrada_o, texto_largo_o = hacer_piezas(OSCURA)
    TXT, NEON, TENUE, GRIS, VERDE, ROJO = (CLARA[k] for k in ("TXT", "NEON", "TENUE", "GRIS", "VERDE", "ROJO"))
    PIEZAS_SALA = {"boton": boton_o, "entrada": entrada_o, "texto_largo": texto_largo_o,
                   "TXT": OSCURA["TXT"], "NEON": OSCURA["NEON"], "TENUE": OSCURA["TENUE"], "GRIS": OSCURA["GRIS"],
                   "VERDE": OSCURA["VERDE"], "ROJO": OSCURA["ROJO"], "FUENTE": FUENTE, "FUENTE_MONO": FUENTE_MONO}

    def fondo_claro(widget):
        """Pinta un fondo claro detrás de una pantalla (las salas siguen con el suyo)."""
        with widget.canvas.before:
            Color(*CLARA["FONDO"])
            rect = Rectangle(pos=widget.pos, size=widget.size)
        widget.bind(pos=lambda w, v: setattr(rect, "pos", v), size=lambda w, v: setattr(rect, "size", v))

    def en_hilo(trabajo, al_terminar):
        def correr():
            try:
                r = trabajo()
            except Exception as e:
                r = e
            Clock.schedule_once(lambda _dt: al_terminar(r), 0)
        threading.Thread(target=correr, daemon=True).start()

    sm = ScreenManager(transition=NoTransition())   # cambio de pantalla al instante (el fundido iba a tirones)
    ganchos = {}                     # nombre de pantalla -> función a llamar al entrar

    def pantalla(nombre, titulo):
        """Pantalla con barra superior ‹ Menú. Devuelve (Screen, caja_de_contenido)."""
        p = Screen(name=nombre)
        fondo_claro(p)
        raiz = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        barra = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        barra.add_widget(boton("‹ Menú", lambda: ir("menu"), GRIS, alto=44, size_hint_x=None, width=dp(96)))
        barra.add_widget(est.ajustar(Label(text=titulo, color=NEON, font_size=tam(18), bold=True, halign="left",
                                           **FUENTE), lineas=1))
        raiz.add_widget(barra)
        p.add_widget(raiz)
        sm.add_widget(p)
        return p, raiz

    # =================================================================================
    #  INICIO: portada blanca con «Kira» de fondo y el botón de neón
    # =================================================================================
    PortadaKira = portada_kira.crear_widgets()
    modelo = esk.NeonModelo()
    escucha = esk.Escucha()
    st = {"ocupado": False, "entrando": False, "reloj_txt": None, "maq": None, "reloj_mic": None, "saludado": False,
          "esc_reloj": None, "esc_stt": False, "esc_t": 0.0, "esc_fallos": 0, "oido": False}

    p_ini = Screen(name="inicio")
    orbe = PortadaKira(modelo=modelo, al_tocar=lambda: entrar())
    p_ini.add_widget(orbe)                       # el fondo y el botón ocupan toda la pantalla
    capa = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(6))
    capa.add_widget(Widget(size_hint_y=0.56))    # hueco: ahí se ve el botón de neón

    sv_burbuja, burbuja = texto_largo("")
    sv_burbuja.size_hint_y = 0.30
    burbuja.font_size = tam(16)
    est.fondo_redondeado(sv_burbuja, (1, 1, 1, 0.97), radio=16)   # tarjeta blanca: se lee bien sobre el fondo
    capa.add_widget(sv_burbuja)
    lbl_escucha = est.ajustar(Label(text="", size_hint_y=None, height=dp(24), color=TENUE, font_size=tam(12.5), **FUENTE),
                              minimo=10, lineas=1)
    capa.add_widget(lbl_escucha)

    campo = entrada("Escríbele a Kira…")
    fila = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
    fila.add_widget(campo)
    btn_escucha = boton("", lambda: alternar_escucha(), GRIS, alto=48, size_hint_x=None, width=dp(88), font_size=tam(13))
    fila.add_widget(btn_escucha)
    fila.add_widget(boton("Enviar", lambda: enviar(), VERDE, alto=48, size_hint_x=None, width=dp(78)))
    capa.add_widget(fila)
    p_ini.add_widget(capa)
    sm.add_widget(p_ini)

    def estado_base():
        return "escuchando" if st["esc_reloj"] is not None else "reposo"

    def decir(texto, hablar=True, ya_escrito=False):
        """Kira 'habla': el texto se escribe poco a poco y, si hay voz y está activada, se lee en voz alta.
        ya_escrito=True: el texto ya fue apareciendo mientras pensaba (no se vuelve a escribir)."""
        if st["reloj_txt"] is not None:
            st["reloj_txt"].cancel()
            st["reloj_txt"] = None
        if ya_escrito:
            burbuja.text = texto
            modelo.poner_estado("hablando")
            Clock.schedule_once(lambda _dt: modelo.estado == "hablando" and not st["ocupado"]
                                and modelo.poner_estado(estado_base()), min(8.0, 1.0 + len(texto) / 16.0))
            if hablar and ajustes.voz_hablar:
                voz.hablar(texto.replace("[OK]", "").replace("[x]", "").replace("[i]", ""))
            return
        st["maq"] = ik.Maquina(texto, cps=ajustes.velocidad)
        modelo.poner_estado("hablando")

        def escribir(dt):
            burbuja.text = st["maq"].paso(dt)
            if st["maq"].terminada:
                st["reloj_txt"].cancel()
                st["reloj_txt"] = None
                if not st["ocupado"] and modelo.estado == "hablando":
                    modelo.poner_estado(estado_base())
        st["reloj_txt"] = Clock.schedule_interval(escribir, 1 / 30.0)
        if hablar and ajustes.voz_hablar:
            voz.hablar(texto.replace("[OK]", "").replace("[x]", "").replace("[i]", ""))

    def enviar(texto=None):
        texto = campo.text if texto is None else texto
        texto = ik.limpiar_entrada(texto)
        if not texto or st["ocupado"]:
            return
        campo.text = ""
        import diseno_kira as dk_
        import programar_kira as pk_
        orden = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", texto, flags=re.I) or texto  # escrito «Kira, …»
        prog = pk_.pedido_programa(orden)
        if prog is not None:                            # «escríbeme un programa que…», «hazme un juego de…»: al editor
            programa_por_voz(prog)
            return
        dis = dk_.pedido_diseno(orden)
        if dis is not None:                             # «diséñame una web para…»: al ordenador de diseño
            diseno_por_voz(*dis)
            return
        pedido = ik.pedido_mejora(orden)
        if pedido is not None:                          # «Kira, mejora…» / «aprende a…»: al flujo de mejoras
            mejora_por_voz(pedido)
            return
        bajo = texto.lower()
        if re.match(r"^abre lo le[ií]do", bajo):        # lo que leyó de una captura, al editor
            lector = getattr(core, "lector", None)
            if lector is not None and lector.ultimo:
                decir("Te lo abro en el editor.")
                codigo_ui["cargar_en_editor"](lector.ultimo, "", "Texto leído de una captura: revísalo y pulsa «Ejecutar».")
            else:
                decir("Todavía no he leído ninguna captura.")
            return
        if re.match(r"^abre la receta ", bajo):          # una técnica probada, al editor para verla o cambiarla
            import saber_mejoras_kira as smk
            r = smk.receta(bajo.split("receta", 1)[1])
            if r is None:
                decir("No tengo esa receta. Di «recetas» para ver la lista.")
            else:
                decir(f"Te abro «{r['titulo']}» en el editor.")
                codigo_ui["cargar_en_editor"](smk.programa(r), r["id"],
                                              "Receta probada: pulsa «Ejecutar» o «Jugar» para verla funcionar.")
            return
        if re.match(r"^(?:lee|léeme|leer)(?: la)? (?:última |ultima )?captura", bajo) and not pedir_permiso_fotos():
            decir("Necesito permiso para ver tus capturas. Concédelo y pídemelo otra vez.")
            return
        if moverse(texto):                              # «abre la sala hacker», «abre WhatsApp», «atrás»…
            return
        st["ocupado"] = True
        if st["reloj_txt"] is not None:
            st["reloj_txt"].cancel()
            st["reloj_txt"] = None
        burbuja.text = "…"
        modelo.poner_estado("pensando")
        escucha.olvidar()

        flujo = {"hubo": False}
        en_vivo = ik.HablaEnVivo(voz, activa=ajustes.voz_hablar)   # dice cada frase en cuanto está completa

        def mostrar_trozo(parcial):                      # la respuesta va apareciendo mientras Kira piensa
            if not st["ocupado"]:
                return
            flujo["hubo"] = True
            burbuja.text = parcial + " …"
            if modelo.estado != "hablando":
                modelo.poner_estado("hablando")
            en_vivo.trozo(parcial)

        def trozo(parcial):                              # llega desde otro hilo: se pinta en el de la pantalla
            Clock.schedule_once(lambda _dt, p_=parcial: mostrar_trozo(p_), 0)

        def terminado(r):
            st["ocupado"] = False
            if isinstance(r, Exception):
                decir(f"[x] Algo falló: {r}", hablar=False)
            else:
                texto_r, via = r
                ya_dicho = via == "charla" and en_vivo.final(texto_r)   # lo fue diciendo mientras llegaba
                decir(texto_r, hablar=(via != "error" and not ya_dicho), ya_escrito=flujo["hubo"] and via == "charla")
                if via == "escena" and cerebro.ultima_escena:
                    mostrar_escena(cerebro.ultima_escena, texto_r)
                enl = getattr(core, "enlace", None)
                if enl is not None and enl.esperando_codigo():   # te ha pedido el código: contéstale sin «Kira»
                    escucha.atender(25 + len(texto_r) / 14.0)
                    if sm.current == "pasarela":
                        pintar_pasarela()
        en_hilo(lambda: conv.preguntar(texto, al_trozo=trozo), terminado)

    # ---------- moverse por la app y fuera de ella ----------
    def accion_de(texto):
        return nk.interpretar(texto, juegos_extra=list(getattr(core, "juegos_modulos", {})))

    def ir_a(accion):
        """Hace una acción de dentro de Kira (pantalla, juego, atrás). Devuelve la frase que dice Kira."""
        tipo = accion["tipo"]
        if tipo == "atras":
            if sm.current == "inicio":
                return "Ya estoy en mi botón."
            tecla(None, 27)
            return ""
        if tipo == "juego":
            if accion["id"].startswith("mejora:"):
                nombre = accion["id"][7:]
                clase = getattr(core, "juegos_modulos", {}).get(nombre)
                if clase is None:
                    return "Ese juego ya no está."
                codigo_ui["empezar_juego"]("", volver="juegos", juego=clase())
                return f"¡A jugar a {nombre}!"
            import juegos_kira as jk
            j = jk.buscar(accion["id"])
            codigo_ui["empezar_juego"](j["codigo"], volver="juegos")
            return f"¡A jugar a {j['titulo']}!"
        destino = accion["destino"]
        if destino.startswith("panel:"):
            ir("panel", destino.split(":", 1)[1])
        else:
            ir(destino)
        return accion["frase"]

    def moverse(texto):
        """Si la frase es moverse, lo hace y devuelve True. Si no, False (y sigue la conversación)."""
        acc = accion_de(texto)
        if not acc:
            return False
        if acc["tipo"] in ("pantalla", "juego", "atras"):
            frase = ir_a(acc)
            if frase:
                decir(frase)
            return True
        movil = getattr(core, "movil", None)
        if movil is None:
            return False
        hecho, frase = movil.hacer(acc)
        if hecho is None:                               # «ve a dormir» no es una app: que conteste Kira
            return False
        decir(("" if hecho else "[x] ") + frase)
        return True

    # ---------- mejoras, programas y diseños pedidos por voz ----------
    def en_equipo():
        """'local' + 'claude' si van a trabajar juntos (para decirlo); si no, ''."""
        rep = getattr(core, "reparto", None)
        try:
            autor, revisor = rep("codigo") if callable(rep) else (None, None)
        except Exception:
            return ""
        return f"{'yo' if autor == 'local' else 'Claude'} y {'Claude' if revisor == 'claude' else 'yo'}" if revisor else ""

    def mejora_por_voz(pedido):
        quien = getattr(core, "cerebro_para_codigo", lambda: None)()
        if quien is None:
            decir("Para programar mejoras necesito un cerebro: el mío (Menú › «Cerebro y oído») o la clave de Claude "
                  "(«config clave: …»). Cuando lo tenga, pídemelo otra vez.")
            return
        equipo = en_equipo()
        decir(f"Vale, me pongo a programar: {pedido}. Lo pruebo aquí en el móvil"
              + (" (y en el ordenador, que está conectado)" if getattr(ctl.pasarela, "url", "") else "")
              + (". Lo haremos en equipo Claude y yo hasta ponernos de acuerdo" if equipo else "")
              + ". Para instalarlo tendrás que tocar Aplicar dos veces.")

        def al_terminar(r):
            if r.get("aprobable"):
                voz.hablar(("Claude y yo estamos de acuerdo. " if r.get("acuerdo") else
                            "Claude y yo no nos hemos puesto de acuerdo: mira lo que dice cada uno. "
                            if r.get("acuerdo") is False else "")
                           + "La mejora ha pasado las pruebas. Revísala y toca Aplicar dos veces si te parece bien.")
            else:
                voz.hablar("No he conseguido una mejora que pase las pruebas. Te dejo el detalle en la terminal.")
        Clock.schedule_once(lambda _dt: hacker["pedir_mejora"](pedido, al_terminar), 2.5)

    def programa_por_voz(pedido):
        """Kira escribe el programa (o juego), lo prueba en modo seguro, lo acuerda con Claude y lo deja en el editor.
        No se instala nada: tú pulsas «Ejecutar» o «Jugar»."""
        if getattr(core, "cerebro_para_codigo", lambda: None)() is None:
            decir("Para escribir programas necesito un cerebro: el mío (Menú › «Cerebro y oído») o la clave de Claude.")
            return
        equipo = en_equipo()
        st["ocupado"] = True
        modelo.poner_estado("pensando")
        decir(f"Vale, te escribo un {pedido}. Lo pruebo en modo seguro"
              + (" y lo repaso con Claude" if equipo else "") + " antes de enseñártelo.")

        def terminado(r):
            st["ocupado"] = False
            if isinstance(r, Exception):
                decir(f"[x] No pude escribir el programa: {r}", hablar=False)
                return
            if not r.get("ok"):
                decir(r["texto"].split("\n")[0], hablar=True)
                return
            juego = "juego" in pedido.split(" ", 1)[0]
            aviso = (("Juego" if juego else "Programa") + " escrito por "
                     + ({"local": "Kira", "claude": "Claude"}.get(r.get("de"), "Kira"))
                     + (", acordado con " + ("Claude" if r.get("de") == "local" else "Kira") if r.get("acuerdo") else "")
                     + f" y probado en modo seguro. Pulsa «{'Jugar' if juego else 'Ejecutar'}».")
            if "input(" in r["codigo"]:
                aviso += " Si pide datos, escríbelos en la caja de entrada (separados con ;)."
            if r.get("acuerdo") is not None:
                aviso += "\n\n" + r["texto"]
            codigo_ui["cargar_en_editor"](r["codigo"], r["nombre"] or "", aviso)
            decir(("Listo, y Claude y yo estamos de acuerdo. " if r.get("acuerdo") else "Listo. ")
                  + f"Te lo dejo en el editor: pulsa {'Jugar' if juego else 'Ejecutar'}.")
        en_hilo(lambda: core.programa_acordado(pedido), terminado)

    def diseno_por_voz(tipo, descripcion):
        nombres = {"web": "la página", "app": "la maqueta", "clip": "el videoclip"}
        decir(f"Vale, diseño {nombres.get(tipo, 'eso')}: {descripcion}.", hablar=True)

        def hecho(origen):
            voz.hablar({"acuerdo": "Hecho, y repasado con Claude. Revísalo y guárdalo si te gusta.",
                        "ia": "Hecho. Revísalo y guárdalo si te gusta."}.get(
                origen, "Lo he hecho con mis plantillas. Revísalo y guárdalo si te gusta."))
        Clock.schedule_once(lambda _dt: diseno["disenar"](tipo, descripcion, hecho), 1.2)

    # ---------- escucha permanente con «Kira» ----------
    def pintar_escucha(texto=None):
        on = st["esc_reloj"] is not None
        btn_escucha.text = "Escucha: SÍ" if on else "Escucha: NO"
        if texto is not None:
            lbl_escucha.text = texto
        elif on:
            lbl_escucha.text = "Te escucho de fondo. Di «Kira» para hablar conmigo."
        else:
            lbl_escucha.text = "Escucha apagada. Escríbeme o activa la escucha."

    def permiso_micro():
        if platform != "android":
            return True
        try:
            from android.permissions import Permission, check_permission, request_permissions
            if not check_permission(Permission.RECORD_AUDIO):
                request_permissions([Permission.RECORD_AUDIO])
                return False
        except Exception:
            pass
        return True

    def usar_oido_propio():
        return ajustes.oido_propio and oido.disponible()

    def al_frase_oido(texto):                          # llega desde el hilo de Java: se pasa al de la pantalla
        if getattr(core, "en_segundo_plano", False):    # estás en otra app: la pantalla de Kira está en pausa
            threading.Thread(target=frase_en_segundo_plano, args=(texto,), daemon=True).start()
            return
        Clock.schedule_once(lambda _dt, t_=texto: procesar_frase(t_), 0)

    def frase_en_segundo_plano(texto):
        """Kira te oye mientras usas otra app: contesta en voz alta, sin tocar la pantalla."""
        que, orden = escucha.oir(texto)
        if que == "atenta":
            voz.hablar("¿Sí? Dime.")
        elif que == "orden" and accion_de(orden):
            acc = accion_de(orden)
            movil = getattr(core, "movil", None)
            if movil is None:
                return
            if acc["tipo"] in ("pantalla", "juego", "atras"):     # algo de Kira: primero vuelve a primer plano
                hecho, frase = movil.hacer({"tipo": "kira"}, en_fondo=True)
                if hecho and acc["tipo"] != "atras":
                    Clock.schedule_once(lambda _dt, a=acc: ir_a(a), 0.6)
                    frase = acc.get("frase") or "Voy."
                voz.hablar(frase)
                return
            hecho, frase = movil.hacer(acc, en_fondo=True)
            if hecho is not None:
                voz.hablar(frase)
                return
            try:
                oido.pausar(True)
                r, _via = conv.preguntar(orden)
                voz.hablar(r.replace("[OK]", "").replace("[x]", "").replace("[i]", "")[:400])
            except Exception as e:
                voz.hablar(f"No he podido: {e}")
            finally:
                oido.pausar(False)
        elif que == "orden":
            try:
                oido.pausar(True)
                r, _via = conv.preguntar(orden)
                voz.hablar(r.replace("[OK]", "").replace("[x]", "").replace("[i]", "")[:400])
            except Exception as e:
                voz.hablar(f"No he podido: {e}")
            finally:
                oido.pausar(False)

    def arrancar_escucha():
        if st["esc_reloj"] is not None:
            return True
        if usar_oido_propio():                         # oído propio: continuo, sin pitidos y sin internet
            if not permiso_micro():
                pintar_escucha("Necesito permiso para el micrófono. Concédelo y pulsa «Escucha».")
                return False
            ok, msg = oido.encender(al_frase_oido)
            if not ok:
                pintar_escucha(msg)
                return False
            st["oido"] = True
            st["esc_reloj"] = Clock.schedule_interval(ciclo_escucha, 0.4)
            if modelo.estado == "reposo":
                modelo.poner_estado("escuchando")
            pintar_escucha("Te escucho de fondo con mi oído propio. Di «Kira» cuando quieras.")
            return True
        if ajustes.oido_propio and oido.libreria_disponible() and not oido.modelo_instalado():
            # sin el reconocedor de Android (pitidos): Kira se descarga su oído ella sola y luego escucha
            if oido.estado != "descargando":
                def bajar_oido():
                    try:
                        oido.descargar_modelo()
                        Clock.schedule_once(lambda _dt: reiniciar_escucha(), 0)
                    except Exception as e:
                        Clock.schedule_once(lambda _dt, e_=e: pintar_escucha(
                            f"No pude descargar mi oído ({e_}). Revisa internet y pulsa «Escucha»."), 0)
                threading.Thread(target=bajar_oido, daemon=True).start()
            pintar_escucha("Me estoy descargando mi oído propio (39 MB, una sola vez). En un momento te escucho sin pitidos.")
            return False
        if not voz.puede_escuchar():
            pintar_escucha("No puedo escuchar en este dispositivo. Escríbeme.")
            return False
        if not permiso_micro():
            pintar_escucha("Necesito permiso para el micrófono. Concédelo y pulsa «Escucha».")
            return False
        st["esc_fallos"] = 0
        st["esc_reloj"] = Clock.schedule_interval(ciclo_escucha, 0.4)
        if modelo.estado == "reposo":
            modelo.poner_estado("escuchando")
        if platform == "android" and ajustes.oido_propio and not oido.libreria_disponible():
            pintar_escucha("Uso el reconocedor de Android (solo en esta pantalla): no encuentro mi oído propio. "
                           "Mira Menú › Cerebro y oído.")
        else:
            pintar_escucha()
        return True

    def parar_escucha():
        if st["esc_reloj"] is not None:
            st["esc_reloj"].cancel()
            st["esc_reloj"] = None
        if st["esc_stt"]:
            voz.parar_escucha()
            st["esc_stt"] = False
        if st["oido"]:
            oido.apagar()
            st["oido"] = False
        escucha.olvidar()                              # el borrador se borra al apagar
        if modelo.estado in ("escuchando", "atenta"):
            modelo.poner_estado("reposo")
        pintar_escucha()

    def alternar_escucha():
        ajustes.alternar_escucha()
        if ajustes.escucha_permanente:
            arrancar_escucha()
        else:
            parar_escucha()
        pintar_config()

    def ciclo_escucha(dt):
        escucha.purgar()                               # lo oído hace más de 15 s se borra
        if modelo.estado == "atenta" and not escucha.atenta:
            modelo.poner_estado(estado_base())
            pintar_escucha()
        if st["oido"]:                                 # el oído propio escucha en TODAS las pantallas
            oido.pausar(st["ocupado"] or voz.hablando() or sm.current == "jugar")
            if oido.estado == "error":
                pintar_escucha(oido.mensaje)
            return
        callada = sm.current != "inicio" or st["ocupado"] or voz.hablando()
        if callada:                                    # fuera de la portada, pensando o hablando: no escucha
            if st["esc_stt"]:
                voz.parar_escucha()
                st["esc_stt"] = False
            return
        if not st["esc_stt"]:
            ok, msg = voz.iniciar_escucha()
            if not ok:
                st["esc_fallos"] += 1
                if st["esc_fallos"] >= 5:
                    parar_escucha()
                    pintar_escucha(msg)
                return
            st["esc_stt"], st["esc_t"] = True, 0.0
            return
        estado, txt = voz.sondear()
        if estado == "escuchando":
            st["esc_t"] += dt
            if st["esc_t"] > 12:                       # una escucha no debe quedarse colgada
                voz.parar_escucha()
                st["esc_stt"] = False
            return
        st["esc_stt"] = False                          # terminó esta frase: la siguiente vuelta escucha otra
        if estado != "listo" or not txt:
            return
        st["esc_fallos"] = 0
        procesar_frase(txt)

    def procesar_frase(txt):
        que, orden = escucha.oir(txt)
        if que == "orden" and accion_de(orden) and not st["ocupado"]:
            pintar_escucha("«" + orden[:60] + "»")
            enviar(orden)                              # moverse: va directo, sin volver antes al botón
            return
        if que != "nada" and sm.current != "inicio":   # te ha oído desde otra pantalla: vuelve a su botón
            ir("inicio")
        if que == "atenta":
            modelo.poner_estado("atenta")
            pintar_escucha("Te escucho… dime.")
            decir("¿Sí? Dime.", hablar=True)
            modelo.poner_estado("atenta")
        elif que == "orden":
            pintar_escucha("«" + orden[:60] + "»")
            enviar(orden)

    def entrar():
        if st["entrando"]:
            return
        st["entrando"] = True
        if ctl.efectos_activos():
            def fin(*_):
                orbe.zoom, orbe.brillo, st["entrando"] = 1.0, 1.0, False
                ir("menu")
            anim = Animation(zoom=2.6, brillo=0.0, duration=0.5, t="in_quad")
            anim.bind(on_complete=fin)
            anim.start(orbe)
        else:
            st["entrando"] = False
            ir("menu")

    def saludar(*_):
        if st["saludado"]:
            return
        st["saludado"] = True
        tiene = bool(getattr(core, "tiene_clave", lambda: False)())
        propio = getattr(core, "cerebro_propio", None)
        despertando = bool(propio and not tiene and propio.modelo_instalado() and propio.tiene_motor())
        texto = ik.saludo(datetime.datetime.now().hour, tiene or despertando, voz.puede_hablar(),
                          voz.puede_escuchar() or oido.disponible())
        if despertando:
            texto += " Estoy cargando mi cerebro: en unos segundos podré charlar contigo."
        if ajustes.escucha_permanente and voz.puede_escuchar():
            texto += " Para hablarme, di «Kira»."
        decir(texto)
        if ajustes.escucha_permanente:
            arrancar_escucha()
        else:
            pintar_escucha()

    campo.bind(on_text_validate=lambda *_: enviar())

    # =================================================================================
    #  MENÚ
    # =================================================================================
    p_menu = Screen(name="menu")
    fondo_claro(p_menu)
    raiz_menu = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    cab_m = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    cab_m.add_widget(boton("‹ Kira", lambda: ir("inicio"), GRIS, alto=44, size_hint_x=None, width=dp(100)))
    cab_m.add_widget(est.ajustar(Label(text="Menú", color=NEON, font_size=tam(20), bold=True, halign="left", **FUENTE), lineas=1))
    raiz_menu.add_widget(cab_m)
    sv_m = ScrollView(do_scroll_x=False)
    rejilla = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, row_default_height=dp(92), row_force_default=True)
    rejilla.bind(minimum_height=rejilla.setter("height"))
    menu_st = {"todos": False}

    def ajustar_columnas(*_):
        rejilla.cols = 2 if Window.width < dp(720) else (3 if Window.width < dp(1100) else 4)
    Window.bind(width=ajustar_columnas)
    ajustar_columnas()

    def baldosa(a):
        """Tarjeta del menú: título arriba (una línea) y descripción corta debajo (hasta dos), cada uno en su sitio."""
        tinta = mk.color_oscuro(a["color"])
        t = Button(text=f"[b]{a['titulo']}[/b]", markup=True, halign="left", valign="top", background_normal="",
                   background_down="", background_color=(0, 0, 0, 0), color=tinta, font_size=tam(15.5),
                   shorten=True, shorten_from="right", **FUENTE)
        fondo_c = est.fondo_redondeado(t, mk.color_claro(a["color"]), radio=14)
        with t.canvas.before:                                     # franja de color a la izquierda
            Color(*a["color"], 1)
            franja = Rectangle(pos=t.pos, size=(dp(5), t.height))
        desc = est.ajustar(Label(text=a["desc"], color=tinta[:3] + (0.8,), font_size=tam(13), halign="left",
                                 size_hint=(None, None), **FUENTE), minimo=10.5, lineas=2, margen=0)
        t.add_widget(desc)

        def colocar(*_):
            t.text_size = (max(1, t.width - dp(28)), max(1, t.height - dp(22)))
            franja.pos, franja.size = (t.x + dp(6), t.y + dp(12)), (dp(4), max(1, t.height - dp(24)))
            desc.size = (max(1, t.width - dp(28)), max(1, t.height * 0.5))
            desc.pos = (t.x + dp(14), t.y + dp(8))
        t.bind(pos=colocar, size=colocar)
        t.bind(on_press=lambda *_: setattr(fondo_c, "a", 0.75),
               on_release=lambda _b, d=a["destino"]: (setattr(fondo_c, "a", 1),
                                                      ir(d[1] if d[0] == "pantalla" else "panel",
                                                         d[1] if d[0] == "panel" else None)))
        return t

    def pintar_menu():
        rejilla.clear_widgets()
        for a in mk.principales():
            rejilla.add_widget(baldosa(a))
        if menu_st["todos"]:
            for a in mk.secundarios():
                rejilla.add_widget(baldosa(a))
        btn_mas.text = "Menos apartados" if menu_st["todos"] else f"Más apartados ({len(mk.secundarios())})"

    def alternar_mas():
        menu_st["todos"] = not menu_st["todos"]
        pintar_menu()
    btn_mas = boton("", alternar_mas, GRIS, alto=44)
    sv_m.add_widget(rejilla)
    raiz_menu.add_widget(sv_m)
    raiz_menu.add_widget(btn_mas)
    p_menu.add_widget(raiz_menu)
    sm.add_widget(p_menu)
    pintar_menu()

    # =================================================================================
    #  PANEL (Sala, Mejoras, Módulos, Consola, Ajustes) dentro de la interfaz
    # =================================================================================
    p_panel = Screen(name="panel")
    caja_panel = BoxLayout(orientation="vertical")
    barra_p = BoxLayout(size_hint_y=None, height=dp(40), padding=(dp(6), dp(2)))
    barra_p.add_widget(boton_o("‹ Menú", lambda: ir("menu"), OSCURA["GRIS"], alto=36, size_hint_x=None, width=dp(100)))
    caja_panel.add_widget(barra_p)
    caja_panel.add_widget(panel_raiz)
    p_panel.add_widget(caja_panel)
    sm.add_widget(p_panel)

    # =================================================================================
    #  BÚSQUEDA
    # =================================================================================
    _, c_bus = pantalla("busqueda", "BÚSQUEDA")
    campo_bus = entrada("Busca en notas, lecciones, módulos y conversaciones…")
    sv_bus, res_bus = texto_largo("Busca en lo que hay guardado en este dispositivo. No busca en internet.")

    def buscar():
        q = campo_bus.text
        lecc = [l for l in ctl.lecciones_texto(limite=30, max_chars=6000).split("\n") if l.strip()]
        mods = [f"{m['nombre']} ({', '.join(m['comandos']) or 'sin comandos'})" for m in ctl.modulos()]
        fuentes = {"nota": notas.textos(), "lección": lecc, "módulo": mods,
                   "aprendido": [f"{i['tema']}: {i['texto']}" for i in cerebro.conocimiento.listar()],
                   "charla": [h["texto"] for h in conv.historial]}
        res = mk.buscar_local(q, fuentes)
        res_bus.text = "\n\n".join(f"[{f}] {t}" for f, t in res) if res else "Sin resultados."

    def preguntar_a_kira():
        q = ik.limpiar_entrada(campo_bus.text)
        if q:
            ir("inicio")
            enviar(q)
    campo_bus.bind(on_text_validate=lambda *_: buscar())
    for w in (campo_bus, boton("Buscar", buscar, VERDE), boton("Preguntárselo a Kira", preguntar_a_kira), sv_bus):
        c_bus.add_widget(w)

    # =================================================================================
    #  NOTAS
    # =================================================================================
    _, c_not = pantalla("notas", "NOTAS")
    campo_not = entrada("Nueva nota…")
    msg_not = Label(text="", size_hint_y=None, height=dp(22), color=TENUE, font_size=sp(13), **FUENTE)
    sv_not = ScrollView(do_scroll_x=False)
    lista_not = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
    lista_not.bind(minimum_height=lista_not.setter("height"))
    sv_not.add_widget(lista_not)

    def pintar_notas():
        lista_not.clear_widgets()
        for n in notas.listar():
            fila_n = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(6))
            lb = Label(text=n["texto"], color=TXT, halign="left", valign="middle", font_size=sp(14), **FUENTE)
            lb.bind(size=lambda w, s: setattr(w, "text_size", (s[0], s[1])), )
            fila_n.add_widget(lb)
            fila_n.add_widget(boton("Borrar", lambda i=n["id"]: borrar_nota(i), ROJO, alto=44,
                                    size_hint_x=None, width=dp(80)))
            lista_not.add_widget(fila_n)

    def borrar_nota(i):
        notas.borrar(i)
        pintar_notas()

    def anadir_nota():
        try:
            ok, m = notas.anadir(campo_not.text)
        except OSError as e:
            ok, m = False, f"No se pudo guardar: {e}"
        msg_not.text = m
        if ok:
            campo_not.text = ""
            pintar_notas()
    campo_not.bind(on_text_validate=lambda *_: anadir_nota())
    for w in (campo_not, boton("Añadir nota", anadir_nota, VERDE), msg_not, sv_not):
        c_not.add_widget(w)
    ganchos["notas"] = pintar_notas

    # =================================================================================
    #  MEMORIA
    # =================================================================================
    _, c_mem = pantalla("memoria", "MEMORIA")
    sv_mem, txt_mem = texto_largo("")
    confirm_borrado = {"reloj": None}
    btn_borrar = boton("Borrar conversación", lambda: pedir_borrado(), ROJO)

    def pintar_memoria():
        lineas = [("Tú: " if h["rol"] == "tu" else "Kira: ") + h["texto"] for h in conv.historial[-20:]]
        lecc = ctl.lecciones_texto(limite=10, max_chars=2500)
        txt_mem.text = ("CONVERSACIÓN (últimos turnos)\n" + ("\n".join(lineas) or "(vacía)")
                        + "\n\nLECCIONES DE MEJORAS\n" + (lecc or "(ninguna)"))

    def pedir_borrado():
        if confirm_borrado["reloj"] is None:           # primer toque: pide confirmar
            btn_borrar.text = "¿Seguro? Toca de nuevo"
            confirm_borrado["reloj"] = Clock.schedule_once(restablecer_borrado, 4)
        else:
            confirm_borrado["reloj"].cancel()
            conv.borrar()
            restablecer_borrado()
            pintar_memoria()

    def restablecer_borrado(*_):
        confirm_borrado["reloj"] = None
        btn_borrar.text = "Borrar conversación"
    c_mem.add_widget(sv_mem)
    c_mem.add_widget(btn_borrar)
    ganchos["memoria"] = pintar_memoria

    # =================================================================================
    #  ESTADO
    # =================================================================================
    _, c_est = pantalla("estado", "ESTADO")
    sv_est, txt_est = texto_largo("")

    def refrescar_estado():
        txt_est.text = "Comprobando…"
        en_hilo(lambda: mk.estado_sistema(ctl, dir_datos),
                lambda r: setattr(txt_est, "text", "\n".join(r) if isinstance(r, list) else f"[x] {r}"))
    c_est.add_widget(sv_est)
    c_est.add_widget(boton("Actualizar", refrescar_estado, VERDE))
    ganchos["estado"] = refrescar_estado

    # =================================================================================
    #  PASARELA
    # =================================================================================
    _, c_pas = pantalla("pasarela", "PASARELA")
    sv_pas, txt_pas = texto_largo("")
    pas_st = {"extra": ""}
    campo_codigo = entrada("Código de 6 cifras que sale en el ordenador")
    fila_codigo = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(6))
    fila_codigo.add_widget(campo_codigo)

    def pintar_pasarela(extra=None):
        if extra is not None:
            pas_st["extra"] = extra
        url = getattr(ctl.pasarela, "url", "")
        nombre = getattr(ctl.pasarela, "nombre", "") or url
        enl = getattr(core, "enlace", None)
        esperando = enl is not None and enl.esperando_codigo()
        conectado = (f"Ordenador guardado: {nombre}" + (f"  ({url})" if url and nombre != url else "")) if url \
            else "No estoy conectada a ningún ordenador (no hace falta)."
        pasos = ("Ya no necesito el ordenador: pruebo las mejoras aquí, en mi laboratorio del móvil, y tú decides si "
                 "se instalan. Si conectas el laboratorio del ordenador, las pruebo también allí (más seguro).\n\n"
                 "Para conectarlo (opcional, una sola vez):\n"
                 "  1. En el ordenador, doble clic en «Arrancar laboratorio» (carpeta kira_laboratorio). Si Windows "
                 "pregunta, pulsa «Permitir».\n"
                 "  2. Aquí pulsa «Conectar con el ordenador» (o dime «Kira, conéctate al ordenador»).\n"
                 "  3. Dime o escribe el código de 6 cifras que sale en la pantalla del ordenador.\n"
                 "Después me conecto sola, aunque el ordenador cambie de dirección.")
        txt_pas.text = conectado + "\n\n" + pasos + (f"\n\n{pas_st['extra']}" if pas_st["extra"] else "")
        fila_codigo.opacity, fila_codigo.disabled = (1, False) if esperando else (0, True)
        fila_codigo.height = dp(52) if esperando else 0              # oculto no deja hueco

    def conectar_pasarela():
        pintar_pasarela("Buscando el laboratorio en tu WiFi…")
        en_hilo(core.enlace.conectar, lambda r: pintar_pasarela(f"[x] {r}" if isinstance(r, Exception) else r))

    def enviar_codigo():
        texto = campo_codigo.text
        campo_codigo.text = ""
        pintar_pasarela("Comprobando el código…")
        en_hilo(lambda: core.enlace.con_codigo(texto) or "[x] Escribe las 6 cifras del código.",
                lambda r: pintar_pasarela(f"[x] {r}" if isinstance(r, Exception) else r))

    def olvidar_pasarela():
        pintar_pasarela(core.enlace.olvidar())

    def probar_pasarela():
        pintar_pasarela("Probando…")
        en_hilo(lambda: core.enlace.estado()[1], lambda r: pintar_pasarela(f"[x] {r}" if isinstance(r, Exception) else r))
    campo_codigo.bind(on_text_validate=lambda *_: enviar_codigo())
    fila_codigo.add_widget(boton("Enviar código", enviar_codigo, VERDE, alto=48, size_hint_x=None, width=dp(130)))
    for w in (sv_pas, boton("Conectar con el ordenador", conectar_pasarela, VERDE), fila_codigo,
              boton("Comprobar la conexión", probar_pasarela),
              boton("Pedir una mejora", lambda: ir("panel", "orden")),
              boton("Olvidar este laboratorio", olvidar_pasarela, ROJO),
              boton("Configurar a mano (avanzado)", lambda: ir("panel", "ajustes"))):
        c_pas.add_widget(w)
    ganchos["pasarela"] = pintar_pasarela

    # =================================================================================
    #  CONFIGURACIÓN
    # =================================================================================
    _, c_cfg = pantalla("config", "CONFIGURACIÓN")
    msg_cfg = Label(text="", size_hint_y=None, height=dp(60), color=TENUE, font_size=tam(13), halign="left",
                    valign="top", **FUENTE)
    msg_cfg.bind(width=lambda w, a: setattr(w, "text_size", (a, None)))
    btn_voz = boton("", lambda: alternar_voz(), GRIS)
    btn_esc_cfg = boton("", lambda: alternar_escucha(), GRIS)
    btn_efe = boton("", lambda: alternar_efectos(), GRIS)
    btn_equipo = boton("", lambda: alternar_equipo(), GRIS)

    def pintar_config(texto=""):
        btn_voz.text = "Kira habla en voz alta: " + ("SÍ" if ajustes.voz_hablar else "NO")
        btn_esc_cfg.text = "Escucha permanente («Kira»): " + ("SÍ" if ajustes.escucha_permanente else "NO")
        btn_efe.text = "Efectos visuales: " + ("SÍ" if ctl.efectos_activos() else "NO (ahorra batería)")
        aj = getattr(core, "acuerdo", None)
        btn_equipo.text = "Kira y Claude en equipo: " + ("SÍ" if aj is None or aj.activo else "NO")
        extra = ""
        if not voz.puede_hablar():
            extra += "Voz de salida no disponible aquí. "
        elif getattr(voz, "aviso", lambda: "")():
            extra += f"Voz: {voz.aviso()}. "
        if not voz.puede_escuchar():
            extra += "Micrófono no disponible aquí. "
        msg_cfg.text = (texto + " " + extra).strip() or f"Velocidad del texto: {ajustes.velocidad} letras/seg."

    def alternar_voz():
        ajustes.alternar_voz()
        pintar_config()

    def alternar_efectos():
        ctl.poner_efectos(not ctl.efectos_activos())
        pintar_config()

    def alternar_equipo():
        aj = getattr(core, "acuerdo", None)
        if aj is None:
            return
        pintar_config(core.procesar_orden(("desactiva" if aj.activo else "activa") + " el acuerdo con claude"))

    def velocidad(delta):
        ajustes.cambiar_velocidad(delta)
        pintar_config(f"Velocidad del texto: {ajustes.velocidad} letras/seg.")
    def permiso_fondo():
        movil = getattr(core, "movil", None)
        _h, t = movil.hacer({"tipo": "permiso_fondo"}) if movil is not None else (False, nk.Movil.SOLO_MOVIL)
        pintar_config(t)
    for w in (btn_voz, btn_esc_cfg, btn_efe, btn_equipo, boton("Texto más lento", lambda: velocidad(-10)),
              boton("Texto más rápido", lambda: velocidad(10)),
              boton("Que abra apps aunque esté en segundo plano", permiso_fondo),
              boton("Laboratorio del ordenador (opcional)", lambda: ir("pasarela"), GRIS),
              boton("Clave de la API", lambda: ir("panel", "ajustes")), msg_cfg,
              Widget()):                                  # hueco flexible: los botones quedan arriba, no abajo
        c_cfg.add_widget(w)
    ganchos["config"] = pintar_config

    # =================================================================================
    #  LIENZO (Kira dibuja)
    # =================================================================================
    EscenaWidget, exportar_png = ek.crear_widgets()
    _, c_lie = pantalla("lienzo", "LIENZO")
    escena_w = EscenaWidget(size_hint_y=1)
    leyenda = Label(text="", size_hint_y=None, height=dp(40), color=TXT, font_size=sp(14), halign="left",
                    valign="middle", **FUENTE)
    leyenda.bind(width=lambda w, a: setattr(w, "text_size", (a, None)))
    campo_lie = entrada("Describe la escena: playa al atardecer con palmeras…")
    est_lie = {"desc": None, "variante": 0, "formas": []}

    def mostrar_escena(desc, mensaje=""):
        try:
            formas = ek.construir(desc)
        except ValueError as e:
            leyenda.text = f"[x] {e}"
            return
        est_lie.update(desc=desc, formas=formas)
        escena_w.poner(formas)
        leyenda.text = mensaje or desc["titulo"]
        ir("lienzo")

    def dibujar_desde_campo(variante=0):
        texto = ik.limpiar_entrada(campo_lie.text) or (est_lie["desc"] or {}).get("titulo", "")
        d = ek.interpretar("dibuja " + texto, variante)
        if d is None or not d.get("tema"):
            leyenda.text = "Solo sé dibujar: " + ek.temas_conocidos() + "."
            return
        est_lie["variante"] = variante
        mostrar_escena(d)

    def otra_variante():
        if est_lie["desc"] is None:
            return
        v = est_lie["variante"] + 1
        d = dict(est_lie["desc"])
        d["semilla"] = (d["semilla"] + 7919) & 0xFFFFFFFF
        est_lie["variante"] = v
        mostrar_escena(d, d["titulo"] + f" (variante {v})")

    def guardar_imagen():
        if not est_lie["formas"]:
            leyenda.text = "Primero dibuja algo."
            return
        carpeta = os.path.join(dir_datos, "galeria")
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, f"escena_{datetime.datetime.now():%Y%m%d_%H%M%S}.png")
        ok_, msg = exportar_png(est_lie["formas"], ruta)
        leyenda.text = msg + ("  (carpeta privada de la app)" if ok_ else "")
    campo_lie.bind(on_text_validate=lambda *_: dibujar_desde_campo())
    c_lie.add_widget(escena_w)
    c_lie.add_widget(leyenda)
    c_lie.add_widget(campo_lie)
    fila_lie = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
    for txt_b, acc in (("Dibujar", dibujar_desde_campo), ("Otra variante", otra_variante), ("Guardar PNG", guardar_imagen)):
        fila_lie.add_widget(boton(txt_b, acc, VERDE))
    c_lie.add_widget(fila_lie)

    # =================================================================================
    #  CONOCIMIENTO (lo que Kira ha aprendido)
    # =================================================================================
    _, c_con = pantalla("conocimiento", "CONOCIMIENTO")
    msg_con = Label(text="", size_hint_y=None, height=dp(40), color=TENUE, font_size=sp(13), halign="left",
                    valign="top", **FUENTE)
    msg_con.bind(width=lambda w, a: setattr(w, "text_size", (a, None)))
    sv_con = ScrollView(do_scroll_x=False)
    lista_con = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
    lista_con.bind(minimum_height=lista_con.setter("height"))
    sv_con.add_widget(lista_con)

    def pintar_conocimiento():
        lista_con.clear_widgets()
        items = cerebro.conocimiento.listar()
        msg_con.text = (f"{len(items)} cosa(s) aprendida(s). Se guardan solo aquí; lo de internet solo si tú dices «sí».")
        for i in items[:60]:
            fila_c = BoxLayout(size_hint_y=None, height=dp(78), spacing=dp(6))
            origen = "internet" if str(i.get("fuente", "")).startswith("http") else "tú"
            lb = Label(text=f"[{origen}] {i['texto'][:160]}", color=TXT, halign="left", valign="middle",
                       font_size=sp(13), **FUENTE)
            lb.bind(size=lambda w, s_: setattr(w, "text_size", (s_[0], s_[1])))
            fila_c.add_widget(lb)
            fila_c.add_widget(boton("Olvidar", lambda i_=i["id"]: olvidar(i_), ROJO, alto=44, size_hint_x=None, width=dp(84)))
            lista_con.add_widget(fila_c)

    def olvidar(id_):
        cerebro.conocimiento.descartar(id_)
        pintar_conocimiento()
    c_con.add_widget(msg_con)
    c_con.add_widget(sv_con)
    ganchos["conocimiento"] = pintar_conocimiento

    # =================================================================================
    #  AYUDA
    # =================================================================================
    _, c_ayu = pantalla("ayuda", "AYUDA")
    sv_ayu, _lb = texto_largo(mk.AYUDA)
    c_ayu.add_widget(sv_ayu)

    # =================================================================================
    #  EDITOR DE CÓDIGO Y JUEGOS
    # =================================================================================
    def juegos_de_mejoras():
        """Juegos que han añadido los módulos de mejora (registrar() -> {'juego …': ClaseJuego})."""
        lista = []
        for nombre, clase in sorted(getattr(core, "juegos_modulos", {}).items()):
            lista.append((nombre, lambda c=clase: codigo_ui["empezar_juego"]("", volver="juegos", juego=c())))
        return lista
    codigo_ui = montar_codigo(sm, {
        "boton": boton, "entrada": entrada, "texto_largo": texto_largo, "en_hilo": en_hilo, "pantalla": pantalla,
        "ir": lambda *a, **k: ir(*a, **k), "TXT": TXT, "TENUE": TENUE, "GRIS": GRIS, "VERDE": VERDE, "ROJO": ROJO,
        "FUENTE": FUENTE, "FUENTE_MONO": FUENTE_MONO, "dir_datos": dir_datos, "ganchos": ganchos,
        "juegos_extra": juegos_de_mejoras})

    # =================================================================================
    #  CEREBRO Y OÍDO PROPIOS
    # =================================================================================
    def reiniciar_escucha():
        parar_escucha()
        if ajustes.escucha_permanente:
            arrancar_escucha()
    montar_cerebro(sm, {"boton": boton, "texto_largo": texto_largo, "pantalla": pantalla, "ganchos": ganchos,
                        "TXT": TXT, "TENUE": TENUE, "GRIS": GRIS, "VERDE": VERDE, "ROJO": ROJO, "NEON": NEON,
                        "FUENTE": FUENTE, "core": core, "oido": oido, "ajustes": ajustes,
                        "reiniciar_escucha": reiniciar_escucha})

    # =================================================================================
    #  LECTOR DE CAPTURAS
    # =================================================================================
    montar_lector(sm, {"boton": boton, "texto_largo": texto_largo, "pantalla": pantalla, "en_hilo": en_hilo,
                       "ganchos": ganchos, "TXT": TXT, "GRIS": GRIS, "VERDE": VERDE, "FUENTE": FUENTE, "core": core,
                       "abrir_en_editor": lambda codigo, aviso="": codigo_ui["cargar_en_editor"](codigo, "", aviso)})

    # =================================================================================
    #  SALA HACKER (habitación 3D, terminal, biblioteca)
    # =================================================================================
    hacker = montar_sala_hacker(sm, {
        **PIEZAS_SALA, "en_hilo": en_hilo,
        "ir": lambda *a, **k: ir(*a, **k), "ctl": ctl, "core": core, "cerebro": cerebro, "voz": voz,
        "ganchos": ganchos, "dir_datos": dir_datos, "ajustes": ajustes,
        "abrir_en_editor": lambda codigo, aviso="": codigo_ui["cargar_en_editor"](codigo, "", aviso)})

    # =================================================================================
    #  SALA DE DISEÑO, SALA DE CINE, MEDIATECA, REPRODUCTOR
    # =================================================================================
    diseno = montar_sala_diseno(sm, {
        **PIEZAS_SALA, "en_hilo": en_hilo,
        "ir": lambda *a, **k: ir(*a, **k), "core": core, "voz": voz,
        "ganchos": ganchos, "dir_datos": dir_datos, "ajustes": ajustes})

    # =================================================================================
    #  SALA DE CIBERSEGURIDAD (búnker de solo lectura y aprendizaje)
    # =================================================================================
    ciber = montar_sala_ciber(sm, {
        **PIEZAS_SALA, "en_hilo": en_hilo,
        "ir": lambda *a, **k: ir(*a, **k), "core": core, "voz": voz, "ganchos": ganchos,
        "dir_datos": dir_datos, "ajustes": ajustes})

    # =================================================================================
    #  MESA DE MEZCLA Y EDITOR DE VÍDEO
    # =================================================================================
    montar_av(sm, {
        **PIEZAS_SALA, "en_hilo": en_hilo,
        "ir": lambda *a, **k: ir(*a, **k), "core": core, "ganchos": ganchos, "dir_datos": dir_datos})

    # =================================================================================
    #  BITÁCORA (pasos, guías, fallos y notas)
    # =================================================================================
    montar_bitacora(sm, {"boton": boton_o, "entrada": entrada_o, "texto_largo": texto_largo_o, "NEON": OSCURA["NEON"],
                         "GRIS": OSCURA["GRIS"], "VERDE": OSCURA["VERDE"], "FUENTE": FUENTE, "ir": lambda *a, **k: ir(*a, **k), "core": core, "ganchos": ganchos})

    # =================================================================================
    #  TALLER (qué sabe hacer Kira y qué le falta)
    # =================================================================================
    montar_taller(sm, {
        **PIEZAS_SALA, "en_hilo": en_hilo,
        "ir": lambda *a, **k: ir(*a, **k), "core": core, "ganchos": ganchos,
        "preparar_mejora": hacker["preparar_mejora"]})

    # =================================================================================
    #  NAVEGACIÓN
    # =================================================================================
    def ir(nombre, sub=None):
        if nombre != "panel":
            panel_raiz.detener_efectos()
        if nombre != "sala_hacker":
            hacker["detener"]()
        if nombre != "sala_ciber":
            ciber["detener"]()
        if nombre != "jugar":
            codigo_ui["parar_juego"]()
        diseno["detener_si_sale"](nombre)
        sm.current = nombre
        if nombre == "inicio":
            orbe.iniciar()
        else:
            orbe.detener()
        if nombre == "panel":
            panel_raiz.ir(sub or "orden")
        gancho = ganchos.get(nombre)
        if gancho:
            gancho()

    def tecla(_ventana, clave, *_a):
        if clave == 27:                          # Esc / botón atrás de Android
            if sm.current == "inicio":
                return False                     # en la portada, atrás cierra la app como siempre
            if sm.current in ("terminal", "biblioteca"):
                hacker["volver_a_sala"]()                 # de la terminal/biblioteca se vuelve a la habitación
            elif sm.current in diseno["atras"]:
                diseno["atras"][sm.current]()             # estudio/mediateca -> sala de diseño; reproductor -> cine; cine -> diseño
            elif sm.current in ciber["atras"]:
                ciber["atras"][sm.current]()              # consola -> sala de ciberseguridad
            else:
                ir("inicio" if sm.current == "menu" else "menu")
            return True
        return False
    Window.bind(on_keyboard=tecla)

    def revisar_avisos(_dt):
        avisos = getattr(core, "avisos", None)
        if avisos is None or st["ocupado"]:
            return
        for _modulo, texto in avisos.vencidos():
            decir(texto)                                 # se ve en la burbuja y se oye
            break

    sm.control, sm.ir = ctl, ir

    # =================================================================================
    #  ARRANQUE: «Preparando a Kira» (oído, cerebro, lector y pantalla listos antes de empezar)
    # =================================================================================
    import arranque_kira
    import red_kira
    preparacion = arranque_kira.Preparacion(core, oido, ajustes, encender_oido=arrancar_escucha,
                                            red=red_kira.red_sin_limite)

    def empezar_kira():
        ir("inicio")
        Clock.schedule_once(saludar, 0.8)
    arranque = arranque_kira.montar_arranque(sm, {"boton": boton, "fondo_claro": fondo_claro, "TXT": TXT, "NEON": NEON,
                                                  "VERDE": VERDE, "FUENTE": FUENTE, "preparacion": preparacion,
                                                  "Portada": PortadaKira, "TENUE": TENUE,
                                                  "al_terminar": empezar_kira})
    if preparacion.hace_falta():
        sm.current = "arranque"
        arranque["empezar"]()
    else:
        empezar_kira()
    Clock.schedule_interval(revisar_avisos, 1.0)
    return sm
