<#
.SYNOPSIS
    Crea el esquema completo (tablas, relaciones, índices y datos semilla) en una
    base ya existente, y deja lista la cuenta de superadministrador.

.DESCRIPTION
    Paso 2 del despliegue. El paso 1 (`sql\01_crear_base.sql`) crea la base vacía y
    la cuenta de acceso; este script corre `manage.py migrate` sobre ella y después
    `crear_superadmin.py`.

    Las tablas NO se crean con un CREATE TABLE propio: las define `migrate` a partir
    de las 65 migraciones del proyecto, que además siembran el rol
    ADMINISTRADOR_GENERAL con sus permisos, la plantilla del correo de recuperación,
    el tema visual por defecto y la plantilla del Directorio de Cartera. Ningún dato
    productivo: ni carteras, ni archivos cargados, ni usuarios más allá del que se
    crea acá.

    Ninguna contraseña se pasa por línea de comandos (quedaría en el historial y en
    la línea de comandos visible del proceso): se piden de forma interactiva o se
    reciben como SecureString, y viajan al proceso de Python por variable de entorno.

.EXAMPLE
    .\02_crear_esquema_y_superadmin.ps1 -DbHost localhost -DbName cmd_dashboards `
        -DbUser cms_dashboards_app -SuperadminEmail dpenarreta@grupolaar.com

    El ejemplo apunta a localhost a propósito: este script ESCRIBE en la base que se le
    indique, así que el valor de muestra nunca debe ser un servidor real. Contra un host
    que no sea local, pide confirmación antes de tocar nada (ver -SinConfirmar).

.NOTES
    Probado en PowerShell 5.1 (el de Windows Server) y en PowerShell 7.
#>

[CmdletBinding()]
param(
    [string]$DbHost = 'localhost',
    [string]$DbPort = '1433',
    [string]$DbName = 'cmd_dashboards',
    [string]$DbUser = 'cms_dashboards_app',
    [SecureString]$DbPassword,

    [string]$SuperadminUsername = 'dpenarreta',
    [string]$SuperadminEmail = 'dpenarreta@grupolaar.com',
    [SecureString]$SuperadminPassword,

    # Cifrado del tráfico hacia SQL Server. Los defaults del código son Encrypt=yes /
    # TrustServerCertificate=no; en una red interna con certificado autofirmado hace
    # falta confiar en él para que la conexión cifrada se establezca igual.
    [string]$DbEncrypt = 'yes',
    [string]$DbTrustServerCertificate = 'yes',

    # Reescribe la contraseña de la cuenta si ya existe. Sin esto, el script se
    # detiene antes de tocar una cuenta existente.
    [switch]$ForzarClave,

    # Solo migra: no toca la cuenta de superadministrador.
    [switch]$SoloMigrar,

    # Salta la confirmación que se pide cuando el destino no es esta máquina. Para uso
    # desatendido; a mano conviene leer lo que el script está por hacer.
    [switch]$SinConfirmar
)

$ErrorActionPreference = 'Stop'

function Convertir-ASecreto([SecureString]$valor) {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($valor)
    try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

$raizRepo = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raizRepo 'backend'
$python = Join-Path $backend '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) { throw "No encontré Python: ni $backend\.venv\Scripts\python.exe ni `python` en el PATH." }
    Write-Warning "Sin entorno virtual en backend\.venv — usando $python"
}

# --- Red de contención: este script ESCRIBE en la base de destino --------------
# Contra un servidor que no sea esta máquina, hay que confirmar a mano. Crear el esquema
# sobre una base equivocada es trabajoso de revertir, y la diferencia entre la base de
# pruebas y una productiva suele ser una palabra en la línea de comandos.
$esLocal = $DbHost -in @('localhost', '127.0.0.1', '.', '(local)', $env:COMPUTERNAME)
if (-not $esLocal -and -not $SinConfirmar) {
    Write-Host ""
    Write-Host "  DESTINO NO LOCAL" -ForegroundColor Yellow
    Write-Host "  Se va a crear el esquema en:  $DbHost / $DbName" -ForegroundColor Yellow
    Write-Host ""
    $respuesta = Read-Host "  Escribí el nombre de la base para confirmar"
    if ($respuesta -ne $DbName) {
        Write-Host "No coincide. No se tocó nada." -ForegroundColor Red
        return
    }
}

if (-not $DbPassword) { $DbPassword = Read-Host "Contraseña de SQL Server para $DbUser" -AsSecureString }
if (-not $SoloMigrar -and -not $SuperadminPassword) {
    $SuperadminPassword = Read-Host "Contraseña para el superadministrador $SuperadminEmail" -AsSecureString
}

# --- Entorno del proceso de Python -----------------------------------------
# Se fija acá y no en un .env para que este script sirva igual antes de que el .env
# de producción exista. Son variables DEL PROCESO: mueren cuando termina.
$env:DJANGO_SETTINGS_MODULE = 'config.settings'
$env:DEBUG = 'False'
$env:DB_ENGINE = 'mssql'
$env:DB_HOST = $DbHost
$env:DB_PORT = $DbPort
$env:DB_NAME = $DbName
$env:DB_USER = $DbUser
$env:DB_PASSWORD = Convertir-ASecreto $DbPassword
$env:DB_ENCRYPT = $DbEncrypt
$env:DB_TRUST_SERVER_CERTIFICATE = $DbTrustServerCertificate

# Con DEBUG=False el arranque exige claves reales. Si el .env de producción todavía
# no está armado, se generan unas efímeras SOLO para esta corrida: migrar no firma
# nada que sobreviva al proceso, así que no queda nada atado a ellas. Las de verdad
# van en el .env que usa el servidor web.
if (-not $env:SECRET_KEY) {
    $env:SECRET_KEY = & $python -c "import secrets; print(secrets.token_urlsafe(64))"
    Write-Host "SECRET_KEY efímera generada para esta corrida (la definitiva va en el .env)." -ForegroundColor DarkGray
}
if (-not $env:JWT_SECRET_KEY) {
    $env:JWT_SECRET_KEY = & $python -c "import secrets; print(secrets.token_urlsafe(64))"
}

Push-Location $backend
try {
    Write-Host ""
    Write-Host "== Verificando la conexión a $DbHost/$DbName ==" -ForegroundColor Cyan
    & $python manage.py check --database default
    if ($LASTEXITCODE -ne 0) { throw "La verificación de Django falló (código $LASTEXITCODE)." }

    Write-Host ""
    Write-Host "== Creando el esquema (migrate) ==" -ForegroundColor Cyan
    & $python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw "migrate falló (código $LASTEXITCODE)." }

    Write-Host ""
    Write-Host "== Migraciones aplicadas ==" -ForegroundColor Cyan
    $plan = & $python manage.py showmigrations --plan
    $aplicadas = ($plan | Select-String -SimpleMatch '[X]').Count
    $pendientes = ($plan | Select-String -SimpleMatch '[ ]').Count
    Write-Host "  $aplicadas aplicadas, $pendientes pendientes"
    if ($pendientes -ne 0) { throw "Quedaron $pendientes migraciones sin aplicar." }
}
finally {
    Pop-Location
}

if ($SoloMigrar) {
    Write-Host ""
    Write-Host "Esquema listo. No se tocó la cuenta de superadministrador (-SoloMigrar)." -ForegroundColor Green
    return
}

Write-Host ""
Write-Host "== Superadministrador ==" -ForegroundColor Cyan
$env:SUPERADMIN_USERNAME = $SuperadminUsername
$env:SUPERADMIN_EMAIL = $SuperadminEmail
$env:SUPERADMIN_PASSWORD = Convertir-ASecreto $SuperadminPassword
if ($ForzarClave) { $env:SUPERADMIN_FORZAR = '1' }

try {
    & $python (Join-Path $PSScriptRoot 'crear_superadmin.py')
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear la cuenta (código $LASTEXITCODE)." }
}
finally {
    # La contraseña deja de estar en memoria del proceso apenas termina, pero no hay
    # motivo para que siga disponible mientras la consola siga abierta.
    Remove-Item Env:SUPERADMIN_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:DB_PASSWORD -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Base lista: esquema completo y cuenta de administrador creada." -ForegroundColor Green
Write-Host "Siguiente paso: el .env de producción y la publicación en IIS." -ForegroundColor Green
