-- ============================================================================
-- Crea la base de la aplicación y su cuenta de acceso. NO crea las tablas.
--
-- Las tablas y sus relaciones las crea `manage.py migrate` (paso 2,
-- `deploy/02_crear_esquema_y_superadmin.ps1`), que es la única fuente de verdad
-- del esquema: son 65 migraciones, varias de ellas de datos (el rol
-- ADMINISTRADOR_GENERAL con sus permisos, la plantilla del correo de
-- recuperación, el tema por defecto, la plantilla del Directorio de Cartera).
-- Un CREATE TABLE escrito a mano dejaría `django_migrations` vacío y la primera
-- migración futura fallaría al chocar contra tablas que ya existen.
--
-- Uso (desde el servidor, con una cuenta que pueda crear bases):
--
--   sqlcmd -S localhost -E ^
--     -v DbName="cmd_dashboards" DbLogin="cms_dashboards_app" DbPassword="<clave>" ^
--     -i 01_crear_base.sql
--
-- Es idempotente: se puede volver a ejecutar sin romper nada.
-- ============================================================================

SET NOCOUNT ON;
GO

-- ---------------------------------------------------------------------------
-- Las variables tienen que estar sustituidas
-- ---------------------------------------------------------------------------
-- `$(DbName)` es una variable de sqlcmd. Si este archivo se ejecuta en SSMS con el
-- modo SQLCMD APAGADO (Consulta > Modo SQLCMD), el texto no se sustituye y se toma
-- literal: el resultado es una base llamada, tal cual, `$(DbName)`. Ya pasó.
IF CHARINDEX('$' + '(', '$(DbName)') > 0 OR CHARINDEX('$' + '(', '$(DbLogin)') > 0
BEGIN
    PRINT '';
    PRINT '!! Las variables no se sustituyeron: estas ejecutando sin el modo SQLCMD.';
    PRINT '!! En SSMS: menu Consulta > Modo SQLCMD, y volve a ejecutar.';
    PRINT '!! Con sqlcmd: pasa -v DbName="..." DbLogin="..." DbPassword="..."';
    PRINT '';
    RAISERROR('Variables sin sustituir: se cancela. No se creo nada.', 16, 1);
    SET NOEXEC ON;
END
GO

-- ---------------------------------------------------------------------------
-- 1. La base
-- ---------------------------------------------------------------------------
-- La colación se fija explícitamente en vez de heredar la del servidor: el
-- código asume comparación insensible a mayúsculas (el login resuelve el
-- usuario con `username__iexact`/`email__iexact`, y la unicidad de username y
-- email se apoya en eso). En un servidor con colación CS, "Dpenarreta" y
-- "dpenarreta" serían dos cuentas distintas.
IF DB_ID('$(DbName)') IS NULL
BEGIN
    PRINT 'Creando base $(DbName)...';
    EXEC('CREATE DATABASE [$(DbName)] COLLATE SQL_Latin1_General_CP1_CI_AS');
END
ELSE
    PRINT 'La base $(DbName) ya existe, no se toca.';
GO

-- Modelo de recuperación SIMPLE: sin respaldos de log programados, el registro
-- de transacciones en FULL crece hasta llenar el disco. Cuando haya un plan de
-- respaldo con backup de log, cambiar a FULL:
--     ALTER DATABASE [$(DbName)] SET RECOVERY FULL;
ALTER DATABASE [$(DbName)] SET RECOVERY SIMPLE;
GO

-- Opcional, no aplicado por defecto. READ_COMMITTED_SNAPSHOT hace que las
-- lecturas no esperen a las escrituras, lo que en una app web reduce bloqueos.
-- Queda comentado porque cambia la semántica de concurrencia y este proyecto no
-- se probó bajo esa configuración: activarlo es una decisión a tomar con carga
-- real, no un default a ciegas.
-- ALTER DATABASE [$(DbName)] SET READ_COMMITTED_SNAPSHOT ON WITH ROLLBACK IMMEDIATE;
-- GO

-- ---------------------------------------------------------------------------
-- 2. El login de la aplicación
-- ---------------------------------------------------------------------------
-- Cuenta propia, nunca `sa`: si la aplicación se ve comprometida, el alcance
-- queda acotado a esta base. CHECK_POLICY hereda la política de contraseñas del
-- dominio/servidor.
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = '$(DbLogin)')
BEGIN
    PRINT 'Creando login $(DbLogin)...';
    EXEC('CREATE LOGIN [$(DbLogin)] WITH PASSWORD = ''$(DbPassword)'', '
       + 'DEFAULT_DATABASE = [$(DbName)], CHECK_POLICY = ON, CHECK_EXPIRATION = OFF');
END
ELSE
    PRINT 'El login $(DbLogin) ya existe, no se cambia su clave.';
GO

USE [$(DbName)];
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = '$(DbLogin)')
BEGIN
    PRINT 'Asociando el login a la base...';
    CREATE USER [$(DbLogin)] FOR LOGIN [$(DbLogin)];
END
GO

-- db_owner SOBRE ESTA BASE ÚNICAMENTE (no es un rol de servidor, no da acceso a
-- ninguna otra base). `migrate` crea y altera tablas, índices y restricciones, y
-- renombra columnas vía sp_rename, que exige más que db_ddladmin.
--
-- Si la política interna no admite db_owner para la cuenta de la aplicación, la
-- alternativa es correr las migraciones con una cuenta administrativa aparte y
-- dejar a la app con db_datareader + db_datawriter. En ese caso hay que acordarse
-- de repetir ese paso con cada despliegue que traiga migraciones.
ALTER ROLE db_owner ADD MEMBER [$(DbLogin)];
GO

PRINT '';
PRINT '== Listo ==';
PRINT 'Base y cuenta creadas. Las tablas las crea el paso 2:';
PRINT '   deploy\02_crear_esquema_y_superadmin.ps1';
GO
