# -*- coding: utf-8 -*-
"""
god_lab_link.py - Enlace REAL entre el laboratorio y el núcleo Kira_god (solo para probar en PC/Termux).

Antes decía "enlazado" sin importar nada. Ahora:
- Busca kira_god.py en la carpeta indicada, en la variable KIRA_GOD_DIR, en ../Kira_god o en la carpeta de arriba.
- Si no lo encuentra, lo dice claramente (no finge).
- El núcleo trabaja con sus datos en datos/god_datos (no toca los de tu móvil).
"""
import importlib.util
import os

from lab_rutas import RAIZ, carpeta_datos


def _buscar_kira_god(carpeta=None):
    candidatas = [carpeta, os.environ.get("KIRA_GOD_DIR"),
                  os.path.join(os.path.dirname(RAIZ), "Kira_god"), os.path.join(os.path.dirname(RAIZ), "kira_god"),
                  os.path.dirname(RAIZ)]           # el laboratorio DENTRO de la carpeta de Kira (como en GitHub)
    for c in candidatas:
        if c and os.path.isfile(os.path.join(c, "kira_god.py")):
            return os.path.abspath(c)
    return None


class GodLabLink:
    def __init__(self, carpeta_god=None):
        self.carpeta = _buscar_kira_god(carpeta_god)
        self.nucleo = None
        self.error = "" if self.carpeta else "No encuentro kira_god.py (define KIRA_GOD_DIR o deja Kira_god junto al laboratorio)."
        if self.carpeta:
            self._cargar()

    def _cargar(self):
        datos = os.path.join(carpeta_datos(), "god_datos")
        os.makedirs(datos, exist_ok=True)
        os.environ["KIRA_DATA_DIR"] = datos
        try:
            spec = importlib.util.spec_from_file_location("kira_god_enlazado", os.path.join(self.carpeta, "kira_god.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.nucleo = mod.KiraGodCore()
        except Exception as e:
            self.error = f"No se pudo cargar kira_god: {e}"

    @property
    def enlazado(self):
        return self.nucleo is not None

    def enviar_instruccion(self, texto: str) -> str:
        if not self.enlazado:
            return f"[x] Sin enlace con Kira_god. {self.error}"
        try:
            return str(self.nucleo.procesar_orden(str(texto)[:2000]))
        except Exception as e:
            return f"[x] El núcleo falló: {e}"


if __name__ == "__main__":
    enlace = GodLabLink()
    print("Enlazado" if enlace.enlazado else enlace.error)
    if enlace.enlazado:
        print(enlace.enviar_instruccion("estado"))
