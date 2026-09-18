<#
.SYNOPSIS
    Despliega el proyecto en 10.0.2.33 de punta a punta, desde esta máquina.

.DESCRIPTION
    Hace las cuatro cosas seguidas: copia el paquete al servidor, lo descomprime,
    ejecuta la publicación en IIS y comprueba que la aplicación responda.

    HAY QUE EJECUTARLO CON UNA CUENTA QUE TENGA PERMISOS EN EL SERVIDOR — la misma con
    la que abriste la consola donde `\\10.0.2.33\c$` es accesible. El script no pide
    credenciales: usa la identidad de la consola.

    Si esa consola no llega al servidor, el script se detiene en la primera comprobación
    y dice exactamente qué falta, sin haber tocado nada.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\desplegar_remoto.ps1

    Así, y no con `.\desplegar_remoto.ps1` a secas: por defecto Windows no permite
    ejecutar scripts (política Restricted) y responde "la ejecución de scripts está
    deshabilitada en este sistema". El Bypass vale solo para ese proceso.

.EXAMPLE
    .\desplegar_remoto.ps1 -SoloCopiar

    Copia y descomprime, sin publicar. Útil si preferís lanzar la publicación a mano por
    RDP, o si todavía faltan los módulos de IIS.
#>

[CmdletBinding()]
param(
    [string]$Servidor = '10.0.2.33',
    [string]$Paquete = 'C:\Users\itinnouio\Desktop\cms_dashboards_deploy.zip',
    [string]$CarpetaRemota = 'C:\deploy\cms_dashboards',
    [int]$Puerto = 50810,
    [switch]$SoloCopiar
)

$ErrorActionPreference = 'Stop'
function Paso($t) { Write-Host "`n== $t ==" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "   $t" -ForegroundColor Green }
function Mal($t)  { Write-Host "   $t" -ForegroundColor Red }

# ---------------------------------------------------------------------------
Paso 'Comprobando acceso al servidor'

Write-Host "   corriendo como: $(whoami)"

$rutaUnc = "\\$Servidor\c$"
# Test-Path LANZA excepción cuando el acceso está denegado (no devuelve $false), y con
# ErrorActionPreference='Stop' eso mata el script con un volcado ilegible justo en el
# caso más común de todos. Se captura para poder explicar qué hacer.
$hayAcceso = $false
try { $hayAcceso = Test-Path $rutaUnc -ErrorAction Stop } catch { $hayAcceso = $false }
if (-not $hayAcceso) {
    Mal "No puedo llegar a $rutaUnc con esta cuenta."
    Write-Host @"

   Esta consola no tiene permisos en el servidor. Abri PowerShell con la cuenta
   administradora del servidor (o ejecuta antes:  net use $rutaUnc /user:DOMINIO\admin * )
   y volve a correr este script.
"@ -ForegroundColor Yellow
    exit 1
}
Ok "$rutaUnc accesible"

if (-not (Test-Path $Paquete)) { throw "No encuentro el paquete en $Paquete" }
Ok "Paquete: $Paquete ({0:N1} MB)" -f ((Get-Item $Paquete).Length / 1MB)

# WinRM solo hace falta para publicar; para copiar, no.
$tieneWinRM = $false
try {
    Invoke-Command -ComputerName $Servidor -ScriptBlock { 1 } -ErrorAction Stop | Out-Null
    $tieneWinRM = $true
    Ok 'WinRM disponible (se puede publicar en remoto)'
} catch {
    Write-Host '   WinRM no disponible con esta cuenta: se copiara igual, pero la publicacion habra que lanzarla por RDP.' -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
Paso 'Copiando el paquete'

$destinoUnc = "\\$Servidor\c$\deploy"
if (-not (Test-Path $destinoUnc)) { New-Item -ItemType Directory -Path $destinoUnc -Force | Out-Null }
Copy-Item $Paquete "$destinoUnc\cms_dashboards_deploy.zip" -Force
Ok "Copiado a $destinoUnc"

# ---------------------------------------------------------------------------
Paso 'Descomprimiendo en el servidor'

# Se descomprime EN el servidor y no sobre la ruta de red: expandir por SMB manda cada
# archivo de a uno por la red y tarda muchisimo mas.
if ($tieneWinRM) {
    Invoke-Command -ComputerName $Servidor -ArgumentList $CarpetaRemota -ScriptBlock {
        param($carpeta)
        $zip = 'C:\deploy\cms_dashboards_deploy.zip'
        if (Test-Path $carpeta) { Remove-Item "$carpeta\*" -Recurse -Force -ErrorAction SilentlyContinue }
        Expand-Archive -Path $zip -DestinationPath $carpeta -Force
        "   descomprimido en $carpeta ($((Get-ChildItem $carpeta -Recurse -File).Count) archivos)"
    } | ForEach-Object { Write-Host $_ -ForegroundColor Green }
} else {
    Expand-Archive -Path "$destinoUnc\cms_dashboards_deploy.zip" `
                   -DestinationPath "\\$Servidor\c$\deploy\cms_dashboards" -Force
    Ok 'Descomprimido (por red, puede haber tardado)'
}

if ($SoloCopiar -or -not $tieneWinRM) {
    Write-Host ''
    Write-Host "Archivos en el servidor, en $CarpetaRemota" -ForegroundColor Green
    Write-Host 'Para publicar, por RDP y en PowerShell como administrador:' -ForegroundColor Yellow
    # Con -ExecutionPolicy Bypass y no `.\publicar.ps1` a secas: la política por defecto
    # de Windows rechaza ejecutar scripts, y el error llega justo al final de todo el
    # trabajo de copia.
    Write-Host "    powershell -ExecutionPolicy Bypass -File $CarpetaRemota\deploy\iis\publicar.ps1 -Origen $CarpetaRemota -AbrirFirewall" -ForegroundColor Yellow
    exit 0
}

# ---------------------------------------------------------------------------
Paso 'Verificando requisitos en el servidor'

$requisitos = Invoke-Command -ComputerName $Servidor -ScriptBlock {
    $modulos = @()
    try {
        Import-Module WebAdministration -ErrorAction Stop
        $modulos = (Get-WebConfiguration -Filter '/system.webServer/globalModules' -PSPath 'IIS:\').Collection.Name
    } catch {}
    [pscustomobject]@{
        IIS        = $modulos.Count -gt 0
        HttpPlat   = $modulos -contains 'httpPlatformHandler'
        Rewrite    = $modulos -contains 'RewriteModule'
        Python     = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
        Odbc       = [bool](Get-OdbcDriver -Name 'ODBC Driver 17 for SQL Server' -ErrorAction SilentlyContinue)
    }
}

$faltantes = @()
if ($requisitos.IIS)      { Ok 'IIS con modulo de administracion' } else { Mal 'IIS no disponible'; $faltantes += 'IIS' }
if ($requisitos.HttpPlat) { Ok 'HttpPlatformHandler' } else { Mal 'FALTA HttpPlatformHandler -> https://www.iis.net/downloads/microsoft/httpplatformhandler'; $faltantes += 'HttpPlatformHandler' }
if ($requisitos.Rewrite)  { Ok 'URL Rewrite' } else { Mal 'FALTA URL Rewrite -> https://www.iis.net/downloads/microsoft/url-rewrite'; $faltantes += 'URL Rewrite' }
if ($requisitos.Python)   { Ok "Python: $($requisitos.Python)" } else { Mal 'FALTA Python 3.12 (instalar para todos los usuarios)'; $faltantes += 'Python' }
if ($requisitos.Odbc)     { Ok 'ODBC Driver 17 for SQL Server' } else { Mal 'FALTA ODBC Driver 17 for SQL Server'; $faltantes += 'ODBC 17' }

if ($faltantes.Count) {
    Write-Host ''
    Write-Host "Falta instalar en el servidor: $($faltantes -join ', ')" -ForegroundColor Yellow
    Write-Host 'Los archivos ya estan copiados. Instala lo que falta y volve a ejecutar este script.' -ForegroundColor Yellow
    exit 1
}

# ---------------------------------------------------------------------------
Paso 'Publicando en IIS'

Invoke-Command -ComputerName $Servidor -ArgumentList $CarpetaRemota, $Puerto -ScriptBlock {
    param($carpeta, $puerto)
    # En un proceso aparte con -ExecutionPolicy Bypass: si el servidor tiene la política
    # restrictiva por defecto (Restricted / AllSigned), un `& script.ps1` se rechaza con
    # "la ejecución de scripts está deshabilitada en este sistema". Bypass aplica SOLO a
    # este proceso: no cambia la configuración de la máquina.
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$carpeta\deploy\iis\publicar.ps1" `
        -Origen $carpeta -Puerto $puerto -AbrirFirewall
} | ForEach-Object { Write-Host $_ }

# ---------------------------------------------------------------------------
Paso 'Comprobando desde esta maquina'

$url = "http://${Servidor}:$Puerto"
try {
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 30
    Ok "El sitio responde ($($r.StatusCode)) en $url"
} catch {
    Mal "El sitio no responde en $url : $($_.Exception.Message)"
    Write-Host "   Revisa el log del backend en \\$Servidor\c`$\inetpub\cms_dashboards\logs" -ForegroundColor Yellow
}

Write-Host ''
Write-Host "Listo. Entra a $url con dpenarreta@grupolaar.com" -ForegroundColor Green
Write-Host 'Falta todavia: sembrar el Directorio de Cartera y registrar las tareas programadas (ver docs/despliegue-iis.md).' -ForegroundColor Yellow
