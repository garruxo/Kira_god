# -*- coding: utf-8 -*-
"""
kira_escritorio.py - La VENTANA de Kira en el portátil (sin móvil). Primer paso de «KiraOS en el portátil».

Una ventana sencilla (Tkinter, que viene con Python, no hay que instalar nada) para hablar con Kira usando el cerebro
grande del portátil: escribes abajo, la respuesta va apareciendo arriba. Botones para cambiar de cerebro y para ver
tu red (defensa). La parte de red es el mismo cliente probado de la consola (kira_consola.Cliente).

  python kira_escritorio.py                 ventana normal
  python kira_escritorio.py --pantalla      a pantalla completa (modo «KiraOS»: todo el portátil para Kira)

La lógica (qué hacer con cada mensaje) está en `manejar()`, que se prueba sin ventana (tests/test_escritorio.py).
"""
import argparse
import os
import sys
import threading

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import kira_consola as kc


# =====================================================================================
#  LÓGICA (sin ventana: se puede probar)
# =====================================================================================
def nucleo_para(cli):
    """El cliente de la Kira COMPLETA del portátil (nucleo_portatil, puerto 8771) en el mismo equipo que el cerebro."""
    import nucleo_portatil as np_
    host = cli.url.split("//", 1)[-1].split("/", 1)[0].rsplit(":", 1)[0]
    return np_.ClienteNucleo(f"http://{host}:{np_.PUERTO}", cli.token)


def manejar(cli, texto, escribir, al_trozo, nucleo=None, wifi=None, ctx=None):
    """Decide qué hacer con lo que escribe el usuario. `escribir(texto)` pone una línea; `al_trozo(t)` añade a la
    respuesta que va llegando. Devuelve una etiqueta de lo que hizo ('charla'|'defensa'|'cerebro'|'wifi'|'vacio'|
    'error'). v2.88: la WiFi del portátil se maneja AQUÍ mismo (`wifi`, por defecto wifi_kira); si hace falta una
    clave, deja `ctx["pedir_clave"] = red` para que la ventana la pida con puntitos."""
    t = texto.strip()
    if not t:
        return "vacio"
    bajo = t.lower()
    if wifi is None:
        import wifi_kira as wifi
    o = wifi.orden_wifi(t)
    if o is not None:
        if wifi.trae_clave(t):
            escribir(wifi.responder(t))
            return "wifi"
        try:
            escribir(wifi.hacer(o[0], o[1]))
        except wifi.WifiError as e:
            if o[0] == "conectar" and o[1] and "tiene clave" in str(e) and ctx is not None:
                ctx["pedir_clave"] = o[1]
                escribir(f"«{o[1]}» tiene clave: te la pido en una ventanita (sale con puntitos y no la guardo).")
            else:
                escribir(f"[x] {e}")
        return "wifi"
    if bajo in ("/rapido", "rápido", "/rápido", "cerebro rapido", "cerebro rápido"):
        cli.grande = False
        escribir("· Ahora uso el cerebro rápido.")
        return "cerebro"
    if bajo in ("/grande", "cerebro grande"):
        cli.grande = True
        escribir("· Ahora uso el cerebro grande.")
        return "cerebro"
    try:
        if bajo in ("/red", "mi red", "aparatos", "/aparatos"):
            escribir(kc.formato_defensa(cli.defensa("inventario")))
            return "defensa"
        if bajo.startswith(("/puertos", "puertos ")):
            partes = t.split()
            if len(partes) < 2:
                escribir("Dime qué aparato: por ejemplo «/puertos 192.168.1.50».")
            else:
                escribir(kc.formato_defensa(cli.defensa("puertos", host=partes[1])))
            return "defensa"
        if bajo.startswith(("/trafico", "/tráfico", "trafico", "tráfico")):
            partes = t.split()
            seg = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 20
            escribir(f"Mirando el tráfico de tu red {seg} s…")
            escribir(kc.formato_defensa(cli.defensa("trafico", segundos=seg)))
            return "defensa"
        if nucleo is not None and nucleo.disponible():     # v2.84: la Kira COMPLETA (estudia, piensa, programa…)
            r = nucleo.orden(t, al_paso=lambda _fr, linea: escribir("· " + linea))
            al_trozo(r.get("respuesta") or "Hecho.")
            if r.get("codigo"):
                escribir("── código (" + (r.get("nombre") or "programa") + ") ──\n" + r["codigo"])
            return "kira"
        cli.charla(t, al_trozo=al_trozo)
        return "charla"
    except kc.ConsolaError as e:
        escribir(f"[x] {e}")
        return "error"


def bienvenida(cli):
    try:
        h = cli.hola()
        cual = (h.get("cargado") and (h.get("cerebros") or {}).get(h["cargado"])) or "cerebro de casa"
        return f"Kira en «{h.get('nombre', 'el portátil')}» — {cual}. Escribe abajo para hablar conmigo."
    except kc.ConsolaError as e:
        return f"[x] No encuentro el cerebro de casa: {e}\n¿Está encendido? (servidor_portatil.py)"


# =====================================================================================
#  LA VENTANA (Tkinter)
# =====================================================================================
def construir(cli, pantalla_completa=False, raiz=None, nucleo=None):
    """Monta la ventana y la devuelve (sin arrancar el bucle): así se puede probar con una pantalla virtual."""
    import tkinter as tk
    from tkinter import scrolledtext, simpledialog
    import wifi_kira as wk

    FONDO, TXT, KIRA, TU = "#0f172a", "#e2e8f0", "#38bdf8", "#a7f3d0"
    raiz = raiz or tk.Tk()
    raiz.title("Kira")
    raiz.configure(bg=FONDO)
    raiz.geometry("820x620")
    if pantalla_completa:
        raiz.attributes("-fullscreen", True)
        raiz.bind("<Escape>", lambda e: raiz.attributes("-fullscreen", False))

    charla = scrolledtext.ScrolledText(raiz, wrap="word", bg=FONDO, fg=TXT, insertbackground=TXT,
                                       font=("DejaVu Sans", 13), bd=0, padx=14, pady=12)
    charla.pack(fill="both", expand=True)
    charla.tag_config("kira", foreground=KIRA)
    charla.tag_config("tu", foreground=TU)
    charla.tag_config("sis", foreground="#94a3b8")
    charla.configure(state="disabled")

    estado = tk.Label(raiz, text="", bg=FONDO, fg="#94a3b8", anchor="w", font=("DejaVu Sans", 10))
    estado.pack(fill="x", padx=14)

    abajo = tk.Frame(raiz, bg=FONDO)
    abajo.pack(fill="x", padx=10, pady=10)
    campo = tk.Entry(abajo, bg="#1e293b", fg=TXT, insertbackground=TXT, font=("DejaVu Sans", 13), bd=0)
    campo.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
    campo.focus_set()

    trabajando = {"si": False}

    def poner(texto, tag="sis", salto=True):
        charla.configure(state="normal")
        charla.insert("end", texto + ("\n" if salto else ""), tag)
        charla.see("end")
        charla.configure(state="disabled")

    def añadir_trozo(t):
        charla.configure(state="normal")
        charla.insert("end", t, "kira")
        charla.see("end")
        charla.configure(state="disabled")

    def en_hilo(fn):
        def correr():
            try:
                fn()
            finally:
                raiz.after(0, lambda: fin())
        threading.Thread(target=correr, daemon=True).start()

    def fin():
        trabajando["si"] = False
        estado.config(text="")
        boton.config(state="normal")
        campo.config(state="normal")
        campo.focus_set()

    def enviar(*_):
        if trabajando["si"]:
            return
        t = campo.get().strip()
        if not t:
            return
        campo.delete(0, "end")
        poner("Tú: " + wk.ocultar_clave(t), "tu")
        poner("Kira: ", "kira", salto=False)
        trabajando["si"] = True
        boton.config(state="disabled")
        campo.config(state="disabled")
        estado.config(text="Kira está pensando… (" + ("cerebro grande" if cli.grande else "rápido") + ")")

        ctx = {}

        def tarea():
            r = manejar(cli, t, lambda x: raiz.after(0, lambda: poner("\n" + x, "sis")),
                        lambda tr: raiz.after(0, lambda: añadir_trozo(tr)), nucleo=nucleo, ctx=ctx)
            raiz.after(0, lambda: poner("", "kira"))      # salto final
            if ctx.get("pedir_clave"):
                raiz.after(50, lambda: pedir_clave_y_conectar(ctx["pedir_clave"]))
        en_hilo(tarea)

    boton = tk.Button(abajo, text="Enviar", command=enviar, bg="#0ea5e9", fg="white", bd=0,
                      font=("DejaVu Sans", 12, "bold"), padx=16, activebackground="#0284c7")
    boton.pack(side="left", ipady=4)
    campo.bind("<Return>", enviar)

    barra = tk.Frame(raiz, bg=FONDO)
    barra.pack(fill="x", padx=10, pady=(0, 8))
    for texto, accion in (("Cerebro grande", lambda: cambia(True)), ("Rápido", lambda: cambia(False)),
                          ("Mi red", lambda: comando("/red")), ("WiFi", lambda: abrir_wifi())):
        tk.Button(barra, text=texto, command=accion, bg="#334155", fg=TXT, bd=0, font=("DejaVu Sans", 10),
                  padx=10, activebackground="#475569").pack(side="left", padx=(0, 6))

    def cambia(grande):
        cli.grande = grande
        estado.config(text="Cerebro " + ("grande" if grande else "rápido"))

    def comando(txt):
        campo.delete(0, "end")
        campo.insert(0, txt)
        enviar()

    # ---------- v2.88: la WiFi del portátil (KiraOS va a pantalla completa: aquí se maneja) ----------
    def wifi_en_hilo(fn, al_final=None):
        def correr():
            try:
                txt = fn()
            except wk.WifiError as e:
                txt = f"[x] {e}"
            except Exception as e:                       # noqa: BLE001 - que la ventana no se caiga nunca
                txt = f"[x] La WiFi falló: {e}"
            raiz.after(0, lambda: (poner("WiFi: " + str(txt), "sis"), al_final() if al_final else None))
        threading.Thread(target=correr, daemon=True).start()

    def pedir_clave_y_conectar(ssid, padre=None, al_final=None):
        clave = simpledialog.askstring("Clave de la WiFi", f"Clave de «{ssid}»\n(no se ve al escribirla y no la "
                                       "guardo en mi memoria; la guarda Linux):", show="*", parent=padre or raiz)
        if not clave:
            poner("WiFi: vale, no me conecto.", "sis")
            return
        poner(f"WiFi: me conecto a «{ssid}»…", "sis")
        wifi_en_hilo(lambda c=clave: wk.conectar(ssid, c), al_final)

    def abrir_wifi():
        win = tk.Toplevel(raiz)
        win.title("WiFi del portátil")
        win.configure(bg=FONDO)
        win.geometry("560x480")
        try:
            win.transient(raiz)
            win.lift()
            win.attributes("-topmost", True)            # que se vea encima de KiraOS a pantalla completa
        except Exception:
            pass
        info = tk.Label(win, text="Mirando la WiFi…", bg=FONDO, fg=TXT, wraplength=520, justify="left",
                        anchor="w", font=("DejaVu Sans", 11))
        info.pack(fill="x", padx=12, pady=(12, 6))
        lista = tk.Listbox(win, bg="#1e293b", fg=TXT, font=("DejaVu Sans", 12), selectbackground="#0ea5e9", bd=0,
                           height=10, activestyle="none")
        lista.pack(fill="both", expand=True, padx=12)
        vistas = []

        def refrescar():
            info.config(text="Buscando redes…")

            def leer():
                try:
                    return wk.estado(), wk.redes()
                except wk.WifiError as e:
                    return e, []

            def pintar(r):
                e, redes_ = r
                info.config(text=f"[x] {e}" if isinstance(e, Exception) else wk.texto_estado(e))
                lista.delete(0, "end")
                vistas[:] = redes_
                for x in redes_:
                    lista.insert("end", ("► " if x["en_uso"] else "   ") + f"{x['ssid']}   —   {x['senal']} %, "
                                 + ("con clave" if x["segura"] else "abierta") + (", la conozco" if x["guardada"] else ""))
            threading.Thread(target=lambda: (lambda r: raiz.after(0, lambda: pintar(r)))(leer()), daemon=True).start()

        def conectar_sel():
            sel = lista.curselection()
            if not sel:
                info.config(text="Elige una red de la lista.")
                return
            red = vistas[sel[0]]
            if red["segura"] and not red["guardada"]:
                pedir_clave_y_conectar(red["ssid"], padre=win, al_final=refrescar)
            else:
                poner(f"WiFi: me conecto a «{red['ssid']}»…", "sis")
                wifi_en_hilo(lambda s_=red["ssid"]: wk.conectar(s_), refrescar)

        fila = tk.Frame(win, bg=FONDO)
        fila.pack(fill="x", padx=12, pady=10)
        for texto, accion in (("Conectar", conectar_sel), ("Buscar otra vez", refrescar),
                              ("Arreglar", lambda: wifi_en_hilo(wk.reparar, refrescar)),
                              ("Desconectar", lambda: wifi_en_hilo(wk.desconectar, refrescar)),
                              ("Apagar", lambda: wifi_en_hilo(lambda: wk.radio(False), refrescar)),
                              ("Encender", lambda: wifi_en_hilo(lambda: wk.radio(True), refrescar)),
                              ("Cerrar", win.destroy)):
            tk.Button(fila, text=texto, command=accion, bg="#0ea5e9" if texto == "Conectar" else "#334155", fg="white",
                      bd=0, font=("DejaVu Sans", 10), padx=8, activebackground="#475569").pack(side="left", padx=(0, 5))
        lista.bind("<Double-Button-1>", lambda _e: conectar_sel())
        refrescar()
        return win

    poner(bienvenida(cli), "sis")
    raiz._kira_enviar = enviar          # para las pruebas
    raiz._kira_wifi = abrir_wifi
    return raiz


def ventana(cli, pantalla_completa=False, nucleo=None):
    if nucleo is None:
        try:
            nucleo = nucleo_para(cli)
        except Exception:
            nucleo = None
    construir(cli, pantalla_completa, nucleo=nucleo).mainloop()


def main(argv=None):
    ap = argparse.ArgumentParser(description="La ventana de Kira en el portátil")
    ap.add_argument("--url", default="http://127.0.0.1:8770")
    ap.add_argument("--pantalla", action="store_true", help="a pantalla completa (modo KiraOS)")
    ap.add_argument("--rapido", action="store_true")
    a = ap.parse_args(argv)
    token = kc.leer_token()
    if len(token) < 16:
        sys.exit("No encuentro el token del laboratorio (arranca antes el cerebro de casa).")
    cli = kc.Cliente(a.url, token)
    cli.grande = not a.rapido
    ventana(cli, pantalla_completa=a.pantalla)


if __name__ == "__main__":
    main()
