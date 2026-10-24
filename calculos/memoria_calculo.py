"""
Memoria de cálculo — Laboratorio 2 Electrónica de Potencia (V20 + ESP32)
Acondicionador: ESP32 PWM -> 6N137 -> 74HC14 -> RC -> LM358 (x2) -> 100 ohm -> AI1

Ejecutar:  python3 memoria_calculo.py
Genera: resultados en consola + figuras en ../figuras/
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

FIG = Path(__file__).resolve().parent.parent / "docs" / "figuras"
FIG.mkdir(exist_ok=True)

# ---------------- Datos de diseño (guía) ----------------
R, C = 10e3, 1e-6
Rf = Rg = 10e3
VH = 5.0
F_PWM = 20e3
N = 10
F_REF = 60.0          # P2000
tau = R * C
T = 1 / F_PWM
G = 1 + Rf / Rg
V_FS = G * VH         # 10 V
KHZ = F_REF / V_FS    # Hz por voltio en AI1 (6 Hz/V)

def linea(t=""):
    print("\n" + "=" * 70 + (f"\n{t}\n" + "=" * 70 if t else ""))

linea("1. FILTRO RC")
fc = 1 / (2 * np.pi * tau)
H20k = 1 / np.sqrt(1 + (F_PWM / fc) ** 2)
print(f"tau = RC            = {tau*1e3:.1f} ms")
print(f"fc = 1/(2 pi RC)    = {fc:.2f} Hz")
print(f"|H(20 kHz)|         = {H20k:.3e}  ({20*np.log10(H20k):.1f} dB)")
print(f"ts (5 tau)          = {5*tau*1e3:.0f} ms ;  ts al 1 % (4.6 tau) = {4.6*tau*1e3:.0f} ms")

linea("2. RIZADO (aprox. lineal de la guía vs. solución exponencial exacta)")
def rizado_aprox(D):
    return VH * D * (1 - D) / (R * C * F_PWM)
def rizado_exacto(D):
    a = np.exp(-D * T / tau); b = np.exp(-(1 - D) * T / tau); c = np.exp(-T / tau)
    return VH * (1 - a) * (1 - b) / (1 - c)
for D in (0.1, 0.25, 0.5, 0.75, 0.9):
    ra, re = rizado_aprox(D), rizado_exacto(D)
    print(f"D={D:4.2f}: filtro {ra*1e3:6.3f} mVpp (aprox) | {re*1e3:6.3f} mVpp (exacto)"
          f" -> AI1 {G*re*1e3:6.2f} mVpp = {G*re*KHZ*1e3:5.1f} mHz")

linea("3. RESOLUCIÓN")
for n in (8, 10, 12):
    dv = V_FS / (2 ** n - 1)
    print(f"{n:2d} bits: dV = {dv*1e3:6.2f} mV -> df = {dv*KHZ:.4f} Hz")
print("ADC del V20 = 10 bits (manual). Si cubre 0..10 V: 9.8 mV (0.059 Hz);")
print("si su rango interno es +/-10 V: 19.6 mV (0.117 Hz) -> el ADC limitaría, no el PWM.")

linea("4. ENTRADA 6N137 (LED) desde GPIO 3.3 V con 220 ohm")
for vgpio in (3.3, 3.0, 2.64):
    for vf in (1.38, 1.70):
        i = (vgpio - vf) / 220
        print(f"V_GPIO={vgpio:4.2f} V, VF={vf:4.2f} V -> IF = {i*1e3:5.2f} mA "
              f"{'OK (>5 mA umbral max)' if i > 5e-3 else 'MARGEN BAJO'}")

linea("5. SALIDA 6N137 con pull-up 1 kohm a 5 V")
print(f"I_OL = (5-0.4)/1k = {(5-0.4)/1e3*1e3:.1f} mA  (máx. prueba 13 mA; RL rec. 330..4k) OK")
print(f"tau_subida ~ 1k*25pF = {1e3*25e-12*1e9:.0f} ns << T = {T*1e6:.0f} us")
for pwd in (10e-9, 40e-9, 90e-9):
    e = pwd / T
    print(f"Distorsión de ancho {pwd*1e9:3.0f} ns -> error de D = {e*100:.3f} % -> {e*F_REF*1e3:.0f} mHz")

linea("6. TOLERANCIAS -> FONDO DE ESCALA (D=100 %)")
vh_min, vh_max = 4.75, 5.25           # 78L05 +/-5 %
g_min = 1 + 0.99 * Rf / (1.01 * Rg); g_max = 1 + 1.01 * Rf / (0.99 * Rg)
vfs_min, vfs_max = vh_min * g_min, vh_max * g_max
print(f"Ganancia con R 1 %: {g_min:.4f} .. {g_max:.4f}")
print(f"V_FS: {vfs_min:.2f} V .. {vfs_max:.2f} V")
print(f"Sin calibrar P0759 (=10 V): f_max = {F_REF*vfs_min/10:.1f} .. {F_REF*vfs_max/10:.1f} Hz "
      f"(error {100*(vfs_min/10-1):+.1f} % .. {100*(vfs_max/10-1):+.1f} %)")
print("Ejemplo de la guía: r0752=9.62 V -> 57.7 Hz (-3.8 %)")
print("Ojo: si V_FS > 10 V la consigna de 60 Hz se alcanza antes de D=100 % (o AI1 satura).")
print("Offset LM358 (2 mV typ, 7 mV max) x2 -> " f"{2*2e-3*KHZ*1e3:.0f}..{2*7e-3*KHZ*1e3:.0f} mHz")
print(f"Carga AI1 (>30 kohm) con 100 ohm serie -> error <= {100*100/30100:.2f} % (lo absorbe P0759, r0752 mide en el borne)")
print("Precisión del ADC del V20: +/-5 % de fondo de escala (manual) -> por eso se calibra con r0752.")

linea("7. PROTECCIÓN ZENER 1N4742A (12 V +/-5 %) tras 100 ohm")
vomax = 13.5
for vz in (11.4, 12.0, 12.6):
    iz = (vomax - vz) / 100
    print(f"Vz={vz:4.1f} V: Iz = {iz*1e3:5.1f} mA, Pz = {vz*iz*1e3:5.0f} mW (1 W) ; LM358 Isc ~40 mA OK")
print("Fuga IR ~5 uA @ 9.1 V -> caída en 100 ohm = 0.5 mV (despreciable)")

linea("8. ALIMENTACIÓN DESDE 24 V DEL V20 (-15 %/+20 % -> 20.4..28.8 V; máx 50 mA)")
cargas = {"6N137 ICC": 10e-3, "pull-up 1k (prom D=0.5)": 2.3e-3, "74HC14": 0.5e-3,
          "LM358 Icc": 1.2e-3, "realim. 20k a 10 V": 0.5e-3, "AI1 (30k)": 0.33e-3}
itot = sum(cargas.values())
for k, v in cargas.items():
    print(f"  {k:28s} {v*1e3:5.2f} mA")
print(f"  TOTAL ~ {itot*1e3:.1f} mA  ({100*itot/50e-3:.0f} % de 50 mA)")
i5 = cargas["6N137 ICC"] + cargas["pull-up 1k (prom D=0.5)"] + cargas["74HC14"]
for vin in (20.4, 24, 28.8):
    print(f"  Vin={vin:4.1f} V: P_78L15 = {(vin-15)*itot*1e3:4.0f} mW ; P_78L05 = {(15-5)*i5*1e3:4.0f} mW (TO-92 ~600 mW)")
print("  Dropout 78L15 ~1.7 V -> requiere Vin >= 16.7 V; mínimo garantizado 20.4 V OK")

linea("9. MOTOR Y V/f")
p = 2
ns = 120 * 60 / p
print(f"Motor 2 polos: ns(60 Hz) = {ns:.0f} rpm ; pendiente V/f = 220/60 = {220/60:.3f} V/Hz")
for f in (10, 20, 30, 40, 50, 60):
    print(f"  {f:2d} Hz: V_lineal = {220*f/60:6.1f} V ; V_cuad (sin boost) = {220*(f/60)**2:6.1f} V ; ns = {120*f/p:5.0f} rpm")
print("Rampa: P1120 se mide de 0 a P1082 -> hacer la Tabla 2 con P1082 = 60 Hz")
for tr in (5, 10, 20):
    print(f"  P1120={tr:2d} s: dw/dt = {2*np.pi*ns/60/tr:6.1f} rad/s^2 -> T_acel = J*{2*np.pi*ns/60/tr:.1f}")

# ---------------- FIGURAS ----------------
plt.rcParams.update({"font.size": 9, "figure.dpi": 150})

# Fig 1: rizado en régimen permanente D=0.5 (simulación exacta por tramos)
D = 0.5; nper = 4
t, v = [], []
v0 = VH * D - rizado_exacto(D) / 2  # valor mínimo en régimen
vv = v0
for k in range(nper):
    th = np.linspace(0, D * T, 50); vh = VH + (vv - VH) * np.exp(-th / tau)
    t += list(k * T + th); v += list(vh); vv = vh[-1]
    tl = np.linspace(0, (1 - D) * T, 50); vl = vv * np.exp(-tl / tau)
    t += list(k * T + D * T + tl); v += list(vl); vv = vl[-1]
t = np.array(t); v = np.array(v) * G
fig, ax = plt.subplots(figsize=(4.2, 2.6))
ax.plot(t * 1e6, (v - 5) * 1e3)
ax.set_xlabel("t [µs]"); ax.set_ylabel("V_AI1 − 5 V [mV]")
ax.set_title(f"Rizado en AI1, D = 0.5: {np.ptp(v)*1e3:.1f} mVpp")
ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(FIG / "fig_rizado_D05.png")

# Fig 2: rizado vs D
Ds = np.linspace(0, 1, 201)
fig, ax = plt.subplots(figsize=(4.2, 2.6))
ax.plot(Ds * 100, G * rizado_exacto(Ds) * 1e3, label="exacto")
ax.plot(Ds * 100, G * rizado_aprox(Ds) * 1e3, "--", label="aprox. guía")
ax.set_xlabel("D [%]"); ax.set_ylabel("ΔV_AI1 [mVpp]"); ax.legend(); ax.grid(alpha=.3)
ax2 = ax.secondary_yaxis("right", functions=(lambda x: x * KHZ, lambda y: y / KHZ)); ax2.set_ylabel("Δf [mHz]")
ax.set_title("Rizado en AI1 vs ciclo de trabajo"); fig.tight_layout(); fig.savefig(FIG / "fig_rizado_vs_D.png")

# Fig 3: respuesta al escalón 0 -> 60 Hz (envolvente) vs rampa de 10 s
ts_ = np.linspace(0, 0.15, 500)
fig, ax = plt.subplots(figsize=(4.2, 2.6))
ax.plot(ts_ * 1e3, V_FS * (1 - np.exp(-ts_ / tau)), label="τ = 10 ms (diseño)")
ax.plot(ts_ * 1e3, V_FS * (1 - np.exp(-ts_ / 1.0)), label="τ = 1 s")
ax.axhline(0.99 * V_FS, ls=":", c="k", lw=.8)
ax.set_xlabel("t [ms]"); ax.set_ylabel("V_AI1 [V]"); ax.legend(); ax.grid(alpha=.3)
ax.set_title("Escalón de consigna 0 → 10 V"); fig.tight_layout(); fig.savefig(FIG / "fig_escalon.png")

# Fig 4: curvas V/f teóricas
fs = np.linspace(0, 60, 121)
fig, ax = plt.subplots(figsize=(4.2, 2.6))
ax.plot(fs, 220 * fs / 60, label="lineal 3.67 V/Hz")
ax.plot(fs, 220 * (fs / 60) ** 2, label="cuadrática")
vb = 0.1 * 220  # ejemplo de refuerzo 10 %
ax.plot(fs, vb + (220 - vb) * fs / 60, label="lineal + boost (ej.)")
ax.set_xlabel("f [Hz]"); ax.set_ylabel("V salida [V]"); ax.legend(); ax.grid(alpha=.3)
ax.set_title("Características V/f teóricas"); fig.tight_layout(); fig.savefig(FIG / "fig_vf_teoricas.png")

print(f"\nFiguras guardadas en {FIG}")
