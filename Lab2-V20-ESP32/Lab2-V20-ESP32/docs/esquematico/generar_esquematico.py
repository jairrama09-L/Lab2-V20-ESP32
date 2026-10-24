"""Esquemático completo del sistema V20 IoT (versión con optoacopladores PC817).
Genera esquematico_v20_iot.svg; el PDF/PNG se exporta con exportar.py."""
from pathlib import Path

W, H = 1720, 1120
out = []
E = lambda s: out.append(s)

AZUL, NAR, GRIS = '#2a63c9', '#b8690b', '#555'

def linea(*p, c='#111', w=1.6, dash=None):
    pts = ' '.join(f'{x},{y}' for x, y in p)
    d = f' stroke-dasharray="{dash}"' if dash else ''
    E(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="{w}"{d}/>')

def punto(x, y): E(f'<circle cx="{x}" cy="{y}" r="3.2" fill="#111"/>')
def txt(x, y, t, s=11, c='#111', a='start', b=False, f='mono'):
    fam = '"DejaVu Sans Mono",monospace' if f == 'mono' else '"DejaVu Sans",Arial,sans-serif'
    E(f'<text x="{x}" y="{y}" font-family={fam!r} font-size="{s}" fill="{c}" text-anchor="{a}"{" font-weight=\"bold\"" if b else ""}>{t}</text>')

def res_h(x1, x2, y, lab, sub=None):
    m = (x1 + x2) / 2
    linea((x1, y), (m - 18, y)); linea((m + 18, y), (x2, y))
    E(f'<rect x="{m-18}" y="{y-6}" width="36" height="12" fill="#fff" stroke="#111" stroke-width="1.5"/>')
    txt(m, y - 10, lab, 10, a='middle')
    if sub: txt(m, y + 19, sub, 9, GRIS, 'middle')

def res_v(x, y1, y2, lab, lado=1):
    m = (y1 + y2) / 2
    linea((x, y1), (x, m - 18)); linea((x, m + 18), (x, y2))
    E(f'<rect x="{x-6}" y="{m-18}" width="12" height="36" fill="#fff" stroke="#111" stroke-width="1.5"/>')
    txt(x + 10 * lado, m + 4, lab, 10, a='start' if lado > 0 else 'end')

def cap_v(x, y1, y2, lab, lado=1):
    m = (y1 + y2) / 2
    linea((x, y1), (x, m - 4)); linea((x, m + 4), (x, y2))
    linea((x - 11, m - 4), (x + 11, m - 4), w=2); linea((x - 11, m + 4), (x + 11, m + 4), w=2)
    txt(x + 15 * lado, m + 4, lab, 10, a='start' if lado > 0 else 'end')

def tierra(x, y, dom):
    c = AZUL if dom == 'esp' else NAR
    linea((x, y), (x, y + 8), c=c)
    linea((x - 9, y + 8), (x + 9, y + 8), c=c, w=2); linea((x - 6, y + 12), (x + 6, y + 12), c=c, w=2); linea((x - 3, y + 16), (x + 3, y + 16), c=c, w=2)

def etiqueta(x, y, t, dom='v20', a='start'):
    c = AZUL if dom == 'esp' else NAR
    w = 7.2 * len(t) + 10
    x0 = x if a == 'start' else x - w
    E(f'<rect x="{x0}" y="{y-9}" width="{w}" height="17" rx="3" fill="#fff" stroke="{c}" stroke-width="1.2"/>')
    txt(x0 + w / 2, y + 4, t, 10, c, 'middle', b=True)

def borne(x, y, num, nombre, lado='izq'):
    E(f'<circle cx="{x}" cy="{y}" r="5" fill="#fff" stroke="{NAR}" stroke-width="1.8"/>')
    if lado == 'izq':
        txt(x + 10, y + 4, f'{num}', 11, NAR, b=True); txt(x + 40, y + 4, nombre, 10)
    else:
        txt(x - 10, y + 4, f'{nombre}  {num}', 10, a='end')

def opto4(x, y, nombre, invertido=False):
    """PC817 de 4 pines. Caja 120×56 centrada en y. Pines: 1 A, 2 K (lado LED), 4 C, 3 E (lado transistor).
    invertido=True pone el LED a la derecha."""
    E(f'<rect x="{x}" y="{y-28}" width="120" height="56" fill="#fff" stroke="#111" stroke-width="1.5"/>')
    txt(x + 60, y - 33, nombre, 10, a='middle', b=True)
    led_x = x + 92 if invertido else x + 28
    tr_x = x + 28 if invertido else x + 92
    # LED
    E(f'<path d="M{led_x-8},{y-8} L{led_x+8},{y-8} L{led_x},{y+6} Z" fill="#111"/>')
    linea((led_x - 8, y + 6), (led_x + 8, y + 6), w=1.6)
    lx_borde = x + 120 if invertido else x
    linea((lx_borde, y - 14), (led_x, y - 14), (led_x, y - 8)); linea((led_x, y + 6), (led_x, y + 14), (lx_borde, y + 14))
    # flechas de luz
    d = -1 if invertido else 1
    linea((led_x + 12 * d, y - 2), (led_x + 22 * d, y - 2), w=1); linea((led_x + 12 * d, y + 4), (led_x + 22 * d, y + 4), w=1)
    # transistor
    tb = x + 120 if not invertido else x
    linea((tr_x - 6 * d, y - 10), (tr_x - 6 * d, y + 10), w=2)
    linea((tr_x - 6 * d, y - 4), (tr_x + 8 * d, y - 14), (tb, y - 14))
    linea((tr_x - 6 * d, y + 4), (tr_x + 8 * d, y + 14), (tb, y + 14))
    if invertido:
        txt(x + 124, y - 18, '1 A', 9, GRIS); txt(x + 124, y + 26, '2 K', 9, GRIS)
        txt(x - 4, y - 18, 'C 4', 9, GRIS, 'end'); txt(x - 4, y + 26, 'E 3', 9, GRIS, 'end')
    else:
        txt(x - 4, y - 18, 'A 1', 9, GRIS, 'end'); txt(x - 4, y + 26, 'K 2', 9, GRIS, 'end')
        txt(x + 124, y - 18, '4 C', 9, GRIS); txt(x + 124, y + 26, '3 E', 9, GRIS)
    return (x, y - 14), (x, y + 14), (x + 120, y - 14), (x + 120, y + 14)

# =========================================================== marco y títulos
E(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>')
txt(30, 38, 'Control IoT del SINAMICS V20 con ESP32 — esquemático completo (versión con optoacopladores PC817)', 18, b=True, f='sans')
txt(30, 60, 'Lab. 2 · Electrónica de Potencia · Universidad del Magdalena · firmware v20_iot_esp32.ino v3.2 · bornes según "Tabla de Conexiones de Módulos de Entrenamiento"', 11, GRIS, f='sans')
E(f'<rect x="{W-420}" y="22" width="390" height="44" fill="#fff" stroke="#bbb"/>')
etiqueta(W - 410, 36, 'GND ESP32 / USB', 'esp'); etiqueta(W - 260, 36, '0V del V20 + fuente ext.', 'v20')
txt(W - 410, 60, 'Los dos dominios de tierra NO se unen nunca.', 10, GRIS, f='sans')

# =========================================================== ESP32
EX0, EX1 = 60, 250
E(f'<rect x="{EX0}" y="110" width="{EX1-EX0}" height="960" rx="6" fill="#eef3fd" stroke="{AZUL}" stroke-width="2"/>')
txt((EX0 + EX1) / 2, 140, 'ESP32', 18, AZUL, 'middle', b=True, f='sans'); txt((EX0 + EX1) / 2, 158, 'DevKit V1', 11, AZUL, 'middle', f='sans')
pines = {'3V3': 190, '5V (VIN)': 220, 'GND': 250, 'GPIO25': 300, 'GPIO26': 486, 'GPIO27': 566, 'GPIO32': 646,
         'GPIO35': 786, 'GPIO33': 886, 'GPIO34': 1010}
for n, y in pines.items():
    txt(EX1 - 8, y + 4, n, 11, a='end', b=n.startswith('GPIO'))
    linea((EX1, y), (EX1 + 14, y), c=AZUL)
etiqueta(EX1 + 16, 190, '3V3', 'esp'); linea((EX1 + 14, 250), (EX1 + 30, 250), c=AZUL); tierra(EX1 + 30, 250, 'esp')
txt(70, 1050, 'USB: solo para programar,', 9, AZUL, f='sans'); txt(70, 1062, 'con J11 desconectado', 9, AZUL, f='sans')
linea((EX1 + 14, 220), (340, 220), c=AZUL)
E(f'<circle cx="340" cy="220" r="5" fill="#fff" stroke="{AZUL}" stroke-width="1.8"/>'); txt(334, 214, '+', 11, AZUL, 'end', b=True)
E(f'<rect x="346" y="176" width="176" height="62" rx="4" fill="#fff" stroke="{AZUL}" stroke-width="1.5"/>')
txt(434, 192, 'J11 · FUENTE 5 V DEL ESP32', 10, AZUL, 'middle', b=True, f='sans')
txt(354, 208, '+5V → VIN y ACS712 (J5)', 9, f='sans'); txt(354, 221, '(−) → GND del ESP32', 9, f='sans')
txt(354, 234, 'aparte de la fuente del V20', 9, '#b3261e', f='sans')

# barrera de aislamiento
linea((650, 200), (650, 930), c='#888', w=1.4, dash='7 6')
txt(656, 214, 'barrera de aislamiento', 10, '#777', f='sans')
txt(600, 214, 'lado ESP32', 10, AZUL, 'end', f='sans'); txt(660, 230, 'lado V20', 10, NAR, f='sans')

# =========================================================== V20 regleta de control
VX = 1500
E(f'<rect x="{VX}" y="270" width="200" height="680" rx="6" fill="#fdf4e7" stroke="{NAR}" stroke-width="2"/>')
txt(VX + 100, 292, 'SINAMICS V20', 14, NAR, 'middle', b=True, f='sans'); txt(VX + 100, 307, 'bornes de control del módulo', 9, NAR, 'middle', f='sans')
bornes = {89: (330, 'AI1 (2)'), 92: (380, '0V analóg. (5)'), 100: (460, '+24 V (13)'), 95: (514, 'DI1 (8)'), 96: (594, 'DI2 (9)'),
          97: (674, 'DI3 (10)'), 99: (710, 'DI C (12)'), 101: (750, '0V (14)'), 102: (800, 'DO1+ (15)'), 103: (850, 'DO1− (16)'),
          105: (886, 'DO2 NO (18)'), 106: (920, 'DO2 C (19)')}
for n, (y, nom) in bornes.items():
    borne(VX, y, n, nom)

# =========================================================== 1. CONSIGNA (AI1)
txt(310, 262, '① CONSIGNA 0–10 V → AI1', 12, b=True, f='sans')
yA = 286
linea((EX1 + 14, 300), (290, 300), (290, yA), (330, yA))
res_h(330, 420, yA, 'R1 220 Ω')
linea((420, yA), (560, yA))
E(f'<rect x="560" y="258" width="180" height="96" fill="#fff" stroke="#111" stroke-width="1.5"/>')
txt(650, 252, '6N137', 11, a='middle', b=True)
E('<path d="M590,282 L606,282 L598,296 Z" fill="#111"/>'); linea((590, 296), (606, 296))
linea((560, yA), (575, yA), (575, 274), (598, 274), (598, 282)); linea((598, 296), (598, 322), (560, 322))
txt(556, 280, '2', 9, GRIS, 'end'); txt(556, 318, '3', 9, GRIS, 'end')
linea((540, 322), (560, 322)); linea((540, 322), (540, 336)); tierra(540, 336, 'esp')
E('<rect x="682" y="280" width="34" height="34" fill="none" stroke="#111" stroke-width="1.3"/>'); txt(699, 302, '&amp;', 12, a='middle')
for yy, n, lab in [(268, '8', 'VCC'), (282, '7', 'VE'), (308, '6', 'VO'), (340, '5', 'GND')]:
    linea((740, yy), (760, yy)); txt(744, yy - 3, n, 8, GRIS)
linea((760, 268), (760, 282)); punto(760, 268); linea((760, 268), (760, 236)); etiqueta(744, 228, '+5V EXT')
linea((760, 340), (760, 352)); tierra(760, 352, 'v20')
# pull-up y 74HC14
linea((760, 308), (850, 308)); punto(850, 308)
res_v(850, 236, 308, 'R2 1 kΩ', -1); etiqueta(834, 228, '+5V EXT')
linea((850, 308), (900, 308))
E('<path d="M900,288 L900,328 L936,308 Z" fill="#fff" stroke="#111" stroke-width="1.5"/>'); E('<circle cx="941" cy="308" r="5" fill="#fff" stroke="#111" stroke-width="1.5"/>')
txt(918, 282, '74HC14', 10, a='middle', b=True); txt(895, 304, '1', 8, GRIS, 'end'); txt(950, 304, '2', 8, GRIS)
linea((946, 308), (960, 308))
res_h(960, 1030, 308, 'R3 10 kΩ 1%')
linea((1030, 308), (1090, 308)); punto(1050, 308)
cap_v(1050, 308, 372, 'C1 1 µF', -1); tierra(1050, 372, 'v20')
txt(1030, 400, 'poliéster', 9, GRIS, 'end')
# LM358
E('<path d="M1090,276 L1090,356 L1160,316 Z" fill="#fff" stroke="#111" stroke-width="1.5"/>')
txt(1100, 300, '+', 13); txt(1101, 342, '−', 13); txt(1110, 270, 'LM358', 10, b=True)
txt(1086, 304, '3', 8, GRIS, 'end'); txt(1086, 344, '2', 8, GRIS, 'end'); txt(1166, 312, '1', 8, GRIS)
linea((1090, 340), (1080, 340), (1080, 395)); punto(1080, 395)
res_v(1080, 395, 435, 'Rg 10 kΩ 1%', 1); tierra(1080, 435, 'v20')
res_h(1080, 1180, 395, 'Rf 10 kΩ 1%'); linea((1180, 395), (1180, 316)); punto(1180, 316)
linea((1160, 316), (1200, 316))
linea((1125, 296), (1125, 250)); etiqueta(1110, 242, '+12V EXT'); txt(1130, 262, '8', 8, GRIS)
linea((1125, 336), (1125, 360)); tierra(1125, 360, 'v20'); txt(1130, 354, '4', 8, GRIS)
res_h(1200, 1280, 316, 'R4 100 Ω')
linea((1280, 316), (1340, 316), (1340, 330), (VX - 5, 330)); punto(1310, 316)
linea((1310, 316), (1310, 344))
E('<path d="M1300,364 L1320,364 L1310,348 Z" fill="#111"/>'); linea((1298, 348), (1322, 348), w=2)
linea((1310, 364), (1310, 380)); tierra(1310, 380, 'v20')
txt(1326, 362, 'DZ 1N4742A', 10); txt(1326, 375, '12 V · 1 W', 9, GRIS)
txt(1200, 430, 'V(AI1) = 2·5 V·D = 10·D [V]', 10, GRIS)
# fuente externa
E(f'<rect x="1250" y="110" width="200" height="88" rx="4" fill="#fff" stroke="{NAR}" stroke-width="1.5"/>')
txt(1350, 128, 'FUENTE EXTERNA', 11, NAR, 'middle', b=True, f='sans')
txt(1262, 148, '+5 V → 6N137, 74HC14', 10); txt(1262, 164, '+12 V → LM358 (o 15 V)', 10); txt(1262, 180, '(−) común de ambas salidas', 10)
linea((1450, 185), (1475, 185), (1475, 380), (VX - 5, 380)); txt(1458, 200, '(−)', 9, NAR)
txt(1262, 214, 'no conectar el borne de tierra física', 9, '#b3261e')

# =========================================================== 2. MANDO (DI1–DI3)
txt(310, 452, '② MANDO: marcha, atrás y reset por entradas digitales (modo PNP)', 12, b=True, f='sans')
BUS = 900
linea((BUS, 460), (VX - 5, 460)); punto(BUS, 460)
txt(BUS + 8, 454, '+24 V del V20', 10, NAR, b=True)
for i, (gp, yC, ter, nom) in enumerate([('GPIO26', 500, 95, 'PC817 #1 · MARCHA'), ('GPIO27', 580, 96, 'PC817 #2 · ATRÁS'), ('GPIO32', 660, 97, 'PC817 #3 · RESET')]):
    a, k, c, e = opto4(590, yC, nom)
    yg = pines[gp]
    linea((EX1 + 14, yg), (300, yg)); punto(300, yg)
    res_v(300, yg, yg + 46, '10 kΩ', -1); tierra(300, yg + 46, 'esp')
    res_h(300, 480, yg, '220 Ω')
    linea((480, yg), (590, yg))
    linea((590, k[1]), (560, k[1]), (560, k[1] + 6)); tierra(560, k[1] + 6, 'esp')
    linea((710, c[1]), (BUS, c[1])); punto(BUS, c[1])
    linea((710, e[1]), (VX - 5, e[1]))
linea((BUS, 460), (BUS, 786))
linea((VX - 5, 710), (1470, 710), (1470, 750), (VX - 5, 750)); punto(1470, 750)
txt(1462, 732, 'puente DIC–0V', 9, NAR, 'end')
txt(330, 704, 'I LED ≈ (3,3 − 1,2) / 220 = 9,5 mA → ≥ 4,8 mA a la DI con CTR mín. 50 % · 10 kΩ a GND: LED apagado en el reset', 9, GRIS, f='sans')

# =========================================================== 3. ESTADO (DO1, DO2)
txt(310, 728, '③ ESTADO del V20: en marcha (DO1) y falla (DO2)', 12, b=True, f='sans')
a, k, c, e = opto4(590, 800, 'PC817 #4 · EN MARCHA', invertido=True)
linea((EX1 + 14, 786), (590, 786)); punto(400, 786)
res_v(400, 786, 748, '10 kΩ', 1); etiqueta(384, 744, '3V3', 'esp')
linea((590, 814), (560, 814), (560, 820)); tierra(560, 820, 'esp')
res_h(710, 860, 786, 'R 2,2 kΩ ½ W'); linea((860, 786), (BUS, 786)); punto(BUS, 786)
linea((710, 814), (980, 814), (980, 800), (VX - 5, 800))
linea((VX - 5, 850), (1450, 850), (1450, 750)); punto(1450, 750)
txt(1442, 840, 'DO1− a 0V', 9, NAR, 'end')
txt(745, 846, 'LED alimentado desde +24 V a través del transistor DO1', 9, GRIS, f='sans')
linea((EX1 + 14, 886), (330, 886)); res_h(330, 440, 886, '1 kΩ'); linea((440, 886), (VX - 5, 886))
linea((VX - 5, 920), (480, 920), (480, 930)); tierra(480, 930, 'esp')
txt(500, 912, 'contacto seco del relé DO2 (aislado 4 kV dentro del V20) · GPIO33 con pull-up interno', 9, GRIS, f='sans')

# =========================================================== 4. CORRIENTE Y POTENCIA
txt(310, 965, '④ CORRIENTE DE FASE (ACS712) Y POTENCIA', 12, b=True, f='sans')
linea((EX1 + 14, 1010), (520, 1010)); punto(470, 1010)
res_v(470, 1010, 1066, '20 kΩ', -1); tierra(470, 1066, 'esp')
cap_v(520, 1010, 1066, '22 nF', 1); tierra(520, 1066, 'esp')
linea((470, 1010), (520, 1010)); res_h(520, 640, 1010, 'R 10 kΩ'); linea((640, 1010), (700, 1010))
E(f'<rect x="700" y="968" width="150" height="96" fill="#fff" stroke="#111" stroke-width="1.5"/>')
txt(775, 962, 'ACS712 (5 A rec.)', 10, a='middle', b=True)
linea((780, 972), (780, 1060), c='#888', w=1, dash='4 3')
for yy, n in [(985, 'VCC'), (1010, 'OUT'), (1040, 'GND')]:
    txt(706, yy + 4, n, 9)
linea((700, 985), (665, 985)); etiqueta(612, 985, '5V J11', 'esp')
linea((700, 1040), (680, 1040), (680, 1048)); tierra(680, 1048, 'esp')
txt(844, 989, 'IP+', 9, a='end'); txt(844, 1044, 'IP−', 9, a='end')
# potencia
E(f'<rect x="950" y="968" width="70" height="96" fill="#fdf4e7" stroke="{NAR}" stroke-width="1.5"/>')
txt(985, 962, 'V20 salida', 10, NAR, 'middle', b=True)
for yy, t in [(985, '83 U'), (1015, '84 V'), (1045, '85 W')]:
    txt(985, yy + 4, t, 10, a='middle')
linea((850, 985), (950, 985), c='#b3261e', w=2.4)
linea((850, 1040), (870, 1040), (870, 1090), (1150, 1090), (1150, 985), (1230, 985), c='#b3261e', w=2.4)
linea((1020, 1015), (1230, 1015), c='#b3261e', w=2.4); linea((1020, 1045), (1230, 1045), c='#b3261e', w=2.4)
E(f'<rect x="1230" y="968" width="250" height="110" rx="4" fill="#fff" stroke="#111" stroke-width="1.5"/>')
txt(1355, 960, 'MOTOR 3φ 1 HP · 2 polos', 10, a='middle', b=True)
for yy, t in [(985, '1  U1'), (1015, '2  V1'), (1045, '3  W1')]:
    txt(1240, yy + 4, t, 10)
txt(1300, 990, 'DELTA (bornes 7–12):', 9, b=True)
txt(1300, 1006, '7–12  U1–W2', 9); txt(1300, 1020, '8–10  V1–U2', 9); txt(1300, 1034, '9–11  W1–V2', 9)
txt(1300, 1058, 'Tensión de red PWM', 9, '#b3261e'); txt(1300, 1071, 'breaker en OFF', 9, '#b3261e')
txt(880, 1104, 'Potencia (rojo): cable con terminales, nunca protoboard', 9, '#b3261e', f='sans')

# notas
notas = ['Desacople: C2 100 nF en el 6N137 (8–5),', 'lo pide su hoja de datos.',
         '74HC14 sin usar: entradas 3, 5 a 0V;', '9, 11, 13 a +5V; salidas 4,6,8,10,12 libres.',
         'LM358 unidad B sin usar: 5 a 0V,', '6 unido a 7 (seguidor).']
for i, t in enumerate(notas): txt(1500, 972 + 13 * i, t, 8.5, f='sans')
for i, t in enumerate(['Parámetros V20: P0700=2 P1000=2', 'P0701=1 P0702=12 P0703=9', 'P0731=52.2 P0732=52.3', 'P0759 = r0752 con 60 Hz']):
    txt(1500, 1054 + 13 * i, t, 8.5, f='sans', b=True)

svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">' + '\n'.join(out) + '</svg>'
Path(__file__).with_name('esquematico_v20_iot.svg').write_text(svg, encoding='utf-8')
print('ok')
