"""Gráficas de la simulación a partir de resultados/planta.csv, telemetria.csv y alarmas.json."""
import csv, json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R = Path(__file__).resolve().parent / 'resultados'
pl = list(csv.DictReader(open(R / 'planta.csv')))
te = list(csv.DictReader(open(R / 'telemetria.csv')))
al = json.load(open(R / 'alarmas.json'))
t0 = float(pl[0]['t'])
tp = [float(r['t']) for r in pl]
# la telemetría usa el reloj del orquestador; se alinea con el primer dato de la planta
tt = [float(r['t']) for r in te]

plt.rcParams.update({'font.size': 9, 'figure.dpi': 150})
fig, ax = plt.subplots(3, 1, figsize=(11, 7.5), sharex=True, gridspec_kw={'height_ratios': [2, 2, 1]})
ax[0].plot(tp, [float(r['f_hz']) for r in pl], color='#0b7a83', lw=1.4, label='Frecuencia de salida del V20 (modelo)')
ax[0].plot(tt, [float(r['f_apl']) * (1) for r in te], color='#c27a12', lw=1, ls='--', label='Consigna aplicada en AI1 (ESP32)')
ax[0].set_ylabel('f [Hz]'); ax[0].grid(alpha=.3); ax[0].legend(loc='lower left', fontsize=8)
ax[1].plot(tp, [float(r['i_real_a']) for r in pl], color='#888', lw=1.2, label='Corriente real de fase (modelo)')
ax[1].plot(tt, [float(r['corriente']) for r in te], color='#b3261e', lw=1.2, marker='.', ms=3, label='Corriente medida por el ESP32 (ACS712)')
ax[1].set_ylabel('I [A rms]'); ax[1].grid(alpha=.3); ax[1].legend(loc='upper left', fontsize=8)
est = {'DETENIDO': 0, 'MARCHA': 1, 'FALLO': 2}
ax[2].step(tt, [est[r['estado']] for r in te], where='post', color='#14232a', lw=1.2)
ax[2].set_yticks([0, 1, 2]); ax[2].set_yticklabels(['DETENIDO', 'MARCHA', 'FALLO']); ax[2].grid(alpha=.3)
ax[2].set_xlabel('t [s]')
fallas = {'FALLA_V20', 'V20_SIN_MARCHA', 'PERDIDA_CORRIENTE_FASE', 'SOBRECORRIENTE', 'SOBRECARGA_I2T',
          'PERDIDA_COMUNICACION', 'PARADA_EMERGENCIA_APP', 'FALLO_SENSOR_CORRIENTE', 'RETORNO_ALIMENTACION'}
vistos = set()
for t, a in al:
    if a in fallas and a not in vistos:
        vistos.add(a)
        for k in range(3): ax[k].axvline(t, color='#b3261e', lw=.6, alpha=.5)
        ax[0].text(t, 64, a.replace('_', ' ').lower(), rotation=90, fontsize=6.5, va='bottom', ha='right', color='#b3261e')
ax[0].set_ylim(-65, 100)
fig.suptitle('Simulación: firmware real del ESP32 + modelo del V20 y del motor, manejado desde la app', fontsize=10)
fig.tight_layout(); fig.savefig(R / 'grafica_simulacion.png')

# Detalle: arranque, aceleración y paro (primeros eventos de marcha)
ini = next(float(r['t']) for r in te if r['estado'] == 'MARCHA')
fin = ini + 35
fig, ax = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
sel = [(x, r) for x, r in zip(tp, pl) if ini - 2 <= x <= fin]
ax[0].plot([x for x, _ in sel], [float(r['f_hz']) for _, r in sel], color='#0b7a83', label='f del V20')
ax[0].plot([x for x, _ in sel], [float(r['di1']) * 10 for _, r in sel], color='#555', lw=.8, label='DI1 (×10)')
ax[0].set_ylabel('f [Hz]'); ax[0].grid(alpha=.3); ax[0].legend(fontsize=8)
st = [(x, r) for x, r in zip(tt, te) if ini - 2 <= x <= fin]
ax[1].plot([x for x, _ in sel], [float(r['i_real_a']) for _, r in sel], color='#888', label='real')
ax[1].plot([x for x, _ in st], [float(r['corriente']) for _, r in st], 'o-', color='#b3261e', ms=3, label='medida (ESP32)')
ax[1].set_ylabel('I [A]'); ax[1].set_xlabel('t [s]'); ax[1].grid(alpha=.3); ax[1].legend(fontsize=8)
fig.suptitle('Detalle: marcha 0→30 Hz, aceleración a 60 Hz y paro (P1120 = P1121 = 10 s)', fontsize=10)
fig.tight_layout(); fig.savefig(R / 'grafica_detalle_marcha.png')
print('ok')
