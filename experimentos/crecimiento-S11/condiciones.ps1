# Uso:  .\experimentos\crecimiento-S11\condiciones.ps1   (una vez, antes de la corrida 1)
$dir = Join-Path $PSScriptRoot "resultados"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$f = Join-Path $dir "condiciones.txt"
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
$q = "select (select count(*) from usuarios) as usuarios, (select count(*) from reportes) as reportes, (select count(*) from funcionarios) as funcionarios"
$lines = @()
$lines += "fecha: $(Get-Date -Format s)"
$lines += "rama: $(git rev-parse --abbrev-ref HEAD)"
$lines += "commit: $(git rev-parse HEAD)"
$lines += "cambios sin commitear (debe estar vacio):"
$lines += (git status --short)
$lines += "cpu: $($cpu.Name)"
$lines += "nucleos fisicos: $($cpu.NumberOfCores)"
$lines += "procesadores logicos: $($cpu.NumberOfLogicalProcessors)"
$lines += "ram_gb: $ram"
$lines += "plan de energia: $(powercfg /getactivescheme)"
$lines += "k6: $(k6 version)"
$lines += "docker: $(docker --version)"
$lines += "imagenes:"
$lines += (docker images --digests --format "  {{.Repository}}:{{.Tag}} {{.Digest}}" | Select-String "postgres|urbanfix")
$lines += "contenedores en ejecucion:"
$lines += (docker ps --format "  {{.Names}} {{.Image}}")
$lines += "filas:"
$lines += (docker exec urbanfixdb psql -U postgres -d urbanfix -c $q)
$lines += "prefijo hash usuario de prueba (solo algoritmo):"
$lines += (docker exec urbanfixdb psql -U postgres -d urbanfix -t -A -c 'select split_part(contrasena_hash, ''$'', 1) from usuarios where email=''test@urbanfix.com''')
$lines | Out-File $f -Encoding ascii
Get-Content $f
