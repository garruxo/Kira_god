# -*- coding: utf-8 -*-
"""
camara_kira.py - Kira MIRA CON LA CÁMARA cuando se lo pides. Todo dentro del móvil.

  - «Kira, lee este papel» / «lee con la cámara»: hace una foto (sin abrir ninguna app de cámara), lee el texto con su
    lector (lector_kira) y BORRA la foto.
  - «Kira, ¿qué tengo delante?» / «describe lo que ves»: con sus OJOS (visión local, ojos de cerebro_propio_kira)
    describe la foto; sin ojos, te dice el texto que haya y cómo conseguirlos.
  - «con la cámara de delante» (o «frontal», «selfie») usa la delantera; si no, la de atrás.
La foto nunca se guarda ni sale del móvil. Android solo deja usar la cámara con Kira abierta en pantalla.
La parte de Android va por el objeto 'java' (JavaCamara); la lógica se prueba en el PC con uno falso.
"""
import os
import re

MAX_LADO = 1600                       # basta para leer texto y no llena la memoria


class CamaraError(RuntimeError):
    pass


class JavaCamara:
    """Puente con android_src/org/kira/servicio/CamaraKira.java (solo en Android)."""

    def __init__(self):
        from jnius import autoclass                     # se busca en el hilo principal (cargador de la app)
        self.Camara = autoclass("org.kira.servicio.CamaraKira")
        self.actividad = autoclass("org.kivy.android.PythonActivity").mActivity

    def tiene_permiso(self):
        return bool(self.Camara.tienePermiso(self.actividad))

    def pedir_permiso(self, al_resultado=None):
        from android.permissions import Permission, request_permissions
        request_permissions([Permission.CAMERA],
                            (lambda _p, r: al_resultado(bool(r and r[0]))) if al_resultado else None)

    def hay_camara(self, trasera=True):
        return bool(self.Camara.hayCamara(self.actividad, bool(trasera)))

    def foto(self, ruta, trasera=True, max_lado=MAX_LADO):
        return str(self.Camara.foto(self.actividad, ruta, bool(trasera), int(max_lado)) or "")


def java_camara():
    try:
        return JavaCamara()
    except Exception:
        return None


def quiere_delantera(texto):
    return bool(re.search(r"\b(delante|delantera|frontal|selfie|de frente)\b", str(texto or "").lower()))


class Camara:
    def __init__(self, dir_datos, java=None):
        self.carpeta = os.path.join(dir_datos, "camara")
        self.java = java
        self.primer_plano = lambda: True             # lo cambia la app: Android no deja la cámara en segundo plano

    def disponible(self):
        return self.java is not None

    def tiene_permiso(self):
        try:
            return self.java is not None and self.java.tiene_permiso()
        except Exception:
            return False

    def _con_foto(self, trasera, usar):
        """Hace la foto, llama a usar(ruta) y BORRA la foto pase lo que pase. Bloquea: úsalo en un hilo."""
        if self.java is None:
            raise CamaraError("La cámara solo funciona en el móvil.")
        if not self.primer_plano():
            raise CamaraError("Para usar la cámara, abre Kira en la pantalla (Android no la deja en segundo plano).")
        if not self.tiene_permiso():
            raise CamaraError("Necesito permiso para la cámara: Menú › Cerebro y oído › «Permiso de cámara».")
        os.makedirs(self.carpeta, exist_ok=True)
        ruta = os.path.join(self.carpeta, "foto.jpg")
        try:
            fallo = self.java.foto(ruta, trasera)
            if fallo or not os.path.isfile(ruta) or os.path.getsize(ruta) < 100:
                raise CamaraError("No pude hacer la foto: " + (fallo or "la cámara no devolvió nada") + ".")
            return usar(ruta)
        finally:
            if os.path.exists(ruta):
                os.remove(ruta)                          # la foto no se guarda nunca

    def leer(self, lector, trasera=True):
        """Texto de lo que enfoca la cámara (un papel, una pantalla, un cartel…)."""
        return self._con_foto(trasera, lector.leer)

    def describir(self, ojos, pregunta="", trasera=True):
        """Lo que ve la cámara, contado por sus ojos (visión local). ojos(ruta, pregunta) -> texto."""
        p = pregunta or "Describe de forma clara y breve lo que se ve en esta foto. Si hay texto, léelo."
        return self._con_foto(trasera, lambda ruta: ojos(ruta, p))
