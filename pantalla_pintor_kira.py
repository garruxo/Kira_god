# -*- coding: utf-8 -*-
"""
pantalla_pintor_kira.py - Pantalla «Pintor» (Kivy): Kira pinta imágenes con su propia IA (pintor_kira).
Escribes (o dices) lo que quieres, eliges pincel y formato, y ves cómo se va formando con una barra de progreso.
Luego: guardarla en la galería, otra versión, ampliarla ×4 o borrarla. «Anterior / Siguiente» recorre lo pintado.
"""
import os

import pintor_kira as pk


def montar_pintor(sm, p):
    from kivy.clock import Clock
    from kivy.graphics import Color, RoundedRectangle
    from kivy.metrics import dp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.image import Image
    from kivy.uix.label import Label
    from kivy.uix.widget import Widget

    import estilo_kira as est
    tam = est.tam
    boton, entrada, pantalla, en_hilo = p["boton"], p["entrada"], p["pantalla"], p["en_hilo"]
    TXT, TENUE, GRIS, VERDE, ROJO, NEON, FUENTE = (p[k] for k in ("TXT", "TENUE", "GRIS", "VERDE", "ROJO", "NEON", "FUENTE"))
    core, voz, ajustes = p["core"], p["voz"], p["ajustes"]
    pintor = core.pintor

    _, c = pantalla("pintor", "PINTOR")
    st = {"pincel": pintor.modelo, "formato": "cuadrada", "ruta": None, "ocupado": False, "progreso": 0.0,
          "texto": "", "vista": os.path.join(pintor.dir, "pintor_vista.png"), "vista_mtime": 0.0, "reloj": None,
          "indice": 0, "ultimo": None, "descarga": None}

    def rotulo(texto="", alto=24, color=TENUE, t=12.5, lineas=1):
        return est.ajustar(Label(text=texto, size_hint_y=None, height=dp(alto), color=color, font_size=tam(t),
                                 halign="left", **FUENTE), minimo=10, lineas=lineas)

    lbl_estado = rotulo("", alto=36, lineas=2)
    c.add_widget(lbl_estado)
    fila_p = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    btn_rapido = boton("", lambda: elegir("rapido"), GRIS, alto=44)
    btn_realista = boton("", lambda: elegir("realista"), GRIS, alto=44)
    fila_p.add_widget(btn_rapido)
    fila_p.add_widget(btn_realista)
    c.add_widget(fila_p)
    btn_bajar = boton("", lambda: descargar(), VERDE, alto=44)
    c.add_widget(btn_bajar)

    campo = entrada("Describe la imagen… (ej.: un faro en una isla al atardecer)")
    c.add_widget(campo)
    fila_a = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
    btn_formato = boton("Cuadrada", lambda: rotar_formato(), GRIS, size_hint_x=0.42)
    btn_pintar = boton("Pintar", lambda: pintar(), VERDE)
    fila_a.add_widget(btn_formato)
    fila_a.add_widget(btn_pintar)
    c.add_widget(fila_a)

    class Barra(Widget):                                   # barra de progreso redondeada
        def __init__(self, **kw):
            super().__init__(size_hint_y=None, height=dp(8), **kw)
            self.valor = 0.0
            with self.canvas:
                Color(0.86, 0.89, 0.93, 1)
                self._fondo = RoundedRectangle(radius=[dp(4)])
                Color(*NEON)
                self._lleno = RoundedRectangle(radius=[dp(4)])
            self.bind(pos=self._colocar, size=self._colocar)

        def poner(self, v):
            self.valor = max(0.0, min(1.0, float(v)))
            self._colocar()

        def _colocar(self, *_):
            self._fondo.pos, self._fondo.size = self.pos, self.size
            self._lleno.pos, self._lleno.size = self.pos, (max(0.0, self.width * self.valor), self.height)

    barra = Barra()
    c.add_widget(barra)
    lbl_prog = rotulo("", alto=22)
    c.add_widget(lbl_prog)

    marco = BoxLayout(padding=dp(4))
    est.fondo_redondeado(marco, (0.93, 0.95, 0.97, 1), radio=14)
    try:
        imagen = Image(fit_mode="contain")
    except TypeError:                                      # Kivy antiguo
        imagen = Image(allow_stretch=True, keep_ratio=True)
    vacio = est.ajustar(Label(text="Aquí aparecerá tu imagen.\nDescríbela arriba y pulsa «Pintar» (o dime «Kira, pinta…»).",
                              color=TENUE, font_size=tam(13.5), halign="center", **FUENTE), minimo=10, lineas=3)
    marco.add_widget(vacio)
    c.add_widget(marco)
    lbl_info = rotulo("", alto=34, lineas=2, t=11.5)
    c.add_widget(lbl_info)

    fila_r = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
    btn_galeria = boton("A la galería", lambda: a_galeria(), VERDE, alto=44)
    btn_otra = boton("Otra versión", lambda: pintar(otra=True), GRIS, alto=44)
    btn_ampliar = boton("Ampliar ×4", lambda: ampliar(), GRIS, alto=44)
    for b in (btn_galeria, btn_otra, btn_ampliar):
        fila_r.add_widget(b)
    c.add_widget(fila_r)
    fila_n = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
    btn_ant = boton("‹ Anterior", lambda: mover(1), GRIS, alto=40)
    btn_borrar = boton("Borrar", lambda: borrar(), ROJO, alto=40)
    btn_sig = boton("Siguiente ›", lambda: mover(-1), GRIS, alto=40)
    for b in (btn_ant, btn_borrar, btn_sig):
        fila_n.add_widget(b)
    c.add_widget(fila_n)

    # ---------- pintar la pantalla ----------
    def refrescar(*_):
        for clave, b in (("rapido", btn_rapido), ("realista", btn_realista)):
            m = pk.MODELOS[clave]
            nombre = "Rápido" if clave == "rapido" else "Realista"
            b.text = nombre + ("" if pintor.instalado(clave) else f" ({m['mb']} MB)")
            b.background_color = VERDE if st["pincel"] == clave else GRIS
            b.color = (1, 1, 1, 1) if st["pincel"] == clave else TXT
        falta = not pintor.instalado(st["pincel"])
        if pintor.estado == "descargando":
            btn_bajar.text = f"Pausar la descarga ({pintor.progreso * 100:.0f} %)"
        elif falta:
            btn_bajar.text = f"Descargar el {pk.MODELOS[st['pincel']]['nombre']} ({pk.MODELOS[st['pincel']]['mb']} MB, una vez)"
        btn_bajar.opacity = 1 if (falta or pintor.estado == "descargando") else 0
        btn_bajar.disabled = not (falta or pintor.estado == "descargando")
        btn_bajar.height = dp(44) if btn_bajar.opacity else 0
        if not pintor.tiene_motor():
            lbl_estado.text = "Esta versión no trae el motor de pintar (va en el APK del móvil)."
        elif not pintor.instalados():
            lbl_estado.text = "Elige un pincel y descárgalo una vez. Después pinta sin internet."
        else:
            lbl_estado.text = ("Pinta con su propia IA, sin internet. Rápido: segundos. Realista: más detalle, "
                               "puede tardar un par de minutos.")
        btn_formato.text = st["formato"].capitalize()
        btn_pintar.text = "Parar" if st["ocupado"] else "Pintar"
        btn_pintar.background_color = ROJO if st["ocupado"] else VERDE
        hay = st["ruta"] is not None and os.path.isfile(st["ruta"])
        for b in (btn_galeria, btn_otra, btn_ampliar, btn_borrar):
            b.disabled = not hay or st["ocupado"]
        btn_ampliar.text = "Ampliar ×4" if pintor.ampliador_instalado() else "Ampliar ×4 (64 MB)"
        lista = pintor.imagenes()
        btn_ant.disabled = st["ocupado"] or st["indice"] >= len(lista) - 1
        btn_sig.disabled = st["ocupado"] or st["indice"] <= 0

    def mostrar(ruta, info=""):
        st["ruta"] = ruta if ruta != st["vista"] else st["ruta"]
        hay = bool(ruta and os.path.isfile(ruta))
        marco.clear_widgets()
        marco.add_widget(imagen if hay else vacio)
        if hay:
            imagen.source = ruta
            try:
                imagen.reload()
            except Exception:
                pass
        else:
            imagen.source = ""
        if info:
            lbl_info.text = info
        refrescar()

    def elegir(clave):
        if st["ocupado"]:
            return
        st["pincel"] = clave
        try:
            pintor.elegir(clave)
        except pk.PintorError:
            pass
        refrescar()

    def rotar_formato():
        orden = list(pk.FORMATOS)
        st["formato"] = orden[(orden.index(st["formato"]) + 1) % len(orden)]
        refrescar()

    # ---------- descargar ----------
    def descargar(que=None):
        if pintor.estado == "descargando":
            pintor.cancelar()
            return
        que = que or st["pincel"]

        def fin(r):
            st["descarga"] = None
            lbl_prog.text = f"[x] {r}" if isinstance(r, Exception) else "Descargado. ¡Ya puedo pintar!"
            if que == "ampliador" and not isinstance(r, Exception):
                lbl_prog.text = "Ampliador descargado. Pulsa «Ampliar ×4»."
            refrescar()
        st["descarga"] = que
        en_hilo(lambda: pintor.descargar(que), fin)
        Clock.schedule_once(refrescar, 0.2)

    # ---------- pintar ----------
    def vigilar(_dt):
        barra.poner(st["progreso"])
        lbl_prog.text = st["texto"]
        if pintor.estado == "descargando":
            barra.poner(pintor.progreso)
            lbl_prog.text = f"Descargando… {pintor.progreso * 100:.0f} %"
            refrescar()
        try:
            m = os.path.getmtime(st["vista"]) if st["ocupado"] and os.path.isfile(st["vista"]) else 0
        except OSError:
            m = 0
        if m and m != st["vista_mtime"]:                   # vista previa: se va formando paso a paso
            st["vista_mtime"] = m
            mostrar(st["vista"])

    def al_progreso(f, texto):                             # llega desde el hilo del motor
        st["progreso"], st["texto"] = f, texto

    def pintar(descripcion=None, otra=False, al_terminar=None):
        if st["ocupado"]:
            pintor.cancelar()
            return False
        if otra and st["ultimo"]:
            descripcion = st["ultimo"]["descripcion"]
        descripcion = " ".join(str(descripcion if descripcion is not None else campo.text).split())
        if len(descripcion) < 2:
            lbl_prog.text = "Escribe qué quieres que pinte."
            return False
        campo.text = descripcion
        st.update(ocupado=True, progreso=0.0, texto="Pensando cómo pintarlo…", vista_mtime=0.0)
        try:
            if os.path.isfile(st["vista"]):
                os.remove(st["vista"])
        except OSError:
            pass
        refrescar()

        def trabajo():
            return core.pintar_imagen(descripcion, modelo=st["pincel"], formato=st["formato"],
                                      al_progreso=al_progreso, vista=st["vista"])

        def fin(r):
            st["ocupado"] = False
            if isinstance(r, Exception):
                st["texto"] = f"[x] {r}"
                barra.poner(0)
                lbl_prog.text = st["texto"]
                refrescar()
                if al_terminar:
                    al_terminar(None)
                return
            st["ultimo"] = dict(r, descripcion=descripcion)
            st["indice"] = 0
            st["progreso"], st["texto"] = 1.0, f"Pintada en {r['segundos']:.0f} s con el pincel " + \
                ("rápido" if r["modelo"] == "rapido" else "realista") + "."
            mostrar(r["ruta"], f"«{descripcion}» · semilla {r['semilla']}" + (f"\n{r['aviso']}" if r.get("aviso") else ""))
            if al_terminar:
                al_terminar(r)
        en_hilo(trabajo, fin)
        return True

    def ampliar():
        if not st["ruta"] or st["ocupado"]:
            return
        if not pintor.ampliador_instalado():
            descargar("ampliador")
            return
        ruta = st["ruta"]
        st.update(ocupado=True, progreso=0.0, texto="Ampliando ×4… (en el móvil tarda)")
        refrescar()

        def fin(r):
            st["ocupado"] = False
            if isinstance(r, Exception):
                st["texto"] = f"[x] {r}"
            else:
                st["progreso"], st["texto"] = 1.0, "Ampliada a 4 veces su tamaño."
                st["indice"] = 0
                mostrar(r, "Versión ampliada ×4.")
            refrescar()
        en_hilo(lambda: pintor.ampliar(ruta, al_progreso), fin)

    def a_galeria():
        if st["ruta"]:
            _ok, msg = pk.guardar_en_galeria(st["ruta"])
            lbl_prog.text = msg

    def borrar():
        if not st["ruta"]:
            return
        try:
            pintor.borrar_imagen(st["ruta"])
            lbl_prog.text = "Borrada."
        except (pk.PintorError, OSError) as e:
            lbl_prog.text = f"[x] {e}"
        lista = pintor.imagenes()
        st["indice"] = min(st["indice"], max(0, len(lista) - 1))
        mostrar(lista[st["indice"]] if lista else None, "" if lista else "Aún no has pintado nada.")

    def mover(paso):
        lista = pintor.imagenes()
        if not lista:
            return
        st["indice"] = max(0, min(len(lista) - 1, st["indice"] + paso))
        mostrar(lista[st["indice"]], os.path.basename(lista[st["indice"]]))

    def al_entrar():
        st["pincel"] = pintor.modelo if not st["ocupado"] else st["pincel"]
        if st["ruta"] is None:
            lista = pintor.imagenes()
            if lista:
                mostrar(lista[0], os.path.basename(lista[0]))
        refrescar()
        if st["reloj"] is None:
            st["reloj"] = Clock.schedule_interval(vigilar, 0.4)

    def al_salir():
        if st["reloj"] is not None and not st["ocupado"] and pintor.estado != "descargando":
            st["reloj"].cancel()
            st["reloj"] = None

    p["ganchos"]["pintor"] = al_entrar
    refrescar()
    return {"pintar": pintar, "al_salir": al_salir, "refrescar": refrescar}
