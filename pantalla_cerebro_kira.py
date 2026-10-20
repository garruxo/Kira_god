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
    vista = core.vista
    camara = core.camara
    cerebro = core.cerebro_propio
    est = {"reloj": None, "aviso": ""}

    _, c = pantalla("cerebro_kira", "CEREBRO Y OÍDO")

    import estilo_kira as _est

    def titulo(t):
        return _est.ajustar(Label(text=t, size_hint_y=None, height=dp(30), color=NEON, font_size=_est.tam(16), bold=True,
                                  halign="left", **FUENTE), lineas=1)

    def etiqueta(alto=56):
        lb = Label(text="", size_hint_y=None, height=dp(alto), color=TXT, font_size=_est.tam(13), halign="left", **FUENTE)
        return _est.ajustar(lb, minimo=10, lineas=max(2, int(alto // 16)))

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
    c.add_widget(titulo("SIEMPRE ACTIVA Y VER LA PANTALLA"))
    lb_vis = etiqueta(56)
    c.add_widget(lb_vis)
    fila4 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    btn_siempre = boton("", lambda: alternar_siempre(), GRIS, alto=44)
    btn_ver = boton("Dejar que vea la pantalla", lambda: pedir_ver(), GRIS, alto=44)
    fila4.add_widget(btn_siempre)
    fila4.add_widget(btn_ver)
    c.add_widget(fila4)
    fila5 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    btn_acc = boton("Permiso para saber qué app usas", lambda: vista.java and vista.java.abrir_ajustes_uso(), GRIS, alto=44)
    fila5.add_widget(btn_acc)
    fila5.add_widget(boton("Apps privadas", lambda: setattr(ayuda, "text", core.procesar_orden("apps privadas")
                                                             + "\n\nPara añadir otra: ábrela y di «Kira, no mires esta app»."),
                           GRIS, alto=44))
    c.add_widget(fila5)
    c.add_widget(titulo("OJOS Y CÁMARA (ver fotos y la pantalla)"))
    lb_ojo = etiqueta(56)
    c.add_widget(lb_ojo)
    fila6 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    btn_ojos = boton("Descargar los ojos (0,7 GB)", lambda: descargar_ojos(), VERDE, alto=44)
    btn_cam = boton("Permiso de cámara", lambda: camara.java and camara.java.pedir_permiso(), GRIS, alto=44)
    fila6.add_widget(btn_ojos)
    fila6.add_widget(btn_cam)
    c.add_widget(fila6)
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
                           if oido.libreria_disponible() else "Oído descargado, pero no encuentro su librería: " + (oido.error_lib or "?"))
        elif not oido.libreria_disponible():
            lb_oid.text = "No encuentro la librería del oído propio (" + (oido.error_lib or "?") + "). Mándale esta pantalla a Claude."
        else:
            lb_oid.text = "Sin oído propio todavía: pulsa «Descargar el oído»."
        btn_oid.disabled = oido.modelo_instalado() or oido.estado == "descargando"
        btn_uso.text = "Usar oído propio: " + ("SÍ" if ajustes.oido_propio else "NO")
        if cerebro.estado == "descargando" and est.get("bajando_ojos"):
            lb_ojo.text = f"Descargando los ojos… {cerebro.progreso * 100:.0f} %"
        elif cerebro.ojos_instalados():
            lb_ojo.text = "Tiene ojos: " + ("cargados, puede ver fotos y la pantalla." if cerebro.con_ojos()
                                            else "se cargan al encender el cerebro.")
        else:
            lb_ojo.text = ("Sin ojos: con la cámara solo lee letras. Con ojos (0,7 GB, sin internet) te dice qué tienes "
                           "delante y entiende la pantalla.")
        btn_ojos.disabled = cerebro.ojos_instalados() or cerebro.estado == "descargando" or not cerebro.modelo_instalado()
        btn_cam.disabled = not camara.disponible() or camara.tiene_permiso()
        btn_cam.text = "Cámara: permiso dado" if camara.tiene_permiso() else "Permiso de cámara"
        btn_siempre.text = "Siempre activa: " + ("SÍ" if vista.siempre_activa else "NO")
        if not vista.disponible():
            lb_vis.text = "Esto solo funciona en el móvil."
        else:
            ver = vista.puede_ver()
            uso = False
            try:
                uso = vista.java.acceso_uso()
            except Exception:
                pass
            lb_vis.text = ("Puede ver la pantalla cuando se lo pidas («Kira, ¿qué ves?»)." if ver else
                           "No ve la pantalla (Android te pedirá permiso).") + \
                          (f" Apps privadas: {len(vista.privadas)}." + ("" if uso else " Falta el permiso para saber qué app usas."))
            btn_ver.disabled = ver

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

    def permiso_notificaciones():
        try:
            from android.permissions import Permission, check_permission, request_permissions
            if hasattr(Permission, "POST_NOTIFICATIONS") and not check_permission(Permission.POST_NOTIFICATIONS):
                request_permissions([Permission.POST_NOTIFICATIONS])
        except Exception:
            pass

    def alternar_siempre():
        permiso_notificaciones()
        vista.poner_siempre_activa(not vista.siempre_activa)
        pintar()

    def pedir_ver():
        if vista.java is None:
            return
        permiso_notificaciones()
        est["aviso"] = "Android te va a pedir permiso para que Kira vea la pantalla."
        vista.pedir_ver(lambda ok: Clock.schedule_once(lambda _dt: (est.update(
            aviso="Ya puedo ver la pantalla cuando me lo pidas." if ok else "No me diste permiso para ver la pantalla."),
            pintar()), 0.5))

    def descargar_ojos():
        est["bajando_ojos"] = True

        def trabajo():
            try:
                cerebro.descargar_ojos()
                est["aviso"] = "Ojos descargados. Reiniciando el cerebro para cargarlos…"
                if cerebro.encendido():
                    cerebro.apagar()
                cerebro.encender()
                core.cerebro_ia.local_disponible(forzar=True)
                est["aviso"] = ""
            except cp.CerebroPropioError as e:
                est["aviso"] = str(e)
            est["bajando_ojos"] = False
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
