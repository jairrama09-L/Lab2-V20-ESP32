"""PDF de fabricación casera, dibujado directamente desde los Gerber/Excellon generados."""
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib
import diseno as D
from lector_gerber import leer_gerber, leer_excellon

fdir = matplotlib.get_data_path() + '/fonts/ttf/'
pdfmetrics.registerFont(TTFont('DV', fdir + 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DVB', fdir + 'DejaVuSans-Bold.ttf'))
MM = 72 / 25.4
base = 'salida/gerber/V20IoT'
CU = leer_gerber(base + '-B_Cu.gbl')
SK = leer_gerber(base + '-F_SilkS.gto')
DR = leer_excellon(base + '-PTH.drl') + leer_excellon(base + '-NPTH.drl')
PUENTES = json.load(open('ruteo.json'))['puentes']

def dibujar(c, prims, ox, oy, color=(0, 0, 0), fondo=(1, 1, 1)):
    for tipo, g, pol in prims:
        col = color if pol == 'D' else fondo
        c.setFillColorRGB(*col); c.setStrokeColorRGB(*col)
        if tipo == 'circ':
            x, y, r = g; c.circle((ox + x) * MM, (oy + y) * MM, r * MM, stroke=0, fill=1)
        elif tipo == 'rect':
            x, y, a, b = g; c.rect((ox + x - a / 2) * MM, (oy + y - b / 2) * MM, a * MM, b * MM, stroke=0, fill=1)
        elif tipo == 'linea':
            x1, y1, x2, y2, w = g; c.setLineWidth(w * MM); c.setLineCap(1)
            c.line((ox + x1) * MM, (oy + y1) * MM, (ox + x2) * MM, (oy + y2) * MM)
        elif tipo == 'poly':
            p = c.beginPath(); p.moveTo((ox + g[0][0]) * MM, (oy + g[0][1]) * MM)
            for (x, y) in g[1:]: p.lineTo((ox + x) * MM, (oy + y) * MM)
            p.close(); c.drawPath(p, stroke=0, fill=1)

def contorno(c, ox, oy, w=0.2):
    c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(w * MM)
    c.rect(ox * MM, oy * MM, D.ANCHO * MM, D.ALTO * MM, stroke=1, fill=0)

def agujeros(c, ox, oy, piloto=0.6):
    c.setFillColorRGB(1, 1, 1)
    for (x, y, d) in DR:
        c.circle((ox + x) * MM, (oy + y) * MM, min(piloto, d) / 2 * MM, stroke=0, fill=1)

def texto(c, x, y, t, s=9, b=False, col=(0, 0, 0)):
    c.setFillColorRGB(*col); c.setFont('DVB' if b else 'DV', s); c.drawString(x * MM, y * MM, t)

def regla(c, x, y):
    c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.3 * MM)
    c.line(x * MM, y * MM, (x + 100) * MM, y * MM)
    for k in range(11):
        h = 3 if k % 5 == 0 else 1.8
        c.line((x + 10 * k) * MM, y * MM, (x + 10 * k) * MM, (y + h) * MM)
    texto(c, x, y - 4.5, '0', 7); texto(c, x + 97, y - 4.5, '100 mm', 7)

c = canvas.Canvas('salida/PCB_V20IoT_planchado_1a1.pdf', pagesize=landscape(A4))
c.setTitle('PCB interfaz ESP32 - SINAMICS V20 (una cara)')
PW, PH = 297, 210

# ---------------------------------------------------------------- pág. 1: cobre para planchado
ox = 12
for oy in (112, 14):
    dibujar(c, CU, ox, oy); agujeros(c, ox, oy); contorno(c, ox, oy)
x = 165
texto(c, x, 196, 'Cobre — lado de soldadura', 14, True)
lineas = ['Imprimir al 100 % ("Tamaño real", sin "Ajustar a página").',
          'Medir la regla: debe dar exactamente 100 mm.',
          'Impresora láser o fotocopia; papel couché o de transferencia.',
          'NO espejar: la hoja ya está lista para planchar.',
          'Al terminar, el texto de cobre "LAB2 V20 IoT" debe',
          'leerse BIEN mirando la tarjeta por el lado del cobre.',
          'Si se lee al revés, el diseño quedó espejado.',
          '',
          'Dos copias por si la primera transferencia falla.',
          'Tarjeta: 142,24 × 86,36 mm, una cara (FR4 o baquelita).',
          'Pistas de 0,8 y 1,0 mm; holgura mínima 0,5 mm.',
          'Puntos blancos = guía de broca (0,6 mm).']
for i, l in enumerate(lineas): texto(c, x, 186 - 6 * i, l, 9)
texto(c, x, 105, 'Brocas', 11, True)
from collections import Counter
cnt = Counter(round(d, 2) for (_, _, d) in DR)
uso = {0.8: 'IC, resistencias, condensadores, puentes W', 0.9: 'R17 (2,2 kΩ ½ W)', 1.0: 'ESP32, tiras, D1',
       1.3: 'borneras 5,08 mm', 3.2: 'fijación M3'}
for i, (d, n) in enumerate(sorted(cnt.items())):
    texto(c, x, 98 - 6 * i, f'Ø {d:.1f} mm · {n:3d} agujeros · {uso.get(d, "")}', 9)
regla(c, x, 40)
texto(c, x, 28, 'Verificación eléctrica del diseño: 0 cortos, 0 aberturas,', 8, col=(0.3, 0.3, 0.3))
texto(c, x, 23, 'leída desde el Gerber con un verificador independiente.', 8, col=(0.3, 0.3, 0.3))
c.showPage()

# ---------------------------------------------------------------- pág. 2: mapa de montaje
ox, oy = 12, 62
c.setFillColorRGB(0.06, 0.36, 0.17); c.rect(ox * MM, oy * MM, D.ANCHO * MM, D.ALTO * MM, stroke=0, fill=1)
dibujar(c, CU, ox, oy, color=(0.42, 0.55, 0.38), fondo=(0.06, 0.36, 0.17))
agujeros(c, ox, oy, 0.9)
dibujar(c, SK, ox, oy, color=(1, 1, 1), fondo=(0.06, 0.36, 0.17))
c.setStrokeColorRGB(1, 0.25, 0.25); c.setLineWidth(0.7 * MM)
for (n, x1, y1, x2, y2) in PUENTES:
    c.line((ox + x1) * MM, (oy + D.ALTO - y1) * MM, (ox + x2) * MM, (oy + D.ALTO - y2) * MM)
texto(c, 12, 196, 'Mapa de montaje — vista desde el lado de componentes', 14, True)
texto(c, 12, 189, 'Cobre en verde claro (visto por transparencia). Puentes de alambre W en rojo: van por el lado de componentes.', 9)
# tabla de valores
vals = [(cm.ref, cm.valor) for cm in D.comps if cm.tipo not in ('agujero',) and not cm.ref.startswith('J')]
orden = lambda r: (r[0].rstrip('0123456789'), int(''.join(ch for ch in r[0] if ch.isdigit()) or 0))
vals.sort(key=orden)
x0 = 162
texto(c, x0, 152, 'Valores', 11, True)
for i, (r, v) in enumerate(vals):
    col, fila = divmod(i, 15)
    texto(c, x0 + col * 42, 145 - fila * 5.2, f'{r:5s} {v}', 8.5)
texto(c, 12, 52, 'Conectores', 11, True)
conect = ['J1 / J2 / J3: tira hembra 1×15 para el ESP32 DevKit V1 de 30 pines, USB hacia arriba. J1 siempre;',
          '   de J2 y J3 solde solo UNA: la que coincida con el ancho de su ESP32 (22,86 mm → J2; 25,40 mm → J3).',
          'J5: tira 1×3 al módulo ACS712 (VCC, OUT, GND).  J6: bornera 2P → bornes 105 / 106 (DO2 del V20).',
          'J11: fuente de 5 V APARTE (cargador USB ≥ 1 A): alimenta el ESP32 por VIN y el ACS712. No usar la +5 V de J7: uniría las tierras.',
          'J7: bornera 3P → fuente externa +5 V / +12 V / 0V.  J8: bornera 2P → bornes 89 (AI1) / 92 (0V).',
          'J9: bornera 3P → bornes 100 (+24 V) / 96 (DI2) / 95 (DI1).  J10: bornera 2P → bornes 97 (DI3) / 102 (DO1+).',
          'En el banco: puentes 99–101 (DIC a 0V) y 103–101 (DO1− a 0V). La corriente del motor NO pasa por esta tarjeta.']
for i, l in enumerate(conect): texto(c, 12, 47 - 5.0 * i, l, 8.5)
c.showPage()

# ---------------------------------------------------------------- pág. 3: puentes y armado
texto(c, 12, 196, 'Puentes de alambre y orden de armado', 14, True)
y = 186
for k, (n, x1, y1, x2, y2) in enumerate(PUENTES):
    L = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    texto(c, 12, y, f'W{k+1}: red {n}, de ({x1:.1f}; {y1:.1f}) a ({x2:.1f}; {y2:.1f}) mm, {L:.1f} mm de largo · alambre aislado o forrado.', 9.5)
    y -= 6
y -= 4
pasos = ['1. Transferir, atacar con cloruro férrico o persulfato, limpiar el tóner y revisar con lupa: ninguna pista unida.',
         '2. Con el multímetro en continuidad, sin componentes: GND del ESP32 (J1 GND) contra 0V del V20 (J8 pin 92) = ABIERTO.',
         '3. Taladrar (tabla de brocas en la pág. 1). Lijar suave y estañar o barnizar el cobre.',
         '4. Soldar primero los puentes W (W1 queda debajo del ESP32), luego resistencias, Zener (banda hacia R4/J8),',
         '   condensadores, bases para los IC (6N137, 74HC14, LM358, 4 × PC817), borneras y tiras hembra.',
         '5. Insertar los IC con la muesca/punto como en la serigrafía. PC817: OK4 va girado 180° (punto abajo a la derecha).',
         '6. Sin ESP32 ni V20: alimentar J7 con 5 V y 12 V. Medir 5 V en U1 pin 8 y U2 pin 14; 12 V en U3 pin 8.',
         '7. Alimentar J11 con 5 V: medir 5 V en J5 pin 1 y 3,3 V en J2/J3 pin 3V3. USB solo para programar, con J11 desconectado.',
         '8. Poner el ESP32 (USB arriba) y seguir las mediciones de la hoja "Lista de materiales y verificación".']
for l in pasos: texto(c, 12, y, l, 9.5); y -= 6.2
y -= 4
texto(c, 12, y, 'Por qué una cara y con puentes', 11, True); y -= 6.5
for l in ['Se puede hacer en casa con planchado. Los 3 puentes evitan cruces que, sin ellos, obligarían a una tarjeta de dos caras.',
          'La línea de puntos de la serigrafía es la barrera de aislamiento: ninguna pista cruza de un lado al otro.',
          'Todas las tierras del ESP32 están a la izquierda y las del V20 a la derecha; solo los optoacopladores las cruzan.',
          'Si prefieren mandarla a fabricar, el .zip de Gerber sirve para JLCPCB, PCBWay o un taller local (1 capa, 1,6 mm).']:
    texto(c, 12, y, l, 9.5); y -= 6
c.save()
print('pdf ok')
