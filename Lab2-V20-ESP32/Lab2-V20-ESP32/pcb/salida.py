"""Genera Gerber RS-274X, Excellon, PDF 1:1 para planchado, mapa de montaje, vistas PNG y netlist."""
import json, math, csv, zipfile
from pathlib import Path
import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MPath
import diseno as D

OUT = Path('salida'); OUT.mkdir(exist_ok=True)
R = json.load(open('ruteo.json'))
PISTAS = [tuple(p) for p in R['pistas']]
PUENTES = [tuple(p) for p in R['puentes']]
PADS = D.pads()
NOMBRE = 'V20IoT'
FUENTE = FontProperties(family='DejaVu Sans', weight='bold')
D_PUENTE, DRILL_PUENTE = 2.0, 0.8

# ------------------------------------------------------------------ texto como polígonos
def texto_poligonos(t, x, y, alto, ancla='c', espejo=False):
    tp = TextPath((0, 0), t, size=alto * 1.36, prop=FUENTE)
    polys = [np.array(p) for p in tp.to_polygons() if len(p) > 2]
    if not polys: return []
    allp = np.vstack(polys)
    x0, x1 = allp[:, 0].min(), allp[:, 0].max()
    y0, y1 = allp[:, 1].min(), allp[:, 1].max()
    dx = {'c': -(x0 + x1) / 2, 'l': -x0, 'r': -x1}[ancla]
    out = []
    for i, p in enumerate(polys):
        q = p.copy()
        q[:, 0] += dx; q[:, 1] -= (y0 + y1) / 2
        if espejo: q[:, 0] = -q[:, 0]
        q[:, 0] += x; q[:, 1] = y - q[:, 1]          # a coordenadas de tarjeta (y hacia abajo)
        hueco = any(j != i and MPath(polys[j]).contains_point(p[0]) for j in range(len(polys)))
        out.append((q, hueco))
    out.sort(key=lambda a: a[1])                     # primero contornos, luego huecos
    return out

# ------------------------------------------------------------------ escritor Gerber
class Gerber:
    def __init__(s, funcion):
        s.ap = {}; s.cuerpo = []; s.funcion = funcion
    def apertura(s, forma, *dim):
        k = (forma, dim)
        if k not in s.ap: s.ap[k] = 10 + len(s.ap)
        return s.ap[k]
    def c(s, v): return int(round(v * 1e6))
    def pt(s, x, y): return f'X{s.c(x)}Y{s.c(D.ALTO - y)}'
    def flash(s, forma, dim, x, y):
        s.cuerpo.append(f'D{s.apertura(forma, *dim)}*'); s.cuerpo.append(f'{s.pt(x, y)}D03*')
    def linea(s, x1, y1, x2, y2, w):
        s.cuerpo.append(f'D{s.apertura("C", w)}*'); s.cuerpo.append(f'{s.pt(x1, y1)}D02*'); s.cuerpo.append(f'{s.pt(x2, y2)}D01*')
    def region(s, pts, claro=False):
        if claro: s.cuerpo.append('%LPC*%')
        s.cuerpo.append('G36*'); s.cuerpo.append(f'{s.pt(*pts[0])}D02*')
        for p in pts[1:]: s.cuerpo.append(f'{s.pt(*p)}D01*')
        s.cuerpo.append(f'{s.pt(*pts[0])}D01*'); s.cuerpo.append('G37*')
        if claro: s.cuerpo.append('%LPD*%')
    def texto(s, t, x, y, alto, ancla='c', espejo=False):
        for poly, hueco in texto_poligonos(t, x, y, alto, ancla, espejo): s.region(poly.tolist(), hueco)
    def guardar(s, ruta):
        h = ['G04 Tarjeta de interfaz ESP32-V20 (Lab 2 Electronica de Potencia)*', f'%TF.FileFunction,{s.funcion}*%',
             '%FSLAX46Y46*%', '%MOMM*%', '%LPD*%']
        for (forma, dim), n in s.ap.items():
            h.append(f'%ADD{n}{forma},{"X".join(f"{d:.4f}" for d in dim)}*%')
        Path(ruta).write_text('\n'.join(h + ['G01*'] + s.cuerpo + ['M02*']) + '\n')

def pad_flash(g, p, extra=0.0):
    if p.cuadrado: g.flash('R', (p.d + extra, p.d + extra), p.x, p.y)
    else: g.flash('C', (p.d + extra,), p.x, p.y)

def capa_cobre():
    g = Gerber('Copper,L1,Bot')
    for (n, x1, y1, x2, y2, w) in PISTAS: g.linea(x1, y1, x2, y2, w)
    for p in PADS:
        if p.ref.startswith('H'): continue
        pad_flash(g, p)
    for (n, x1, y1, x2, y2) in PUENTES:
        g.flash('C', (D_PUENTE,), x1, y1); g.flash('C', (D_PUENTE,), x2, y2)
    tx = D.TEXTO_COBRE
    g.texto('LAB2 V20 IoT', (tx[0] + tx[2]) / 2, tx[1] + 3.5, 3.0, espejo=True)
    g.texto('UNIMAGDALENA', (tx[0] + tx[2]) / 2, tx[1] + 8.5, 2.4, espejo=True)
    return g

def capa_mascara():
    g = Gerber('Soldermask,Bot')
    for p in PADS:
        if p.ref.startswith('H'): g.flash('C', (p.d + 0.2,), p.x, p.y)
        else: pad_flash(g, p, 0.2)
    for (n, x1, y1, x2, y2) in PUENTES:
        g.flash('C', (D_PUENTE + 0.2,), x1, y1); g.flash('C', (D_PUENTE + 0.2,), x2, y2)
    return g

ETIQ_REF = {}
def capa_serigrafia():
    g = Gerber('Legend,Top')
    W = 0.15
    for c in D.comps:
        if c.tipo == 'agujero': continue
        x0, y0, x1, y1 = c.cuerpo
        for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            g.linea(*a, *b, W)
        if c.tipo == 'dip':
            p1 = c.pads[0]
            mx_, my_ = {0: (p1.x - 1.9, p1.y), 180: (p1.x + 1.9, p1.y), 90: (p1.x, p1.y + 1.9)}[c.rot]
            g.flash('C', (0.7,), mx_, my_)
        if c.ref == 'D1':   # banda del cátodo junto al pad 1
            p1 = c.pads[0]; g.linea(x0, p1.y + 2.6, x1, p1.y + 2.6, 0.5); g.texto('K', x0 - 0.8, p1.y + 1.5, 1.1, 'r')
        # referencia
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        alto = 1.3
        if c.ref == 'D1':
            g.texto(c.ref, x0 - 0.6, cy + 1.5, alto, 'r')
        elif c.tipo in ('axial', 'cap') and (x1 - x0) < (y1 - y0):
            g.texto(c.ref, x1 + 0.6, cy, alto, 'l')
        elif c.tipo == 'bornera':
            if c.vertical: g.texto(c.ref, cx, y0 - 1.4, alto)
            else: g.texto(c.ref, x0 - 0.8, cy, alto, 'r')
        elif c.ref == 'J5':
            g.texto('J5 ACS712', cx, y0 - 1.4, alto)
        elif c.tipo == 'tira' and c.ref in ('J1', 'J2', 'J3'):
            g.texto(c.ref, cx, y0 - 1.5, alto)
        else:
            g.texto(c.ref, cx, cy, alto)
        if c.tipo == 'bornera':
            for p, et in zip(c.pads, c.etiqueta):
                if c.vertical: g.texto(et, p.x - 4.4, p.y, 1.4, 'r')
                else: g.texto(et, p.x, p.y + 4.6 if p.y < D.ALTO / 2 else p.y - 4.6, 1.4)
    # marcas ESP32
    x0, y0, x1, y1 = D.ESP_CUERPO
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        g.linea(*a, *b, W)
    g.texto('ESP32 DevKit V1 (30 pines) - USB ARRIBA', (x0 + x1) / 2, y0 + 1.6, 1.1)
    g.texto('ANTENA', (x0 + x1) / 2, y1 - 2.5, 1.3)
    for k, n in enumerate(D.nombresL):
        if n in ('VIN', 'GND', 'D27', 'D26', 'D25', 'D33', 'D32', 'D35', 'D34'):
            g.texto(n, 30.48 - 1.6, D.Y0 + k * D.P, 0.9, 'r')
    g.texto('3V3', 10.0, D.Y0, 0.9, 'l')
    # barrera
    y = 6.0
    while y < 60:
        g.linea(D.BARRERA_X, y, D.BARRERA_X, y + 1.2, W); y += 2.4
    g.texto('ESP32', D.BARRERA_X - 2.5, 61.5, 1.4, 'r'); g.texto('V20', D.BARRERA_X + 2.5, 61.5, 1.4, 'l')
    # puentes
    for k, (n, x1, y1, x2, y2) in enumerate(PUENTES):
        g.linea(x1, y1, x2, y2, 0.5)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if abs(x2 - x1) > abs(y2 - y1): g.texto(f'W{k+1}', mx, my - 1.6, 1.2)
        else: g.texto(f'W{k+1}', mx + 1.0, my, 1.2, 'l')
    g.texto('Interfaz ESP32 - SINAMICS V20  v3.2', 100.0, 70.5, 1.5)
    g.texto('Lab. 2 Electronica de Potencia', 100.0, 86.36 - 2.3, 1.2)
    return g

def capa_borde():
    g = Gerber('Profile,NP')
    pts = [(0, 0), (D.ANCHO, 0), (D.ANCHO, D.ALTO), (0, D.ALTO), (0, 0)]
    for a, b in zip(pts, pts[1:]): g.linea(*a, *b, 0.1)
    return g

def excellon(ruta, agujeros, plateado=True):
    tools = sorted({d for (_, _, d) in agujeros})
    L = ['M48', '; Tarjeta interfaz ESP32-V20', f'; {"PTH" if plateado else "NPTH"}', 'METRIC,TZ']
    L += [f'T{i+1}C{d:.3f}' for i, d in enumerate(tools)] + ['%', 'G90', 'G05']
    for i, d in enumerate(tools):
        L.append(f'T{i+1}')
        L += [f'X{x:.3f}Y{D.ALTO - y:.3f}' for (x, y, dd) in agujeros if dd == d]
    L.append('M30'); Path(ruta).write_text('\n'.join(L) + '\n')

if __name__ == '__main__':
    g_dir = OUT / 'gerber'; g_dir.mkdir(exist_ok=True)
    capa_cobre().guardar(g_dir / f'{NOMBRE}-B_Cu.gbl')
    capa_mascara().guardar(g_dir / f'{NOMBRE}-B_Mask.gbs')
    capa_serigrafia().guardar(g_dir / f'{NOMBRE}-F_SilkS.gto')
    capa_borde().guardar(g_dir / f'{NOMBRE}-Edge_Cuts.gm1')
    pth = [(p.x, p.y, p.drill) for p in PADS if not p.ref.startswith('H')]
    pth += [(x, y, DRILL_PUENTE) for (_, x1, y1, x2, y2) in PUENTES for (x, y) in ((x1, y1), (x2, y2))]
    excellon(g_dir / f'{NOMBRE}-PTH.drl', pth)
    excellon(g_dir / f'{NOMBRE}-NPTH.drl', [(p.x, p.y, p.drill) for p in PADS if p.ref.startswith('H')], False)
    with zipfile.ZipFile(OUT / f'{NOMBRE}_gerber.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(g_dir.iterdir()): z.write(f, f.name)
    # netlist
    with open(OUT / 'netlist_V20IoT.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['Referencia', 'Valor', 'Pin', 'Net'])
        for c in D.comps:
            if c.tipo == 'agujero': continue
            for p in c.pads:
                if not p.net.startswith('NC_'): w.writerow([c.ref, c.valor, p.num, p.net])
    print('gerber ok', len(pth), 'agujeros PTH')
