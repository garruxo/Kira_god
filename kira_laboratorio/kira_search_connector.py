# -*- coding: utf-8 -*-
"""
kira_search_connector.py - Conector de búsqueda (HONESTO: aún NO busca en internet).

La versión anterior envolvía un texto y decía "integrado en el taller" sin buscar nada.
Esta solo prepara una consulta como PROPUESTA de texto para que la revises tú. Para búsqueda real,
el siguiente paso sería una función con tu confirmación y una API concreta.
"""


class KiraSearchConnector:
    def preparar_consulta(self, tema: str) -> str:
        tema = " ".join(str(tema).split())[:200]
        if not tema:
            return "[x] Indica un tema."
        return f"[i] Consulta preparada (NO ejecutada): '{tema}'. Este conector todavía no accede a internet."


if __name__ == "__main__":
    print(KiraSearchConnector().preparar_consulta("ejemplo"))
