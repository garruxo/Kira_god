# -*- coding: utf-8 -*-
"""
pantalla_defensa_kira.py - El JUEGO DE DEFENSA en 1ª persona (look Matrix), dentro de interfaz_kira.py (Kivy).

Pasillo en perspectiva con las paredes hechas de lluvia de letras; cada obstáculo es una AMENAZA (puerta trasera,
fuerza bruta, escaneo, enlace trampa) o tráfico sano. Tú (o Kira sola) decides COMBATIR o DEJAR PASAR. Al tocar una
amenaza sale una PANTALLA ROJA con qué es y CÓMO la combate Kira. Al final, Kira AFINA sus datos (umbrales) para
mejorar y lo apunta en la consola de trabajo.

Solo defensa, datos inventados, sin red real. La "cabeza" (amenazas, decidir, aprender) está en
defensa_juego_kira.py (pura, probada). Esto es solo la pantalla.
"""


def montar_defensa(sm, ctx):
    import random
    import estilo_kira as _est
    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.uix.screenmanager import Screen
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.widget import Widget
    from kivy.graphics import Color, Line, Rectangle
    from kivy.metrics import dp
    import defensa_juego_kira as dj

    tam = _est.tam
    boton = ctx["boton"]
    FUENTE = ctx["FUENTE"]
    MONO = ctx.get("FUENTE_MONO", FUENTE)
    NEON, VERDE, ROJO, TENUE, GRIS, TXT = (ctx[k] for k in ("NEON", "VERDE", "ROJO", "TENUE", "GRIS", "TXT"))
    ir, core, voz, con = ctx["ir"], ctx["core"], ctx.get("voz"), ctx.get("consola")

    CY = (0.13, 0.89, 1, 1)        # cian
    VD = (0.10, 1.0, 0.60, 1)      # verde
    RJ = (1.0, 0.25, 0.42, 1)      # rojo amenaza
    CHARS = "アイウエオカキクケコサシスセソ01=+*<>KIRA"
    RONDAS = 10

    pant = Screen(name="defensa")
    raiz = FloatLayout()
    pant.add_widget(raiz)

    # ---- fondo negro + pasillo en perspectiva (líneas cian) ----
    fondo = Widget()
    raiz.add_widget(fondo)
    with fondo.canvas.before:
        Color(0.01, 0.02, 0.035, 1)
        bg = Rectangle(pos=(0, 0), size=(10, 10))

    def pintar_fondo(*_):
        bg.pos, bg.size = fondo.pos, fondo.size
        fondo.canvas.after.clear()
        w, h = fondo.width, fondo.height
        cx, cy = w * 0.5, h * 0.60            # punto de fuga, algo por encima del centro
        fw, fh = w * 0.28, h * 0.22           # hueco del fondo (fin del pasillo)
        x0, x1, y0, y1 = cx - fw / 2, cx + fw / 2, cy - fh / 2, cy + fh / 2
        with fondo.canvas.after:
            Color(*CY)
            Line(points=[0, h, x0, y1], width=1.2)
            Line(points=[w, h, x1, y1], width=1.2)
            Line(points=[0, 0, x0, y0], width=1.2)
            Line(points=[w, 0, x1, y0], width=1.2)
            Line(rectangle=[x0, y0, fw, fh], width=1.2)
    fondo.bind(pos=pintar_fondo, size=pintar_fondo)

    # ---- lluvia de letras (columnas que caen, forman las paredes) ----
    capa = FloatLayout()
    raiz.add_widget(capa)
    columnas = []

    def crear_lluvia():
        for c in columnas:
            capa.remove_widget(c)
        columnas.clear()
        w = max(dp(300), Window.width)
        n = max(10, int(w / dp(26)))
        for i in range(n):
            lb = Label(text="", markup=False, color=(0.11, 1, 0.6, 0.55), font_size=tam(13),
                       halign="center", valign="top", size_hint=(None, None),
                       width=dp(22), height=Window.height, **MONO)
            lb.x = i * (w / n)
            lb.y = random.uniform(-Window.height * 0.5, Window.height * 0.5)
            lb._vel = random.uniform(dp(60), dp(180))
            lb._largo = random.randint(8, 26)
            lb.text = "\n".join(random.choice(CHARS) for _ in range(lb._largo))
            capa.add_widget(lb)
            columnas.append(lb)

    def mover_lluvia(dt):
        if sm.current != "defensa":
            return
        for lb in columnas:
            lb.y -= lb._vel * dt
            if lb.top < 0:
                lb.y = Window.height + random.uniform(0, Window.height * 0.4)
                lb.text = "\n".join(random.choice(CHARS) for _ in range(lb._largo))

    # ---- HUD (encima de todo) ----
    hud = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
    raiz.add_widget(hud)

    titulo = Label(text="KIRA // DEFENSA", color=CY, font_size=tam(16), bold=True, size_hint_y=None,
                   height=dp(28), halign="center", **MONO)
    hud.add_widget(titulo)

    panel = BoxLayout(orientation="vertical", size_hint=(0.92, None), height=dp(220), spacing=dp(4),
                      pos_hint={"center_x": 0.5})
    with panel.canvas.before:
        pcol = Color(0.2, 0.02, 0.06, 0.0)
        prect = Rectangle(pos=(0, 0), size=(10, 10))
        pbor = Color(1, 0.25, 0.42, 0.0)
        pline = Line(width=1.4)

    def _panel_bg(*_):
        prect.pos, prect.size = panel.pos, panel.size
        pline.rectangle = [panel.x, panel.y, panel.width, panel.height]
    panel.bind(pos=_panel_bg, size=_panel_bg)
    etq = Label(text="", color=(1, 1, 1, 1), font_size=tam(13), halign="center", valign="middle",
                markup=True, **FUENTE)
    etq.bind(size=lambda w, v: setattr(w, "text_size", (w.width - dp(10), None)))
    panel.add_widget(etq)
    hud_centro = BoxLayout()
    hud_centro.add_widget(panel)
    hud.add_widget(hud_centro)

    marcador = Label(text="", color=TENUE, font_size=tam(12), size_hint_y=None, height=dp(24),
                     halign="center", **MONO)
    hud.add_widget(marcador)

    linea_con = Label(text="", color=(0.56, 0.94, 0.77, 1), font_size=tam(11.5), size_hint_y=None,
                      height=dp(40), halign="center", valign="middle", **MONO)
    linea_con.bind(size=lambda w, v: setattr(w, "text_size", (w.width - dp(8), w.height)))
    hud.add_widget(linea_con)

    fila = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
    btn_combatir = boton("COMBATIR", lambda: decidir(True), ROJO)
    btn_pasar = boton("dejar pasar", lambda: decidir(False), GRIS)
    btn_salir = boton("‹ Salir", lambda: salir(), GRIS, size_hint_x=None, width=dp(88))
    fila.add_widget(btn_salir)
    fila.add_widget(btn_combatir)
    fila.add_widget(btn_pasar)
    hud.add_widget(fila)

    # ---- estado del juego ----
    est = {"i": 0, "esc": None, "esperando": False, "resultados": [], "ac": 0, "fa": 0, "fl": 0,
           "defensa": None, "reloj_auto": None, "activo": False}

    def _mostrar_panel(color_borde, fondo_rgba):
        pcol.rgba = fondo_rgba
        pbor.rgba = color_borde

    def nueva_ronda(_dt=None):
        if not est["activo"]:
            return
        if est["i"] >= RONDAS:
            terminar()
            return
        est["i"] += 1
        esc = dj.generar((id(pant), est["i"], random.random()))
        est["esc"] = esc
        est["esperando"] = True
        titulo.text = f"KIRA // DEFENSA · ronda {est['i']} de {RONDAS}"
        datos = []
        if esc.get("trafico", 0) >= 1.6:
            datos.append(f"tráfico x{esc['trafico']}")
        if esc.get("logins", 0) >= 10:
            datos.append(f"{esc['logins']} logins fallidos")
        if esc.get("puertos", 0) >= 10:
            datos.append(f"{esc['puertos']} puertos tocados")
        if esc.get("oculto"):
            datos.append("una conexión oculta")
        if esc.get("enlace"):
            datos.append("un enlace raro")
        pista = ", ".join(datos) if datos else "movimiento tranquilo, nada raro"
        _mostrar_panel((1, 0.65, 0.2, 0.9), (0.12, 0.09, 0.02, 0.85))
        etq.text = "[b]ALGO SE ACERCA[/b]\n" + pista + "\n\n¿Lo combates o lo dejas pasar?"
        _con("▸ Ronda %d: %s" % (est["i"], pista))
        # si no decides en 3,5 s, Kira decide (así puedes solo mirar)
        est["reloj_auto"] = Clock.schedule_once(lambda _d: decidir(None), 3.5)

    def decidir(combatir):
        if not est["esperando"]:
            return
        est["esperando"] = False
        if est["reloj_auto"] is not None:
            est["reloj_auto"].cancel()
            est["reloj_auto"] = None
        esc = est["esc"]
        d = dj.decidir(est["defensa"], esc)        # lo que ve Kira (para aprender)
        if combatir is None:                        # lo decide Kira
            combatir = d["es_amenaza"]
            quien = "Kira decide"
        else:
            quien = "Tú decides"
        # resultado según la verdad del escenario
        if esc["ataque"] and combatir:
            est["ac"] += 1
            res = "acierto"
            nom = dj.AMENAZAS[esc["tipo"]]["nombre"]
            combate = "\n".join("• " + c for c in dj.AMENAZAS[esc["tipo"]]["combate"])
            _mostrar_panel((1, 0.25, 0.42, 1), (0.28, 0.02, 0.08, 0.92))
            etq.text = f"[b]⛔ AMENAZA: {nom.upper()}[/b]\n{dj.AMENAZAS[esc['tipo']]['pista']}\n\n[b]CÓMO LA COMBATO[/b]\n{combate}"
            _con(f"⛔ {nom} → la combato ✓ ({quien})")
        elif esc["ataque"] and not combatir:
            est["fl"] += 1
            res = "se_escapo"
            nom = dj.AMENAZAS[esc["tipo"]]["nombre"]
            _mostrar_panel((1, 0.65, 0.2, 1), (0.2, 0.12, 0.02, 0.9))
            etq.text = f"[b]✗ SE TE ESCAPÓ[/b]\nEra una «{nom}» y la dejaste pasar.\nApunto para reconocerla antes."
            _con(f"✗ se escapó una «{nom}» ({quien})")
        elif (not esc["ataque"]) and combatir:
            est["fa"] += 1
            res = "falsa_alarma"
            _mostrar_panel((1, 0.65, 0.2, 1), (0.2, 0.12, 0.02, 0.9))
            etq.text = "[b]⚠ FALSA ALARMA[/b]\nEra tráfico sano y lo paraste.\nMejor dejarlo pasar la próxima."
            _con(f"⚠ falsa alarma: era tráfico sano ({quien})")
        else:
            est["ac"] += 1
            res = "acierto"
            _mostrar_panel((0.1, 1, 0.6, 1), (0.02, 0.18, 0.1, 0.9))
            etq.text = "[b]✓ TRÁFICO SANO[/b]\nBien: no era amenaza y lo dejaste pasar."
            _con(f"✓ tráfico sano, bien hecho ({quien})")
        est["resultados"].append({"esc": esc, "decision": d, "resultado": res})
        _marcador()
        Clock.schedule_once(nueva_ronda, 1.8)

    def terminar():
        est["activo"] = False
        d = est["defensa"]
        cambios = dj.aprender(d, est["resultados"])    # afina los DATOS (umbrales)
        try:
            d.guardar()
        except Exception:
            pass
        _mostrar_panel((0.1, 1, 0.6, 1), (0.02, 0.16, 0.09, 0.92))
        etq.text = (f"[b]ENTRENAMIENTO HECHO[/b]\nAciertos {est['ac']} · se escaparon {est['fl']} · "
                    f"falsas {est['fa']}\n\n" + ("He afinado mis defensas:\n" + "\n".join("• " + c for c in cambios)
                                                 if cambios else "Mis defensas ya estaban finas."))
        for c in cambios:
            _con("⟳ Aprendí: " + c)
        _con("■ Entrenamiento terminado.")
        try:
            if con is not None:
                con.poner_codigo(dj.codigo_detector(d)) if hasattr(con, "poner_codigo") else con.codigo_vivo(dj.codigo_detector(d))
        except Exception:
            pass
        if voz is not None:
            try:
                voz.hablar(f"Entrenamiento hecho. {est['ac']} aciertos. He afinado mis defensas.")
            except Exception:
                pass

    def _marcador():
        marcador.text = f"aciertos {est['ac']}   ·   se escaparon {est['fl']}   ·   falsas {est['fa']}"

    def _con(texto):
        linea_con.text = texto
        try:
            if con is not None and con.activa:
                con.linea(texto)
        except Exception:
            pass

    def abrir(*_):
        est.update(i=0, esc=None, esperando=False, resultados=[], ac=0, fa=0, fl=0, activo=True, reloj_auto=None)
        try:
            est["defensa"] = dj.Defensa(ruta=__import__("os").path.join(getattr(core, "dir", "."), "defensa.json"))
        except Exception:
            est["defensa"] = dj.Defensa()
        try:
            if con is not None:
                con.empezar("Juego de defensa (laberinto)", pedido="defensa")
        except Exception:
            pass
        crear_lluvia()
        _marcador()
        ir("defensa")
        pintar_fondo()
        Clock.schedule_once(nueva_ronda, 0.6)

    def salir():
        est["activo"] = False
        if est["reloj_auto"] is not None:
            try:
                est["reloj_auto"].cancel()
            except Exception:
                pass
        try:
            if con is not None and con.activa:
                con.terminar("Saliste del juego de defensa.")
        except Exception:
            pass
        ir("menu")

    def detener():
        est["activo"] = False

    Clock.schedule_interval(mover_lluvia, 1 / 20.0)
    Window.bind(size=lambda *_: (crear_lluvia(), pintar_fondo()))
    sm.add_widget(pant)
    return {"abrir": abrir, "detener": detener}
