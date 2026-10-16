#!/usr/bin/env python3
"""Resume las corridas del Spike 01: mediana por brazo, criterios del pre-registro y borrador del veredicto.

Uso:  python exp/spike-01/resumir.py
Lee   exp/spike-01/resultados/{baseline,spike}-corrida-N-{resumen.json, .csv, docker-stats.csv, conexiones.csv}
Descarta la corrida 1 de cada brazo (calentamiento), segun el pre-registro.
Escribe resultados/resumen.md y veredicto-borrador.md
"""
import csv, json, re, statistics as st, sys
from pathlib import Path

AQUI = Path(__file__).parent
RES = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI / "resultados"
MEJORA_MIN = 0.30      # p95 spike <= 0.70 x p95 baseline
ERROR_MAX = 0.05
MIN_VALIDAS = 3


def metricas(m, nombre):
    x = m.get(nombre, {})
    return x.get("values", x)


def a_mib(txt):
    n, u = re.match(r"([\d.]+)\s*([A-Za-z]+)", txt.strip()).groups()
    f = {"B": 1 / 1048576, "KiB": 1 / 1024, "kB": 1 / 1024, "MiB": 1, "MB": 1, "GiB": 1024, "GB": 1024}.get(u, 1)
    return float(n) * f


def leer_corrida(arm, n):
    b = RES / f"{arm}-corrida-{n}"
    j = json.load(open(f"{b}-resumen.json", encoding="utf-8"))["metrics"]
    dur = metricas(j, "http_req_duration")
    fail = metricas(j, "http_req_failed")
    reqs = metricas(j, "http_reqs")
    chk = metricas(j, "checks")
    r = {
        "p95_s": dur["p(95)"] / 1000, "avg_s": dur["avg"] / 1000,
        "error": fail.get("value", fail.get("rate", 0.0)),
        "reqs": reqs["count"], "rps": reqs["rate"],
        "checks_ok": chk.get("passes", 0), "checks_fail": chk.get("fails", 0),
    }
    cod = {"2xx": 0, "4xx": 0, "5xx": 0, "sin_respuesta": 0}
    p = Path(f"{b}.csv")
    if p.exists():
        for row in csv.DictReader(open(p, encoding="utf-8")):
            if row.get("metric_name") != "http_reqs":
                continue
            s = int(row.get("status") or 0)
            k = "2xx" if 200 <= s < 300 else "4xx" if 400 <= s < 500 else "5xx" if s >= 500 else "sin_respuesta"
            cod[k] += 1
    r.update(cod)
    p = Path(f"{b}-docker-stats.csv")
    if p.exists():
        cpu, mem = [], []
        for ln in open(p, encoding="ascii").read().splitlines()[1:]:
            t = ln.split(",", 3)
            if len(t) == 4 and t[1] == "urbanfixbackend":
                cpu.append(float(t[2].rstrip("%"))); mem.append(a_mib(t[3].split("/")[0]))
        r["cpu_back_prom"] = st.mean(cpu) if cpu else None
        r["cpu_back_max"] = max(cpu) if cpu else None
        r["mem_back_max_mib"] = max(mem) if mem else None
    p = Path(f"{b}-conexiones.csv")
    if p.exists():
        v = [int(ln.split(",")[1]) for ln in open(p, encoding="ascii").read().splitlines()[1:]
             if ln.count(",") == 1 and ln.split(",")[1].strip().isdigit()]
        r["conex_db_max"] = max(v) if v else None
    return r


def corridas(arm):
    nums = sorted(int(re.search(r"corrida-(\d+)-resumen", f.name).group(1)) for f in RES.glob(f"{arm}-corrida-*-resumen.json"))
    return [leer_corrida(arm, n) for n in nums if n != 1], nums


def med(rs, k):
    v = [r[k] for r in rs if r.get(k) is not None]
    return st.median(v) if v else None


CAMPOS = [("p95_s", "p95 http_req_duration (s)"), ("avg_s", "promedio (s)"), ("error", "tasa de error"),
          ("rps", "throughput (req/s)"), ("reqs", "peticiones"), ("2xx", "respuestas 2xx"), ("4xx", "respuestas 4xx"),
          ("5xx", "respuestas 5xx"), ("sin_respuesta", "sin respuesta / timeout"),
          ("cpu_back_prom", "CPU backend promedio (%)"), ("cpu_back_max", "CPU backend maximo (%)"),
          ("mem_back_max_mib", "memoria backend maxima (MiB)"), ("conex_db_max", "conexiones max. a Postgres")]


def fmt(v, k):
    if v is None:
        return "n/d"
    return f"{v*100:.2f} %" if k == "error" else f"{v:,.2f}" if isinstance(v, float) else f"{v:,}"


def main():
    base, nb = corridas("baseline")
    spk, ns = corridas("spike")
    L = []
    L.append("# Resumen de resultados — Spike 01\n")
    L.append(f"Corridas encontradas: baseline {nb}, spike {ns}. Se descarta la corrida 1 de cada brazo; "
             f"validas: baseline {len(base)}, spike {len(spk)} (minimo {MIN_VALIDAS}).\n")
    L.append("## Corrida por corrida (p95 s / error)\n")
    for nombre, rs, nums in (("Linea base", base, [n for n in nb if n != 1]), ("Spike", spk, [n for n in ns if n != 1])):
        L.append(f"- **{nombre}:** " + "; ".join(f"corrida {n}: {r['p95_s']:.2f} s / {r['error']*100:.2f} %" for n, r in zip(nums, rs)))
    L.append("\n## Medianas por brazo\n\n| Metrica | Linea base | Spike |\n|---|---|---|")
    for k, nombre in CAMPOS:
        L.append(f"| {nombre} | {fmt(med(base,k),k)} | {fmt(med(spk,k),k)} |")
    if len(base) < MIN_VALIDAS or len(spk) < MIN_VALIDAS:
        veredicto, razon = "INCONCLUSO", f"menos de {MIN_VALIDAS} corridas validas por brazo"
        c1 = c2 = c3 = None
    else:
        bp, sp = med(base, "p95_s"), med(spk, "p95_s")
        mejora = 1 - sp / bp
        c1 = sp <= (1 - MEJORA_MIN) * bp
        c2 = med(spk, "error") <= ERROR_MAX
        tot = lambda rs, k: med([{**r, "tot": r["2xx"] + r["4xx"] + r["5xx"] + r["sin_respuesta"]} for r in rs], k)
        s5 = (med(spk, "5xx") or 0) / max(tot(spk, "tot") or 1, 1)
        b5 = (med(base, "5xx") or 0) / max(tot(base, "tot") or 1, 1)
        c3 = s5 <= b5
        L.append("\n## Criterios del pre-registro\n\n| Criterio | Resultado | Cumple |\n|---|---|---|")
        L.append(f"| p95 mediano spike <= 0,70 x linea base | {sp:.2f} s vs {bp:.2f} s (mejora {mejora*100:.1f} %) | {'SI' if c1 else 'NO'} |")
        L.append(f"| error mediano spike <= 5 % | {med(spk,'error')*100:.2f} % | {'SI' if c2 else 'NO'} |")
        L.append(f"| 5xx no aumentan frente a linea base | {s5*100:.2f} % vs {b5*100:.2f} % de las respuestas | {'SI' if c3 else 'NO'} |")
        veredicto = "HIPOTESIS RESPALDADA" if (c1 and c2 and c3) else "HIPOTESIS REFUTADA"
        razon = "se cumplen todos los criterios" if (c1 and c2 and c3) else "al menos un criterio no se cumple"
    L.append(f"\n**Veredicto segun la regla pre-registrada: {veredicto}** ({razon}).\n")
    (RES / "resumen.md").write_text("\n".join(L), encoding="utf-8")

    cpu = med(base, "cpu_back_max"), med(spk, "cpu_back_max")
    V = f"""# Veredicto del Spike 01 (BORRADOR — revisar y completar a mano)

**Veredicto:** {veredicto}. Regla aplicada: la definida en `exp/00-preregistro.md` (medianas de {len(base)} corridas validas en linea base y {len(spk)} en spike, descartando la corrida 1 de cada brazo).

## Resultados
Ver `resultados/resumen.md` (tabla completa) y los archivos crudos en `resultados/`.

## Lo que muestran los datos de recursos
- CPU maxima mediana del backend: linea base {fmt(cpu[0],'x')} %, spike {fmt(cpu[1],'x')} %.
- Conexiones maximas a Postgres (mediana): linea base {fmt(med(base,'conex_db_max'),'x')}, spike {fmt(med(spk,'conex_db_max'),'x')}.
- COMPLETAR: que recurso se saturo primero (CPU o conexiones) y que dice eso sobre la premisa del ADR 0002.

## Interpretacion acordada de antemano (pre-registro, seccion 9)
- Si fue respaldada: PgBouncer entra al ADR 3 como alternativa viable, con los limites declarados.
- Si fue refutada: la premisa "el pool es la causa" no se sostiene con esta evidencia; el ADR 3 se redacta con los datos de CPU y conexiones.

## Limites de la evidencia (del pre-registro, seccion 10)
- Medicion local en el laptop de Samuel (i5-1035G1, 16 GB), no en produccion (EC2 t2.micro + Neon).
- Un solo usuario de prueba y un solo endpoint (`POST /login`); no se evaluo aislamiento entre dominios.
- No se midio mantenibilidad, costo ni comportamiento de `/reportes`.
- COMPLETAR: cualquier desviacion del protocolo ocurrida durante las corridas.
"""
    (RES / "veredicto-borrador.md").write_text(V, encoding="utf-8")
    print("\n".join(L))


main()
