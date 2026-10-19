# -*- coding: utf-8 -*-
"""
vista_kira.py - Kira VE TU PANTALLA cuando se lo pides, y SIEMPRE ACTIVA en segundo plano. Todo dentro del móvil.

  - Siempre activa: un servicio en primer plano (android_src/org/kira/servicio/ServicioKira.java) con su
    notificación fija; así puede seguir oyendo «Kira…» mientras usas otras apps.
  - Ver la pantalla: Android te pide permiso («¿Permitir que Kira capture la pantalla?»). Mientras lo tenga, sale la
    notificación y el icono de captura. Kira solo mira cuando se lo pides («Kira, ¿qué ves?»), lee el texto con su
    lector (lector_kira) y BORRA la captura.
  - Apps privadas: si la app que tienes delante está en la lista, Kira NO mira. «no mires esta app» la añade (hace
    falta el permiso «Acceso a datos de uso» para saber qué app es). Las apps de bancos ya salen en negro por Android.
La lista y la lógica son puras (se prueban en el PC); lo de Android va por el objeto 'java'.
"""
import json
import os

PRIVADAS_DEFECTO = [
    "com.whatsapp", "com.whatsapp.w4b", "org.telegram.messenger", "org.thoughtcrime.securesms",
    "com.google.android.gm", "com.google.android.apps.photos", "com.google.android.apps.messaging",
    "com.android.vending", "com.google.android.apps.walletnfcrel",
]
CODIGO_PERMISO = 4712


class VistaError(RuntimeError):
    pass


class JavaAndroid:
    """Puente con el servicio Java (solo en Android)."""

    def __init__(self):
        from jnius import autoclass
        self.Servicio = autoclass("org.kira.servicio.ServicioKira")
        self.actividad = autoclass("org.kivy.android.PythonActivity").mActivity
        self.paquete = str(self.actividad.getPackageName())

    def iniciar(self, pantalla=False):
        self.Servicio.iniciar(self.actividad, bool(pantalla))

    def detener(self):
        self.Servicio.detener(self.actividad)

    def activo(self):
        return bool(self.Servicio.activo())

    def puede_ver(self):
        return bool(self.Servicio.puedeVer())

    def pedir_permiso(self, al_resultado):
        from android import activity

        def resultado(codigo, resultado_, datos):
            if codigo != CODIGO_PERMISO:
                return
            activity.unbind(on_activity_result=resultado)
            if resultado_ == -1 and datos is not None:           # RESULT_OK
                self.Servicio.iniciarPantalla(self.actividad, resultado_, datos)
                al_resultado(True)
            else:
                al_resultado(False)
        activity.bind(on_activity_result=resultado)
        self.actividad.startActivityForResult(self.Servicio.pedirPermisoPantalla(self.actividad), CODIGO_PERMISO)

    def capturar(self, ruta):
        return bool(self.Servicio.capturar(ruta))

    def app_actual(self):
        p = self.Servicio.appEnPrimerPlano(self.actividad)
        return str(p) if p else None

    def acceso_uso(self):
        return bool(self.Servicio.tieneAccesoUso(self.actividad))

    def abrir_ajustes_uso(self):
        from jnius import autoclass
        Intent, Settings = autoclass("android.content.Intent"), autoclass("android.provider.Settings")
        self.actividad.startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS))


def java_android():
    try:
        return JavaAndroid()
    except Exception:
        return None


class Vista:
    def __init__(self, dir_datos, java=None):
        self.carpeta = os.path.join(dir_datos, "vista")
        self.ruta_cfg = os.path.join(dir_datos, "vista.json")
        self.java = java
        cfg = {}
        try:
            with open(self.ruta_cfg, encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, ValueError):
            pass
        cfg = cfg if isinstance(cfg, dict) else {}
        lista = cfg.get("privadas")
        self.privadas = [str(x) for x in lista if isinstance(x, str)] if isinstance(lista, list) else list(PRIVADAS_DEFECTO)
        self.siempre_activa = cfg.get("siempre_activa", False) is True

    def _guardar(self):
        tmp = self.ruta_cfg + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"privadas": self.privadas, "siempre_activa": self.siempre_activa}, f, ensure_ascii=False)
        os.replace(tmp, self.ruta_cfg)

    def disponible(self):
        return self.java is not None

    # ---------- siempre activa ----------
    def poner_siempre_activa(self, si):
        self.siempre_activa = bool(si)
        self._guardar()
        if self.java is None:
            return False
        if si:
            self.java.iniciar(pantalla=False)
        elif not self.java.puede_ver():
            self.java.detener()
        return True

    # ---------- apps privadas ----------
    def es_privada(self, paquete):
        return bool(paquete) and paquete in self.privadas

    def anadir_privada(self, paquete):
        if paquete and paquete not in self.privadas:
            self.privadas.append(paquete)
            self._guardar()
            return True
        return False

    def quitar_privada(self, paquete):
        if paquete in self.privadas:
            self.privadas.remove(paquete)
            self._guardar()
            return True
        return False

    def app_actual(self):
        if self.java is None:
            return None
        try:
            return self.java.app_actual()
        except Exception:
            return None

    # ---------- mirar ----------
    def puede_ver(self):
        try:
            return self.java is not None and self.java.puede_ver()
        except Exception:
            return False

    def mirar(self, lector):
        """Captura la pantalla, la lee y BORRA la captura. Devuelve (texto, app). Bloquea: úsalo en un hilo."""
        if self.java is None:
            raise VistaError("Ver la pantalla solo funciona en el móvil.")
        if not self.puede_ver():
            raise VistaError("Primero dame permiso para ver la pantalla: Menú > Cerebro y oído > «Dejar que Kira vea "
                             "la pantalla».")
        app = self.app_actual()
        propia = getattr(self.java, "paquete", None)
        if app and app != propia and self.es_privada(app):
            raise VistaError("Esa app está en tu lista de apps privadas: no miro.")
        os.makedirs(self.carpeta, exist_ok=True)
        ruta = os.path.join(self.carpeta, "pantalla.png")
        try:
            if not self.java.capturar(ruta):
                raise VistaError("No he podido capturar la pantalla (¿quitaste el permiso?).")
            texto = lector.leer(ruta)
        finally:
            if os.path.exists(ruta):
                os.remove(ruta)                                  # la captura no se guarda nunca
        return texto, app
