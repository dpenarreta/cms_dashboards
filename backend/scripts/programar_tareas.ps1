<#
.SYNOPSIS
Registra (o quita) en el Programador de tareas de Windows las dos tareas periódicas del proyecto.

.DESCRIPTION
`actualizar_fuentes_bd` y `clean_temp_uploads` existen y están probados, pero nada los invocaba:
el proyecto decidió explícitamente no llevar un programador propio dentro de la app (ver el `help`
de `actualizar_fuentes_bd`) y delegar en el del sistema operativo. Esto es esa delegación, escrita
una vez en vez de por pasos manuales en la interfaz del Programador.

Las dos tareas se registran DIARIAS, incluso la actualización de fuentes: el comando mismo decide
qué dashboards le tocan hoy (`fuente_bd_scheduler.debe_actualizarse_hoy`), así que invocarlo un
martes simplemente no hace nada. Programarlo solo los domingos sería mover esa decisión a un
segundo lugar, y encima uno que no conoce las frecuencias mensuales.

`-StartWhenAvailable` importa más de lo que parece: si a la hora prevista la máquina está apagada,
Windows corre la tarea apenas puede en vez de saltearla. Sin eso, una máquina apagada a las 3 AM
del domingo pierde la actualización semanal entera (ver la advertencia sobre recuperación de
corridas perdidas en `docs/tareas_programadas.md`).

Requiere PowerShell como administrador.

.PARAMETER Hora
Hora de la actualización de fuentes, formato HH:mm. La limpieza de temporales corre 30 minutos
después. Por defecto 03:00.

.PARAMETER Quitar
Elimina las dos tareas en vez de crearlas.

.EXAMPLE
.\programar_tareas.ps1

.EXAMPLE
.\programar_tareas.ps1 -Hora 02:15

.EXAMPLE
.\programar_tareas.ps1 -Quitar
#>
param(
    [string]$Hora = '03:00',
    [switch]$Quitar
)

$ErrorActionPreference = 'Stop'

$PrefijoTarea = 'CMS Dashboards'
$TareaFuentes = "$PrefijoTarea - actualizar fuentes BD"
$TareaLimpieza = "$PrefijoTarea - limpiar temporales"
$Envoltorio = Join-Path $PSScriptRoot 'tarea_programada.ps1'

function Quitar-Tarea($nombre) {
    $existente = Get-ScheduledTask -TaskName $nombre -ErrorAction SilentlyContinue
    if ($existente) {
        Unregister-ScheduledTask -TaskName $nombre -Confirm:$false
        Write-Host "Quitada: $nombre"
    } else {
        Write-Host "No estaba registrada: $nombre"
    }
}

if ($Quitar) {
    Quitar-Tarea $TareaFuentes
    Quitar-Tarea $TareaLimpieza
    return
}

if (-not (Test-Path $Envoltorio)) {
    Write-Error "No se encontró '$Envoltorio'."
    exit 1
}

try {
    $HoraInicio = [datetime]::ParseExact($Hora, 'HH:mm', $null)
} catch {
    Write-Error "La hora '$Hora' no tiene el formato HH:mm."
    exit 1
}

function Registrar-Tarea($nombre, $descripcion, $comando, $argumentosComando, $momento) {
    # `-NoProfile` para no depender del perfil de PowerShell de quien haya instalado la tarea;
    # `-ExecutionPolicy Bypass` porque la política por defecto de la máquina puede impedir correr
    # un .ps1 sin firmar y no corresponde relajarla a nivel de sistema solo para esto.
    $argumentos = "-NoProfile -ExecutionPolicy Bypass -File `"$Envoltorio`" -Comando $comando"
    if ($argumentosComando) { $argumentos += " $argumentosComando" }

    $accion = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $argumentos
    $disparador = New-ScheduledTaskTrigger -Daily -At $momento
    $opciones = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries `
        -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)

    Register-ScheduledTask -TaskName $nombre -Description $descripcion -Action $accion `
        -Trigger $disparador -Settings $opciones -Force | Out-Null
    Write-Host "Registrada: $nombre  ($($momento.ToString('HH:mm')), diaria)"
}

Registrar-Tarea $TareaFuentes `
    'Reaplica el último mapeo confirmado a los dashboards conectados a una vista/procedimiento de base de datos cuya frecuencia venza hoy.' `
    'actualizar_fuentes_bd' $null $HoraInicio

Registrar-Tarea $TareaLimpieza `
    'Borra los archivos temporales de carga de más de 24 horas que ninguna CargaArchivo siga referenciando.' `
    'clean_temp_uploads' '--horas 24' $HoraInicio.AddMinutes(30)

Write-Host ''
Write-Host 'Listo. Para verificar sin esperar a mañana:'
Write-Host "  Start-ScheduledTask -TaskName '$TareaFuentes'"
Write-Host "  Get-ScheduledTaskInfo -TaskName '$TareaFuentes'"
Write-Host 'Y revisá el registro en backend\logs\tareas\.'
