# -*- coding: utf-8 -*-
"""Sala de Ciberseguridad (DEFENSIVA): escena 3D, info del dispositivo, revisión de hábitos, biblioteca de conceptos."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ciber_kira as ck, salas_kira as sk, habitacion_kira as hk
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
T = tempfile.mkdtemp()

# ---------- escena 3D ----------
e = sk.construir_ciber()
ok(80 < len(e) < 400, f"nº de caras razonable ({len(e)})")
ok(all(len(c[0]) >= 3 for c in e), "todas las caras tienen 3+ vértices")
ok(all(all(0 <= v <= 1.0001 for v in c[1]) for c in e), "colores en rango")
ok({c[4] for c in e if c[4]} == {"centro", "dispositivo", "regreso"}, f"hotspots: {sorted({c[4] for c in e if c[4]})}")
ok(sk.construir_ciber() == e, "escena determinista")
W, H = 360, 640
def centro(pose): return hk.hotspot_en(hk.render_caras(e, pose, W, H, niebla=sk.NIEBLA_CIBER), W/2, H/2)
for d, p in sk.CFG_CIBER["poses"].items():
    ok(centro(p) == d, f"mirando a '{d}' el centro de pantalla es ese objeto (es {centro(p)})")
et = hk.etiquetas(sk.POSE_X_MESA, W, H, None, sk.ANCLAS_X, sk.NOMBRES_X)
ok(any(t == "KIRA" for t, _x, _y in et), "el cartel KIRA se ve desde la consola")
r = sk.recorrido_ciber()
ok(r.cfg is sk.CFG_CIBER and r.estado == "caminando", "entra caminando")
for _ in range(120): r.paso(0.05)
ok(r.estado == "libre" and r.pose == sk.POSE_X_MESA, "llega a la consola")
r.ordenar("centro"); ev = None
for _ in range(60): ev = r.paso(0.05) or ev
ok(ev == "centro", "acercarse a la pantalla emite 'centro'")
# las otras salas no se tocan
ok(hk.Recorrido().cfg is hk.CFG_HACKER, "la Sala Hacker sigue intacta")

# ---------- intenciones ----------
for t, d in (("estudiar phishing", "centro"), ("quiero aprender a protegerme", "centro"), ("revisar seguridad", "centro"),
             ("ver el dispositivo", "dispositivo"), ("cuánta memoria hay", "dispositivo"), ("salir", "regreso"),
             ("volver al menú", "regreso"), ("zzz", None)):
    ok(sk.intencion_ciber(t) == d, f"intención '{t}' -> {d} (es {sk.intencion_ciber(t)})")

# ---------- info del dispositivo (solo lectura) ----------
info = ck.info_dispositivo()
ok(isinstance(info, list) and any(k == "Memoria RAM" for k, _v in info) and any(k == "Sistema" for k, _v in info), "da RAM y sistema")
ok(all(isinstance(k, str) and isinstance(v, str) for k, v in info), "todo son textos")

# ---------- revisión (solo lectura) ----------
os.makedirs(os.path.join(T, "x"), exist_ok=True)
# sin clave ni pasarela
items = ck.revision(T)
ok(all(len(it) == 3 and it[0] in ("ok", "aviso", "info") for it in items), "cada hallazgo es (nivel, texto, consejo)")
ok(any("clave" in it[1].lower() for it in items), "avisa de que no hay clave")
ok(any("copias" in (it[1] + it[2]).lower() for it in items), "recuerda las copias de seguridad")
# clave con permisos abiertos + pasarela débil + módulos con fallo
open(os.path.join(T, "api_key.txt"), "w").write("sk-xxxxxxxxxxxxxxxxxxxx")
if os.name == "posix": os.chmod(os.path.join(T, "api_key.txt"), 0o644)
json.dump({"url": "http://0.0.0.0:8765", "token": "corto"}, open(os.path.join(T, "pasarela.json"), "w"))
items = ck.revision(T, errores_modulos={"malo": "x"}, pasarela={"url": "http://0.0.0.0:8765", "token": "corto"})
txt = ck.texto_revision(items)
ok("0.0.0.0" in txt and "token" in txt.lower() and "módulo" in txt.lower(), "detecta laboratorio abierto, token corto y módulo roto")
ok(any(it[0] == "aviso" for it in items) and "aviso" in txt, "marca avisos")
ok("solo lectura" in txt.lower(), "deja claro que solo lee")
json.dump({"url": "http://127.0.0.1:8765", "token": "token-largo-de-sobra-123"}, open(os.path.join(T, "pasarela.json"), "w"))
items2 = ck.revision(T)
ok(any(it[0] == "ok" and "token" in it[1].lower() for it in items2), "con token largo: ok")

# ---------- biblioteca de conceptos (educación defensiva) ----------
ok(len(ck.CONCEPTOS) >= 8 and all({"id", "nombre", "que_es", "protegerse"} <= set(c) for c in ck.CONCEPTOS), "conceptos completos")
ok(all(c["protegerse"] for c in ck.CONCEPTOS), "cada concepto dice cómo protegerse")
for t, idc in (("phishing", "phishing"), ("me quieren robar la contraseña", "contrasenas"), ("un virus en el móvil", "malware"),
               ("secuestro de archivos", "ransomware"), ("wifi del bar", "wifi")):
    c = ck.buscar_concepto(t); ok(c and c["id"] == idc, f"buscar '{t}' -> {idc} (es {c and c['id']})")
tx = ck.texto_concepto(ck.POR_ID["phishing"])
ok("Cómo protegerse" in tx and "2FA" in tx and "no ejecuta" in tx.lower(), "el texto enseña defensa y recuerda el blindaje")
# ningún concepto da instrucciones de ataque (comprobación defensiva de tono)
todo = " ".join(c["que_es"] + " " + " ".join(c["protegerse"]) for c in ck.CONCEPTOS).lower()
ok(not any(p in todo for p in ("cómo crear", "cómo hackear", "payload", "exploit para", "paso 1 para atacar")), "el contenido es defensivo, no ofensivo")

# ---------- progreso de estudio (solo guarda estados) ----------
ap = ck.Aprendizaje(os.path.join(T, "ap.json"))
ok(ap.estado("phishing") == "por_estudiar", "por defecto, por estudiar")
ok(ap.marcar("phishing", "estudiado") and ap.estado("phishing") == "estudiado", "marca estudiado")
ok(ap.marcar("malware", "aplicado") and not ap.marcar("malware", "zzz") and not ap.marcar("no_existe", "estudiado"), "valida id y estado")
ok(len(ap.listar("estudiado")) == 1 and len(ap.listar("aplicado")) == 1, "lista por estado")
ok("estudiados: 1" in ap.resumen() and "aplicas: 1" in ap.resumen(), "resumen de progreso")
ap2 = ck.Aprendizaje(os.path.join(T, "ap.json"))
ok(ap2.estado("phishing") == "estudiado", "persiste en disco")
open(os.path.join(T, "ap.json"), "w").write("{roto")
ok(ck.Aprendizaje(os.path.join(T, "ap.json")).estado("phishing") == "por_estudiar", "archivo corrupto -> por defecto")
# el archivo guardado SOLO tiene estados, nunca contenido ejecutable
ap.marcar("wifi", "estudiado")
guardado = open(os.path.join(T, "ap.json")).read()
ok(set(json.loads(guardado).values()) <= set(ck.ESTADOS), "solo se guardan estados de estudio")
# ---------- profundidad: más conceptos, «qué hago si», preguntas defensivas, revisiones nuevas ----------
ok(len(ck.CONCEPTOS) >= 18 and len(ck.POR_ID) == len(ck.CONCEPTOS), "18+ conceptos y sin ids repetidos")
for t, idc in (("me llega un sms de un paquete", "smishing"), ("me llaman del soporte técnico", "vishing"), ("escaneé un qr", "qr"),
               ("duplicado de la sim", "sim"), ("el router de casa", "router"), ("mi perfil de instagram", "redes_sociales"),
               ("whatsapp web abierto", "sesiones"), ("una tienda online con chollos", "compras"), ("dime algo simple", None)):
    c = ck.buscar_concepto(t); ok((c["id"] if c else None) == idc, f"buscar '{t}' -> {idc} (es {c and c['id']})")
ok(len(ck.CASOS) >= 5 and all(len(c["pasos"]) >= 3 for c in ck.CASOS), "casos con pasos")
for t, idc in (("me han robado la cuenta", "cuenta_robada"), ("he pulsado un enlace raro", "enlace"), ("creo que tengo un virus", "virus"),
               ("perdí el móvil", "perdido"), ("me llamó mi banco y le di el código", "llamada_banco")):
    c = ck.buscar_caso(t); ok(c and c["id"] == idc, f"caso '{t}' -> {idc} (es {c and c['id']})")
tc = ck.texto_caso(ck.CASOS[0]); ok("en orden" in tc and "1." in tc and "banco" in tc, "texto del caso con pasos numerados")
ok(ck.respuesta_local("he pulsado un enlace raro").startswith("He pulsado") and ck.respuesta_local("qué es el phishing").startswith("Phishing"), "respuesta local: casos y conceptos")
ok(ck.respuesta_local("xyzzy") is None, "lo que no está en la biblioteca no se inventa")
sd = ck.SISTEMA_DEFENSA.lower()
ok("solo das información defensiva" in sd and "nunca des pasos, código" in sd and "aunque se presente como estudio" in sd, "el modo de la IA es estrictamente defensivo")
for malo in ("", "   ", "\x00\x01"):
    try: ck.limpiar_pregunta(malo); ok(False, "pregunta vacía")
    except ValueError: ok(True, "pregunta vacía rechazada")
ok(len(ck.limpiar_pregunta("a" * 900)) == ck.MAX_PREGUNTA, "la pregunta se recorta")
# revisión: secretos guardados por error y módulos instalados
T2 = tempfile.mkdtemp()
open(os.path.join(T2, "notas.json"), "w").write('[{"id":1,"texto":"mi clave sk-ant-api03-AAAAAAAAAAAAAAAAAAAA"}]')
os.makedirs(os.path.join(T2, "modulos")); open(os.path.join(T2, "modulos", "hora.py"), "w").write("x=1")
txt = ck.texto_revision(ck.revision(T2))
ok("notas.json" in txt and "clave o token" in txt, "detecta una clave guardada por error en las notas")
ok("1 módulo(s)" in txt and "hora" in txt, "informa de los módulos instalados")
ok("sk-ant" not in txt, "la revisión no muestra la clave")
T3 = tempfile.mkdtemp(); ok("No hay claves ni tokens" in ck.texto_revision(ck.revision(T3)), "sin secretos: ok")
# núcleo: explicar_defensa
os.environ["KIRA_DATA_DIR"] = T3
import kira_god
core = kira_god.KiraGodCore(); core._leer_clave = lambda: ""
r, o = core.explicar_defensa("me han robado la cuenta"); ok(o == "local" and "Qué hacer" in r, "sin clave: responde con la biblioteca")
r, o = core.explicar_defensa("algo que no está"); ok(o == "local" and "clave de la API" in r, "sin clave y sin tema: lo dice")
vistos = []
core._leer_clave = lambda: "clave-falsa"
core._llamar_api = lambda clave, system, usuario, max_tokens=4000, mensajes=None: (vistos.append((system, usuario, max_tokens)), "Para protegerte, activa la verificación en dos pasos.")[1]
r, o = core.explicar_defensa("cómo me protejo del ransomware")
ok(o == "ia" and "dos pasos" in r and "solo explica la defensa" in r, "con clave: respuesta de la IA con aviso de blindaje")
ok(vistos and vistos[0][0] == ck.SISTEMA_DEFENSA and vistos[0][2] <= 500, "usa el modo defensivo y un límite de longitud")
def caida(*a, **k): raise RuntimeError("sin red")
core._llamar_api = caida
r, o = core.explicar_defensa("phishing"); ok(o == "local" and "Phishing" in r, "sin red: cae a la biblioteca local")
ok("017" in ck.texto_caso(ck.CASOS[0]) and "incibe.es" in ck.texto_caso(ck.CASOS[0]), "cada caso recuerda el 017 de INCIBE")
ok(all(u.startswith("https://www.incibe.es/") for _t, u, _d in ck.RECURSOS) and "017" in ck.texto_recursos(), "recursos oficiales de INCIBE")
print("CIBER OK", n)
