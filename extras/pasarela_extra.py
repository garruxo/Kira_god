# -*- coding: utf-8 -*-
"""
pasarela_extra.py - Pasarela HTTP para el cerebro auxiliar (NO va en el APK). Sustituye a
secure_gateway.py y curite_gateway.py, que tenían el token escrito en el código y lo servían en una página.

Uso:   export KIRA_GATEWAY_TOKEN="un-token-largo-y-aleatorio"      (mínimo 16 caracteres)
       python pasarela_extra.py                  (solo 127.0.0.1:8000; no hay opción de abrirla a la red)

- Token SOLO por variable de entorno, comparado en tiempo constante. Sin token válido: 401.
- GET /salud es lo único público y no revela nada. No se sirve ninguna página.
- POST /tarea  {"task_type": "...", "prompt": "..."}  con cabecera  Authorization: Bearer <token>
- Los sensores (cámara, GPS, pantalla) están desactivados y no se pueden activar por esta vía.
"""
import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from master_brain import KiraMasterBrain

TOKEN = os.environ.get("KIRA_GATEWAY_TOKEN", "")
MAX_BODY = 20_000
cerebro = None


class Handler(BaseHTTPRequestHandler):
    def _json(self, codigo, obj):
        datos = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        self._json(200, {"ok": True}) if self.path == "/salud" else self._json(404, {"ok": False})

    def do_POST(self):
        if self.path != "/tarea":
            return self._json(404, {"ok": False})
        enviado = self.headers.get("Authorization", "")
        if not hmac.compare_digest(enviado, "Bearer " + TOKEN):
            return self._json(401, {"ok": False, "error": "token no válido"})
        try:
            largo = int(self.headers.get("Content-Length", "0"))
            if not 0 < largo <= MAX_BODY:
                return self._json(413, {"ok": False, "error": "tamaño no válido"})
            datos = json.loads(self.rfile.read(largo).decode("utf-8"))
            prompt, tipo = str(datos.get("prompt", "")), str(datos.get("task_type", "")).lower()
        except Exception:
            return self._json(400, {"ok": False, "error": "petición mal formada"})
        if tipo in ("programa", "codigo"):
            r = cerebro.generar_programa(prompt)
        elif tipo in ("diseno", "grafico"):
            r = cerebro.procesar_diseno(prompt)
        elif tipo in ("audio", "voz"):
            r = cerebro.sintetizar_audio(prompt)
        else:
            r = cerebro.process_universal_order(prompt)
        self._json(200, {"ok": True, "result": r})

    def log_message(self, fmt, *args):
        sys.stderr.write("[pasarela] " + fmt % args + "\n")


def main(puerto=8000):
    global cerebro
    if len(TOKEN) < 16:
        sys.exit("Define KIRA_GATEWAY_TOKEN con al menos 16 caracteres antes de arrancar.")
    cerebro = KiraMasterBrain(permitir_sensores=False, voz=False)
    print(f"[pasarela] Escuchando en 127.0.0.1:{puerto}  (Ctrl+C para parar)")
    ThreadingHTTPServer(("127.0.0.1", puerto), Handler).serve_forever()


if __name__ == "__main__":
    main()
