# -*- coding: utf-8 -*-
"""
vigilancia_kira.py - La «guardiana» de TU red (portátil). SOLO DEFENSA. Aprende cómo es tu red normal y te AVISA de
lo anormal. No ataca, no escanea fuera de tu red (se apoya en red_defensa_kira, que tiene el candado «solo tu red»).

Qué hace y cómo EVOLUCIONA (lo que mejora con el tiempo son los DATOS, no el código):
  - Aprende qué aparatos son habituales en tu red. La primera vez que ve uno nuevo, te avisa; luego ya lo conoce.
  - Aprende el tráfico NORMAL (cuántos paquetes es lo habitual) y, con eso, cada vez afina mejor qué es «mucho»
    (umbral adaptativo). Así da menos falsas alarmas según pasa el tiempo.
  - Guarda un MAPA/historial de lo que va viendo (eventos), para que Kira te lo pueda contar.
  - Puedes CONFIRMAR un aparato como de confianza (tú mandas: como los «dos toques» de las mejoras).

Solo AVISA: nunca hace nada en tu red por su cuenta. Solo librería estándar. Se prueba con una defensa de mentira.

  python vigilancia_kira.py --revisar            una pasada ahora (aprende y avisa)
  python vigilancia_kira.py --vigilar --cada 10  vigila sola cada 10 minutos (lo que arranca el portátil)
  python vigilancia_kira.py --mapa               enseña lo que sabe de tu red
"""
import argparse
import ipaddress
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(os.path.expanduser("~"), ".kira_vigilancia.json")

APRENDIENDO = 5          # primeras pasadas: solo aprende el tráfico normal, no avisa de «mucho tráfico»
MAX_EVENTOS = 400        # el historial no crece sin fin
_SUELO_PAQ = 400         # por debajo de esto, el tráfico nunca se considera «mucho» (evita avisos tontos)


# =====================================================================================
#  Guardar / cargar lo aprendido
# =====================================================================================
def _vacio():
    return {"aparatos": {}, "trafico": {"muestras": 0, "media": 0.0, "max": 0}, "eventos": []}


def cargar(ruta=None):
    ruta = ruta or RUTA
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        for k in _vacio():
            d.setdefault(k, _vacio()[k])
        return d
    except (OSError, ValueError):
        return _vacio()


def guardar(estado, ruta=None):
    ruta = ruta or RUTA
    tmp = (ruta) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False)
    os.replace(tmp, ruta)
    try:
        os.chmod(ruta, 0o600)
    except OSError:
        pass


# =====================================================================================
#  La defensa que usa (por defecto red_defensa_kira; en las pruebas, una de mentira)
# =====================================================================================
class DefensaReal:
    def inventario(self):
        import red_defensa_kira as rd
        return rd.inventario()

    def trafico(self, segundos=20):
        import red_defensa_kira as rd
        return rd.trafico(segundos)


def _clave(a):
    """Identifica un aparato: por su MAC (lo más fiable); si no la hay, por su IP."""
    return (a.get("mac") or "").upper() or a.get("ip", "")


def _es_externa(ip):
    try:
        return not ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def _apunta(estado, tipo, detalle, nivel="aviso"):
    estado["eventos"].append({"cuando": int(time.time()), "tipo": tipo, "detalle": detalle,
                              "nivel": nivel, "visto": False})
    if len(estado["eventos"]) > MAX_EVENTOS:
        estado["eventos"] = estado["eventos"][-MAX_EVENTOS:]


# =====================================================================================
#  Una pasada: aprende y avisa de lo anormal
# =====================================================================================
def revisar(estado, defensa=None, ahora=None):
    """Mira la red una vez. Devuelve la lista de avisos nuevos (aparatos desconocidos, mucho tráfico). Aprende de
    paso (actualiza lo que es normal). NO toca nada de la red: solo mira y avisa."""
    defensa = defensa or DefensaReal()
    ahora = int(ahora if ahora is not None else time.time())
    avisos = []

    # --- aparatos ---
    try:
        inv = defensa.inventario()
    except Exception as e:
        return [{"tipo": "sin_red", "detalle": f"No pude mirar la red: {e}", "nivel": "info"}]
    for a in inv:
        k = _clave(a)
        if not k:
            continue
        ap = estado["aparatos"].get(k)
        if ap is None:
            estado["aparatos"][k] = {"ip": a.get("ip", ""), "mac": a.get("mac", ""),
                                     "nombre": a.get("nombre", ""), "fabricante": a.get("fabricante", ""),
                                     "primera_vez": ahora, "ultima_vez": ahora, "veces": 1, "confirmado": False}
            det = f"Aparato NUEVO en tu red: {a.get('ip','?')} {a.get('nombre') or ''} {a.get('fabricante') or ''}".strip()
            _apunta(estado, "aparato_nuevo", det, "importante")
            avisos.append({"tipo": "aparato_nuevo", "detalle": det, "nivel": "importante"})
        else:
            ap["ultima_vez"] = ahora
            ap["veces"] = ap.get("veces", 0) + 1
            if a.get("ip"):
                ap["ip"] = a["ip"]
            if a.get("nombre"):
                ap["nombre"] = a["nombre"]

    # --- tráfico: aprende lo normal y avisa solo si hay MUCHO comparado con lo aprendido ---
    try:
        t = defensa.trafico(20)
    except Exception:
        t = None
    if t and t.get("conversaciones"):
        externas = [c for c in t["conversaciones"] if _es_externa(c.get("a", "")) or _es_externa(c.get("b", ""))]
        tope = max((c.get("paquetes", 0) for c in externas), default=0)
        tr = estado["trafico"]
        if tr["muestras"] >= APRENDIENDO:
            limite = max(_SUELO_PAQ, int(tr["max"] * 1.6), int(tr["media"] * 3))
            if tope > limite:
                peor = max(externas, key=lambda c: c.get("paquetes", 0))
                fuera = peor["b"] if _es_externa(peor.get("b", "")) else peor.get("a", "")
                det = f"Mucho tráfico hacia fuera: {fuera} ({tope} paquetes; lo normal aquí es ~{int(tr['media'])})."
                _apunta(estado, "trafico_alto", det, "importante")
                avisos.append({"tipo": "trafico_alto", "detalle": det, "nivel": "importante"})
        # aprender (la media y el máximo van evolucionando)
        n = tr["muestras"]
        tr["media"] = (tr["media"] * n + tope) / (n + 1)
        tr["max"] = max(tr["max"], tope)
        tr["muestras"] = n + 1

    return avisos


# =====================================================================================
#  Tú mandas: confirmar un aparato de confianza, olvidarlo, y ver/limpiar avisos
# =====================================================================================
def confirmar(estado, clave_o_ip):
    for k, ap in estado["aparatos"].items():
        if k == clave_o_ip or ap.get("ip") == clave_o_ip:
            ap["confirmado"] = True
            return True
    return False


def olvidar(estado, clave_o_ip):
    for k in list(estado["aparatos"]):
        ap = estado["aparatos"][k]
        if k == clave_o_ip or ap.get("ip") == clave_o_ip:
            del estado["aparatos"][k]
            return True
    return False


def pendientes(estado):
    """Los avisos que aún no has visto."""
    return [e for e in estado["eventos"] if not e.get("visto")]


def marcar_vistos(estado):
    for e in estado["eventos"]:
        e["visto"] = True


def mapa(estado):
    """Lo que Kira sabe de tu red: aparatos (y cuáles has confirmado), el tráfico normal aprendido y los últimos
    eventos. Es el «mapa» de tu red, que va creciendo."""
    aparatos = sorted(estado["aparatos"].values(), key=lambda a: a.get("ip", ""))
    return {"aparatos": aparatos,
            "confirmados": sum(1 for a in aparatos if a.get("confirmado")),
            "trafico_normal": estado["trafico"],
            "pendientes": len(pendientes(estado)),
            "ultimos": estado["eventos"][-15:]}


# =====================================================================================
#  Vigilar sola cada cierto tiempo (lo que arranca el portátil)
# =====================================================================================
def vigilar(cada_min=10, ruta=None, defensa=None, avisar=None, parar=None, dormir=time.sleep):
    """Da una pasada cada `cada_min` minutos, para siempre (hasta que `parar()` diga que no). Cada aviso nuevo se
    pasa a `avisar(aviso)`. Solo mira y avisa; nunca toca la red."""
    avisar = avisar or (lambda a: print(f"[Kira·red] {a['detalle']}"))
    cada = max(1, int(cada_min)) * 60
    while True:
        if parar and parar():
            return
        estado = cargar(ruta)
        for a in revisar(estado, defensa=defensa):
            if a.get("nivel") != "info":
                avisar(a)
        guardar(estado, ruta)
        if parar and parar():
            return
        dormir(cada)


def main(argv=None):
    ap = argparse.ArgumentParser(description="La guardiana de tu red (solo defensa)")
    ap.add_argument("--revisar", action="store_true", help="una pasada ahora")
    ap.add_argument("--vigilar", action="store_true", help="vigilar sola, para siempre")
    ap.add_argument("--cada", type=int, default=10, help="minutos entre pasadas (con --vigilar)")
    ap.add_argument("--mapa", action="store_true", help="enseña lo que sabe de tu red")
    ap.add_argument("--ruta", default=None)
    a = ap.parse_args(argv)
    if a.mapa:
        print(json.dumps(mapa(cargar(a.ruta)), ensure_ascii=False, indent=1))
        return
    if a.vigilar:
        print(f"Vigilando tu red cada {a.cada} min (solo aviso, nada automático). Ctrl+C para parar.")
        try:
            vigilar(a.cada, ruta=a.ruta)
        except KeyboardInterrupt:
            print("\nFin de la vigilancia.")
        return
    # por defecto: una pasada
    estado = cargar(a.ruta)
    avisos = revisar(estado)
    guardar(estado, a.ruta)
    if not avisos:
        print("Todo normal en tu red (o estoy aún aprendiendo cómo es).")
    for av in avisos:
        print(f"- [{av['nivel']}] {av['detalle']}")


if __name__ == "__main__":
    main()
