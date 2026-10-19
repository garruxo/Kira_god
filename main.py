# -*- coding: utf-8 -*-
"""
Punto de entrada principal de KiraOS (main.py) - versión mejorada.

Cambios respecto a la anterior:
- Si el núcleo no carga, el error se MUESTRA (antes respondía "Simulación" en silencio).
- Los comandos se ejecutan en un hilo: la interfaz ya no se congela.
- El texto largo se ajusta al ancho de la pantalla.
- Se expone la carpeta de datos de Android en la variable KIRA_DATA_DIR,
  para que las mejoras aprobadas se guarden ahí (el código del APK es de solo lectura).
"""
import os
import sys
import threading
import traceback

# 1. Cargar el Núcleo Kira God, mostrando el error real si falla
CORE_ERROR = None
try:
    from kira_god import KiraGodCore
except Exception:
    CORE_ERROR = traceback.format_exc()

    class KiraGodCore:
        def __init__(self):
            print("[!] Núcleo NO cargado:\n" + str(CORE_ERROR))

        def procesar_orden(self, cmd):
            return "[x] El núcleo kira_god no se pudo cargar:\n" + str(CORE_ERROR)

# 2. Importar Kivy de forma aislada
KIVY_AVAILABLE = False
try:
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.textinput import TextInput
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView
    KIVY_AVAILABLE = True
except ImportError:
    pass


# 2b. Comandos de mejoras / pasarela (los gestiona main.py, NO el núcleo de Kira)
#     La aprobación sale de lo que escribe el usuario: el núcleo nunca recibe el promotor.
class ComandosMejoras:
    AYUDA = (
        "Comandos de mejoras:\n"
        "  config pasarela <url> <token>   guarda la conexión con el laboratorio\n"
        "  estado pasarela                 comprueba si el laboratorio responde\n"
        "  mejorar <lo que quieres>        Kira propone, el laboratorio prueba\n"
        "  APLICAR <id>                    aplica la mejora pendiente (frase exacta)\n"
        "  descartar                       descarta la mejora pendiente\n"
        "  revertir <modulo>               vuelve a la copia anterior\n"
        "  modulos                         lista los módulos instalados"
    )

    def __init__(self):
        self.pendiente = None
        self.error = None
        try:
            import pasarela_cliente as pc
            self.pc = pc
            self.promotor = pc.Promotor()
        except Exception:
            self.pc = None
            self.promotor = None
            self.error = traceback.format_exc()

    def manejar(self, texto, core):
        """Devuelve un texto si el comando es de mejoras; None si debe ir al núcleo."""
        t = texto.strip()
        bajo = t.lower()
        claves = ("config pasarela", "estado pasarela", "mejorar ", "aplicar ",
                  "descartar", "revertir ", "modulos", "ayuda mejoras")
        if not bajo.startswith(claves):
            return None
        if self.promotor is None:
            return "[x] Módulo pasarela_cliente no disponible:\n" + str(self.error)

        if bajo == "ayuda mejoras":
            return self.AYUDA

        if bajo.startswith("aplicar "):
            if not t.startswith("APLICAR "):
                return "Para aplicar escribe la frase exacta, en mayúsculas: APLICAR <id>"
            if not self.pendiente:
                return "No hay ninguna mejora pendiente."
            ok, msg = self.promotor.aplicar(self.pendiente, t)
            if ok or self.pendiente.usado:
                self.pendiente = None
            return ("[OK] " if ok else "[x] ") + msg

        if bajo == "descartar":
            self.pendiente = None
            return "Mejora pendiente descartada."

        if bajo.startswith("config pasarela"):
            partes = t.split()
            if len(partes) != 4:
                return "Uso: config pasarela <url> <token>"
            ruta = os.path.join(self.pc.carpeta_datos(), "pasarela.json")
            with open(ruta, "w", encoding="utf-8") as f:
                import json
                json.dump({"url": partes[2], "token": partes[3]}, f)
            self.promotor.pasarela = self.pc.PasarelaCliente()
            return "[OK] Pasarela guardada. Prueba con: estado pasarela"

        if bajo == "estado pasarela":
            p = self.promotor.pasarela
            if not p.url:
                return "[x] Pasarela sin configurar. Usa: config pasarela <url> <token>"
            try:
                import urllib.request
                with urllib.request.urlopen(p.url + "/salud", timeout=5) as r:
                    return "[OK] Laboratorio responde: " + r.read(200).decode("utf-8", "replace")
            except Exception as e:
                return f"[x] Laboratorio no alcanzable: {e}"

        if bajo == "modulos":
            nombres = sorted(f[:-3] for f in os.listdir(self.promotor.dir_modulos) if f.endswith(".py"))
            return "Módulos: " + (", ".join(nombres) if nombres else "(ninguno)")

        if bajo.startswith("revertir "):
            ok, msg = self.promotor.revertir(t.split(None, 1)[1].strip())
            return ("[OK] " if ok else "[x] ") + msg

        if bajo.startswith("mejorar "):
            gen = getattr(core, "generar_mejora", None)
            if not callable(gen):
                return ("[x] El núcleo no tiene generar_mejora(pedido) -> (nombre, codigo). "
                        "Hay que conectarlo en kira_god.py.")
            try:
                nombre, codigo = gen(t[8:].strip())
            except Exception as e:
                return f"[x] Kira no pudo generar la mejora: {e}"
            pend, err = self.promotor.preparar(nombre, codigo)
            if err:
                return "[x] " + err
            self.pendiente = pend
            return pend.resumen()
        return None


COMANDOS = ComandosMejoras()

# 3. Interfaz gráfica (solo si Kivy está disponible)
if KIVY_AVAILABLE:
    class KiraMainView(BoxLayout):
        def __init__(self, on_submit_callback=None, nucleo=None, **kwargs):
            super(KiraMainView, self).__init__(**kwargs)
            self.orientation = 'vertical'
            self.padding = 20
            self.spacing = 15
            self.on_submit_callback = on_submit_callback
            self.nucleo = nucleo
            self.ocupado = False

            self.add_widget(Label(
                text='[KiraOS - Interfaz Móvil]',
                font_size=22,
                size_hint_y=None,
                height=40,
                color=(0.1, 0.8, 1, 1)
            ))

            self.scroll = ScrollView(size_hint=(1, 1))
            self.output_label = Label(
                text='[OK] Sistema KiraOS inicializado con GUI.\n',
                size_hint_y=None,
                halign='left',
                valign='top',
                color=(0.9, 0.9, 0.9, 1)
            )
            # El texto se ajusta al ancho y la altura crece con el contenido
            self.output_label.bind(
                width=lambda inst, w: setattr(inst, 'text_size', (w, None)))
            self.output_label.bind(
                texture_size=lambda inst, ts: setattr(inst, 'height', ts[1]))
            self.scroll.add_widget(self.output_label)
            self.add_widget(self.scroll)

            self.input_box = TextInput(
                text='',
                hint_text='Escribe un comando...',
                size_hint_y=None,
                height=50,
                multiline=False
            )
            self.input_box.bind(on_text_validate=self.enviar_comando)
            self.add_widget(self.input_box)

            self.submit_btn = Button(
                text='Enviar al Núcleo',
                size_hint_y=None,
                height=50,
                background_color=(0.2, 0.6, 0.8, 1)
            )
            self.submit_btn.bind(on_press=self.enviar_comando)
            self.add_widget(self.submit_btn)

            if CORE_ERROR:
                self.output_label.text += (
                    "\n[x] AVISO: el núcleo no cargó.\n" + CORE_ERROR + "\n")

        def _mostrar(self, texto):
            self.output_label.text += f"{texto}\n"
            self.scroll.scroll_y = 0  # bajar al final

        def enviar_comando(self, instance):
            texto_cmd = self.input_box.text.strip()
            if not texto_cmd or self.ocupado:
                return
            visible = texto_cmd
            if texto_cmd.lower().startswith("config pasarela"):
                visible = " ".join(texto_cmd.split()[:3] + ["****"])
            elif texto_cmd.lower().startswith("config clave"):
                visible = "config clave: ****"
            self.output_label.text += f"\n> {visible}\n"
            self.input_box.text = ""
            if not self.on_submit_callback:
                return

            self.ocupado = True
            self.submit_btn.text = 'Procesando...'

            def trabajo():
                try:
                    respuesta = COMANDOS.manejar(texto_cmd, self.nucleo)
                    if respuesta is None:
                        respuesta = self.on_submit_callback(texto_cmd)
                except Exception as e:
                    respuesta = f"[x] Error: {e}"
                Clock.schedule_once(lambda dt: self._terminar(respuesta))

            threading.Thread(target=trabajo, daemon=True).start()

        def _terminar(self, respuesta):
            self._mostrar(respuesta)
            self.ocupado = False
            self.submit_btn.text = 'Enviar al Núcleo'

    class KiraApp(App):
        def build(self):
            # Carpeta escribible de la app (en Android el código del APK no se puede modificar)
            os.environ['KIRA_DATA_DIR'] = self.user_data_dir
            self.kira_god = KiraGodCore()
            consola = KiraMainView(on_submit_callback=self.kira_god.procesar_orden,
                                   nucleo=self.kira_god)
            try:  # interfaz inmersiva (orbe + menú); la consola de siempre queda dentro como "Consola"
                from interfaz_kira import construir_interfaz
                return construir_interfaz(self.kira_god, consola=consola)
            except Exception:
                print("[!] Interfaz inmersiva no disponible, se prueba el panel:\n" + traceback.format_exc())
            try:
                from panel_kira import construir_panel
                return construir_panel(self.kira_god, consola=consola)
            except Exception:
                print("[!] Panel no disponible, se usa la consola clásica:\n" + traceback.format_exc())
                return consola

        def on_pause(self):
            return True                       # al cambiar de app, Kira se pausa (no se cierra)

        def on_stop(self):
            for pieza in ("cerebro_propio", "oido"):
                try:
                    getattr(getattr(self, "kira_god", None), pieza).apagar()
                except Exception:
                    pass

# 4. Ejecución principal adaptativa
if __name__ == '__main__':
    if KIVY_AVAILABLE:
        print("[OK] Iniciando aplicación con interfaz gráfica (Kivy)...")
        KiraApp().run()
    else:
        print("[!] Kivy no está disponible en este entorno.")
        print("[*] Cambiando automáticamente a Modo Consola (CLI)...")
        core = KiraGodCore()
        if hasattr(core, 'run_permanent_loop'):
            core.run_permanent_loop()
        else:
            while True:
                cmd = input("Kira >>> ")
                if cmd.lower() == "salir":
                    break
                r = COMANDOS.manejar(cmd, core)
                print(r if r is not None else core.procesar_orden(cmd))
