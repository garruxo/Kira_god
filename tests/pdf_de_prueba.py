# -*- coding: utf-8 -*-
"""Hace PDF de verdad (pequeños) para las pruebas, sin librerías: texto en Helvetica, una lista de líneas por página."""


def _esc(t):
    return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def hacer_pdf(paginas, titulo="Documento de prueba"):
    objs = {}
    n_pag = len(paginas)
    ids_pag = [4 + 2 * i for i in range(n_pag)]
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = ("<< /Type /Pages /Kids [" + " ".join(f"{i} 0 R" for i in ids_pag) + f"] /Count {n_pag} >>").encode()
    objs[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    for i, lineas in enumerate(paginas):
        pid, cid = ids_pag[i], ids_pag[i] + 1
        if isinstance(lineas, str):
            lineas = lineas.split("\n")
        flujo = b"BT /F1 11 Tf 50 780 Td 14 TL\n" + b"".join(b"(" + _esc(l).encode("cp1252") + b") Tj T*\n" for l in lineas) + b"ET"
        objs[pid] = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> "
                     f"/Contents {cid} 0 R >>").encode()
        objs[cid] = f"<< /Length {len(flujo)} >>\nstream\n".encode() + flujo + b"\nendstream"
    info = 4 + 2 * n_pag
    objs[info] = b"<< /Title (" + _esc(titulo).encode("cp1252") + b") /Author (Kira) >>"
    sal = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    pos = {}
    for k in sorted(objs):
        pos[k] = len(sal)
        sal += f"{k} 0 obj\n".encode() + objs[k] + b"\nendobj\n"
    xref = len(sal)
    total = max(objs) + 1
    sal += f"xref\n0 {total}\n0000000000 65535 f \n".encode()
    for k in range(1, total):
        sal += f"{pos[k]:010d} 00000 n \n".encode()
    sal += f"trailer\n<< /Size {total} /Root 1 0 R /Info {info} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(sal)
