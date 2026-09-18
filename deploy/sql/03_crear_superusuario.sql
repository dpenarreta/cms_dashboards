-- ============================================================================
-- Crea (o repara) la cuenta de superadministrador en una base que YA tiene el esquema.
--
-- Sirve para dos casos: crear la cuenta cuando el esquema se creó por otra vía, o
-- restablecer el acceso si alguien quedó afuera. `02_crear_esquema.sql` ya la crea en
-- un despliegue normal, así que este script no hace falta en el camino habitual.
--
-- Se ejecuta tal cual en SSMS (F5), sin modo SQLCMD: los valores van en las variables
-- de abajo, no como parámetros de sqlcmd.
--
-- IMPORTANTE: la contraseña no se escribe acá. Lo que se pega es su hash Argon2, que
-- se genera con:   python deploy\generar_hash.py
-- SQL Server no puede calcular ese hash, y guardar la contraseña en claro en la
-- columna dejaría a la cuenta sin poder iniciar sesión (Django compara contra el hash).
--
-- Por qué el INSERT y el UPDATE van dentro de EXEC sp_executesql: SQL Server compila
-- el lote ENTERO antes de ejecutar una sola línea, así que si la tabla `users_user` de
-- la base fuera la de otra aplicación —y hay varias en estos servidores—, el lote
-- moriría con "Invalid column name" ANTES de que corriera ninguna comprobación. Con el
-- SQL dinámico esas sentencias se compilan recién al ejecutarse, y las validaciones de
-- más abajo llegan a cancelar el script con un mensaje que explica qué pasó.
-- ============================================================================

USE [cmd_dashboards];   -- <<< la base donde está el esquema
GO

-- Necesario, no decorativo: `users_user` tiene índices filtrados (los UNIQUE sobre
-- columnas que admiten NULL llevan `WHERE ... IS NOT NULL`), y SQL Server rechaza el
-- INSERT si QUOTED_IDENTIFIER está apagado — que es como sqlcmd abre la sesión por
-- defecto. En SSMS ya viene encendido; esto lo cubre en ambos casos.
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF;
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

-- ---------------------------------------------------------------------------
-- Valores a completar
-- ---------------------------------------------------------------------------
DECLARE @base_esperada nvarchar(128) = N'cmd_dashboards';
DECLARE @usuario  nvarchar(150) = N'dpenarreta';
DECLARE @correo   nvarchar(254) = N'dpenarreta@grupolaar.com';
DECLARE @hash     nvarchar(128) = N'<<PEGAR-EL-HASH-DE-generar_hash.py>>';
-- Poner 1 para reescribir la contraseña si la cuenta ya existe:
DECLARE @reescribir_clave bit = 0;

-- ---------------------------------------------------------------------------
-- Comprobación 1: la base correcta
-- ---------------------------------------------------------------------------
-- En SSMS, si el `USE` de arriba falla (por ejemplo porque esa base no existe en el
-- servidor al que estás conectado), ese lote se corta pero SSMS SIGUE con los lotes
-- siguientes, que se ejecutan contra la base seleccionada en el desplegable. Sin esta
-- comprobación, el script termina escribiendo en la base de otra aplicación.
IF DB_NAME() <> @base_esperada
BEGIN
    PRINT '';
    PRINT '!! Estas conectado a la base: ' + DB_NAME();
    PRINT '!! Este script es para:       ' + @base_esperada;
    PRINT '!! No se hizo nada. Revisa la base seleccionada en SSMS, o el -d de sqlcmd.';
    PRINT '';
    RAISERROR('Base equivocada: se cancela.', 16, 1);
    RETURN;
END

-- ---------------------------------------------------------------------------
-- Comprobación 2: la tabla es la de ESTE proyecto
-- ---------------------------------------------------------------------------
IF OBJECT_ID('users_user') IS NULL
BEGIN
    RAISERROR('En esta base no existe la tabla users_user: falta crear el esquema (02_crear_esquema.sql). No se hizo nada.', 16, 1);
    RETURN;
END

DECLARE @faltantes nvarchar(max) =
    STUFF((SELECT ', ' + c.nombre
             FROM (VALUES ('created_at'), ('updated_at'), ('status'), ('must_change_password'),
                          ('created_by_id'), ('updated_by_id'), ('area'), ('avatar')) AS c(nombre)
            WHERE NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
                               WHERE TABLE_NAME = 'users_user' AND COLUMN_NAME = c.nombre)
              FOR XML PATH('')), 1, 2, '');

IF @faltantes IS NOT NULL
BEGIN
    PRINT '';
    PRINT '!! La tabla users_user de esta base NO es la de este proyecto.';
    PRINT '!! Le faltan estas columnas: ' + @faltantes;
    PRINT '!! Probablemente pertenece a otra aplicacion Django del mismo servidor.';
    PRINT '!! No se hizo nada.';
    PRINT '';
    RAISERROR('Tabla users_user de otro proyecto: se cancela.', 16, 1);
    RETURN;
END

-- ---------------------------------------------------------------------------
-- Comprobación 3: el hash está pegado
-- ---------------------------------------------------------------------------
IF @hash LIKE '%PEGAR-EL-HASH%' OR @hash NOT LIKE 'argon2$%'
BEGIN
    RAISERROR('Falta pegar el hash Argon2 en la variable @hash (lo genera deploy\generar_hash.py). No se hizo nada.', 16, 1);
    RETURN;
END

-- ---------------------------------------------------------------------------
-- Alta o actualización
-- ---------------------------------------------------------------------------
DECLARE @id bigint;
DECLARE @sql nvarchar(max);

SET @sql = N'SELECT TOP 1 @id_salida = id FROM users_user WHERE username = @usuario OR email = @correo';
EXEC sp_executesql @sql,
     N'@usuario nvarchar(150), @correo nvarchar(254), @id_salida bigint OUTPUT',
     @usuario = @usuario, @correo = @correo, @id_salida = @id OUTPUT;

IF @id IS NULL
BEGIN
    SET @sql = N'
        INSERT INTO users_user
            ([password], [last_login], [is_superuser], [username], [first_name], [last_name],
             [is_staff], [is_active], [date_joined], [created_at], [updated_at], [email],
             [status], [must_change_password], [created_by_id], [updated_by_id], [area], [avatar])
        VALUES
            (@hash, NULL, 1, @usuario, N'''', N'''',
             1, 1, SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET(), @correo,
             N''active'', 0, NULL, NULL, N'''', NULL);
        SET @id_salida = SCOPE_IDENTITY();';
    EXEC sp_executesql @sql,
         N'@hash nvarchar(128), @usuario nvarchar(150), @correo nvarchar(254), @id_salida bigint OUTPUT',
         @hash = @hash, @usuario = @usuario, @correo = @correo, @id_salida = @id OUTPUT;

    PRINT 'Cuenta creada.';
END
ELSE
BEGIN
    -- Los permisos y el estado se corrigen siempre; la contraseña solo si se pidió, para
    -- que volver a ejecutar esto por las dudas no le cambie la clave a nadie.
    SET @sql = N'
        UPDATE users_user
           SET is_superuser = 1,
               is_staff = 1,
               is_active = 1,
               status = N''active'',
               email = @correo,
               updated_at = SYSDATETIMEOFFSET(),
               [password] = CASE WHEN @reescribir = 1 THEN @hash ELSE [password] END
         WHERE id = @id;';
    EXEC sp_executesql @sql,
         N'@hash nvarchar(128), @correo nvarchar(254), @id bigint, @reescribir bit',
         @hash = @hash, @correo = @correo, @id = @id, @reescribir = @reescribir_clave;

    PRINT CASE WHEN @reescribir_clave = 1
               THEN 'La cuenta ya existia: se actualizaron permisos y contrasena.'
               ELSE 'La cuenta ya existia: se actualizaron permisos. La contrasena NO se toco (poner @reescribir_clave = 1).'
          END;
END

-- ---------------------------------------------------------------------------
-- Rol ADMINISTRADOR_GENERAL
-- ---------------------------------------------------------------------------
-- Como superusuario ya recibe el catálogo completo de permisos; el rol se asigna para
-- que la pantalla de usuarios lo muestre como administrador.
IF NOT EXISTS (SELECT 1 FROM auth_group WHERE name = N'ADMINISTRADOR_GENERAL')
    PRINT 'AVISO: no existe el rol ADMINISTRADOR_GENERAL en esta base. La cuenta funciona igual (es superusuario), pero revisa que el esquema se haya creado completo.';
ELSE
BEGIN
    INSERT INTO users_user_groups ([user_id], [group_id])
    SELECT @id, g.id
      FROM auth_group g
     WHERE g.name = N'ADMINISTRADOR_GENERAL'
       AND NOT EXISTS (SELECT 1 FROM users_user_groups ug
                        WHERE ug.user_id = @id AND ug.group_id = g.id);
END

-- ---------------------------------------------------------------------------
-- Resultado
-- ---------------------------------------------------------------------------
SET @sql = N'
    SELECT u.id, u.username, u.email, u.is_superuser, u.is_active, u.status,
           roles = ISNULL(STUFF((SELECT '', '' + g.name
                                   FROM users_user_groups ug
                                   JOIN auth_group g ON g.id = ug.group_id
                                  WHERE ug.user_id = u.id
                                    FOR XML PATH('''')), 1, 2, ''''), ''(ninguno)''),
           clave_cargada = CASE WHEN u.[password] LIKE ''argon2$%'' THEN ''si (Argon2)'' ELSE ''REVISAR'' END
      FROM users_user u
     WHERE u.id = @id;';
EXEC sp_executesql @sql, N'@id bigint', @id = @id;
GO
