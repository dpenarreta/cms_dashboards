-- ============================================================================
-- ESQUEMA COMPLETO — cms_dashboards
-- Documento de REVISIÓN. No ejecutar para crear la base.
--
-- Generado el 2026-09-17 a partir de las 65 migraciones del
-- proyecto (`manage.py sqlmigrate`, una por una, en el orden real de aplicación).
--
-- Para qué sirve: que alguien lea y apruebe las tablas, columnas, tipos, índices y
-- claves foráneas antes de crear la base.
--
-- Para qué NO sirve: para crear la base. Ejecutar esto dejaría la tabla de control
-- `django_migrations` vacía, y la próxima migración del proyecto intentaría crear
-- objetos que ya existen. La base se crea con `deploy\02_crear_esquema_y_superadmin.ps1`.
--
-- Contenido: 26 CREATE TABLE, 28 claves foráneas y 54 índices. La tabla 27 de la base
-- es `django_migrations`, que Django crea por su cuenta antes de aplicar la primera
-- migración y por eso no figura acá.
--
-- Las migraciones de DATOS aparecen marcadas como "Raw Python operation / THIS
-- OPERATION CANNOT BE WRITTEN AS SQL": son las que siembran el rol
-- ADMINISTRADOR_GENERAL con sus permisos, la plantilla del correo de recuperación y el
-- tema visual por defecto. Ejecutan código Python, no SQL, así que su contenido no se
-- puede mostrar en este formato — quedan señaladas en su lugar del orden para que se
-- vea que existen.
-- ============================================================================

-- ===========================================================================
-- contenttypes.0001_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model ContentType
--
CREATE TABLE [django_content_type] ([id] int NOT NULL PRIMARY KEY IDENTITY (1, 1), [name] nvarchar(100) NOT NULL, [app_label] nvarchar(100) NOT NULL, [model] nvarchar(100) NOT NULL);
--
-- Alter unique_together for contenttype (1 constraint(s))
--
CREATE UNIQUE INDEX [django_content_type_app_label_model_76bd3d3b_uniq] ON [django_content_type] ([app_label], [model]) WHERE [app_label] IS NOT NULL AND [model] IS NOT NULL;
COMMIT;
GO

-- ===========================================================================
-- contenttypes.0002_remove_content_type_name
-- ===========================================================================
BEGIN TRANSACTION
--
-- Change Meta options on contenttype
--
-- (no-op)
--
-- Alter field name on contenttype
--
ALTER TABLE [django_content_type] ALTER COLUMN [name] nvarchar(100) NULL;
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
--
-- Remove field name from contenttype
--
ALTER TABLE [django_content_type] DROP COLUMN [name];
COMMIT;
GO

-- ===========================================================================
-- auth.0001_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model Permission
--
CREATE TABLE [auth_permission] ([id] int NOT NULL PRIMARY KEY IDENTITY (1, 1), [name] nvarchar(50) NOT NULL, [content_type_id] int NOT NULL, [codename] nvarchar(100) NOT NULL);
--
-- Create model Group
--
CREATE TABLE [auth_group] ([id] int NOT NULL PRIMARY KEY IDENTITY (1, 1), [name] nvarchar(80) NOT NULL UNIQUE);
CREATE TABLE [auth_group_permissions] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [group_id] int NOT NULL, [permission_id] int NOT NULL);
--
-- Create model User
--
-- (no-op)
CREATE UNIQUE INDEX [auth_permission_content_type_id_codename_01ab375a_uniq] ON [auth_permission] ([content_type_id], [codename]) WHERE [content_type_id] IS NOT NULL AND [codename] IS NOT NULL;
ALTER TABLE [auth_permission] ADD CONSTRAINT [auth_permission_content_type_id_2f476e4b_fk_django_content_type_id] FOREIGN KEY ([content_type_id]) REFERENCES [django_content_type] ([id]);
CREATE INDEX [auth_group_permissions_permission_id_84c5c92e] ON [auth_group_permissions] ([permission_id]);
CREATE INDEX [auth_permission_content_type_id_2f476e4b] ON [auth_permission] ([content_type_id]);
ALTER TABLE [auth_group_permissions] ADD CONSTRAINT [auth_group_permissions_permission_id_84c5c92e_fk_auth_permission_id] FOREIGN KEY ([permission_id]) REFERENCES [auth_permission] ([id]);
CREATE UNIQUE INDEX [auth_group_permissions_group_id_permission_id_0cd325b0_uniq] ON [auth_group_permissions] ([group_id], [permission_id]) WHERE [group_id] IS NOT NULL AND [permission_id] IS NOT NULL;
ALTER TABLE [auth_group_permissions] ADD CONSTRAINT [auth_group_permissions_group_id_b120cbf9_fk_auth_group_id] FOREIGN KEY ([group_id]) REFERENCES [auth_group] ([id]);
CREATE INDEX [auth_group_permissions_group_id_b120cbf9] ON [auth_group_permissions] ([group_id]);
COMMIT;
GO

-- ===========================================================================
-- auth.0002_alter_permission_name_max_length
-- ===========================================================================
BEGIN TRANSACTION
--
-- Alter field name on permission
--
ALTER TABLE [auth_permission] ALTER COLUMN [name] nvarchar(255) NOT NULL;
COMMIT;
GO

-- ===========================================================================
-- auth.0003_alter_user_email_max_length
-- ===========================================================================
BEGIN TRANSACTION
--
-- Alter field email on user
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- auth.0004_alter_user_username_opts
-- ===========================================================================
BEGIN TRANSACTION
--
-- Alter field username on user
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- auth.0005_alter_user_last_login_null
-- ===========================================================================
BEGIN TRANSACTION
--
-- Alter field last_login on user
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- auth.0007_alter_validators_add_error_messages
-- ===========================================================================
BEGIN TRANSACTION
--
-- Alter field username on user
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- auth.0008_alter_user_username_max_length
-- ===========================================================================
BEGIN TRANSACTION
--
-- Alter field username on user
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- auth.0009_alter_user_last_name_max_length
-- ===========================================================================
BEGIN TRANSACTION
--
-- Alter field last_name on user
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- auth.0010_alter_group_name_max_length
-- ===========================================================================
BEGIN TRANSACTION
--
-- Alter field name on group
--
ALTER TABLE [auth_group] DROP CONSTRAINT [auth_group_name_a6ea08ec_uniq];
ALTER TABLE [auth_group] ALTER COLUMN [name] nvarchar(150) NOT NULL;
ALTER TABLE [auth_group] ADD CONSTRAINT [auth_group_name_a6ea08ec_uniq] UNIQUE ([name]);
COMMIT;
GO

-- ===========================================================================
-- auth.0011_update_proxy_permissions
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- auth.0012_alter_user_first_name_max_length
-- ===========================================================================
BEGIN TRANSACTION
--
-- Alter field first_name on user
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- users.0001_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model User
--
CREATE TABLE [users_user] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [password] nvarchar(128) NOT NULL, [last_login] datetimeoffset NULL, [is_superuser] bit NOT NULL, [username] nvarchar(150) NOT NULL UNIQUE, [first_name] nvarchar(150) NOT NULL, [last_name] nvarchar(150) NOT NULL, [is_staff] bit NOT NULL, [is_active] bit NOT NULL, [date_joined] datetimeoffset NOT NULL, [created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [email] nvarchar(254) NOT NULL UNIQUE, [status] nvarchar(20) NOT NULL, [must_change_password] bit NOT NULL, [created_by_id] bigint NULL, [updated_by_id] bigint NULL);
CREATE TABLE [users_user_groups] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [user_id] bigint NOT NULL, [group_id] int NOT NULL);
CREATE TABLE [users_user_user_permissions] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [user_id] bigint NOT NULL, [permission_id] int NOT NULL);
CREATE INDEX [users_user_user_permissions_user_id_20aca447] ON [users_user_user_permissions] ([user_id]);
ALTER TABLE [users_user_groups] ADD CONSTRAINT [users_user_groups_group_id_9afc8d0e_fk_auth_group_id] FOREIGN KEY ([group_id]) REFERENCES [auth_group] ([id]);
ALTER TABLE [users_user_user_permissions] ADD CONSTRAINT [users_user_user_permissions_permission_id_0b93982e_fk_auth_permission_id] FOREIGN KEY ([permission_id]) REFERENCES [auth_permission] ([id]);
CREATE INDEX [users_user_created_by_id_ba0dd846] ON [users_user] ([created_by_id]);
ALTER TABLE [users_user_user_permissions] ADD CONSTRAINT [users_user_user_permissions_user_id_20aca447_fk_users_user_id] FOREIGN KEY ([user_id]) REFERENCES [users_user] ([id]);
ALTER TABLE [users_user] ADD CONSTRAINT [users_user_created_by_id_ba0dd846_fk_users_user_id] FOREIGN KEY ([created_by_id]) REFERENCES [users_user] ([id]);
CREATE INDEX [users_user_groups_user_id_5f6f5a90] ON [users_user_groups] ([user_id]);
ALTER TABLE [users_user] ADD CONSTRAINT [users_user_updated_by_id_82c4d566_fk_users_user_id] FOREIGN KEY ([updated_by_id]) REFERENCES [users_user] ([id]);
ALTER TABLE [users_user_groups] ADD CONSTRAINT [users_user_groups_user_id_5f6f5a90_fk_users_user_id] FOREIGN KEY ([user_id]) REFERENCES [users_user] ([id]);
CREATE UNIQUE INDEX [users_user_user_permissions_user_id_permission_id_43338c45_uniq] ON [users_user_user_permissions] ([user_id], [permission_id]) WHERE [user_id] IS NOT NULL AND [permission_id] IS NOT NULL;
CREATE INDEX [users_user_updated_by_id_82c4d566] ON [users_user] ([updated_by_id]);
CREATE UNIQUE INDEX [users_user_groups_user_id_group_id_b88eab82_uniq] ON [users_user_groups] ([user_id], [group_id]) WHERE [user_id] IS NOT NULL AND [group_id] IS NOT NULL;
CREATE INDEX [users_user_user_permissions_permission_id_0b93982e] ON [users_user_user_permissions] ([permission_id]);
CREATE INDEX [users_user_groups_group_id_9afc8d0e] ON [users_user_groups] ([group_id]);
COMMIT;
GO

-- ===========================================================================
-- admin.0001_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model LogEntry
--
CREATE TABLE [django_admin_log] ([id] int NOT NULL PRIMARY KEY IDENTITY (1, 1), [action_time] datetimeoffset NOT NULL, [object_id] nvarchar(max) NULL, [object_repr] nvarchar(200) NOT NULL, [action_flag] smallint NOT NULL CONSTRAINT django_admin_log_action_flag_a8637d59_check CHECK ([action_flag] >= 0), [change_message] nvarchar(max) NOT NULL, [content_type_id] int NULL, [user_id] bigint NOT NULL);
CREATE INDEX [django_admin_log_user_id_c564eba6] ON [django_admin_log] ([user_id]);
ALTER TABLE [django_admin_log] ADD CONSTRAINT [django_admin_log_content_type_id_c4bce8eb_fk_django_content_type_id] FOREIGN KEY ([content_type_id]) REFERENCES [django_content_type] ([id]);
ALTER TABLE [django_admin_log] ADD CONSTRAINT [django_admin_log_user_id_c564eba6_fk_users_user_id] FOREIGN KEY ([user_id]) REFERENCES [users_user] ([id]);
CREATE INDEX [django_admin_log_content_type_id_c4bce8eb] ON [django_admin_log] ([content_type_id]);
COMMIT;
GO

-- ===========================================================================
-- admin.0002_logentry_remove_auto_add
-- ===========================================================================
BEGIN TRANSACTION
--
-- Alter field action_time on logentry
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- admin.0003_logentry_add_action_flag_choices
-- ===========================================================================
BEGIN TRANSACTION
--
-- Alter field action_flag on logentry
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- core.0001_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model AuditLog
--
CREATE TABLE [core_auditlog] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [action] nvarchar(100) NOT NULL, [module] nvarchar(50) NOT NULL, [target_type] nvarchar(100) NOT NULL, [target_id] nvarchar(64) NOT NULL, [previous_values] nvarchar(max) NOT NULL CONSTRAINT core_auditlog_previous_values_db974116_check CHECK ((ISJSON ("previous_values") = 1)), [new_values] nvarchar(max) NOT NULL CONSTRAINT core_auditlog_new_values_bb53eae1_check CHECK ((ISJSON ("new_values") = 1)), [result] nvarchar(10) NOT NULL, [ip_address] nvarchar(39) NULL, [user_agent] nvarchar(255) NOT NULL);
CREATE INDEX [core_auditlog_module_baadd22e] ON [core_auditlog] ([module]);
CREATE INDEX [core_auditlog_action_978477aa] ON [core_auditlog] ([action]);
COMMIT;
GO

-- ===========================================================================
-- core.0002_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field actor to auditlog
--
ALTER TABLE [core_auditlog] ADD [actor_id] bigint NULL;
CREATE INDEX [core_auditlog_actor_id_ab091f3c] ON [core_auditlog] ([actor_id]);
ALTER TABLE [core_auditlog] ADD CONSTRAINT [core_auditlog_actor_id_ab091f3c_fk_users_user_id] FOREIGN KEY ([actor_id]) REFERENCES [users_user] ([id]);
COMMIT;
GO

-- ===========================================================================
-- cartera.0001_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model CargaArchivo
--
CREATE TABLE [cartera_cargaarchivo] ([id] char(32) NOT NULL PRIMARY KEY, [nombre_original] nvarchar(255) NOT NULL, [nombre_hoja] nvarchar(255) NOT NULL, [tamano_bytes] bigint NOT NULL, [fecha_carga] datetimeoffset NOT NULL, [estado] nvarchar(20) NOT NULL, [fecha_corte] date NULL, [total_filas_excel] int NOT NULL, [filas_validas] int NOT NULL, [filas_advertencia] int NOT NULL, [filas_descartadas] int NOT NULL, [mapeo_columnas] nvarchar(max) NOT NULL CONSTRAINT cartera_cargaarchivo_mapeo_columnas_9e84c854_check CHECK ((ISJSON ("mapeo_columnas") = 1)), [resumen_validacion] nvarchar(max) NOT NULL CONSTRAINT cartera_cargaarchivo_resumen_validacion_121ef9ba_check CHECK ((ISJSON ("resumen_validacion") = 1)), [archivo_temp_nombre] nvarchar(255) NOT NULL);
--
-- Create model RegistroCartera
--
CREATE TABLE [cartera_registrocartera] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [cliente] nvarchar(255) NOT NULL, [ruc_cliente] nvarchar(50) NOT NULL, [codigo_cliente] nvarchar(100) NOT NULL, [identificador_cliente] nvarchar(255) NOT NULL, [sucursal] nvarchar(255) NOT NULL, [ciudad] nvarchar(255) NOT NULL, [zona] nvarchar(255) NOT NULL, [vendedor_ejecutivo] nvarchar(255) NOT NULL, [estado_cliente] nvarchar(100) NOT NULL, [telefono] nvarchar(50) NOT NULL, [direccion] nvarchar(max) NOT NULL, [numero_documento] nvarchar(100) NOT NULL, [fecha_emision] date NULL, [fecha_vencimiento] date NULL, [saldo] numeric(18, 2) NOT NULL, [articulo] nvarchar(255) NOT NULL, [vence_original] nvarchar(100) NOT NULL, [observacion] nvarchar(max) NOT NULL, [mes] nvarchar(50) NOT NULL, [tipo_venta] nvarchar(100) NOT NULL, [causal] nvarchar(100) NOT NULL, [producto] nvarchar(255) NOT NULL, [fecha_compromiso_pago] date NULL, [observaciones] nvarchar(max) NOT NULL, [tipo_cartera] nvarchar(100) NOT NULL, [recuperador] nvarchar(255) NOT NULL, [dias_credito] int NULL, [carga_id] char(32) NOT NULL);
CREATE INDEX [cartera_registrocartera_saldo_2f880fe7] ON [cartera_registrocartera] ([saldo]);
CREATE INDEX [cartera_reg_carga_i_635d5a_idx] ON [cartera_registrocartera] ([carga_id], [fecha_vencimiento]);
CREATE INDEX [cartera_registrocartera_fecha_vencimiento_c86ebe20] ON [cartera_registrocartera] ([fecha_vencimiento]);
CREATE INDEX [cartera_registrocartera_carga_id_68b448fb] ON [cartera_registrocartera] ([carga_id]);
CREATE INDEX [cartera_reg_carga_i_62cddf_idx] ON [cartera_registrocartera] ([carga_id], [ciudad]);
CREATE INDEX [cartera_registrocartera_identificador_cliente_c0e487e0] ON [cartera_registrocartera] ([identificador_cliente]);
ALTER TABLE [cartera_registrocartera] ADD CONSTRAINT [cartera_registrocartera_carga_id_68b448fb_fk_cartera_cargaarchivo_id] FOREIGN KEY ([carga_id]) REFERENCES [cartera_cargaarchivo] ([id]);
CREATE INDEX [cartera_reg_carga_i_c1b23f_idx] ON [cartera_registrocartera] ([carga_id], [recuperador]);
CREATE INDEX [cartera_registrocartera_numero_documento_447bb1c0] ON [cartera_registrocartera] ([numero_documento]);
CREATE INDEX [cartera_registrocartera_recuperador_58630248] ON [cartera_registrocartera] ([recuperador]);
CREATE INDEX [cartera_reg_carga_i_35cd0a_idx] ON [cartera_registrocartera] ([carga_id], [causal]);
CREATE INDEX [cartera_registrocartera_causal_388de230] ON [cartera_registrocartera] ([causal]);
CREATE INDEX [cartera_registrocartera_ciudad_7601c6db] ON [cartera_registrocartera] ([ciudad]);
COMMIT;
GO

-- ===========================================================================
-- cartera.0002_dashboardauditlog_dashboardlayout_dashboardcomponent
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model DashboardAuditLog
--
CREATE TABLE [cartera_dashboardauditlog] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [dashboard_id] nvarchar(100) NOT NULL, [component_id] nvarchar(100) NOT NULL, [change_type] nvarchar(30) NOT NULL, [changed_by] nvarchar(150) NOT NULL, [changed_at] datetimeoffset NOT NULL, [version] int NOT NULL CONSTRAINT cartera_dashboardauditlog_version_82fb4eeb_check CHECK ([version] >= 0), [previous_config] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardauditlog_previous_config_a9fdc814_check CHECK ((ISJSON ("previous_config") = 1)), [new_config] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardauditlog_new_config_ceb58801_check CHECK ((ISJSON ("new_config") = 1)));
--
-- Create model DashboardLayout
--
CREATE TABLE [cartera_dashboardlayout] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [dashboard_id] nvarchar(100) NOT NULL UNIQUE, [version] int NOT NULL CONSTRAINT cartera_dashboardlayout_version_e5169841_check CHECK ([version] >= 0), [scope] nvarchar(20) NOT NULL, [theme] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardlayout_theme_f40738d5_check CHECK ((ISJSON ("theme") = 1)), [actualizado_en] datetimeoffset NOT NULL);
--
-- Create model DashboardComponent
--
CREATE TABLE [cartera_dashboardcomponent] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [component_id] nvarchar(100) NOT NULL, [type] nvarchar(20) NOT NULL, [chart_type] nvarchar(30) NOT NULL, [row] int NOT NULL CONSTRAINT cartera_dashboardcomponent_row_3fecc723_check CHECK ([row] >= 0), [order] int NOT NULL CONSTRAINT cartera_dashboardcomponent_order_4590cccb_check CHECK ([order] >= 0), [width] smallint NOT NULL CONSTRAINT cartera_dashboardcomponent_width_2b3b069f_check CHECK ([width] >= 0), [height] int NOT NULL CONSTRAINT cartera_dashboardcomponent_height_178f9e43_check CHECK ([height] >= 0), [is_visible] bit NOT NULL, [content] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardcomponent_content_33ec3db4_check CHECK ((ISJSON ("content") = 1)), [styles] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardcomponent_styles_0c894d1d_check CHECK ((ISJSON ("styles") = 1)), [config] nvarchar(max) NOT NULL CONSTRAINT cartera_dashboardcomponent_config_bc2dbab5_check CHECK ((ISJSON ("config") = 1)), [layout_id] bigint NOT NULL);
ALTER TABLE [cartera_dashboardcomponent] ADD CONSTRAINT [cartera_dashboardcomponent_layout_id_a1c000bc_fk_cartera_dashboardlayout_id] FOREIGN KEY ([layout_id]) REFERENCES [cartera_dashboardlayout] ([id]);
CREATE INDEX [cartera_dashboardauditlog_component_id_44563a63] ON [cartera_dashboardauditlog] ([component_id]);
CREATE INDEX [cartera_dashboardauditlog_dashboard_id_bec78c2b] ON [cartera_dashboardauditlog] ([dashboard_id]);
CREATE INDEX [cartera_dashboardcomponent_layout_id_a1c000bc] ON [cartera_dashboardcomponent] ([layout_id]);
CREATE UNIQUE INDEX [cartera_dashboardcomponent_layout_id_component_id_8e4f88b3_uniq] ON [cartera_dashboardcomponent] ([layout_id], [component_id]) WHERE [layout_id] IS NOT NULL AND [component_id] IS NOT NULL;
CREATE INDEX [cartera_dashboardcomponent_component_id_5e91a8f1] ON [cartera_dashboardcomponent] ([component_id]);
COMMIT;
GO

-- ===========================================================================
-- cartera.0003_alter_dashboardauditlog_change_type
-- ===========================================================================
BEGIN TRANSACTION
--
-- Alter field change_type on dashboardauditlog
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- audit.0001_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model AuditEvent
--
CREATE TABLE [audit_auditevent] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [domain] nvarchar(30) NOT NULL, [action] nvarchar(100) NOT NULL, [result] nvarchar(10) NOT NULL, [severity] nvarchar(10) NOT NULL, [actor_username] nvarchar(150) NOT NULL, [entity_type] nvarchar(100) NOT NULL, [entity_id] nvarchar(64) NOT NULL, [entity_name] nvarchar(255) NOT NULL, [dashboard_id] nvarchar(100) NOT NULL, [component_id] nvarchar(100) NOT NULL, [request_id] nvarchar(64) NOT NULL, [session_id] nvarchar(64) NOT NULL, [ip_address] nvarchar(39) NULL, [user_agent] nvarchar(255) NOT NULL, [previous_values] nvarchar(max) NOT NULL CONSTRAINT audit_auditevent_previous_values_dec45c1c_check CHECK ((ISJSON ("previous_values") = 1)), [new_values] nvarchar(max) NOT NULL CONSTRAINT audit_auditevent_new_values_9e970336_check CHECK ((ISJSON ("new_values") = 1)), [metadata] nvarchar(max) NOT NULL CONSTRAINT audit_auditevent_metadata_7d01b378_check CHECK ((ISJSON ("metadata") = 1)), [message] nvarchar(500) NOT NULL, [created_at] datetimeoffset NOT NULL, [actor_id] bigint NULL);
CREATE INDEX [audit_auditevent_severity_89be939a] ON [audit_auditevent] ([severity]);
CREATE INDEX [audit_auditevent_result_49d270e2] ON [audit_auditevent] ([result]);
CREATE INDEX [audit_auditevent_dashboard_id_47d2ae6d] ON [audit_auditevent] ([dashboard_id]);
CREATE INDEX [audit_auditevent_action_2131bb77] ON [audit_auditevent] ([action]);
CREATE INDEX [audit_auditevent_created_at_58e81936] ON [audit_auditevent] ([created_at]);
ALTER TABLE [audit_auditevent] ADD CONSTRAINT [audit_auditevent_actor_id_270bb4b7_fk_users_user_id] FOREIGN KEY ([actor_id]) REFERENCES [users_user] ([id]);
CREATE INDEX [audit_auditevent_actor_id_270bb4b7] ON [audit_auditevent] ([actor_id]);
CREATE INDEX [audit_auditevent_domain_3f23c8b0] ON [audit_auditevent] ([domain]);
COMMIT;
GO

-- ===========================================================================
-- audit.0002_migrar_historico_legacy
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- authentication.0001_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model LoginAttempt
--
CREATE TABLE [authentication_loginattempt] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [identifier] nvarchar(255) NOT NULL, [ip_address] nvarchar(39) NULL, [successful] bit NOT NULL);
--
-- Create model Session
--
CREATE TABLE [authentication_session] ([created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [id] char(32) NOT NULL PRIMARY KEY, [refresh_token_jti] nvarchar(64) NOT NULL UNIQUE, [device] nvarchar(255) NOT NULL, [user_agent] nvarchar(255) NOT NULL, [ip_address] nvarchar(39) NULL, [last_used_at] datetimeoffset NOT NULL, [expires_at] datetimeoffset NOT NULL, [revoked_at] datetimeoffset NULL);
CREATE INDEX [authentication_loginattempt_identifier_16a5398a] ON [authentication_loginattempt] ([identifier]);
COMMIT;
GO

-- ===========================================================================
-- authentication.0002_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field user to loginattempt
--
ALTER TABLE [authentication_loginattempt] ADD [user_id] bigint NULL;
--
-- Add field user to session
--
ALTER TABLE [authentication_session] ADD [user_id] bigint NOT NULL;
CREATE INDEX [authentication_loginattempt_user_id_253ccbc6] ON [authentication_loginattempt] ([user_id]);
ALTER TABLE [authentication_loginattempt] ADD CONSTRAINT [authentication_loginattempt_user_id_253ccbc6_fk_users_user_id] FOREIGN KEY ([user_id]) REFERENCES [users_user] ([id]);
CREATE INDEX [authentication_session_user_id_c9667cdb] ON [authentication_session] ([user_id]);
ALTER TABLE [authentication_session] ADD CONSTRAINT [authentication_session_user_id_c9667cdb_fk_users_user_id] FOREIGN KEY ([user_id]) REFERENCES [users_user] ([id]);
COMMIT;
GO

-- ===========================================================================
-- authentication.0003_passwordresettoken
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model PasswordResetToken
--
CREATE TABLE [authentication_passwordresettoken] ([created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [id] char(32) NOT NULL PRIMARY KEY, [token_hash] nvarchar(64) NOT NULL UNIQUE, [expires_at] datetimeoffset NOT NULL, [used_at] datetimeoffset NULL, [user_id] bigint NOT NULL);
CREATE INDEX [authentication_passwordresettoken_user_id_167c3ac5] ON [authentication_passwordresettoken] ([user_id]);
ALTER TABLE [authentication_passwordresettoken] ADD CONSTRAINT [authentication_passwordresettoken_user_id_167c3ac5_fk_users_user_id] FOREIGN KEY ([user_id]) REFERENCES [users_user] ([id]);
COMMIT;
GO

-- ===========================================================================
-- authentication.0004_emailtemplate
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model EmailTemplate
--
CREATE TABLE [authentication_emailtemplate] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [key] nvarchar(50) NOT NULL UNIQUE, [subject] nvarchar(200) NOT NULL, [html_body] nvarchar(max) NOT NULL, [updated_by_id] bigint NULL);
CREATE INDEX [authentication_emailtemplate_updated_by_id_081040d7] ON [authentication_emailtemplate] ([updated_by_id]);
ALTER TABLE [authentication_emailtemplate] ADD CONSTRAINT [authentication_emailtemplate_updated_by_id_081040d7_fk_users_user_id] FOREIGN KEY ([updated_by_id]) REFERENCES [users_user] ([id]);
COMMIT;
GO

-- ===========================================================================
-- authentication.0005_seed_password_reset_email_template
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- branding.0001_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model SiteTheme
--
CREATE TABLE [branding_sitetheme] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [created_at] datetimeoffset NOT NULL, [updated_at] datetimeoffset NOT NULL, [site_name] nvarchar(150) NOT NULL, [short_name] nvarchar(50) NOT NULL, [logo_url] nvarchar(500) NOT NULL, [favicon_url] nvarchar(500) NOT NULL, [color_primary] nvarchar(7) NOT NULL, [color_secondary] nvarchar(7) NOT NULL, [color_background] nvarchar(7) NOT NULL, [color_headings] nvarchar(7) NOT NULL, [color_text] nvarchar(7) NOT NULL, [color_links] nvarchar(7) NOT NULL, [color_buttons] nvarchar(7) NOT NULL, [color_menu] nvarchar(7) NOT NULL, [font_primary] nvarchar(20) NOT NULL, [font_secondary] nvarchar(20) NOT NULL, [font_size_base] nvarchar(10) NOT NULL, [border_radius] nvarchar(20) NOT NULL);
COMMIT;
GO

-- ===========================================================================
-- branding.0002_seed_default_theme
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- branding.0003_agregar_colores_bootstrap
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field color_button_text to sitetheme
--
ALTER TABLE [branding_sitetheme] ADD [color_button_text] nvarchar(7) DEFAULT '#ffffff' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'branding_sitetheme' AND c.name = 'color_button_text';
ALTER TABLE [branding_sitetheme] DROP CONSTRAINT [color_button_text];
--
-- Add field color_danger to sitetheme
--
ALTER TABLE [branding_sitetheme] ADD [color_danger] nvarchar(7) DEFAULT '#dc3545' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'branding_sitetheme' AND c.name = 'color_danger';
ALTER TABLE [branding_sitetheme] DROP CONSTRAINT [color_danger];
--
-- Add field color_info to sitetheme
--
ALTER TABLE [branding_sitetheme] ADD [color_info] nvarchar(7) DEFAULT '#0dcaf0' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'branding_sitetheme' AND c.name = 'color_info';
ALTER TABLE [branding_sitetheme] DROP CONSTRAINT [color_info];
--
-- Add field color_success to sitetheme
--
ALTER TABLE [branding_sitetheme] ADD [color_success] nvarchar(7) DEFAULT '#198754' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'branding_sitetheme' AND c.name = 'color_success';
ALTER TABLE [branding_sitetheme] DROP CONSTRAINT [color_success];
--
-- Add field color_warning to sitetheme
--
ALTER TABLE [branding_sitetheme] ADD [color_warning] nvarchar(7) DEFAULT '#ffc107' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'branding_sitetheme' AND c.name = 'color_warning';
ALTER TABLE [branding_sitetheme] DROP CONSTRAINT [color_warning];
COMMIT;
GO

-- ===========================================================================
-- cartera.0004_agregar_modelo_dashboard
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field dashboard_id to cargaarchivo
--
ALTER TABLE [cartera_cargaarchivo] ADD [dashboard_id] nvarchar(100) DEFAULT 'cartera' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_cargaarchivo' AND c.name = 'dashboard_id';
ALTER TABLE [cartera_cargaarchivo] DROP CONSTRAINT [dashboard_id];
--
-- Create model Dashboard
--
CREATE TABLE [cartera_dashboard] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [dashboard_id] nvarchar(100) NOT NULL UNIQUE, [name] nvarchar(150) NOT NULL, [area] nvarchar(100) NOT NULL, [description] nvarchar(300) NOT NULL, [created_at] datetimeoffset NOT NULL, [created_by_id] bigint NULL);
CREATE INDEX [cartera_cargaarchivo_dashboard_id_b5e4094b] ON [cartera_cargaarchivo] ([dashboard_id]);
ALTER TABLE [cartera_dashboard] ADD CONSTRAINT [cartera_dashboard_created_by_id_42025471_fk_users_user_id] FOREIGN KEY ([created_by_id]) REFERENCES [users_user] ([id]);
CREATE INDEX [cartera_dashboard_created_by_id_42025471] ON [cartera_dashboard] ([created_by_id]);
COMMIT;
GO

-- ===========================================================================
-- cartera.0005_seed_dashboard_cartera
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- cartera.0006_eliminar_dashboard_cartera
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- cartera.0007_cargaarchivo_archivo_permanente_nombre_and_more
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field archivo_permanente_nombre to cargaarchivo
--
ALTER TABLE [cartera_cargaarchivo] ADD [archivo_permanente_nombre] nvarchar(255) DEFAULT '' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_cargaarchivo' AND c.name = 'archivo_permanente_nombre';
ALTER TABLE [cartera_cargaarchivo] DROP CONSTRAINT [archivo_permanente_nombre];
--
-- Add field mapeo to dashboardcomponent
--
ALTER TABLE [cartera_dashboardcomponent] ADD [mapeo] nvarchar(max) DEFAULT '{}' NOT NULL CHECK ((ISJSON ("mapeo") = 1));
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_dashboardcomponent' AND c.name = 'mapeo';
ALTER TABLE [cartera_dashboardcomponent] DROP CONSTRAINT [mapeo];
COMMIT;
GO

-- ===========================================================================
-- cartera.0008_dashboard_orden_dashboard_parent
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field orden to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [orden] int DEFAULT 1 NOT NULL CHECK ([orden] >= 0);
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_dashboard' AND c.name = 'orden';
ALTER TABLE [cartera_dashboard] DROP CONSTRAINT [orden];
--
-- Add field parent to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [parent_id] bigint NULL;
CREATE INDEX [cartera_dashboard_parent_id_44e0b45f] ON [cartera_dashboard] ([parent_id]);
ALTER TABLE [cartera_dashboard] ADD CONSTRAINT [cartera_dashboard_parent_id_44e0b45f_fk_cartera_dashboard_id] FOREIGN KEY ([parent_id]) REFERENCES [cartera_dashboard] ([id]);
COMMIT;
GO

-- ===========================================================================
-- cartera.0009_dashboard_owner_roles
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field owner to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [owner_id] bigint NULL;
--
-- Add field roles_editores to dashboard
--
CREATE TABLE [cartera_dashboard_roles_editores] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [dashboard_id] bigint NOT NULL, [group_id] int NOT NULL);
--
-- Add field roles_lectores to dashboard
--
CREATE TABLE [cartera_dashboard_roles_lectores] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [dashboard_id] bigint NOT NULL, [group_id] int NOT NULL);
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
ALTER TABLE [cartera_dashboard_roles_lectores] ADD CONSTRAINT [cartera_dashboard_roles_lectores_dashboard_id_86877019_fk_cartera_dashboard_id] FOREIGN KEY ([dashboard_id]) REFERENCES [cartera_dashboard] ([id]);
CREATE INDEX [cartera_dashboard_owner_id_a70ba7e7] ON [cartera_dashboard] ([owner_id]);
ALTER TABLE [cartera_dashboard_roles_lectores] ADD CONSTRAINT [cartera_dashboard_roles_lectores_group_id_b69b45b3_fk_auth_group_id] FOREIGN KEY ([group_id]) REFERENCES [auth_group] ([id]);
CREATE INDEX [cartera_dashboard_roles_editores_group_id_08a7f9e2] ON [cartera_dashboard_roles_editores] ([group_id]);
ALTER TABLE [cartera_dashboard_roles_editores] ADD CONSTRAINT [cartera_dashboard_roles_editores_group_id_08a7f9e2_fk_auth_group_id] FOREIGN KEY ([group_id]) REFERENCES [auth_group] ([id]);
CREATE UNIQUE INDEX [cartera_dashboard_roles_lectores_dashboard_id_group_id_90e0462d_uniq] ON [cartera_dashboard_roles_lectores] ([dashboard_id], [group_id]) WHERE [dashboard_id] IS NOT NULL AND [group_id] IS NOT NULL;
CREATE INDEX [cartera_dashboard_roles_lectores_group_id_b69b45b3] ON [cartera_dashboard_roles_lectores] ([group_id]);
ALTER TABLE [cartera_dashboard_roles_editores] ADD CONSTRAINT [cartera_dashboard_roles_editores_dashboard_id_406132bf_fk_cartera_dashboard_id] FOREIGN KEY ([dashboard_id]) REFERENCES [cartera_dashboard] ([id]);
CREATE INDEX [cartera_dashboard_roles_editores_dashboard_id_406132bf] ON [cartera_dashboard_roles_editores] ([dashboard_id]);
CREATE INDEX [cartera_dashboard_roles_lectores_dashboard_id_86877019] ON [cartera_dashboard_roles_lectores] ([dashboard_id]);
CREATE UNIQUE INDEX [cartera_dashboard_roles_editores_dashboard_id_group_id_0b4071e2_uniq] ON [cartera_dashboard_roles_editores] ([dashboard_id], [group_id]) WHERE [dashboard_id] IS NOT NULL AND [group_id] IS NOT NULL;
ALTER TABLE [cartera_dashboard] ADD CONSTRAINT [cartera_dashboard_owner_id_a70ba7e7_fk_users_user_id] FOREIGN KEY ([owner_id]) REFERENCES [users_user] ([id]);
COMMIT;
GO

-- ===========================================================================
-- cartera.0010_filaarchivohistorico
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model FilaArchivoHistorico
--
CREATE TABLE [cartera_filaarchivohistorico] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [orden] int NOT NULL CONSTRAINT cartera_filaarchivohistorico_orden_2340da53_check CHECK ([orden] >= 0), [datos] nvarchar(max) NOT NULL CONSTRAINT cartera_filaarchivohistorico_datos_7847350f_check CHECK ((ISJSON ("datos") = 1)), [carga_id] char(32) NOT NULL);
CREATE INDEX [cartera_filaarchivohistorico_carga_id_493c7247] ON [cartera_filaarchivohistorico] ([carga_id]);
ALTER TABLE [cartera_filaarchivohistorico] ADD CONSTRAINT [cartera_filaarchivohistorico_carga_id_493c7247_fk_cartera_cargaarchivo_id] FOREIGN KEY ([carga_id]) REFERENCES [cartera_cargaarchivo] ([id]);
COMMIT;
GO

-- ===========================================================================
-- cartera.0011_cargaarchivo_subido_por
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field subido_por to cargaarchivo
--
ALTER TABLE [cartera_cargaarchivo] ADD [subido_por_id] bigint NULL;
CREATE INDEX [cartera_cargaarchivo_subido_por_id_15720237] ON [cartera_cargaarchivo] ([subido_por_id]);
ALTER TABLE [cartera_cargaarchivo] ADD CONSTRAINT [cartera_cargaarchivo_subido_por_id_15720237_fk_users_user_id] FOREIGN KEY ([subido_por_id]) REFERENCES [users_user] ([id]);
COMMIT;
GO

-- ===========================================================================
-- cartera.0012_backfill_tablas_historicas
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- cartera.0013_columnahistorica
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model ColumnaHistorica
--
CREATE TABLE [cartera_columnahistorica] ([id] bigint NOT NULL PRIMARY KEY IDENTITY (1, 1), [dashboard_id] nvarchar(100) NOT NULL, [columna] nvarchar(200) NOT NULL);
CREATE UNIQUE INDEX [cartera_columnahistorica_dashboard_id_columna_fda23d01_uniq] ON [cartera_columnahistorica] ([dashboard_id], [columna]) WHERE [dashboard_id] IS NOT NULL AND [columna] IS NOT NULL;
CREATE INDEX [cartera_columnahistorica_dashboard_id_6557fe99] ON [cartera_columnahistorica] ([dashboard_id]);
COMMIT;
GO

-- ===========================================================================
-- cartera.0014_eliminar_tablas_4_y_5
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- cartera.0015_dashboard_contexto
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field contexto to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [contexto] nvarchar(max) DEFAULT '' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_dashboard' AND c.name = 'contexto';
ALTER TABLE [cartera_dashboard] DROP CONSTRAINT [contexto];
COMMIT;
GO

-- ===========================================================================
-- cartera.0016_cargaarchivo_incluir_en_historico
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field incluir_en_historico to cargaarchivo
--
ALTER TABLE [cartera_cargaarchivo] ADD [incluir_en_historico] bit DEFAULT 1 NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_cargaarchivo' AND c.name = 'incluir_en_historico';
ALTER TABLE [cartera_cargaarchivo] DROP CONSTRAINT [incluir_en_historico];
COMMIT;
GO

-- ===========================================================================
-- cartera.0017_dashboard_fuente_bd
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field fuente_bd_nombre to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [fuente_bd_nombre] nvarchar(255) DEFAULT '' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_dashboard' AND c.name = 'fuente_bd_nombre';
ALTER TABLE [cartera_dashboard] DROP CONSTRAINT [fuente_bd_nombre];
--
-- Add field fuente_bd_tipo to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [fuente_bd_tipo] nvarchar(20) DEFAULT '' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_dashboard' AND c.name = 'fuente_bd_tipo';
ALTER TABLE [cartera_dashboard] DROP CONSTRAINT [fuente_bd_tipo];
COMMIT;
GO

-- ===========================================================================
-- cartera.0018_dashboard_fuente_bd_parametros
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field fuente_bd_parametros to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [fuente_bd_parametros] nvarchar(max) DEFAULT '{}' NOT NULL CHECK ((ISJSON ("fuente_bd_parametros") = 1));
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_dashboard' AND c.name = 'fuente_bd_parametros';
ALTER TABLE [cartera_dashboard] DROP CONSTRAINT [fuente_bd_parametros];
COMMIT;
GO

-- ===========================================================================
-- cartera.0019_dashboard_fuente_bd_scheduler
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field fuente_bd_fecha_configuracion to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [fuente_bd_fecha_configuracion] date NULL;
--
-- Add field fuente_bd_frecuencia_actualizacion to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [fuente_bd_frecuencia_actualizacion] nvarchar(20) DEFAULT '' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_dashboard' AND c.name = 'fuente_bd_frecuencia_actualizacion';
ALTER TABLE [cartera_dashboard] DROP CONSTRAINT [fuente_bd_frecuencia_actualizacion];
--
-- Add field fuente_bd_ultima_actualizacion_automatica to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [fuente_bd_ultima_actualizacion_automatica] date NULL;
--
-- Add field fuente_bd_ultimo_aliases to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [fuente_bd_ultimo_aliases] nvarchar(max) DEFAULT '{}' NOT NULL CHECK ((ISJSON ("fuente_bd_ultimo_aliases") = 1));
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_dashboard' AND c.name = 'fuente_bd_ultimo_aliases';
ALTER TABLE [cartera_dashboard] DROP CONSTRAINT [fuente_bd_ultimo_aliases];
--
-- Add field fuente_bd_ultimo_mapeo to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [fuente_bd_ultimo_mapeo] nvarchar(max) DEFAULT '{}' NOT NULL CHECK ((ISJSON ("fuente_bd_ultimo_mapeo") = 1));
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_dashboard' AND c.name = 'fuente_bd_ultimo_mapeo';
ALTER TABLE [cartera_dashboard] DROP CONSTRAINT [fuente_bd_ultimo_mapeo];
COMMIT;
GO

-- ===========================================================================
-- cartera.0020_dashboard_fuente_bd_fecha_formato
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field fuente_bd_fecha_formato to dashboard
--
ALTER TABLE [cartera_dashboard] ADD [fuente_bd_fecha_formato] nvarchar(30) DEFAULT 'YYYY-MM-DD' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'cartera_dashboard' AND c.name = 'fuente_bd_fecha_formato';
ALTER TABLE [cartera_dashboard] DROP CONSTRAINT [fuente_bd_fecha_formato];
COMMIT;
GO

-- ===========================================================================
-- cartera.0021_sembrar_cartera_dashboard_directorio
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- permissions.0001_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model ModulePermission
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- permissions.0002_alter_modulepermission_options
-- ===========================================================================
BEGIN TRANSACTION
--
-- Change Meta options on modulepermission
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- permissions.0003_alter_modulepermission_options
-- ===========================================================================
BEGIN TRANSACTION
--
-- Change Meta options on modulepermission
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- permissions.0004_alter_modulepermission_options
-- ===========================================================================
BEGIN TRANSACTION
--
-- Change Meta options on modulepermission
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- permissions.0005_alter_modulepermission_options
-- ===========================================================================
BEGIN TRANSACTION
--
-- Change Meta options on modulepermission
--
-- (no-op)
COMMIT;
GO

-- ===========================================================================
-- roles.0001_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- roles.0002_agregar_dashboard_crear_a_administrador_general
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- roles.0003_agregar_dashboard_editar_eliminar_a_administrador_general
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- roles.0004_agregar_permisos_ia_a_administrador_general
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- roles.0005_agregar_permisos_fuente_bd_a_administrador_general
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- roles.0006_agregar_permiso_cargar_archivo_a_administrador_general
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- roles.0007_agregar_permiso_datos_editar_a_administrador_general
-- ===========================================================================
BEGIN TRANSACTION
--
-- Raw Python operation
--
-- THIS OPERATION CANNOT BE WRITTEN AS SQL
COMMIT;
GO

-- ===========================================================================
-- sessions.0001_initial
-- ===========================================================================
BEGIN TRANSACTION
--
-- Create model Session
--
CREATE TABLE [django_session] ([session_key] nvarchar(40) NOT NULL PRIMARY KEY, [session_data] nvarchar(max) NOT NULL, [expire_date] datetimeoffset NOT NULL);
CREATE INDEX [django_session_expire_date_a5c62663] ON [django_session] ([expire_date]);
COMMIT;
GO

-- ===========================================================================
-- users.0002_user_area_user_avatar
-- ===========================================================================
BEGIN TRANSACTION
--
-- Add field area to user
--
ALTER TABLE [users_user] ADD [area] nvarchar(100) DEFAULT '' NOT NULL;
SELECT d.name FROM sys.default_constraints d INNER JOIN sys.tables t ON d.parent_object_id = t.object_id INNER JOIN sys.columns c ON d.parent_object_id = c.object_id AND d.parent_column_id = c.column_id INNER JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE t.name = 'users_user' AND c.name = 'area';
ALTER TABLE [users_user] DROP CONSTRAINT [area];
--
-- Add field avatar to user
--
ALTER TABLE [users_user] ADD [avatar] nvarchar(100) NULL;
COMMIT;
GO
