-- ============================================================================
-- Permisos para la aplicación — servidor 10.0.2.51, base cmd_dashboards
--
-- Es lo ÚNICO que hace falta de un administrador. Sin esto el despliegue no avanza
-- por ningún camino: ni con los scripts, ni a mano desde SSMS.
--
-- Por qué: la cuenta de la aplicación (`ia_gestion_tareas`) conecta al servidor y
-- llega hasta la base, pero no tiene un solo permiso dentro de ella. Comprobado el
-- 2026-09-18:
--
--     sysadmin / dbcreator ............. no
--     dentro de cmd_dashboards:
--       CREATE TABLE ................... no
--       INSERT / SELECT ................ no
--       db_owner / db_ddladmin ......... no
--
-- La base `cmd_dashboards` ya existe (creada el 2026-09-17) y está vacía: 0 tablas,
-- 0 objetos. No hay que crearla ni borrar nada.
--
-- Ejecutar con una cuenta administradora:
--     sqlcmd -S 10.0.2.51 -U <cuenta_admin> -b -i 00_para_el_dba.sql
-- ============================================================================

SET NOCOUNT ON;
GO

USE [cmd_dashboards];
GO

-- ---------------------------------------------------------------------------
-- Permisos de la aplicación sobre su base   [NECESARIO]
-- ---------------------------------------------------------------------------
-- db_owner SOBRE ESTA BASE ÚNICAMENTE: no es un rol de servidor y no da acceso a
-- ninguna otra base de este servidor. La aplicación lo necesita porque crea el
-- esquema completo y porque cada versión nueva trae migraciones que alteran tablas,
-- índices y restricciones.
--
-- Si la política interna no admite db_owner para la cuenta de una aplicación, la
-- alternativa es db_ddladmin + db_datareader + db_datawriter; alcanza para todo lo
-- que hace el sistema hoy.
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'ia_gestion_tareas')
BEGIN
    PRINT 'Creando el usuario de base para el login ia_gestion_tareas...';
    CREATE USER [ia_gestion_tareas] FOR LOGIN [ia_gestion_tareas];
END
GO

ALTER ROLE db_owner ADD MEMBER [ia_gestion_tareas];
GO

PRINT 'Listo: ia_gestion_tareas es db_owner de cmd_dashboards.';
GO

-- ---------------------------------------------------------------------------
-- Un login propio para la aplicación   [RECOMENDADO, se puede dejar para después]
-- ---------------------------------------------------------------------------
-- `ia_gestion_tareas` parece ser la cuenta de otro sistema: en este mismo servidor
-- hay una base con ese nombre. Compartirla tiene dos costos concretos — rotar la
-- contraseña rompe las dos aplicaciones a la vez, y comprometer una expone la otra.
--
-- Para usarlo: descomentar, reemplazar la contraseña, y apuntar DB_USER/DB_PASSWORD
-- del .env a esta cuenta.
--
-- USE [master];
-- GO
-- IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'cms_dashboards_app')
--     CREATE LOGIN [cms_dashboards_app] WITH PASSWORD = '<clave-nueva>',
--         DEFAULT_DATABASE = [cmd_dashboards], CHECK_POLICY = ON, CHECK_EXPIRATION = OFF;
-- GO
-- USE [cmd_dashboards];
-- GO
-- IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'cms_dashboards_app')
--     CREATE USER [cms_dashboards_app] FOR LOGIN [cms_dashboards_app];
-- GO
-- ALTER ROLE db_owner ADD MEMBER [cms_dashboards_app];
-- GO

-- ---------------------------------------------------------------------------
-- Modelo de recuperación   [REVISAR contra la política de respaldos del servidor]
-- ---------------------------------------------------------------------------
-- Si la base no entra en un plan de respaldo con backup de log, conviene SIMPLE: en
-- FULL el registro de transacciones crece hasta llenar el disco.
--
-- ALTER DATABASE [cmd_dashboards] SET RECOVERY SIMPLE;
-- GO

-- ---------------------------------------------------------------------------
-- Nota sobre la colación   [no requiere acción]
-- ---------------------------------------------------------------------------
-- La base está en Modern_Spanish_CI_AS y el entorno de desarrollo usa
-- SQL_Latin1_General_CP1_CI_AS. Las dos son CI (insensibles a mayúsculas), que es lo
-- que el código necesita: el login resuelve al usuario con `username__iexact` y la
-- unicidad de username y email se apoya en eso. La diferencia que queda es el orden
-- alfabético de los listados con acentos y ñ. Se puede dejar como está.
