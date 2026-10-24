import sys, json, random, time
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
import diseno as D
from router import rutear, drc, W_PISTA

pads = D.pads()
nets = sorted({p.net for p in pads if not p.net.startswith('NC_')})
cuenta = {n: sum(1 for p in pads if p.net == n) for n in nets}
anchos = {'GND': 1.0, 'GX': 1.0, 'V24': 1.0, 'P5X': 1.0, 'P12X': 1.0, 'V5E': 1.0}
keep = [D.TEXTO_COBRE]
cuerpos = [(*c.cuerpo, c.tipo in ('axial', 'cap')) for c in D.comps]
limite = 2.5
rangos = {n: ((0, D.BARRERA_X - limite) if n in D.DOMINIO_ESP else (D.BARRERA_X + limite, 1e3)) for n in nets}

def ordenar(sem):
    r = random.Random(sem)
    base = sorted([n for n in nets if cuenta[n] >= 2], key=lambda n: (cuenta[n] > 3, cuenta[n]))
    if sem == 0: return base
    # perturbación: intercambios aleatorios
    o = base[:]
    for _ in range(r.randint(2, 8)):
        a, b = r.randrange(len(o)), r.randrange(len(o)); o[a], o[b] = o[b], o[a]
    return o

def dibujar(pistas, puentes, archivo, titulo=''):
    fig, ax = plt.subplots(figsize=(D.ANCHO / 9, D.ALTO / 9), dpi=110)
    ax.add_patch(Rectangle((0, 0), D.ANCHO, D.ALTO, fc='#0b5d2a', ec='k'))
    for (n, x1, y1, x2, y2, w) in pistas:
        ax.plot([x1, x2], [y1, y2], color='#e8b04a', lw=w * 72 / 9 * 110/72 * 0.62, solid_capstyle='round', zorder=2)
    for p in pads:
        ax.add_patch(Circle((p.x, p.y), p.r, fc='#e8b04a', ec='none', zorder=3))
        ax.add_patch(Circle((p.x, p.y), p.drill / 2, fc='k', zorder=4))
    for (n, x1, y1, x2, y2) in puentes:
        ax.plot([x1, x2], [y1, y2], color='#ff3030', lw=2, zorder=6)
        for x, y in ((x1, y1), (x2, y2)): ax.add_patch(Circle((x, y), 1.0, fc='#ff9090', zorder=5))
    for c in D.comps:
        x0, y0, x1, y1 = c.cuerpo
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='none', ec='w', lw=0.6, zorder=7))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, c.ref, color='w', fontsize=5, ha='center', va='center', zorder=8)
    x0, y0, x1, y1 = D.ESP_CUERPO
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc='none', ec='#9cf', lw=0.8, ls='--', zorder=7))
    ax.axvline(D.BARRERA_X, color='#ccc', ls=':', lw=0.6)
    ax.set_xlim(-1, D.ANCHO + 1); ax.set_ylim(D.ALTO + 1, -1); ax.set_aspect('equal'); ax.set_title(titulo, fontsize=8)
    fig.savefig(archivo, bbox_inches='tight'); plt.close(fig)

if __name__ == '__main__':
    intentos = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    mejor = None
    for sem in range(intentos):
        t = time.time()
        pistas, puentes, fallas = rutear(pads, D.ANCHO, D.ALTO, ordenar(sem), keep, anchos, rangos=rangos, previas=D.PREVIAS, cuerpos=cuerpos)
        nota = len(fallas) * 1000 + len(puentes) * 25 + sum(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 for (_, x1, y1, x2, y2, _) in pistas) / 100
        print(f'semilla {sem}: fallas {len(fallas)} puentes {len(puentes)} nota {nota:.1f} ({time.time()-t:.0f}s)', fallas[:5], flush=True)
        if mejor is None or nota < mejor[0]: mejor = (nota, sem, pistas, puentes, fallas)
    nota, sem, pistas, puentes, fallas = mejor
    dibujar(pistas, puentes, 'vista_ruteo.png', f'semilla {sem} · fallas {len(fallas)} · puentes {len(puentes)}')
    json.dump({'pistas': pistas, 'puentes': puentes, 'fallas': fallas, 'semilla': sem}, open('ruteo.json', 'w'))
    err, sin, minimo = drc(pads, pistas, puentes, D.ANCHO, D.ALTO)
    print('DRC errores:', len(err), err[:10]); print('nets sin conectar:', sin); print(f'holgura mínima {minimo:.3f} mm')
