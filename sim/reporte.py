"""Arma el reporte de simulación (HTML → PDF) desde resultados/."""
import json, html
from pathlib import Path
from playwright.sync_api import sync_playwright

R = Path(__file__).resolve().parent / 'resultados'
res = json.load(open(R / 'resultados.json'))
ok = sum(r['ok'] for r in res)
filas = '\n'.join(
    f"<tr><td class='c'>{i + 1}</td><td>{html.escape(r['prueba'])}</td><td class='c {'p' if r['ok'] else 'f'}'>{'PASA' if r['ok'] else 'FALLA'}</td><td class='d'>{html.escape(r['detalle'])}</td></tr>"
    for i, r in enumerate(res))

doc = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Reporte de simulación V20 IoT</title>
<style>
@page{{size:Letter;margin:13mm 12mm}}
body{{font:9.5pt/1.4 "DejaVu Sans",Arial,sans-serif;color:#141c20;margin:0}}
h1{{font-size:15pt;margin:0 0 2px}} h2{{font-size:11pt;margin:12px 0 5px;padding:3px 7px;background:#e7eef0;border-left:4px solid #0b7a83}}
p{{margin:3px 0 7px}} .sub{{color:#555;font-size:9pt}}
table{{border-collapse:collapse;width:100%;margin:4px 0}} tr{{break-inside:avoid}}
th,td{{border:1px solid #9aa6aa;padding:3px 5px;font-size:8.4pt;vertical-align:top}} th{{background:#f0f3f4;text-align:left}}
.c{{text-align:center}} .p{{color:#1f6d3d;font-weight:700}} .f{{color:#b3261e;font-weight:700}} .d{{font-family:"DejaVu Sans Mono",monospace;font-size:7.6pt}}
.res{{font-size:13pt;font-weight:700;color:#1f6d3d}}
img{{max-width:100%}} .shots{{display:flex;gap:6px}} .shots img{{width:24%;border:1px solid #ccc}}
.cap{{font-size:8pt;color:#555;text-align:center;margin:2px 0 8px}}
code{{font-family:"DejaVu Sans Mono",monospace;font-size:8.4pt;background:#eef2f3;padding:0 3px}}
ul{{margin:3px 0 7px;padding-left:18px}}
</style></head><body>
<h1>Reporte de simulación · Control IoT del SINAMICS V20</h1>
<div class="sub">Firmware <code>v20_iot_esp32.ino</code> v3.0 · app web <code>app/index.html</code> · Universidad del Magdalena · Electrónica de Potencia</div>

<h2>1. Qué se simuló</h2>
<p>Se ejecutó el <b>código real del firmware</b>, sin modificaciones, compilado para PC. Las funciones de hardware del ESP32 (GPIO, ADC, PWM, Wi-Fi y PubSubClient) se reemplazaron por equivalentes simulados conectados a:</p>
<ul>
<li><b>Modelo del V20:</b> lee la consigna de AI1 (f = 60·D), DI1 marcha, DI2 inversión y DI3 reconocimiento; aplica rampas P1120 = P1121 = 10 s y límites P1080/P1082; entrega DO1 "en marcha" y DO2 "falla".</li>
<li><b>Modelo del motor y del ACS712-30A:</b> corriente de vacío 1,4 A, componente de aceleración proporcional a df/dt, carga ajustable, onda senoidal a la frecuencia de salida, rizado de portadora de 4 kHz y ruido de 10 mV.</li>
<li><b>Broker MQTT 3.1.1</b> local (TCP y WebSocket) en lugar de HiveMQ Cloud.</li>
<li><b>La app web real</b> en Chromium con pantalla de teléfono (412 × 915). La prueba hace clic en los mismos botones que usaría el operador.</li>
</ul>
<p>Además se inyectaron fallas: falla del V20, corte de energía, fase abierta, sobrecorriente, sobrecarga, pérdida de red, orden retenida y sensor desconectado.</p>

<h2>2. Resultado: <span class="res">{ok} de {len(res)} pruebas pasan</span></h2>
<table><tr><th>#</th><th>Prueba</th><th>Resultado</th><th>Evidencia medida en la simulación</th></tr>
{filas}
</table>

<h2>3. Señales registradas</h2>
<img src="grafica_simulacion.png">
<div class="cap">Frecuencia de salida del V20 frente a la consigna aplicada por el ESP32, corriente real frente a la medida y estado de la máquina de estados. Las líneas rojas marcan cada falla inyectada. La consigna se grafica en magnitud: en la marcha atrás el V20 gira a −30 Hz. Durante la prueba de fase abierta, la corriente "real" corresponde a las fases sanas; la fase medida no conduce.</div>
<img src="grafica_detalle_marcha.png" style="width:80%;display:block;margin:0 auto">
<div class="cap">Detalle del primer ciclo. La rampa 0→30 Hz dura 5,0 s, que corresponde a P1120 = 10 s de 0 a 60 Hz. La corriente medida sigue a la real con un retardo de una ventana RMS más el periodo de publicación de 1 s.</div>

<h2>4. La app durante la simulación</h2>
<div class="shots"><img src="app_01_arranque_bloqueado.png"><img src="app_02_marcha_30Hz.png"><img src="app_04_falla_v20.png"><img src="app_05_configuracion.png"></div>
<div class="cap">De izquierda a derecha: arranque bloqueado tras reinicio, marcha a 30 Hz, falla del V20 y límite de 45 Hz con rampa del ESP32.</div>

<h2>5. Alcance y limitaciones</h2>
<ul>
<li>El modelo del V20 es de comportamiento (rampas, DI/DO, escalado de AI1). No reproduce sus protecciones internas, el límite de corriente ni el control V/f; esas variables se miden en el banco con r0021, r0025 y r0027.</li>
<li>El modelo del motor no incluye inercia real ni deslizamiento. Las corrientes son representativas de un motor de 1 HP en vacío, no los valores de placa.</li>
<li>La simulación usa MQTT sin TLS. En el ESP32 real la conexión a HiveMQ va cifrada (puerto 8883) y la app usa WSS (puerto 8884).</li>
<li>Los tiempos del ESP32 real dependen del Wi-Fi. La reconexión TLS puede bloquear el lazo 1–3 s, y durante ese tiempo las salidas mantienen su último valor.</li>
<li>La constante térmica se redujo a 30 s solo en la simulación, para probar el I²t en segundos. El firmware real usa 300 s.</li>
</ul>

<h2>6. Cómo repetirla</h2>
<p>En Linux o WSL: <code>cd sim</code> → <code>./compilar.sh</code> → <code>python3 run_sim.py</code> → <code>python3 graficas.py</code> → <code>python3 reporte.py</code>. Requiere g++, Python 3 con Playwright y matplotlib. La simulación dura unos 4 minutos.</p>
</body></html>"""
(R / 'reporte_simulacion.html').write_text(doc, encoding='utf-8')
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto((R / 'reporte_simulacion.html').as_uri()); pg.wait_for_timeout(500)
    pg.pdf(path=str(R / 'Reporte_Simulacion_V20_IoT.pdf'), format='Letter', print_background=True, prefer_css_page_size=True)
    b.close()
print('ok', ok, len(res))
