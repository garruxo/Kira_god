# -*- coding: utf-8 -*-
"""
taller_kira.py - Pantalla TALLER (Kivy): qué sabe hacer Kira, qué le falta y cómo prepararse.

Para cada capacidad Kira dice su estado:
  - DISPONIBLE: ya funciona; el botón «Abrir» te lleva a donde se usa (mesa de mezcla, editor, estudio…).
  - FALTA ENTORNO: necesita ffmpeg; se explica cómo conseguirlo. Si tu laboratorio arrancó con --permitir-instalar,
    el botón «Instalar en el PC» se lo pide al PC (lista blanca de paquetes, con tu confirmación).
Nada se instala ni se abre sin que lo pulses tú. (Para funciones NUEVAS que no están en esta lista, Kira todavía
puede programarlas desde la Sala Hacker: el Taller solo gestiona las que ya trae.)
"""
import os


def montar_taller(sm, ctx):
    from kivy.clock import Clock
    from kivy.metrics import dp, sp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.screenmanager import Screen
    from kivy.uix.scrollview import ScrollView

    import capacidades_kira as cap

    boton, texto_largo, en_hilo = ctx["boton"], ctx["texto_largo"], ctx["en_hilo"]
    TXT, NEON, TENUE, GRIS, VERDE, ROJO = (ctx[k] for k in ("TXT", "NEON", "TENUE", "GRIS", "VERDE", "ROJO"))
    FUENTE, ir, core, ganchos = ctx["FUENTE"], ctx["ir"], ctx["core"], ctx["ganchos"]
    preparar_mejora = ctx["preparar_mejora"]

    p = Screen(name="taller")
    raiz = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
    barra = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    barra.add_widget(boton("‹ Menú", lambda: ir("menu"), GRIS, alto=44, size_hint_x=None, width=dp(100)))
    barra.add_widget(Label(text="TALLER DE KIRA", color=NEON, font_size=sp(16), halign="left", **FUENTE))
    raiz.add_widget(barra)
    resumen = Label(text="", size_hint_y=None, height=dp(44), color=TENUE, font_size=sp(12), halign="left", valign="middle", **FUENTE)
    resumen.bind(width=lambda w, a: setattr(w, "text_size", (a, None)))
    raiz.add_widget(resumen)
    sv = ScrollView(size_hint_y=0.42, do_scroll_x=False)
    lista = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
    lista.bind(minimum_height=lista.setter("height"))
    sv.add_widget(lista)
    raiz.add_widget(sv)
    sv_det, detalle = texto_largo("Elige una capacidad para ver qué hace falta.")
    raiz.add_widget(sv_det)
    fila = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
    btn_abrir = boton("Abrir", lambda: abrir(), VERDE, disabled=True)
    btn_inst = boton("Instalar en el PC", lambda: instalar(), GRIS, disabled=True)
    fila.add_widget(btn_abrir)
    fila.add_widget(btn_inst)
    raiz.add_widget(fila)
    btn_ref = boton("Actualizar (consulta el laboratorio)", lambda: refrescar(), GRIS)

    raiz.add_widget(btn_ref)
    p.add_widget(raiz)
    sm.add_widget(p)
    est = {"hechos": {"prefijos": [], "ffmpeg": None, "lab": False, "lab_instalar": False}, "sel": None, "reloj": None}
    ETIQ = {"disponible": "[OK] ", "programable": "[ ] ", "falta_entorno": "[!] "}
    COLOR = {"disponible": VERDE, "programable": GRIS, "falta_entorno": ROJO}

    def pintar():
        lista.clear_widgets()
        estados = cap.informe(est["hechos"])
        for c, e in zip(cap.CAPACIDADES, estados):
            lista.add_widget(boton(ETIQ[e["estado"]] + e["nombre"][:44], lambda c_=c: elegir(c_), COLOR[e["estado"]], alto=44))
        h = est["hechos"]
        resumen.text = ("ffmpeg: " + ({"local": "en este dispositivo", "laboratorio": "en el laboratorio del PC"}.get(h["ffmpeg"], "no disponible")) +
                        "  ·  laboratorio: " + ("conectado" if h["lab"] else "no conectado") +
                        ("  ·  el PC permite instalar" if h["lab_instalar"] else ""))
        if est["sel"]:
            elegir(est["sel"])

    def elegir(c):
        est["sel"] = c
        e = cap.estado(c, est["hechos"])
        detalle.text = cap.texto_plan(c, est["hechos"])
        btn_abrir.disabled = not (e["estado"] == "disponible" and c.get("abrir"))
        btn_inst.disabled = not (e["estado"] == "falta_entorno" and est["hechos"]["lab_instalar"])
        btn_inst.text = "Instalar en el PC" if est["hechos"]["lab_instalar"] else "Instalar (desactivado en el PC)"

    def refrescar(aviso=None):
        """Vuelve a mirar qué hay. 'aviso' se muestra encima del plan al terminar (para no perder un resultado)."""
        btn_ref.disabled = True
        resumen.text = "Mirando qué hay disponible…"

        def hecho(r):
            btn_ref.disabled = False
            est["hechos"] = r if isinstance(r, dict) else {"prefijos": [], "ffmpeg": None, "lab": False, "lab_instalar": False}
            pintar()
            if aviso:
                detalle.text = aviso + "\n\n" + detalle.text
        en_hilo(lambda: core.hechos_capacidades(), hecho)

    def abrir():
        """Abre la pantalla donde se usa la capacidad (mesa de mezcla, editor, estudio…) cuando ya está disponible."""
        c = est["sel"]
        if c is None or not c.get("abrir"):
            return
        if cap.estado(c, est["hechos"])["estado"] != "disponible":
            return
        ir(c["abrir"])

    def _programar_desactivado():
        c = est["sel"]
        if c is None or not cap.pedido_mejora(c):
            return
        preparar_mejora(cap.pedido_mejora(c))        # la API de «kira» ya va en las instrucciones del generador
        detalle.text = ("He preparado el pedido en la terminal (MEJORAR). Pulsa «Pedir mejora»: Kira escribirá el módulo, "
                        "el laboratorio lo probará y tú decides si se aplica.")

    def instalar():
        """Pide al PC instalar lo que falta (doble toque para confirmar)."""
        c = est["sel"]
        if c is None or not est["hechos"]["lab_instalar"]:
            return
        paquetes = cap.PAQUETES_UTILES["ffmpeg"]
        if est["reloj"] is None:
            btn_inst.text = "¿Seguro? Toca otra vez"
            detalle.text = (f"Se pedirá a TU PC instalar: {', '.join(paquetes)} (con pip, en el Python del laboratorio). "
                            "Solo paquetes de su lista permitida; nada se instala en el móvil.\nToca otra vez (6 s) para confirmar.")
            est["reloj"] = Clock.schedule_once(restablecer, 6)
            return
        est["reloj"].cancel()
        restablecer()
        btn_inst.disabled = True
        detalle.text = "Instalando en el PC… (puede tardar un par de minutos)"

        def hecho(r):
            btn_inst.disabled = False
            if isinstance(r, Exception):
                detalle.text = f"[x] {r}"
                return
            ok, msg = r
            consejo = ""
            if not ok and callable(getattr(core, "registrar_error", None)):
                consejo = core.registrar_error("instalar", str(msg)[-300:]) or ""
            texto = ("[OK] Instalado en el PC.\n" if ok else "[x] No se pudo instalar.\n") + str(msg)[-800:] + (("\n" + consejo) if consejo else "")
            detalle.text = texto
            if ok:
                refrescar(aviso=texto)
        en_hilo(lambda: _instalar(paquetes), hecho)

    def _instalar(paquetes):
        import video_cliente_kira as vc
        return vc.ClienteVideo().instalar(paquetes)

    def restablecer(*_):
        est["reloj"] = None
        btn_inst.text = "Instalar en el PC" if est["hechos"]["lab_instalar"] else "Instalar (desactivado en el PC)"

    def al_entrar():
        est["hechos"] = core.hechos_capacidades(consultar_laboratorio=False)
        pintar()
        refrescar()
    ganchos["taller"] = al_entrar
    return {"refrescar": refrescar}
