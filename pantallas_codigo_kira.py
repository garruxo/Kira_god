# -*- coding: utf-8 -*-
"""
pantallas_codigo_kira.py - Pantallas (Kivy) del EDITOR DE CÓDIGO, la lista de JUEGOS y la pantalla para JUGAR.
La lógica está en ejecutor_kira (ejecutar en modo seguro), motor_juegos_kira (motor 2D) y juegos_kira (juegos).
"""
import os

import curso_avanzado_kira as ca
import ejecutor_kira as ej
import juegos_kira as jk
import motor_juegos_kira as mj
import programacion_kira as pk


def montar_codigo(sm, p):
    """p: piezas de la interfaz (boton, entrada, texto_largo, en_hilo, pantalla, ir, colores, dir_datos, ganchos)."""
    from kivy.clock import Clock
    from kivy.core.text import Label as CoreLabel
    from kivy.graphics import Color, Ellipse, Line, Mesh, Rectangle
    from kivy.metrics import dp, sp
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.textinput import TextInput
    from kivy.uix.widget import Widget

    boton, entrada, texto_largo, en_hilo, pantalla, ir = (p[k] for k in ("boton", "entrada", "texto_largo", "en_hilo",
                                                                          "pantalla", "ir"))
    TXT, TENUE, GRIS, VERDE, ROJO, FUENTE = (p[k] for k in ("TXT", "TENUE", "GRIS", "VERDE", "ROJO", "FUENTE"))
    programas = ej.Programas(os.path.join(p["dir_datos"], "programas"))
    ganchos = p["ganchos"]

    # =================================================================================
    #  EDITOR
    # =================================================================================
    _, c_ed = pantalla("editor_codigo", "EDITOR DE CÓDIGO")
    fila_nom = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
    campo_nombre = entrada("nombre_del_programa")
    fila_nom.add_widget(campo_nombre)
    fila_nom.add_widget(boton("Guardar", lambda: guardar(), VERDE, size_hint_x=None, width=dp(96)))
    c_ed.add_widget(fila_nom)
    codigo = TextInput(text="", multiline=True, size_hint_y=0.48, font_size=sp(14), **FUENTE,
                       background_color=(1, 1, 1, 1), foreground_color=TXT, cursor_color=(0, 0.5, 0.8, 1),
                       hint_text="Escribe aquí tu programa de Python…", hint_text_color=TENUE,
                       write_tab=False, do_wrap=False)
    c_ed.add_widget(codigo)
    campo_entrada = entrada("Entrada para input() (separa con ; si son varias)")
    c_ed.add_widget(campo_entrada)
    fila1 = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
    fila1.add_widget(boton("Ejecutar", lambda: ejecutar(), VERDE))
    fila1.add_widget(boton("Jugar", lambda: jugar_editor(), VERDE))
    fila1.add_widget(boton("Comprobar", lambda: comprobar(), GRIS))
    c_ed.add_widget(fila1)
    fila2 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    fila2.add_widget(boton("Abrir…", lambda: abrir_lista("mios"), GRIS, alto=44))
    fila2.add_widget(boton("Ejemplos…", lambda: abrir_lista("ejemplos"), GRIS, alto=44))
    fila2.add_widget(boton("Nuevo", lambda: nuevo(), GRIS, alto=44))
    c_ed.add_widget(fila2)
    sv_sal, salida = texto_largo("Escribe un programa y pulsa «Ejecutar». Modo seguro: sin archivos, red ni sistema; "
                                 "se corta a los 5 segundos.")
    c_ed.add_widget(sv_sal)

    def cargar_en_editor(texto, nombre="", aviso=""):
        codigo.text = texto
        campo_nombre.text = nombre
        salida.text = aviso or "Listo. Pulsa «Ejecutar» (o «Jugar» si es un juego)."
        ir("editor_codigo")

    def nuevo():
        codigo.text, campo_nombre.text = "", ""
        salida.text = "Programa nuevo."

    def comprobar():
        m = ej.revisar(codigo.text)
        salida.text = "[OK] Correcto: se puede ejecutar en modo seguro." if m is None else "[x] " + m

    def ejecutar():
        texto = codigo.text
        entrada_txt = "\n".join(x.strip() for x in campo_entrada.text.split(";")) if campo_entrada.text else ""
        salida.text = "Ejecutando…"
        en_hilo(lambda: ej.ejecutar(texto, entrada=entrada_txt),
                lambda r: setattr(salida, "text", f"[x] {r}" if isinstance(r, Exception) else
                                  (r["salida"] or "(no imprimió nada)") + (f"\n\n[x] {r['error']}" if r["error"] else
                                                                            f"\n\n[OK] Terminado en {r['segundos']} s")))

    def guardar():
        try:
            n = programas.guardar(campo_nombre.text, codigo.text)
        except (ValueError, OSError) as e:
            salida.text = f"[x] {e}"
            return
        campo_nombre.text = n
        salida.text = f"[OK] Guardado como «{n}». Lo tienes en «Abrir…»."

    def jugar_editor():
        empezar_juego(codigo.text, volver="editor_codigo")

    # =================================================================================
    #  LISTA PARA ABRIR (mis programas, ejemplos del curso y juegos)
    # =================================================================================
    _, c_lis = pantalla("abrir_codigo", "ABRIR")
    titulo_lis = Label(text="", size_hint_y=None, height=dp(28), color=TENUE, font_size=sp(13), **FUENTE)
    c_lis.add_widget(titulo_lis)
    sv_lis = ScrollView(do_scroll_x=False)
    lista = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
    lista.bind(minimum_height=lista.setter("height"))
    sv_lis.add_widget(lista)
    c_lis.add_widget(sv_lis)

    def abrir_lista(que):
        lista.clear_widgets()
        if que == "mios":
            nombres = programas.listar()
            titulo_lis.text = f"Tus programas ({len(nombres)})" if nombres else "Aún no has guardado programas."
            for n in nombres:
                fila = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
                fila.add_widget(boton(n, lambda n_=n: cargar_en_editor(programas.abrir(n_) or "", n_), GRIS))
                fila.add_widget(boton("Borrar", lambda n_=n: (programas.borrar(n_), abrir_lista("mios")), ROJO,
                                      size_hint_x=None, width=dp(84)))
                lista.add_widget(fila)
        else:
            titulo_lis.text = "Ejemplos: curso básico, avanzado, códigos y juegos (se abren para que los cambies)"
            grupos = [("Básico", pk.CURSO), ("Avanzado", ca.CURSO_AVANZADO), ("Código", ca.CODIGOS)]
            for etiqueta, items in grupos:
                for l in items:
                    lista.add_widget(boton(f"[{etiqueta}] {l['titulo']}", lambda l_=l: cargar_en_editor(
                        l_["codigo"], "", f"{l_['titulo']}: {l_['texto']}"), GRIS, alto=44))
            for j in jk.JUEGOS + [{"id": "mi_juego", "titulo": "Plantilla para tu juego", "codigo": jk.PLANTILLA}]:
                lista.add_widget(boton(f"[Juego] {j['titulo']}", lambda j_=j: cargar_en_editor(
                    j_["codigo"], j_["id"] + "_mio", "Es un juego: pulsa «Jugar». Cámbialo y guárdalo como tuyo."), GRIS, alto=44))
        ir("abrir_codigo")

    # =================================================================================
    #  JUEGOS
    # =================================================================================
    _, c_jue = pantalla("juegos", "JUEGOS")
    c_jue.add_widget(Label(text="Juegos hechos con el motor de Kira. Todos son programas: ábrelos y cámbialos.",
                           size_hint_y=None, height=dp(40), color=TENUE, font_size=sp(13), **FUENTE))
    sv_j = ScrollView(do_scroll_x=False)
    lista_j = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
    lista_j.bind(minimum_height=lista_j.setter("height"))
    sv_j.add_widget(lista_j)
    c_jue.add_widget(sv_j)

    def pintar_juegos():
        lista_j.clear_widgets()
        for j in jk.JUEGOS:
            fila = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(6))
            fila.add_widget(boton(j["titulo"], lambda j_=j: empezar_juego(j_["codigo"], volver="juegos"), VERDE, alto=56))
            fila.add_widget(boton("Código", lambda j_=j: cargar_en_editor(j_["codigo"], j_["id"] + "_mio",
                                  "Cámbialo y pulsa «Jugar». Guárdalo para tenerlo como tuyo."), GRIS, alto=56,
                                  size_hint_x=None, width=dp(96)))
            lista_j.add_widget(fila)
        mios = [n for n in programas.listar() if "Juego" in (programas.abrir(n) or "")]
        for n in mios:
            lista_j.add_widget(boton("(tuyo) " + n, lambda n_=n: empezar_juego(programas.abrir(n_) or "", volver="juegos"),
                                     GRIS, alto=50))
        for nombre, accion in p.get("juegos_extra", lambda: [])():
            lista_j.add_widget(boton("(mejora) " + nombre, accion, GRIS, alto=50))
        lista_j.add_widget(boton("+ Programar un juego nuevo", lambda: cargar_en_editor(
            jk.PLANTILLA, "mi_juego", "Plantilla de juego: pulsa «Jugar» para probarla y luego cámbiala."), GRIS, alto=50))
    ganchos["juegos"] = pintar_juegos

    # =================================================================================
    #  JUGAR
    # =================================================================================
    class JuegoWidget(Widget):
        def __init__(self, **kw):
            super().__init__(**kw)
            self.juego = None
            self._textos = {}
            self._previo = None

        def escala(self):
            g = self.juego
            s = min(self.width / g.ancho, self.height / g.alto)
            return s, self.x + (self.width - g.ancho * s) / 2, self.y + (self.height - g.alto * s) / 2

        def a_juego(self, x, y):
            s, ox, oy = self.escala()
            return (x - ox) / s, (y - oy) / s

        def textura(self, texto, tam):
            clave = (texto, tam)
            if clave not in self._textos:
                if len(self._textos) > 200:
                    self._textos.clear()
                lb = CoreLabel(text=texto, font_size=tam)
                lb.refresh()
                self._textos[clave] = lb.texture
            return self._textos[clave]

        def dibujar(self):
            g = self.juego
            if g is None or self.width < 10:
                return
            s, ox, oy = self.escala()
            self.canvas.clear()
            with self.canvas:
                Color(*mj.color(g.fondo))
                Rectangle(pos=(ox, oy), size=(g.ancho * s, g.alto * s))
                for forma, x, y, w, h, col, texto, tam, puntos in g.dibujo():
                    Color(*col)
                    if forma == "rect":
                        Rectangle(pos=(ox + x * s, oy + y * s), size=(w * s, h * s))
                    elif forma == "circulo":
                        Ellipse(pos=(ox + (x - w / 2) * s, oy + (y - h / 2) * s), size=(w * s, h * s))
                    elif forma == "linea" and len(puntos) >= 2:
                        Line(points=[v for px, py in puntos for v in (ox + px * s, oy + py * s)], width=max(1.0, tam * s / 2))
                    elif forma == "poligono" and len(puntos) >= 3:
                        cx, cy = ox + x * s, oy + y * s                  # abanico desde el centro
                        vs = [cx, cy, 0, 0]
                        for px, py in puntos + puntos[:1]:
                            vs += [ox + px * s, oy + py * s, 0, 0]
                        Mesh(vertices=vs, indices=list(range(len(vs) // 4)), mode="triangle_fan")
                    elif forma == "texto" and texto:
                        tx = self.textura(texto, max(8, int(tam * s)))
                        Rectangle(texture=tx, pos=(ox + x * s, oy + y * s), size=tx.size)

        def on_touch_down(self, t):
            if self.juego and self.collide_point(*t.pos):
                self._previo = self.a_juego(t.x, t.y)
                self.juego.tocar(*self._previo)
                return True
            return super().on_touch_down(t)

        def on_touch_move(self, t):
            if self.juego and self._previo is not None:
                x, y = self.a_juego(t.x, t.y)
                self.juego.mover_dedo(x, y, x - self._previo[0], y - self._previo[1])
                if abs(x - self._previo[0]) + abs(y - self._previo[1]) > 25:   # deslizamientos cortos y claros
                    self._previo = (x, y)
                return True
            return False

        def on_touch_up(self, t):
            if self.juego and self._previo is not None:
                self._previo = None
                self.juego.soltar(*self.a_juego(t.x, t.y))
                return True
            return False

    p_jug, c_jug = pantalla("jugar", "JUGANDO")
    marcador = Label(text="", size_hint_y=None, height=dp(30), color=TXT, font_size=sp(14), **FUENTE)
    c_jug.add_widget(marcador)
    vista = JuegoWidget()
    c_jug.add_widget(vista)
    fila_j = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
    fila_j.add_widget(boton("Pausa", lambda: vista.juego and vista.juego.pausar(), GRIS, alto=46))
    fila_j.add_widget(boton("Reiniciar", lambda: vista.juego and vista.juego.reiniciar(), GRIS, alto=46))
    fila_j.add_widget(boton("Salir", lambda: salir_juego(), ROJO, alto=46))
    c_jug.add_widget(fila_j)
    est = {"reloj": None, "volver": "juegos"}

    def fotograma(dt):
        g = vista.juego
        if g is None:
            return
        try:
            ej.con_limite(g.paso, 0.25, dt)                # un fotograma no puede colgar la app
        except ej.TiempoAgotado:
            parar("[x] El juego se quedó colgado en un fotograma (¿un bucle infinito en actualizar?).")
            return
        except Exception as e:
            parar(f"[x] Error en el juego: {type(e).__name__}: {e}")
            return
        marcador.text = g.marcador()
        vista.dibujar()

    def parar(mensaje=""):
        if est["reloj"] is not None:
            est["reloj"].cancel()
            est["reloj"] = None
        if mensaje:
            marcador.text = mensaje

    def empezar_juego(codigo_juego, volver="juegos", juego=None):
        if juego is None:
            juego, error = jk.cargar(codigo_juego)
            if error:
                if volver == "editor_codigo":
                    salida.text = "[x] " + error
                    ir("editor_codigo")
                else:
                    marcador.text = "[x] " + error
                return False
        parar()
        vista.juego = juego
        est["volver"] = volver
        marcador.text = juego.instrucciones or juego.titulo
        ir("jugar")
        est["reloj"] = Clock.schedule_interval(fotograma, 1 / 60.0)
        return True

    def salir_juego():
        parar()
        ir(est["volver"])

    ganchos["jugar"] = lambda: None
    return {"cargar_en_editor": cargar_en_editor, "empezar_juego": empezar_juego, "parar_juego": parar,
            "abrir_lista": abrir_lista, "vista": vista, "programas": programas}
