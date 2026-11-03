# -*- coding: utf-8 -*-
"""v2.65: la curiosidad de Kira (pensador_kira). Lógica pura (generar preguntas, clasificar, cuaderno, elegir
semilla) + un pensamiento entero con cerebro/estudio/experimento DE MENTIRA (sin red). Lo que piensa son notas;
nada se aplica solo."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
os.environ["HOME"] = tempfile.mkdtemp()

import pensador_kira as pk

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


# --- preguntas: 5 tipos, con la semilla metida ---
qs = pk.generar_preguntas("un bucle")
ok(len(qs) == 7 and all("un bucle" in q for q in qs), "genera 7 preguntas con la semilla")
ok(any(q.startswith("¿por qué") for q in qs) and any("¿cómo" in q for q in qs), "incluye por qué y cómo")

# --- clasificar la respuesta ---
ok(pk.clasificar_respuesta("No lo sé, ni idea")[1] is True, "detecta la duda (no lo sé)")
ok(pk.clasificar_respuesta("x")[0] == "baja", "respuesta vacía/corta = baja")
ok(pk.clasificar_respuesta("Creo que podría ser por el orden")[0] == "media", "titubeo = media")
ok(pk.clasificar_respuesta("Funciona porque la CPU repite las instrucciones del cuerpo hasta "
                           "que la condición es falsa.")[0] == "alta", "respuesta firme = alta")

# --- es_programable ---
ok(pk.es_programable("una pila") and pk.es_programable("la búsqueda binaria"), "temas de código = programables")
ok(not pk.es_programable("la ética"), "un tema no-código no es programable")

# --- cuaderno: anota, no repite, respeta el tope ---
est = pk._vacio()
ok(pk.anotar(est, {"pregunta": "¿por qué X?", "respuesta": "porque sí"}), "anota una nota nueva")
ok(not pk.anotar(est, {"pregunta": "¿por qué X?", "respuesta": "otra"}), "no repite la misma pregunta")
ok(pk.ya_pensada(est, "¿por qué X?"), "sabe que ya la pensó")

# --- pensar_una con cerebro/estudio/experimento de mentira ---
llamadas = {"preguntar": 0, "estudiar": 0, "experimentar": 0}


def preguntar_falso(prompt):
    llamaladas = llamadas["preguntar"]
    llamadas["preguntar"] += 1
    # la 1.ª vez duda (para forzar el estudio); luego responde firme
    if "Me he informado" in prompt:
        return "Ahora lo entiendo: una pila es LIFO, el último en entrar es el primero en salir."
    if llamadas["preguntar"] == 1:
        return "No lo sé."
    return "Una pila guarda cosas y saca la última; sirve para deshacer, por ejemplo."


def estudiar_falso(pregunta):
    llamadas["estudiar"] += 1
    return "Una pila (stack) es una estructura LIFO."


def experimentar_falso(pregunta, semilla):
    llamadas["experimentar"] += 1
    return {"ok": True, "resultado": "salida: 3 2 1", "codigo": "p=[];p.append(1)"}


est2 = pk._vacio()
nota = pk.pensar_una(est2, preguntar_falso, estudiar=estudiar_falso, experimentar=experimentar_falso,
                     semillas=["una pila"])
ok(nota is not None, "produjo una nota")
ok(llamadas["estudiar"] >= 1 and nota["fuente"] == "estudiado", "al dudar, estudió y lo marca")
ok(nota["tipo"] == "experimento" and nota["experimento"]["ok"], "al ser de código, experimentó (aislado)")
ok(est2["notas"] and est2["vistas"], "la nota quedó en el cuaderno")

# otra pasada: pregunta distinta (no repite)
nota2 = pk.pensar_una(est2, preguntar_falso, estudiar=estudiar_falso, experimentar=experimentar_falso,
                      semillas=["una pila"])
ok(nota2 is None or nota2["pregunta"] != nota["pregunta"], "la 2.ª pasada no repite pregunta")

# --- textos para leer ---
ok("Cuaderno de Kira" in pk.texto_cuaderno(est2), "texto del cuaderno")
ok("pensamiento" in pk.resumen(est2).lower(), "resumen legible")

# --- un tema NO programable no dispara experimento ---
est3 = pk._vacio()
n3 = pk.pensar_una(est3, lambda p: "La ética estudia el bien y el mal.", estudiar=None,
                   experimentar=experimentar_falso, semillas=["la ética"])
ok(n3["tipo"] == "idea" and "experimento" not in n3, "tema no-código: piensa, no experimenta")

# --- v2.75: consolidar (borra lo resuelto, se queda con la solución, para mejorar más adelante) ---
ok(pk.es_resuelta({"seguridad": "alta", "duda": False}), "alta + sin duda -> resuelta")
ok(not pk.es_resuelta({"seguridad": "alta", "duda": True}), "con duda -> NO resuelta")
ok(not pk.es_resuelta({"seguridad": "media", "duda": False}), "media -> NO resuelta")
ok(not pk.es_resuelta({"seguridad": "alta", "duda": False, "experimento": {"ok": False}}), "experimento fallido -> NO resuelta")

estc = pk._vacio()
# una nota floja (duda) y una buena del MISMO tema
pk.anotar(estc, {"semilla": "una pila", "pregunta": "¿y si falla una pila?", "respuesta": "no lo sé", "duda": True, "seguridad": "baja", "fuente": "sin cerebro"})
buena = {"semilla": "una pila", "pregunta": "¿cómo funciona una pila?", "respuesta": "LIFO: el último en entrar sale primero, clarísimo y seguro.", "duda": False, "seguridad": "alta", "cuando": 100, "experimento": {"ok": True, "codigo": "p=[]"}}
pk.anotar(estc, buena)
ok(pk.consolidar(estc, buena), "consolida una nota resuelta")
ok("una pila" in pk.texto_soluciones(estc), "la solución queda guardada")
ok(estc["soluciones"], "hay soluciones en el estado")
ok(all(not (nt.get("duda") and pk._norm(nt.get("semilla","")) == pk._norm("una pila")) for nt in estc["notas"]), "borró la nota floja del tema resuelto")
ok(any(nt is buena for nt in estc["notas"]), "la nota buena se queda")

# mejorar: una segunda solución del mismo tema cuenta veces y se queda con la mejor
buena2 = {"semilla": "una pila", "pregunta": "¿cómo mejorar una pila?", "respuesta": "igual pero con tope de tamaño y mejor explicado para que no reviente nunca.", "duda": False, "seguridad": "alta", "cuando": 200, "experimento": {"ok": True, "codigo": "p=[]; MAX=100"}}
pk.anotar(estc, buena2)
pk.consolidar(estc, buena2)
ok(estc["soluciones"][pk._norm("una pila")]["veces"] == 2, "cuenta las mejoras (2 veces)")

# proxima_semilla: con soluciones, de vez en cuando vuelve a MEJORAR una
estm = pk._vacio()
estm["soluciones"] = {"x": {"semilla": "una pila", "cuando": 1}}
estm["i"] = 4
sm = pk.proxima_semilla(estm)
ok("mejorar" in sm, "revisita una solución para mejorarla")

# --- la experiencia NO se queda en la RAM: se guarda en DISCO y sobrevive (pedido del dueño) ---
import tempfile
ruta_tmp = os.path.join(tempfile.mkdtemp(), "pensamientos.json")
pk.guardar(estc, ruta_tmp)                  # estc trae notas + soluciones
ok(os.path.exists(ruta_tmp), "el cuaderno se escribe en disco")
recargado = pk.cargar(ruta_tmp)             # simula cerrar y volver a abrir la app
ok(recargado.get("soluciones"), "al recargar de disco siguen las soluciones")
ok(pk._norm("una pila") in recargado["soluciones"], "la solución guardada sobrevive al reinicio")
ok(recargado.get("notas") == estc.get("notas"), "las notas sobreviven al reinicio tal cual")

print(f"\nTODO BIEN {n}")
