"""Lector independiente de Gerber/Excellon (sólo lo que usa este proyecto) para verificar los archivos
y dibujar el PDF 1:1 directamente desde ellos."""
import re

def leer_gerber(ruta):
    ap = {}; prims = []; cur = None; x = y = 0.0; pol = 'D'; region = None
    for raw in open(ruta).read().replace('\n', '').split('*'):
        t = raw.strip().lstrip('%')
        if not t: continue
        if t.startswith('ADD'):
            m = re.match(r'ADD(\d+)([CR]),([\d.X]+)', t)
            ap[int(m.group(1))] = (m.group(2), [float(v) for v in m.group(3).split('X')]); continue
        if t.startswith('LPC'): pol = 'C'; continue
        if t.startswith('LPD'): pol = 'D'; continue
        if t.startswith(('TF', 'FS', 'MO')) or t.startswith('G04') or t == 'G01' or t == 'M02': continue
        if t == 'G36': region = []; continue
        if t == 'G37': prims.append(('poly', region, pol)); region = None; continue
        m = re.fullmatch(r'D(\d+)', t)
        if m and int(m.group(1)) >= 10: cur = int(m.group(1)); continue
        m = re.fullmatch(r'X(-?\d+)Y(-?\d+)D0([123])', t)
        if not m: raise ValueError(f'comando desconocido: {t}')
        nx, ny, op = int(m.group(1)) / 1e6, int(m.group(2)) / 1e6, m.group(3)
        if region is not None:
            region.append((nx, ny))
        elif op == '3':
            forma, dim = ap[cur]
            prims.append(('circ', (nx, ny, dim[0] / 2), pol) if forma == 'C' else ('rect', (nx, ny, dim[0], dim[1]), pol))
        elif op == '1':
            prims.append(('linea', (x, y, nx, ny, ap[cur][1][0]), pol))
        x, y = nx, ny
    return prims

def leer_excellon(ruta):
    tools = {}; cur = None; out = []
    for l in open(ruta).read().splitlines():
        m = re.fullmatch(r'T(\d+)C([\d.]+)', l)
        if m: tools[m.group(1)] = float(m.group(2)); continue
        m = re.fullmatch(r'T(\d+)', l)
        if m: cur = tools[m.group(1)]; continue
        m = re.fullmatch(r'X([\d.]+)Y([\d.]+)', l)
        if m: out.append((float(m.group(1)), float(m.group(2)), cur))
    return out
