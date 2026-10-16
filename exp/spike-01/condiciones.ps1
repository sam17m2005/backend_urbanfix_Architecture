# Uso:  .\exp\spike-01\condiciones.ps1 -Brazo baseline   (antes de la primera corrida de cada brazo)
param([Parameter(Mandatory=$true)][ValidateSet('baseline','spike')][string]$Brazo)
$dir = Join-Path $PSScriptRoot "resultados"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$f = Join-Path $dir "condiciones-$Brazo.txt"
$q = "select (select count(*) from usuarios) as usuarios, (select count(*) from reportes) as reportes, (select count(*) from funcionarios) as funcionarios"
$lines = @()
$lines += "brazo: $Brazo"
$lines += "fecha: $(Get-Date -Format s)"
$lines += "rama: $(git rev-parse --abbrev-ref HEAD)"
$lines += "commit: $(git rev-parse HEAD)"
$lines += "k6: $(k6 version)"
$lines += "docker: $(docker --version)"
$lines += "imagenes:"
$lines += (docker images --digests --format "  {{.Repository}}:{{.Tag}} {{.Digest}}" | Select-String "postgres|pgbouncer|urbanfix")
$lines += "filas:"
$lines += (docker exec urbanfixdb psql -U postgres -d urbanfix -c $q)
$lines += "prefijo hash usuario de prueba (solo algoritmo):"
$lines += (docker exec urbanfixdb psql -U postgres -d urbanfix -t -A -c 'select split_part(contrasena_hash, ''$'', 1) from usuarios where email=''test@urbanfix.com''')
$lines | Out-File $f -Encoding ascii
Get-Content $f
