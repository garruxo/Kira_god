# -*- coding: utf-8 -*-
"""Iluminación de las salas 3D: luces automáticas, degradados, sombras de contacto, autoexposición y animación."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import habitacion_kira as hk, luz3d_kira as lz, salas_kira as sk
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

base = hk.construir_escena()
prep = lz.preparar(base)
ok(len(prep["caras"]) > len(base) and len(prep["luz"]) == len(prep["caras"]) == len(prep["anim"]), "subdivide y da luz a cada cara")
ok(4 <= len(prep["luces"]) <= lz.MAX_LUCES, f"encuentra las lámparas de la sala ({len(prep['luces'])})")
ok(all(len(l) == 6 for l in prep["luces"]), "cada luz: posición, color, intensidad, alcance, normal, área")
ok(all((f is None) == c[5] for f, c in zip(prep["luz"], prep["caras"])), "lo que brilla no se ilumina; lo demás sí")
ok(all(v <= lz.TOPE for f in prep["luz"] if f for v in f), "ninguna cara se quema")

def luz_suelo(x, z):
    for (pts, col, nor, capa, hot, emi), f in zip(prep["caras"], prep["luz"]):
        if f and capa == 0 and nor == (0, 1, 0):
            xs, zs = [p[0] for p in pts], [p[2] for p in pts]
            if min(xs) <= x <= max(xs) and min(zs) <= z <= max(zs):
                return sum(f) / 3
bajo, libre = luz_suelo(0.0, 7.0), luz_suelo(0.0, 2.5)
ok(bajo is not None and libre is not None and bajo < libre * 0.8, f"sombra bajo la mesa ({bajo:.2f} < {libre:.2f})")
pesos = [(lz.area(c[0]), f) for c, f in zip(prep["caras"], prep["luz"]) if f]
media = sum(a * (0.3 * f[0] + 0.55 * f[1] + 0.15 * f[2]) for a, f in pesos) / sum(a for a, _ in pesos)
ok(0.6 < media < 0.85, f"autoexposición: brillo medio razonable ({media:.2f})")
tipos = {a[0] for a in prep["anim"] if a}
ok(tipos == {"parpadeo", "brillo"}, "pilotos que parpadean y luces que respiran")
c0 = (1.0, 0.5, 0.2)
ok(lz.color_animado(c0, None, 3) == c0, "sin animación, igual")
parp = next(a for a in prep["anim"] if a and a[0] == "parpadeo")
ok(len({lz.color_animado(c0, parp, t / 10)[0] for t in range(60)}) == 2, "el piloto se enciende y se apaga")

# todas las salas se preparan, se pintan y tienen sus luces
for nombre, cons, cfg in (("hacker", hk.construir_escena, hk.CFG_HACKER), ("diseño", sk.construir_diseno, sk.CFG_DISENO),
                          ("cine", sk.construir_cine, sk.CFG_CINE), ("ciber", sk.construir_ciber, sk.CFG_CIBER)):
    r = hk.Recorrido(cons(), cfg)
    r.pose = cfg["mesa"]
    caras = r.render(400, 700)
    ok(len(caras) > 30 and r.luces and r.luz is not None, f"{nombre}: iluminada ({len(r.luces)} luces)")
    ok(all(0 <= v <= 1 for _, col, _ in caras for v in col), f"{nombre}: colores válidos")
    sin = hk.Recorrido(cons(), cfg, luces=False)
    ok(sin.luz is None and len(sin.escena) < len(r.escena), f"{nombre}: se puede apagar la iluminación")

# en reposo sigue animando (pero sin redibujar a lo loco)
r = hk.Recorrido()
r.estado, r.sucio = "libre", False
r.paso(0.05); ok(not r.sucio, "no redibuja en cada fotograma")
r.paso(0.1); ok(r.anim_sucio and not r.sucio, "cada ~0,12 s repinta SOLO el color de lo que brilla (no toda la sala)")
import luz3d_kira as _l3
_ix = [i for i, a in enumerate(r.anim) if a is not None]
ok(_ix and all(hk.color_cara(r.escena, i, 2.0, niebla=r.cfg["niebla"], luz=r.luz, anim=r.anim, t=r.reloj)
               == hk._sombrear(_l3.color_animado(r.escena[i][1], r.anim[i], r.reloj), r.escena[i][2], 2.0, r.escena[i][5],
                               r.cfg["niebla"], r.luz[i]) for i in _ix[:5]), "el color repintado es el mismo que el del dibujo")
_full = hk.render_caras(r.escena, r.pose, 400, 700, niebla=r.cfg["niebla"], luz=r.luz, anim=r.anim, t=r.reloj)
_idx = hk.render_caras_idx(r.escena, r.pose, 400, 700, niebla=r.cfg["niebla"], luz=r.luz, anim=r.anim, t=r.reloj)
ok([c[:3] for c in _idx] == _full and all(hk.color_cara(r.escena, c[3], c[4], niebla=r.cfg["niebla"], luz=r.luz,
                                                        anim=r.anim, t=r.reloj) == c[1] for c in _idx), "render con índice")
r.pose = hk.POSE_MESA
h = r.halos(400, 700)
ok(h and all(len(x) == 4 and x[2] > 0 for x in h), "resplandor de las lámparas pequeñas")
grandes = [l for l in r.luces if l[5] > lz.HALO_AREA]
ok(len(h) <= len(r.luces) - len(grandes), "las luces grandes no llevan halo")
# los objetos se siguen pudiendo tocar
mx, my = hk.proyectar(hk.a_camara((0, 1.28, 6.88), hk.POSE_MESA), 100, 100, 90)
ok(hk.hotspot_en(r.render(100, 100), mx, my) == "ordenador", "tocar el ordenador sigue funcionando")
print("LUZ 3D OK", n)
