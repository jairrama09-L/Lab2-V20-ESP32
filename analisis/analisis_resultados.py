"""
Análisis de resultados — Laboratorio 2 (V20 + ESP32)

1. Llene datos_lab2.csv con lo medido (deje vacío lo que no midió).
   T1: consigna, multímetro, r0752, r0021, rpm y, si lo anotó, r0021 ANTES de calibrar P0759.
   T2: P1120, tiempo medido y corriente máxima (r0027).
   T3: r0025 en lineal, cuadrática y lineal con refuerzo.
2. Ejecute:  python3 analisis_resultados.py
   Genera ../figuras/res_*.png y resumen_resultados.txt con los números para el informe.
"""
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = Path(__file__).resolve().parent
FIG = AQUI.parent / "docs" / "figuras"; FIG.mkdir(parents=True, exist_ok=True)
POLOS = 2
plt.rcParams.update({"font.family": "serif", "font.size": 9, "figure.dpi": 200})

def num(x):
    try: return float(x.replace(",", "."))
    except (ValueError, AttributeError): return np.nan

filas = {"T1": [], "T2": [], "T3": []}
with open(AQUI / "datos_lab2.csv", newline="", encoding="utf-8") as f:
    for r in csv.reader(f):
        if r and r[0] in filas:
            filas[r[0]].append([num(c) for c in r[1:]])
T1, T2, T3 = (np.array(filas[k], dtype=float) for k in ("T1", "T2", "T3"))
out = []

# ---------- Tabla 1 ----------
fc, vm, r752, r21, rpm, r21sc = T1.T[:6]
ns = 120 * fc / POLOS
with np.errstate(invalid="ignore", divide="ignore"):
    s = np.where(ns > 0, (ns - rpm) / ns * 100, np.nan)
    e_cal = (r21 - fc) / 60 * 100
    e_sin = (r21sc - fc) / 60 * 100
    e_v = (vm - fc / 6) / 10 * 100
out.append("TABLA 1 — linealidad")
out.append(" f[Hz]  V_mult  r0752  r0021  rpm    ns     s[%]   e_cal[%FS] e_sin[%FS]")
for i in range(len(fc)):
    out.append(f" {fc[i]:5.0f}  {vm[i]:6.3f} {r752[i]:6.3f} {r21[i]:6.2f} {rpm[i]:6.0f} {ns[i]:6.0f} {s[i]:6.2f}  {e_cal[i]:8.3f}  {e_sin[i]:8.3f}")
if np.isfinite(e_cal).any(): out.append(f"Error máximo DESPUÉS de calibrar: {np.nanmax(abs(e_cal)):.3f} % del fondo de escala")
if np.isfinite(e_sin).any(): out.append(f"Error máximo ANTES de calibrar:   {np.nanmax(abs(e_sin)):.3f} % del fondo de escala")
if np.isfinite(e_v).any():   out.append(f"Error máximo de tensión (multímetro vs 10·D): {np.nanmax(abs(e_v)):.3f} % FS")
ok = np.isfinite(fc) & np.isfinite(r21)
if ok.sum() >= 2:
    m, b = np.polyfit(fc[ok], r21[ok], 1)
    res = r21[ok] - (m * fc[ok] + b)
    out.append(f"Ajuste r0021 = {m:.4f}·f + {b:.3f} Hz ; no linealidad máx. = {np.max(abs(res))/60*100:.3f} % FS")

fig, ax = plt.subplots(figsize=(3.4, 2.4))
ax.plot([0, 60], [0, 60], "k:", lw=.8, label="ideal")
if np.isfinite(r21sc).any(): ax.plot(fc, r21sc, "s--", ms=4, label="antes de calibrar")
if np.isfinite(r21).any():   ax.plot(fc, r21, "o-", ms=4, label="después de calibrar")
ax.set_xlabel("Consigna [Hz]"); ax.set_ylabel("r0021 [Hz]"); ax.grid(alpha=.3); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(FIG / "res_linealidad.png")

# ---------- Tabla 2 ----------
out.append("\nTABLA 2 — rampas (0 → 60 Hz, P1082 = 60)")
tr, tmed, imax = T2.T[:3]
for i in range(len(tr)):
    dw = 2 * np.pi * (120 * 60 / POLOS) / 60 / tr[i]
    err = (tmed[i] - tr[i]) / tr[i] * 100 if np.isfinite(tmed[i]) else np.nan
    out.append(f" P1120={tr[i]:4.0f} s  dω/dt={dw:5.1f} rad/s²  t_med={tmed[i]:6.2f} s (err {err:+.1f} %)  Imax={imax[i]:.2f} A")
if np.isfinite(imax).any():
    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    ax.plot(2 * np.pi * 60 / tr, imax, "o-")
    for x, y, l in zip(2 * np.pi * 60 / tr, imax, tr):
        if np.isfinite(y): ax.annotate(f"{l:.0f} s", (x, y), (4, 4), textcoords="offset points", fontsize=8)
    ax.set_xlabel("dω/dt [rad/s²]"); ax.set_ylabel("I máx. [A]"); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(FIG / "res_rampas.png")

# ---------- Tabla 3 ----------
out.append("\nTABLA 3 — V/f (r0025)")
f3, vl, vq, vb = T3.T[:4]
teo = 220 * f3 / 60
for i in range(len(f3)):
    out.append(f" {f3[i]:3.0f} Hz  teórica {teo[i]:6.1f}  lineal {vl[i]:6.1f}  cuadr {vq[i]:6.1f}  boost {vb[i]:6.1f}")
okl = np.isfinite(vl)
if okl.sum() >= 2:
    m, b = np.polyfit(f3[okl], vl[okl], 1)
    out.append(f"Pendiente lineal medida: {m:.3f} V/Hz (teórica 3,667) ; corte en 0 Hz: {b:.1f} V (refuerzo de fábrica)")
fig, ax = plt.subplots(figsize=(3.4, 2.4))
ff = np.linspace(0, 60, 61)
ax.plot(ff, 220 * ff / 60, "k:", lw=.8, label="3,67 V/Hz")
for y, l, mk in ((vl, "lineal", "o-"), (vq, "cuadrática", "s-"), (vb, "lineal + boost", "^-")):
    if np.isfinite(y).any(): ax.plot(f3, y, mk, ms=4, label=l)
ax.set_xlabel("f [Hz]"); ax.set_ylabel("r0025 [V]"); ax.grid(alpha=.3); ax.legend(frameon=False, fontsize=7)
fig.tight_layout(); fig.savefig(FIG / "res_vf.png")

texto = "\n".join(out)
(AQUI / "resumen_resultados.txt").write_text(texto, encoding="utf-8")
print(texto)
print(f"\nFiguras en {FIG}")
