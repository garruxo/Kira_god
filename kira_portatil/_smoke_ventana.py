# Prueba rápida de que la ventana de Kira se monta (se usa en GitHub con una pantalla virtual).
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kira_consola as kc
import kira_escritorio as ke

cli = kc.Cliente(os.environ.get("KIRA_URL", "http://localhost:8770"), os.environ.get("TOKEN", "x" * 32))
raiz = ke.construir(cli)
raiz.update()
raiz.update_idletasks()
assert raiz.winfo_children(), "la ventana no tiene nada dentro"
raiz.destroy()
print("VENTANA OK")
