# -*- coding: utf-8 -*-
"""
kira_master.py - Consola del laboratorio. Escribe 'ayuda' para ver las órdenes.
Las órdenes desconocidas ahora se rechazan (antes se aceptaban en silencio).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

AYUDA = """Órdenes:
  zona <archivador|escritorio|taller>     filtro <brightness|contrast|hue-rotate> <valor>
  escanear                                 inventario de datos/
  diagnostico                              comprobaciones reales del laboratorio
  optimizar [simular]                      limpia logs/temporales antiguos (simular = solo mostrar)
  ejecutar <script.py>                     ejecuta datos/<script.py> en el sandbox
  propuestas                               lista mejoras pendientes
  verificar                                comprueba el sello de integridad
  sellar SELLAR NUCLEO                     guarda el sello (hazlo tras revisar el código)
  enlace <orden>                           envía una orden a Kira_god (si está al lado)
  ayuda | salir"""


class KiraMaster:
    def __init__(self):
        from studio_core import KiraStudioRoom
        from kira_registry import KiraRegistry
        from kira_optimizer import KiraOptimizer
        from kira_sandbox import KiraSandbox
        from kira_evolver import KiraEvolver
        from labor_memory import KiraMemory
        self.estudio, self.registro = KiraStudioRoom(), KiraRegistry()
        self.optimizador, self.sandbox = KiraOptimizer(), KiraSandbox()
        self.evolver, self.memoria = KiraEvolver(), KiraMemory()
        self.enlace = None

    def ejecutar_comando(self, linea: str) -> str:
        partes = str(linea).strip().split()
        if not partes:
            return ""
        cmd, args = partes[0].lower(), partes[1:]
        self.memoria.registrar_evento("comando", cmd)
        if cmd == "ayuda":
            return AYUDA
        if cmd == "zona":
            return self.estudio.cambiar_zona(args[0] if args else "")
        if cmd == "filtro":
            return self.estudio.ajustar_regulador_remoto(args[0] if args else "", args[1] if len(args) > 1 else None)
        if cmd == "escanear":
            inv = self.registro.escanear_laboratorio()
            return "Inventario: " + ", ".join(f"{k}={len(v)}" for k, v in inv.items() if k != "huellas")
        if cmd == "diagnostico":
            import kira_diagnostico
            res = kira_diagnostico.comprobar()
            return "\n".join(f"[{'OK' if ok else 'FALLA'}] {n}: {d}" for n, ok, d in res)
        if cmd == "optimizar":
            return self.optimizador.purgar_logs_temporales(simular=bool(args and args[0].lower() == "simular"))
        if cmd == "ejecutar":
            return self.sandbox.ejecutar_script_seguro(args[0]) if args else "[x] Indica un script."
        if cmd == "propuestas":
            p = self.evolver.listar_propuestas()
            return "Propuestas: " + (", ".join(p) if p else "ninguna")
        if cmd == "verificar":
            return self.registro.verificar_integridad()["mensaje"]
        if cmd == "sellar":
            return self.registro.sellar_nucleo(" ".join(args))
        if cmd == "enlace":
            if self.enlace is None:
                from god_lab_link import GodLabLink
                self.enlace = GodLabLink()
            return self.enlace.enviar_instruccion(" ".join(args))
        return f"[x] Orden desconocida: '{cmd[:30]}'. Escribe 'ayuda'."


def main():
    k = KiraMaster()
    print("Laboratorio Kira. 'ayuda' para ver las órdenes.")
    while True:
        try:
            linea = input("lab> ")
        except (EOFError, KeyboardInterrupt):
            break
        if linea.strip().lower() in ("salir", "exit"):
            break
        out = k.ejecutar_comando(linea)
        if out:
            print(out)


if __name__ == "__main__":
    main()
