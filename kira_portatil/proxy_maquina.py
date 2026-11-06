# -*- coding: utf-8 -*-
"""
proxy_maquina.py - La PUERTA a internet de la máquina virtual de Kira (v2.91).

Lo pidió el dueño: que KiraOS aprenda, investigue, experimente y busque por internet DESDE SU MÁQUINA VIRTUAL, y eligió
«internet siempre, pero sin ver tu casa».

Cómo se consigue (y por qué no se puede saltar desde dentro):
  - la máquina arranca con la red de QEMU AISLADA («restrict=on»): por sí sola no llega ni a internet, ni a tu
    portátil, ni a ningún aparato de tu casa;
  - lo único que QEMU le deja es UNA puerta: la dirección 10.0.2.100:3128 de dentro. Cada conexión a esa puerta la
    atiende ESTE programa, que corre en el portátil (fuera de la máquina) — QEMU lo lanza por cada conexión
    («guestfwd … cmd:»), con la conexión en su entrada/salida;
  - la puerta solo deja ir a INTERNET DE VERDAD: resuelve el nombre aquí fuera y, si la dirección no es pública
    (tu router, tu portátil, tu móvil, 127.0.0.1, 10.x, 192.168.x, 172.16-31.x, 169.254.x, 100.64.x, IPv6 locales…),
    contesta «403» y no conecta. Solo puertos web: 443 (https, por CONNECT) y 80 (http);
  - aunque algo dentro de la máquina llegara a ser administrador, no puede cambiar ESTO: está fuera.

Apunta en `puerta.log` (de la carpeta de la máquina) a qué sitios fue (solo el nombre y el puerto, nunca el contenido).
OJO: QEMU conecta también la salida de errores a la conexión de la máquina: este programa no escribe NADA en stderr.
"""
import ipaddress
import os
import re
import select
import socket
import sys
import time

PUERTOS = {"CONNECT": {443}, "HTTP": {80}}     # https (por CONNECT) y http normal
MAX_CABECERA = 32 * 1024
ESPERA = 120          # segundos sin moverse nada → se cierra
TOPE = 30 * 60        # una conexión no dura más de media hora


class PuertaError(Exception):
    def __init__(self, codigo, motivo):
        super().__init__(motivo)
        self.codigo, self.motivo = codigo, motivo


# =====================================================================================
#  PARTE PURA (se prueba sin red)
# =====================================================================================
def permitido(ip):
    """¿Es una dirección de INTERNET de verdad (no de tu casa, ni del portátil, ni especial)?"""
    try:
        d = ipaddress.ip_address(str(ip).split("%")[0])
    except ValueError:
        return False
    if isinstance(d, ipaddress.IPv6Address) and d.ipv4_mapped:
        d = d.ipv4_mapped
    return bool(d.is_global) and not (d.is_multicast or d.is_reserved or d.is_loopback or d.is_link_local
                                      or d.is_private or d.is_unspecified)


_HOST = re.compile(r"^[A-Za-z0-9.\-\[\]:]{1,255}$")


def _host_puerto(texto, defecto):
    texto = texto.strip()
    if texto.startswith("["):                                   # [IPv6]:puerto
        m = re.match(r"^\[([0-9A-Fa-f:.]+)\](?::(\d{1,5}))?$", texto)
        if not m:
            raise PuertaError(400, "dirección rara")
        return m.group(1), int(m.group(2) or defecto)
    if texto.count(":") == 1:
        h, p = texto.split(":")
        if not p.isdigit():
            raise PuertaError(400, "puerto raro")
        return h, int(p)
    return texto, defecto


def analizar(cabecera):
    """De la petición (bytes hasta la línea en blanco) saca qué quiere: {'tipo', 'host', 'puerto', 'linea', 'resto'}.
    Lanza PuertaError si no es una petición de un navegador normal o va a un puerto que no es web."""
    try:
        texto = cabecera.decode("latin-1")
    except Exception:
        raise PuertaError(400, "petición ilegible")
    lineas = texto.split("\r\n")
    partes = lineas[0].split(" ")
    if len(partes) != 3 or not partes[2].startswith("HTTP/1."):
        raise PuertaError(400, "petición rara")
    metodo, objetivo, version = partes
    if metodo.upper() == "CONNECT":
        host, puerto = _host_puerto(objetivo, 443)
        tipo = "CONNECT"
    else:
        m = re.match(r"^http://([^/?#]+)(.*)$", objetivo, flags=re.I)
        if not m:
            raise PuertaError(400, "solo atiendo direcciones completas (http://…) o CONNECT")
        host, puerto = _host_puerto(m.group(1).split("@")[-1], 80)
        ruta = m.group(2) or "/"
        if not ruta.startswith("/"):
            ruta = "/" + ruta
        tipo = "HTTP"
        objetivo = ruta
    if not host or not _HOST.match(host):
        raise PuertaError(400, "nombre de sitio raro")
    if puerto not in PUERTOS[tipo]:
        raise PuertaError(403, f"solo dejo salir a webs (puerto {sorted(PUERTOS[tipo])[0]}), no al {puerto}")
    return {"tipo": tipo, "host": host.strip("[]"), "puerto": puerto, "metodo": metodo.upper(),
            "linea": f"{metodo} {objetivo} {version}", "resto": lineas[1:]}


def cabecera_http(peticion):
    """La petición http normal, ya para el sitio: ruta corta, sin cabeceras del proxy y cerrando al acabar."""
    fuera = ("proxy-connection", "proxy-authorization", "connection", "keep-alive")
    lineas = [peticion["linea"]]
    for l in peticion["resto"]:
        if not l:
            continue
        nombre = l.split(":", 1)[0].strip().lower()
        if nombre not in fuera:
            lineas.append(l)
    lineas.append("Connection: close")
    return ("\r\n".join(lineas) + "\r\n\r\n").encode("latin-1")


def elegir_direccion(host, puerto, getaddrinfo=socket.getaddrinfo):
    """La primera dirección PÚBLICA del sitio (resuelta aquí fuera). Si todas son de casa/especiales → 403."""
    try:                                                   # una dirección escrita a mano: se mira tal cual
        d = ipaddress.ip_address(host)
        if not permitido(d):
            raise PuertaError(403, f"«{host}» no es de internet: la puerta de mi máquina no deja ir a tu casa")
        return (socket.AF_INET6 if d.version == 6 else socket.AF_INET), (str(d), puerto)
    except ValueError:
        pass
    try:
        res = getaddrinfo(host, puerto, 0, socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, OSError):
        raise PuertaError(502, f"no encuentro «{host}» en internet")
    vistas = []
    for familia, _t, _p, _c, dire in res:
        ip = dire[0]
        vistas.append(ip)
        if permitido(ip):
            return familia, dire
    raise PuertaError(403, f"«{host}» no es de internet ({', '.join(sorted(set(vistas))[:3])}): "
                           "la puerta de mi máquina no deja ir a tu casa")


def respuesta_error(codigo, motivo):
    frase = {400: "Bad Request", 403: "Forbidden", 502: "Bad Gateway", 504: "Gateway Timeout"}.get(codigo, "Error")
    cuerpo = ("Kira (puerta de la máquina): " + motivo + "\n").encode("utf-8")
    return (f"HTTP/1.1 {codigo} {frase}\r\nContent-Type: text/plain; charset=utf-8\r\n"
            f"Content-Length: {len(cuerpo)}\r\nConnection: close\r\n\r\n").encode("latin-1") + cuerpo


# =====================================================================================
#  ATENDER UNA CONEXIÓN
# =====================================================================================
def _leer_cabecera(leer):
    datos = b""
    while b"\r\n\r\n" not in datos:
        trozo = leer(4096)
        if not trozo:
            raise PuertaError(400, "la conexión se cerró antes de pedir nada")
        datos += trozo
        if len(datos) > MAX_CABECERA:
            raise PuertaError(400, "petición demasiado larga")
    cab, _, sobra = datos.partition(b"\r\n\r\n")
    return cab, sobra


def _escribir_todo(fd, datos):
    while datos:
        n = os.write(fd, datos)
        datos = datos[n:]


def atender(fd_in, fd_out, getaddrinfo=socket.getaddrinfo, conectar=None, registrar=None, espera=ESPERA,
            tope=TOPE, reloj=time.monotonic):
    """Atiende UNA conexión de la máquina (fd_in/fd_out: su entrada y salida). Devuelve lo que pasó (texto corto)."""
    conectar = conectar or (lambda familia, dire: socket.create_connection(dire[:2], timeout=20))
    registrar = registrar or (lambda _t: None)
    destino = None
    try:
        cab, sobra = _leer_cabecera(lambda n: os.read(fd_in, n))
        pet = analizar(cab)
        familia, dire = elegir_direccion(pet["host"], pet["puerto"], getaddrinfo)
        try:
            destino = conectar(familia, dire)
        except OSError:
            raise PuertaError(504, f"«{pet['host']}» no contesta")
        destino.settimeout(None)
        if pet["tipo"] == "CONNECT":
            _escribir_todo(fd_out, b"HTTP/1.1 200 Connection established\r\n\r\n")
        else:
            destino.sendall(cabecera_http(pet))
        if sobra:
            destino.sendall(sobra)
        registrar(f"{pet['host']}:{pet['puerto']} ok")
    except PuertaError as e:
        registrar(f"denegado ({e.codigo}): {e.motivo}")
        try:
            _escribir_todo(fd_out, respuesta_error(e.codigo, e.motivo))
        except OSError:
            pass
        if destino is not None:
            destino.close()
        return f"{e.codigo} {e.motivo}"
    # pasar los datos en las dos direcciones, hasta que alguno cierre (o se quede quieto demasiado)
    inicio, ultimo = reloj(), reloj()
    dfd = destino.fileno()
    try:
        while True:
            listos, _, _ = select.select([fd_in, dfd], [], [], 1.0)
            ahora = reloj()
            if not listos:
                if ahora - ultimo > espera or ahora - inicio > tope:
                    break
                continue
            ultimo = ahora
            if fd_in in listos:
                d = os.read(fd_in, 65536)
                if not d:
                    break
                destino.sendall(d)
            if dfd in listos:
                d = destino.recv(65536)
                if not d:
                    break
                _escribir_todo(fd_out, d)
            if ahora - inicio > tope:
                break
    except OSError:
        pass
    finally:
        try:
            destino.close()
        except OSError:
            pass
    return "ok"


def _registro(ruta):
    def apuntar(texto):
        if not ruta:
            return
        try:
            if os.path.isfile(ruta) and os.path.getsize(ruta) > 1_000_000:   # que no crezca sin fin
                os.replace(ruta, ruta + ".1")
            with open(ruta, "a", encoding="utf-8") as f:
                f.write(time.strftime("%d/%m %H:%M:%S ") + texto + "\n")
        except OSError:
            pass
    return apuntar


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ruta = None
    if "--registro" in argv:
        i = argv.index("--registro")
        ruta = argv[i + 1] if i + 1 < len(argv) else None
    try:                                     # stderr va a la máquina: que no salga nada por ahí
        nulo = os.open(os.devnull, os.O_WRONLY)
        os.dup2(nulo, 2)
    except OSError:
        pass
    try:
        atender(0, 1, registrar=_registro(ruta))
    except Exception:                        # noqa: BLE001 - la puerta nunca enseña errores de Python a la máquina
        pass


if __name__ == "__main__":
    main()
