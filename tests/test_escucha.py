# -*- coding: utf-8 -*-
"""Escucha permanente con «Kira», borrador de 15 s, luz de neón y conversaciones nuevas en el baúl."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import escucha_kira as ek
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- el nombre ----------
ok(ek.contiene_nombre("Kira, ¿qué hora es?") == (True, "qué hora es?"), "nombre al principio")
ok(ek.contiene_nombre("oye kira pon música")[1] == "pon música", "nombre en medio")
ok(ek.contiene_nombre("KÍRA")[0] and ek.contiene_nombre("kyra")[0], "mayúsculas, tildes y variantes")
ok(not ek.contiene_nombre("puede que no quiera venir mañana")[0], "«quiera» en medio de la frase no la despierta")
ok(ek.contiene_nombre("quiera venir mañana")[0], "al principio sí (así escribe «Kira» el reconocedor sin conexión)")
ok(not ek.contiene_nombre("kirguistán")[0] and not ek.contiene_nombre("")[0], "palabras parecidas no")

# ---------- borrador de 15 segundos ----------
reloj = [100.0]
e = ek.Escucha(reloj=lambda: reloj[0])
ok(e.oir("hablando de otra cosa") == ("nada", None) and len(e.borrador) == 1, "sin nombre: no contesta, va al borrador")
reloj[0] += 5; e.oir("y más cosas")
ok(len(e.borrador) == 2, "dos frases en el borrador")
reloj[0] += 6
ok(e.purgar() == 0 and len(e.borrador) == 2, "a los 11 s todavía no se borra (dura 15 s)")
reloj[0] += 5
ok(e.purgar() == 1 and len(e.borrador) == 1, "lo de hace más de 15 s se borra")
reloj[0] += 16; e.purgar()
ok(e.borrador == [], "todo se borra al pasar 15 s")

# ---------- activación ----------
e.oir("cosas sueltas")
ok(e.oir("Kira, ¿qué tiempo hace?") == ("orden", "qué tiempo hace?") and e.borrador == [], "con el nombre para el borrador y da la orden")
ok(e.oir("Kira") == ("atenta", None) and e.atenta, "solo el nombre: se queda atenta")
reloj[0] += 3
ok(e.oir("pon una canción") == ("orden", "pon una canción") and not e.atenta, "la siguiente frase es la orden")
e.oir("Kira"); reloj[0] += 9
ok(not e.atenta and e.oir("esto ya no es para ella") == ("nada", None), "la atención caduca a los 8 s")
ok(e.oir("   ") == ("nada", None), "frase vacía")
e.oir("Kira"); e.olvidar(); ok(not e.atenta and e.borrador == [], "olvidar lo borra todo")

# ---------- neón ----------
m = ek.NeonModelo()
for _ in range(60): m.paso(0.05)
reposo = m.intensidad
m.poner_estado("atenta")
for _ in range(40): m.paso(0.05)
ok(m.intensidad > reposo + 0.3, f"brilla más al escuchar de verdad ({reposo:.2f} -> {m.intensidad:.2f})")
m.poner_estado("hablando"); vals = []
for _ in range(80): m.paso(0.05); vals.append(m.intensidad)
ok(min(vals[20:]) > reposo + 0.2 and max(vals) - min(vals[20:]) > 0.05, "al hablar brilla y late")
m.poner_estado("inventado"); ok(m.estado == "hablando", "estado desconocido: se ignora")
ok(ek.dentro_del_boton(50, 50, 50, 50, 10) and not ek.dentro_del_boton(80, 50, 50, 50, 10), "toque dentro del botón redondo")
pos = ek.rejilla_letras(400, 800, 80, 40)
ok(len(pos) > 60 and any(x < 0 for x, _ in pos) and max(y for _, y in pos) >= 800 - 40, "«Kira» cubre todo el fondo")
ok(ek.rejilla_letras(0, 100, 10, 10) == [], "sin tamaño, sin letras")

# ---------- conversaciones nuevas en el baúl ----------
import recuerdos_kira as rk
B = rk.Recuerdos(os.path.join(tempfile.mkdtemp(), "b"))
k1 = B.guardar_charla("qué película vimos el sábado", "Vimos una de ciencia ficción con naves espaciales.")
ok(k1 is not None, "guarda una conversación nueva")
ok(B.guardar_charla("qué película vimos el sábado", "Vimos una de ciencia ficción con naves espaciales.") is None, "la ya reconocida no se repite")
ok(B.respuesta_directa("qué película vimos el sábado")["n"] == k1, "la recuerda si preguntas lo mismo")
ok(B.respuesta_directa("película favorita de mi madre") is None, "no la usa para otra pregunta")
ok(B.guardar_charla("hola", "¡Hola! ¿Qué tal estás hoy?") is None, "un saludo no se guarda")
ok(B.guardar_charla("cuéntame algo largo", "[x] No pude responder") is None, "los errores no se guardan")
B.guardar("Mi gato se llama Miko.", fuente="usuario")
ok(B.guardar_charla("cómo se llama mi gato", "Tu gato se llama Miko, me lo dijiste.") is None, "lo que ya sabía no se guarda otra vez")
ok("lo hablamos" in rk.texto_lista(B.buscar("película sábado")), "en la lista sale como conversación")

# ---------- pedir mejoras con la voz ----------
import inicio_kira as ik
ok(ik.pedido_mejora("mejora la mesa de mezcla para que tenga eco") == "la mesa de mezcla para que tenga eco", "mejora …")
ok(ik.pedido_mejora("Aprende a convertir euros a dólares") == "convertir euros a dólares", "aprende a …")
ok(ik.pedido_mejora("añade un temporizador de cocina.") == "un temporizador de cocina", "añade …")
ok(ik.pedido_mejora("Mejórate: que me digas el tiempo") == "que me digas el tiempo", "mejórate …")
ok(ik.pedido_mejora("quiero que sepas leer códigos QR") == "leer códigos QR", "quiero que sepas …")
ok(ik.pedido_mejora("aprende que mi perro se llama Toby") is None, "«aprende que» es recordar, no programar")
ok(ik.pedido_mejora("aprende sola") is None and ik.pedido_mejora("aprende sobre volcanes") is None, "estudiar no es programar")
ok(ik.pedido_mejora("qué tal estás") is None and ik.pedido_mejora("mejora") is None, "charla normal o pedido vacío")
print("ESCUCHA OK", n)
