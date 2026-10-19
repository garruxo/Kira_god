# -*- coding: utf-8 -*-
"""
sala_av_kira.py - MESA DE MEZCLA de audio y EDITOR DE VÍDEO (Kivy). Pantallas finas sobre audio_kira/editor_kira.

  mezcla : faders por pista (hasta 4) con volumen y panorámica, volumen general, y botón Mezclar.
  editor : elige un vídeo de la mediateca y aplícale cortar / redimensionar / unir / poner música / quitar audio.

Todo se ejecuta con el ffmpeg RESTRINGIDO (aquí si lo hay, o en el laboratorio del PC) a través de
herramientas_kira.Herramientas. El resultado se añade a la mediateca y se intenta copiar a Descargas.
"""
import os


def montar_av(sm, ctx):
    from kivy.clock import Clock
    from kivy.metrics import dp, sp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.screenmanager import Screen
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.slider import Slider

    import audio_kira as ak
    import editor_kira as ed
    import herramientas_kira as hkmod
    import inicio_kira as ik

    boton, entrada, texto_largo, en_hilo = ctx["boton"], ctx["entrada"], ctx["texto_largo"], ctx["en_hilo"]
    TXT, NEON, TENUE, GRIS, VERDE, ROJO = (ctx[k] for k in ("TXT", "NEON", "TENUE", "GRIS", "VERDE", "ROJO"))
    FUENTE, ir, core, ganchos, dir_datos = ctx["FUENTE"], ctx["ir"], ctx["core"], ctx["ganchos"], ctx["dir_datos"]
    import diseno_kira as dk
    mediateca = dk.Mediateca(os.path.join(dir_datos, "mediateca.json"))
    herr = hkmod.Herramientas(dir_datos)

    def etiqueta(texto="", alto=24, color=TENUE, **kw):
        lb = Label(text=texto, size_hint_y=None, height=dp(alto), color=color, font_size=sp(13), halign="left", valign="middle", **FUENTE, **kw)
        lb.bind(width=lambda w, a: setattr(w, "text_size", (a, None)))
        return lb

    def barra(titulo, accion):
        b = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        b.add_widget(boton("‹ Menú", accion, GRIS, alto=44, size_hint_x=None, width=dp(100)))
        b.add_widget(Label(text=titulo, color=NEON, font_size=sp(16), halign="left", **FUENTE))
        return b

    def audios():
        return [m["titulo"] for m in mediateca.listar(tipo="audio")]

    def videos():
        return [m["titulo"] for m in mediateca.listar(tipo="video")]

    def avisa_hilo(destino_label, accion, fin):
        """Corre 'accion' en un hilo y escribe el resultado o el error en destino_label."""
        destino_label.text = "Procesando… (si lo hace el laboratorio, puede tardar)"

        def hecho(r):
            if isinstance(r, Exception):
                destino_label.text = f"[x] {r}"
                consejo = core.registrar_error("mezcla/editor", str(r)) if callable(getattr(core, "registrar_error", None)) else ""
                if consejo:
                    destino_label.text += "\n" + consejo
            else:
                fin(r)
        en_hilo(accion, hecho)

    def entregar(nombre, tipo, destino_label):
        # Guarda el resultado en una carpeta PERSISTENTE (diseno/audios|videos), no en la de trabajo (que es temporal),
        # lo añade a la mediateca desde allí y lo intenta copiar a Descargas.
        try:
            _ok, msg = herr.exportar(nombre)
        except Exception as e:
            destino_label.text = f"[x] No se pudo guardar: {e}"
            return
        destino_label.text = f"[OK] Listo: {nombre}. {msg}"
        refrescar_listas()

    # =================================================================================
    #  MESA DE MEZCLA
    # =================================================================================
    p_mez = Screen(name="mezcla")
    r_mez = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
    r_mez.add_widget(barra("MESA DE MEZCLA", lambda: ir("menu")))
    r_mez.add_widget(etiqueta("Elige audios de tu mediateca y ajusta volumen y panorámica (izquierda/derecha) de cada pista.", alto=40))
    sv = ScrollView(size_hint_y=0.5, do_scroll_x=False)
    cont = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=(0, dp(4)))
    cont.bind(minimum_height=cont.setter("height"))
    sv.add_widget(cont)
    r_mez.add_widget(sv)
    pistas_ui = []

    def fila_pista(idx):
        caja = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(96), spacing=dp(2))
        sel = {"titulo": None}
        lb_sel = boton("Pista vacía (tocar para elegir)", lambda: ciclar(), GRIS, alto=36)
        caja.add_widget(lb_sel)
        fila_v = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(6))
        fila_v.add_widget(Label(text="Vol", size_hint_x=None, width=dp(34), color=TENUE, font_size=sp(12), **FUENTE))
        s_vol = Slider(min=0, max=200, value=100, step=5)
        fila_v.add_widget(s_vol)
        lb_v = Label(text="100%", size_hint_x=None, width=dp(50), color=TXT, font_size=sp(12), **FUENTE)
        fila_v.add_widget(lb_v)
        s_vol.bind(value=lambda _w, v: setattr(lb_v, "text", f"{int(v)}%"))
        caja.add_widget(fila_v)
        fila_p = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(6))
        fila_p.add_widget(Label(text="Pan", size_hint_x=None, width=dp(34), color=TENUE, font_size=sp(12), **FUENTE))
        s_pan = Slider(min=-100, max=100, value=0, step=5)
        fila_p.add_widget(s_pan)
        lb_p = Label(text="centro", size_hint_x=None, width=dp(50), color=TXT, font_size=sp(12), **FUENTE)
        fila_p.add_widget(lb_p)
        s_pan.bind(value=lambda _w, v: setattr(lb_p, "text", "centro" if abs(v) < 5 else (f"izq {int(-v)}" if v < 0 else f"der {int(v)}")))
        caja.add_widget(fila_p)

        def ciclar():
            lista = ["(vacía)"] + audios()
            actual = sel["titulo"] or "(vacía)"
            i = (lista.index(actual) + 1) % len(lista) if actual in lista else 0
            sel["titulo"] = None if lista[i] == "(vacía)" else lista[i]
            lb_sel.text = "Pista vacía (tocar para elegir)" if sel["titulo"] is None else f"♪ {sel['titulo'][:40]}"
        info = {"sel": sel, "vol": s_vol, "pan": s_pan, "ciclar": ciclar}
        pistas_ui.append(info)
        return caja
    for k in range(4):
        cont.add_widget(fila_pista(k))
    fila_mg = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(6))
    fila_mg.add_widget(Label(text="Volumen general", size_hint_x=None, width=dp(140), color=TENUE, font_size=sp(12), **FUENTE))
    s_master = Slider(min=0, max=200, value=100, step=5)
    fila_mg.add_widget(s_master)
    r_mez.add_widget(fila_mg)
    est_mez = etiqueta("", alto=48, color=TXT)
    r_mez.add_widget(est_mez)
    campo_nom = entrada("Nombre de la mezcla (opcional)")
    r_mez.add_widget(campo_nom)
    btn_mez = boton("Mezclar", lambda: mezclar(), VERDE)
    r_mez.add_widget(btn_mez)
    p_mez.add_widget(r_mez)
    sm.add_widget(p_mez)

    def mezclar():
        pistas = []
        for info in pistas_ui:
            if info["sel"]["titulo"]:
                pistas.append({"titulo": info["sel"]["titulo"],
                               "volumen": getattr(info["vol"], "value", 100) / 100.0,
                               "pan": getattr(info["pan"], "value", 0) / 100.0})
        if not pistas:
            est_mez.text = "Elige al menos una pista (toca «Pista vacía»)."
            return
        nombre = ik.limpiar_entrada(campo_nom.text) or "mezcla"
        salida = dk._nombre_archivo(nombre, ".mp3") if hasattr(dk, "_nombre_archivo") else "mezcla.mp3"
        vg = getattr(s_master, "value", 100) / 100.0
        btn_mez.disabled = True

        def accion():
            return ak.mezclar(herr, pistas, salida, volumen_general=vg)

        def fin(r):
            btn_mez.disabled = False
            entregar(r, "audio", est_mez)
        avisa_hilo(est_mez, accion, fin)
        if btn_mez.disabled:
            pass
    ganchos["mezcla"] = lambda: None

    # =================================================================================
    #  EDITOR DE VÍDEO
    # =================================================================================
    p_ed = Screen(name="editor_video")
    r_ed = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
    r_ed.add_widget(barra("EDITOR DE VÍDEO", lambda: ir("menu")))
    sel_v = {"titulo": None, "titulo2": None, "audio": None, "tam": "720p"}
    btn_vid = boton("Elegir vídeo…", lambda: ciclar("titulo", videos, btn_vid, "Vídeo"), GRIS)
    r_ed.add_widget(btn_vid)
    fila_op = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    campo_ini = entrada("inicio (s o mm:ss)")
    campo_fin = entrada("fin")
    fila_op.add_widget(campo_ini)
    fila_op.add_widget(campo_fin)
    fila_op.add_widget(boton("Cortar", lambda: op_cortar(), VERDE, size_hint_x=None, width=dp(90)))
    r_ed.add_widget(fila_op)
    fila_t = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    btn_tam = boton("Tamaño: 720p", lambda: ciclar_tam(), GRIS)
    fila_t.add_widget(btn_tam)
    fila_t.add_widget(boton("Redimensionar", lambda: op_redim(), VERDE, size_hint_x=None, width=dp(140)))
    r_ed.add_widget(fila_t)
    fila_u = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    btn_vid2 = boton("2º vídeo…", lambda: ciclar("titulo2", videos, btn_vid2, "2º"), GRIS)
    fila_u.add_widget(btn_vid2)
    fila_u.add_widget(boton("Unir", lambda: op_unir(), VERDE, size_hint_x=None, width=dp(90)))
    r_ed.add_widget(fila_u)
    fila_m = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    btn_aud = boton("Música…", lambda: ciclar("audio", audios, btn_aud, "Música"), GRIS)
    fila_m.add_widget(btn_aud)
    fila_m.add_widget(boton("Poner música", lambda: op_musica(), VERDE, size_hint_x=None, width=dp(140)))
    r_ed.add_widget(fila_m)
    fila_q = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    fila_q.add_widget(boton("Quitar audio", lambda: op_quitar(), GRIS))
    fila_q.add_widget(boton("Extraer audio (mp3)", lambda: op_extraer(), GRIS))
    r_ed.add_widget(fila_q)
    est_ed = etiqueta("Elige un vídeo y una operación.", alto=60, color=TXT)
    r_ed.add_widget(est_ed)
    p_ed.add_widget(r_ed)
    sm.add_widget(p_ed)

    def ciclar(clave, fuente, btn, prefijo):
        lista = ["(ninguno)"] + fuente()
        actual = sel_v[clave] or "(ninguno)"
        i = (lista.index(actual) + 1) % len(lista) if actual in lista else 0
        sel_v[clave] = None if lista[i] == "(ninguno)" else lista[i]
        btn.text = f"{prefijo}…" if sel_v[clave] is None else f"{prefijo}: {sel_v[clave][:26]}"

    def ciclar_tam():
        ts = list(ed.TAMANOS)
        sel_v["tam"] = ts[(ts.index(sel_v["tam"]) + 1) % len(ts)]
        btn_tam.text = "Tamaño: " + sel_v["tam"]

    def _necesita_video():
        if not sel_v["titulo"]:
            est_ed.text = "Elige primero un vídeo."
            return False
        return True

    def _correr(accion):
        avisa_hilo(est_ed, accion, lambda r: entregar(r, "video" if r.endswith(".mp4") else "audio", est_ed))

    def op_cortar():
        if not _necesita_video():
            return
        _correr(lambda: ed.cortar(herr, sel_v["titulo"], ik.limpiar_entrada(campo_ini.text) or "0", ik.limpiar_entrada(campo_fin.text) or "5"))

    def op_redim():
        if not _necesita_video():
            return
        _correr(lambda: ed.redimensionar(herr, sel_v["titulo"], sel_v["tam"]))

    def op_unir():
        if not (_necesita_video() and sel_v["titulo2"]):
            est_ed.text = "Elige el vídeo y el 2º vídeo."
            return
        _correr(lambda: ed.unir(herr, [sel_v["titulo"], sel_v["titulo2"]], sel_v["tam"]))

    def op_musica():
        if not (_necesita_video() and sel_v["audio"]):
            est_ed.text = "Elige el vídeo y la música."
            return
        _correr(lambda: ed.poner_musica(herr, sel_v["titulo"], sel_v["audio"]))

    def op_quitar():
        if _necesita_video():
            _correr(lambda: ed.quitar_audio(herr, sel_v["titulo"]))

    def op_extraer():
        if _necesita_video():
            _correr(lambda: ed.extraer_audio_video(herr, sel_v["titulo"], "mp3"))

    def refrescar_listas():
        pass
    ganchos["editor_video"] = lambda: None
    ganchos["mezcla"] = lambda: None

    return {"mediateca": mediateca, "herramientas": herr}
