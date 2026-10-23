#!/usr/bin/env python3
"""Genera las graficas de degradacion del experimento de crecimiento (requiere matplotlib).

Uso:  pip install matplotlib   y luego   python experimentos/crecimiento-S11/graficar.py
Lee los resultados crudos con las mismas funciones de resumir.py y escribe PNG en graficas/.
"""
import statistics as st, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = Path(__file__).parent
RES = AQUI / "resultados"
SAL = AQUI / "graficas"
SAL.mkdir(exist_ok=True)

# se reutilizan las funciones de lectura de resumir.py (sin ejecutar su main)
sys.argv = [sys.argv[0], str(RES)]
ns = {"__file__": str(AQUI / "resumir.py"), "__name__": "resumir"}
exec(compile((AQUI / "resumir.py").read_text(encoding="utf-8").rsplit("\nmain()", 1)[0], "resumir.py", "exec"), ns)
n_log, _ = ns["logicos"]()
nums = sorted(int(p.name.split("-")[1]) for p in RES.glob("corrida-*-resumen.json"))
validas = [ns["leer_corrida"](n, n_log) for n in nums if n != 1]
pasos = sorted(validas[0])
X = list(range(len(pasos)))


def serie(k, escala=1.0):
    med, lo, hi = [], [], []
    for v in pasos:
        vals = [r[v][k] * escala for r in validas if r[v].get(k) is not None]
        med.append(st.median(vals)); lo.append(min(vals)); hi.append(max(vals))
    return med, lo, hi


def base(titulo, ylabel):
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.set_title(titulo, fontsize=12); ax.set_xlabel("Usuarios virtuales simultáneos (escalón)"); ax.set_ylabel(ylabel)
    ax.set_xticks(X); ax.set_xticklabels([str(v) for v in pasos]); ax.grid(alpha=.3)
    return fig, ax


def guardar(fig, nombre):
    fig.tight_layout(); fig.savefig(SAL / nombre, dpi=140); plt.close(fig)

# 1. Latencia p95
m, lo, hi = serie("p95_ms", 1 / 1000)
fig, ax = base("Latencia p95 de POST /login por escalón de carga", "p95 (segundos, escala logarítmica)")
ax.errorbar(X, m, yerr=[[a - b for a, b in zip(m, lo)], [b - a for a, b in zip(m, hi)]], marker="o", capsize=3, label="mediana (barras: mín–máx de las 3 corridas)")
ax.axhline(1, color="orange", ls="--", label="umbral de degradación (1 s)"); ax.axhline(60, color="red", ls=":", label="tiempo máximo de k6 (60 s)")
ax.set_yscale("log"); ax.legend(fontsize=8); guardar(fig, "1-latencia-p95.png")

# 2. Errores por tipo (barras apiladas, % de peticiones)
c500, csin = [], []
for v in pasos:
    a, b = [], []
    for r in validas:
        t = sum(r[v]["codigos"].values()); a.append(r[v]["codigos"].get("500", 0) / t * 100); b.append(r[v]["codigos"].get("0", 0) / t * 100)
    c500.append(st.median(a)); csin.append(st.median(b))
fig, ax = base("Peticiones fallidas por escalón (mediana de cada tipo por separado)", "% de las peticiones del escalón")
ax.bar(X, c500, label="HTTP 500", color="#d9822b"); ax.bar(X, csin, bottom=c500, label="sin respuesta (conexión rechazada, timeout, EOF)", color="#b03a48")
ax.axhline(5, color="black", ls="--", label="umbral de quiebre (5 %)"); ax.legend(fontsize=8); guardar(fig, "2-errores.png")

# 3. Capacidad
m, lo, hi = serie("ok_por_s")
fig, ax = base("Logins exitosos por segundo (capacidad efectiva)", "logins HTTP 200 por segundo")
ax.errorbar(X, m, yerr=[[a - b for a, b in zip(m, lo)], [b - a for a, b in zip(m, hi)]], marker="o", capsize=3, color="green")
ax.set_ylim(0, max(hi) * 1.25); guardar(fig, "3-capacidad.png")

# 4. Recursos
cpu, _, _ = serie("cpu_total_prom"); k6, _, _ = serie("k6_pct_prom")
fig, ax = base("CPU del equipo durante cada escalón", "% de la CPU total del equipo")
ax.plot(X, cpu, marker="o", label="CPU total del equipo (media)"); ax.plot(X, k6, marker="s", color="red", label="CPU consumida por k6")
ax.axhline(25, color="red", ls="--", alpha=.5, label="umbral de límite del instrumento (k6 > 25 %)"); ax.set_ylim(0, 110); ax.legend(fontsize=8)
guardar(fig, "4-cpu.png")
print("graficas escritas en", SAL)
