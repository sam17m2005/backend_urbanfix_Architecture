#!/usr/bin/env python3
"""Clasifica las peticiones sin respuesta (HTTP 0) por tipo y momento, a partir de la consola de k6.

Uso:  python experimentos/crecimiento-S11/analisis_errores.py
Lee   resultados/corrida-N-consola.txt (UTF-16: asi lo guarda Tee-Object en Windows PowerShell 5.1) y corrida-N-filtrado.csv
Escribe resultados/errores.md. Solo biblioteca estandar.
"""
import csv, datetime, re, statistics as st, sys
from collections import Counter, defaultdict
from pathlib import Path

RES = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "resultados"
DURACION, PAUSA, TOL = 45, 30, 2   # TOL: segundos de tolerancia para ubicar un aviso en su escalon


def leer_texto(p):
    raw = p.read_bytes()
    return raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8", errors="replace").replace("\r", "")


def tipo(e):
    return "conexion rechazada" if "connectex" in e else "timeout 60 s" if "timeout" in e else "EOF" if "EOF" in e else "otro"


nums = sorted(int(re.search(r"corrida-(\d+)-consola", p.name).group(1)) for p in RES.glob("corrida-*-consola.txt"))
tipos = defaultdict(lambda: defaultdict(Counter))   # corrida -> paso -> tipo -> n
inicio = Counter()                                   # conexiones rechazadas: primeros 5 s del escalon vs resto
cods = defaultdict(lambda: defaultdict(Counter))     # corrida -> paso -> status -> n
pasos = []
for n in nums:
    filas = list(csv.DictReader(open(RES / f"corrida-{n}-filtrado.csv", encoding="utf-8")))
    pasos = sorted({int(re.match(r"paso_(\d+)", r["scenario"]).group(1)) for r in filas if re.match(r"paso_(\d+)", r["scenario"] or "")})
    t0 = min(int(r["timestamp"]) for r in filas if r["scenario"] == f"paso_{pasos[0]:04d}")
    for r in filas:
        m = re.match(r"paso_(\d+)", r["scenario"] or "")
        if m and r["metric_name"] == "http_reqs":
            cods[n][int(m.group(1))][r["status"] or "0"] += 1
    for l in leer_texto(RES / f"corrida-{n}-consola.txt").split("\n"):
        m = re.match(r'time="([^"]+)".*?error="(.*)"\s*$', l)
        if not m:
            continue
        ts = int(datetime.datetime.fromisoformat(m.group(1)).timestamp())
        i = (ts - t0 + TOL) // (DURACION + PAUSA)
        dentro = (ts - t0 + TOL) % (DURACION + PAUSA)
        if 0 <= i < len(pasos):
            t = tipo(m.group(2))
            tipos[n][pasos[i]][t] += 1
            if t == "conexion rechazada":
                inicio["primeros 5 s del escalon" if dentro < 5 + TOL else "resto del escalon"] += 1

validas = [n for n in nums if n != 1]
L = ["# Errores por tipo y momento (experimento de crecimiento)\n",
     "Fuente: avisos `Request Failed` de la consola de k6 (corridas válidas 2 a 4) y códigos de respuesta del CSV.\n",
     "## Conexiones rechazadas: ¿cuándo ocurren?\n",
     f"- Primeros 5 s de un escalón: **{inicio['primeros 5 s del escalon']}** · resto del escalón: **{inicio['resto del escalon']}** (suma de las {len(nums)} corridas).\n",
     "## Tasa de error por escalón: total y sin contar las conexiones rechazadas (mediana de las corridas válidas)\n",
     "| VUs | Error total | Error sin conexiones rechazadas | HTTP 500 | Sin respuesta (todas) | de ellas: rechazadas | de ellas: timeout 60 s |",
     "|---|---|---|---|---|---|---|"]
for p in pasos:
    tot, sinr, c500, c0, rech, tmo = [], [], [], [], [], []
    for n in validas:
        c = cods[n][p]; total = sum(c.values()); ok = c.get("200", 0)
        r = tipos[n][p]["conexion rechazada"]
        tot.append((total - ok) / total if total else 0)
        sinr.append(((total - ok) - r) / (total - r) if total - r > 0 else 0)
        c500.append(c.get("500", 0)); c0.append(c.get("0", 0)); rech.append(r); tmo.append(tipos[n][p]["timeout 60 s"])
    L.append(f"| {p} | {st.median(tot)*100:.2f} % | {st.median(sinr)*100:.2f} % | {st.median(c500):.0f} | {st.median(c0):.0f} | {st.median(rech):.0f} | {st.median(tmo):.0f} |")
L.append("\nNota: los avisos de k6 se ubican en su escalón por la hora (tolerancia de 2 s); la clasificación es aproximada en los bordes de cada escalón.")
(RES / "errores.md").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))
