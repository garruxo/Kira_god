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
import time


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
    from pantalla_pintor_kira import montar_pintor
    from pantalla_internet_kira import montar_internet
    from pantalla_pdf_kira import montar_pdf
    from pantalla_librerias_kira import montar_librerias
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

    # ---------- bocadillo: Kira contesta en la pantalla en la que estés (sin llevarte a su botón) ----------
    boc = {"w": None, "hasta": 0.0, "reloj": None, "visible": False}
    import tareas_kira as tk_
    gestor = getattr(core, "tareas", None) or tk_.Gestor(os.path.join(getattr(core, "dir", "."), "tareas.json"))
    core.tareas = gestor                               # una tarea larga cada vez, con su barra de tiempo y %
    barra = {"w": None, "visible": False, "colocar": None}

    def ocultar_bocadillo(*_):
        w = boc["w"]
        if boc["reloj"] is not None:
            boc["reloj"].cancel()
            boc["reloj"] = None
        if w is not None and boc["visible"]:
            boc["visible"] = False
            try:
                Window.remove_widget(w)
            except Exception:
                pass

    def bocadillo(texto, segundos=None):
        """Enseña lo que dice Kira flotando arriba, en cualquier pantalla que no sea la de su botón."""
        texto = str(texto or "").strip()
        if not texto or sm.current == "inicio":
            return
        w = boc["w"]
        if w is None:
            w = Label(text="", size_hint=(None, None), color=TXT, font_size=tam(15), halign="left", valign="top",
                      **FUENTE)
            est.fondo_redondeado(w, (1, 1, 1, 0.97), radio=16)

            def colocar(*_):
                ancho = max(dp(120), Window.width - dp(24))
                w.width = ancho
                w.text_size = (ancho - dp(28), None)
                w.height = min((w.texture_size[1] if w.texture_size else 0) + dp(24), Window.height * 0.45)
                w.x, w.top = dp(12), Window.height - dp(62)

            def tocar(inst, toque):
                if boc["visible"] and inst.collide_point(*toque.pos):
                    ocultar_bocadillo()                    # tocarlo lo cierra
                    return True
                return False
            w.bind(texture_size=colocar, text=colocar, on_touch_down=tocar)
            try:
                Window.bind(size=colocar)
            except Exception:
                pass
            boc["w"], boc["colocar"] = w, colocar
        w.text = texto[-700:]
        if not boc["visible"]:
            boc["visible"] = True
            Window.add_widget(w)
        boc["colocar"]()
        boc["hasta"] = time.monotonic() + (segundos or max(4.0, len(texto) / 13.0))

        def vigilar(_dt):                                  # se va cuando ha terminado de hablar y de pensar
            if time.monotonic() > boc["hasta"] and not st["ocupado"] and not voz.hablando():
                ocultar_bocadillo()
        if boc["reloj"] is None:
            boc["reloj"] = Clock.schedule_interval(vigilar, 0.8)

    def decir(texto, hablar=True, ya_escrito=False):
        """Kira 'habla': el texto se escribe poco a poco y, si hay voz y está activada, se lee en voz alta.
        ya_escrito=True: el texto ya fue apareciendo mientras pensaba (no se vuelve a escribir)."""
        if st["reloj_txt"] is not None:
            st["reloj_txt"].cancel()
            st["reloj_txt"] = None
        bocadillo(texto)
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
        if texto and contestar_pregunta(texto):         # «sí» / «déjalo» a «¿sigo con lo que dejé a medias?»
            campo.text = ""
            return
        if texto and esk.orden_control(texto):         # «para», «cancela» (escrito): vale aunque esté ocupada
            campo.text = ""
            control_por_voz(esk.orden_control(texto))
            return
        if not texto:
            return
        if gestor.ocupado() or st["ocupado"]:
            orden_n = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", texto, flags=re.I) or texto
            campo.text = ""
            if moverse(orden_n):                        # moverse por la app no interrumpe nada
                return
            if re.match(r"^(?:qu[eé] est[aá]s haciendo|en qu[eé] est[aá]s|c[oó]mo vas|por d[oó]nde vas|"
                        r"cu[aá]nto te queda|qu[eé] haces)\b", esk._norm(orden_n)):
                decir((gestor.resumen() or "Estoy terminando de contestarte") + ".")   # informa sin parar nada
                return
            # TU ORDEN VA PRIMERO: Kira para lo que hace, te dice qué era, te atiende y luego decides tú si sigue
            if gestor.ocupado():
                resumen = gestor.resumen()
                t = gestor.interrumpir()
                st["preguntado"] = False
                decir(f"Paro: {resumen[len('Estoy con '):] if resumen.startswith('Estoy con ') else resumen}. "
                      "Te atiendo, y luego me dices si sigo con ello.")
            else:
                st["charla_cortada"] = True             # una respuesta a medias: se corta y no se dice
                callar_ya()
            if callable(getattr(core, "cancelar", None)):
                core.cancelar()
            gestor.cola.insert(0, orden_n)              # en cuanto pare (un segundo), lo tuyo
            return
        campo.text = ""
        if callable(getattr(core, "nueva_tarea", None)):
            core.nueva_tarea()                          # algo nuevo: un «cancela» de antes ya no cuenta
        import diseno_kira as dk_
        import programar_kira as pk_
        orden = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", texto, flags=re.I) or texto  # escrito «Kira, …»
        if callable(getattr(core, "es_orden_de_modulo", None)) and core.es_orden_de_modulo(orden):
            hablar_con_kira(orden)                      # una MEJORA INSTALADA: se usa ella (nada la intercepta)
            return
        if ik.pedido_con_codigo(orden):                 # «implementa este código (en las mejoras)»
            mejora_con_codigo(orden)
            return
        if re.match(r"^(?:p[ií]nta(?:me)?|dib[uú]ja(?:me)?|haz(?:me)?|cr[eé]a(?:me)?|rehaz)\s+(?:los\s+|las\s+)?"
                    r"(?:dibujos|gr[aá]ficos|personajes|sprites|im[aá]genes)\s+(?:del|de\s+este|de\s+mi|para\s+el)\s+"
                    r"(?:juego|programa)\b", orden, re.I):
            dibujos_del_juego()                         # «pinta los dibujos del juego» (el que está en el editor)
            return
        import librerias_kira as lbk_
        o_lib = lbk_.interpretar(orden)
        if o_lib is not None:                           # «instala la librería X»: la decides tú (dos toques)
            libreria_por_voz(o_lib, orden)
            return
        import pdf_kira as pdk_
        o_pdf = pdk_.interpretar(orden)
        if o_pdf is not None:                           # biblioteca de PDF: descargar de un enlace, leer, preguntar…
            pdf_por_voz(o_pdf, orden)
            return
        import cierres_kira as ck_
        if ck_.pide_seguir(orden) and retomar_aparcada():   # «sigue con lo que hacías»: la que dejó por ti
            return
        if ck_.pide_seguir(orden):                      # «sigue con lo que hacías»: lo que cortó un cierre
            trab = getattr(core, "trabajo", None)
            t = trab.retomar() if trab is not None else None
            if t is None:
                decir("No tengo nada a medias. ¿Qué quieres que haga?")
            elif t["tipo"] == "programa":
                programa_por_voz(t["pedido"])
            elif t["tipo"] == "experimento":
                experimento_por_voz(t["pedido"])
            elif t["tipo"] == "juego_realista":
                juego_realista_por_voz(t["pedido"])
            else:
                mejora_por_voz(re.sub(r"^Mejora para [^:]{1,60}:\s*", "", t["pedido"]))
            return
        import web_juegos_kira as wj_
        que_app = wj_.pedido_app(orden)
        if que_app is not None:                         # «conviértelo en una app», «pon el juego en el inicio»…
            app_por_voz(que_app)
            return
        import experimentos_kira as ex_
        exp = ex_.pedido_experimento(orden)
        if exp is not None:                             # «experimenta con…», «inventa un algoritmo nuevo…»
            experimento_por_voz(exp)
            return
        prog = pk_.pedido_programa(orden)
        if prog is not None:                            # «escríbeme un programa que…», «hazme un juego de…»: al editor
            import juego_realista_kira as jr_
            import generos_juegos_kira as gj_
            resto = jr_.es_realista(prog)
            if resto is None and prog.startswith("juego ") and gj_.genero_de(prog) != "esquivar":
                resto = re.sub(r"^juego\s+(?:de\s+|del\s+)?", "", prog)   # «juego de carreras…»: con plantilla
            if resto is not None:                       # «hazme un juego realista de…»: pintor + programa
                juego_realista_por_voz(resto or "un explorador")
            else:
                programa_por_voz(prog)
            return
        import pintor_kira as pin_
        import internet_kira as net_
        img = pin_.pedido_imagen(orden, siempre_dibuja=bool(core.pintor.instalados()))
        if img is not None:                             # «pinta…», «hazme una foto de…»: al pintor
            imagen_por_voz(img)
            return
        red = net_.interpretar(orden)
        if red is not None:                             # «busca en internet…», «lee el 2», «estudia en internet…»
            internet_por_voz(red, orden)
            return
        dis = dk_.pedido_diseno(orden)
        if dis is not None:                             # «diséñame una web para…»: al ordenador de diseño
            diseno_por_voz(*dis)
            return
        pedido = ik.pedido_mejora(orden)
        if pedido is not None:                          # «Kira, mejora…» / «aprende a…»: al flujo de mejoras
            mejora_por_voz(pedido, espera=ik.pide_esperar(orden))
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
        m_exp = re.match(r"^abre el experimento\s+(\d+)(?:\s+(?:hip[oó]tesis|la)\s+(\d+))?", bajo)
        if m_exp:                                       # uno del cuaderno de experimentos, al editor
            import experimentos_kira as ex_
            import os as os_
            cuad = getattr(core, "cuaderno", None) or ex_.Cuaderno(os_.path.join(core.dir, "experimentos.json"))
            r = cuad.codigo(int(m_exp.group(1)), int(m_exp.group(2)) if m_exp.group(2) else None)
            if r is None:
                decir("No tengo ese experimento (o esa hipótesis no funcionó). Di «mis experimentos».")
            else:
                decir(f"Te abro el experimento {m_exp.group(1)} en el editor.")
                codigo_ui["cargar_en_editor"](r[1], r[0], "Código EXPERIMENTAL de Kira (probado en modo seguro): "
                                                          "pulsa «Ejecutar» o «Jugar».")
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
        hablar_con_kira(texto)

    def hablar_con_kira(texto):
        """La charla de siempre (y las órdenes del núcleo y de las mejoras instaladas): la respuesta va apareciendo."""
        st["ocupado"] = True
        if st["reloj_txt"] is not None:
            st["reloj_txt"].cancel()
            st["reloj_txt"] = None
        burbuja.text = "…"
        modelo.poner_estado("pensando")
        escucha.olvidar()

        flujo = {"hubo": False}
        en_vivo = ik.HablaEnVivo(voz, activa=ajustes.voz_hablar)   # dice cada frase en cuanto está completa
        st["en_vivo"] = en_vivo                          # para poder callarla con «para»

        def mostrar_trozo(parcial):                      # la respuesta va apareciendo mientras Kira piensa
            if not st["ocupado"]:
                return
            flujo["hubo"] = True
            burbuja.text = parcial + " …"
            bocadillo(parcial + " …")
            if modelo.estado != "hablando":
                modelo.poner_estado("hablando")
            en_vivo.trozo(parcial)

        def trozo(parcial):                              # llega desde otro hilo: se pinta en el de la pantalla
            Clock.schedule_once(lambda _dt, p_=parcial: mostrar_trozo(p_), 0)

        def terminado(r):
            st["ocupado"] = False
            if st.pop("charla_cortada", False):        # la cortaste con otra orden: no se dice
                return
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

    def mejora_por_voz(pedido, espera=False):
        quien = getattr(core, "cerebro_para_codigo", lambda: None)()
        if quien is None:
            decir("Para programar mejoras necesito un cerebro: el mío (Menú › «Cerebro y oído») o la clave de Claude "
                  "(«config clave: …»). Cuando lo tenga, pídemelo otra vez.")
            return
        equipo = en_equipo()
        tarea_empieza("mejora", pedido, lambda p_=pedido: mejora_por_voz(p_), {"pedido": pedido})
        decir((f"Entendido: «{pedido}». Como me pides, primero escribo el código y lo pruebo en mi laboratorio del móvil"
               if espera else f"Vale, me pongo a programar: {pedido}. Lo pruebo aquí en el móvil")
              + (" (y en el ordenador, que está conectado)" if getattr(ctl.pasarela, "url", "") else "")
              + (". Lo haremos en equipo Claude y yo hasta ponernos de acuerdo" if equipo else "")
              + ". Para instalarlo tendrás que tocar Aplicar dos veces.")

        def al_terminar(r):
            t = tarea_fin(bool(r.get("aprobable")))
            if t is not None and t.interrumpida:
                return
            if r.get("aprobable"):
                voz.hablar(("Claude y yo estamos de acuerdo. " if r.get("acuerdo") else
                            "Claude y yo no nos hemos puesto de acuerdo: mira lo que dice cada uno. "
                            if r.get("acuerdo") is False else "")
                           + "La mejora ha pasado las pruebas. Revísala y toca Aplicar dos veces si te parece bien.")
            else:
                voz.hablar("No he conseguido una mejora que pase las pruebas. Te dejo el detalle en la terminal.")
        Clock.schedule_once(lambda _dt: hacker["pedir_mejora"](pedido, al_terminar), 2.5)

    def mejora_con_codigo(orden):
        """La mejora sale del código que tienes en el editor (o de lo último leído: captura o internet). Si ya es un
        módulo de Kira se prueba tal cual; si es un programa, Kira lo convierte. Instalar: tus dos toques."""
        codigo, nombre = codigo_ui["codigo_actual"]() if "codigo_actual" in codigo_ui else ("", "")
        origen = "el editor"
        if len(str(codigo or "").strip()) < 10:
            lector = getattr(core, "lector", None)
            codigo, nombre, origen = (getattr(lector, "ultimo", "") or ""), "", "lo último que leí"
        if len(str(codigo or "").strip()) < 10:
            decir("No veo ningún código: ábrelo en el editor (o léelo de una captura o de internet) y pídemelo otra vez.")
            return
        modulo = "def registrar" in codigo
        if not modulo and getattr(core, "cerebro_para_codigo", lambda: None)() is None:
            decir("Ese código es un programa normal: para convertirlo en mejora necesito un cerebro (el mío o la clave "
                  "de Claude). Si ya fuera un módulo de Kira (con registrar()), lo probaría tal cual.")
            return
        tarea_empieza("mejora", "implementar el código de " + origen, lambda o_=orden: mejora_con_codigo(o_))
        decir(f"Vale: cojo el código de {origen} y lo pruebo en mi laboratorio"
              + (" tal cual" if modulo else " después de convertirlo en una mejora")
              + ". Para instalarlo tendrás que tocar Aplicar dos veces.")

        def al_terminar(r):
            t = tarea_fin(bool(r.get("aprobable")))
            if t is not None and t.interrumpida:
                return
            voz.hablar("Ha pasado las pruebas. Revísalo y toca Aplicar dos veces si te parece bien." if r.get("aprobable")
                       else "No ha pasado las pruebas. Te dejo el motivo en la terminal.")
        Clock.schedule_once(lambda _dt: hacker["pedir_mejora"](
            ("Implementar el código de " + origen + (f" «{nombre}»" if nombre else "")), al_terminar,
            codigo=codigo), 1.5)

    def avance(texto, fraccion=None):                   # progreso largo (llega desde un hilo): sin hablar
        gestor.progreso(fraccion, texto)               # la barra de la tarea (tiempo y % que queda)

        def poner(_dt):
            burbuja.text = texto
            bocadillo(texto)
        Clock.schedule_once(poner, 0)

    # ---------- UNA tarea larga cada vez, con su barra (tiempo y %) ----------
    def tarea_empieza(tipo, descripcion, relanzar, datos=None):
        gestor.empezar(tipo, descripcion, relanzar, datos)
        pintar_barra()

    def tarea_fin(ok=True):
        """La tarea terminó. Devuelve la Tarea: si estaba aparcada (la dejaste por otra cosa), no se anuncia."""
        t = gestor.terminar(ok)
        pintar_barra()
        return t

    def pintar_barra(*_):
        texto = gestor.texto_barra()
        w = barra["w"]
        if not texto:
            if w is not None and barra["visible"]:
                barra["visible"] = False
                try:
                    Window.remove_widget(w)
                except Exception:
                    pass
            return
        if w is None:
            w = Label(text="", size_hint=(None, None), color=(1, 1, 1, 1), font_size=tam(12.5), halign="left",
                      valign="middle", **FUENTE)
            est.fondo_redondeado(w, (0.10, 0.12, 0.22, 0.93), radio=12)

            def colocar(*_):
                w.width = max(dp(120), Window.width - dp(16))
                w.height = dp(46)
                w.text_size = (w.width - dp(20), w.height)
                w.x, w.top = dp(8), Window.height - dp(4)
            try:
                Window.bind(size=colocar)
            except Exception:
                pass
            barra["w"], barra["colocar"] = w, colocar
        e = gestor.estimacion() or (0.0, 0.0)
        llenos = int(round(e[0] * 16))
        w.text = "▰" * llenos + "▱" * (16 - llenos) + "  " + texto
        if not barra["visible"]:
            barra["visible"] = True
            Window.add_widget(w)
        barra["colocar"]()

    def libre_para_mas(_dt=None):
        """Cuando Kira queda libre: primero lo que le pediste; después te PREGUNTA si sigue con lo que dejó a medias
        (decides tú)."""
        if gestor.ocupado() or st["ocupado"] or voz.hablando() or st.get("pregunta"):
            return
        if gestor.cola:
            enviar(gestor.cola.pop(0))
            return
        if gestor.aparcadas and not st.get("preguntado"):
            t = gestor.aparcadas[-1]
            st["pregunta"], st["preguntado"] = t, True
            escucha.atender(30)                         # la respuesta vale sin decir «Kira»
            decir(f"Ya he terminado lo tuyo. Había dejado a medias {tk_.NOMBRES.get(t.tipo, t.tipo)}: "
                  f"«{t.descripcion[:60]}». ¿Sigo con ello? Dime «sí» o «déjalo».")

    def retomar_aparcada():
        """«sigue con lo que hacías»: la última tarea que dejó a medias. True si había alguna."""
        if not gestor.aparcadas:
            return False
        t = gestor.aparcadas.pop()
        gestor._guardar()
        st["preguntado"] = False
        decir(f"Vuelvo con {tk_.NOMBRES.get(t.tipo, t.tipo)}: «{t.descripcion[:60]}».")
        if callable(t.relanzar):
            Clock.schedule_once(lambda _dt, f_=t.relanzar: f_(), 1.2)
        return True
    Clock.schedule_interval(lambda _dt: (pintar_barra(), libre_para_mas()), 1.0)

    def contestar_pregunta(texto):
        """Tu respuesta a «¿sigo con lo que dejé a medias?»: «sí / sigue» la retoma, «no / déjalo» la olvida.
        Si dices otra cosa, la tarea se queda guardada («sigue con lo que hacías» la retoma luego). True si respondía."""
        t = st.get("pregunta")
        if t is None:
            return False
        b = esk._norm(texto).strip(" .!¡?¿,")
        b = re.sub(r"^(?:kira\s*,?\s*)", "", b)
        si = re.match(r"^(?:si|vale|venga|claro|dale|ok|de acuerdo|sigue|continua|retomalo|retoma|termina(?:lo)?|hazlo)\b", b)
        no = re.match(r"^(?:no|dejalo|deja(?:lo)? estar|olvidalo|olvida(?:lo)?|ya no|no hace falta|cancela(?:lo)?|"
                      r"borra(?:lo)?|para)\b", b)
        st["pregunta"] = None
        if si:
            retomar_aparcada()
            return True
        if no:
            if gestor.aparcadas and gestor.aparcadas[-1] is t:
                gestor.aparcadas.pop()
                gestor._guardar()
            st["preguntado"] = False
            decir(f"Vale, dejo «{t.descripcion[:60]}».")
            return True
        st["preguntado"] = False                        # otra orden: se atiende y, al acabar, te vuelve a preguntar
        return False

    def juego_realista_por_voz(pedido):
        """«Kira, hazme un juego realista de un caballero que esquiva dragones»: piensa el juego, el pintor dibuja el
        escenario y los personajes (estilo real, recortados) y lo deja en el editor ya jugando."""
        tarea_empieza("juego_realista", pedido, lambda p_=pedido: juego_realista_por_voz(p_), {"pedido": pedido})
        modelo.poner_estado("pensando")
        import generos_juegos_kira as gj_
        g_ = gj_.genero_de(pedido)
        decir(f"¡Vamos allá! Un juego de {gj_.NOMBRES[g_]}: {pedido}. " + (
            "Lo retro va con formas, sin dibujos: enseguida está." if g_ == "retro" else
            "Diseño el juego, pinto los personajes en estilo realista y lo programo. Pintar los dibujos puede tardar "
            "unos minutos."))
        ultimo = {"t": 0.0}

        def prog(f, texto):
            gestor.progreso(f, texto)
            if time.monotonic() - ultimo["t"] > 0.7:
                ultimo["t"] = time.monotonic()
                avance(texto, f)

        def fin(r):
            t = tarea_fin(not isinstance(r, Exception))
            if t is not None and t.interrumpida:
                return
            if isinstance(r, Exception):
                decir(f"[x] No pude crear el juego: {r}")
                return
            aviso = ("Juego realista hecho por Kira. Los dibujos están en la carpeta «" + r["nombre"] + "». "
                     + (r["aviso"] + " " if r["aviso"] else "") + "Pulsa «Jugar» para jugarlo otra vez.")
            codigo_ui["cargar_en_editor"](r["codigo"], r["nombre"], aviso)
            codigo_ui["empezar_juego"](r["codigo"], volver="editor_codigo")
            import generos_juegos_kira as gj_
            como = gj_.instrucciones(r["plan"])
            decir("¡Listo! " + ("" if not r["aviso"] else r["aviso"] + " ")
                  + como + " El programa está en el editor por si quieres cambiarlo.")
        en_hilo(lambda: core.crear_juego_realista(pedido, al_progreso=prog), fin)

    def app_por_voz(que="app"):
        """Tu juego como app: «inicio» = icono en la pantalla de inicio (abre Kira en ese juego); «web» = página de un
        solo archivo en Descargas/Kira que se abre en el navegador (sin internet); «app» = las dos cosas."""
        import web_juegos_kira as wj_
        import juegos_kira as jk_
        import sprites_kira as spk_
        cod = codigo_ui["juego_actual"]() if "juego_actual" in codigo_ui else ""
        if not cod or "Juego" not in cod:
            cod = (codigo_ui["codigo_actual"]() if "codigo_actual" in codigo_ui else ("", ""))[0]
        if not cod or "Juego" not in cod:
            decir("Primero juega (o abre en el editor) el juego que quieres convertir, y luego dime «conviértelo en "
                  "una app».")
            return
        juego, error = jk_.cargar(cod)
        if error:
            decir(f"[x] Ese juego no arranca, así que no lo convierto todavía: {error}")
            return
        titulo = getattr(juego, "titulo", "") or wj_.titulo_de(cod)
        if que == "apk":
            apk_por_voz(cod, titulo)
            return
        partes = []

        def al_inicio():
            nombre = "app_" + (ej_nombre(titulo) or "juego")
            try:
                codigo_ui["programas"].guardar(nombre, cod)
            except (ValueError, OSError) as e:
                return f"no he podido guardarlo ({e})"
            if platform != "android":
                return f"guardado como «{nombre}» (el icono solo se puede poner en el móvil)"
            try:
                from jnius import autoclass
                act = autoclass("org.kivy.android.PythonActivity").mActivity
                paleta = [0xFF2563EB, 0xFFDB2777, 0xFF059669, 0xFFD97706, 0xFF7C3AED, 0xFFDC2626, 0xFF0891B2]
                col = paleta[sum(map(ord, titulo)) % len(paleta)]
                r = str(autoclass("org.kira.servicio.AppsKira").ponerEnInicio(act, nombre, titulo, col - 2 ** 32))
            except Exception as e:
                return f"no he podido poner el icono ({type(e).__name__})"
            return {"ok": "te pido permiso para poner el icono en la pantalla de inicio: acéptalo",
                    "viejo": "tu Android es anterior al 8 y no deja poner el icono desde la app",
                    }.get(r, "tu pantalla de inicio no deja poner iconos desde las apps")

        def web():
            carpeta, _d = spk_.dibujos_de(cod)
            dibujos = wj_.dibujos_png(os.path.dirname(spk_.ruta(carpeta or "juego", "x"))) if carpeta else {}
            pagina = wj_.html_juego(cod, dibujos, titulo)
            dest = os.path.join(core.dir, "web")
            os.makedirs(dest, exist_ok=True)
            ruta = os.path.join(dest, wj_.nombre_archivo(titulo))
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(pagina)
            return ruta

        def tras_web(r):
            if isinstance(r, Exception):
                partes.append(f"la versión web no ha salido: {r}")
            elif platform == "android":
                try:
                    from jnius import autoclass
                    act = autoclass("org.kivy.android.PythonActivity").mActivity
                    hecho = str(autoclass("org.kira.servicio.AppsKira").abrirHtml(act, r, os.path.basename(r)))
                except Exception:
                    hecho = ""
                partes.append({"abierto": f"la página web está en Descargas/Kira/{os.path.basename(r)} y te la abro "
                                          "en el navegador (funciona sin internet y la puedes pasar a quien quieras)",
                               "guardado": f"la página web está en Descargas/Kira/{os.path.basename(r)}: ábrela desde "
                                           "Archivos con el navegador"}.get(hecho, "no he podido guardar la página "
                                                                                   "web en Descargas"))
            else:
                partes.append(f"la página web está en {r}")
            terminar()

        def terminar():
            decir(f"«{titulo}» como app: " + "; ".join(partes) + ".")

        if que in ("inicio", "app"):
            partes.append(al_inicio())
        if que in ("web", "app"):
            decir(f"Preparo «{titulo}» como página web…", hablar=False)
            en_hilo(web, tras_web)
        else:
            terminar()

    def apk_por_voz(cod, titulo):
        """La app DE VERDAD (APK) del juego: se compila en TU GitHub (repositorio kira-juegos) y baja a Descargas."""
        import apk_juegos_kira as apk_
        import sprites_kira as spk_
        import web_juegos_kira as wj_
        token = core.clave_github() if hasattr(core, "clave_github") else ""
        if not token:
            decir("Para la app de verdad necesito tu clave de GitHub (solo una vez). En github.com: tu foto › Settings › "
                  "Developer settings › Personal access tokens › Tokens (classic) › Generate new token (classic). "
                  "Marca «public_repo» y «workflow», ponle caducidad y cópiala. Luego escríbeme «config github: » y "
                  "la clave, y repíteme «conviértelo en una app de verdad».")
            return
        tarea_empieza("apk", f"app de «{titulo}»", lambda: apk_por_voz(cod, titulo), {"titulo": titulo})
        decir(f"Hago la app de «{titulo}» en tu GitHub. La primera vez tarda unos 30 minutos (luego menos); te voy "
              "contando y, al terminar, te la dejo en Descargas.")

        def trabajo():
            gh = apk_.GitHub(token)
            carpeta, _d = spk_.dibujos_de(cod)
            dibujos = wj_.dibujos_png(os.path.dirname(spk_.ruta(carpeta or "juego", "x"))) if carpeta else {}
            reg = apk_.Registro(os.path.join(core.dir, "apk_juegos.json"))
            r = apk_.compilar(gh, cod, titulo, reg, dibujos, progreso=lambda f, t: avance(t, f),
                              cancelado=getattr(core, "cancelado", None))
            import descargas_kira as dsk
            dest = os.path.join(core.dir, "apk", r["id"] + ".apk")
            for viejo in (dest, dest + ".parte"):
                if os.path.exists(viejo):
                    os.remove(viejo)
            avance("Bajo el APK…", 0.99)
            dsk.bajar(r["url_apk"], dest, None, "el APK")
            r["ruta"] = dest
            r["descargas"] = core.exportar_a_descargas(dest, r["id"] + ".apk", "application/vnd.android.package-archive")
            return r

        def fin(r):
            t = tarea_fin(not isinstance(r, Exception))
            if t is not None and t.interrumpida:
                return
            if isinstance(r, Exception):
                decir(f"[x] {r}")
                return
            ok, msg = r["descargas"]
            decir(f"¡Lista la app de «{titulo}» (versión {r['n']})! "
                  + ("Está en Descargas › Kira como «" + r["id"] + ".apk»: ábrela desde Archivos y pulsa Instalar."
                     if ok else f"No la he podido poner en Descargas ({msg}); bájala de aquí: {r['url_apk']}"))
        en_hilo(trabajo, fin)

    def ej_nombre(texto):
        import ejecutor_kira as ej__
        return ej__.nombre_valido(texto)

    def dibujos_del_juego():
        """Pinta (o repinta) los dibujos que pide el juego del editor (atributos «sprites» y «dibujos»)."""
        import sprites_kira as spk_
        cod, _nombre = codigo_ui["codigo_actual"]() if "codigo_actual" in codigo_ui else ("", "")
        carpeta, dibujos = spk_.dibujos_de(cod or "")
        if not dibujos:
            decir("El juego del editor no dice qué dibujos necesita: ponle «sprites = \"nombre\"» y un diccionario "
                  "«dibujos» con lo que hay que pintar (o pídeme «hazme un juego realista de…»).")
            return
        carpeta = carpeta or "juego"
        tarea_empieza("imagen", f"pintar {len(dibujos)} dibujo(s) del juego", dibujos_del_juego)
        decir(f"Pinto {len(dibujos)} dibujo(s) del juego en estilo realista. Tardo un poco.")
        ultimo = {"t": 0.0}

        def prog(f, texto):
            gestor.progreso(f, texto)
            if time.monotonic() - ultimo["t"] > 0.7:
                ultimo["t"] = time.monotonic()
                avance(texto, f)

        def fin(r):
            t = tarea_fin(not isinstance(r, Exception))
            if t is not None and t.interrumpida:
                return
            if isinstance(r, Exception):
                decir(f"[x] {r}")
            else:
                decir(f"Hecho: {len(r)} dibujo(s) listos. Pulsa «Jugar» en el editor para verlos.")
        en_hilo(lambda: core.pintar_dibujos(carpeta, dibujos, prog, rehacer=True), fin)

    def programa_por_voz(pedido):
        """Kira escribe el programa (o juego), lo prueba en modo seguro, lo acuerda con Claude y lo deja en el editor.
        No se instala nada: tú pulsas «Ejecutar» o «Jugar»."""
        if getattr(core, "cerebro_para_codigo", lambda: None)() is None:
            decir("Para escribir programas necesito un cerebro: el mío (Menú › «Cerebro y oído») o la clave de Claude.")
            return
        equipo = en_equipo()
        tarea_empieza("programa", pedido, lambda p_=pedido: programa_por_voz(p_), {"pedido": pedido})
        modelo.poner_estado("pensando")
        decir(f"Vale, te escribo un {pedido}. Lo pruebo en modo seguro"
              + (" y lo repaso con Claude" if equipo else "") + " antes de enseñártelo.")

        def terminado(r):
            t = tarea_fin(not isinstance(r, Exception) and bool(r.get("ok")))
            if t is not None and t.interrumpida:
                return
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
            aviso += " Si quieres que sea parte de Kira (una orden nueva), dime «implementa este código»."
            codigo_ui["cargar_en_editor"](r["codigo"], r["nombre"] or "", aviso)
            decir(("Listo, y Claude y yo estamos de acuerdo. " if r.get("acuerdo") else "Listo. ")
                  + f"Te lo dejo en el editor: pulsa {'Jugar' if juego else 'Ejecutar'}.")
        en_hilo(lambda: core.programa_acordado(pedido), terminado)

    def experimento_por_voz(tema):
        """«Kira, experimenta con…»: plantea 2-3 hipótesis, escribe y prueba cada una en modo seguro, se queda con
        la mejor (acordada con Claude si están los dos), lo apunta en su cuaderno y lo deja en el editor."""
        if getattr(core, "cerebro_para_codigo", lambda: None)() is None:
            decir("Para inventar código necesito un cerebro: el mío (Menú › «Cerebro y oído») o la clave de Claude.")
            return
        equipo = en_equipo()
        tarea_empieza("experimento", tema, lambda t_=tema: experimento_por_voz(t_), {"pedido": tema})
        modelo.poner_estado("pensando")
        decir(f"¡Me encanta! Voy a experimentar con {tema}: pruebo varias ideas en modo seguro, me quedo con la "
              "mejor" + (" y la repaso con Claude" if equipo else "") + ". Puede tardar un rato.")

        def terminado(r):
            t = tarea_fin(not isinstance(r, Exception) and bool(r.get("ok")))
            if t is not None and t.interrumpida:
                return
            if isinstance(r, Exception):
                decir(f"[x] No pude experimentar: {r}", hablar=False)
                return
            if not r.get("ok"):
                decir("Ninguna de mis ideas ha funcionado esta vez; lo he apuntado para aprender. "
                      "Di «mis experimentos» para ver qué pasó.")
                burbuja.text = r["texto"]
                return
            juego = r.get("juego")
            aviso = (f"Código EXPERIMENTAL de Kira (experimento {r.get('n') or ''}), probado en modo seguro. "
                     f"Pulsa «{'Jugar' if juego else 'Ejecutar'}». Si te gusta y quieres que sea parte de mí, "
                     "dime «implementa este código».\n\n" + r["texto"])
            codigo_ui["cargar_en_editor"](r["codigo"], r["nombre"], aviso)
            buenas = sum(1 for x in r["resultados"] if x["ok"])
            decir(f"Listo: {buenas} de {len(r['resultados'])} ideas funcionan" +
                  (" y Claude y yo estamos de acuerdo con la mejor" if r.get("acuerdo") else "") +
                  f". Te dejo la mejor en el editor: pulsa {'Jugar' if juego else 'Ejecutar'}.")
        en_hilo(lambda: core.experimentar(tema, al_progreso=lambda f, t: avance(t, f)), terminado)

    def diseno_por_voz(tipo, descripcion):
        nombres = {"web": "la página", "app": "la maqueta", "clip": "el videoclip"}
        decir(f"Vale, diseño {nombres.get(tipo, 'eso')}: {descripcion}.", hablar=True)

        def hecho(origen):
            voz.hablar({"acuerdo": "Hecho, y repasado con Claude. Revísalo y guárdalo si te gusta.",
                        "ia": "Hecho. Revísalo y guárdalo si te gusta."}.get(
                origen, "Lo he hecho con mis plantillas. Revísalo y guárdalo si te gusta."))
        Clock.schedule_once(lambda _dt: diseno["disenar"](tipo, descripcion, hecho), 1.2)

    def imagen_por_voz(descripcion):
        """«Kira, pinta un faro al atardecer»: va al pintor y lo pinta (con barra de progreso)."""
        if not core.pintor.instalados():
            ir("pintor")
            decir("Para pintar necesito un pincel: descarga uno aquí una vez (el rápido pesa 683 MB). Luego pinto sin "
                  "internet.")
            return
        ir("pintor")
        tarea_empieza("imagen", descripcion, lambda d_=descripcion: imagen_por_voz(d_))
        decir(f"Vale, pinto: {descripcion}. Te enseño cómo se va formando.")

        def hecho(r):
            t = tarea_fin(r is not None)
            if t is not None and t.interrumpida:
                return
            if r is None:
                voz.hablar("No he podido pintarla. Te dejo el motivo en la pantalla.")
            else:
                voz.hablar(f"Ya está, en {r['segundos']:.0f} segundos. Si te gusta, toca «A la galería».")
        def pintar_ya(_dt):
            if pintor_ui["pintar"](descripcion, al_terminar=hecho) is False:
                tarea_fin(False)                        # no llegó a empezar
        Clock.schedule_once(pintar_ya, 0.3)

    def internet_por_voz(p_red, orden):
        """«Kira, busca en internet…», «lee el 2», «resume el 2», «guarda el 2», «estudia en internet…»."""
        acc = p_red["accion"]
        if acc == "buscar":
            ir("internet")
            decir(f"Busco «{p_red['consulta']}» en internet.")

            def hecho(r):
                if isinstance(r, Exception):
                    voz.hablar(f"No he podido buscar: {r}")
                elif r:
                    voz.hablar(f"He encontrado {len(r)} resultados. El primero es {r[0]['titulo']}, de "
                               f"{r[0]['fuente']}. Toca uno o dime «lee el uno».")
            internet_ui["buscar"](p_red["consulta"], p_red["tipo"], al_terminar=hecho)
            return
        if acc == "estudiar":
            ir("internet")
            decir(f"Me pongo a estudiar «{p_red['consulta']}» en internet: leo las mejores páginas y lo guardo en mi baúl.")
            internet_ui["estudiar"](p_red["consulta"], al_terminar=lambda r: voz.hablar(
                str(r).replace("[OK] ", "").replace("[x] ", "") if not isinstance(r, Exception) else f"No he podido: {r}"))
            return
        if acc == "leer" and p_red.get("n"):
            ir("internet")
            if internet_ui["leer"](p_red["n"], al_terminar=lambda pag: voz.hablar(
                    f"Te lo enseño: {pag['titulo']}." if isinstance(pag, dict) else f"No he podido leerlo: {pag}")):
                return
        if acc == "editor":
            def abrir(pag):
                cod = core.internet.codigo_de(pag) if isinstance(pag, dict) else ""
                if cod:
                    codigo_ui["cargar_en_editor"](cod, "", f"Código de {pag['url']}: revísalo y pulsa «Ejecutar» "
                                                           "(modo seguro). Lo de internet nunca se ejecuta solo.")
                    decir("Te dejo el código en el editor.")
                else:
                    decir("[x] " + (str(pag) if isinstance(pag, Exception) else "Esa página no tiene código."))
            en_hilo(lambda: core.leer_resultado(p_red["n"]), abrir)
            return
        # resumir / guardar / navegador / leer una dirección: lo hace el núcleo y Kira lo dice
        st["ocupado"] = True
        modelo.poner_estado("pensando")
        burbuja.text = "…"

        def fin(r):
            st["ocupado"] = False
            decir(f"[x] {r}" if isinstance(r, Exception) else str(r))
        en_hilo(lambda: core.procesar_orden(orden), fin)

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

    def callar_ya():
        """«Para», «cállate»: deja de hablar YA (y lo que faltaba de la respuesta ya no se dice)."""
        try:
            voz.callar()
        except Exception:
            pass
        ev = st.get("en_vivo")
        if ev is not None:
            ev.callar()

    def control_por_voz(que):
        """'callar' o 'cancelar', oído aunque Kira esté hablando o trabajando. Desde cualquier hilo."""
        callar_ya()
        if que == "cancelar":
            r = core.cancelar() if callable(getattr(core, "cancelar", None)) else "Vale."
            Clock.schedule_once(lambda _dt: decir(r, hablar=True), 0.25)

    def al_frase_oido(texto):                          # llega desde el hilo de Java: se pasa al de la pantalla
        control = esk.orden_control(texto) if st.get("pregunta") is None else None   # «déjalo» puede ser la respuesta
        if control:                                    # «para», «cancela»: valen SIEMPRE, también mientras habla
            control_por_voz(control)
            return
        if voz.hablando() or time.monotonic() < st.get("hablo_hasta", 0.0):
            return                                     # mientras habla, lo que oye es su propia voz: no lo atiende
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
                if callable(getattr(core, "nueva_tarea", None)):
                    core.nueva_tarea()
                r, _via = conv.preguntar(orden)
                if not core.cancelado() if callable(getattr(core, "cancelado", None)) else True:
                    voz.hablar(r.replace("[OK]", "").replace("[x]", "").replace("[i]", "")[:400])
            except Exception as e:
                if type(e).__name__ != "Cancelada":
                    voz.hablar(f"No he podido: {e}")
        elif que == "orden":
            try:
                if callable(getattr(core, "nueva_tarea", None)):
                    core.nueva_tarea()
                r, _via = conv.preguntar(orden)
                if not core.cancelado() if callable(getattr(core, "cancelado", None)) else True:
                    voz.hablar(r.replace("[OK]", "").replace("[x]", "").replace("[i]", "")[:400])
            except Exception as e:
                if type(e).__name__ != "Cancelada":
                    voz.hablar(f"No he podido: {e}")

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
            if voz.hablando():                         # sigue oyendo mientras habla (para «para» y «cancela»)
                st["hablo_hasta"] = time.monotonic() + 1.2     # y un poco después: el eco de su última frase
            oido.pausar(sm.current == "jugar")
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
        # te oye desde cualquier pantalla y contesta AHÍ (bocadillo flotante y voz): ya no te lleva a su botón
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
        if getattr(core, "aviso_android", ""):        # por qué la cerró Android la última vez, y qué hacer
            texto = core.aviso_android + " " + texto
            core.aviso_android = ""
        trab = getattr(core, "trabajo", None)
        if trab is not None and trab.aviso():         # la cerraron a mitad de algo: se puede retomar
            texto += " " + trab.aviso()
        if getattr(ctl, "recuperada", False):
            texto += " Tienes una mejora probada esperando tus dos toques en la Sala Hacker."
        cierre = getattr(core, "aviso_cierre", "")
        if cierre:                                   # la vez anterior se cerró de golpe: lo enseña para arreglarlo
            burbuja.text = ("La última vez me cerré de golpe. Hazle una captura a esto y mándasela a Claude:\n\n"
                            + cierre[-900:] + "\n\n" + texto)
            core.aviso_cierre = ""
        else:
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
    import version_kira
    _, c_cfg = pantalla("config", f"CONFIGURACIÓN · Kira {version_kira.VERSION}")
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
        "juegos_extra": juegos_de_mejoras, "como_app": lambda: app_por_voz("app")})

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
    #  PINTOR (imágenes con su propia IA) e INTERNET (buscar, leer y aprender)
    # =================================================================================
    pintor_ui = montar_pintor(sm, {"boton": boton, "entrada": entrada, "pantalla": pantalla, "en_hilo": en_hilo,
                                   "ganchos": ganchos, "TXT": TXT, "TENUE": TENUE, "GRIS": GRIS, "VERDE": VERDE,
                                   "ROJO": ROJO, "NEON": NEON, "FUENTE": FUENTE, "core": core, "voz": voz,
                                   "ajustes": ajustes})
    internet_ui = montar_internet(sm, {"boton": boton, "entrada": entrada, "texto_largo": texto_largo,
                                       "pantalla": pantalla, "en_hilo": en_hilo, "ganchos": ganchos, "TXT": TXT,
                                       "TENUE": TENUE, "GRIS": GRIS, "VERDE": VERDE, "NEON": NEON, "FUENTE": FUENTE,
                                       "core": core,
                                       "abrir_en_editor": lambda codigo, aviso="": codigo_ui["cargar_en_editor"](codigo, "", aviso)})

    pdf_ui = montar_pdf(sm, {"boton": boton, "entrada": entrada, "texto_largo": texto_largo, "pantalla": pantalla,
                             "en_hilo": en_hilo, "TXT": TXT, "TENUE": TENUE, "GRIS": GRIS, "VERDE": VERDE, "ROJO": ROJO,
                             "FUENTE": FUENTE, "core": core, "avance": lambda t: avance(t)})

    librerias_ui = montar_librerias(sm, {"boton": boton, "entrada": entrada, "texto_largo": texto_largo,
                                         "pantalla": pantalla, "en_hilo": en_hilo, "TXT": TXT, "TENUE": TENUE, "GRIS": GRIS,
                                         "VERDE": VERDE, "ROJO": ROJO, "FUENTE": FUENTE, "core": core,
                                         "avance": lambda t, f=None: avance(t, f), "decir": lambda t: decir(t)})

    def libreria_por_voz(o, orden):
        """«instala la librería X»: la enseña en «Librerías» y espera tus dos toques; «mis librerías»; «quita…»."""
        if o["accion"] == "preparar":
            ir("librerias")
            decir(f"Miro qué es «{o['nombre']}». Si te convence, toca Instalar dos veces.")
            librerias_ui["ver"](o["nombre"], al_terminar=lambda r: decir(
                f"[x] {r}" if isinstance(r, Exception) else
                f"«{r['plan'][0]['nombre_bonito']}»: {r['plan'][0]['resumen'][:120]}. Pesa {r['bytes'] / 1e6:.1f} megas"
                + (f" y necesita {len(r['plan']) - 1} más" if len(r["plan"]) > 1 else "") + ". Toca Instalar dos veces."))
            return
        if o["accion"] == "lista":
            ir("librerias")
        decir(str(core.orden_librerias(orden)).replace("[OK] ", "").replace("[x] ", ""))
        librerias_ui["pintar_lista"]()

    def recibir_compartido(intent=None):
        """Lo que te COMPARTEN con Kira desde otra app (un PDF o un enlace), o un PDF que abres «con Kira»."""
        if platform != "android":
            return
        try:
            from jnius import autoclass
            act = autoclass("org.kivy.android.PythonActivity").mActivity
            intent = intent or act.getIntent()
            juego_id = intent.getStringExtra("kira_juego") if intent is not None else None
            if juego_id:                                       # el icono de un juego en la pantalla de inicio
                act.setIntent(autoclass("android.content.Intent")())
                cod = codigo_ui["programas"].abrir(str(juego_id))
                if cod:
                    codigo_ui["empezar_juego"](cod, volver="juegos")
                else:
                    decir("Ese juego ya no está entre tus programas (¿lo borraste?).")
                return
            s = str(autoclass("org.kira.servicio.ArchivosKira").leerIntent(act, intent, os.path.join(core.dir, "pdf")) or "")
            act.setIntent(autoclass("android.content.Intent")())   # que no se vuelva a recibir al volver a la app
        except Exception:
            return
        partes = s.split("\n")
        if partes[0] == "archivo" and len(partes) >= 2:
            ir("pdf")
            decir("Me guardo el PDF que me has pasado…", hablar=False)

            def fin(r):
                if isinstance(r, Exception):
                    decir(f"[x] No he podido guardar ese PDF: {r}")
                else:
                    pdf_ui["ver_lista"]()
                    decir((f"Ese PDF ya lo tenía: es el número {r['n']}." if r.get("repetido") else
                           f"Guardado como PDF {r['n']}: «{r['nombre']}», {r['paginas']} páginas. "
                           f"Dime «resume el pdf {r['n']}» o pregúntame por él."))
            nombre = partes[2] if len(partes) > 2 else ""
            en_hilo(lambda: core.pdfs.anadir_archivo(partes[1], nombre[:-4] if nombre.lower().endswith(".pdf") else nombre,
                                                     mover=True), fin)
        elif partes[0] == "texto" and len(partes) >= 2:
            import pdf_kira as pdk
            url = pdk.url_de("\n".join(partes[1:]))
            if url:
                ir("pdf")
                decir("Me has pasado un enlace: si es un PDF, me lo guardo.", hablar=False)
                pdf_ui["descargar"](url, al_terminar=lambda r: decir(str(r).replace("[OK] ", "").replace("[x] ", "")))
            else:
                campo.text = "\n".join(partes[1:])[:2000]      # un texto: queda escrito para que le digas qué hacer
                ir("inicio")
    try:
        if platform == "android":
            import android.activity as aa
            aa.bind(on_new_intent=lambda intent: Clock.schedule_once(lambda _dt, i_=intent: recibir_compartido(i_), 0.3))
    except Exception:
        pass
    Clock.schedule_once(lambda _dt: recibir_compartido(), 2.5)

    def pdf_por_voz(o, orden):
        """«descarga este PDF: enlace», «mis pdf», «lee el pdf 2», «resume el pdf 2», «qué dice el pdf 2 sobre…»…"""
        acc = o["accion"]
        if acc == "descargar":
            ir("pdf")
            tarea_empieza("pdf", "descargar " + o["url"][:60], lambda o_=o, t_=orden: pdf_por_voz(o_, t_))
            decir("Me pongo a descargar el PDF.", hablar=True)

            def bajado(r):
                t = tarea_fin(not isinstance(r, Exception) and not str(r).startswith("[x]"))
                if t is not None and t.interrumpida:
                    return
                decir(str(r).replace("[OK] ", "").replace("[x] ", "") if not isinstance(r, Exception) else f"No he podido: {r}")
            pdf_ui["descargar"](o["url"], al_terminar=bajado)
            return
        if acc == "lista":
            ir("pdf")
            decir(core.pdfs.texto_lista())
            return
        if acc in ("leer", "abrir"):
            e = core.pdfs.buscar_doc(o.get("doc"))
            if e is None:
                decir("No tengo ese PDF. Di «mis pdf» para ver la lista.")
                return
            ir("pdf")
            pdf_ui["abrir"](e["n"], o.get("pagina", 1))
            decir(f"Te abro «{e['nombre']}», página {o.get('pagina', 1)}.")
            return
        tarea_empieza("pdf", ("preguntar a tus documentos: " + o.get("pregunta", "")) if acc == "rag" else
                      {"resumir": "resumir", "preguntar": "preguntar a", "estudiar": "estudiar",
                       "buscar": "buscar en"}.get(acc, acc) + " el PDF " + str(o.get("doc") or ""),
                      lambda o_=o, t_=orden: pdf_por_voz(o_, t_))
        modelo.poner_estado("pensando")
        burbuja.text = "…"

        def fin(r):
            t = tarea_fin(not isinstance(r, Exception))
            if t is not None and t.interrumpida:
                return
            decir(f"[x] {r}" if isinstance(r, Exception) else str(r).replace("[OK] ", "").replace("[i] ", ""))
        en_hilo(lambda: core.orden_pdf(orden, al_progreso=lambda f, t: avance(t, f)), fin)

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
        if nombre != "pintor":
            pintor_ui["al_salir"]()
        sm.current = nombre
        if nombre == "inicio":
            ocultar_bocadillo()
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
