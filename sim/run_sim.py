"""
Simulación completa del sistema V20 IoT:
  firmware real del ESP32 (compilado para PC)  ⇄  broker MQTT  ⇄  app web (Chromium)
  + modelo del V20 y del motor (planta.cpp)
La prueba maneja la app con clics como lo haría un usuario, inyecta fallas en la
planta y verifica la respuesta del firmware. Genera resultados/ con el informe.

Uso:  python3 run_sim.py
"""
import json, os, subprocess, sys, threading, time
from pathlib import Path
from broker import Broker, Cliente

AQUI = Path(__file__).resolve().parent
RES = AQUI / 'resultados'; RES.mkdir(exist_ok=True)
APP = AQUI.parent / 'app' / 'index.html'
PREF = 'lab/v20'
T0 = time.time()

# ------------------------------------------------------------------ broker
broker = Broker()
broker.iniciar(1883, 9001, archivo_app=str(APP))
trafico, tele = [], {}
alarmas = []

def observar(t, p, r):
    trafico.append((round(time.time() - T0, 2), t, p, r))
    if t == PREF + '/telemetria':
        try: tele.update(json.loads(p)); tele['_t'] = time.time()
        except Exception: pass
    if t in (PREF + '/alarma', PREF + '/aviso'):
        alarmas.append((round(time.time() - T0, 2), p))
broker.observadores.append(observar)

# ------------------------------------------------------------------ firmware
fw = subprocess.Popen([str(AQUI / 'build' / 'esp32_sim')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
lock = threading.Lock()
def escribir(l):
    with lock:
        fw.stdin.write(l + '\n'); fw.stdin.flush()

class Puente(Cliente):
    def entregar(self, topico, payload, retain=False):
        escribir(f'MSG {topico} {payload}')
puente = Puente(broker, None)

logs, csv = [], []
def lector():
    for l in fw.stdout:
        l = l.rstrip('\n'); t = round(time.time() - T0, 2)
        if l.startswith('CSV '): csv.append([float(x) for x in l[4:].split(',')])
        elif l.startswith('LOG '): logs.append((t, l[4:]))
        elif l.startswith('PUB '):
            _, r, top, *pl = l.split(' ', 3)
            broker.en_hilo(broker.publicar, top, pl[0] if pl else '', r == '1')
        elif l.startswith('SUB '):
            broker.en_hilo(broker.suscribir, puente, l[4:])
        elif l.startswith('CON '):
            _, cid, wt, wm = l.split(' ', 3)
            puente.subs = []; puente.will = (wt, wm, True)
            broker.en_hilo(broker.clientes.add, puente)
threading.Thread(target=lector, daemon=True).start()

def planta(o): escribir('PLANTA ' + o)
def red(on):
    escribir('NET ' + ('1' if on else '0'))
    if not on: broker.en_hilo(broker.desconectar, puente)
def ult_csv(): return csv[-1] if csv else None   # t,duty,di1,di2,di3,f,i,marcha,falla,red,fase
def esperar(cond, timeout, paso=0.1):
    fin = time.time() + timeout
    while time.time() < fin:
        try:
            if cond(): return True
        except Exception: pass
        time.sleep(paso)
    return False

# ------------------------------------------------------------------ pruebas
resultados = []
def verificar(nombre, ok, detalle=''):
    resultados.append({'t': round(time.time() - T0, 1), 'prueba': nombre, 'ok': bool(ok), 'detalle': detalle})
    print(('PASA ' if ok else 'FALLA') + f' | {nombre} | {detalle}', flush=True)

from playwright.sync_api import sync_playwright
try:
  with sync_playwright() as pw:
      nav = pw.chromium.launch()
      pg = nav.new_page(viewport={'width': 412, 'height': 915}, device_scale_factor=2)
      pg.goto(f'http://127.0.0.1:9001/?host=127.0.0.1&port=9001&path=/&tls=0&pref={PREF}&user=app&pass=x')
      def foto(n, completa=False):
        pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(300)
        pg.screenshot(path=str(RES / f'app_{n}.png'), full_page=completa)
      def clic(sel): pg.click(sel)
      def rapido(f): pg.click(f'#quick button[data-f="{f}"]')
      def estado(): return tele.get('estado')
      def alarma(): return tele.get('alarma')
      def ultima_alarma(): return alarmas[-1][1] if alarmas else ''

      # 1. Arranque
      ok = esperar(lambda: 'conectado' in pg.inner_text('#chipBroker') and tele.get('estado'), 15)
      verificar('App conectada al broker y recibiendo telemetría', ok, pg.inner_text('#chipBroker'))
      esperar(lambda: tele.get('ruido_a', 0) > 0, 5)
      verificar('Arranque tras reinicio queda en FALLO (bloqueo)', estado() == 'FALLO' and alarma() == 'RETORNO_ALIMENTACION',
                f"estado={estado()} alarma={alarma()} DI1={tele.get('di1')} AI1={tele.get('v_ai1')} V")
      verificar('ACS712 calibrado al arrancar', tele.get('sensor_ok') == 1 and tele.get('ruido_a', 9) < 0.15,
                f"ruido equivalente={tele.get('ruido_a')} A, sensor_ok={tele.get('sensor_ok')}")
      pg.wait_for_timeout(2500); foto('01_arranque_bloqueado')

      # 2. Reset y configuración
      clic('#bReset'); ok = esperar(lambda: estado() == 'DETENIDO', 4)
      verificar('RESET desde la app rearma (pulso DI3)', ok, f'estado={estado()}')
      pg.fill('#cIn', '3.0'); clic('#bConfig')
      verificar('Configuración In = 3,0 A aplicada', esperar(lambda: abs(tele.get('in_a', 0) - 3.0) < 1e-6, 3), f"in_a={tele.get('in_a')}")

      # 3. Consigna y marcha
      rapido(30)
      verificar('Consigna 30 Hz → AI1 = 5,0 V', esperar(lambda: abs(tele.get('v_ai1', 0) - 5.0) < 0.02, 3), f"v_ai1={tele.get('v_ai1')} V, duty={tele.get('duty')}")
      clic('#bStart')
      verificar('MARCHA desde la app → DI1 activo y V20 en marcha', esperar(lambda: ult_csv()[2] == 1 and tele.get('v20_marcha') == 1, 3),
                f"DI1={ult_csv()[2]}, v20_marcha={tele.get('v20_marcha')}")
      esperar(lambda: abs(ult_csv()[5] - 30) < 0.05, 8)
      fil = [r for r in csv if r[0] > csv[-1][0] - 15]
      t_on = next(r[0] for r in fil if r[2] == 1); t_30 = next(r[0] for r in fil if r[0] > t_on and abs(r[5] - 30) < 0.05)
      verificar('Rampa del V20 0→30 Hz en ≈ 5 s (P1120 = 10 s)', 4.7 < t_30 - t_on < 5.3, f'DI1↑ → 30 Hz: {t_30 - t_on:.2f} s (teórico 5,00 s)')
      time.sleep(3)
      i_real, i_med = ult_csv()[6], tele.get('corriente')
      verificar('Corriente medida ≈ real a 30 Hz (error < 5 %)', abs(i_med - i_real) / i_real < 0.05, f'real={i_real:.3f} A, medida={i_med:.3f} A')
      foto('02_marcha_30Hz')

      # 4. Aceleración a 60 Hz
      rapido(60); picos = []
      fin = time.time() + 8
      while time.time() < fin: picos.append(tele.get('corriente', 0)); time.sleep(0.25)
      verificar('Corriente sube durante la aceleración y vuelve a vacío', max(picos) > 1.55 and abs(tele.get('corriente') - 1.4) < 0.1,
                f'pico medido={max(picos):.2f} A, final={tele.get("corriente"):.2f} A')
      verificar('V20 llega a 60 Hz', abs(ult_csv()[5] - 60) < 0.1, f'f={ult_csv()[5]:.2f} Hz')

      # 5. Inversión en marcha (debe rechazarse)
      clic('#bRev'); esperar(lambda: ultima_alarma() == 'SENTIDO_RECHAZADO_EN_MARCHA', 3)
      verificar('Inversión rechazada con el motor en marcha', ultima_alarma() == 'SENTIDO_RECHAZADO_EN_MARCHA' and ult_csv()[3] == 0,
                f'alarma={ultima_alarma()}, DI2={ult_csv()[3]}')

      # 6. Paro con rampa
      clic('#bStop'); t_p = time.time()
      ok = esperar(lambda: tele.get('v20_marcha') == 0 and ult_csv()[5] == 0, 15)
      verificar('PARO → DI1 abierto y el V20 desacelera hasta 0 Hz (≈ 10 s)', ok and 9 < time.time() - t_p < 11.5, f'{time.time() - t_p:.1f} s')

      # 7. Inversión con el motor parado y marcha atrás
      clic('#bRev'); rapido(30); time.sleep(0.5); clic('#bStart')
      esperar(lambda: ult_csv()[5] < -29.9, 9); time.sleep(2)
      verificar('Marcha atrás: DI2 activo y frecuencia negativa', ult_csv()[3] == 1 and ult_csv()[5] < -29.9, f'DI2={ult_csv()[3]}, f={ult_csv()[5]:.1f} Hz')
      foto('03_marcha_atras')
      clic('#bStop'); esperar(lambda: tele.get('v20_marcha') == 0, 12); clic('#bFwd'); time.sleep(1)

      # 8. Falla del V20 y reconocimiento por DI3
      clic('#bStart'); esperar(lambda: abs(ult_csv()[5] - 30) < 0.1, 8)
      planta('FALLA'); ok = esperar(lambda: estado() == 'FALLO' and alarma() == 'FALLA_V20', 3)
      verificar('Falla del V20 (DO2) → FALLO, DI1 abierto, AI1 = 0', ok and ult_csv()[2] == 0 and ult_csv()[1] == 0, f'alarma={alarma()}')
      pg.wait_for_timeout(1200); foto('04_falla_v20')
      clic('#bReset'); ok = esperar(lambda: estado() == 'DETENIDO', 4)
      verificar('RESET reconoce la falla del V20 con pulso en DI3', ok and ult_csv()[8] == 0, f'estado={estado()}, falla_v20={ult_csv()[8]}')

      # 9. Corte de red al V20 en marcha
      clic('#bStart'); esperar(lambda: abs(ult_csv()[5] - 30) < 0.1, 8)
      planta('RED 0'); t_c = time.time(); ok = esperar(lambda: alarma() == 'V20_SIN_MARCHA', 5)
      verificar('Corte de energía del V20 → FALLO "V20_SIN_MARCHA"', ok, f'{time.time() - t_c:.1f} s tras el corte')
      planta('RED 1'); time.sleep(1); esperar(lambda: ult_csv()[5] == 0, 12)
      clic('#bReset'); esperar(lambda: estado() == 'DETENIDO', 4)

      # 10. Fase abierta (el V20 sigue en marcha pero no circula corriente)
      clic('#bStart'); esperar(lambda: abs(ult_csv()[5] - 30) < 0.1, 8); time.sleep(2)
      planta('FASE_ABIERTA 1'); t_f = time.time(); ok = esperar(lambda: alarma() == 'PERDIDA_CORRIENTE_FASE', 6)
      verificar('Fase abierta → FALLO "PERDIDA_CORRIENTE_FASE"', ok, f'{time.time() - t_f:.1f} s tras abrir la fase')
      planta('FASE_ABIERTA 0'); esperar(lambda: tele.get('v20_marcha') == 0, 12)
      clic('#bReset'); esperar(lambda: estado() == 'DETENIDO', 4)

      # 11. Sobrecorriente
      pg.fill('#cIn', '1.0'); clic('#bConfig'); esperar(lambda: tele.get('in_a') == 1.0, 3)
      clic('#bStart'); esperar(lambda: abs(ult_csv()[5] - 30) < 0.1, 8)
      planta('CARGA 2.2'); t_s = time.time(); i_ant = []
      ok = esperar(lambda: (i_ant.append(tele.get('corriente')) or True) and alarma() == 'SOBRECORRIENTE', 5)
      verificar('Sobrecorriente > 2,5·In → FALLO "SOBRECORRIENTE"', ok, f'{time.time() - t_s:.1f} s; I medida antes del disparo={max(i_ant):.2f} A (límite 2,50 A)')
      planta('CARGA 0'); esperar(lambda: tele.get('v20_marcha') == 0, 12)
      clic('#bReset'); ok = esperar(lambda: ultima_alarma() == 'RESET_RECHAZADO_TERMICO' or estado() == 'DETENIDO', 3)
      if estado() != 'DETENIDO':
          esperar(lambda: tele.get('theta', 9) < 0.6, 40); clic('#bReset'); esperar(lambda: estado() == 'DETENIDO', 4)

      # 12. Imagen térmica I²t (τ = 30 s en la simulación)
      clic('#bStart'); t_i = time.time()
      ok_adv = esperar(lambda: ultima_alarma() == 'ADVERTENCIA_TERMICA', 40)
      ok = esperar(lambda: alarma() == 'SOBRECARGA_I2T', 40)
      verificar('Sobrecarga sostenida 1,4·In → advertencia y disparo I²t', ok_adv and ok, f'disparo a los {time.time() - t_i:.0f} s; θ={tele.get("theta")}')
      esperar(lambda: tele.get('v20_marcha') == 0, 12)
      clic('#bReset'); esperar(lambda: ultima_alarma() == 'RESET_RECHAZADO_TERMICO', 3)
      verificar('Memoria térmica: RESET rechazado mientras θ > 0,6', ultima_alarma() == 'RESET_RECHAZADO_TERMICO', ultima_alarma())
      esperar(lambda: tele.get('theta', 9) < 0.6, 45); clic('#bReset'); esperar(lambda: estado() == 'DETENIDO', 4)
      pg.fill('#cIn', '3.0'); clic('#bConfig'); esperar(lambda: tele.get('in_a') == 3.0, 3)

      # 13. Pérdida de comunicación en marcha remota
      clic('#bStart'); esperar(lambda: abs(ult_csv()[5] - 30) < 0.1, 8)
      red(False); t_r = time.time()
      esperar(lambda: 'fuera de línea' in pg.inner_text('#chipEsp'), 4)
      verificar('La app detecta el ESP32 fuera de línea (testamento MQTT)', 'fuera de línea' in pg.inner_text('#chipEsp'), pg.inner_text('#chipEsp'))
      ok = esperar(lambda: ult_csv()[2] == 0, 13)
      verificar('Sin red 10 s en marcha remota → paro por failsafe', ok and 9.5 < time.time() - t_r < 11.5, f'DI1 abierto a los {time.time() - t_r:.1f} s')
      red(True); ok = esperar(lambda: estado() == 'FALLO' and alarma() == 'PERDIDA_COMUNICACION', 8)
      verificar('Al reconectar informa "PERDIDA_COMUNICACION"', ok, f'estado={estado()} alarma={alarma()}')
      esperar(lambda: tele.get('v20_marcha') == 0, 12); time.sleep(3.5)
      clic('#bReset'); esperar(lambda: estado() == 'DETENIDO', 4)
      # Orden START retenida mientras el ESP32 está desconectado: no debe arrancar al volver
      red(False); time.sleep(1)
      broker.en_hilo(broker.publicar, PREF + '/cmd', 'START', True)
      red(True); esperar(lambda: estado() == 'DETENIDO' and time.time() - tele.get('_t', 0) < 1.5, 10); time.sleep(4)
      verificar('Orden START retenida ignorada al reconectar (en DETENIDO)', ult_csv()[2] == 0 and estado() == 'DETENIDO', f'DI1={ult_csv()[2]}, estado={estado()}')
      broker.en_hilo(broker.publicar, PREF + '/cmd', '', True)

      # 14. Emergencia desde la app
      clic('#bStart'); esperar(lambda: abs(ult_csv()[5] - 30) < 0.1, 8)
      clic('#bEmerg'); t_e = time.time(); ok = esperar(lambda: ult_csv()[2] == 0 and ult_csv()[1] == 0, 2, 0.02)
      dt_e = (time.time() - t_e) * 1000; esperar(lambda: alarma() == 'PARADA_EMERGENCIA_APP', 3)
      verificar('EMERGENCIA → DI1 abierto y AI1 = 0', ok and alarma() == 'PARADA_EMERGENCIA_APP', f'{dt_e:.0f} ms desde el clic; alarma={alarma()}')
      esperar(lambda: tele.get('v20_marcha') == 0, 12); clic('#bReset'); esperar(lambda: estado() == 'DETENIDO', 4)

      # 15. Sensor desconectado en marcha
      clic('#bStart'); esperar(lambda: abs(ult_csv()[5] - 30) < 0.1, 8)
      planta('SENSOR 0'); ok = esperar(lambda: alarma() == 'FALLO_SENSOR_CORRIENTE', 4)
      verificar('ACS712 desconectado en marcha → FALLO y lectura 0 A', ok and tele.get('corriente') == 0, f'alarma={alarma()}, I={tele.get("corriente")}')
      esperar(lambda: tele.get('v20_marcha') == 0, 12); clic('#bReset'); esperar(lambda: estado() == 'DETENIDO', 4)
      clic('#bStart'); esperar(lambda: ultima_alarma() == 'MARCHA_RECHAZADA_SENSOR', 3)
      verificar('MARCHA rechazada con el sensor en falla', ult_csv()[2] == 0 and ultima_alarma() == 'MARCHA_RECHAZADA_SENSOR', f'última alarma={ultima_alarma()}')
      planta('SENSOR 1'); ok = esperar(lambda: tele.get('sensor_ok') == 1, 4)
      verificar('Sensor reconectado se recupera solo', ok, f"sensor_ok={tele.get('sensor_ok')}")

      # 16. Límites y rampa propia del ESP32
      pg.fill('#cFmax', '45'); pg.fill('#cRampa', '10'); clic('#bConfig'); time.sleep(1); rapido(60)
      esperar(lambda: tele.get('f_apl', 0) >= 44.9, 12)
      verificar('Límite fmax = 45 Hz y rampa ESP32 de 10 s', abs(tele.get('f_apl') - 45) < 0.1, f"f_cons={tele.get('f_cons')} → f_apl={tele.get('f_apl')}")
      foto('05_configuracion')
      pg.fill('#cFmax', '60'); pg.fill('#cRampa', '0'); clic('#bConfig'); rapido(0); time.sleep(2)

      foto('06_final', completa=True)
      nav.close()

except Exception:
  import traceback; traceback.print_exc()
escribir('SALIR')
time.sleep(0.5)

# ------------------------------------------------------------------ guardar
(RES / 'resultados.json').write_text(json.dumps(resultados, ensure_ascii=False, indent=1))
(RES / 'firmware_log.txt').write_text('\n'.join(f'{t:8.2f}  {l}' for t, l in logs))
(RES / 'mqtt_trafico.txt').write_text('\n'.join(f'{t:8.2f}  {"R" if r else " "} {top}  {p}' for t, top, p, r in trafico if not top.endswith('telemetria')))
with open(RES / 'planta.csv', 'w') as f:
    f.write('t,duty,di1,di2,di3,f_hz,i_real_a,v20_marcha,v20_falla,red,fase_abierta\n')
    for r in csv: f.write(','.join(str(x) for x in r) + '\n')
tel = [(t, json.loads(p)) for t, top, p, r in trafico if top.endswith('telemetria')]
with open(RES / 'telemetria.csv', 'w') as f:
    f.write('t,estado,f_cons,f_apl,corriente,theta,v20_marcha,v20_falla,di1\n')
    for t, j in tel: f.write(f"{t},{j['estado']},{j['f_cons']},{j['f_apl']},{j['corriente']},{j['theta']},{j['v20_marcha']},{j['v20_falla']},{j['di1']}\n")
(RES / 'alarmas.json').write_text(json.dumps(alarmas, ensure_ascii=False))
n_ok = sum(r['ok'] for r in resultados)
print(f'\nRESULTADO: {n_ok}/{len(resultados)} pruebas pasan')
