# -*- coding: utf-8 -*-
"""kira_cli.py - Atajo de una sola orden:  python kira_cli.py zona taller   |   python kira_cli.py diagnostico"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python kira_cli.py <orden> [argumentos]   (orden 'ayuda' para ver todas)")
    from kira_master import KiraMaster
    print(KiraMaster().ejecutar_comando(" ".join(sys.argv[1:])))
