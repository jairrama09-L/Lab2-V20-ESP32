"""Ruteador de laberinto (A*) a una cara con puentes de alambre, y DRC geométrico exacto."""
import heapq, math, random
import numpy as np
from diseno import G

W_PISTA = 0.8
CLR_RUTEO = 0.6     # holgura usada al rutear (la rejilla diagonal puede perder ~0,08)
CLR_DRC = 0.5       # holgura mínima exigida en el DRC
BORDE = 1.5         # cobre a borde de tarjeta
COSTO_PUENTE = 45.0

class Rejilla:
    def __init__(s, ancho, alto):
        s.nx, s.ny = int(round(ancho / G)) + 1, int(round(alto / G)) + 1
        s.dueno = np.full((s.ny, s.nx), -1, dtype=np.int32)     # para centro de pista
        s.duenoPad = np.full((s.ny, s.nx), -1, dtype=np.int32)  # para centro de pad de puente
        s.xs = np.arange(s.nx) * G
        s.ys = np.arange(s.ny) * G
        m = int(math.ceil((BORDE + W_PISTA / 2) / G))
        for arr in (s.dueno, s.duenoPad):
            arr[:m, :] = -2; arr[-m:, :] = -2; arr[:, :m] = -2; arr[:, -m:] = -2
        s.nojump = np.zeros((s.ny, s.nx), bool)   # no aterrizar un puente aquí
        s.nocross = np.zeros((s.ny, s.nx), bool)  # un puente no puede pasar por aquí

    def rect_mask(s, mask, x0, y0, x1, y1):
        i0, i1 = max(0, int(np.floor(x0 / G))), min(s.nx, int(np.ceil(x1 / G)) + 1)
        j0, j1 = max(0, int(np.floor(y0 / G))), min(s.ny, int(np.ceil(y1 / G)) + 1)
        mask[j0:j1, i0:i1] = True

    def circ_mask(s, mask, x, y, r):
        X, Y = np.meshgrid(s.xs, s.ys)
        mask |= np.hypot(X - x, Y - y) < r

    def _marcar(s, arr, net, dist_fn, x0, y0, x1, y1, lim, r=0.0):
        e = lim + r
        i0, i1 = max(0, int((x0 - e) / G) - 1), min(s.nx, int((x1 + e) / G) + 2)
        j0, j1 = max(0, int((y0 - e) / G) - 1), min(s.ny, int((y1 + e) / G) + 2)
        X, Y = np.meshgrid(s.xs[i0:i1], s.ys[j0:j1])
        d = dist_fn(X, Y)
        mask = d < lim - 1e-9
        sub = arr[j0:j1, i0:i1]
        libre = (sub == -1) & mask
        otro = (sub != -1) & (sub != net) & mask
        sub[libre] = net
        sub[otro] = -2

    def agregar_circulo(s, net, x, y, r):
        f = lambda X, Y: np.hypot(X - x, Y - y) - r
        s._marcar(s.dueno, net, f, x, y, x, y, CLR_RUTEO + W_PISTA / 2, r)
        s._marcar(s.duenoPad, net, f, x, y, x, y, CLR_RUTEO + 1.0, r)

    def agregar_segmento(s, net, x1, y1, x2, y2, r):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy or 1e-12
        def f(X, Y):
            t = np.clip(((X - x1) * dx + (Y - y1) * dy) / L2, 0, 1)
            return np.hypot(X - (x1 + t * dx), Y - (y1 + t * dy)) - r
        s._marcar(s.dueno, net, f, min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), CLR_RUTEO + W_PISTA / 2, r)
        s._marcar(s.duenoPad, net, f, min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), CLR_RUTEO + 1.0, r)

    def bloquear_rect(s, x0, y0, x1, y1):
        i0, i1 = int(x0 / G), int(x1 / G) + 1
        j0, j1 = int(y0 / G), int(y1 / G) + 1
        s.dueno[j0:j1, i0:i1] = -2; s.duenoPad[j0:j1, i0:i1] = -2

DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]

def a_estrella(rj, net, fuentes, destinos, permitir_puentes=True, max_puente=28, rango=(0, 10**6)):
    """fuentes/destinos: conjuntos de celdas (i,j). Devuelve lista de pasos [(i,j,'p'|'j')]."""
    D = rj.dueno; DP = rj.duenoPad
    lo, hi = rango
    ok = lambda i, j: lo <= i <= hi and 0 <= i < rj.nx and 0 <= j < rj.ny and (D[j, i] == -1 or D[j, i] == net)
    okp = lambda i, j: lo <= i <= hi and 0 <= i < rj.nx and 0 <= j < rj.ny and (DP[j, i] == -1 or DP[j, i] == net)
    dl = list(destinos)
    def h(i, j):
        return min(max(abs(i - a), abs(j - b)) + 0.414 * min(abs(i - a), abs(j - b)) for a, b in dl[:40])
    dest = set(destinos)
    g = {}; prev = {}; tipo = {}
    pq = []
    for c in fuentes:
        g[c] = 0; prev[c] = None; tipo[c] = 'p'
        heapq.heappush(pq, (h(*c), 0, c, (0, 0)))
    cerrado = set()
    while pq:
        f, gc, c, ultdir = heapq.heappop(pq)
        if c in cerrado: continue
        cerrado.add(c)
        if c in dest:
            camino = []
            while c is not None:
                camino.append((c[0], c[1], tipo[c])); c = prev[c]
            return camino[::-1]
        i, j = c
        for di, dj, w in DIRS:
            ni, nj = i + di, j + dj
            if not ok(ni, nj): continue
            if di and dj and not (ok(i + di, j) and ok(i, j + dj)): continue
            giro = 0.0 if (di, dj) == ultdir or ultdir == (0, 0) else 0.35
            ng = gc + w + giro
            n = (ni, nj)
            if ng < g.get(n, 1e18):
                g[n] = ng; prev[n] = c; tipo[n] = 'p'
                heapq.heappush(pq, (ng + h(ni, nj), ng, n, (di, dj)))
        if permitir_puentes and okp(i, j) and not rj.nojump[j, i]:
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for k in range(2, max_puente // 4 + 1):
                    ni, nj = i + di * 4 * k, j + dj * 4 * k
                    if not (0 <= ni < rj.nx and 0 <= nj < rj.ny): break
                    if any(rj.nocross[j + dj * q, i + di * q] for q in range(4 * k - 3, 4 * k + 1)):
                        break
                    if not okp(ni, nj) or rj.nojump[nj, ni]: continue
                    ng = gc + COSTO_PUENTE + 4 * k * 0.3
                    n = (ni, nj)
                    if ng < g.get(n, 1e18):
                        g[n] = ng; prev[n] = c; tipo[n] = 'j'
                        heapq.heappush(pq, (ng + h(ni, nj), ng, n, (0, 0)))
    return None

def celda(x, y): return (int(round(x / G)), int(round(y / G)))

def rutear(pads, ancho, alto, orden, keepouts=(), anchos=None, permitir_puentes=True, semilla=0, rangos=None, previas=(), cuerpos=None):
    rangos = rangos or {}
    anchos = anchos or {}
    rj = Rejilla(ancho, alto)
    for k in keepouts: rj.bloquear_rect(*k)
    nets = sorted({p.net for p in pads})
    nid = {n: i for i, n in enumerate(nets)}
    for p in pads:
        rj.agregar_circulo(nid[p.net], p.x, p.y, p.r)
        rj.circ_mask(rj.nojump, p.x, p.y, 2.2)
    for (x0, y0, x1, y1, cruza) in (cuerpos or []):
        rj.rect_mask(rj.nojump, x0 - 0.8, y0 - 0.8, x1 + 0.8, y1 + 0.8)
        if not cruza: rj.rect_mask(rj.nocross, x0, y0, x1, y1)
    pistas = []   # (net, x1,y1,x2,y2, ancho)
    puentes = []  # (net, x1,y1,x2,y2)
    fallas = []
    celdas_previas = {}
    for net, pts in previas:
        w = anchos.get(net, W_PISTA)
        for q in range(1, len(pts)):
            (x1, y1), (x2, y2) = pts[q - 1], pts[q]
            pistas.append((net, x1, y1, x2, y2, w))
            rj.agregar_segmento(nid[net], x1, y1, x2, y2, w / 2)
            L = max(abs(x2 - x1), abs(y2 - y1)); k = max(1, int(round(L / G)))
            for m in range(k + 1):
                celdas_previas.setdefault(net, set()).add(celda(x1 + (x2 - x1) * m / k, y1 + (y2 - y1) * m / k))
    for net in orden:
        pp = [p for p in pads if p.net == net]
        if len(pp) < 2: continue
        n = nid[net]
        arbol = {celda(pp[0].x, pp[0].y)} | celdas_previas.get(net, set())
        pend = [p for p in pp[1:] if celda(p.x, p.y) not in arbol]
        # conectar primero el pad más cercano al árbol
        while pend:
            pend.sort(key=lambda p: min(abs(celda(p.x, p.y)[0] - a) + abs(celda(p.x, p.y)[1] - b) for a, b in arbol))
            p = pend.pop(0)
            rg = rangos.get(net, (0, 10**6))
            cam = a_estrella(rj, n, arbol, {celda(p.x, p.y)}, permitir_puentes, rango=(int(rg[0] / G), int(rg[1] / G)))
            if cam is None:
                fallas.append((net, p.ref, p.num)); continue
            w = anchos.get(net, W_PISTA)
            # convertir en segmentos
            seg_ini = cam[0]
            for k in range(1, len(cam)):
                a, b = cam[k - 1], cam[k]
                if b[2] == 'j':
                    puentes.append((net, a[0] * G, a[1] * G, b[0] * G, b[1] * G))
                    rj.agregar_circulo(n, a[0] * G, a[1] * G, 1.0); rj.agregar_circulo(n, b[0] * G, b[1] * G, 1.0)
                    for (x, y) in ((a[0] * G, a[1] * G), (b[0] * G, b[1] * G)): rj.circ_mask(rj.nojump, x, y, 2.2)
            # pistas: tramos continuos sin puente, simplificados
            tramo = [cam[0]]
            tramos = []
            for k in range(1, len(cam)):
                if cam[k][2] == 'j':
                    tramos.append(tramo); tramo = [cam[k]]
                else: tramo.append(cam[k])
            tramos.append(tramo)
            for t in tramos:
                pts = [(c[0], c[1]) for c in t]
                simp = [pts[0]]
                for q in range(1, len(pts) - 1):
                    d1 = (pts[q][0] - simp[-1][0], pts[q][1] - simp[-1][1])
                    d2 = (pts[q + 1][0] - pts[q][0], pts[q + 1][1] - pts[q][1])
                    if d1[0] * d2[1] - d1[1] * d2[0] != 0: simp.append(pts[q])
                if len(pts) > 1: simp.append(pts[-1])
                for q in range(1, len(simp)):
                    x1, y1, x2, y2 = simp[q - 1][0] * G, simp[q - 1][1] * G, simp[q][0] * G, simp[q][1] * G
                    pistas.append((net, x1, y1, x2, y2, w))
                    rj.agregar_segmento(n, x1, y1, x2, y2, w / 2)
                for c in t: arbol.add((c[0], c[1]))
    return pistas, puentes, fallas

# ------------------------------------------------------------------ DRC
def _dps(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)

def _dss(a, b):
    (x1, y1, x2, y2), (x3, y3, x4, y4) = a, b
    def cruza(p1, p2, p3, p4):
        d = lambda a, b, c: (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        d1, d2, d3, d4 = d(p3, p4, p1), d(p3, p4, p2), d(p1, p2, p3), d(p1, p2, p4)
        return (d1 * d2 < 0) and (d3 * d4 < 0)
    if cruza((x1, y1), (x2, y2), (x3, y3), (x4, y4)): return 0.0
    return min(_dps(x1, y1, x3, y3, x4, y4), _dps(x2, y2, x3, y3, x4, y4), _dps(x3, y3, x1, y1, x2, y2), _dps(x4, y4, x1, y1, x2, y2))

def drc(pads, pistas, puentes, ancho, alto):
    errores = []
    cobre = []  # (net, tipo, geom, radio, desc)
    for p in pads: cobre.append((p.net, 'c', (p.x, p.y), p.r, f'{p.ref}.{p.num}'))
    for (n, x1, y1, x2, y2, w) in pistas: cobre.append((n, 's', (x1, y1, x2, y2), w / 2, 'pista'))
    for (n, x1, y1, x2, y2) in puentes:
        cobre.append((n, 'c', (x1, y1), 1.0, 'puente')); cobre.append((n, 'c', (x2, y2), 1.0, 'puente'))
    minimo = 99
    for i in range(len(cobre)):
        ni, ti, gi, ri, di = cobre[i]
        for j in range(i + 1, len(cobre)):
            nj, tj, gj, rj_, dj = cobre[j]
            if ni == nj: continue
            if ti == 'c' and tj == 'c': d = math.hypot(gi[0] - gj[0], gi[1] - gj[1])
            elif ti == 'c': d = _dps(gi[0], gi[1], *gj)
            elif tj == 'c': d = _dps(gj[0], gj[1], *gi)
            else: d = _dss(gi, gj)
            hol = d - ri - rj_
            minimo = min(minimo, hol)
            if hol < CLR_DRC - 1e-6:
                errores.append(f'holgura {hol:.2f} mm entre {ni}({di}) y {nj}({dj})')
    for (n, t, g, r, d) in cobre:
        pts = [g[:2]] + ([g[2:]] if t == 's' else [])
        for (x, y) in pts:
            if x - r < 1.0 or y - r < 1.0 or x + r > ancho - 1.0 or y + r > alto - 1.0:
                errores.append(f'cobre a menos de 1 mm del borde: {n} {d} ({x:.1f},{y:.1f})')
    # conectividad por net
    from collections import defaultdict
    porNet = defaultdict(list)
    for k, c in enumerate(cobre): porNet[c[0]].append(c)
    for (n, x1, y1, x2, y2) in puentes: porNet[n].append((n, 's', (x1, y1, x2, y2), 0.0, 'alambre'))
    sin = []
    for n, lst in porNet.items():
        if n.startswith('NC_'): continue
        padre = list(range(len(lst)))
        def raiz(a):
            while padre[a] != a: padre[a] = padre[padre[a]]; a = padre[a]
            return a
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                a, b = lst[i], lst[j]
                if a[1] == 'c' and b[1] == 'c': d = math.hypot(a[2][0] - b[2][0], a[2][1] - b[2][1])
                elif a[1] == 'c': d = _dps(a[2][0], a[2][1], *b[2])
                elif b[1] == 'c': d = _dps(b[2][0], b[2][1], *a[2])
                else: d = _dss(a[2], b[2])
                if d <= a[3] + b[3] + 1e-6: padre[raiz(i)] = raiz(j)
        grupos = {raiz(i) for i in range(len(lst)) if lst[i][4] not in ('pista', 'alambre', 'puente')}
        if len(grupos) > 1: sin.append((n, len(grupos)))
    return errores, sin, minimo
