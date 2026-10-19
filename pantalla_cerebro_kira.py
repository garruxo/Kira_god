# -*- coding: utf-8 -*-
"""
pantalla_cerebro_kira.py - Pantalla «Cerebro y oído» (Kivy): descargar y encender el CEREBRO PROPIO de Kira
(cerebro_propio_kira) y su OÍDO PROPIO (oido_kira), con el progreso de las descargas.
"""
import threading

import cerebro_propio_kira as cp


def montar_cerebro(sm, p):
    from kivy.clock import Clock
    from kivy.metrics import dp, sp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label

    boton, texto_largo, pantalla = p["boton"], p["texto_largo"], p["pantalla"]
    TXT, TENUE, GRIS, VERDE, ROJO, NEON, FUENTE = (p[k] for k in ("TXT", "TENUE", "GRIS", "VERDE", "ROJO", "NEON", "FUENTE"))
    core, oido, ajustes = p["core"], p["oido"], p["ajustes"]
    cerebro = core.cerebro_propio
    est = {"reloj": None, "aviso": ""}

    _, c = pantalla("cerebro_kira", "CEREBRO Y OÍDO")

    def titulo(t):
        return Label(text=t, size_hint_y=None, height=dp(28), color=NEON, font_size=sp(16), bold=True,
                     halign="left", **FUENTE)

    def etiqueta(alto=56):
        lb = Label(text="", size_hint_y=None, height=dp(alto), color=TXT, font_size=sp(13), halign="left",
                   valign="middle", **FUENTE)
        lb.bind(width=lambda w, a: setattr(w, "text_size", (a, None)))
        return lb

    c.add_widget(titulo("CEREBRO PROPIO (su IA, dentro del móvil)"))
    lb_cer = etiqueta(70)
    c.add_widget(lb_cer)
    fila1 = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
    btn_lig = boton("", lambda: descargar("ligero"), VERDE)
    btn_lis = boton("", lambda: descargar("listo"), GRIS)
    fila1.add_widget(btn_lig)
    fila1.add_widget(btn_lis)
    c.add_widget(fila1)
    fila2 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    btn_enc = boton("Encender", lambda: encender(), VERDE, alto=44)
    btn_apa = boton("Apagar", lambda: apagar(), GRIS, alto=44)
    btn_pau = boton("Pausar descarga", lambda: cerebro.cancelar_descarga(), GRIS, alto=44)
    for b in (btn_enc, btn_apa, btn_pau):
        fila2.add_widget(b)
    c.add_widget(fila2)

    c.add_widget(titulo("OÍDO PROPIO (escucha sin parar, sin internet)"))
    lb_oid = etiqueta(56)
    c.add_widget(lb_oid)
    fila3 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    btn_oid = boton("Descargar el oído (39 MB)", lambda: descargar_oido(), VERDE, alto=44)
    btn_uso = boton("", lambda: alternar_oido(), GRIS, alto=44)
    fila3.add_widget(btn_oid)
    fila3.add_widget(btn_uso)
    c.add_widget(fila3)
    sv, ayuda = texto_largo(
        "Con el cerebro propio Kira charla y programa SIN internet, sin clave y sin Termux. Se descarga UNA vez "
        "(mejor con WiFi y el móvil enchufado) y se enciende sola cada vez que abres Kira. El ligero responde antes; "
        "el listo entiende y programa mejor, pero necesita más memoria (6 GB de RAM o más). Las respuestas van "
        "apareciendo mientras piensa. Es más lento y menos listo que Claude: si tienes clave, Kira puede usar Claude "
        "para lo difícil («cerebro mejoras claude»).")
    c.add_widget(sv)

    def pintar(*_):
        m = cp.MODELOS[cerebro.modelo]
        texto = cerebro.estado_texto()
        if cerebro.estado == "descargando":
            texto += f"\n[{'#' * int(cerebro.progreso * 20):<20}] {cerebro.progreso * 100:.1f} %"
        elif est["aviso"]:
            texto += "\n" + est["aviso"]
        lb_cer.text = texto
        for b, id_ in ((btn_lig, "ligero"), (btn_lis, "listo")):
            mm = cp.MODELOS[id_]
            if cerebro.modelo_instalado(id_):
                b.text = ("Usando " if cerebro.modelo == id_ else "Usar ") + mm["nombre"].split(" (")[0]
            else:
                b.text = f"Descargar {id_} ({mm['bytes'] / 1e9:.1f} GB)"
            b.background_color = VERDE if cerebro.modelo == id_ else GRIS
        btn_pau.disabled = cerebro.estado != "descargando"
        btn_enc.disabled = cerebro.encendido() or not cerebro.modelo_instalado() or cerebro.estado == "arrancando"
        btn_apa.disabled = not cerebro.encendido()
        if oido.estado == "descargando":
            lb_oid.text = f"Descargando el oído… {oido.progreso * 100:.0f} %"
        elif oido.modelo_instalado():
            lb_oid.text = ("Oído instalado. " + ({"escuchando": "Escuchando ahora.", "pausa": "En pausa mientras habla.",
                                                   "cargando": "Preparándose…", "error": oido.mensaje}.get(oido.estado, ""))
                           if oido.libreria_disponible() else "Oído descargado, pero esta versión de la app no trae su librería.")
        else:
            lb_oid.text = "Sin oído propio: Kira usa el reconocedor de Android (con sus pitidos)."
        btn_oid.disabled = oido.modelo_instalado() or oido.estado == "descargando"
        btn_uso.text = "Usar oído propio: " + ("SÍ" if ajustes.oido_propio else "NO")

    def descargar(id_):
        if cerebro.modelo_instalado(id_):
            cerebro.elegir(id_)
            if cerebro.encendido():
                cerebro.apagar()
            encender()
            return
        if cerebro.estado == "descargando":
            return
        cerebro.elegir(id_)
        est["aviso"] = ""

        def trabajo():
            try:
                cerebro.descargar(id_)
                est["aviso"] = "Descargado. Encendiendo…"
                if cerebro.tiene_motor():
                    cerebro.encender()
                    core.cerebro_ia.local_disponible(forzar=True)
            except cp.CerebroPropioError as e:
                est["aviso"] = str(e)
        threading.Thread(target=trabajo, daemon=True).start()
        pintar()

    def encender():
        est["aviso"] = "Despertando… (la primera vez tarda un poco)"
        cerebro.encender_en_segundo_plano(lambda ok: (est.update(aviso="" if ok else cerebro.mensaje),
                                                      core.cerebro_ia.local_disponible(forzar=True)))
        pintar()

    def apagar():
        cerebro.apagar()
        est["aviso"] = "Apagado (ahorra batería)."
        pintar()

    def descargar_oido():
        def trabajo():
            try:
                oido.descargar_modelo()
                Clock.schedule_once(lambda _dt: p["reiniciar_escucha"](), 0)
            except Exception:
                pass
        threading.Thread(target=trabajo, daemon=True).start()
        pintar()

    def alternar_oido():
        ajustes.alternar_oido()
        p["reiniciar_escucha"]()
        pintar()

    def al_entrar():
        pintar()
        if est["reloj"] is None:
            est["reloj"] = Clock.schedule_interval(lambda _dt: pintar() if sm.current == "cerebro_kira" else None, 0.5)
    p["ganchos"]["cerebro_kira"] = al_entrar
    return {"pintar": pintar}
