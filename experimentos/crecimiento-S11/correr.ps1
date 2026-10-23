# Uso (desde la raiz del repo):  .\experimentos\crecimiento-S11\correr.ps1 -Corrida 1
# Cada corrida dura ~11 minutos. No reinicies los contenedores entre corridas.
param([Parameter(Mandatory=$true)][int]$Corrida)
$dir = Join-Path $PSScriptRoot "resultados"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$base = Join-Path $dir ("corrida-{0}" -f $Corrida)
$k6js = Join-Path $PSScriptRoot "crecimiento.js"

# Muestreo en segundo plano (~cada 2-3 s): CPU total del equipo, CPU acumulada de k6, backend, BD y conexiones a Postgres
$muestreo = Start-Job -ArgumentList $base -ScriptBlock {
  param($base)
  "epoch,cpu_total_pct,k6_cpu_seg,backend_cpu,backend_mem,db_cpu,conexiones_db" | Out-File "$base-muestreo.csv" -Encoding ascii
  while ($true) {
    $epoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $cpu = (Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'").PercentProcessorTime
    $k6 = (Get-Process k6 -ErrorAction SilentlyContinue | Measure-Object -Property CPU -Sum).Sum
    if ($null -eq $k6) { $k6 = 0 }
    $stats = docker stats --no-stream --format "{{.Name}};{{.CPUPerc}};{{.MemUsage}}"
    $b = ($stats | Where-Object { $_ -like "urbanfixbackend;*" }) -split ";"
    $d = ($stats | Where-Object { $_ -like "urbanfixdb;*" }) -split ";"
    $n = docker exec urbanfixdb psql -U postgres -d urbanfix -t -A -c "select count(*) from pg_stat_activity where datname='urbanfix'"
    "$epoch,$cpu,$k6,$($b[1]),$($b[2]),$($d[1]),$n" | Out-File "$base-muestreo.csv" -Append -Encoding ascii
    Start-Sleep -Seconds 1
  }
}

Write-Host "Corrida $Corrida del experimento de crecimiento (~11 min). No uses el equipo mientras tanto."
try {
  k6 run --quiet --out "csv=$base.csv" --summary-export "$base-resumen.json" $k6js 2>&1 |
    ForEach-Object { "$_" } | Tee-Object -FilePath "$base-consola.txt"
}
finally {
  Stop-Job $muestreo; Remove-Job $muestreo
}

# El CSV completo de k6 pesa decenas de MB: se conservan solo las filas que usa el analisis
# (peticiones y duraciones, con su escalon y codigo de respuesta). Es un filtro sin perdida para esos datos.
if (Test-Path "$base.csv") {
  Get-Content "$base.csv" -ReadCount 5000 |
    ForEach-Object { $_ | Where-Object { $_ -match '^(metric_name|http_reqs|http_req_duration),' } } |
    Set-Content "$base-filtrado.csv" -Encoding ascii
  Remove-Item "$base.csv"
}
Write-Host "Listo. Espera 2 minutos antes de la siguiente corrida."
