"""Diseño del PCB (una cara, THT) de la tarjeta de interfaz ESP32 ↔ SINAMICS V20.
Define huellas, ubicación y netlist. Unidades: mm, eje y hacia abajo, vista desde el lado de componentes."""
P = 2.54
G = 0.635  # rejilla de ruteo

class Pad:
    def __init__(s, ref, num, x, y, net, d=1.9, drill=0.8, cuadrado=False):
        s.ref, s.num, s.x, s.y, s.net, s.d, s.drill, s.cuadrado = ref, num, x, y, net, d, drill, cuadrado
    @property
    def r(s): return s.d / 2

class Comp:
    def __init__(s, ref, valor, tipo, pads, cuerpo, etiqueta=None):
        s.ref, s.valor, s.tipo, s.pads, s.cuerpo = ref, valor, tipo, pads, cuerpo  # cuerpo: (x0,y0,x1,y1)
        s.etiqueta = etiqueta

comps = []

def dip(ref, valor, x, y, n, nets, rot=0):
    """rot=0: pin 1 arriba-izq, columnas verticales (7,62 mm). rot=180: girado.
    rot=90: filas horizontales, pin 1 abajo-izq (muesca a la izquierda)."""
    pads = []
    h = n // 2
    for i in range(n):
        if i < h: sx, sy = 0, i * P
        else: sx, sy = 3 * P, (n - 1 - i) * P
        if rot == 180: sx, sy = 3 * P - sx, (h - 1) * P - sy
        if rot == 90: sx, sy = sy, 3 * P - sx
        pads.append(Pad(ref, i + 1, x + sx, y + sy, nets[i], 1.8, 0.8, i == 0))
    xs = [p.x for p in pads]; ys = [p.y for p in pads]
    if rot == 90: cuerpo = (min(xs) - 1.3, min(ys) + 1.1, max(xs) + 1.3, max(ys) - 1.1)
    else: cuerpo = (min(xs) + 1.1, min(ys) - 1.3, max(xs) - 1.1, max(ys) + 1.3)
    c = Comp(ref, valor, 'dip', pads, cuerpo); c.rot = rot; comps.append(c); return c

def axial(ref, valor, x1, y1, x2, y2, n1, n2, drill=0.8, d=1.9, ancho=2.6):
    pads = [Pad(ref, 1, x1, y1, n1, d, drill, False), Pad(ref, 2, x2, y2, n2, d, drill, False)]
    if y1 == y2: cuerpo = (min(x1, x2) + 2.2, y1 - ancho / 2, max(x1, x2) - 2.2, y1 + ancho / 2)
    else: cuerpo = (x1 - ancho / 2, min(y1, y2) + 2.2, x1 + ancho / 2, max(y1, y2) - 2.2)
    c = Comp(ref, valor, 'axial', pads, cuerpo); comps.append(c); return c

def radial(ref, valor, x1, y1, x2, y2, n1, n2, ancho=3.0):
    pads = [Pad(ref, 1, x1, y1, n1, 1.7, 0.8), Pad(ref, 2, x2, y2, n2, 1.7, 0.8)]
    if y1 == y2: cuerpo = (min(x1, x2) - 1.2, y1 - ancho / 2, max(x1, x2) + 1.2, y1 + ancho / 2)
    else: cuerpo = (x1 - ancho / 2, min(y1, y2) - 1.2, x1 + ancho / 2, max(y1, y2) + 1.2)
    c = Comp(ref, valor, 'cap', pads, cuerpo); comps.append(c); return c

def bornera(ref, valor, x, y, nets, etiquetas, vertical=True):
    pads = []
    for i, n in enumerate(nets):
        px, py = (x, y + i * 5.08) if vertical else (x + i * 5.08, y)
        pads.append(Pad(ref, i + 1, px, py, n, 2.8, 1.3, i == 0))
    if vertical: cuerpo = (x - 3.6, y - 2.6, x + 4.6, y + (len(nets) - 1) * 5.08 + 2.6)
    else: cuerpo = (x - 2.6, y - 4.6, x + (len(nets) - 1) * 5.08 + 2.6, y + 3.6)
    c = Comp(ref, valor, 'bornera', pads, cuerpo, etiquetas); c.vertical = vertical; comps.append(c); return c

def tira(ref, valor, x, y, nets, vertical=True, d=1.8, drill=1.0):
    pads = []
    for i, n in enumerate(nets):
        px, py = (x, y + i * P) if vertical else (x + i * P, y)
        pads.append(Pad(ref, i + 1, px, py, n, d, drill, i == 0))
    if vertical: cuerpo = (x - 1.3, y - 1.3, x + 1.3, y + (len(nets) - 1) * P + 1.3)
    else: cuerpo = (x - 1.3, y - 1.3, x + (len(nets) - 1) * P + 1.3, y + 1.3)
    c = Comp(ref, valor, 'tira', pads, cuerpo); comps.append(c); return c

NC = lambda tag: f'NC_{tag}'

# ---------------------------------------------------------------- ESP32 (girado 180°: USB arriba)
Y0 = 10.16
L = ['V5E', 'GND', NC(1), NC(2), NC(3), 'G27', 'G26', 'G25', 'G33', 'G32', 'G35', 'G34', NC(4), NC(5), NC(6)]
nombresL = ['VIN', 'GND', 'D13', 'D12', 'D14', 'D27', 'D26', 'D25', 'D33', 'D32', 'D35', 'D34', 'VN', 'VP', 'EN']
nombresR = ['3V3', 'GND', 'D15', 'D2', 'D4', 'RX2', 'TX2', 'D5', 'D18', 'D19', 'D21', 'RX0', 'TX0', 'D22', 'D23']
jL = tira('J1', 'ESP32 lado A', 30.48, Y0, L)
jRa = tira('J2', 'ESP32 lado B (22,86)', 7.62, Y0, ['V33'] + [NC(f'a{k}') for k in range(1, 15)])
jRb = tira('J3', 'ESP32 lado B (25,40)', 5.08, Y0, ['V33'] + [NC(f'b{k}') for k in range(1, 15)])
ESP_CUERPO = (2.0, 4.0, 33.6, 66.0)
ANTENA = (3.0, 49.5, 33.0, 66.0)

# ---------------------------------------------------------------- columna de aislamiento
XO = 63.5
dip('OK2', 'PC817', XO, 12.70, 4, ['A_OK2', 'GND', 'DI2', 'V24'])
dip('OK1', 'PC817', XO, 20.32, 4, ['A_OK1', 'GND', 'DI1', 'V24'])
dip('U1', '6N137', XO, 27.94, 8, [NC('u1'), 'A6', 'GND', NC('u4'), 'GX', 'VO6', 'P5X', 'P5X'])
dip('OK3', 'PC817', XO, 43.18, 4, ['A_OK3', 'GND', 'DI3', 'V24'])
dip('OK4', 'PC817', XO, 50.80, 4, ['A_OK4', 'DO1P', 'GND', 'G35'], rot=180)

# ---------------------------------------------------------------- lado ESP32
# Por canal: R serie de 48,26 a 58,42 (fila del ánodo) y pull-down de 43,18 a 53,34 (fila del cátodo).
# La espina de GND corre en x = 53,34 y pasa por debajo de las R serie.
axial('R5', '220', 48.26, 12.70, 58.42, 12.70, 'G27', 'A_OK2')
axial('R8', '10k', 43.18, 15.24, 53.34, 15.24, 'G27', 'GND')
axial('R6', '220', 48.26, 20.32, 58.42, 20.32, 'G26', 'A_OK1')
axial('R9', '10k', 43.18, 22.86, 53.34, 22.86, 'G26', 'GND')
axial('R1', '220', 48.26, 30.48, 58.42, 30.48, 'G25', 'A6')
axial('R7', '220', 48.26, 43.18, 58.42, 43.18, 'G32', 'A_OK3')
axial('R10', '10k', 43.18, 45.72, 53.34, 45.72, 'G32', 'GND')
axial('R11', '10k', 48.26, 55.88, 58.42, 55.88, 'V33', 'G35')
axial('R12', '1k', 27.94, 71.12, 38.10, 71.12, 'DO2NO', 'G33')
axial('R13', '10k', 43.18, 78.74, 53.34, 78.74, 'ACSO', 'G34')
axial('R14', '20k', 45.72, 68.58, 55.88, 68.58, 'G34', 'GND')
radial('C5', '22n', 58.42, 68.58, 58.42, 73.66, 'G34', 'GND')
tira('J5', 'ACS712', 33.02, 81.28, ['V5E', 'ACSO', 'GND'], vertical=False)
bornera('J6', 'DO2', 7.62, 76.20, ['DO2NO', 'GND'], ['105', '106'], vertical=False)
bornera('J11', '5V ESP32', 22.86, 81.28, ['V5E', 'GND'], ['+5V', 'GND'], vertical=False)  # fuente aparte del ESP32 y del ACS712

# ---------------------------------------------------------------- lado V20
axial('R2', '1k', 78.74, 22.86, 78.74, 33.02, 'P5X', 'VO6')
radial('C2', '100n', 76.20, 38.10, 76.20, 43.18, 'P5X', 'GX')
dip('U2', '74HC14', 86.36, 25.40, 14, ['VO6', 'HCO', 'GX', NC('h4'), 'GX', NC('h6'), 'GX',
                                       NC('h8'), 'P5X', NC('h10'), 'P5X', NC('h12'), 'P5X', 'P5X'], rot=90)
axial('R3', '10k', 99.06, 38.10, 109.22, 38.10, 'HCO', 'RCN')
radial('C1', '1u', 111.76, 38.10, 111.76, 43.18, 'RCN', 'GX', ancho=4.0)
dip('U3', 'LM358', 116.84, 25.40, 8, ['OPO', 'FB', 'RCN', 'GX', 'GX', 'LMB', 'LMB', 'P12X'], rot=90)
axial('R15', '10k', 116.84, 40.64, 127.00, 40.64, 'FB', 'GX')   # Rg
axial('R16', '10k', 106.68, 45.72, 116.84, 45.72, 'OPO', 'FB')  # Rf
axial('R4', '100', 116.84, 50.80, 127.00, 50.80, 'OPO', 'AI1')
axial('D1', '1N4742A', 127.00, 55.88, 127.00, 66.04, 'AI1', 'GX', drill=1.0, d=2.0)
bornera('J7', 'ALIM', 135.89, 12.70, ['P5X', 'P12X', 'GX'], ['+5', '+12', '0V'])
bornera('J8', 'AI1', 135.89, 60.96, ['AI1', 'GX'], ['89', '92'])
bornera('J9', 'DI', 101.60, 6.35, ['V24', 'DI2', 'DI1'], ['100', '96', '95'], vertical=False)
bornera('J10', 'DI/DO', 101.60, 78.74, ['DI3', 'DO1P'], ['97', '102'], vertical=False)
axial('R17', '2,2k', 76.20, 58.42, 88.90, 58.42, 'A_OK4', 'V24', drill=0.9, d=2.0, ancho=3.4)

ANCHO, ALTO = 142.24, 86.36
BARRERA_X = (XO + XO + 3 * P) / 2

def pads():
    return [p for c in comps for p in c.pads]

DOMINIO_ESP = {'GND', 'V5E', 'V33', 'G25', 'G26', 'G27', 'G32', 'G33', 'G34', 'G35', 'A_OK1', 'A_OK2', 'A_OK3', 'A6',
               'DO2NO', 'ACSO'}

# Pistas trazadas a mano antes del ruteo automático: (net, [puntos])
PREVIAS = [
    ('GND', [(30.48, 12.70), (35.56, 12.70), (38.10, 10.16), (53.34, 10.16), (53.34, 50.80), (63.50, 50.80)]),
    ('GND', [(53.34, 15.24), (63.50, 15.24)]),
    ('GND', [(53.34, 22.86), (63.50, 22.86)]),
    ('GND', [(53.34, 33.02), (63.50, 33.02)]),
    ('GND', [(53.34, 45.72), (63.50, 45.72)]),
    ('A_OK2', [(58.42, 12.70), (63.50, 12.70)]),
    ('A_OK1', [(58.42, 20.32), (63.50, 20.32)]),
    ('A6', [(58.42, 30.48), (63.50, 30.48)]),
    ('A_OK3', [(58.42, 43.18), (63.50, 43.18)]),
    ('G27', [(30.48, 22.86), (33.02, 22.86), (40.64, 15.24), (43.18, 15.24), (45.72, 12.70), (48.26, 12.70)]),
    ('G26', [(30.48, 25.40), (40.64, 25.40), (43.18, 22.86), (45.72, 20.32), (48.26, 20.32)]),
    ('G25', [(30.48, 27.94), (45.72, 27.94), (48.26, 30.48)]),
    ('G32', [(30.48, 33.02), (33.02, 33.02), (43.18, 43.18), (45.72, 43.18), (48.26, 43.18)]),
    ('G32', [(43.18, 43.18), (43.18, 45.72)]),
]

# Agujeros de fijación M3 (sin cobre útil; se dejan como obstáculo)
AGUJEROS = [(3.81, 3.81), (ANCHO - 3.81, 3.81), (3.81, ALTO - 3.81), (ANCHO - 3.81, ALTO - 3.81)]
for k, (x, y) in enumerate(AGUJEROS):
    c = Comp(f'H{k+1}', 'M3', 'agujero', [Pad(f'H{k+1}', 1, x, y, f'NC_H{k+1}', 3.2, 3.2)], (x - 1.6, y - 1.6, x + 1.6, y + 1.6))
    comps.append(c)
TEXTO_COBRE = (108.0, 72.0, 130.0, 84.0)   # zona del texto en cobre (verifica el lado al planchar)
