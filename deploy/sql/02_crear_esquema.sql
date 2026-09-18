-- ============================================================================
-- cms_dashboards — creación completa del esquema
--
-- Generado el 2026-09-18 por `deploy/generar_script_sql.py` a partir del
-- estado final de los modelos. EJECUTABLE: crea las tablas, las semillas y la cuenta
-- de administrador sin necesitar Python en este servidor.
--
-- Uso (la base tiene que existir; la crea `01_crear_base.sql`). Los tres valores van
-- por VARIABLE DE ENTORNO, no con `-v`: el hash de Argon2 contiene `$` y `=`, y sqlcmd
-- parte el argumento de `-v` en pedazos al encontrarlos ("Invalid argument").
--
--   $env:SuperadminUsername = 'dpenarreta'
--   $env:SuperadminEmail    = 'dpenarreta@grupolaar.com'
--   $env:SuperadminHash     = '<lo que imprime deploy\generar_hash.py>'
--   sqlcmd -S <servidor> -d cmd_dashboards -E -b -i 02_crear_esquema.sql
--
-- Contiene: 27 tablas, 28 claves foráneas, 54 índices,
-- las semillas de las migraciones de datos y las 65 filas de
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
CREATE TABLE [django_migrations] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [app] nvarchar(255) NOT NULL, [name] nvarchar(255) NOT NULL, [applied] datetimeoffset NOT NULL);
GO
CREATE TABLE [auth_group] ([id] int NOT NULL PRIMARY KEY IDENTITY (1, 1), [name] nvarchar(150) NOT NULL UNIQUE);
GO
CREATE TABLE [auth_group_permissions] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [group_id] int NOT NULL, [permission_id] int NOT NULL);
GO
CREATE TABLE [branding_sitetheme] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [site_name] nvarchar(150) NOT NULL, [short_name] nvarchar(50) NOT NULL, [logo_url] nvarchar(500) NOT NULL, [favicon_url] nvarchar(500) NOT NULL, [color_primary] nvarchar(7) NOT NULL, [color_secondary] nvarchar(7) NOT NULL, [color_background] nvarchar(7) NOT NULL, [color_headings] nvarchar(7) NOT NULL, [color_text] nvarchar(7) NOT NULL, [color_links] nvarchar(7) NOT NULL, [color_buttons] nvarchar(7) NOT NULL, [color_menu] nvarchar(7) NOT NULL, [font_primary] nvarchar(20) NOT NULL, [font_secondary] nvarchar(20) NOT NULL, [font_size_base] nvarchar(10) NOT NULL, [border_radius] nvarchar(20) NOT NULL, [color_button_text] nvarchar(7) NOT NULL, [color_danger] nvarchar(7) NOT NULL, [color_info] nvarchar(7) NOT NULL, [color_success] nvarchar(7) NOT NULL, [color_warning] nvarchar(7) NOT NULL);
GO
CREATE TABLE [cartera_dashboardauditlog] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [dashboard_id] nvarchar(100) NOT NULL, [component_id] nvarchar(100) NOT NULL, [change_type] nvarchar(30) NOT NULL, [changed_by] nvarchar(150) NOT NULL, [changed_at] datetimeoffset NOT NULL, [version] int NOT NULL CONSTRAINT cartera_dashboardauditlog_version_82fb4eeb_check CHECK ([version] >= 0), [previous_config] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardauditlog_previous_config_a9fdc814_check CHECK ((ISJSON ("previous_config") = 1)), [new_config] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardauditlog_new_config_ceb58801_check CHECK ((ISJSON ("new_config") = 1)));
GO
CREATE TABLE [cartera_dashboardlayout] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [dashboard_id] nvarchar(100) NOT NULL UNIQUE, [version] int NOT NULL CONSTRAINT cartera_dashboardlayout_version_e5169841_check CHECK ([version] >= 0), [scope] nvarchar(20) NOT NULL, [theme] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardlayout_theme_f40738d5_check CHECK ((ISJSON ("theme") = 1)), [actualizado_en] datetimeoffset NOT NULL);
GO
CREATE TABLE [cartera_dashboardcomponent] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [component_id] nvarchar(100) NOT NULL, [type] nvarchar(20) NOT NULL, [chart_type] nvarchar(30) NOT NULL, [row] int NOT NULL CONSTRAINT cartera_dashboardcomponent_row_3fecc723_check CHECK ([row] >= 0), [order] int NOT NULL CONSTRAINT cartera_dashboardcomponent_order_4590cccb_check CHECK ([order] >= 0), [width] smallint NOT NULL CONSTRAINT cartera_dashboardcomponent_width_2b3b069f_check CHECK ([width] >= 0), [height] int NOT NULL CONSTRAINT cartera_dashboardcomponent_height_178f9e43_check CHECK ([height] >= 0), [is_visible] bit NOT NULL, [content] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardcomponent_content_33ec3db4_check CHECK ((ISJSON ("content") = 1)), [styles] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardcomponent_styles_0c894d1d_check CHECK ((ISJSON ("styles") = 1)), [config] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardcomponent_config_bc2dbab5_check CHECK ((ISJSON ("config") = 1)), [layout_id] bigint NOT NULL, [mapeo] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardcomponent_mapeo_7b8d4e0f_check CHECK ((ISJSON ("mapeo") = 1)));
GO
CREATE TABLE [cartera_columnahistorica] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [dashboard_id] nvarchar(100) NOT NULL, [columna] nvarchar(200) NOT NULL);
GO
CREATE TABLE [django_content_type] ([id] int NOT NULL PRIMARY KEY IDENTITY (1, 1), [app_label] nvarchar(100) NOT NULL, [model] nvarchar(100) NOT NULL);
GO
CREATE TABLE [django_session] ([session_key] nvarchar(40) NOT NULL PRIMARY KEY, [session_data] nvarchar(max) NOT NULL, [expire_date] datetimeoffset NOT NULL);
GO
CREATE TABLE [users_user] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [password] nvarchar(128) NOT NULL, [last_login] datetimeoffset NULL, [is_superuser] bit NOT NULL, [username] nvarchar(150) NOT NULL UNIQUE, [first_name] nvarchar(150) NOT NULL, [last_name] nvarchar(150) NOT NULL, [is_staff] bit NOT NULL, [is_active] bit NOT NULL, [date_joined] datetimeoffset NOT NULL, [created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [email] nvarchar(254) NOT NULL UNIQUE, [status] nvarchar(20) NOT NULL, [must_change_password] bit NOT NULL, [created_by_id] bigint NULL, [updated_by_id] bigint NULL, [area] nvarchar(100) NOT NULL, [avatar] nvarchar(100) NULL);
GO
CREATE TABLE [users_user_groups] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [user_id] bigint NOT NULL, [group_id] int NOT NULL);
GO
CREATE TABLE [users_user_user_permissions] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [user_id] bigint NOT NULL, [permission_id] int NOT NULL);
GO
CREATE TABLE [django_admin_log] ([id] int NOT NULL PRIMARY KEY IDENTITY (1, 1), [action_time] datetimeoffset NOT NULL, [object_id] nvarchar(max) NULL, [object_repr] nvarchar(200) NOT NULL, [action_flag] smallint NOT NULL CONSTRAINT django_admin_log_action_flag_a8637d59_check CHECK ([action_flag] >= 0), [change_message] nvarchar(max) NOT NULL, [content_type_id] int NULL, [user_id] bigint NOT NULL);
GO
CREATE TABLE [audit_auditevent] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [domain] nvarchar(30) NOT NULL, [action] nvarchar(100) NOT NULL, [result] nvarchar(10) NOT NULL, [severity] nvarchar(10) NOT NULL, [actor_username] nvarchar(150) NOT NULL, [entity_type] nvarchar(100) NOT NULL, [entity_id] nvarchar(64) NOT NULL, [entity_name] nvarchar(255) NOT NULL, [dashboard_id] nvarchar(100) NOT NULL, [component_id] nvarchar(100) NOT NULL, [request_id] nvarchar(64) NOT NULL, [session_id] nvarchar(64) NOT NULL, [ip_address] nvarchar(39) NULL, [user_agent] nvarchar(255) NOT NULL, [previous_values] nvarchar(max) NOT NULL CONSTRAINT audit_auditevent_previous_values_dec45c1c_check CHECK ((ISJSON ("previous_values") = 1)), [new_values] nvarchar(max) NOT NULL CONSTRAINT audit_auditevent_new_values_9e970336_check CHECK ((ISJSON ("new_values") = 1)), [metadata] nvarchar(max) NOT NULL CONSTRAINT audit_auditevent_metadata_7d01b378_check CHECK ((ISJSON ("metadata") = 1)), [message] nvarchar(500) NOT NULL, [created_at] datetimeoffset NOT NULL, [actor_id] bigint NULL);
GO
CREATE TABLE [auth_permission] ([id] int NOT NULL PRIMARY KEY IDENTITY (1, 1), [name] nvarchar(255) NOT NULL, [content_type_id] int NOT NULL, [codename] nvarchar(100) NOT NULL);
GO
CREATE TABLE [authentication_loginattempt] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [identifier] nvarchar(255) NOT NULL, [ip_address] nvarchar(39) NULL, [successful] bit NOT NULL, [user_id] bigint NULL);
GO
CREATE TABLE [authentication_session] ([created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [id] char(32) NOT NULL PRIMARY KEY, [refresh_token_jti] nvarchar(64) NOT NULL UNIQUE, [device] nvarchar(255) NOT NULL, [user_agent] nvarchar(255) NOT NULL, [ip_address] nvarchar(39) NULL, [last_used_at] datetimeoffset NOT NULL, [expires_at] datetimeoffset NOT NULL, [revoked_at] datetimeoffset NULL, [user_id] bigint NOT NULL);
GO
CREATE TABLE [authentication_passwordresettoken] ([created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [id] char(32) NOT NULL PRIMARY KEY, [token_hash] nvarchar(64) NOT NULL UNIQUE, [expires_at] datetimeoffset NOT NULL, [used_at] datetimeoffset NULL, [user_id] bigint NOT NULL);
GO
CREATE TABLE [authentication_emailtemplate] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [key] nvarchar(50) NOT NULL UNIQUE, [subject] nvarchar(200) NOT NULL, [html_body] nvarchar(max) NOT NULL, [updated_by_id] bigint NULL);
GO
CREATE TABLE [cartera_cargaarchivo] ([id] char(32) NOT NULL PRIMARY KEY, [nombre_original] nvarchar(255) NOT NULL, [nombre_hoja] nvarchar(255) NOT NULL, [tamano_bytes] bigint NOT NULL, [fecha_carga] datetimeoffset NOT NULL, [estado] nvarchar(20) NOT NULL, [fecha_corte] date NULL, [total_filas_excel] int NOT NULL, [filas_validas] int NOT NULL, [filas_advertencia] int NOT NULL, [filas_descartadas] int NOT NULL, [mapeo_columnas] nvarchar(max) NOT NULL CONSTRAINT cartera_cargaarchivo_mapeo_columnas_9e84c854_check CHECK ((ISJSON ("mapeo_columnas") = 1)), [resumen_validacion] nvarchar(max) NOT NULL CONSTRAINT cartera_cargaarchivo_resumen_validacion_121ef9ba_check CHECK ((ISJSON ("resumen_validacion") = 1)), [archivo_temp_nombre] nvarchar(255) NOT NULL, [dashboard_id] nvarchar(100) NOT NULL, [archivo_permanente_nombre] nvarchar(255) NOT NULL, [subido_por_id] bigint NULL, [incluir_en_historico] bit NOT NULL);
GO
CREATE TABLE [cartera_registrocartera] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [cliente] nvarchar(255) NOT NULL, [ruc_cliente] nvarchar(50) NOT NULL, [codigo_cliente] nvarchar(100) NOT NULL, [identificador_cliente] nvarchar(255) NOT NULL, [sucursal] nvarchar(255) NOT NULL, [ciudad] nvarchar(255) NOT NULL, [zona] nvarchar(255) NOT NULL, [vendedor_ejecutivo] nvarchar(255) NOT NULL, [estado_cliente] nvarchar(100) NOT NULL, [telefono] nvarchar(50) NOT NULL, [direccion] nvarchar(max) NOT NULL, [numero_documento] nvarchar(100) NOT NULL, [fecha_emision] date NULL, [fecha_vencimiento] date NULL, [saldo] numeric(18, 2) NOT NULL, [articulo] nvarchar(255) NOT NULL, [vence_original] nvarchar(100) NOT NULL, [observacion] nvarchar(max) NOT NULL, [mes] nvarchar(50) NOT NULL, [tipo_venta] nvarchar(100) NOT NULL, [causal] nvarchar(100) NOT NULL, [producto] nvarchar(255) NOT NULL, [fecha_compromiso_pago] date NULL, [observaciones] nvarchar(max) NOT NULL, [tipo_cartera] nvarchar(100) NOT NULL, [recuperador] nvarchar(255) NOT NULL, [dias_credito] int NULL, [carga_id] char(32) NOT NULL);
GO
CREATE TABLE [cartera_dashboard] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [dashboard_id] nvarchar(100) NOT NULL UNIQUE, [name] nvarchar(150) NOT NULL, [area] nvarchar(100) NOT NULL, [description] nvarchar(300) NOT NULL, [created_at] datetimeoffset NOT NULL, [created_by_id] bigint NULL, [orden] int NOT NULL CONSTRAINT cartera_dashboard_orden_dd7d9633_check CHECK ([orden] >= 0), [parent_id] bigint NULL, [owner_id] bigint NULL, [contexto] nvarchar(max) NOT NULL, [fuente_bd_nombre] nvarchar(255) NOT NULL, [fuente_bd_tipo] nvarchar(20) NOT NULL, [fuente_bd_parametros] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboard_fuente_bd_parametros_f855eaf5_check CHECK ((ISJSON ("fuente_bd_parametros") = 1)), [fuente_bd_fecha_configuracion] date NULL, [fuente_bd_frecuencia_actualizacion] nvarchar(20) NOT NULL, [fuente_bd_ultima_actualizacion_automatica] date NULL, [fuente_bd_ultimo_aliases] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboard_fuente_bd_ultimo_aliases_7adccb29_check CHECK ((ISJSON ("fuente_bd_ultimo_aliases") = 1)), [fuente_bd_ultimo_mapeo] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboard_fuente_bd_ultimo_mapeo_65b9c762_check CHECK ((ISJSON ("fuente_bd_ultimo_mapeo") = 1)), [fuente_bd_fecha_formato] nvarchar(30) NOT NULL);
GO
CREATE TABLE [cartera_dashboard_roles_editores] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [dashboard_id] bigint NOT NULL, [group_id] int NOT NULL);
GO
CREATE TABLE [cartera_dashboard_roles_lectores] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [dashboard_id] bigint NOT NULL, [group_id] int NOT NULL);
GO
CREATE TABLE [cartera_filaarchivohistorico] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [orden] int NOT NULL CONSTRAINT cartera_filaarchivohistorico_orden_2340da53_check CHECK ([orden] >= 0), [datos] nvarchar(max) NOT NULL CONSTRAINT cartera_filaarchivohistorico_datos_7847350f_check CHECK ((ISJSON ("datos") = 1)), [carga_id] char(32) NOT NULL);
GO
CREATE TABLE [core_auditlog] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [action] nvarchar(100) NOT NULL, [module] nvarchar(50) NOT NULL, [target_type] nvarchar(100) NOT NULL, [target_id] nvarchar(64) NOT NULL, [previous_values] nvarchar(max) NOT NULL CONSTRAINT core_auditlog_previous_values_db974116_check CHECK ((ISJSON ("previous_values") = 1)), [new_values] nvarchar(max) NOT NULL CONSTRAINT core_auditlog_new_values_bb53eae1_check CHECK ((ISJSON ("new_values") = 1)), [result] nvarchar(10) NOT NULL, [ip_address] nvarchar(39) NULL, [user_agent] nvarchar(255) NOT NULL, [actor_id] bigint NULL);
GO
CREATE INDEX [audit_auditevent_domain_3f23c8b0] ON [audit_auditevent] ([domain]);
GO
ALTER TABLE [cartera_cargaarchivo] ADD CONSTRAINT [cartera_cargaarchivo_subido_por_id_15720237_fk_users_user_id] FOREIGN KEY ([subido_por_id]) REFERENCES [users_user] ([id]);
GO
CREATE INDEX [core_auditlog_actor_id_ab091f3c] ON [core_auditlog] ([actor_id]);
GO
CREATE INDEX [cartera_dashboard_created_by_id_42025471] ON [cartera_dashboard] ([created_by_id]);
GO
ALTER TABLE [cartera_dashboardcomponent] ADD CONSTRAINT [cartera_dashboardcomponent_layout_id_a1c000bc_fk_cartera_dashboardlayout_id] FOREIGN KEY ([layout_id]) REFERENCES [cartera_dashboardlayout] ([id]);
GO
CREATE INDEX [audit_auditevent_action_2131bb77] ON [audit_auditevent] ([action]);
GO
ALTER TABLE [users_user] ADD CONSTRAINT [users_user_updated_by_id_82c4d566_fk_users_user_id] FOREIGN KEY ([updated_by_id]) REFERENCES [users_user] ([id]);
GO
CREATE INDEX [cartera_dashboard_parent_id_44e0b45f] ON [cartera_dashboard] ([parent_id]);
GO
CREATE INDEX [cartera_cargaarchivo_dashboard_id_b5e4094b] ON [cartera_cargaarchivo] ([dashboard_id]);
GO
CREATE INDEX [cartera_dashboardauditlog_component_id_44563a63] ON [cartera_dashboardauditlog] ([component_id]);
GO
CREATE INDEX [audit_auditevent_result_49d270e2] ON [audit_auditevent] ([result]);
GO
CREATE INDEX [users_user_created_by_id_ba0dd846] ON [users_user] ([created_by_id]);
GO
CREATE INDEX [cartera_dashboard_owner_id_a70ba7e7] ON [cartera_dashboard] ([owner_id]);
GO
CREATE INDEX [cartera_cargaarchivo_subido_por_id_15720237] ON [cartera_cargaarchivo] ([subido_por_id]);
GO
CREATE INDEX [audit_auditevent_severity_89be939a] ON [audit_auditevent] ([severity]);
GO
CREATE UNIQUE INDEX [cartera_dashboardcomponent_layout_id_component_id_8e4f88b3_uniq] ON [cartera_dashboardcomponent] ([layout_id], [component_id]) WHERE [layout_id] IS NOT NULL AND [component_id] IS NOT NULL;
GO
CREATE INDEX [users_user_updated_by_id_82c4d566] ON [users_user] ([updated_by_id]);
GO
CREATE UNIQUE INDEX [cartera_dashboard_roles_lectores_dashboard_id_group_id_90e0462d_uniq] ON [cartera_dashboard_roles_lectores] ([dashboard_id], [group_id]) WHERE [dashboard_id] IS NOT NULL AND [group_id] IS NOT NULL;
GO
ALTER TABLE [cartera_dashboard_roles_editores] ADD CONSTRAINT [cartera_dashboard_roles_editores_dashboard_id_406132bf_fk_cartera_dashboard_id] FOREIGN KEY ([dashboard_id]) REFERENCES [cartera_dashboard] ([id]);
GO
CREATE UNIQUE INDEX [auth_group_permissions_group_id_permission_id_0cd325b0_uniq] ON [auth_group_permissions] ([group_id], [permission_id]) WHERE [group_id] IS NOT NULL AND [permission_id] IS NOT NULL;
GO
ALTER TABLE [cartera_registrocartera] ADD CONSTRAINT [cartera_registrocartera_carga_id_68b448fb_fk_cartera_cargaarchivo_id] FOREIGN KEY ([carga_id]) REFERENCES [cartera_cargaarchivo] ([id]);
GO
CREATE INDEX [cartera_dashboardauditlog_dashboard_id_bec78c2b] ON [cartera_dashboardauditlog] ([dashboard_id]);
GO
CREATE INDEX [audit_auditevent_dashboard_id_47d2ae6d] ON [audit_auditevent] ([dashboard_id]);
GO
ALTER TABLE [users_user_groups] ADD CONSTRAINT [users_user_groups_user_id_5f6f5a90_fk_users_user_id] FOREIGN KEY ([user_id]) REFERENCES [users_user] ([id]);
GO
CREATE INDEX [auth_group_permissions_permission_id_84c5c92e] ON [auth_group_permissions] ([permission_id]);
GO
CREATE INDEX [audit_auditevent_created_at_58e81936] ON [audit_auditevent] ([created_at]);
GO
CREATE UNIQUE INDEX [cartera_dashboard_roles_editores_dashboard_id_group_id_0b4071e2_uniq] ON [cartera_dashboard_roles_editores] ([dashboard_id], [group_id]) WHERE [dashboard_id] IS NOT NULL AND [group_id] IS NOT NULL;
GO
ALTER TABLE [cartera_dashboard_roles_editores] ADD CONSTRAINT [cartera_dashboard_roles_editores_group_id_08a7f9e2_fk_auth_group_id] FOREIGN KEY ([group_id]) REFERENCES [auth_group] ([id]);
GO
CREATE INDEX [cartera_registrocartera_identificador_cliente_c0e487e0] ON [cartera_registrocartera] ([identificador_cliente]);
GO
CREATE UNIQUE INDEX [django_content_type_app_label_model_76bd3d3b_uniq] ON [django_content_type] ([app_label], [model]) WHERE [app_label] IS NOT NULL AND [model] IS NOT NULL;
GO
ALTER TABLE [users_user_groups] ADD CONSTRAINT [users_user_groups_group_id_9afc8d0e_fk_auth_group_id] FOREIGN KEY ([group_id]) REFERENCES [auth_group] ([id]);
GO
CREATE INDEX [audit_auditevent_actor_id_270bb4b7] ON [audit_auditevent] ([actor_id]);
GO
CREATE INDEX [cartera_registrocartera_ciudad_7601c6db] ON [cartera_registrocartera] ([ciudad]);
GO
ALTER TABLE [auth_permission] ADD CONSTRAINT [auth_permission_content_type_id_2f476e4b_fk_django_content_type_id] FOREIGN KEY ([content_type_id]) REFERENCES [django_content_type] ([id]);
GO
CREATE INDEX [cartera_registrocartera_numero_documento_447bb1c0] ON [cartera_registrocartera] ([numero_documento]);
GO
CREATE INDEX [cartera_dashboard_roles_editores_dashboard_id_406132bf] ON [cartera_dashboard_roles_editores] ([dashboard_id]);
GO
CREATE INDEX [users_user_groups_user_id_5f6f5a90] ON [users_user_groups] ([user_id]);
GO
CREATE INDEX [auth_group_permissions_group_id_b120cbf9] ON [auth_group_permissions] ([group_id]);
GO
CREATE INDEX [cartera_registrocartera_fecha_vencimiento_c86ebe20] ON [cartera_registrocartera] ([fecha_vencimiento]);
GO
CREATE UNIQUE INDEX [cartera_columnahistorica_dashboard_id_columna_fda23d01_uniq] ON [cartera_columnahistorica] ([dashboard_id], [columna]) WHERE [dashboard_id] IS NOT NULL AND [columna] IS NOT NULL;
GO
CREATE INDEX [cartera_dashboard_roles_editores_group_id_08a7f9e2] ON [cartera_dashboard_roles_editores] ([group_id]);
GO
CREATE INDEX [users_user_groups_group_id_9afc8d0e] ON [users_user_groups] ([group_id]);
GO
CREATE UNIQUE INDEX [users_user_user_permissions_user_id_permission_id_43338c45_uniq] ON [users_user_user_permissions] ([user_id], [permission_id]) WHERE [user_id] IS NOT NULL AND [permission_id] IS NOT NULL;
GO
CREATE INDEX [cartera_registrocartera_saldo_2f880fe7] ON [cartera_registrocartera] ([saldo]);
GO
CREATE INDEX [auth_permission_content_type_id_2f476e4b] ON [auth_permission] ([content_type_id]);
GO
ALTER TABLE [cartera_dashboard_roles_lectores] ADD CONSTRAINT [cartera_dashboard_roles_lectores_dashboard_id_86877019_fk_cartera_dashboard_id] FOREIGN KEY ([dashboard_id]) REFERENCES [cartera_dashboard] ([id]);
GO
ALTER TABLE [users_user_user_permissions] ADD CONSTRAINT [users_user_user_permissions_user_id_20aca447_fk_users_user_id] FOREIGN KEY ([user_id]) REFERENCES [users_user] ([id]);
GO
CREATE INDEX [cartera_registrocartera_causal_388de230] ON [cartera_registrocartera] ([causal]);
GO
ALTER TABLE [authentication_loginattempt] ADD CONSTRAINT [authentication_loginattempt_user_id_253ccbc6_fk_users_user_id] FOREIGN KEY ([user_id]) REFERENCES [users_user] ([id]);
GO
ALTER TABLE [cartera_dashboard_roles_lectores] ADD CONSTRAINT [cartera_dashboard_roles_lectores_group_id_b69b45b3_fk_auth_group_id] FOREIGN KEY ([group_id]) REFERENCES [auth_group] ([id]);
GO
ALTER TABLE [users_user_user_permissions] ADD CONSTRAINT [users_user_user_permissions_permission_id_0b93982e_fk_auth_permission_id] FOREIGN KEY ([permission_id]) REFERENCES [auth_permission] ([id]);
GO
CREATE INDEX [cartera_registrocartera_recuperador_58630248] ON [cartera_registrocartera] ([recuperador]);
GO
CREATE INDEX [authentication_loginattempt_identifier_16a5398a] ON [authentication_loginattempt] ([identifier]);
GO
CREATE INDEX [cartera_registrocartera_carga_id_68b448fb] ON [cartera_registrocartera] ([carga_id]);
GO
ALTER TABLE [django_admin_log] ADD CONSTRAINT [django_admin_log_content_type_id_c4bce8eb_fk_django_content_type_id] FOREIGN KEY ([content_type_id]) REFERENCES [django_content_type] ([id]);
GO
CREATE INDEX [authentication_loginattempt_user_id_253ccbc6] ON [authentication_loginattempt] ([user_id]);
GO
ALTER TABLE [cartera_filaarchivohistorico] ADD CONSTRAINT [cartera_filaarchivohistorico_carga_id_493c7247_fk_cartera_cargaarchivo_id] FOREIGN KEY ([carga_id]) REFERENCES [cartera_cargaarchivo] ([id]);
GO
CREATE INDEX [users_user_user_permissions_user_id_20aca447] ON [users_user_user_permissions] ([user_id]);
GO
CREATE UNIQUE INDEX [auth_permission_content_type_id_codename_01ab375a_uniq] ON [auth_permission] ([content_type_id], [codename]) WHERE [content_type_id] IS NOT NULL AND [codename] IS NOT NULL;
GO
CREATE INDEX [cartera_reg_carga_i_635d5a_idx] ON [cartera_registrocartera] ([carga_id], [fecha_vencimiento]);
GO
CREATE INDEX [cartera_dashboardcomponent_layout_id_a1c000bc] ON [cartera_dashboardcomponent] ([layout_id]);
GO
ALTER TABLE [authentication_session] ADD CONSTRAINT [authentication_session_user_id_c9667cdb_fk_users_user_id] FOREIGN KEY ([user_id]) REFERENCES [users_user] ([id]);
GO
CREATE INDEX [cartera_dashboard_roles_lectores_dashboard_id_86877019] ON [cartera_dashboard_roles_lectores] ([dashboard_id]);
GO
CREATE INDEX [users_user_user_permissions_permission_id_0b93982e] ON [users_user_user_permissions] ([permission_id]);
GO
CREATE INDEX [cartera_reg_carga_i_c1b23f_idx] ON [cartera_registrocartera] ([carga_id], [recuperador]);
GO
CREATE INDEX [cartera_dashboard_roles_lectores_group_id_b69b45b3] ON [cartera_dashboard_roles_lectores] ([group_id]);
GO
CREATE INDEX [authentication_session_user_id_c9667cdb] ON [authentication_session] ([user_id]);
GO
CREATE INDEX [cartera_reg_carga_i_35cd0a_idx] ON [cartera_registrocartera] ([carga_id], [causal]);
GO
ALTER TABLE [django_admin_log] ADD CONSTRAINT [django_admin_log_user_id_c564eba6_fk_users_user_id] FOREIGN KEY ([user_id]) REFERENCES [users_user] ([id]);
GO
ALTER TABLE [authentication_passwordresettoken] ADD CONSTRAINT [authentication_passwordresettoken_user_id_167c3ac5_fk_users_user_id] FOREIGN KEY ([user_id]) REFERENCES [users_user] ([id]);
GO
CREATE INDEX [cartera_reg_carga_i_62cddf_idx] ON [cartera_registrocartera] ([carga_id], [ciudad]);
GO
ALTER TABLE [auth_group_permissions] ADD CONSTRAINT [auth_group_permissions_group_id_b120cbf9_fk_auth_group_id] FOREIGN KEY ([group_id]) REFERENCES [auth_group] ([id]);
GO
CREATE INDEX [cartera_filaarchivohistorico_carga_id_493c7247] ON [cartera_filaarchivohistorico] ([carga_id]);
GO
CREATE INDEX [cartera_dashboardcomponent_component_id_5e91a8f1] ON [cartera_dashboardcomponent] ([component_id]);
GO
ALTER TABLE [cartera_dashboard] ADD CONSTRAINT [cartera_dashboard_created_by_id_42025471_fk_users_user_id] FOREIGN KEY ([created_by_id]) REFERENCES [users_user] ([id]);
GO
ALTER TABLE [auth_group_permissions] ADD CONSTRAINT [auth_group_permissions_permission_id_84c5c92e_fk_auth_permission_id] FOREIGN KEY ([permission_id]) REFERENCES [auth_permission] ([id]);
GO
ALTER TABLE [core_auditlog] ADD CONSTRAINT [core_auditlog_actor_id_ab091f3c_fk_users_user_id] FOREIGN KEY ([actor_id]) REFERENCES [users_user] ([id]);
GO
CREATE INDEX [django_admin_log_content_type_id_c4bce8eb] ON [django_admin_log] ([content_type_id]);
GO
CREATE INDEX [authentication_passwordresettoken_user_id_167c3ac5] ON [authentication_passwordresettoken] ([user_id]);
GO
ALTER TABLE [authentication_emailtemplate] ADD CONSTRAINT [authentication_emailtemplate_updated_by_id_081040d7_fk_users_user_id] FOREIGN KEY ([updated_by_id]) REFERENCES [users_user] ([id]);
GO
ALTER TABLE [cartera_dashboard] ADD CONSTRAINT [cartera_dashboard_parent_id_44e0b45f_fk_cartera_dashboard_id] FOREIGN KEY ([parent_id]) REFERENCES [cartera_dashboard] ([id]);
GO
CREATE INDEX [cartera_columnahistorica_dashboard_id_6557fe99] ON [cartera_columnahistorica] ([dashboard_id]);
GO
CREATE INDEX [django_admin_log_user_id_c564eba6] ON [django_admin_log] ([user_id]);
GO
CREATE INDEX [core_auditlog_action_978477aa] ON [core_auditlog] ([action]);
GO
ALTER TABLE [audit_auditevent] ADD CONSTRAINT [audit_auditevent_actor_id_270bb4b7_fk_users_user_id] FOREIGN KEY ([actor_id]) REFERENCES [users_user] ([id]);
GO
CREATE UNIQUE INDEX [users_user_groups_user_id_group_id_b88eab82_uniq] ON [users_user_groups] ([user_id], [group_id]) WHERE [user_id] IS NOT NULL AND [group_id] IS NOT NULL;
GO
CREATE INDEX [django_session_expire_date_a5c62663] ON [django_session] ([expire_date]);
GO
ALTER TABLE [cartera_dashboard] ADD CONSTRAINT [cartera_dashboard_owner_id_a70ba7e7_fk_users_user_id] FOREIGN KEY ([owner_id]) REFERENCES [users_user] ([id]);
GO
CREATE INDEX [authentication_emailtemplate_updated_by_id_081040d7] ON [authentication_emailtemplate] ([updated_by_id]);
GO
CREATE INDEX [core_auditlog_module_baadd22e] ON [core_auditlog] ([module]);
GO
ALTER TABLE [users_user] ADD CONSTRAINT [users_user_created_by_id_ba0dd846_fk_users_user_id] FOREIGN KEY ([created_by_id]) REFERENCES [users_user] ([id]);
GO

PRINT 'Cargando datos semilla...';
GO
PRINT '  django_content_type (22 filas)';
SET IDENTITY_INSERT [django_content_type] ON;
INSERT INTO [django_content_type] ([id], [app_label], [model]) VALUES
    (2, N'admin', N'logentry'),
    (16, N'audit', N'auditevent'),
    (4, N'auth', N'group'),
    (3, N'auth', N'permission'),
    (20, N'authentication', N'emailtemplate'),
    (17, N'authentication', N'loginattempt'),
    (19, N'authentication', N'passwordresettoken'),
    (18, N'authentication', N'session'),
    (22, N'branding', N'sitetheme'),
    (7, N'cartera', N'cargaarchivo'),
    (14, N'cartera', N'columnahistorica'),
    (12, N'cartera', N'dashboard'),
    (9, N'cartera', N'dashboardauditlog'),
    (11, N'cartera', N'dashboardcomponent'),
    (10, N'cartera', N'dashboardlayout'),
    (13, N'cartera', N'filaarchivohistorico'),
    (8, N'cartera', N'registrocartera'),
    (5, N'contenttypes', N'contenttype'),
    (15, N'core', N'auditlog'),
    (1, N'permissions', N'modulepermission'),
    (6, N'sessions', N'session'),
    (21, N'users', N'user');
SET IDENTITY_INSERT [django_content_type] OFF;
GO
PRINT '  auth_permission (113 filas)';
SET IDENTITY_INSERT [auth_permission] ON;
INSERT INTO [auth_permission] ([id], [name], [content_type_id], [codename]) VALUES
    (1, N'Ver usuarios', 1, N'usuarios.ver'),
    (2, N'Crear usuarios', 1, N'usuarios.crear'),
    (3, N'Editar usuarios y su asignación de roles/permisos', 1, N'usuarios.editar'),
    (4, N'Habilitar, deshabilitar, bloquear y desbloquear usuarios', 1, N'usuarios.deshabilitar'),
    (5, N'Forzar cambio de contraseña o cerrar sesiones activas de un usuario', 1, N'usuarios.restablecer_password'),
    (6, N'Ver roles y el catálogo de permisos', 1, N'roles.ver'),
    (7, N'Crear, editar y eliminar roles', 1, N'roles.editar'),
    (8, N'Ver el catálogo de permisos y a qué módulo pertenece cada uno', 1, N'permisos.ver'),
    (9, N'Ver configuración del sistema', 1, N'configuracion.ver'),
    (10, N'Editar configuración del sistema', 1, N'configuracion.editar'),
    (11, N'Ver el registro de auditoría', 1, N'auditoria.ver'),
    (12, N'Ver el detalle (valores anteriores y nuevos) de un evento', 1, N'auditoria.ver_detalle'),
    (13, N'Exportar el registro de auditoría', 1, N'auditoria.exportar'),
    (14, N'Crear nuevos dashboards por área', 1, N'dashboard.crear'),
    (15, N'Editar el nombre y área de un dashboard', 1, N'dashboard.editar'),
    (16, N'Eliminar un dashboard', 1, N'dashboard.eliminar'),
    (17, N'Ver Dashboards', 1, N'dashboard.view'),
    (18, N'Entrar en modo edición del dashboard', 1, N'dashboard.edit'),
    (19, N'Editar el diseño (orden/tamaño) del dashboard', 1, N'dashboard.layout.edit'),
    (20, N'Editar estilos de un componente del dashboard', 1, N'dashboard.component.style'),
    (21, N'Crear componentes del dashboard', 1, N'dashboard.component.create'),
    (22, N'Eliminar componentes del dashboard', 1, N'dashboard.component.delete'),
    (23, N'Restablecer la configuración del dashboard', 1, N'dashboard.configuration.reset'),
    (24, N'Generar la interpretación completa del dashboard con IA', 1, N'dashboard.interpretar'),
    (25, N'Generar hallazgos clave por componente con IA', 1, N'dashboard.hallazgos_ia'),
    (26, N'Elegir/cambiar la vista o procedimiento de base de datos, sus parámetros y la frecuencia de actualización automática de un dashboard', 1, N'dashboard.fuente_bd.configurar'),
    (27, N'Forzar una actualización inmediata de los datos desde la base de datos ya configurada', 1, N'dashboard.fuente_bd.actualizar'),
    (28, N'Cargar un archivo Excel nuevo que reemplaza los datos de un dashboard ("Cargar otro archivo")', 1, N'dashboard.archivo.cargar'),
    (29, N'Procesar, reprocesar, borrar o remapear los datos ya cargados de un dashboard', 1, N'dashboard.datos.editar'),
    (30, N'Can add log entry', 2, N'add_logentry'),
    (31, N'Can change log entry', 2, N'change_logentry'),
    (32, N'Can delete log entry', 2, N'delete_logentry'),
    (33, N'Can view log entry', 2, N'view_logentry'),
    (34, N'Can add permission', 3, N'add_permission'),
    (35, N'Can change permission', 3, N'change_permission'),
    (36, N'Can delete permission', 3, N'delete_permission'),
    (37, N'Can view permission', 3, N'view_permission'),
    (38, N'Can add group', 4, N'add_group'),
    (39, N'Can change group', 4, N'change_group'),
    (40, N'Can delete group', 4, N'delete_group'),
    (41, N'Can view group', 4, N'view_group'),
    (42, N'Can add content type', 5, N'add_contenttype'),
    (43, N'Can change content type', 5, N'change_contenttype'),
    (44, N'Can delete content type', 5, N'delete_contenttype'),
    (45, N'Can view content type', 5, N'view_contenttype'),
    (46, N'Can add session', 6, N'add_session'),
    (47, N'Can change session', 6, N'change_session'),
    (48, N'Can delete session', 6, N'delete_session'),
    (49, N'Can view session', 6, N'view_session'),
    (50, N'Can add carga archivo', 7, N'add_cargaarchivo'),
    (51, N'Can change carga archivo', 7, N'change_cargaarchivo'),
    (52, N'Can delete carga archivo', 7, N'delete_cargaarchivo'),
    (53, N'Can view carga archivo', 7, N'view_cargaarchivo'),
    (54, N'Can add registro cartera', 8, N'add_registrocartera'),
    (55, N'Can change registro cartera', 8, N'change_registrocartera'),
    (56, N'Can delete registro cartera', 8, N'delete_registrocartera'),
    (57, N'Can view registro cartera', 8, N'view_registrocartera'),
    (58, N'Can add dashboard audit log', 9, N'add_dashboardauditlog'),
    (59, N'Can change dashboard audit log', 9, N'change_dashboardauditlog'),
    (60, N'Can delete dashboard audit log', 9, N'delete_dashboardauditlog'),
    (61, N'Can view dashboard audit log', 9, N'view_dashboardauditlog'),
    (62, N'Can add dashboard layout', 10, N'add_dashboardlayout'),
    (63, N'Can change dashboard layout', 10, N'change_dashboardlayout'),
    (64, N'Can delete dashboard layout', 10, N'delete_dashboardlayout'),
    (65, N'Can view dashboard layout', 10, N'view_dashboardlayout'),
    (66, N'Can add dashboard component', 11, N'add_dashboardcomponent'),
    (67, N'Can change dashboard component', 11, N'change_dashboardcomponent'),
    (68, N'Can delete dashboard component', 11, N'delete_dashboardcomponent'),
    (69, N'Can view dashboard component', 11, N'view_dashboardcomponent'),
    (70, N'Can add dashboard', 12, N'add_dashboard'),
    (71, N'Can change dashboard', 12, N'change_dashboard'),
    (72, N'Can delete dashboard', 12, N'delete_dashboard'),
    (73, N'Can view dashboard', 12, N'view_dashboard'),
    (74, N'Can add fila archivo historico', 13, N'add_filaarchivohistorico'),
    (75, N'Can change fila archivo historico', 13, N'change_filaarchivohistorico'),
    (76, N'Can delete fila archivo historico', 13, N'delete_filaarchivohistorico'),
    (77, N'Can view fila archivo historico', 13, N'view_filaarchivohistorico'),
    (78, N'Can add columna historica', 14, N'add_columnahistorica'),
    (79, N'Can change columna historica', 14, N'change_columnahistorica'),
    (80, N'Can delete columna historica', 14, N'delete_columnahistorica'),
    (81, N'Can view columna historica', 14, N'view_columnahistorica'),
    (82, N'Can add audit log', 15, N'add_auditlog'),
    (83, N'Can change audit log', 15, N'change_auditlog'),
    (84, N'Can delete audit log', 15, N'delete_auditlog'),
    (85, N'Can view audit log', 15, N'view_auditlog'),
    (86, N'Can add audit event', 16, N'add_auditevent'),
    (87, N'Can change audit event', 16, N'change_auditevent'),
    (88, N'Can delete audit event', 16, N'delete_auditevent'),
    (89, N'Can view audit event', 16, N'view_auditevent'),
    (90, N'Can add login attempt', 17, N'add_loginattempt'),
    (91, N'Can change login attempt', 17, N'change_loginattempt'),
    (92, N'Can delete login attempt', 17, N'delete_loginattempt'),
    (93, N'Can view login attempt', 17, N'view_loginattempt'),
    (94, N'Can add session', 18, N'add_session'),
    (95, N'Can change session', 18, N'change_session'),
    (96, N'Can delete session', 18, N'delete_session'),
    (97, N'Can view session', 18, N'view_session'),
    (98, N'Can add password reset token', 19, N'add_passwordresettoken'),
    (99, N'Can change password reset token', 19, N'change_passwordresettoken'),
    (100, N'Can delete password reset token', 19, N'delete_passwordresettoken');
INSERT INTO [auth_permission] ([id], [name], [content_type_id], [codename]) VALUES
    (101, N'Can view password reset token', 19, N'view_passwordresettoken'),
    (102, N'Can add email template', 20, N'add_emailtemplate'),
    (103, N'Can change email template', 20, N'change_emailtemplate'),
    (104, N'Can delete email template', 20, N'delete_emailtemplate'),
    (105, N'Can view email template', 20, N'view_emailtemplate'),
    (106, N'Can add user', 21, N'add_user'),
    (107, N'Can change user', 21, N'change_user'),
    (108, N'Can delete user', 21, N'delete_user'),
    (109, N'Can view user', 21, N'view_user'),
    (110, N'Can add site theme', 22, N'add_sitetheme'),
    (111, N'Can change site theme', 22, N'change_sitetheme'),
    (112, N'Can delete site theme', 22, N'delete_sitetheme'),
    (113, N'Can view site theme', 22, N'view_sitetheme');
SET IDENTITY_INSERT [auth_permission] OFF;
GO
PRINT '  auth_group (1 filas)';
SET IDENTITY_INSERT [auth_group] ON;
INSERT INTO [auth_group] ([id], [name]) VALUES
    (1, N'ADMINISTRADOR_GENERAL');
SET IDENTITY_INSERT [auth_group] OFF;
GO
PRINT '  auth_group_permissions (29 filas)';
SET IDENTITY_INSERT [auth_group_permissions] ON;
INSERT INTO [auth_group_permissions] ([id], [group_id], [permission_id]) VALUES
    (1, 1, 1),
    (2, 1, 2),
    (3, 1, 3),
    (4, 1, 4),
    (5, 1, 5),
    (6, 1, 6),
    (7, 1, 7),
    (8, 1, 8),
    (9, 1, 9),
    (10, 1, 10),
    (11, 1, 11),
    (12, 1, 12),
    (13, 1, 13),
    (14, 1, 14),
    (15, 1, 15),
    (16, 1, 16),
    (17, 1, 17),
    (18, 1, 18),
    (19, 1, 19),
    (20, 1, 20),
    (21, 1, 21),
    (22, 1, 22),
    (23, 1, 23),
    (24, 1, 24),
    (25, 1, 25),
    (26, 1, 26),
    (27, 1, 27),
    (28, 1, 28),
    (29, 1, 29);
SET IDENTITY_INSERT [auth_group_permissions] OFF;
GO
PRINT '  authentication_emailtemplate (1 filas)';
SET IDENTITY_INSERT [authentication_emailtemplate] ON;
INSERT INTO [authentication_emailtemplate] ([id], [created_at], [updated_at], [key], [subject], [html_body], [updated_by_id]) VALUES
    (1, N'2026-09-18T14:26:37.786555+00:00', N'2026-09-18T14:26:37.786555+00:00', N'password_reset', N'Recuperación de contraseña | {{ site_name }}', N'<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, ''Segoe UI'', Roboto, Helvetica, Arial, sans-serif; background: #eeeeee; padding: 24px;">
  <div style="max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 10px; padding: 32px; border: 1px solid #dddddd;">
    <h1 style="font-size: 20px; color: {{ color_primary }}; margin: 0 0 16px;">{{ site_name }}</h1>
    <p>Hola {{ nombre_usuario }},</p>
    <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en {{ site_name }}.</p>
    <p style="text-align: center; margin: 28px 0;">
      <a href="{{ enlace }}" style="background: {{ color_primary }}; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 6px; display: inline-block;">
        Restablecer contraseña
      </a>
    </p>
    <p style="font-size: 13px; color: #444444;">Si el botón no funciona, copiá y pegá este enlace
      en tu navegador: {{ enlace }}</p>
    <p>Este enlace es válido durante {{ minutos_expiracion }} minutos. Si no lo utilizas en ese
      tiempo, deberás solicitar uno nuevo.</p>
    <p>Si tú no solicitaste este cambio, puedes ignorar este mensaje: tu contraseña actual seguirá
      funcionando y no se realizará ningún cambio.</p>
    <p style="font-size: 12px; color: #666666; margin-top: 32px;">
      Por seguridad, nunca compartas este enlace con nadie. {{ site_name }} nunca te pedirá tu
      contraseña por correo electrónico.
    </p>
  </div>
</body>
</html>
', NULL);
SET IDENTITY_INSERT [authentication_emailtemplate] OFF;
GO
PRINT '  branding_sitetheme (1 filas)';
SET IDENTITY_INSERT [branding_sitetheme] ON;
INSERT INTO [branding_sitetheme] ([id], [created_at], [updated_at], [site_name], [short_name], [logo_url], [favicon_url], [color_primary], [color_secondary], [color_background], [color_headings], [color_text], [color_links], [color_buttons], [color_menu], [font_primary], [font_secondary], [font_size_base], [border_radius], [color_button_text], [color_danger], [color_info], [color_success], [color_warning]) VALUES
    (1, N'2026-09-18T14:26:37.828322+00:00', N'2026-09-18T14:26:37.828322+00:00', N'Dashboard de Cartera', N'Cartera', N'', N'', N'#2a78d6', N'#eb6834', N'#eeeeee', N'#000000', N'#000000', N'#2a78d6', N'#2a78d6', N'#ffffff', N'system', N'system', N'16px', N'medium', N'#ffffff', N'#dc3545', N'#0dcaf0', N'#198754', N'#ffc107');
SET IDENTITY_INSERT [branding_sitetheme] OFF;
GO

PRINT '  django_migrations (65 filas)';
INSERT INTO [django_migrations] ([app], [name], [applied]) VALUES
    (N'contenttypes', N'0001_initial', SYSDATETIMEOFFSET()),
    (N'contenttypes', N'0002_remove_content_type_name', SYSDATETIMEOFFSET()),
    (N'auth', N'0001_initial', SYSDATETIMEOFFSET()),
    (N'auth', N'0002_alter_permission_name_max_length', SYSDATETIMEOFFSET()),
    (N'auth', N'0003_alter_user_email_max_length', SYSDATETIMEOFFSET()),
    (N'auth', N'0004_alter_user_username_opts', SYSDATETIMEOFFSET()),
    (N'auth', N'0005_alter_user_last_login_null', SYSDATETIMEOFFSET()),
    (N'auth', N'0006_require_contenttypes_0002', SYSDATETIMEOFFSET()),
    (N'auth', N'0007_alter_validators_add_error_messages', SYSDATETIMEOFFSET()),
    (N'auth', N'0008_alter_user_username_max_length', SYSDATETIMEOFFSET()),
    (N'auth', N'0009_alter_user_last_name_max_length', SYSDATETIMEOFFSET()),
    (N'auth', N'0010_alter_group_name_max_length', SYSDATETIMEOFFSET()),
    (N'auth', N'0011_update_proxy_permissions', SYSDATETIMEOFFSET()),
    (N'auth', N'0012_alter_user_first_name_max_length', SYSDATETIMEOFFSET()),
    (N'users', N'0001_initial', SYSDATETIMEOFFSET()),
    (N'admin', N'0001_initial', SYSDATETIMEOFFSET()),
    (N'admin', N'0002_logentry_remove_auto_add', SYSDATETIMEOFFSET()),
    (N'admin', N'0003_logentry_add_action_flag_choices', SYSDATETIMEOFFSET()),
    (N'core', N'0001_initial', SYSDATETIMEOFFSET()),
    (N'core', N'0002_initial', SYSDATETIMEOFFSET()),
    (N'cartera', N'0001_initial', SYSDATETIMEOFFSET()),
    (N'cartera', N'0002_dashboardauditlog_dashboardlayout_dashboardcomponent', SYSDATETIMEOFFSET()),
    (N'cartera', N'0003_alter_dashboardauditlog_change_type', SYSDATETIMEOFFSET()),
    (N'audit', N'0001_initial', SYSDATETIMEOFFSET()),
    (N'audit', N'0002_migrar_historico_legacy', SYSDATETIMEOFFSET()),
    (N'authentication', N'0001_initial', SYSDATETIMEOFFSET()),
    (N'authentication', N'0002_initial', SYSDATETIMEOFFSET()),
    (N'authentication', N'0003_passwordresettoken', SYSDATETIMEOFFSET()),
    (N'authentication', N'0004_emailtemplate', SYSDATETIMEOFFSET()),
    (N'authentication', N'0005_seed_password_reset_email_template', SYSDATETIMEOFFSET()),
    (N'branding', N'0001_initial', SYSDATETIMEOFFSET()),
    (N'branding', N'0002_seed_default_theme', SYSDATETIMEOFFSET()),
    (N'branding', N'0003_agregar_colores_bootstrap', SYSDATETIMEOFFSET()),
    (N'cartera', N'0004_agregar_modelo_dashboard', SYSDATETIMEOFFSET()),
    (N'cartera', N'0005_seed_dashboard_cartera', SYSDATETIMEOFFSET()),
    (N'cartera', N'0006_eliminar_dashboard_cartera', SYSDATETIMEOFFSET()),
    (N'cartera', N'0007_cargaarchivo_archivo_permanente_nombre_and_more', SYSDATETIMEOFFSET()),
    (N'cartera', N'0008_dashboard_orden_dashboard_parent', SYSDATETIMEOFFSET()),
    (N'cartera', N'0009_dashboard_owner_roles', SYSDATETIMEOFFSET()),
    (N'cartera', N'0010_filaarchivohistorico', SYSDATETIMEOFFSET()),
    (N'cartera', N'0011_cargaarchivo_subido_por', SYSDATETIMEOFFSET()),
    (N'cartera', N'0012_backfill_tablas_historicas', SYSDATETIMEOFFSET()),
    (N'cartera', N'0013_columnahistorica', SYSDATETIMEOFFSET()),
    (N'cartera', N'0014_eliminar_tablas_4_y_5', SYSDATETIMEOFFSET()),
    (N'cartera', N'0015_dashboard_contexto', SYSDATETIMEOFFSET()),
    (N'cartera', N'0016_cargaarchivo_incluir_en_historico', SYSDATETIMEOFFSET()),
    (N'cartera', N'0017_dashboard_fuente_bd', SYSDATETIMEOFFSET()),
    (N'cartera', N'0018_dashboard_fuente_bd_parametros', SYSDATETIMEOFFSET()),
    (N'cartera', N'0019_dashboard_fuente_bd_scheduler', SYSDATETIMEOFFSET()),
    (N'cartera', N'0020_dashboard_fuente_bd_fecha_formato', SYSDATETIMEOFFSET()),
    (N'cartera', N'0021_sembrar_cartera_dashboard_directorio', SYSDATETIMEOFFSET()),
    (N'permissions', N'0001_initial', SYSDATETIMEOFFSET()),
    (N'permissions', N'0002_alter_modulepermission_options', SYSDATETIMEOFFSET()),
    (N'permissions', N'0003_alter_modulepermission_options', SYSDATETIMEOFFSET()),
    (N'permissions', N'0004_alter_modulepermission_options', SYSDATETIMEOFFSET()),
    (N'permissions', N'0005_alter_modulepermission_options', SYSDATETIMEOFFSET()),
    (N'roles', N'0001_initial', SYSDATETIMEOFFSET()),
    (N'roles', N'0002_agregar_dashboard_crear_a_administrador_general', SYSDATETIMEOFFSET()),
    (N'roles', N'0003_agregar_dashboard_editar_eliminar_a_administrador_general', SYSDATETIMEOFFSET()),
    (N'roles', N'0004_agregar_permisos_ia_a_administrador_general', SYSDATETIMEOFFSET()),
    (N'roles', N'0005_agregar_permisos_fuente_bd_a_administrador_general', SYSDATETIMEOFFSET()),
    (N'roles', N'0006_agregar_permiso_cargar_archivo_a_administrador_general', SYSDATETIMEOFFSET()),
    (N'roles', N'0007_agregar_permiso_datos_editar_a_administrador_general', SYSDATETIMEOFFSET()),
    (N'sessions', N'0001_initial', SYSDATETIMEOFFSET()),
    (N'users', N'0002_user_area_user_avatar', SYSDATETIMEOFFSET());
GO

-- ---------------------------------------------------------------------------
-- Cuenta de administrador
-- ---------------------------------------------------------------------------
-- El hash llega por parámetro (`-v SuperadminHash=...`): es un hash Argon2, no la
-- contraseña, y aun así no se guarda en el repositorio. Se genera con:
--     deploy\generar_hash.py
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

PRINT '';
PRINT '== Base lista ==';
GO
