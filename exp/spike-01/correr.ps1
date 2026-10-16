# Uso (desde la raiz del repo):  .\exp\spike-01\correr.ps1 -Brazo baseline -Corrida 1
param(
  [Parameter(Mandatory=$true)][ValidateSet('baseline','spike')][string]$Brazo,
  [Parameter(Mandatory=$true)][int]$Corrida
)
$dir = Join-Path $PSScriptRoot "resultados"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$base  = Join-Path $dir ("{0}-corrida-{1}" -f $Brazo, $Corrida)
$k6js  = Join-Path $PSScriptRoot "..\..\Pruebas\prueba2.js"

# Muestreo en segundo plano: CPU/memoria de contenedores y conexiones abiertas en Postgres
$muestreo = Start-Job -ArgumentList $base -ScriptBlock {
  param($base)
  "t,contenedor,cpu,mem" | Out-File "$base-docker-stats.csv" -Encoding ascii
  "t,conexiones_db"      | Out-File "$base-conexiones.csv"   -Encoding ascii
  while ($true) {
    $t = Get-Date -Format "HH:mm:ss"
    docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}}" |
      ForEach-Object { "$t,$_" } | Out-File "$base-docker-stats.csv" -Append -Encoding ascii
    $n = docker exec urbanfixdb psql -U postgres -d urbanfix -t -A -c "select count(*) from pg_stat_activity where datname='urbanfix'"
    "$t,$n" | Out-File "$base-conexiones.csv" -Append -Encoding ascii
    Start-Sleep -Seconds 1
  }
}

Write-Host "Corrida $Corrida del brazo $Brazo ... (60 s)"
try {
  k6 run --quiet --out "csv=$base.csv" --summary-export "$base-resumen.json" $k6js 2>&1 |
    ForEach-Object { "$_" } | Tee-Object -FilePath "$base-consola.txt"
}
finally {
  Stop-Job $muestreo; Remove-Job $muestreo
}
Write-Host "Listo. Espera 2 minutos antes de la siguiente corrida."
