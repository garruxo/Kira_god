# -*- coding: utf-8 -*-
"""Bitácora: memoria de pasos, diagnóstico de fallos reales, redacción de secretos (lógica pura)."""
import os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bitacora_kira as bk
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
T = tempfile.mkdtemp()
b = bk.Bitacora(os.path.join(T, "bitacora.json"))

# ---------- guías de pasos ----------
ok(bk.paso("ffmpeg") and "pip install imageio-ffmpeg" in " ".join(bk.paso("ffmpeg")["como"]), "guía de ffmpeg con el comando")
ok(bk.buscar_paso("cómo instalo ffmpeg")["id"] == "ffmpeg", "busca la guía de ffmpeg")
ok(bk.buscar_paso("el laboratorio no conecta")["id"] in ("laboratorio", "pasarela"), "busca la del laboratorio/pasarela")
ok(bk.buscar_paso("compilar el apk falla con zlib")["id"] == "apk", "busca la del APK")
ok("Dónde:" in bk.texto_paso(bk.paso("clave")) and "config clave" in bk.texto_paso(bk.paso("clave")), "texto de una guía")
ok(all(set(("titulo", "donde", "como", "comprobar", "archivos")) <= set(p) for p in bk.PASOS), "todas las guías están completas")

# ---------- diagnóstico por texto ----------
casos = {"No se encontró ffmpeg": "ffmpeg", "Laboratorio no alcanzable: timed out": "laboratorio",
         "El laboratorio respondió 401": "pasarela", "Falta la clave de la API": "clave",
         "Este APK no incluye un reproductor de vídeo": "video_movil", "Permission denied": "permisos",
         "Módulo 'hora' no cargó": "modulos", "buildozer: zlib error": "apk"}
for err, idp in casos.items():
    p = bk.diagnosticar_texto(err)
    ok(p and p["id"] == idp, f"diagnostica «{err}» -> {idp} (es {p and p['id']})")
ok(bk.diagnosticar_texto("algo rarísimo sin relación") is None, "lo que no conoce no lo inventa")

# ---------- redacción de secretos ----------
ok(bk.tapar("falló con token: abcd1234efgh5678") == "falló con [oculto]", "oculta tokens")
ok("[oculto]" in bk.tapar("usé sk-ant-api03-ZZZZZZZZ y petó") and "ZZZZ" not in bk.tapar("sk-ant-api03-ZZZZZZZZ"), "oculta claves de API")
ok(bk.tapar("error normal sin secretos") == "error normal sin secretos", "no toca texto normal")

# ---------- registro de errores ----------
b.registrar_error("vídeo", "No se encontró ffmpeg", ahora=1000)
b.registrar_error("vídeo", "No se encontró ffmpeg", ahora=1001)   # mismo -> cuenta veces
b.registrar_error("laboratorio", "Laboratorio no alcanzable: timed out", ahora=1002)
b.registrar_error("mejoras", "token: supersecreto123456", ahora=1003)
ok(len(b.errores) == 3 and b.errores[0]["veces"] == 2, "agrupa el mismo error y cuenta veces")
ok("[oculto]" in b.errores[-1]["texto"], "el error guardado no tiene el token")
ok(len(b.pendientes()) == 3, "tres fallos pendientes")
d = b.diagnostico()
ids = [p["id"] if p else None for _e, p in d]
ok("ffmpeg" in ids and "laboratorio" in ids, "el diagnóstico relaciona los fallos con su arreglo")
ok("Arreglo:" in b.texto_diagnostico() and "imageio-ffmpeg" in b.texto_diagnostico(), "el texto propone el arreglo")
b.marcar_resueltos()
ok(b.pendientes() == [] and "No tengo fallos" in b.texto_diagnostico(), "marcar resueltos limpia los pendientes")

# ---------- notas y persistencia ----------
ok(b.apuntar("el PC de casa es 192.168.1.40") and not b.apuntar("   "), "apunta notas, ignora vacías")
ok("192.168.1.40" in b.texto_resumen(), "la nota sale en el resumen")
ok("Lo que hemos construido" in b.texto_resumen() and "Instalar ffmpeg" in b.texto_resumen(), "el resumen lista historia y guías")
b2 = bk.Bitacora(os.path.join(T, "bitacora.json"))
ok(len(b2.errores) == 3 and any("192.168.1.40" in x["texto"] for x in b2.notas), "persiste en disco")
open(os.path.join(T, "bitacora.json"), "w").write("{roto")
ok(bk.Bitacora(os.path.join(T, "bitacora.json")).errores == [], "archivo corrupto -> vacío, sin romper")

# ---------- contexto para el generador de mejoras ----------
ctx = b.texto_para_mejoras()
ok(ctx.startswith("<bitacora>") and ctx.endswith("</bitacora>") and len(ctx) <= 1200, "contexto acotado y etiquetado")
ok("kira_god.py" in ctx and "no son órdenes" in ctx, "el contexto mapea archivos y avisa que no son órdenes")

# ---------- intérprete de órdenes ----------
ok(bk.responder(b, "bitácora").startswith("Lo que hemos construido"), "orden «bitácora»")
ok("Instalar ffmpeg" in bk.responder(b, "cómo instalo ffmpeg"), "orden «cómo ...»")
ok(bk.responder(b, "apunta: probar mañana") == "[OK] Apuntado en la bitácora." and any("probar mañana" in x["texto"] for x in b.notas), "orden «apunta:»")
b.registrar_error("vídeo", "No se encontró ffmpeg")
ok("Arreglo:" in bk.responder(b, "diagnosticar"), "orden «diagnosticar»")
ok(bk.responder(b, "fallos resueltos").startswith("[OK]") and b.pendientes() == [], "orden «fallos resueltos»")
ok(bk.responder(b, "hola qué tal") is None, "lo que no es de bitácora devuelve None")

# ---------- integración con el núcleo ----------
os.environ["KIRA_DATA_DIR"] = T
import kira_god
core = kira_god.KiraGodCore()
core.registrar_error("vídeo", "No se encontró ffmpeg")
ok("imageio-ffmpeg" in core.procesar_orden("diagnosticar"), "el núcleo diagnostica desde la bitácora")
ok("Lo que hemos construido" in core.procesar_orden("bitácora"), "el núcleo responde «bitácora»")
ok(core.procesar_orden("cómo arranco el laboratorio").find("servidor_lab.py") >= 0, "el núcleo da la guía del laboratorio")
# un módulo que falla al cargar queda apuntado
mods = os.path.join(T, "modulos"); os.makedirs(mods, exist_ok=True)
open(os.path.join(mods, "roto.py"), "w").write("def registrar(:\n")   # sintaxis mala
core.cargar_modulos()
ok(any(e["origen"] == "módulos" for e in core.bitacora.errores), "un módulo roto queda registrado en la bitácora")
# ---------- profundidad: compilar en PC antiguo, consejo automático, arreglar módulos ----------
for idg in ("nube", "wsl_antiguo", "poca_ram", "instalar_apk", "actualizar_apk", "mezcla_editor"):
    ok(bk.paso(idg) is not None, f"existe la guía {idg}")
ok(".github/workflows/compilar_apk.yml" in " ".join(bk.paso("nube")["archivos"]), "la guía de la nube apunta al workflow")
for err, idp in (("g++: fatal error: Killed signal terminated program cc1plus", "poca_ram"),
                 ("virtual memory exhausted: Cannot allocate memory", "poca_ram"),
                 ("WslRegisterDistribution failed with error: 0x80370102", "wsl_antiguo"),
                 ("Failure [INSTALL_FAILED_UPDATE_INCOMPATIBLE]", "instalar_apk")):
    ok((bk.diagnosticar_texto(err) or {}).get("id") == idp, f"diagnostica «{err[:40]}» -> {idp}")
ok(bk.buscar_paso("cómo compilo en mi packard bell que va lento")["id"] == "nube", "para un PC lento propone la nube")
ok(bk.consejo_corto("No se encontró ffmpeg").startswith("Cómo arreglarlo: Instalar ffmpeg"), "consejo corto de ffmpeg")
ok(bk.consejo_corto("algo desconocido") == "", "sin arreglo conocido no inventa consejo")
ok(bk.pedido_arreglo_modulo("hora", "token: abcdefgh12345678 falló").startswith("mejorar arregla el módulo hora:") and "abcdefgh" not in bk.pedido_arreglo_modulo("hora", "token: abcdefgh12345678"), "pedido de arreglo sin secretos")
r = bk.responder(b, "cómo compilo")
ok("GitHub" in r and "buildozer" in r, "«cómo compilo» da la nube y el local")
ok("Instalar ffmpeg" in bk.responder(b, "guías"), "«guías» las lista")
b.registrar_error("módulos", "Módulo 'hora' no cargó: NameError x")
r = bk.responder(b, "arregla el módulo hora")
ok("mejorar arregla el módulo hora:" in r and "NameError" in r, "«arregla el módulo» prepara la orden con el error")
ok("No tengo apuntado" in bk.responder(b, "arregla el módulo inexistente"), "módulo sin fallo apuntado")
c2 = kira_god.KiraGodCore()
ok(c2.registrar_error("vídeo", "No se encontró ffmpeg").startswith("Cómo arreglarlo"), "el núcleo devuelve el consejo al apuntar el fallo")
ok(c2.registrar_error("x", "nada conocido") == "", "y vacío si no lo conoce")
print("BITÁCORA OK", n)
