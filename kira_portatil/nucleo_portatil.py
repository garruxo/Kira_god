# -*- coding: utf-8 -*-
"""
nucleo_portatil.py - La KIRA COMPLETA corriendo en el portátil (sin pantalla), para que el móvil solo le MANDE órdenes.

Pedido del dueño: «la Kira del móvil, que solo le envíe órdenes y la ejecute el portátil». Aquí corre el MISMO núcleo
de Kira que en el móvil (kira_god.KiraGodCore: estudiar, pensar, investigar, foco, programar, experimentar, baúl…),
con su carpeta de datos propia (~/kira_portatil/kira_datos) y usando como cerebro el del portátil (servidor_portatil,
127.0.0.1:8770). El móvil le manda la orden por la WiFi de casa, ve la barra de progreso y recibe la respuesta.

  POST /orden   {"orden": "estudia Python"}  -> {"id": "…"}          (una orden cada vez; si está ocupada, 409)
  GET  /tarea?id=…                          -> {"estado", "fraccion", "avance": [...], "respuesta", "codigo", "nombre"}
  POST /cancelar                            -> para lo que esté haciendo («para» en el móvil)
  POST /memoria  (cuerpo = .zip)            -> importa la memoria del móvil (memoria_kira) y reinicia el núcleo
  GET  /hola                                -> quién soy, si estoy ocupada, cuánto recuerdo
  GET  /salud                               -> {"ok": true} (sin token)

Todo pide el token del laboratorio (el mismo que el cerebro de casa). Escucha en la red de casa (puerto 8771).
SEGURIDAD: aquí NO se ejecuta código que llegue por la red: solo ÓRDENES en lenguaje normal, que el núcleo trata
igual que en el móvil (modo seguro, laboratorio, dos toques / auto-mejora con su interruptor). La memoria que llega se
valida nombre a nombre (memoria_kira) y lo que había se guarda antes.
"""
import argparse
import hmac
import json
import os
import sys
import tempfile
import threading
import time
import uuid
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
PUERTO = 8771
MAX_MEMORIA = 900 * 1024 * 1024
DATOS = os.path.expanduser("~/kira_portatil/kira_datos")


# =====================================================================================
#  PREPARAR LA CARPETA DE DATOS (antes de importar el núcleo)
# =====================================================================================
def preparar_datos(datos, token, cerebro_url="http://127.0.0.1:8770", lab_url="http://127.0.0.1:8765"):
    """Deja la carpeta de datos lista y le dice al núcleo dónde está su cerebro (el del portátil) con pasarela.json.
    Tiene que ir ANTES de importar kira_god (que lee KIRA_DATA_DIR)."""
    os.makedirs(datos, exist_ok=True)
    os.environ["KIRA_DATA_DIR"] = datos
    ruta = os.path.join(datos, "pasarela.json")
    d = {}
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.update(url=lab_url, token=token, portatil_url=cerebro_url, nombre=d.get("nombre") or "portátil")
    with open(ruta + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.chmod(ruta + ".tmp", 0o600)
    os.replace(ruta + ".tmp", ruta)
    if RAIZ not in sys.path:
        sys.path.insert(0, RAIZ)
    if AQUI not in sys.path:
        sys.path.insert(0, AQUI)
    return datos


# =====================================================================================
#  QUÉ HACER CON CADA ORDEN (lo mismo que hace la pantalla del móvil, pero sin pantalla)
# =====================================================================================
_MAQUINA = {"m": None}


def maquina():
    """La máquina virtual de Kira (v2.85), una para todo el núcleo."""
    if _MAQUINA["m"] is None:
        import maquina_kira as mq
        _MAQUINA["m"] = mq.Maquina()
    return _MAQUINA["m"]


def red_maquina():
    """v2.91: por dónde sale a internet lo de investigar (su máquina; si no puede, el portátil)."""
    if _MAQUINA.get("red") is None:
        import maquina_kira as mq
        _MAQUINA["red"] = mq.RedMaquina(maquina())
    return _MAQUINA["red"]


def enganchar_maquina(core):
    """v2.91 (lo pidió el dueño): KiraOS aprende, investiga, busca y EXPERIMENTA desde su máquina virtual. Buscar,
    leer páginas, vídeos y la Wikipedia salen DESDE la máquina (por su puerta, sin ver tu casa) y sus experimentos al
    pensar corren DENTRO, como un usuario sin permisos. Lo que lleva una clave (Claude, GitHub) o va a casa sale
    directo: una clave nunca entra en la máquina."""
    import maquina_kira as mq
    import red_kira
    red = red_maquina()
    red_kira.poner_investigar(red.abrir)
    core.probar_experimento = lambda codigo: mq.probar_en_maquina(maquina(), codigo, red=red)
    return red


def encender_maquina_al_arrancar(m=None):
    """Al encender KiraOS se enciende también su máquina (con la puerta), si está preparada y hay KVM."""
    m = m or maquina()
    try:
        if m.preparada() and m.kvm() and not m.encendida():
            m.encender(red=True)
    except Exception as e:                       # noqa: BLE001 - si no puede, investigará desde el portátil
        print(f"[núcleo] no pude encender la máquina: {e}", flush=True)


_Y_PRUEBALO = r"\s*,?\s*y\s+pru[eé]balo\s+en\s+(?:tu|la|mi)\s+m[aá]quina(?:\s+virtual)?\s*$"

# v2.87: KiraOS, cerebro central, también le cambia el ASPECTO al móvil y le prepara MEJORAS de sistema
_TEMA_MOVIL = (r"^(?:cambia|pon|ponle|cambiale)\s+(?:el\s+)?(?:aspecto|tema|color(?:es)?|estetica|estética)\s+"
               r"(?:del|al|de\s+la\s+kira\s+del)\s+m[oó]vil\s+(?:a|en)\s+(?:color\s+)?(?P<t>[\wáéíóú]+)$")
_MEJORA_MOVIL = (r"^(?:prepara|crea|hazle|haz)\s+(?:una\s+)?(?:mejora|funci[oó]n|orden\s+nueva)\s+"
                 r"(?:para\s+(?:el|la\s+kira\s+del)\s+m[oó]vil)\s*(?:que|:|para)?\s*(?P<p>.+)$")


def mejora_para_movil(core, pedido, paso):
    """KiraOS escribe una mejora de sistema para el móvil, la prueba en SU laboratorio y la deja lista para la
    próxima sincronía. El móvil la vuelve a probar en el suyo y espera los dos toques del dueño."""
    import laboratorio_movil_kira as lab
    import sincronia_kira as sc
    paso(0.1, "Escribo la mejora para el móvil…")
    nombre, codigo = core.generar_mejora(pedido)
    paso(0.6, f"La pruebo en mi laboratorio ({nombre})…")
    res = lab.LaboratorioMovil().probar(nombre, codigo)
    if not res.get("ok"):
        mal = next((e for e in res.get("etapas", []) if not e.get("ok")), {})
        return {"texto": f"[x] La mejora «{nombre}» no pasa mi laboratorio ({mal.get('nombre', '?')}: "
                         f"{mal.get('detalle', '')}). No se la mando al móvil.", "ok": False}
    sc.guardar_para_movil(core.dir, nombre, codigo, descripcion=pedido, prueba=res)
    return {"texto": f"Mejora «{nombre}» lista y probada en mi laboratorio. Se la daré al móvil en la próxima "
                     "sincronía; allí la volverá a probar y esperará tus dos toques.", "codigo": codigo,
            "nombre": nombre, "ok": True}


# =====================================================================================
#  v3.07: KiraOS SE MEJORA A SÍ MISMA, con la misma red de seguridad que el móvil
#  «mejórate: …» -> la escribe, la prueba en SU laboratorio y la deja ESPERANDO. Instalarla solo desde ESTE portátil,
#  en la ventana «Mejoras» del escritorio, con DOS toques. Antes de instalar se guarda copia: «Volver atrás» la deshace.
# =====================================================================================
_MEJORA_TI = (r"^(?:por\s+favor\s+)?(?:mej[oó]rate|mejora\s+(?:a\s+)?(?:kira\s?os|tu\s+(?:propio\s+)?sistema|"
              r"a\s+ti\s+misma|el\s+sistema\s+del\s+port[aá]til)|prepara(?:te)?\s+una\s+mejora\s+para\s+"
              r"(?:ti(?:\s+misma)?|kira\s?os)|a[ñn][aá]dete(?:\s+una\s+funci[oó]n)?|prepara\s+una\s+mejora\s+para\s+"
              r"el\s+port[aá]til)\s*(?P<sep>[:,]|para\s+que|para|con|que|y)?\s*(?P<p>.*)$")
_NO_ES_MEJORA_TI = r"^(?:sola|solita|sin\s+parar|constantemente|siempre|cada\s+d[ií]a)$"


def pedido_mejora_kiraos(texto):
    """Lo que pide de mejora PARA KiraOS (o None). «mejórate sola» es el interruptor de la auto-mejora: no es esto."""
    import re
    m = re.match(_MEJORA_TI, str(texto or "").strip().rstrip(" .!?"), flags=re.I)
    if not m:
        return None
    p = m.group("p").strip(" ,.:")
    if len(p) < 4 or re.match(_NO_ES_MEJORA_TI, p, flags=re.I):
        return None
    sep = (m.group("sep") or "").lower()
    return (sep + " " + p).strip() if sep in ("para que", "que") else p


def panel_de(core):
    """El panel de mejoras de KiraOS (el mismo PanelControl del móvil: laboratorio, pendiente, aplicar, volver atrás)."""
    pan = getattr(core, "_panel", None)
    if pan is None:
        import panel_kira
        pan = panel_kira.PanelControl(core)
        core._panel = pan
    return pan


def mejora_para_kiraos(core, pedido, paso):
    paso(0.1, "Escribo la mejora para mí y la pruebo en mi laboratorio…")
    try:
        r = panel_de(core).enviar_orden(pedido)
    except Exception as e:                            # noqa: BLE001
        return {"texto": f"[x] No he podido preparar la mejora: {e}", "ok": False}
    if r.get("aprobable"):
        pend = panel_de(core).pendiente
        nombre = getattr(pend, "nombre", "") or r.get("nombre", "")
        return {"texto": f"Mejora «{nombre}» escrita y aprobada por mi laboratorio. NO la he instalado: ábrela en "
                         "Cuaderno ▸ Mejoras ▸ «Instalar o deshacer mis mejoras», mira el código y pulsa «Instalar» DOS "
                         "veces (solo se puede desde este portátil). Si luego no te gusta, «Volver atrás».",
                "codigo": getattr(pend, "codigo", None), "nombre": nombre, "ok": True}
    return {"texto": "No la instalo: " + str(r.get("texto", "no pasó el laboratorio")).strip(), "ok": False}


def orden_ventana(core, o, paso):
    """v3.19: crear / cambiar / quitar una ventana, sección o botón. Crear y cambiar = una MEJORA (laboratorio + tus
    dos toques en Cuaderno ▸ Mejoras); al cambiar, el cerebro recibe el código de ahora y la versión nueva SUSTITUYE
    a la vieja (con copia: «Volver atrás»)."""
    import ventanas_kira as vk
    if o[0] == "crear":
        return mejora_para_kiraos(core, o[1], paso)
    ventanas = core.ventanas_lista() if callable(getattr(core, "ventanas_lista", None)) else []
    v = vk.buscar(ventanas, o[1])
    if v is None:
        nombres = ", ".join(f"«{x['titulo']}»" for x in ventanas) or "ninguna todavía"
        return {"texto": f"No encuentro la ventana «{o[1]}». Las que me he añadido: {nombres}.", "ok": False}
    if o[0] == "quitar":
        return {"texto": f"La ventana «{v['titulo']}» es parte de mi mejora «{v['modulo']}». Para quitarla: Cuaderno ▸ "
                         "Mejoras ▸ «Instalar o deshacer mis mejoras» ▸ «Quitar» (dos toques). Si esa mejora hace más "
                         f"cosas, mejor dime «cambia la ventana {v['id']}: quítala y deja lo demás».", "ok": True}
    try:
        codigo = open(os.path.join(core.dir, "modulos", v["modulo"] + ".py"), encoding="utf-8").read()
    except OSError:
        return {"texto": f"No encuentro el código de la mejora «{v['modulo']}».", "ok": False}
    paso(0.1, f"Cambio la ventana «{v['titulo']}» y la pruebo en mi laboratorio…")
    try:
        r = panel_de(core).enviar_orden(f"Cambia la ventana «{v['id']}» de mi mejora «{v['modulo']}»: {o[2]}",
                                        nombre=v["modulo"], extra=vk.pedido_cambio(v, codigo, o[2]))
    except Exception as e:                            # noqa: BLE001
        return {"texto": f"[x] No he podido preparar el cambio: {e}", "ok": False}
    if r.get("aprobable"):
        pend = panel_de(core).pendiente
        return {"texto": f"Cambio de «{v['titulo']}» escrito y aprobado por mi laboratorio. NO lo he puesto: Cuaderno ▸ "
                         "Mejoras ▸ «Instalar o deshacer mis mejoras» ▸ «Instalar» (dos toques). La versión de antes "
                         "queda guardada: «Volver atrás» si no te gusta.",
                "codigo": getattr(pend, "codigo", None), "nombre": v["modulo"], "ok": True}
    return {"texto": "No lo cambio: " + str(r.get("texto", "no pasó el laboratorio")).strip(), "ok": False}


def _pensamientos(core):
    import pensador_kira as pn
    ruta = core._ruta_pensar()
    return pn, ruta, pn.cargar(ruta)


def conocimiento_a_mejora(core, ident, paso):
    """v3.12: «Pasar a mejorar» un conocimiento: si tiene código lo PRUEBA en la máquina virtual; luego escribe la
    mejora y la pasa por el laboratorio. Si pasa, queda en Mejoras esperando tus dos toques; si no, VUELVE a
    Pensamiento con el motivo."""
    import cuaderno_clases_kira as cc
    pn, ruta, est = _pensamientos(core)
    tipo, x = cc.buscar(est, ident)
    if tipo is None:
        return {"texto": "Ese conocimiento ya no está en el cuaderno.", "ok": False}
    if tipo == "sol":
        tema, sol = x
        codigo, resp = sol.get("codigo") or "", sol.get("respuesta") or ""
    else:
        tema, codigo, resp = cc.tema_de(x), (x.get("experimento") or {}).get("codigo") or "", x.get("respuesta") or ""

    def volver(motivo):
        pn2, ruta2, est2 = _pensamientos(core)
        cc.volver_a_pensamiento(est2, ident, motivo)
        pn2.guardar(est2, ruta2)
        return {"texto": f"[x] «{tema}» no pasó las pruebas ({motivo}). Ha vuelto a Pensamiento para seguir "
                         "dándole vueltas.", "ok": False}
    if codigo.strip():
        paso(0.15, f"Pruebo «{tema}» en mi máquina virtual…")
        try:
            ok_p, motivo, _dato = core._probar_experimento(codigo)
        except Exception as e:                        # noqa: BLE001
            ok_p, motivo = False, str(e)
        if not ok_p:
            return volver(str(motivo or "falló al probarlo")[:160])
    paso(0.4, "Funciona. Escribo la mejora y la paso por mi laboratorio…")
    r = mejora_para_kiraos(core, f"una función sobre {tema}, siguiendo esto que ya sé: {str(resp)[:400]}", paso)
    if not r.get("ok"):
        return volver(str(r.get("texto", "no pasó el laboratorio")).replace("No la instalo: ", "")[:160])
    return r


def marcar_nota(core, ident, **cambios):
    import cuaderno_clases_kira as cc
    pn, ruta, est = _pensamientos(core)
    tipo, x = cc.buscar(est, ident)
    if tipo == "nota":
        x.update(cambios)
        pn.guardar(est, ruta)
    return x if tipo == "nota" else None


def implementar_nota(core, ident, paso):
    """v3.12: «Implementar» una mejora del cuaderno: la escribe y la pasa por el laboratorio; queda esperando tus dos
    toques (nunca se instala sola). Apunta en la nota cómo fue."""
    import cuaderno_clases_kira as cc
    _pn, _ruta, est = _pensamientos(core)
    tipo, x = cc.buscar(est, ident)
    if tipo != "nota":
        return {"texto": "Esa mejora ya no está en el cuaderno.", "ok": False}
    pedido = ("una función sobre " + cc.tema_de(x) + ". Idea: "
              + __import__("re").sub(r"\s+", " ", str(x.get("respuesta", "")))[:400])
    r = mejora_para_kiraos(core, pedido, paso)
    marcar_nota(core, ident, en_marcha="", intento=("lista: espera tus dos toques" if r.get("ok") else
                                                    "no pasó el laboratorio: " + str(r.get("texto", ""))[:120]))
    return r


def cuaderno_accion(nucleo, accion, ident):
    """v3.12: los botones de Pensamiento / Conocimiento / Mejoras. viable | implementar | repensar | amejora."""
    import re
    import cuaderno_clases_kira as cc
    core = nucleo.core
    pn, ruta, est = _pensamientos(core)
    tipo, x = cc.buscar(est, ident)
    if tipo is None:
        return {"ok": False, "texto": "Ese apunte ya no está (puede que lo haya resuelto o movido)."}
    if accion == "viable" and tipo == "nota":
        x.update(viable=True, a_pensamiento=False)
        pn.guardar(est, ruta)
        return {"ok": True, "texto": f"Pasado a Mejoras ({cc.tipo_mejora(x)}): desde ahí puedes pedirme que lo "
                                     "implemente o que lo repiense."}
    if accion == "implementar" and tipo == "nota":
        x["en_marcha"] = "implementar"
        pn.guardar(est, ruta)
        tid = nucleo.trabajos.empezar(f"implementa la mejora del cuaderno: {ident} {cc.tema_de(x)}")
        return {"ok": True, "id": tid, "texto": "En cola: la escribo, la pruebo en mi laboratorio y, si pasa, te la "
                "dejo en «Instalar o deshacer mis mejoras» para tus dos toques. Lo verás en Tareas."}
    if accion == "repensar" and tipo == "nota":
        x["en_marcha"] = "repensar"
        pn.guardar(est, ruta)
        tid = nucleo.trabajos.empezar(f"repiensa a fondo: {ident} {cc.tema_de(x)}")
        return {"ok": True, "id": tid, "texto": "En cola: vuelvo a pensarlo, buscar y experimentar con ello. Lo "
                                                "verás en Tareas."}
    if accion == "amejora":
        tema = x[0] if tipo == "sol" else cc.tema_de(x)
        tid = nucleo.trabajos.empezar(f"pasa a mejora el conocimiento: {ident} {tema}")
        return {"ok": True, "id": tid, "texto": "En cola: lo pruebo en mi máquina virtual y, si funciona, lo paso por "
                "el laboratorio. Si pasa, irá a Mejoras (tus dos toques); si no, vuelve a Pensamiento."}
    return {"ok": False, "texto": "No conozco ese botón."}


def mejoras_estado(core):
    """Para la ventana «Mejoras»: la pendiente (con su código) y las instaladas."""
    pan = panel_de(core)
    pend = pan.pendiente
    d = {"pendiente": None, "instaladas": [], "auto": False}
    if pend is not None:
        d["pendiente"] = {"nombre": pend.nombre, "pedido": pan.pedido_actual, "codigo": pend.codigo[:12000],
                          "aprobable": bool(pend.aprobable), "resumen": str(pend.resumen())[:1500]}
    try:
        d["instaladas"] = pan.modulos()
    except Exception:
        pass
    try:
        d["auto"] = bool(pan.auto_mejora())
    except Exception:
        pass
    return d


def mejora_hacer(core, accion, nombre="", confirmado=False):
    pan = panel_de(core)
    if accion == "aplicar":
        return pan.aplicar(confirmado=confirmado is True)
    if accion == "rechazar":
        return pan.rechazar("descartada en el escritorio de KiraOS")
    if accion == "revertir":
        return pan.revertir(nombre)
    if accion == "quitar":
        if confirmado is not True:
            return {"ok": False, "texto": "[x] Falta tu confirmación."}
        return pan.quitar(nombre)
    if accion == "ver":
        return pan.ver_modulo(nombre)
    return {"ok": False, "texto": "[x] No conozco esa acción."}


def _crear_acceso(core, titulo, codigo):
    """v3.26: deja un ACCESO DIRECTO con icono en el escritorio del programa recién hecho (clic derecho ▸ desinstalar)."""
    if not codigo:
        return
    try:
        import accesos_kira as ak
        ak.anadir(core.dir, str(titulo or "Programa de Kira")[:60], codigo)
    except Exception:
        pass


def ejecutar(core, orden, paso):
    """Hace la orden con el núcleo. `paso(fraccion|None, texto)` va contando. Devuelve {texto, codigo?, nombre?}."""
    import re
    o = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", str(orden or ""), flags=re.I).strip() or orden
    try:
        core.registrar_actividad()
    except Exception:
        pass
    try:
        core.nueva_tarea()
    except Exception:
        pass
    import experimentos_kira as ex
    import programar_kira as pk
    import internet_kira as net
    import maquina_kira as mq
    import wifi_kira as wk
    import sentidos_portatil as sp
    import sistema_kira as sis_                   # v3.21: cambiar SU sistema (aspecto, salvapantallas, voz, brillo,
    o_s = sis_.orden(o)                            # sonido, bluetooth…) — antes que las ventanas («pon el icono…»)
    if o_s is not None:
        paso(0.3, "Cambio mi sistema…")
        try:
            ex_ = [(v["id"], v["titulo"]) for v in core.ventanas_lista() if v.get("en") == "escritorio"]
        except Exception:
            ex_ = []
        r_s = sis_.hacer(o_s[0], o_s[1], extras=ex_)
        return {"texto": r_s, **({"ok": False} if r_s.startswith("[x]") else {})}
    import ventanas_kira as vk_                    # v3.19: «crea/cambia/quita la ventana/el botón/la sección…» (antes que
    o_v = vk_.orden(o.rstrip(" .!¡?¿"))            # la WiFi: «crea una sección en la wifi…» es esto, no la WiFi)
    if o_v is not None:
        return orden_ventana(core, o_v, paso)
    if wk.orden_wifi(o) is not None:              # v2.88: la WiFi del portátil (la clave, solo en el portátil)
        paso(0.2, "Miro la WiFi del portátil…")
        return {"texto": wk.responder(o)}
    so = sp.es_orden(o)                           # v2.93: los SENTIDOS del portátil (cámara y pantalla, con OCR)
    if so:
        tipo, describir = so
        paso(0.3, "Miro con mi cámara…" if tipo == "camara" else "Leo la pantalla…")
        return {"texto": sp.hacer(tipo, describir)}
    om = mq.orden_maquina(o)                      # v2.85: su MÁQUINA VIRTUAL (Linux ligero)
    if om:
        accion, carga = om
        paso(0.0, f"Mi máquina: {accion}…")
        rec = getattr(core, "recuerdos", None)
        guardar = (lambda tema, texto: rec.guardar(texto, tema=tema, fuente="mi máquina virtual")) if rec else None
        try:
            return mq.hacer(maquina(), accion, carga, al_paso=lambda fr, t: paso(fr, t), guardar_ficha=guardar)
        except mq.MaquinaError as e:
            return {"texto": f"[x] {e}", "ok": False}
    o_limpia = o.rstrip(" .!¡?¿")
    m_t = re.match(_TEMA_MOVIL, o_limpia, flags=re.I)
    if m_t:
        import sincronia_kira as sc
        try:
            tema = sc.poner_tema_movil(core.dir, m_t.group("t"))
        except ValueError as e:
            return {"texto": f"[x] {e}", "ok": False}
        return {"texto": f"Hecho: el móvil se verá en «{tema['nombre']}» después de la próxima sincronía "
                         "(al volver a abrir la app)."}
    m_m = re.match(_MEJORA_MOVIL, o_limpia, flags=re.I)
    if m_m:
        return mejora_para_movil(core, m_m.group("p").strip(), paso)
    m_rp = re.match(r"^repiensa a fondo\s*:\s*(?:(?P<i>n[0-9a-f]{10})\s+)?(?P<t>.+)$", o_limpia, flags=re.I)  # v3.12
    if m_rp:
        paso(0.0, f"Vuelvo a pensar y experimentar «{m_rp.group('t')}»…")
        try:
            r = core.ciclo_una(semilla=m_rp.group("t").strip())
        finally:
            if m_rp.group("i"):
                marcar_nota(core, m_rp.group("i"), en_marcha="")
        return {"texto": (r or "No he sacado nada nuevo esta vez.") if isinstance(r, str) or r is None else str(r)}
    m_im = re.match(r"^implementa la mejora del cuaderno\s*:\s*(?P<i>n[0-9a-f]{10})", o_limpia, flags=re.I)
    if m_im:
        return implementar_nota(core, m_im.group("i"), paso)
    m_cm = re.match(r"^pasa a mejora el conocimiento\s*:\s*(?P<i>[ns][0-9a-f]{10})\s*(?P<t>.*)$", o_limpia, flags=re.I)
    if m_cm:
        return conocimiento_a_mejora(core, m_cm.group("i"), paso)
    p_ti = pedido_mejora_kiraos(o_limpia)          # v3.07: una mejora para MÍ (KiraOS): laboratorio + tus dos toques
    if p_ti:
        return mejora_para_kiraos(core, p_ti, paso)
    import apk_juegos_kira as apk_                 # v3.07: app ANDROID de verdad de cualquier programa
    p_apk = apk_.pedido_apk(o)
    if p_apk is not None:
        paso(0.0, "Preparo la app Android…")
        if not getattr(core, "ultimo_codigo", None):
            try:
                core.ultimo_codigo = maquina().ultimo_codigo
            except Exception:
                pass
        return core.app_android(p_apk.get("pedido"), al_paso=lambda fr, t: paso(fr, t))
    en_maquina = bool(re.search(_Y_PRUEBALO, o, flags=re.I))
    if en_maquina:
        o = re.sub(_Y_PRUEBALO, "", o, flags=re.I).strip()
    try:
        import internet_kira as ik_w
        o_web = ik_w.interpretar(o)
    except Exception:
        o_web = None
    if o_web is not None and o_web.get("accion") == "estudiar_enlaces":     # v3.03: estudio completo, con barra
        return {"texto": core.estudiar_pagina(o_web.get("url"), seguir=bool(o_web.get("seguir")),
                                              al_avance=lambda fr, t: paso(fr, t))}
    tema = None
    try:
        tema = core.es_estudia_general(o)
    except Exception:
        tema = None
    if tema:
        paso(0.0, f"Estudio {tema}: webs oficiales y cursos completos…")
        return {"texto": core.estudiar_a_fondo(tema, al_paso=lambda fr, t: paso(fr, t))}
    exp = ex.pedido_experimento(o)
    if exp is not None:
        paso(0.0, f"Experimento con {exp}…")
        r = core.experimentar(exp, al_progreso=lambda fr, t: paso(fr, t), mejorar=ex.quiere_mejorar(o))
        if r.get("ok") and r.get("codigo"):
            maquina().ultimo_codigo = r.get("codigo")
            core.ultimo_codigo = r.get("codigo")
            _crear_acceso(core, r.get("nombre") or exp, r.get("codigo"))   # v3.26: icono en el escritorio
        return {"texto": r.get("texto", ""), "codigo": r.get("codigo") if r.get("ok") else None,
                "nombre": r.get("nombre"), "ok": bool(r.get("ok"))}
    prog = pk.pedido_programa(o)
    if prog is not None:
        paso(0.0, f"Escribo el programa: {prog}…")
        r = core.programa_acordado(prog, al_paso=lambda t: paso(None, t))
        if not r.get("ok"):
            return {"texto": str(r.get("texto", "No me salió el programa.")).split("\n")[0], "ok": False}
        maquina().ultimo_codigo = r.get("codigo")
        core.ultimo_codigo = r.get("codigo")
        _crear_acceso(core, r.get("nombre") or prog, r.get("codigo"))      # v3.26: icono en el escritorio
        texto = "Programa escrito y probado en modo seguro en el portátil."
        if en_maquina:
            try:
                c, salida = maquina().probar_python(r.get("codigo") or "")
                texto += (" Y en mi máquina " + ("funciona" if c == 0 else f"falló (código {c})") + ":\n"
                          + (salida.strip() or "(sin salida)"))
            except mq.MaquinaError as e:
                texto += f" En mi máquina no pude probarlo: {e}"
        return {"texto": texto, "codigo": r.get("codigo"), "nombre": r.get("nombre"), "ok": True}
    cod = net.pedido_aprender_codigo(o)
    if cod is not None:
        return {"texto": core.aprender_codigo(cod, al_paso=lambda t: paso(None, t))}
    paso(None, "Pensando…")
    return {"texto": core.procesar_orden(o)}


# =====================================================================================
#  LAS TAREAS (una cada vez; el móvil pregunta cómo va)
# =====================================================================================
class Trabajos:
    """Las tareas del núcleo EN COLA (v2.95). Antes solo hacía una y, si estaba ocupada, decía 409. Ahora se pueden
    ENCOLAR varias: un solo obrero las va sacando de una en una. TUS órdenes van DELANTE de las de fondo. Se puede
    PAUSAR (deja de sacar nuevas; la de ahora sigue hasta que la PARES con cancelar) y SEGUIR."""

    def __init__(self, hacer, guardar=20):
        self._hacer = hacer            # hacer(orden, paso) -> dict
        self._lock = threading.Lock()
        self._hay = threading.Condition(self._lock)
        self.tareas = {}
        self.cola = []                 # tids esperando, en orden (las tuyas delante)
        self.actual = None
        self.pausada = False
        self._guardar = guardar
        self._obrero = threading.Thread(target=self._bucle, daemon=True)
        self._obrero.start()

    def ocupado(self):
        t = self.tareas.get(self.actual) if self.actual else None
        return bool(t and t["estado"] == "en curso")

    def parar_actual(self, borrar=False):
        """v3.18: «Parar»/«Borrar» la que se está haciendo. Queda MARCADA hasta que acabe (antes el «cancela» caducaba
        a los 25 s y, con el cerebro del Packard Bell leyendo varios minutos, la tarea seguía como si nada)."""
        with self._lock:
            t = self.tareas.get(self.actual) if self.actual else None
            if not t or t["estado"] != "en curso":
                return None
            t["parar"] = True
            if borrar:
                t["borrar_al_acabar"] = True
            return t["id"]

    def debe_parar(self):
        """¿Hay que parar la tarea en curso? (lo mira el núcleo en cada paso, junto a su «cancelado»)."""
        t = self.tareas.get(self.actual) if self.actual else None
        return bool(t and t.get("parar"))

    def en_cola(self):
        with self._lock:
            return len(self.cola)

    def pausar(self, si=True):
        with self._lock:
            self.pausada = bool(si)
            self._hay.notify_all()
        return self.pausada

    def empezar(self, orden, tuya=True):
        """Encola la orden y devuelve su id. Ya NO devuelve None por estar ocupada: se pone en la cola."""
        with self._lock:
            tid = uuid.uuid4().hex[:12]
            t = {"id": tid, "orden": str(orden)[:500], "estado": "en cola", "fraccion": 0.0, "avance": [],
                 "respuesta": "", "codigo": None, "nombre": None, "tuya": bool(tuya), "inicio": time.time()}
            self.tareas[tid] = t
            if tuya:                              # tu orden: delante de las de fondo (pero tras otras tuyas)
                pos = len(self.cola)
                for i, c in enumerate(self.cola):
                    if not self.tareas.get(c, {}).get("tuya"):
                        pos = i
                        break
                self.cola.insert(pos, tid)
            else:
                self.cola.append(tid)
            self._olvidar_viejas()
            self._hay.notify()
        return tid

    def _olvidar_viejas(self):
        acabadas = [k for k, v in self.tareas.items() if v["estado"] in ("hecho", "error", "cancelado", "quitado")]
        for viejo in sorted(acabadas, key=lambda k: self.tareas[k]["inicio"])[:-self._guardar]:
            self.tareas.pop(viejo, None)

    def _bucle(self):
        while True:
            with self._lock:
                while self.pausada or not any(not self.tareas.get(c, {}).get("retenida") for c in self.cola):
                    self._hay.wait(timeout=10)
                tid = next(c for c in self.cola if not self.tareas.get(c, {}).get("retenida"))   # v3.10: las paradas no
                self.cola.remove(tid)
                t = self.tareas[tid]
                t["estado"] = "en curso"
                self.actual = tid

            def paso(fr, texto, _t=t):
                if fr is not None:
                    try:
                        _t["fraccion"] = max(0.0, min(1.0, float(fr)))
                    except (TypeError, ValueError):
                        pass
                if texto:
                    _t["avance"] = (_t["avance"] + [str(texto)[:300]])[-40:]
            try:
                if t.get("parar"):                 # la paraste justo antes de empezar
                    raise _Parada("Parado.")
                r = self._hacer(t["orden"], paso) or {}
                if t.get("parar"):                 # se paró pero lo de dentro no lo dijo: cuenta como parada
                    raise _Parada("Parado.")
                t.update(respuesta=str(r.get("texto") or ""), codigo=r.get("codigo"), nombre=r.get("nombre"),
                         estado="hecho", fraccion=1.0, fin=time.time())
                if r.get("ok") is False and not str(t["respuesta"]).lstrip().startswith("[x]"):
                    t["respuesta"] = "[x] " + t["respuesta"]
            except Exception as e:                 # noqa: BLE001
                cancel = type(e).__name__ in ("Cancelada", "_Parada") or bool(t.get("parar"))
                t.update(estado="cancelado" if cancel else "error",
                         respuesta="Parado." if cancel else f"[x] {e}", fin=time.time())
            self._cerrar(t)
            with self._lock:
                if self.actual == tid:
                    self.actual = None
                if t.get("borrar_al_acabar"):
                    self.tareas.pop(tid, None)

    @staticmethod
    def _cerrar(t):
        """v3.10: apunta CÓMO acabó (implementado / mejorado / falló… y por qué)."""
        try:
            import cuaderno_clases_kira as cc
            t["resultado"], t["por_que"] = cc.resultado_tarea(t["estado"], t.get("respuesta", ""))
        except Exception:
            t["resultado"], t["por_que"] = t["estado"], str(t.get("respuesta", ""))[:160]

    def hechas(self, n=15):
        """v3.08: las últimas terminadas (para la pestaña «Tareas» del cuaderno), la más reciente primero."""
        with self._lock:
            ac = [t for t in self.tareas.values() if t["estado"] in ("hecho", "error", "cancelado", "quitado")]
        ac.sort(key=lambda t: -(t.get("fin") or t.get("inicio") or 0))
        return [{"id": t["id"], "orden": _sin_claves(t["orden"]), "estado": t["estado"], "fin": t.get("fin"),
                 "resultado": t.get("resultado", ""), "por_que": t.get("por_que", ""),
                 "respuesta": str(t.get("respuesta") or "")[:400]} for t in ac[:n]]

    # ---------- v3.10: botones Parar / Borrar / Empezar de cada tarea ----------
    def quitar(self, tid):
        """Borrar: si espera, sale de la cola y va a «Terminadas» como quitada (no se hace); si ya acabó, se borra el
        apunte. Devuelve 'quitada' | 'borrada' | 'en curso' | None."""
        with self._lock:
            t = self.tareas.get(tid)
            if t is None:
                return None
            if tid in self.cola:
                self.cola.remove(tid)
                t.update(estado="quitado", fin=time.time(), retenida=False)
                self._cerrar(t)
                return "quitada"
            if t["estado"] == "en curso":
                t["borrar_al_acabar"] = True
                return "en curso"
            self.tareas.pop(tid, None)
            return "borrada"

    def retener(self, tid, si=True):
        """Parar una que ESPERA: se queda en la lista pero no empieza hasta «Empezar»."""
        with self._lock:
            t = self.tareas.get(tid)
            if t is None or tid not in self.cola:
                return False
            t["retenida"] = bool(si)
            self._hay.notify_all()
            return True

    def adelantar(self, tid):
        """Empezar una que espera: la primera de la cola (y deja de estar parada)."""
        with self._lock:
            if tid not in self.cola:
                return False
            self.cola.remove(tid)
            self.cola.insert(0, tid)
            self.tareas[tid]["retenida"] = False
            self._hay.notify_all()
            return True

    def ver(self, tid):
        t = self.tareas.get(tid)
        if not t:
            return None
        d = {k: t[k] for k in ("id", "orden", "estado", "fraccion", "avance", "respuesta", "codigo", "nombre")}
        d["orden"] = _sin_claves(d["orden"])
        return d

    def lista(self):
        """Lo que hay ahora mismo (la de curso primero, luego las que esperan), para enseñarlo."""
        with self._lock:
            out = []
            a = self.tareas.get(self.actual) if self.actual else None
            if a and a["estado"] == "en curso":
                out.append({"orden": _sin_claves(a["orden"]), "estado": "en curso"})
            if a and a["estado"] == "en curso":
                out[-1]["id"] = a["id"]
            for c in self.cola:
                out.append({"id": c, "orden": _sin_claves(self.tareas.get(c, {}).get("orden", "")), "estado": "en cola",
                            "retenida": bool(self.tareas.get(c, {}).get("retenida"))})
            return out


# =====================================================================================
#  EL NÚCLEO (se puede reiniciar tras importar la memoria)
# =====================================================================================
class _Parada(Exception):
    pass


class Nucleo:
    def __init__(self, datos, crear=None, con_maquina=False):
        self.datos = datos
        self._crear = crear or self._crear_real
        self.con_maquina = con_maquina
        self.core = self._crear()
        self._enganchar()
        self.trabajos = Trabajos(self._hacer)
        self._lock_sinc = threading.Lock()

    def _hacer(self, orden, paso):
        try:
            self.core.nueva_tarea()                  # un «cancela» de antes no corta esta
        except Exception:
            pass
        r = ejecutar(self.core, orden, paso)
        if getattr(self.core, "pedir_reinicio", False):     # v3.11: tras ponerse las mejoras, se reinicia solo
            self.core.pedir_reinicio = False
            if reiniciar_proceso_luego():
                r = dict(r or {})
                r["texto"] = (str(r.get("texto") or "") + "\nMi núcleo se reinicia solo en unos segundos para usar "
                              "el código nuevo (las tareas que esperaban se pierden; vuelve a pedírmelas).")
        return r

    @staticmethod
    def _crear_real():
        import kira_god
        return kira_god.KiraGodCore()

    def _enganchar(self):
        try:                                     # v3.18: el «Parar» de la tarea vale hasta que acabe (no caduca)
            self.core.parar_extra = lambda: bool(getattr(self, "trabajos", None) and self.trabajos.debe_parar())
        except Exception:
            pass
        try:
            self.core.es_kiraos = True           # v3.02: soy KiraOS (no reenvío órdenes a KiraOS: sería a mí misma)
        except Exception:
            pass
        if self.con_maquina:
            try:
                enganchar_maquina(self.core)
            except Exception as e:                   # noqa: BLE001
                print(f"[núcleo] sin máquina para investigar: {e}", flush=True)

    def reiniciar(self):
        try:
            self.core.pensar_sola(False)
        except Exception:
            pass
        self.core = self._crear()
        self._enganchar()
        try:
            self.core.reanudar_pensar()
        except Exception:
            pass

    def importar_memoria(self, zip_ruta):
        if self.trabajos.ocupado():
            raise RuntimeError("Estoy haciendo algo; cuando acabe, mándame la memoria.")
        import memoria_kira as mk
        r = mk.importar(zip_ruta, self.datos)
        try:                                          # su nacimiento sigue siendo su primer recuerdo
            import nacimiento_kira as nk
            p = nk.cargar()
            if p:
                nk.primer_recuerdo(p, os.path.join(self.datos, "recuerdos"))
        except Exception:
            pass
        self.reiniciar()
        return r

    def pausar(self, si=True):
        """Pausa (o reanuda) el trabajo: la cola deja de sacar tareas nuevas y Kira deja de pensar sola. La tarea que
        esté en curso NO se corta (para eso está «parar»/cancelar). Al seguir, solo vuelve a pensar si lo estaba."""
        self.trabajos.pausar(si)
        try:
            if si:
                self._pensaba = bool(getattr(self.core, "_pensar_on", False))
                self.core.pensar_sola(False)
            elif getattr(self, "_pensaba", False):
                self.core.reanudar_pensar()
        except Exception:
            pass
        return {"pausada": self.trabajos.pausada}

    def seguir(self):
        return self.pausar(False)

    def tarea_accion(self, tid, accion):
        """v3.10: los botones de cada tarea. parar | borrar | empezar."""
        tb = self.trabajos
        t = tb.tareas.get(tid)
        if t is None:
            return {"ok": False, "texto": "Esa tarea ya no está."}
        curso = t["estado"] == "en curso"
        if accion == "parar":
            if curso:
                tb.parar_actual()
                try:
                    self.core.cancelar()
                except Exception:
                    pass
                return {"ok": True, "texto": "La paro. Saldrá en «Terminadas» como parada."}
            if tb.retener(tid, True):
                return {"ok": True, "texto": "Parada: se queda esperando hasta que pulses «Empezar»."}
            return {"ok": False, "texto": "Esa ya terminó."}
        if accion == "borrar":
            r = tb.quitar(tid)
            if r == "en curso":
                tb.parar_actual(borrar=True)
                try:
                    self.core.cancelar()
                except Exception:
                    pass
                return {"ok": True, "texto": "La paro y la borro de la lista."}
            if r == "quitada":
                return {"ok": True, "texto": "Quitada: no se hará. Está en «Terminadas» con el motivo."}
            return {"ok": True, "texto": "Borrada de la lista."}
        if accion == "empezar":
            if curso:
                return {"ok": False, "texto": "Ya la estoy haciendo."}
            if tid in tb.cola:
                tb.adelantar(tid)
                if tb.pausada:
                    self.seguir()
                return {"ok": True, "texto": "Es la siguiente: la empiezo en cuanto acabe lo de ahora."}
            nuevo = tb.empezar(t["orden"])
            if tb.pausada:
                self.seguir()
            return {"ok": True, "texto": "La vuelvo a hacer: está en la cola.", "id": nuevo}
        return {"ok": False, "texto": "No conozco ese botón."}

    def estado(self):
        """Estado ligero para la barra del escritorio (sin leer versión/recuerdos/equipo): ¿ocupada?, ¿cuántas en
        espera?, ¿pausada?, y qué está haciendo por su cuenta (pensar/estudiar/foco)."""
        t = self.trabajos.tareas.get(self.trabajos.actual) if self.trabajos.actual else None
        ocup = self.trabajos.ocupado()
        return {"ocupada": ocup,
                "haciendo": _sin_claves((t or {}).get("orden", "")) if ocup else "",
                "pizarra": pizarra_de(self.core) if ocup else None,          # v3.14: lo que escribe, EN VIVO
                "ultimo_codigo": self._ultimo_codigo(),
                "fraccion": float((t or {}).get("fraccion") or 0) if ocup else 0.0,      # v3.09: para el «termina en…»
                "inicio": (t or {}).get("inicio") if ocup else None,
                "avance": ((t or {}).get("avance") or [""])[-1] if ocup else "",
                "en_cola": self.trabajos.en_cola(), "pausada": self.trabajos.pausada,
                "cola": self.trabajos.lista(), "hechas": self.trabajos.hechas(), "actividad": actividad(self.core)}

    def _ultimo_codigo(self):
        """v3.14: el último código que escribió (de la última tarea con código, o el que recuerda el núcleo)."""
        with self.trabajos._lock:
            con = [t for t in self.trabajos.tareas.values() if t.get("codigo")]
        con.sort(key=lambda t: -(t.get("fin") or t.get("inicio") or 0))
        if con:
            t = con[0]
            return {"orden": _sin_claves(t["orden"]), "codigo": str(t["codigo"])[-20000:], "nombre": t.get("nombre"),
                    "cuando": t.get("fin") or t.get("inicio")}
        c = getattr(self.core, "ultimo_codigo", None)
        return {"orden": "", "codigo": str(c)[-20000:], "nombre": None, "cuando": None} if c else None

    def hola(self):
        rec = getattr(self.core, "recuerdos", None)
        try:
            n = rec.total() if rec is not None else 0
        except Exception:
            n = 0
        try:
            import version_kira as vk
            ver = vk.VERSION
        except Exception:
            ver = "?"
        llamar = ""
        try:
            import nacimiento_kira as nk
            llamar = (nk.cargar() or {}).get("llamar", "")
        except Exception:
            pass
        t = self.trabajos.tareas.get(self.trabajos.actual) if self.trabajos.actual else None
        return {"kira_nucleo": 1, "version": ver, "recuerdos": n, "llamar": llamar,
                "ocupada": self.trabajos.ocupado(), "haciendo": _sin_claves((t or {}).get("orden", "")) if self.trabajos.ocupado() else "",
                "en_cola": self.trabajos.en_cola(), "pausada": self.trabajos.pausada,
                "actividad": actividad(self.core), "equipo": equipo_corto(), "sincronia": sincronia_corta(self.datos),
                "fuera_ip": _ip_fuera()}

    def sincronizar(self, paquete):
        """v2.87: lo nuevo del móvil entra en KiraOS (se suma, no se borra) y le devuelve lo nuevo de KiraOS."""
        import sincronia_kira as sc
        with self._lock_sinc:
            return sc.aplicar_en_kiraos(self.datos, self.core.recuerdos, paquete)


def reiniciar_proceso_luego(segundos=15, salir=None):
    """v3.11: tras «implementa las mejoras», el núcleo se cierra para que systemd (Restart=always) lo abra con el
    código nuevo. Solo si lo lleva systemd (si lo lanzaste tú a mano, no: se apagaría). Devuelve si lo hará."""
    if not os.environ.get("INVOCATION_ID") and salir is None:
        return False
    salir = salir or (lambda: os._exit(0))
    t = threading.Timer(segundos, salir)
    t.daemon = True
    t.start()
    return True


def es_local(ip):
    """¿La petición viene de este mismo portátil (la ventana o la consola de Kira)?"""
    return str(ip or "") in ("127.0.0.1", "::1", "localhost") or str(ip or "").startswith("127.")


def _sin_claves(texto):
    """v3.14: una orden como «config github: ghp_…» nunca se enseña con la clave (barra, cuaderno, móvil)."""
    try:
        import ordenes_kira
        return ordenes_kira.ocultar_claves(texto)
    except Exception:
        return str(texto or "")


def pizarra_de(core):
    """v3.14: lo que el cerebro está escribiendo AHORA (el texto hasta ahora), si es reciente."""
    p = getattr(core, "pizarra", None) or {}
    if not p.get("inicio") or time.time() - float(p.get("cuando") or 0) > 900:
        return None                                 # v3.16: también vacía (= el cerebro aún lee las instrucciones)
    return {"texto": _sin_claves(str(p.get("texto") or "")[-12000:]), "inicio": p.get("inicio"), "cuando": p.get("cuando"),
            "primera": p.get("primera")}


def actividad(core):
    """Qué está haciendo la Kira del portátil (para el panel del móvil)."""
    d = {"pensando": bool(getattr(core, "_pensar_on", False)), "estudiando": bool(getattr(core, "_estudiando", False)),
         "foco": "", "pensamientos": 0, "soluciones": 0, "maquina": False}
    try:
        foco = json.load(open(os.path.join(core.dir, "foco.json"), encoding="utf-8"))
        if foco.get("activo"):
            d["foco"] = str(foco.get("tema", ""))[:80]
    except (OSError, ValueError, AttributeError):
        pass
    try:
        import pensador_kira as pn
        est = pn.cargar(os.path.join(core.dir, "pensamientos.json"))
        d["pensamientos"], d["soluciones"] = len(est.get("notas", [])), len(est.get("soluciones", {}))
    except Exception:
        pass
    m = _MAQUINA.get("m")
    try:
        d["maquina"] = bool(m and m.encendida())
    except Exception:
        pass
    r = _MAQUINA.get("red")
    if r is not None:
        d["internet"] = r.estado()
    try:
        import wifi_kira as wk
        d["wifi"] = wk.resumen_corto()
    except Exception:
        pass
    return d


def _ip_fuera():
    """v3.00: la dirección de Tailscale de este portátil (para que el móvil me encuentre fuera de casa), o None."""
    try:
        import fuera_kira
        return fuera_kira.ip_tailscale()
    except Exception:
        return None


def equipo_corto():
    try:
        import nacimiento_kira as nk
        e = nk.equipo()
        try:
            import shutil as _sh
            e["disco_libre_gb"] = _sh.disk_usage("/").free // (1000 ** 3)
        except OSError:
            pass
        try:
            with open("/proc/loadavg") as f:
                e["carga"] = f.read().split()[0]
        except OSError:
            pass
        try:
            with open("/proc/uptime") as f:
                e["encendido_h"] = round(float(f.read().split()[0]) / 3600, 1)
        except (OSError, ValueError):
            pass
        return e
    except Exception:
        return {}


def sincronia_corta(datos):
    try:
        import sincronia_kira as sc
        est = sc.estado_kiraos(datos)
        return {"ultima": est.get("ultima", 0), "recibidos": est.get("recibidos_total", 0)}
    except Exception:
        return {}


# =====================================================================================
#  EL SERVIDOR
# =====================================================================================
def crear_servidor(host, puerto, token, nucleo):
    class Manejador(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "KiraNucleo/1"

        def log_message(self, *a):
            pass

        def _json(self, codigo, d):
            cuerpo = json.dumps(d, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def _ok_token(self):
            t = self.headers.get("X-Kira-Token", "")
            if token and t and hmac.compare_digest(t.encode(), token.encode()):
                return True
            self._json(401, {"error": "token"})
            return False

        def _cuerpo_json(self, maximo=200_000):
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > maximo:
                return {}
            try:
                return json.loads(self.rfile.read(n).decode("utf-8"))
            except ValueError:
                return {}

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == "/salud":
                return self._json(200, {"ok": True})
            if not self._ok_token():
                return
            if u.path == "/hola":
                return self._json(200, nucleo.hola())
            if u.path == "/estado":
                return self._json(200, nucleo.estado())
            if u.path == "/ventanas":                   # v3.19: las ventanas que se ha añadido (solo este portátil)
                if not es_local(self.client_address[0]):
                    return self._json(403, {"error": "Solo desde el propio portátil."})
                try:
                    return self._json(200, {"ventanas": nucleo.core.ventanas_lista()})
                except Exception as e:                 # noqa: BLE001
                    return self._json(500, {"error": str(e)})
            if u.path == "/mejoras":                    # v3.07: solo desde este portátil
                if not es_local(self.client_address[0]):
                    return self._json(403, {"error": "Las mejoras de KiraOS solo se miran en el propio portátil."})
                try:
                    return self._json(200, mejoras_estado(nucleo.core))
                except Exception as e:                 # noqa: BLE001
                    return self._json(500, {"error": str(e)})
            if u.path == "/tarea":
                tid = (urllib.parse.parse_qs(u.query).get("id") or [""])[0]
                t = nucleo.trabajos.ver(tid)
                return self._json(200, t) if t else self._json(404, {"error": "no existe esa tarea"})
            self._json(404, {"error": "no existe"})

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            if not self._ok_token():
                return
            if u.path == "/orden":
                orden = str(self._cuerpo_json().get("orden") or "").strip()
                if not orden:
                    return self._json(400, {"error": "falta la orden"})
                if not es_local(self.client_address[0]):     # v2.88: desde el móvil, la WiFi con cuidado
                    import wifi_kira as wk
                    vale, porque = wk.permitida_remota(orden)
                    if not vale:
                        return self._json(403, {"error": porque})
                    import fuera_kira as fk_
                    if fk_.es_ip_tailscale(self.client_address[0]):   # v3.02: desde FUERA de casa, solo lo tranquilo
                        import mando_kira as mk_
                        vale, porque = mk_.permitida_fuera(orden)
                        if not vale:
                            return self._json(403, {"error": "Por seguridad, eso no lo hago si me lo pides desde "
                                                              "fuera de casa: toca el portátil o tu casa. Pídemelo "
                                                              "cuando estés en la misma WiFi."})
                tid = nucleo.trabajos.empezar(orden)   # v2.95: se encola (si está ocupada, espera su turno)
                return self._json(200, {"id": tid, "en_cola": nucleo.trabajos.en_cola()})
            if u.path == "/mejora":                     # v3.07: instalar/descartar/volver atrás, SOLO en el portátil
                if not es_local(self.client_address[0]):
                    return self._json(403, {"error": "Por seguridad, las mejoras de KiraOS solo se instalan desde el "
                                                     "propio portátil, con tus dos toques."})
                d = self._cuerpo_json()
                try:
                    return self._json(200, mejora_hacer(nucleo.core, str(d.get("accion") or ""),
                                                        str(d.get("nombre") or ""), d.get("confirmado") is True))
                except Exception as e:                 # noqa: BLE001
                    return self._json(500, {"ok": False, "texto": f"[x] {e}"})
            if u.path == "/cuaderno/accion":            # v3.12: botones del cuaderno (solo en el portátil)
                if not es_local(self.client_address[0]):
                    return self._json(403, {"error": "Eso solo desde el propio portátil."})
                d = self._cuerpo_json()
                try:
                    return self._json(200, cuaderno_accion(nucleo, str(d.get("accion") or ""), str(d.get("id") or "")))
                except Exception as e:                 # noqa: BLE001
                    return self._json(500, {"ok": False, "texto": f"[x] {e}"})
            if u.path == "/tarea/accion":               # v3.10: Parar / Borrar / Empezar (solo en el portátil)
                if not es_local(self.client_address[0]):
                    return self._json(403, {"error": "Eso solo desde el propio portátil."})
                d = self._cuerpo_json()
                return self._json(200, nucleo.tarea_accion(str(d.get("id") or ""), str(d.get("accion") or "")))
            if u.path == "/pausar":
                d = self._cuerpo_json()
                return self._json(200, nucleo.pausar(bool(d.get("si", True))))
            if u.path == "/seguir":
                return self._json(200, nucleo.seguir())
            if u.path == "/sincronizar":
                d = self._cuerpo_json(maximo=40_000_000)
                try:
                    resumen, respuesta = nucleo.sincronizar(d.get("paquete") or {})
                except (ValueError, TypeError) as e:
                    return self._json(400, {"error": str(e)})
                return self._json(200, {"ok": True, "resumen": resumen, "respuesta": respuesta})
            if u.path == "/cancelar":
                try:
                    nucleo.trabajos.parar_actual()
                except Exception:
                    pass
                try:
                    nucleo.core.cancelar()
                except Exception:
                    pass
                return self._json(200, {"ok": True})
            if u.path == "/memoria":
                n = int(self.headers.get("Content-Length") or 0)
                if n <= 0 or n > MAX_MEMORIA:
                    return self._json(413, {"error": "el paquete de memoria no vale (vacío o enorme)"})
                fd, tmp = tempfile.mkstemp(suffix=".zip")
                try:
                    with os.fdopen(fd, "wb") as f:
                        quedan = n
                        while quedan > 0:
                            trozo = self.rfile.read(min(1 << 20, quedan))
                            if not trozo:
                                break
                            f.write(trozo)
                            quedan -= len(trozo)
                    import memoria_kira as mk
                    r = nucleo.importar_memoria(tmp)
                    return self._json(200, {"ok": True, "texto": mk.texto_resumen(r, "recibido"), **{
                        k: r.get(k) for k in ("archivos", "origen")}})
                except Exception as e:
                    return self._json(400, {"ok": False, "error": str(e)})
                finally:
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
            self._json(404, {"error": "no existe"})

    return ThreadingHTTPServer((host, puerto), Manejador)


# =====================================================================================
#  CLIENTE (lo usa la ventana del portátil; el móvil usa casa_kira)
# =====================================================================================
class ClienteNucleo:
    def __init__(self, url, token, abrir=None):
        import urllib.request
        self.url, self.token = url.rstrip("/"), token
        self._abrir = abrir or urllib.request.urlopen

    def _pedir(self, ruta, datos=None, timeout=10):
        import urllib.request
        req = urllib.request.Request(self.url + ruta, data=None if datos is None else json.dumps(datos).encode(),
                                     method="GET" if datos is None else "POST",
                                     headers={"X-Kira-Token": self.token, "Content-Type": "application/json"})
        with self._abrir(req, timeout=timeout) as r:
            return json.loads(r.read(4_000_000).decode("utf-8"))

    def mejoras(self):
        return self._pedir("/mejoras", timeout=10)

    def ventanas(self):
        try:
            return self._pedir("/ventanas", timeout=5).get("ventanas") or []
        except Exception:
            return []

    def tarea_accion(self, tid, accion):
        return self._pedir("/tarea/accion", {"id": tid, "accion": accion}, timeout=10)

    def cuaderno_accion(self, accion, ident):
        return self._pedir("/cuaderno/accion", {"accion": accion, "id": ident}, timeout=15)

    def mejora(self, accion, nombre="", confirmado=False):
        return self._pedir("/mejora", {"accion": accion, "nombre": nombre, "confirmado": confirmado is True},
                           timeout=120)

    def hola(self):
        try:
            return self._pedir("/hola", timeout=3)
        except Exception:
            return {}

    def disponible(self):
        try:
            return self._pedir("/hola", timeout=2).get("kira_nucleo") == 1
        except Exception:
            return False

    def orden(self, texto, al_paso=None, cada=1.0, parar=None, espera_max=6 * 3600):
        """Manda la orden y espera el resultado contando los pasos. Devuelve la tarea final (dict).
        v2.94: si está ocupada (409), lo dice con buenas palabras en vez de soltar «HTTP Error 409»."""
        import urllib.error
        try:
            d = self._pedir("/orden", {"orden": texto})
            tid = d["id"]
            if d.get("en_cola"):                     # v2.95: hay cosas antes; se hará al llegar su turno
                if al_paso:
                    al_paso(None, "En cola: lo haré en cuanto acabe lo de antes.")
        except urllib.error.HTTPError as e:
            if e.code == 409:                        # núcleo antiguo (antes de la v2.95 no encolaba)
                hago = ""
                try:
                    dd = json.loads((e.read() or b"{}").decode("utf-8"))
                    act = [k for k, v in (dd.get("actividad") or {}).items() if v]
                    hago = (" (estoy con: " + ", ".join(act) + ")") if act else ""
                except Exception:
                    pass
                return {"estado": "ocupada",
                        "respuesta": "Estoy ocupada terminando lo anterior" + hago +
                                     ". Dame un momento y vuelve a pedírmelo."}
            raise
        vistos, fin, avisada = 0, time.time() + espera_max, False
        while time.time() < fin:
            t = self._pedir("/tarea?id=" + tid)
            for linea in t.get("avance", [])[vistos:]:
                if al_paso:
                    al_paso(t.get("fraccion"), linea)
            vistos = len(t.get("avance", []))
            if t.get("estado") not in ("en curso", "en cola"):   # v2.95: «en cola» también es esperar
                return t
            if parar and parar():
                self._pedir("/cancelar", {})
            time.sleep(cada)
        return {"estado": "error", "respuesta": "Ha tardado demasiado."}

    def estado(self):
        try:
            return self._pedir("/estado", timeout=4)
        except Exception:
            return {}

    def cancelar(self):
        try:
            return self._pedir("/cancelar", {})
        except Exception:
            return {"ok": False}

    def pausar(self, si=True):
        try:
            return self._pedir("/pausar", {"si": bool(si)})
        except Exception:
            return {"ok": False}

    def seguir(self):
        try:
            return self._pedir("/seguir", {})
        except Exception:
            return {"ok": False}


def main(argv=None):
    ap = argparse.ArgumentParser(description="La Kira completa en el portátil (el móvil le manda órdenes)")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--puerto", type=int, default=PUERTO)
    ap.add_argument("--datos", default=DATOS)
    ap.add_argument("--token", default=os.path.join(RAIZ, "kira_laboratorio", "token_lab.txt"))
    ap.add_argument("--sin-wifi", action="store_true", help="no vigilar la WiFi")
    ap.add_argument("--sin-maquina", action="store_true", help="investigar desde el portátil, no desde su máquina")
    a = ap.parse_args(argv)
    sys.path.insert(0, AQUI)
    import servidor_portatil as sp
    token = sp.leer_token(a.token)
    if len(token) < 16:
        sys.exit("No encuentro el token del laboratorio (arranca antes el laboratorio una vez: lo crea él).")
    preparar_datos(a.datos, token)
    os.environ.setdefault("KIRA_BAUL_PORTATIL", os.path.join(a.datos, "recuerdos"))
    nucleo = Nucleo(a.datos, con_maquina=not a.sin_maquina)
    if not a.sin_maquina:                       # v2.91: su máquina se enciende con ella (investiga desde ahí)
        threading.Thread(target=encender_maquina_al_arrancar, daemon=True).start()
    try:
        nucleo.core.reanudar_pensar()
    except Exception:
        pass
    if not a.sin_wifi:                          # v2.88: si la WiFi se cae, vuelve a conectar sola (redes guardadas)
        import wifi_kira as wk
        threading.Thread(target=wk.vigilar, daemon=True).start()
    srv = crear_servidor(a.host, a.puerto, token, nucleo)
    print(f"[núcleo] Kira completa escuchando en {a.host}:{a.puerto} (datos en {a.datos}).", flush=True)
    try:
        srv.serve_forever()
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
