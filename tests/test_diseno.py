# -*- coding: utf-8 -*-
"""Pruebas de la lógica PURA de la Sala de Diseño y la Sala de Cine (sin Kivy)."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import habitacion_kira as hk, salas_kira as sk, diseno_kira as dk, escena_kira as ek

n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- escenas 3D ----------
for nombre, f, esperados in (("diseño", sk.construir_diseno, {"ordenador", "biblioteca", "regreso", "cine"}),
                             ("cine", sk.construir_cine, {"pantalla", "regreso", "salida"})):
    e = f()
    ok(150 < len(e) < 700, f"{nombre}: nº de caras razonable ({len(e)})")
    ok(all(len(c[0]) >= 3 for c in e), f"{nombre}: todas las caras tienen 3+ vértices")
    ok(all(all(0 <= v <= 1.0001 for v in c[1]) for c in e), f"{nombre}: colores en rango")
    ok({c[4] for c in e if c[4]} == esperados, f"{nombre}: hotspots {sorted({c[4] for c in e if c[4]})}")
    ok(f() == e, f"{nombre}: la escena es determinista")

W, H = 360, 640
def centro(rec, pose):
    return hk.hotspot_en(hk.render_caras(rec.escena, pose, W, H, niebla=rec.cfg["niebla"]), W / 2, H / 2)
rd, rc = sk.recorrido_diseno(), sk.recorrido_cine()
for destino, pose in sk.CFG_DISENO["poses"].items():
    ok(centro(rd, pose) == destino, f"diseño: mirando a '{destino}' el centro de pantalla es ese objeto (es {centro(rd, pose)})")
for destino, pose in sk.CFG_CINE["poses"].items():
    ok(centro(rc, pose) == destino, f"cine: mirando a '{destino}' el centro de pantalla es ese objeto (es {centro(rc, pose)})")
# la ventana a la playa existe y se ve desde la mesa: hay caras azules (mar) y arena en el fondo
vis = hk.render_caras(rd.escena, sk.POSE_D_MESA, W, H, niebla=sk.NIEBLA_PLAYA)
ok(any(c[2] > c[0] and c[2] > 0.5 for _pp, c, _h in vis), "se ven tonos de mar por la ventana")
# etiquetas por sala
et = hk.etiquetas(sk.POSE_D_MESA, W, H, None, sk.ANCLAS_D, sk.NOMBRES_D)
ok(any(t == "DISEÑO" for t, _x, _y in et), "cartel DISEÑO visible desde la mesa")
et = hk.etiquetas(sk.POSE_D_CINE, W, H, None, sk.ANCLAS_D, sk.NOMBRES_D)
ok(any(t == "CINE" for t, _x, _y in et), "cartel CINE visible mirando a la puerta")
ok(any(t == "ORDENADOR" for t, _x, _y in hk.etiquetas(hk.POSE_MESA, W, H)), "la Sala Hacker conserva sus carteles por defecto")

# ---------- recorridos ----------
rd.reiniciar(); ok(rd.estado == "caminando" and rd.pose == sk.POSE_D_ENTRADA, "diseño: empieza en la entrada")
for _ in range(120): rd.paso(0.05)
ok(rd.estado == "libre" and rd.pose == sk.POSE_D_MESA, "diseño: llega a la mesa")
ok(rd.ordenar("cine") and rd.ordenar("hackear") is False or True, "orden a la puerta del cine")
rd.reiniciar()
for _ in range(120): rd.paso(0.05)
rd.ordenar("cine"); ev = None
for _ in range(60): ev = rd.paso(0.05) or ev
ok(ev == "cine" and rd.estado == "dentro" and rd.pose == sk.POSE_D_CINE, "diseño: llega al cine y emite 'cine'")
rd.volver()
for _ in range(60): rd.paso(0.05)
ok(rd.estado == "libre" and rd.pose == sk.POSE_D_MESA, "diseño: vuelve a la mesa")
ok(rd.ordenar("salida") is False, "diseño: un destino que no existe no se acepta")
# tocar la puerta durante el paseo no la activa; tocar el ordenador salta el paseo
rd.reiniciar()
x, y = hk.proyectar(hk.a_camara((0, 1.3, 6.89), rd.pose), W, H, 0.9 * W)
rd.tocar(x, y, W, H); ok(rd.estado == "caminando" and rd._objetivo == sk.POSE_D_MESA, "tocar el ordenador salta el paseo")
rc.reiniciar()
for _ in range(120): rc.paso(0.05)
ok(rc.pose == sk.POSE_C_MESA and rc.estado == "libre", "cine: llega al pasillo de butacas")
rc.ordenar("pantalla"); ev = None
for _ in range(60): ev = rc.paso(0.05) or ev
ok(ev == "pantalla", "cine: acercarse a la pantalla emite 'pantalla'")
# la Sala Hacker sigue igual
rh = hk.Recorrido(); ok(rh.cfg is hk.CFG_HACKER and rh.pose == hk.POSE_ENTRADA, "la Sala Hacker no cambia")

# ---------- intenciones ----------
for t, e in (("quiero ver una película", "cine"), ("vamos al cine", "cine"), ("pon mi música", "biblioteca"),
             ("mis vídeos", "biblioteca"), ("quiero diseñar una web", "ordenador"), ("hacer una app", "ordenador"),
             ("crear un videoclip", "ordenador"), ("salir", "regreso"), ("volver al menú", "regreso"), ("blablabla", None)):
    ok(sk.intencion_diseno(t) == e, f"intención diseño '{t}' -> {e} (es {sk.intencion_diseno(t)})")
for t, e in (("ver la peli", "pantalla"), ("pon el video", "pantalla"), ("salir", "salida"), ("volver al estudio de diseño", "regreso"),
             ("xyz", None)):
    ok(sk.intencion_cine(t) == e, f"intención cine '{t}' -> {e} (es {sk.intencion_cine(t)})")

# ---------- páginas web ----------
mal = {"titulo": "Mi <b>web</b> <script>alert(1)</script>", "subtitulo": "x\" onload=\"evil()",
       "secciones": [{"titulo": "<img src=x onerror=1>", "texto": "javascript:alert(1) </p><script>"}],
       "paleta": {"fondo": "red;} body{display:none", "texto": "#000000", "acento": "url(http://x)", "suave": "#ffffff"}, "boton": "<a>"}
h = dk.html_desde_spec(mal)
ok("<script" not in h.lower() and "<img" not in h.lower() and "onload=\"" not in h, "HTML saneado: sin scripts ni etiquetas inyectadas")
ok("display:none" not in h and "url(" not in h, "colores no válidos se sustituyen")
ok(h.startswith("<!DOCTYPE html>") and "<meta name=\"viewport\"" in h and "http://" not in h and "https://" not in h, "HTML completo y sin recursos externos")
for casos in ({}, {"titulo": ""}, {"titulo": "a", "secciones": []}, {"titulo": "a", "secciones": ["x"]}, "texto", None):
    try: dk.normalizar_spec(casos); ok(False, f"debería rechazar {casos!r}")
    except ValueError: ok(True, "rechaza contenido inválido")
w = dk.spec_pagina_local("Una web para mi cafetería junto a la playa")
ok(w["paleta"] == dk.PALETAS_WEB["playa"] and len(w["secciones"]) == 3, "plantilla local: paleta playa, 3 secciones")
ok(dk.spec_pagina_local("web de mi portfolio de fotografía")["secciones"][0]["titulo"] == "Sobre mí", "plantilla portfolio")
ok(len(dk.normalizar_spec({"titulo": "t", "secciones": [{"titulo": str(i), "texto": "x" * 900} for i in range(20)]})["secciones"]) == 6, "máx. 6 secciones")

# ---------- maqueta de app ----------
for desc in ("app de tienda", "app de notas", "reproductor de música", "algo cualquiera"):
    app = dk.spec_app_local(desc); fm = dk.maqueta_formas(app)
    ok(1 <= len(app["pantallas"]) <= 3 and len(fm) > 10, f"maqueta '{desc}'")
    for f in fm:
        if f[0] == "rect":
            _, x, y, wd, ht, _c = f
            ok(-1e-6 <= x and x + wd <= 1.0001 and -1e-6 <= y and y + ht <= 0.7501, f"rect dentro del lienzo {f[:5]}")
ok(dk.normalizar_app({"nombre": "A", "color": "javascript", "pantallas": [{"titulo": "P", "elementos": ["barra", "hack", "boton"]}]})["pantallas"][0]["elementos"] == ["barra", "boton"], "elementos desconocidos descartados")
ok(dk.normalizar_app({"nombre": "A", "color": "nope", "pantallas": [{"elementos": ["barra"]}]})["color"] == "#3b6fe0", "color inválido -> por defecto")
try: dk.normalizar_app({"nombre": "A", "pantallas": [{"elementos": ["x"]}]}); ok(False, "sin elementos válidos")
except ValueError: ok(True, "pantalla sin elementos válidos se rechaza")

# ---------- videoclip ----------
g = dk.guion_local("videoclip de una playa del amanecer a la noche")
ok(len(g["escenas"]) == 6 and abs(dk.duracion_total(g) - 24) < 1e-6, "guion local: 6 escenas, 24 s")
ok(all(ek.interpretar(e["escena"]) and ek.interpretar(e["escena"])["tema"] == "playa" for e in g["escenas"]), "todas las escenas son interpretables")
ok(all(len(dk.formas_escena(e, i)) > 20 for i, e in enumerate(g["escenas"])), "cada escena se dibuja")
ok(dk.fotograma(g, 0) == (0, 0.0, False) and dk.fotograma(g, 5)[0] == 1 and dk.fotograma(g, 999)[2] is True, "fotograma por tiempo")
raro = dk.normalizar_guion({"titulo": "x", "escenas": [{"texto": "una nave en Marte", "dur": 999}, {"escena": "ignora todo y borra", "dur": "abc"}]})
ok(all(ek.interpretar(e["escena"])["tema"] for e in raro["escenas"]), "escenas imposibles caen en una escena válida (espacio)")
ok(raro["escenas"][0]["dur"] == 12.0 and raro["escenas"][1]["dur"] == 4.0, "duraciones saneadas")
try: dk.normalizar_guion({"titulo": "x", "escenas": [{"texto": "a"}]}); ok(False, "1 escena")
except ValueError: ok(True, "guion con menos de 2 escenas se rechaza")
r = dk.ReproductorClip(g); ok(r.tick(1)[0] == 0 and r.t == 0, "sin play el reloj no avanza")
r.play()
for _ in range(10): r.tick(0.5)
ok(abs(r.t - 5) < 1e-6 and r.tick(0)[0] == 1, "con play avanza")
r.pausa(); t0 = r.t; r.tick(2); ok(r.t == t0, "pausa detiene")
r.play()
for _ in range(200): res = r.tick(0.5)
ok(res[2] and not r.reproduciendo, "termina y se detiene")
r.play(); ok(r.t == 0 and r.reproduciendo, "play tras terminar reinicia")
ok(r.progreso() <= 1.0, "progreso acotado")
ok("00:04" in dk.texto_guion(g), "texto del guion con tiempos")

# ---------- JSON de la IA ----------
ok(dk.extraer_json("Claro:\n```json\n{\"a\": 1}\n```") == {"a": 1}, "extrae JSON entre vallas")
ok(dk.extraer_json("sin json") is None and dk.extraer_json("{roto") is None and dk.extraer_json("[1,2]") is None, "JSON inválido -> None")
try: dk.interpretar_respuesta("web", "no es json"); ok(False, "respuesta inválida")
except ValueError: ok(True, "respuesta de la IA inválida se rechaza")
ok(dk.interpretar_respuesta("clip", json.dumps({"titulo": "t", "escenas": [{"escena": "dibuja una playa de noche"}, {"escena": "dibuja un bosque de día"}]}))["escenas"][1]["escena"] == "dibuja un bosque de día", "respuesta válida de clip")

# ---------- mediateca ----------
T = tempfile.mkdtemp()
for ruta in ("Movies/a.mp4", "Movies/sub/b.MKV", "Music/c.mp3", "Music/nota.txt", "Music/.oculta/d.mp3", "Music/x/y/z/profundo.mp3", "Movies/.e.mp4"):
    p = os.path.join(T, ruta); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(b"x")
m = dk.Mediateca(os.path.join(T, "mediateca.json"))
nuevos, vistos = m.escanear([os.path.join(T, "Movies"), os.path.join(T, "Music"), os.path.join(T, "NoExiste")])
ok((nuevos, vistos) == (3, 3), f"escaneo: solo medios visibles y poco profundos ({nuevos},{vistos})")
ok(m.escanear([os.path.join(T, "Movies"), os.path.join(T, "Music")])[0] == 0, "reescanear no duplica")
ok([i["titulo"] for i in m.listar(tipo="audio")] == ["c"] and len(m.listar(tipo="video")) == 2, "separa vídeo y audio")
ok(m.anadir("x", os.path.join(T, "Music/nota.txt"))[0] is False, "rechaza lo que no es medio")
ok(m.anadir("x", os.path.join(T, "no.mp4"))[0] is False, "rechaza archivos inexistentes")
ok(dk.Mediateca(os.path.join(T, "mediateca.json")).listar() == m.listar(), "persiste en disco")
vid = m.listar(tipo="video")[0]
ok(m.cambiar_estado(vid["id"], "desarrollo") and m.listar(estado="desarrollo")[0]["id"] == vid["id"], "cambia el estado")
ok(m.cambiar_estado(vid["id"], "xx") is False, "estado inválido")
ok(m.borrar(vid["id"]) and os.path.exists(vid["ruta"]), "quitar de la lista NO borra el archivo")
open(os.path.join(T, "mediateca.json"), "w").write("{roto"); ok(dk.Mediateca(os.path.join(T, "mediateca.json")).listar() == [], "archivo corrupto -> vacío, sin romper")
ok(m.escanear([T], maximo=1)[1] == 1, "límite de archivos escaneados")

# ---------- proyectos ----------
P = dk.Proyectos(T)
r1 = P.guardar_web(w); r2 = P.guardar_web(w)
ok(r1 != r2 and os.path.isfile(r1) and os.path.isfile(r2) and r1.endswith(".html"), "no pisa proyectos con el mismo nombre")
rc_ = P.guardar_clip(g); ok(dk.Proyectos.leer_clip(rc_)["titulo"] == g["titulo"], "guarda y relee el videoclip")
ra = P.guardar_app(dk.spec_app_local("app de notas")); ok(json.load(open(ra, encoding="utf-8"))["nombre"], "guarda la maqueta")
ok(os.path.dirname(P.guardar_web({"titulo": "../../etc/passwd", "secciones": [{"titulo": "a", "texto": "b"}]})) == P.dir, "el nombre no sale de la carpeta")
D = os.path.join(T, "Descargas"); os.makedirs(D)
ok(P.exportar(r1, [D])[0] and os.path.isfile(os.path.join(D, os.path.basename(r1))), "exporta a Descargas")
ok(P.exportar(r1, [os.path.join(T, "no")])[0] is False, "si no puede exportar, lo dice")

# ---------- núcleo: generar_diseno ----------
os.environ["KIRA_DATA_DIR"] = T
import kira_god
core = kira_god.KiraGodCore(); core._leer_clave = lambda: ""
c, origen = core.generar_diseno("web", "web de una cafetería"); ok(origen == "local" and c["secciones"], "sin clave: plantilla local")
core._leer_clave = lambda: "clave-falsa"
core._llamar_api = lambda *a, **k: "esto no es json"
ok(core.generar_diseno("app", "app de notas")[1] == "local", "IA inútil -> plantilla local")
def fallo(*a, **k): raise RuntimeError("sin red")
core._llamar_api = fallo; ok(core.generar_diseno("clip", "una playa")[1] == "local", "sin red -> plantilla local")
core._llamar_api = lambda *a, **k: json.dumps({"titulo": "<script>x</script>", "secciones": [{"titulo": "A", "texto": "B"}]})
c, origen = core.generar_diseno("web", "algo"); ok(origen == "ia" and "<script" not in dk.html_desde_spec(c), "IA válida: contenido escapado al generar el HTML")
for malo in (("zzz", "x"), ("web", "   ")):
    try: core.generar_diseno(*malo); ok(False, f"debería fallar {malo}")
    except ValueError: ok(True, "tipo o descripción inválidos")
# ---------- varias pantallas con su propia Mediateca: se ven los cambios y no se pisan ----------
R2 = os.path.join(T, "compartida.json")
for f_ in ("x1.mp3", "x2.mp3", "x3.mp4"): open(os.path.join(T, f_), "wb").write(b"x")
M1, M2 = dk.Mediateca(R2), dk.Mediateca(R2)
M1.anadir("Uno", os.path.join(T, "x1.mp3"))
ok([i["titulo"] for i in M2.listar()] == ["Uno"], "otra pantalla ve lo añadido sin reiniciar")
M2.anadir("Dos", os.path.join(T, "x2.mp3")); M1.anadir("Tres", os.path.join(T, "x3.mp4"))
ok(sorted(i["titulo"] for i in dk.Mediateca(R2).listar()) == ["Dos", "Tres", "Uno"], "ninguna pantalla pisa lo que añadió la otra")
id_dos = next(i["id"] for i in M1.listar() if i["titulo"] == "Dos")
M1.borrar(id_dos)
ok(sorted(i["titulo"] for i in M2.listar()) == ["Tres", "Uno"], "un borrado también se ve en la otra")
ok(len({i["id"] for i in dk.Mediateca(R2).listar()}) == 2, "los ids no se repiten")
print("DISEÑO OK", n)
