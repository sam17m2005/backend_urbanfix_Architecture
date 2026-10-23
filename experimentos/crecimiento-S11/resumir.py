#!/usr/bin/env python3
"""Resume el experimento de crecimiento (E3): resultados por escalon, medianas de las corridas validas,
punto de degradacion / quiebre / meseta, limite del instrumento y evaluacion de las predicciones del plan.

Uso:  python experimentos/crecimiento-S11/resumir.py
Lee   resultados/corrida-N-filtrado.csv (o corrida-N.csv), corrida-N-muestreo.csv y condiciones.txt
Descarta la corrida 1 (calentamiento). Escribe resultados/resumen.md y resultados/resumen.json
Solo usa la biblioteca estandar.
"""
import csv, json, re, statistics as st, sys
from pathlib import Path

AQUI = Path(__file__).parent
RES = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI / "resultados"

# --- deben coincidir con crecimiento.js y con 00-plan.md ---
DURACION = 45          # s por escalon
PAUSA = 30             # s entre escalones
UMBRAL_P95_MS = 1000   # degradacion: p95 mediano > 1 s
UMBRAL_ERROR = 0.05    # quiebre: error mediano > 5 %
CRECIMIENTO_MIN = 0.10 # meseta: los logins OK/s crecen menos de 10 % al subir al escalon siguiente
UMBRAL_K6 = 0.25       # instrumento limitado: k6 consume > 25 % de la CPU total del equipo
MIN_VALIDAS = 3
PRED_DEGRADACION_MAX_VUS = 50    # prediccion (a): degradacion con <= 50 VUs
PRED_QUIEBRE_MIN_VUS = 200       # prediccion (b): quiebre no antes de 200 VUs


def p95(v):
    if not v:
        return None
    v = sorted(v)
    k = (len(v) - 1) * 0.95
    f = int(k)
    c = min(f + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)


def num(txt):
    m = re.search(r"-?\d+(?:[.,]\d+)?", txt or "")
    return float(m.group(0).replace(",", ".")) if m else None


def mib(txt):
    m = re.match(r"\s*([\d.,]+)\s*([A-Za-z]+)", txt or "")
    if not m:
        return None
    f = {"B": 1 / 1048576, "KiB": 1 / 1024, "kB": 1 / 1024, "MiB": 1, "MB": 1, "GiB": 1024, "GB": 1024}.get(m.group(2), 1)
    return float(m.group(1).replace(",", ".")) * f


def logicos():
    p = RES / "condiciones.txt"
    if p.exists():
        m = re.search(r"procesadores logicos:\s*(\d+)", p.read_text(encoding="utf-8", errors="replace"))
        if m:
            return int(m.group(1)), True
    return 8, False


def leer_corrida(n, n_log):
    base = RES / f"corrida-{n}"
    arch = base.with_name(base.name + "-filtrado.csv")
    if not arch.exists():
        arch = base.with_suffix(".csv")
    por = {}
    t_ini = {}
    for r in csv.DictReader(open(arch, encoding="utf-8")):
        m = re.match(r"paso_(\d+)$", r.get("scenario") or "")
        if not m or not r.get("timestamp"):
            continue
        vus = int(m.group(1))
        ts = int(r["timestamp"])
        d = por.setdefault(vus, {"dur": [], "cod": {}, "ok_ts": []})
        t_ini[vus] = min(t_ini.get(vus, ts), ts)
        if r["metric_name"] == "http_req_duration" and (r.get("status") or "0") not in ("0", ""):
            d["dur"].append(float(r["metric_value"]))
        elif r["metric_name"] == "http_reqs":
            s = r.get("status") or "0"
            d["cod"][s] = d["cod"].get(s, 0) + 1
            if s == "200":
                d["ok_ts"].append(ts)
    pasos = sorted(por)
    t0 = t_ini[pasos[0]]
    muestras = []
    mp = Path(f"{base}-muestreo.csv")
    if mp.exists():
        prev = None
        for r in csv.DictReader(open(mp, encoding="ascii", errors="replace")):
            try:
                ep = int(r["epoch"])
            except (ValueError, KeyError):
                continue
            k6 = num(r.get("k6_cpu_seg"))
            k6pct = None
            if prev is not None and k6 is not None and prev[1] is not None and ep > prev[0] and k6 >= prev[1]:
                k6pct = (k6 - prev[1]) / (ep - prev[0]) / n_log * 100
            prev = (ep, k6)
            muestras.append({"ep": ep, "cpu": num(r.get("cpu_total_pct")), "k6": k6pct,
                             "back": num(r.get("backend_cpu")), "mem": mib(r.get("backend_mem")),
                             "con": num(r.get("conexiones_db"))})
    out = {}
    for i, vus in enumerate(pasos):
        d = por[vus]
        w0 = t0 + i * (DURACION + PAUSA)
        w1 = w0 + DURACION
        n_req = sum(d["cod"].values())
        n_ok = d["cod"].get("200", 0)
        ok_ventana = sum(1 for t in d["ok_ts"] if w0 <= t < w1)
        ms = [m for m in muestras if w0 <= m["ep"] < w1]
        def agg(k, f):
            v = [m[k] for m in ms if m[k] is not None]
            return f(v) if v else None
        out[vus] = {
            "peticiones": n_req, "ok": n_ok, "codigos": d["cod"],
            "error": (n_req - n_ok) / n_req if n_req else None,
            "p95_ms": p95(d["dur"]), "prom_ms": st.mean(d["dur"]) if d["dur"] else None,
            "ok_por_s": ok_ventana / DURACION,
            "cpu_total_prom": agg("cpu", st.mean), "cpu_total_max": agg("cpu", max),
            "cpu_back_prom": agg("back", st.mean), "cpu_back_max": agg("back", max),
            "k6_pct_prom": agg("k6", st.mean), "conex_max": agg("con", max), "mem_back_max": agg("mem", max),
        }
    return out


def med(runs, vus, k):
    v = [r[vus][k] for r in runs if vus in r and r[vus].get(k) is not None]
    return st.median(v) if v else None


def f(v, d=2, suf=""):
    return "n/d" if v is None else f"{v:,.{d}f}{suf}"


def main():
    n_log, hay_cond = logicos()
    nums = sorted(int(re.search(r"corrida-(\d+)", p.name).group(1))
                  for p in RES.glob("corrida-*-resumen.json"))
    todas = {n: leer_corrida(n, n_log) for n in nums}
    validas = [todas[n] for n in nums if n != 1]
    pasos = sorted({v for r in todas.values() for v in r})
    L = ["# Resumen — experimento de crecimiento (POST /login)\n"]
    L.append(f"Corridas encontradas: {nums}. Se descarta la corrida 1 (calentamiento); válidas: {len(validas)} (mínimo {MIN_VALIDAS}).")
    if not hay_cond:
        L.append(f"> Aviso: no se encontró `condiciones.txt`; se asumen {n_log} procesadores lógicos para el % de CPU de k6.")
    L.append("\n## Por escalón: medianas de las corridas válidas\n")
    L.append("| VUs | Peticiones | p95 (ms) | Error | Logins OK/s | CPU total prom. (%) | CPU backend máx. (%) | k6 % del total | Conexiones BD máx. |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    res = {}
    for v in pasos:
        row = {k: med(validas, v, k) for k in ("peticiones", "p95_ms", "prom_ms", "error", "ok_por_s", "cpu_total_prom",
                                              "cpu_total_max", "cpu_back_prom", "cpu_back_max", "k6_pct_prom", "conex_max", "mem_back_max")}
        res[v] = row
        L.append(f"| {v} | {f(row['peticiones'],0)} | {f(row['p95_ms'],0)} | {f((row['error'] or 0)*100 if row['error'] is not None else None,2,' %')} "
                 f"| {f(row['ok_por_s'],2)} | {f(row['cpu_total_prom'],1)} | {f(row['cpu_back_max'],0)} | {f(row['k6_pct_prom'],1)} | {f(row['conex_max'],0)} |")
    L.append("\n## p95 por corrida (ms) — para ver la dispersión\n")
    L.append("| VUs | " + " | ".join(f"corrida {n}" + (" (descartada)" if n == 1 else "") for n in nums) + " |")
    L.append("|---|" + "---|" * len(nums))
    for v in pasos:
        L.append(f"| {v} | " + " | ".join(f(todas[n].get(v, {}).get('p95_ms'), 0) for n in nums) + " |")
    L.append("\n## Códigos de respuesta por escalón (mediana de peticiones por código)\n")
    cods = sorted({c for r in validas for v in r for c in r[v]['codigos']})
    L.append("| VUs | " + " | ".join(f"HTTP {c}" for c in cods) + " |")
    L.append("|---|" + "---|" * len(cods))
    for v in pasos:
        L.append(f"| {v} | " + " | ".join(f(st.median([r[v]['codigos'].get(c, 0) for r in validas if v in r]) if validas else None, 0) for c in cods) + " |")

    # --- puntos clave segun las definiciones del plan ---
    deg = next((v for v in pasos if res[v]["p95_ms"] is not None and res[v]["p95_ms"] > UMBRAL_P95_MS), None)
    qui = next((v for v in pasos if res[v]["error"] is not None and res[v]["error"] > UMBRAL_ERROR), None)
    mes = None
    for a, b in zip(pasos, pasos[1:]):
        oa, ob = res[a]["ok_por_s"], res[b]["ok_por_s"]
        if oa and ob is not None and ob < oa * (1 + CRECIMIENTO_MIN):
            mes = b
            break
    cap = max((res[v]["ok_por_s"] for v in pasos if res[v]["ok_por_s"] is not None), default=None)
    cap_v = next((v for v in pasos if res[v]["ok_por_s"] == cap), None)
    lim_k6 = [v for v in pasos if res[v]["k6_pct_prom"] is not None and res[v]["k6_pct_prom"] > UMBRAL_K6 * 100]
    equipo_sat = [v for v in pasos if res[v]["cpu_total_prom"] is not None and res[v]["cpu_total_prom"] > 90]
    L.append("\n## Puntos clave (definiciones del plan)\n")
    L.append(f"- **Punto de degradación** (p95 mediano > {UMBRAL_P95_MS} ms): {'primer escalón: **' + str(deg) + ' VUs**' if deg else 'no se alcanzó'}.")
    L.append(f"- **Punto de quiebre** (error mediano > {UMBRAL_ERROR*100:.0f} %): {'primer escalón: **' + str(qui) + ' VUs**' if qui else 'no se alcanzó'}.")
    L.append(f"- **Meseta de capacidad** (los logins OK/s crecen menos de {CRECIMIENTO_MIN*100:.0f} % al subir de escalón): {'desde **' + str(mes) + ' VUs**' if mes else 'no se observó'}; capacidad máxima observada: {f(cap,2)} logins OK/s (en {cap_v} VUs).")
    L.append(f"- **Límite del instrumento** (k6 consume > {UMBRAL_K6*100:.0f} % de la CPU total): {'escalones ' + ', '.join(map(str, lim_k6)) if lim_k6 else 'no se superó en ningún escalón'}. "
             f"Equipo con CPU total media > 90 %: {', '.join(map(str, equipo_sat)) if equipo_sat else 'ninguno'} VUs.")

    # --- predicciones ---
    L.append("\n## Evaluación de las predicciones pre-registradas\n")
    if len(validas) < MIN_VALIDAS:
        veredicto = "INCONCLUSO"
        L.append(f"Menos de {MIN_VALIDAS} corridas válidas: no se emite veredicto.")
    else:
        pa = deg is not None and deg <= PRED_DEGRADACION_MAX_VUS
        pb = qui is None or qui >= PRED_QUIEBRE_MIN_VUS
        L.append(f"| Predicción | Resultado | Se cumple |\n|---|---|---|")
        L.append(f"| (a) degradación de latencia con ≤ {PRED_DEGRADACION_MAX_VUS} VUs | {deg if deg else 'no se alcanzó'} VUs | {'Sí' if pa else 'No'} |")
        L.append(f"| (b) quiebre por errores no antes de {PRED_QUIEBRE_MIN_VUS} VUs | {qui if qui else 'no se alcanzó'} VUs | {'Sí' if pb else 'No'} |")
        veredicto = "HIPÓTESIS RESPALDADA" if (pa and pb) else "HIPÓTESIS REFUTADA"
    L.append(f"\n**Veredicto según la regla pre-registrada: {veredicto}.**\n")
    (RES / "resumen.md").write_text("\n".join(L), encoding="utf-8")
    (RES / "resumen.json").write_text(json.dumps({"pasos": pasos, "mediana": {str(v): res[v] for v in pasos},
        "corridas": nums, "degradacion": deg, "quiebre": qui, "meseta": mes, "capacidad_ok_s": cap,
        "limite_k6": lim_k6, "veredicto": veredicto}, indent=2), encoding="utf-8")
    print("\n".join(L))


main()
