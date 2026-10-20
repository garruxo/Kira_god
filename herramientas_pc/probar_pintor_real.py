# -*- coding: utf-8 -*-
"""
probar_pintor_real.py - Prueba DE VERDAD el pintor y el buscador (lo usa .github/workflows/probar_pintor.yml):
  1. descarga los pinceles reales con pintor_kira (comprueba tamaño y huella sha256),
  2. pinta con el motor de verdad (stable-diffusion.cpp compilado para PC) y mide el tiempo,
  3. amplía una imagen ×4,
  4. busca y lee en internet con internet_kira (DuckDuckGo, Wikipedia, Stack Overflow, GitHub, un PDF).
Deja todo en salida_pruebas/ (imágenes + resumen.json) para revisarlo.
Uso: python herramientas_pc/probar_pintor_real.py <carpeta_del_motor> <carpeta_de_modelos>
"""
import hashlib
import json
import os
import shutil
import sys
import time
import traceback

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import pintor_kira as pk          # noqa: E402
import internet_kira as ik        # noqa: E402

MOTOR, MODELOS = sys.argv[1], sys.argv[2]
SAL = os.path.join(RAIZ, "salida_pruebas")
os.makedirs(SAL, exist_ok=True)
resumen = {"pintor": {}, "internet": {}}


def sha(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for trozo in iter(lambda: f.read(1 << 20), b""):
            h.update(trozo)
    return h.hexdigest()


def guardar():
    with open(os.path.join(SAL, "resumen.json"), "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=1)


def abrir_sin_proxy_raro(req, timeout=60):
    import urllib.request
    return urllib.request.urlopen(req, timeout=timeout)


# ---------- 1. pinceles ----------
datos = os.path.join(RAIZ, ".pruebas_datos")
os.makedirs(datos, exist_ok=True)
pin = pk.Pintor(datos, carpeta_binarios=MOTOR, abrir=abrir_sin_proxy_raro)
pin.carpeta_modelos = MODELOS                          # los modelos van en la carpeta que se guarda entre ejecuciones
pin.hilos = os.cpu_count() or 4
for id_ in list(pk.MODELOS) + ["ampliador"]:
    t0 = time.time()
    try:
        ruta = pin.descargar(id_)
        info = {"ok": True, "segundos": round(time.time() - t0, 1), "bytes": os.path.getsize(ruta)}
        if id_ != "ampliador":
            info["sha_ok"] = sha(ruta) == pk.MODELOS[id_]["sha256"]
        resumen["pintor"]["descarga_" + id_] = info
    except Exception as e:
        resumen["pintor"]["descarga_" + id_] = {"ok": False, "error": str(e)}
guardar()

# ---------- 2. pintar ----------
PRUEBAS = [("rapido", "a lighthouse on a rocky island at sunset, realistic photo, natural light", "cuadrada"),
           ("realista", "a lighthouse on a rocky island at sunset, realistic photo, natural light", "cuadrada"),
           ("realista", pk.preparar("un gato negro durmiendo en un sofá rojo, foto")["prompt"], "vertical"),
           ("rapido", pk.preparar("una acuarela de un velero en el mar")["prompt"], "horizontal")]
for i, (id_, prompt, formato) in enumerate(PRUEBAS):
    clave = f"pintar_{i}_{id_}_{formato}"
    textos = []
    try:
        r = pin.pintar(prompt, id_, formato, semilla=42, al_progreso=lambda f, t: textos.append(f"{f:.2f} {t}"),
                       vista=os.path.join(SAL, f"vista_{i}.png"))
        destino = os.path.join(SAL, f"{i}_{id_}_{formato}.png")
        shutil.copyfile(r["ruta"], destino)
        resumen["pintor"][clave] = {"ok": True, "segundos": r["segundos"], "prompt": prompt, "imagen": os.path.basename(destino),
                                    "progreso": textos[:3] + textos[-4:], "pasos_vistos": len(textos)}
    except Exception as e:
        resumen["pintor"][clave] = {"ok": False, "error": str(e), "prompt": prompt, "progreso": textos[-6:]}
    guardar()
try:
    with open(pin.ruta_log, "rb") as f:
        resumen["pintor"]["log_final"] = f.read()[-3000:].decode("utf-8", "replace")
except OSError:
    pass

# ---------- 2b. dibujos de un juego realista (personajes recortados) ----------
import juego_realista_kira as jr   # noqa: E402
import sprites_kira as spk         # noqa: E402
plan = jr.plan_simple("un caballero que esquiva dragones y recoge monedas en un castillo", pk.traducir_simple)
for nombre, desc in jr.dibujos(plan).items():
    try:
        t0 = time.time()
        r = pin.pintar(desc, "realista", "vertical" if nombre == "fondo" else "cuadrada", semilla=7)
        destino = os.path.join(SAL, f"juego_{nombre}.png")
        nota = spk.preparar_sprite(r["ruta"], destino, fondo=nombre == "fondo")
        resumen["pintor"][f"juego_{nombre}"] = {"ok": True, "segundos": round(time.time() - t0, 1), "nota": nota,
                                               "prompt": desc}
    except Exception as e:
        resumen["pintor"][f"juego_{nombre}"] = {"ok": False, "error": str(e)}
    guardar()

# ---------- 3. ampliar ----------
try:
    base = next(os.path.join(SAL, x) for x in sorted(os.listdir(SAL)) if x.startswith("0_") and x.endswith(".png"))
    t0 = time.time()
    r = pin.ampliar(base)
    shutil.copyfile(r, os.path.join(SAL, "0_ampliada_x4.png"))
    resumen["pintor"]["ampliar"] = {"ok": True, "segundos": round(time.time() - t0, 1)}
except StopIteration:
    resumen["pintor"]["ampliar"] = {"ok": False, "error": "no hay imagen base"}
except Exception as e:
    resumen["pintor"]["ampliar"] = {"ok": False, "error": str(e)}
guardar()

# ---------- 4. internet de verdad ----------
net = ik.Internet(os.path.join(datos, "internet"), abrir=abrir_sin_proxy_raro)
for clave, consulta, tipo in (("web", "cómo plantar tomates en maceta", "web"),
                               ("codigo", "python leer un archivo csv", "codigo"),
                               ("docs", "fotosíntesis apuntes", "docs")):
    try:
        res = net.buscar(consulta, tipo)
        info = {"ok": True, "n": len(res), "avisos": net.avisos, "resultados": res[:6]}
        lecturas = []
        for r in res[:3]:
            try:
                pag = net.leer(r["url"])
                lecturas.append({"url": r["url"], "tipo": pag["tipo"], "titulo": pag["titulo"], "letras": len(pag["texto"]),
                                 "codigos": len(pag["codigos"]), "principio": pag["texto"][:300]})
            except Exception as e:
                lecturas.append({"url": r["url"], "error": str(e)})
        info["lecturas"] = lecturas
        resumen["internet"][clave] = info
    except Exception as e:
        resumen["internet"][clave] = {"ok": False, "error": str(e), "traza": traceback.format_exc()[-800:]}
    guardar()
print(json.dumps({k: {kk: (vv.get("ok"), vv.get("segundos"), vv.get("error")) for kk, vv in v.items() if isinstance(vv, dict)}
                  for k, v in resumen.items()}, ensure_ascii=False, indent=1))
