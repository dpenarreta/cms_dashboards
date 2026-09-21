<#
.SYNOPSIS
    Publica la aplicación en IIS: copia el código, arma el entorno de Python, deja los
    web.config en su lugar y crea el sitio con su aplicación y su directorio virtual.

.DESCRIPTION
    Se ejecuta EN EL SERVIDOR (10.0.2.33), en una consola de PowerShell ABIERTA COMO
    ADMINISTRADOR: crear sitios en IIS y dar permisos NTFS lo exige.

    Qué deja montado:

        <sitio>/            -> frontend compilado (Vite)        [archivos estáticos]
        <sitio>/api         -> aplicación IIS con el backend    [HttpPlatformHandler]
        <sitio>/media       -> directorio virtual               [archivos subidos]

    Es idempotente: volver a ejecutarlo actualiza el código y la configuración sin
    recrear el sitio. Para una actualización de rutina alcanza con -SoloCodigo.

.PARAMETER Origen
    Carpeta del repositorio (la que contiene backend\ y frontend\). Si el repositorio no
    está en el servidor, hay que copiarlo antes: este script no descarga nada.

.PARAMETER Destino
    Dónde queda instalada la aplicación. Por defecto C:\inetpub\cms_dashboards.

.PARAMETER Puerto
    Puerto del binding del sitio. Por defecto 50810, porque el 80 de 10.0.2.33 ya está
    ocupado por otro sitio.

.EXAMPLE
    .\publicar.ps1 -Origen C:\deploy\cms_dashboards -AbrirFirewall

.EXAMPLE
    .\publicar.ps1 -Origen C:\deploy\cms_dashboards -SoloCodigo

.NOTES
    Requisitos en el servidor, verificados antes de tocar nada:
      - IIS con el módulo de administración (WebAdministration)
      - HttpPlatformHandler 1.2   https://www.iis.net/downloads/microsoft/httpplatformhandler
      - URL Rewrite 2.1           https://www.iis.net/downloads/microsoft/url-rewrite
      - Python 3.12 instalado para todos los usuarios
      - ODBC Driver 17 for SQL Server
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Origen,

    [string]$Destino = 'C:\inetpub\cms_dashboards',
    [string]$NombreSitio = 'CMS Dashboards',
    [int]$Puerto = 50810,
    [string]$NombreHost = '',
    [string]$PoolAplicacion = 'CMSDashboardsPool',

    # Abre el puerto en el firewall de Windows (entrante, TCP). Sin esto, el sitio
    # responde en el servidor pero no desde la red.
    [switch]$AbrirFirewall,

    # Actualiza código y configuración, sin tocar IIS ni el entorno virtual.
    [switch]$SoloCodigo,

    # Ruta al .env de producción. Si se omite, se busca en deploy\.env.produccion del
    # origen y, si tampoco está, se avisa y se sigue (hay que ponerlo a mano después).
    [string]$ArchivoEnv = ''
)

$ErrorActionPreference = 'Stop'

function Paso($texto) { Write-Host "`n== $texto ==" -ForegroundColor Cyan }
function Ok($texto)   { Write-Host "   $texto" -ForegroundColor Green }
function Aviso($texto){ Write-Host "   $texto" -ForegroundColor Yellow }

# ---------------------------------------------------------------------------
# Comprobaciones previas
# ---------------------------------------------------------------------------
Paso 'Comprobando requisitos'

$esAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $esAdmin) {
    throw 'Hay que ejecutar esta consola como administrador: crear sitios en IIS y asignar permisos NTFS lo exige.'
}
Ok 'Consola elevada'

Import-Module WebAdministration -ErrorAction Stop
Ok 'Modulo WebAdministration disponible'

# Los dos módulos nativos se verifican leyendo la configuración de IIS, no buscando
# archivos: es la única forma fiable de saber si están REGISTRADOS y no solo copiados.
$modulos = (Get-WebConfiguration -Filter '/system.webServer/globalModules' -PSPath 'IIS:\').Collection.Name
if ($modulos -notcontains 'httpPlatformHandler') {
    throw @'
Falta el modulo HttpPlatformHandler, que es lo que arranca el proceso de Python.
Descarga: https://www.iis.net/downloads/microsoft/httpplatformhandler
Instalalo, cerra y volve a abrir esta consola, y ejecuta de nuevo.
'@
}
Ok 'HttpPlatformHandler instalado'

if ($modulos -notcontains 'RewriteModule') {
    throw @'
Falta el modulo URL Rewrite, necesario para que las rutas del frontend (React Router)
devuelvan el index.html en vez de un 404.
Descarga: https://www.iis.net/downloads/microsoft/url-rewrite
'@
}
Ok 'URL Rewrite instalado'

$python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $python) {
    $python = Get-ChildItem 'C:\Program Files\Python*\python.exe', 'C:\Python*\python.exe' -ErrorAction SilentlyContinue |
              Select-Object -First 1 -ExpandProperty FullName
}
if (-not $python) { throw 'No encontre Python en el servidor. Instalalo para todos los usuarios y volve a ejecutar.' }
$version = & $python --version
Ok "Python: $version ($python)"

# Se acepta el 17 o el 18: `pyodbc` busca el driver por su nombre exacto, pero cual de
# los dos haya da igual mientras el .env lo declare con DB_ODBC_DRIVER. Exigir el 17
# obligaria a instalar una version vieja en un servidor que ya tiene la nueva.
$driversOdbc = (Get-OdbcDriver -ErrorAction SilentlyContinue).Name
$driverElegido = @('ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server') |
                 Where-Object { $driversOdbc -contains $_ } | Select-Object -First 1
if (-not $driverElegido) {
    throw @'
No hay ningun ODBC Driver 17 ni 18 for SQL Server instalado: sin uno de los dos, la
aplicacion no puede conectarse a la base.

Descarga: https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server

(No alcanza con que otras aplicaciones del servidor usen SQL Server: las apps .NET se
conectan con SqlClient, que no necesita ODBC. Python si.)
'@
}
Ok "ODBC disponible: $driverElegido"

# Si el .env declara un driver que no esta instalado, la aplicacion arranca pero falla al
# primer acceso a la base, con un error de pyodbc poco claro. Mejor avisar ahora.
$envParaRevisar = if ($ArchivoEnv) { $ArchivoEnv } else { Join-Path $Origen 'deploy\.env.produccion' }
if (Test-Path $envParaRevisar) {
    $declarado = (Get-Content $envParaRevisar | Select-String '^DB_ODBC_DRIVER=') -replace '^DB_ODBC_DRIVER=', ''
    if ($declarado) {
        $declarado = $declarado.Trim()
        if ($driversOdbc -contains $declarado) { Ok "El .env declara '$declarado' y esta instalado" }
        else { Aviso "El .env declara DB_ODBC_DRIVER='$declarado', que NO esta instalado. Instalado: $driverElegido. Corregi el .env antes de publicar." }
    }
}

# El rango de puertos dinámicos de Windows arranca en 49152: cualquier puerto por
# encima de ese número puede ser tomado por una conexión saliente efímera ANTES de que
# IIS lo reserve. El síntoma es desconcertante — el sitio funciona, el servidor se
# reinicia y el sitio ya no arranca porque "el puerto está en uso" — y es intermitente.
# La reserva le dice a Windows que no lo reparta.
# `netsh` ya devuelve un arreglo de líneas: se recorren tal cual, sin partir texto. La
# expresión pide "dos puntos, espacios, dígitos Y FIN DE LÍNEA" — sin el fin de línea, en
# la salida en español "Puerto de inicio : 49152" seguido de "Número de puertos : 16384"
# se capturaba como un solo valor y la conversión a entero fallaba.
$inicioDinamico = 49152   # el default de Windows; se confirma con lo que informe netsh
foreach ($linea in (netsh int ipv4 show dynamicport tcp)) {
    if ($linea -match ':\s*(\d+)\s*$') { $inicioDinamico = [int]$Matches[1]; break }
}

if ($Puerto -ge $inicioDinamico) {
    $yaReservado = $false
    foreach ($linea in (netsh int ipv4 show excludedportrange protocol=tcp)) {
        if ($linea -match '^\s*(\d+)\s+(\d+)') {
            if ([int]$Matches[1] -le $Puerto -and [int]$Matches[2] -ge $Puerto) { $yaReservado = $true; break }
        }
    }
    if ($yaReservado) {
        Ok "Puerto $Puerto ya reservado frente al rango dinamico"
    } else {
        Aviso "El puerto $Puerto esta dentro del rango dinamico de Windows (desde $inicioDinamico): se reserva para que nadie mas lo tome."
        netsh int ipv4 add excludedportrange protocol=tcp startport=$Puerto numberofports=1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Ok "Puerto $Puerto reservado" }
        else { Aviso "No se pudo reservar el puerto $Puerto (solo se puede con el puerto libre). Si el sitio no arranca despues de un reinicio, esta es la causa: netsh int ipv4 add excludedportrange protocol=tcp startport=$Puerto numberofports=1" }
    }
}

if (-not (Test-Path (Join-Path $Origen 'backend\manage.py'))) {
    throw "En $Origen no encuentro backend\manage.py. ¿Es la carpeta del repositorio?"
}
$distOrigen = Join-Path $Origen 'frontend\dist'
if (-not (Test-Path (Join-Path $distOrigen 'index.html'))) {
    throw @"
No encuentro el frontend compilado en $distOrigen.
Compilalo antes (en tu maquina o en el servidor, donde haya Node):
    cd frontend
    npm ci
    npm run build
y copia la carpeta dist\ junto con el resto del repositorio.
"@
}
Ok 'Origen valido (backend y frontend compilado)'

# ---------------------------------------------------------------------------
# Carpetas
# ---------------------------------------------------------------------------
Paso 'Preparando carpetas'
$destBackend  = Join-Path $Destino 'backend'
$destFrontend = Join-Path $Destino 'frontend'
$destLogs     = Join-Path $Destino 'logs'
foreach ($ruta in @($Destino, $destBackend, $destFrontend, $destLogs)) {
    if (-not (Test-Path $ruta)) { New-Item -ItemType Directory -Path $ruta -Force | Out-Null }
}
Ok $Destino

# ---------------------------------------------------------------------------
# Código
# ---------------------------------------------------------------------------
Paso 'Copiando el backend'
# /MIR replica y borra lo que sobra, pero se excluyen tres cosas que viven en el destino
# y no en el origen: el entorno virtual, los archivos subidos por los usuarios y el .env.
# Sin esas exclusiones, cada despliegue borraria los archivos de los dashboards.
$excluirDirs = @('.venv', '__pycache__', 'media', 'logs', '.pytest_cache')
$argsRobocopy = @(
    (Join-Path $Origen 'backend'), $destBackend, '/MIR', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:2', '/W:2',
    '/XD') + $excluirDirs + @('/XF', '.env', '*.pyc')
& robocopy.exe @argsRobocopy | Out-Null
# Robocopy usa códigos de salida de mapa de bits: 0-7 es éxito, 8 o más es error real.
if ($LASTEXITCODE -ge 8) { throw "robocopy fallo al copiar el backend (codigo $LASTEXITCODE)." }
Ok 'Backend copiado'

Paso 'Copiando el frontend compilado'
& robocopy.exe $distOrigen $destFrontend '/MIR' '/NFL' '/NDL' '/NJH' '/NJS' '/NP' '/R:2' '/W:2' | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy fallo al copiar el frontend (codigo $LASTEXITCODE)." }
Ok 'Frontend copiado'

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
Paso 'Configuracion (.env y web.config)'
if (-not $ArchivoEnv) { $ArchivoEnv = Join-Path $Origen 'deploy\.env.produccion' }
$destEnv = Join-Path $destBackend '.env'
if (Test-Path $ArchivoEnv) {
    # Un despliegue anterior deja el .env con la herencia cortada y permisos restringidos; sin
    # devolvérsela, `Copy-Item` no puede reemplazarlo ni siquiera como administrador ("Acceso
    # denegado"). Se restaura acá y se vuelve a restringir más abajo, ya con el archivo nuevo.
    if (Test-Path $destEnv) {
        $aclPrevia = Get-Acl $destEnv
        $aclPrevia.SetAccessRuleProtection($false, $true)
        Set-Acl $destEnv $aclPrevia
    }
    Copy-Item $ArchivoEnv $destEnv -Force
    Ok ".env instalado desde $ArchivoEnv"
} elseif (Test-Path $destEnv) {
    Aviso ".env no provisto; se conserva el que ya estaba en el servidor."
} else {
    Aviso "FALTA el .env. La aplicacion no va a arrancar hasta que copies uno a $destEnv"
}

# Las rutas absolutas del web.config del backend dependen de donde se instale.
$plantillaBackend = Join-Path $PSScriptRoot 'backend-web.config'
$contenido = (Get-Content $plantillaBackend -Raw).
    Replace('__RUTA_PYTHON__', (Join-Path $destBackend '.venv\Scripts\python.exe')).
    Replace('__RUTA_LOGS__', $destLogs)
Set-Content -Path (Join-Path $destBackend 'web.config') -Value $contenido -Encoding UTF8
Ok 'web.config del backend generado'

Copy-Item (Join-Path $PSScriptRoot 'frontend-web.config') (Join-Path $destFrontend 'web.config') -Force
Ok 'web.config del frontend instalado'

# ---------------------------------------------------------------------------
# Entorno de Python
# ---------------------------------------------------------------------------
if (-not $SoloCodigo) {
    Paso 'Entorno virtual y dependencias'
    $venvPython = Join-Path $destBackend '.venv\Scripts\python.exe'
    if (-not (Test-Path $venvPython)) {
        & $python -m venv (Join-Path $destBackend '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno virtual.' }
        Ok 'Entorno virtual creado'
    }
    & $venvPython -m pip install --upgrade pip --quiet
    & $venvPython -m pip install -r (Join-Path $destBackend 'requirements.txt') --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la instalacion de dependencias.' }
    Ok 'Dependencias instaladas'

    Paso 'Verificando la configuracion contra la base'
    Push-Location $destBackend
    try {
        & $venvPython manage.py check --database default
        if ($LASTEXITCODE -ne 0) { throw 'manage.py check fallo: revisa el .env y la conexion a la base.' }
        Ok 'Django arranca y la base responde'

        $plan = & $venvPython manage.py showmigrations --plan
        $pendientes = ($plan | Select-String -SimpleMatch '[ ]').Count
        if ($pendientes -gt 0) {
            Aviso "Hay $pendientes migraciones pendientes. Aplicalas con: manage.py migrate"
        } else {
            Ok 'Sin migraciones pendientes'
        }
    }
    finally { Pop-Location }
}

# ---------------------------------------------------------------------------
# IIS
# ---------------------------------------------------------------------------
if (-not $SoloCodigo) {
    Paso 'Configurando IIS'

    if (-not (Test-Path "IIS:\AppPools\$PoolAplicacion")) {
        New-WebAppPool -Name $PoolAplicacion | Out-Null
        Ok "Grupo de aplicaciones $PoolAplicacion creado"
    }
    # Sin código administrado: todo lo sirve el proceso de Python o el manejador estático.
    Set-ItemProperty "IIS:\AppPools\$PoolAplicacion" -Name managedRuntimeVersion -Value ''
    # El reciclado por tiempo corta peticiones en curso sin ganar nada acá: el proceso de
    # Python lo administra HttpPlatformHandler, no el pool.
    Set-ItemProperty "IIS:\AppPools\$PoolAplicacion" -Name recycling.periodicRestart.time -Value ([TimeSpan]::Zero)
    Set-ItemProperty "IIS:\AppPools\$PoolAplicacion" -Name processModel.idleTimeout -Value ([TimeSpan]::Zero)
    Set-ItemProperty "IIS:\AppPools\$PoolAplicacion" -Name startMode -Value 'AlwaysRunning'
    Ok 'Grupo de aplicaciones configurado'

    if (-not (Test-Path "IIS:\Sites\$NombreSitio")) {
        $parametros = @{ Name = $NombreSitio; PhysicalPath = $destFrontend; ApplicationPool = $PoolAplicacion; Port = $Puerto }
        if ($NombreHost) { $parametros['HostHeader'] = $NombreHost }
        New-Website @parametros | Out-Null
        Ok "Sitio '$NombreSitio' creado en el puerto $Puerto"
    } else {
        Set-ItemProperty "IIS:\Sites\$NombreSitio" -Name physicalPath -Value $destFrontend
        Ok "Sitio '$NombreSitio' ya existia: se actualizo su ruta"
    }

    if (-not (Get-WebApplication -Site $NombreSitio -Name 'api' -ErrorAction SilentlyContinue)) {
        New-WebApplication -Site $NombreSitio -Name 'api' -PhysicalPath $destBackend -ApplicationPool $PoolAplicacion | Out-Null
        Ok 'Aplicacion /api creada'
    } else {
        Set-ItemProperty "IIS:\Sites\$NombreSitio\api" -Name physicalPath -Value $destBackend
        Ok 'Aplicacion /api actualizada'
    }

    # Django no sirve /media fuera de DEBUG (a proposito): lo sirve IIS como archivos
    # estaticos. Sin esto, los avatares y los archivos de los dashboards dan 404.
    $destMedia = Join-Path $destBackend 'media'
    if (-not (Test-Path $destMedia)) { New-Item -ItemType Directory -Path $destMedia -Force | Out-Null }
    if (-not (Get-WebVirtualDirectory -Site $NombreSitio -Name 'media' -ErrorAction SilentlyContinue)) {
        New-WebVirtualDirectory -Site $NombreSitio -Name 'media' -PhysicalPath $destMedia | Out-Null
        Ok 'Directorio virtual /media creado'
    }

    if ($AbrirFirewall) {
        Paso 'Firewall'
        $nombreRegla = "CMS Dashboards (TCP $Puerto)"
        if (-not (Get-NetFirewallRule -DisplayName $nombreRegla -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -DisplayName $nombreRegla -Direction Inbound -Protocol TCP `
                -LocalPort $Puerto -Action Allow -Profile Domain,Private | Out-Null
            Ok "Regla creada: $nombreRegla (perfiles Dominio y Privado)"
        } else {
            Ok "La regla '$nombreRegla' ya existia"
        }
    } else {
        Aviso "Firewall sin tocar. Si el sitio responde en el servidor pero no desde la red, volve a ejecutar con -AbrirFirewall"
    }

    Paso 'Permisos'
    # El proceso de Python corre como la identidad del pool, y necesita ESCRIBIR en las
    # carpetas de archivos subidos y de logs. Sobre el codigo, solo lectura.
    $identidad = "IIS AppPool\$PoolAplicacion"
    foreach ($carpeta in @($destMedia, $destLogs)) {
        $acl = Get-Acl $carpeta
        $regla = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $identidad, 'Modify', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
        $acl.SetAccessRule($regla)
        Set-Acl $carpeta $acl
        Ok "Escritura para $identidad en $carpeta"
    }
    # El .env tiene credenciales: lo lee el proceso, no hace falta que lo lea nadie más.
    if (Test-Path $destEnv) {
        $acl = Get-Acl $destEnv
        $acl.SetAccessRuleProtection($true, $false)
        # Los grupos integrados se identifican por SID y no por nombre: en un Windows en
        # español el grupo es "Administradores", no "Administrators", y AddAccessRule
        # falla con "No se pudieron convertir algunas o todas las referencias de
        # identidad". Los SID son los mismos en cualquier idioma.
        #   S-1-5-32-544 = Administradores locales
        #   S-1-5-18     = SYSTEM
        # El proceso de la aplicación solo LEE el archivo; Administradores y SYSTEM necesitan
        # control total para poder actualizarlo. Dárselo también en 'Read' dejaba el .env
        # imposible de reemplazar en el siguiente despliegue, incluso con permisos de
        # administrador.
        $permisos = @(
            @{ Cuenta = (New-Object System.Security.Principal.NTAccount($identidad)); Derecho = 'Read' },
            @{ Cuenta = (New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')); Derecho = 'FullControl' },
            @{ Cuenta = (New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')); Derecho = 'FullControl' }
        )
        foreach ($permiso in $permisos) {
            $acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule(
                $permiso.Cuenta, $permiso.Derecho, 'Allow')))
        }
        Set-Acl $destEnv $acl
        Ok 'Permisos del .env restringidos'
    }
}

# ---------------------------------------------------------------------------
# Arranque y prueba
# ---------------------------------------------------------------------------
Paso 'Reiniciando y probando'
Restart-WebAppPool -Name $PoolAplicacion
Start-Sleep -Seconds 3

$baseUrl = if ($NombreHost) { "http://$NombreHost" } else { "http://localhost:$Puerto" }
if ($Puerto -ne 80 -and $NombreHost) { $baseUrl = "http://${NombreHost}:$Puerto" }

$fallos = 0
try {
    $r = Invoke-WebRequest -Uri "$baseUrl/" -UseBasicParsing -TimeoutSec 30
    if ($r.Content -match '<div id="root"') { Ok "Frontend responde ($($r.StatusCode))" }
    else { Aviso "El frontend responde $($r.StatusCode) pero el HTML no parece el del SPA"; $fallos++ }
} catch { Aviso "Frontend: $($_.Exception.Message)"; $fallos++ }

try {
    # Se espera 400: el endpoint existe y valida el cuerpo vacio. Un 200 seria raro y un
    # 404 significaria que /api no esta enrutando al backend.
    Invoke-WebRequest -Uri "$baseUrl/api/auth/login" -Method POST -Body '{}' `
        -ContentType 'application/json' -UseBasicParsing -TimeoutSec 60 | Out-Null
    Aviso 'La API respondio 200 a un login vacio, lo que no deberia pasar'; $fallos++
} catch {
    $codigo = $_.Exception.Response.StatusCode.value__
    if ($codigo -eq 400) { Ok 'La API responde y valida (400 al login vacio, como corresponde)' }
    elseif ($codigo -eq 404) { Aviso 'La API devuelve 404: /api no esta llegando al backend. Revisa el log en ' + $destLogs; $fallos++ }
    else { Aviso "La API respondio $codigo. Revisa el log en $destLogs"; $fallos++ }
}

Write-Host ''
if ($fallos -eq 0) {
    Write-Host "Publicacion terminada. La aplicacion esta en $baseUrl" -ForegroundColor Green
} else {
    Write-Host "Publicacion terminada con $fallos comprobacion(es) en rojo." -ForegroundColor Yellow
    Write-Host "El log del backend esta en $destLogs (lo escribe HttpPlatformHandler)." -ForegroundColor Yellow
}
