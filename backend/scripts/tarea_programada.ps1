<#
.SYNOPSIS
Ejecuta un comando de `manage.py` dejando registro en disco. Pensado para que lo invoque el
Programador de tareas de Windows, no una persona.

.DESCRIPTION
El Programador de tareas no hereda el entorno de nadie: no tiene el venv activo, arranca en
`C:\Windows\System32` y descarta la salida estándar. Este envoltorio resuelve las tres cosas —
usa el Python del venv por ruta absoluta, se sitúa en `backend/` (que es donde `manage.py` espera
correr) y escribe todo a un log, porque una tarea programada que falla en silencio es peor que una
que no existe: nadie se entera hasta que alguien nota que los datos están viejos.

Devuelve el mismo código de salida que el comando, para que el Programador marque la tarea como
fallida y eso se vea en su historial.

.PARAMETER Comando
Nombre del comando de `manage.py` (p. ej. `actualizar_fuentes_bd`).

.PARAMETER Argumentos
Argumentos extra para el comando, escritos sueltos al final (p. ej. `--horas 24`).

.EXAMPLE
.\tarea_programada.ps1 -Comando actualizar_fuentes_bd

.EXAMPLE
.\tarea_programada.ps1 -Comando clean_temp_uploads -Argumentos '--horas','24'
#>
param(
    [Parameter(Mandatory = $true)][string]$Comando,
    # `ValueFromRemainingArguments` y no un array normal: cuando el Programador de tareas invoca
    # `powershell.exe -File ...`, PowerShell NO interpreta la sintaxis de arrays — `'--horas','24'`
    # llega como la cadena literal `--horas,24` y Django la rechaza. Así los argumentos se escriben
    # sueltos (`-Comando clean_temp_uploads --horas 24`) y funcionan igual desde la consola.
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Argumentos = @()
)

$ErrorActionPreference = 'Stop'

$RaizBackend = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RaizBackend '.venv\Scripts\python.exe'
$ManagePy = Join-Path $RaizBackend 'manage.py'
$CarpetaLogs = Join-Path $RaizBackend 'logs\tareas'

if (-not (Test-Path $Python)) {
    Write-Error "No existe el intérprete del entorno virtual en '$Python'. Creá el venv antes de programar la tarea."
    exit 1
}
if (-not (Test-Path $ManagePy)) {
    Write-Error "No existe '$ManagePy'."
    exit 1
}

if (-not (Test-Path $CarpetaLogs)) {
    New-Item -ItemType Directory -Force -Path $CarpetaLogs | Out-Null
}

# Un archivo por comando y por mes: suficiente para revisar qué pasó sin que crezca indefinidamente
# ni haya que montar rotación de logs.
$Log = Join-Path $CarpetaLogs "$Comando-$(Get-Date -Format 'yyyy-MM').log"
$Inicio = Get-Date

Add-Content -Path $Log -Encoding utf8 -Value ''
Add-Content -Path $Log -Encoding utf8 -Value "===== $($Inicio.ToString('yyyy-MM-dd HH:mm:ss')) — manage.py $Comando $($Argumentos -join ' ')"

# El Programador de tareas arranca la consola con la página de códigos OEM del sistema, no con la
# del usuario: sin esto, la salida de Django llega mal decodificada al log ("Ning·n", "automßtica")
# y un traceback con acentos se vuelve difícil de leer, que es justo cuando más falta hace. Se fija
# UTF-8 en los dos extremos: lo que Python escribe y cómo PowerShell lo lee.
$env:PYTHONIOENCODING = 'utf-8'
$EncodingPrevio = [Console]::OutputEncoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Push-Location $RaizBackend
try {
    # stderr se une a stdout para que el traceback de un fallo quede en el mismo log que la salida
    # normal, en orden. `cmd /c` evita que PowerShell 5.1 envuelva cada línea de stderr de un
    # ejecutable nativo en un ErrorRecord (NativeCommandError), que ensucia el log y rompe $?.
    $Salida = & cmd /c "`"$Python`" `"$ManagePy`" $Comando $($Argumentos -join ' ') 2>&1"
    $Codigo = $LASTEXITCODE
    if ($Salida) { Add-Content -Path $Log -Encoding utf8 -Value $Salida }
} finally {
    Pop-Location
    [Console]::OutputEncoding = $EncodingPrevio
}

$Duracion = [int]((Get-Date) - $Inicio).TotalSeconds
if ($Codigo -eq 0) {
    Add-Content -Path $Log -Encoding utf8 -Value "----- OK en ${Duracion}s"
} else {
    Add-Content -Path $Log -Encoding utf8 -Value "----- FALLÓ con código $Codigo en ${Duracion}s"
}

exit $Codigo
