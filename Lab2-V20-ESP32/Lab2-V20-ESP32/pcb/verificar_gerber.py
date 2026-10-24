"""Verificación independiente: rasteriza el Gerber de cobre (0,025 mm/px), etiqueta islas de cobre y compara
con el netlist del diseño. Detecta cortos, aberturas y holguras menores a 0,4 mm medidas en la imagen."""
import json, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import diseno as D
from lector_gerber import leer_gerber, leer_excellon

RES = 0.025
W, H = int(D.ANCHO / RES) + 1, int(D.ALTO / RES) + 1

def raster(prims, extra=0.0):
    im = Image.new('1', (W, H), 0); dr = ImageDraw.Draw(im)
    px = lambda x, y: (x / RES, (D.ALTO - y) / RES)
    for tipo, g, pol in prims:
        col = 1 if pol == 'D' else 0
        if tipo == 'circ':
            x, y, r = g; cx, cy = px(x, y); rr = (r + extra) / RES
            dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)
        elif tipo == 'rect':
            x, y, a, b = g; cx, cy = px(x, y)
            dr.rectangle([cx - (a / 2 + extra) / RES, cy - (b / 2 + extra) / RES, cx + (a / 2 + extra) / RES, cy + (b / 2 + extra) / RES], fill=col)
        elif tipo == 'linea':
            x1, y1, x2, y2, w = g; a, b = px(x1, y1), px(x2, y2); ww = (w + 2 * extra) / RES
            dr.line([a, b], fill=col, width=int(round(ww)))
            for c in (a, b): dr.ellipse([c[0] - ww / 2, c[1] - ww / 2, c[0] + ww / 2, c[1] + ww / 2], fill=col)
        elif tipo == 'poly':
            dr.polygon([px(*p) for p in g], fill=col)
    return np.array(im, dtype=bool)

if __name__ == '__main__':
    base = 'salida/gerber/V20IoT'
    cu = leer_gerber(base + '-B_Cu.gbl')
    puentes = json.load(open('ruteo.json'))['puentes']
    img = raster(cu)
    lab, n = ndimage.label(img)
    print(f'islas de cobre: {n}')
    # etiqueta de cada pad
    def etiqueta(x, y):
        i, j = int(round(x / RES)), int(round(y / RES))
        return lab[j, i]
    grupos = {}
    for p in D.pads():
        if p.ref.startswith('H'): continue
        grupos.setdefault(p.net, set()).add(etiqueta(p.x, p.y))
    # unir islas por los puentes de alambre
    padre = {}
    def raiz(a):
        padre.setdefault(a, a)
        while padre[a] != a: a = padre[a]
        return a
    for (net, x1, y1, x2, y2) in puentes:
        a, b = raiz(etiqueta(x1, y1)), raiz(etiqueta(x2, y2)); padre[a] = b
    errores = 0
    isla_net = {}
    for net, gs in grupos.items():
        rs = {raiz(g) for g in gs}
        if 0 in gs: print('pad sin cobre en', net); errores += 1
        if not net.startswith('NC_') and len(rs) > 1:
            print(f'ABIERTO: {net} en {len(rs)} islas'); errores += 1
        for r_ in rs:
            if r_ in isla_net and isla_net[r_] != net and not (net.startswith('NC_') and isla_net[r_].startswith('NC_')):
                print(f'CORTO: {net} con {isla_net[r_]}'); errores += 1
            isla_net[r_] = net
    # holgura: dilatar cada isla 0,2 mm (=0,4 mm entre dos) y buscar contactos entre islas distintas
    rad = int(round(0.2 / RES))
    estructura = np.hypot(*np.mgrid[-rad:rad + 1, -rad:rad + 1]) <= rad
    mx = ndimage.grey_dilation(lab, footprint=estructura)
    mn = -ndimage.grey_dilation(-np.where(lab == 0, n + 1, lab), footprint=estructura)
    contacto = (mx != mn) & (mn <= n) & (mx > 0)
    pares = set()
    for a, b in zip(mn[contacto][:20000], mx[contacto][:20000]):
        ra, rb = raiz(a), raiz(b)
        if ra != rb and isla_net.get(ra, '?') != isla_net.get(rb, '?'):
            pares.add((isla_net.get(ra, '?'), isla_net.get(rb, '?')))
    for pr in sorted(pares): print('holgura < 0,4 mm entre', pr); errores += 1
    # taladros sobre pads
    agujeros = leer_excellon(base + '-PTH.drl')
    for (x, y, d) in agujeros:
        if not img[int(round((D.ALTO - y) / RES)), int(round(x / RES))]: print('agujero sin cobre', x, y); errores += 1
    print(f'agujeros PTH: {len(agujeros)} · nets verificadas: {sum(1 for k in grupos if not k.startswith("NC_"))}')
    print('RESULTADO:', 'SIN ERRORES' if errores == 0 else f'{errores} ERRORES')
    sys.exit(1 if errores else 0)
