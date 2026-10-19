# -*- coding: utf-8 -*-
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

class KiraMainView(BoxLayout):
    def __init__(self, on_submit_callback=None, **kwargs):
        super(KiraMainView, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 15
        self.on_submit_callback = on_submit_callback

        # Título superior
        self.add_widget(Label(
            text='[KiraOS - Interfaz Móvil]',
            font_size=22,
            size_hint_y=None,
            height=40,
            color=(0.1, 0.8, 1, 1)
        ))

        # Área de registro de texto (Historial de comandos y respuestas)
        self.scroll = ScrollView(size_hint=(1, 1))
        self.output_label = Label(
            text='[✔] Sistema KiraOS inicializado y conectado.\nEscribe un comando abajo...\n',
            size_hint_y=None,
            halign='left',
            valign='top',
            color=(0.9, 0.9, 0.9, 1)
        )
        self.output_label.bind(texture_size=self.output_label.setter('size'))
        self.scroll.add_widget(self.output_label)
        self.add_widget(self.scroll)

        # Campo de entrada de texto para los comandos
        self.input_box = TextInput(
            text='',
            hint_text='Escribe un comando (ej: auditar, aprender: ...)',
            size_hint_y=None,
            height=50,
            multiline=False
        )
        self.input_box.bind(on_text_validate=self.enviar_comando)
        self.add_widget(self.input_box)

        # Botón de ejecución
        self.submit_btn = Button(
            text='Enviar al Núcleo',
            size_hint_y=None,
            height=50,
            background_color=(0.2, 0.6, 0.8, 1)
        )
        self.submit_btn.bind(on_press=self.enviar_comando)
        self.add_widget(self.submit_btn)

    def enviar_comando(self, instance):
        texto_cmd = self.input_box.text.strip()
        if not texto_cmd:
            return

        # Mostrar comando del usuario en pantalla
        self.output_label.text += f"\n> {texto_cmd}\n"
        self.input_box.text = ""

        # Enviar al callback (KiraGodCore) si está conectado
        if self.on_submit_callback:
            try:
                respuesta = self.on_submit_callback(texto_cmd)
                self.output_label.text += f"{respuesta}\n"
            except Exception as e:
                self.output_label.text += f"[x] Error ejecutando orden: {e}\n"
        else:
            self.output_label.text += "[x] Error: Núcleo no vinculado.\n"