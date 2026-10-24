# -*- coding: utf-8 -*-
"""
kira_consola.py - Hablar con Kira DIRECTAMENTE en el portátil, sin el móvil.

El portátil ya tiene el cerebro grande (servidor_portatil.py). Esto es una ventana de texto para usarlo:
escribes y Kira contesta ahí mismo. Útil para programar, preguntar o revisar tu red desde el propio portátil.

  python kira_consola.py                 charla (cerebro grande por defecto)
  python kira_consola.py --rapido        empieza con el cerebro rápido
  python kira_consola.py -p "una idea"   una sola pregunta y a la salida (para scripts/pruebas)

Dentro de la charla:
  /rapido  /grande     cambiar de cerebro
  /red                 aparatos conectados a tu red (defensa)
  /puertos 192.168.1.x  puertos abiertos de un aparato tuyo
  /trafico [segundos]  resumen del tráfico de tu red
  /estado              qué tiene el portátil
  /salir               cerrar

Habla con el servidor del portátil (127.0.0.1:8770) con el token del laboratorio. Solo librería estándar.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))


def leer_token(ruta=None):
    t = os.environ.get("KIRA_LAB_TOKEN", "").strip()
    ruta = ruta or os.path.join(os.path.dirname(AQUI), "kira_laboratorio", "token_lab.txt")
    if not t and os.path.isfile(ruta):
        with open(ruta, encoding="utf-8") as f:
            t = f.read().strip()
    return t


class ConsolaError(RuntimeError):
    pass


class Cliente:
    def __init__(self, url="http://127.0.0.1:8770", token="", abrir=None):
        self.url = url.rstrip("/")
        self.token = token
        self._abrir = abrir or urllib.request.urlopen
        self.historial = []
        self.grande = True

    def _pedir(self, ruta, datos, timeout=900, stream=False, al_trozo=None):
        cuerpo = json.dumps(datos).encode("utf-8")
        req = urllib.request.Request(self.url + ruta, data=cuerpo, method="POST",
                                     headers={"Content-Type": "application/json", "X-Kira-Token": self.token})
        try:
            with self._abrir(req, timeout=timeout) as r:
                if stream and al_trozo:
                    texto = ""
                    for linea in r:
                        linea = linea.decode("utf-8", "replace").strip()
                        if not linea.startswith("data:"):
                            continue
                        d = linea[5:].strip()
                        if d == "[DONE]":
                            break
                        try:
                            trozo = (json.loads(d)["choices"][0].get("delta") or {}).get("content") or ""
                        except (ValueError, KeyError, IndexError):
                            trozo = ""
                        if trozo:
                            texto += trozo
                            al_trozo(trozo)
                    return texto
                return json.loads(r.read(8_000_000).decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise ConsolaError(f"El portátil respondió {e.code}.")
        except Exception as e:
            raise ConsolaError(f"No se pudo hablar con el portátil (¿está encendido el cerebro de casa?): {e}")

    def hola(self):
        req = urllib.request.Request(self.url + "/hola", method="GET", headers={"X-Kira-Token": self.token})
        try:
            with self._abrir(req, timeout=5) as r:
                return json.loads(r.read(20000).decode("utf-8"))
        except Exception as e:
            raise ConsolaError(f"No encuentro el cerebro de casa en {self.url}: {e}")

    SISTEMA = ("Eres Kira, una asistente en el portátil de tu dueño. Respondes en español, con claridad. Puedes "
               "programar, explicar y ayudar con la seguridad de SU red (defensa). No creas malware ni herramientas "
               "de ataque.")

    def charla(self, texto, al_trozo=None):
        self.historial.append({"role": "user", "content": texto})
        self.historial = self.historial[-16:]
        msgs = [{"role": "system", "content": self.SISTEMA}] + self.historial
        r = self._pedir("/v1/chat/completions",
                        {"messages": msgs, "max_tokens": 1500, "temperature": 0.6,
                         "kira_cerebro": "grande" if self.grande else "rapido",
                         "stream": bool(al_trozo), "chat_template_kwargs": {"enable_thinking": False}},
                        stream=bool(al_trozo), al_trozo=al_trozo)
        texto_r = r if isinstance(r, str) else r["choices"][0]["message"]["content"]
        self.historial.append({"role": "assistant", "content": texto_r})
        return texto_r

    def defensa(self, accion, **extra):
        return self._pedir("/defensa", {"accion": accion, **extra}, timeout=300)


def formato_defensa(r):
    if not r.get("ok"):
        return "[x] " + r.get("error", "no se pudo")
    if "aparatos" in r:
        if not r["aparatos"]:
            return "No veo aparatos (¿estás en la WiFi?)."
        return "Aparatos en tu red:\n" + "\n".join(
            f"  {a['ip']:16} {a.get('nombre') or '':24} {a.get('fabricante') or ''}" for a in r["aparatos"])
    if "abiertos" in r:
        if not r["abiertos"]:
            return f"{r['host']}: no veo puertos abiertos (bien)."
        return f"Puertos abiertos en {r['host']}:\n" + "\n".join(
            f"  {p['puerto']:6} {p['servicio']}" for p in r["abiertos"])
    if "conversaciones" in r:
        lineas = ["Tráfico de tu red (quién habla con quién):"]
        for c in r["conversaciones"][:12]:
            lineas.append(f"  {c['a']:16} <-> {c['b']:16} {c['paquetes']} paquetes")
        if r.get("protocolos"):
            lineas.append("Protocolos: " + ", ".join(f"{p['protocolo']}({p['paquetes']})" for p in r["protocolos"][:8]))
        return "\n".join(lineas)
    return json.dumps(r, ensure_ascii=False)


def una_vez(cli, pregunta):
    print("Kira: ", end="", flush=True)
    print(cli.charla(pregunta, al_trozo=lambda t: print(t, end="", flush=True)))


def bucle(cli):
    h = cli.hola()
    cual = (h.get("cargado") and (h.get("cerebros") or {}).get(h["cargado"])) or "cerebro de casa"
    print(f"Kira en «{h.get('nombre', 'el portátil')}» — {cual}. Escribe, o «/salir» para cerrar. «/red» para tu red.")
    while True:
        try:
            tu = input("\nTú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            return
        if not tu:
            continue
        bajo = tu.lower()
        if bajo in ("/salir", "/sal", "salir", "adios"):
            print("Hasta luego.")
            return
        if bajo in ("/rapido", "/grande"):
            cli.grande = bajo == "/grande"
            print(f"[cerebro {'grande' if cli.grande else 'rápido'}]")
            continue
        try:
            if bajo == "/estado":
                print(json.dumps(cli.hola(), ensure_ascii=False, indent=1))
                continue
            if bajo in ("/red", "/aparatos"):
                print(formato_defensa(cli.defensa("inventario")))
                continue
            if bajo.startswith("/puertos"):
                partes = tu.split()
                if len(partes) < 2:
                    print("Usa: /puertos 192.168.1.50")
                else:
                    print(formato_defensa(cli.defensa("puertos", host=partes[1])))
                continue
            if bajo.startswith("/trafico") or bajo.startswith("/tráfico"):
                partes = tu.split()
                seg = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 20
                print(f"Mirando el tráfico {seg} s…")
                print(formato_defensa(cli.defensa("trafico", segundos=seg)))
                continue
            print("Kira: ", end="", flush=True)
            cli.charla(tu, al_trozo=lambda t: print(t, end="", flush=True))
            print()
        except ConsolaError as e:
            print(f"[x] {e}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Hablar con Kira en el portátil")
    ap.add_argument("--url", default="http://127.0.0.1:8770")
    ap.add_argument("--rapido", action="store_true")
    ap.add_argument("-p", "--pregunta", default=None)
    a = ap.parse_args(argv)
    token = leer_token()
    if len(token) < 16:
        sys.exit("No encuentro el token del laboratorio (arranca antes el cerebro de casa).")
    cli = Cliente(a.url, token)
    cli.grande = not a.rapido
    try:
        if a.pregunta:
            una_vez(cli, a.pregunta)
            print()
        else:
            bucle(cli)
    except ConsolaError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
