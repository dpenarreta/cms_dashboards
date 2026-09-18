"""Genera `sql/02_crear_esquema.sql`: un script SQL ejecutable que crea el esquema
completo, las semillas y la cuenta de administrador, sin necesitar Python en el
servidor donde se ejecuta.

Por qué existe
--------------
`manage.py sqlmigrate` vuelca la SECUENCIA de las 65 migraciones, y esa secuencia no
es ejecutable: al agregar una columna con valor por defecto, el driver de SQL Server
primero consulta el nombre que el motor le autogeneró a la restricción y recién
después la elimina, así que el volcado imprime el nombre de la columna como marcador
("'area' is not a constraint" al ejecutarlo). Este generador, en cambio, pide el DDL
del estado FINAL de cada modelo —lo mismo que hace `migrate --run-syncdb`— con lo que
no hay ningún ALTER intermedio que resolver.

Las semillas (roles, permisos, plantilla de correo, tema visual) las siembran
migraciones de datos en Python, así que no tienen DDL: se vuelcan como INSERT leyendo
una base recién migrada, que este script crea y destruye por su cuenta.

Y se incluyen las 65 filas de `django_migrations`. Ese es el detalle que hace que la
base resultante sea equivalente a una migrada y no un callejón sin salida: sin esas
filas, el próximo `migrate` intentaría crear de nuevo lo que ya existe.

Uso
---
    python deploy/generar_script_sql.py            # usa la base de .env para la muestra
    python deploy/generar_script_sql.py --salida otro.sql

Hay que volver a correrlo cuando se agregue una migración nueva al proyecto.
"""

import argparse
import os
import subprocess
import sys
import uuid
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'backend'))

import django  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# La conexión a la base de muestra se arma con las mismas variables que usa la app, y
# en desarrollo viven en backend/.env — hay que cargarlas antes de leerlas de os.environ.
load_dotenv(RAIZ / 'backend' / '.env')

# --- Tablas cuyos datos semilla se vuelcan, en orden de dependencia --------------
# `django_migrations` va aparte (se arma desde el grafo, no desde la base de muestra).
TABLAS_SEMILLA = [
    'django_content_type',
    'auth_permission',
    'auth_group',
    'auth_group_permissions',
    'authentication_emailtemplate',
    'branding_sitetheme',
]


def literal(valor):
    """Valor Python -> literal de T-SQL."""
    if valor is None:
        return 'NULL'
    if isinstance(valor, bool):
        return '1' if valor else '0'
    if isinstance(valor, (int, float)):
        return str(valor)
    if isinstance(valor, (bytes, bytearray)):
        return '0x' + valor.hex()
    texto = str(valor)
    if hasattr(valor, 'isoformat'):
        texto = valor.isoformat()
    return "N'" + texto.replace("'", "''") + "'"


def ordenar_modelos(modelos):
    """Orden topológico por dependencias de clave foránea.

    Las FK se emiten como ALTER TABLE al final, así que el orden no es estrictamente
    necesario; se hace igual para que el archivo se lea de arriba hacia abajo sin
    referencias hacia adelante.
    """
    pendientes = list(modelos)
    ordenados = []
    vistos = set()
    while pendientes:
        progreso = False
        for modelo in list(pendientes):
            dependencias = {
                campo.related_model for campo in modelo._meta.get_fields()
                if getattr(campo, 'many_to_one', False) or getattr(campo, 'one_to_one', False)
                if campo.related_model is not None and campo.related_model is not modelo
                and getattr(campo, 'concrete', False)
            }
            if dependencias <= vistos:
                ordenados.append(modelo)
                vistos.add(modelo)
                pendientes.remove(modelo)
                progreso = True
        if not progreso:  # ciclo (ej. users_user.created_by -> users_user): se acepta
            ordenados.extend(pendientes)
            break
    return ordenados


def ddl_del_esquema():
    """El DDL de creación de todas las tablas, desde el estado final de las MIGRACIONES.

    No desde `apps.get_models()` —los modelos vivos en memoria—: los dos estados
    normalmente coinciden, pero no siempre. Comprobado en este proyecto:
    `auth_group_permissions.id` es `bigint` después de aplicar las 65 migraciones y
    `int` según el modelo en memoria (el `AppConfig` de `django.contrib.auth` declara
    `AutoField`, y una migración posterior de Django lo amplía). Generar desde los
    modelos producía una base sutilmente distinta de la que crea `migrate`.
    """
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from django.db.migrations.recorder import MigrationRecorder

    estado = MigrationExecutor(connection).loader.project_state()
    modelos = [m for m in estado.apps.get_models() if m._meta.managed]
    modelos = ordenar_modelos(modelos)
    # `django_migrations` no pertenece a ninguna app: su modelo lo define el propio
    # registrador de migraciones. Va primero, porque es lo que vuelve reanudable a la base.
    modelos.insert(0, MigrationRecorder.Migration)

    with connection.schema_editor(collect_sql=True, atomic=False) as editor:
        for modelo in modelos:
            editor.create_model(modelo)
    # `collected_sql` se lee FUERA del `with`: las claves foráneas y los índices quedan
    # en `deferred_sql` mientras el editor está abierto y solo se agregan al salir. Leerlo
    # adentro devuelve las tablas sin ninguna relación.
    sentencias = list(editor.collected_sql)
    return modelos, sentencias


def filas_de(tabla, conexion):
    with conexion.cursor() as c:
        c.execute(f'SELECT * FROM [{tabla}]')
        columnas = [d[0] for d in c.description]
        return columnas, c.fetchall()


def tiene_identity(tabla, conexion):
    with conexion.cursor() as c:
        c.execute("SELECT COUNT(*) FROM sys.identity_columns WHERE OBJECT_NAME(object_id) = %s", [tabla])
        return c.fetchone()[0] > 0


def volcar_semillas(conexion):
    bloques = []
    for tabla in TABLAS_SEMILLA:
        columnas, filas = filas_de(tabla, conexion)
        if not filas:
            continue
        identity = tiene_identity(tabla, conexion)
        lineas = [f'PRINT \'  {tabla} ({len(filas)} filas)\';']
        if identity:
            lineas.append(f'SET IDENTITY_INSERT [{tabla}] ON;')
        nombres = ', '.join(f'[{c}]' for c in columnas)
        # Lotes de 100: SQL Server admite hasta 1000 tuplas por INSERT ... VALUES.
        for inicio in range(0, len(filas), 100):
            lote = filas[inicio:inicio + 100]
            valores = ',\n    '.join('(' + ', '.join(literal(v) for v in fila) + ')' for fila in lote)
            lineas.append(f'INSERT INTO [{tabla}] ({nombres}) VALUES\n    {valores};')
        if identity:
            lineas.append(f'SET IDENTITY_INSERT [{tabla}] OFF;')
        bloques.append('\n'.join(lineas))
    return bloques


def volcar_migraciones():
    """Las 65 filas de `django_migrations`, en el orden real de aplicación."""
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes(), clean_start=True)
    valores = ',\n    '.join(
        f'({literal(m.app_label)}, {literal(m.name)}, SYSDATETIMEOFFSET())' for m, _ in plan
    )
    return len(plan), (
        f'PRINT \'  django_migrations ({len(plan)} filas)\';\n'
        f'INSERT INTO [django_migrations] ([app], [name], [applied]) VALUES\n    {valores};'
    )


def bloque_superadmin():
    """La cuenta de administrador, con el hash Argon2 recibido como variable de sqlcmd.

    El hash no se incrusta en el archivo: se pasa al ejecutar con
    `-v SuperadminHash="..."`, para que este .sql pueda versionarse sin arrastrar
    ninguna credencial.
    """
    return """-- ---------------------------------------------------------------------------
-- Cuenta de administrador
-- ---------------------------------------------------------------------------
-- El hash llega por parámetro (`-v SuperadminHash=...`): es un hash Argon2, no la
-- contraseña, y aun así no se guarda en el repositorio. Se genera con:
--     deploy\\generar_hash.py
IF NOT EXISTS (SELECT 1 FROM [users_user] WHERE [username] = N'$(SuperadminUsername)')
BEGIN
    PRINT '  creando la cuenta $(SuperadminUsername)...';
    INSERT INTO [users_user]
        ([password], [last_login], [is_superuser], [username], [first_name], [last_name],
         [email], [is_staff], [is_active], [date_joined], [created_at], [updated_at],
         [status], [must_change_password], [area], [avatar], [created_by_id], [updated_by_id])
    VALUES
        (N'$(SuperadminHash)', NULL, 1, N'$(SuperadminUsername)', N'', N'',
         N'$(SuperadminEmail)', 1, 1, SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET(), SYSDATETIMEOFFSET(),
         N'active', 0, N'', NULL, NULL, NULL);

    -- Como superusuario ya recibe el catálogo completo de permisos; el rol se asigna
    -- para que la pantalla de usuarios lo muestre como administrador.
    INSERT INTO [users_user_groups] ([user_id], [group_id])
    SELECT u.[id], g.[id]
    FROM [users_user] u
    CROSS JOIN [auth_group] g
    WHERE u.[username] = N'$(SuperadminUsername)'
      AND g.[name] = N'ADMINISTRADOR_GENERAL'
      AND NOT EXISTS (SELECT 1 FROM [users_user_groups] ug
                      WHERE ug.[user_id] = u.[id] AND ug.[group_id] = g.[id]);
END
ELSE
    PRINT '  la cuenta $(SuperadminUsername) ya existe, no se toca.';
GO
"""


def conectar_a_master():
    """Conexión directa (sin el ORM) para crear y borrar la base de muestra."""
    import pyodbc

    cadena = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        f'SERVER={os.environ["DB_HOST"]},{os.environ["DB_PORT"]};DATABASE=master;'
        f'UID={os.environ["DB_USER"]};PWD={os.environ["DB_PASSWORD"]};'
        f'Encrypt={os.environ.get("DB_ENCRYPT", "yes")};'
        f'TrustServerCertificate={os.environ.get("DB_TRUST_SERVER_CERTIFICATE", "yes")}'
    )
    return pyodbc.connect(cadena, autocommit=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--salida', default=str(RAIZ / 'deploy' / 'sql' / '02_crear_esquema.sql'))
    parser.add_argument('--base-muestra', default=f'cms_gen_{uuid.uuid4().hex[:8]}',
                        help='Nombre de la base temporal que se crea para leer las semillas.')
    parser.add_argument('--permitir-host-remoto', action='store_true',
                        help='Permite crear la base de muestra en un DB_HOST que no sea esta máquina.')
    args = parser.parse_args()

    # La base de muestra se crea con `migrate` y se destruye al terminar: es la única
    # forma de obtener las semillas que las migraciones de datos escriben en Python.
    # Claves efímeras, impuestas sobre lo que traiga el .env: con DEBUG=False el arranque
    # rechaza los valores de ejemplo ('change-me'), y acá no se firma nada que sobreviva
    # al proceso — solo hace falta que Django arranque para leer el esquema.
    import secrets

    entorno = dict(os.environ, DB_NAME=args.base_muestra, DEBUG='False',
                   SECRET_KEY=secrets.token_urlsafe(64), JWT_SECRET_KEY=secrets.token_urlsafe(64))
    python = sys.executable

    # --- Red de contención ---------------------------------------------------
    # Este generador CREA Y BORRA una base en el servidor que indique el .env. Es
    # inofensivo mientras ese servidor sea el de desarrollo; contra uno productivo,
    # no. Como el nombre de la base de muestra es aleatorio nunca pisaría una
    # existente, pero un CREATE/DROP DATABASE en producción no es algo que deba
    # poder pasar por tener mal una variable.
    host = os.environ.get('DB_HOST', '')
    if host.lower() not in ('localhost', '127.0.0.1', '.', '(local)') and not args.permitir_host_remoto:
        sys.exit(
            f'DB_HOST apunta a "{host}", que no es esta máquina.\n'
            f'Este script crea y borra una base temporal en ese servidor.\n'
            f'Si es realmente lo que querés, volvé a ejecutarlo con --permitir-host-remoto.'
        )

    print(f'Creando base de muestra {args.base_muestra} en {host or "localhost"}...')
    maestra = conectar_a_master()
    maestra.execute(f'CREATE DATABASE [{args.base_muestra}]')

    try:
        migrar = subprocess.run([python, 'manage.py', 'migrate', '--noinput'],
                                cwd=str(RAIZ / 'backend'), env=entorno, capture_output=True, text=True)
        if migrar.returncode:
            sys.exit(f'migrate falló en la base de muestra:\n{migrar.stdout}\n{migrar.stderr}')

        os.environ.update(entorno)
        django.setup()
        from django.db import connection

        modelos, sentencias = ddl_del_esquema()
        semillas = volcar_semillas(connection)
        total_migraciones, bloque_migraciones = volcar_migraciones()

        tablas = sum(1 for s in sentencias if s.strip().upper().startswith('CREATE TABLE'))
        fks = sum(1 for s in sentencias if 'FOREIGN KEY' in s.upper())
        indices = sum(1 for s in sentencias if s.strip().upper().startswith('CREATE INDEX'))

        partes = [f'''-- ============================================================================
-- cms_dashboards — creación completa del esquema
--
-- Generado el {date.today():%Y-%m-%d} por `deploy/generar_script_sql.py` a partir del
-- estado final de los modelos. EJECUTABLE: crea las tablas, las semillas y la cuenta
-- de administrador sin necesitar Python en este servidor.
--
-- Uso (la base tiene que existir; la crea `01_crear_base.sql`). Los tres valores van
-- por VARIABLE DE ENTORNO, no con `-v`: el hash de Argon2 contiene `$` y `=`, y sqlcmd
-- parte el argumento de `-v` en pedazos al encontrarlos ("Invalid argument").
--
--   $env:SuperadminUsername = 'dpenarreta'
--   $env:SuperadminEmail    = 'dpenarreta@grupolaar.com'
--   $env:SuperadminHash     = '<lo que imprime deploy\\generar_hash.py>'
--   sqlcmd -S <servidor> -d cmd_dashboards -E -b -i 02_crear_esquema.sql
--
-- Contiene: {tablas} tablas, {fks} claves foráneas, {indices} índices,
-- las semillas de las migraciones de datos y las {total_migraciones} filas de
-- `django_migrations` — esto último es lo que deja la base al día frente al proyecto,
-- de modo que un `migrate` futuro aplique solo lo nuevo en vez de chocar con lo que ya
-- existe.
--
-- Es idempotente solo a nivel de la cuenta de administrador: sobre una base que ya
-- tiene el esquema, falla al crear la primera tabla. Está pensado para una base vacía.
-- ============================================================================

-- Estas opciones NO son decorativas. Django crea índices filtrados (los UNIQUE sobre
-- columnas que admiten NULL llevan `WHERE ... IS NOT NULL`), y SQL Server los rechaza
-- si QUOTED_IDENTIFIER está apagado — que es justo como sqlcmd abre la sesión por
-- defecto: "CREATE INDEX failed because the following SET options have incorrect
-- settings: 'QUOTED_IDENTIFIER'". El resto acompaña por el mismo motivo.
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

-- Corta la ejecución ante el primer error, sin depender de que quien lo invoque se
-- haya acordado de pasar `-b`.
:on error exit

-- ---------------------------------------------------------------------------
-- La base tiene que estar vacía
-- ---------------------------------------------------------------------------
-- Sin esto, ejecutarlo por error contra una base que ya tiene el proyecto —la de
-- desarrollo, sin ir más lejos, que suele llamarse igual— falla recién en el primer
-- CREATE TABLE, con un mensaje que no dice qué pasó. No borra nada en ningún caso:
-- solo se niega a seguir.
IF EXISTS (SELECT 1 FROM sys.tables
           WHERE name IN ('django_migrations', 'users_user', 'cartera_dashboard', 'auth_permission'))
BEGIN
    PRINT '';
    PRINT '!! La base ' + DB_NAME() + ' ya tiene tablas de este proyecto.';
    PRINT '!! Este script crea el esquema desde cero y espera una base VACIA.';
    PRINT '!! No se modifico nada.';
    PRINT '!! Si es la base equivocada, revisa el parametro -d; si querias rehacerla, borrala primero.';
    PRINT '';
    RAISERROR('Base no vacia: se cancela la creacion del esquema.', 16, 1);
    SET NOEXEC ON;  -- por si se ejecuta desde SSMS, donde `:on error exit` no aplica
END
GO

PRINT 'Creando tablas...';
GO
''']

        for sentencia in sentencias:
            texto = sentencia.strip()
            if not texto:
                continue
            if not texto.endswith(';'):
                texto += ';'
            partes.append(texto + '\nGO\n')

        partes.append("\nPRINT 'Cargando datos semilla...';\nGO\n")
        for bloque in semillas:
            partes.append(bloque + '\nGO\n')

        partes.append('\n' + bloque_migraciones + '\nGO\n')
        partes.append('\n' + bloque_superadmin())
        partes.append("\nPRINT '';\nPRINT '== Base lista ==';\nGO\n")

        salida = Path(args.salida)
        salida.write_text(''.join(partes), encoding='utf-8-sig')  # BOM: sqlcmd y PowerShell 5.1

        print(f'Archivo   : {salida}')
        print(f'Tablas    : {tablas}   claves foraneas: {fks}   indices: {indices}')
        print(f'Semillas  : {len(semillas)} tablas')
        print(f'Migraciones registradas: {total_migraciones}')
        print(f'Tamano    : {salida.stat().st_size / 1024:.1f} KB')
    finally:
        print(f'Eliminando base de muestra {args.base_muestra}...')
        try:
            from django.db import connections
            connections.close_all()
        except Exception:  # noqa: BLE001 — si Django ni llegó a configurarse, no hay nada que cerrar
            pass
        maestra.execute(f'ALTER DATABASE [{args.base_muestra}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE')
        maestra.execute(f'DROP DATABASE [{args.base_muestra}]')


if __name__ == '__main__':
    main()
