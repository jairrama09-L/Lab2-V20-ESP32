from playwright.sync_api import sync_playwright
from pathlib import Path
svg = Path('esquematico_v20_iot.svg').read_text()
bom = [
 ('U1','ESP32 DevKit V1','1','Wi-Fi + MQTT'),
 ('U2','6N137 optoacoplador rápido','1','Consigna PWM 20 kHz'),
 ('U3','74HC14 (Schmitt inversor)','1','Recuadra la señal'),
 ('U4','LM358 amplificador doble','1','Ganancia 2 (0–10 V)'),
 ('U5','ACS712 módulo (5 A recomendado; 20/30 A sirve)','1','Fase U del motor'),
 ('OK1–OK4','PC817 optoacoplador','4','DI1, DI2, DI3 y DO1'),
 ('R1','220 Ω ¼ W','1','LED 6N137'),
 ('R2','1 kΩ ¼ W (1,5 kΩ también sirve)','1','Pull-up VO 6N137'),
 ('R3, Rf, Rg','10 kΩ 1 % ¼ W','3','Filtro RC y ganancia'),
 ('R4','100 Ω ¼ W','1','Protección salida AI1'),
 ('R5–R7','220 Ω ¼ W','3','LED de PC817 #1–#3 (≈9,5 mA)'),
 ('—','2,2 kΩ ½ W','1','LED de PC817 #4 desde 24 V (≈10 mA, 0,23 W)'),
 ('—','10 kΩ ¼ W','6','3 pull-down (GPIO26/27/32), pull-up GPIO35, divisor ACS712'),
 ('—','20 kΩ ¼ W','1','Divisor ACS712 (5 V → 3,3 V)'),
 ('—','1 kΩ ¼ W','1','Serie GPIO33 (DO2)'),
 ('C1','1 µF poliéster/MKT ≥ 25 V','1','Filtro RC fc = 15,9 Hz'),
 ('C2','100 nF cerámico','1','Desacople del 6N137'),
 ('—','22 nF cerámico','1','Filtro portadora en GPIO34'),
 ('DZ','1N4742A Zener 12 V 1 W','1','Protección AI1'),
 ('—','Fuente externa 5 V + 12 V (o 15 V)','1','Etapa V20: (−) al borne 92; sin tierra física'),
 ('J11','Fuente 5 V ≥ 1 A aparte (cargador USB)','1','ESP32 por VIN + ACS712; NO unir al 0V del V20'),
]
filas = ''.join(f'<tr><td>{a}</td><td>{b}</td><td style="text-align:center">{c}</td><td>{d}</td></tr>' for a,b,c,d in bom)
html = f'''<html><head><style>
@page {{ size: 1720px 1120px; margin: 0 }}
body {{ margin:0; font-family: "DejaVu Sans", Arial }}
.p {{ width:1720px; height:1120px; page-break-after: always; overflow:hidden }}
.b {{ padding: 50px 70px; box-sizing: border-box }}
h1 {{ font-size: 26px; margin: 0 0 6px }} h2 {{ font-size: 18px; margin: 26px 0 8px; color:#b8690b }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px }}
td,th {{ border: 1px solid #bbb; padding: 5px 9px; text-align:left }} th {{ background:#f3f3f3 }}
.cols {{ display:grid; grid-template-columns: 1.35fr 1fr; gap: 40px }} li {{ font-size: 14px; margin: 4px 0 }}
</style></head><body>
<div class="p">{svg}</div>
<div class="p b"><h1>Lista de materiales y verificación</h1>
<div style="color:#555">Control IoT del SINAMICS V20 · versión con optoacopladores PC817 · firmware v3.2 (salidas activas en ALTO)</div>
<div class="cols"><div><h2>Materiales</h2><table><tr><th>Ref.</th><th>Componente</th><th>Cant.</th><th>Función</th></tr>{filas}</table></div>
<div><h2>Verificación sin variador (multímetro)</h2><ol>
<li>Sin ESP32: entre 100 y 101 debe haber 24 V (±20 %).</li>
<li>Comando <b>MARCHA</b> en la app: GPIO26 ≈ 3,3 V; entre 95 y 101 ≈ 23 V. Con PARO ≈ 0 V.</li>
<li>Repite con ATRÁS (GPIO27 → 96) y RESET (GPIO32 → 97, pulso de 300 ms).</li>
<li>Reset del ESP32: 95/96/97 deben quedar en 0 V (pull-down 10 kΩ).</li>
<li>Continuidad 0 Ω entre GND ESP32 y 101 = <b>error</b>. Debe ser circuito abierto.</li>
<li>Consigna: con 30 Hz → 5,0 V en 89–92; con 60 Hz → 10,0 V (calibrar P0759 = r0752).</li>
<li>GPIO35 con el motor parado ≈ 3,3 V; en marcha ≈ 0,2 V (DO1 cierra).</li>
<li>GPIO33: falla del V20 → 0 V; normal → 3,3 V.</li>
<li>ACS712 desconectado: el firmware debe ir a FALLO_SENSOR.</li></ol>
<h2>Polaridad PC817</h2><ul>
<li>Pin 1 (punto) = ánodo LED · 2 = cátodo · 3 = emisor · 4 = colector.</li>
<li>Entradas: colector a +24 V (100), emisor al DI. El V20 ve 24 V → entrada activa (PNP, DIC a 0V).</li>
<li>DO1 es polarizado: + en 102, − en 103. Si se invierte, nunca conduce.</li></ul>
<h2>Parámetros del V20</h2><ul><li>P0700=2 · P1000=2 · P0701=1 · P0702=12 · P0703=9</li>
<li>P0731=52.2 · P0732=52.3 · P1120=P1121=10 s · P0759 = r0752 a 60 Hz</li></ul></div></div></div>
</body></html>'''
Path('_tmp.html').write_text(html)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width':1720,'height':1120}, device_scale_factor=2)
    pg.set_content(f'<html><body style="margin:0">{svg}</body></html>')
    pg.screenshot(path='esquematico_v20_iot.png', full_page=True)
    pg.goto('file://' + str(Path('_tmp.html').resolve()))
    pg.pdf(path='Esquematico_V20_IoT_PC817.pdf', width='1720px', height='1120px', print_background=True)
    b.close()
Path('_tmp.html').unlink()
print('ok')
