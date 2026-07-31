"""Migración de datos NO destructiva (Módulo A, trabajo futuro post-integración): copia el
historial de `apps.core.AuditLog` y `cartera.DashboardAuditLog` a `AuditEvent`, la nueva fuente
única de auditoría. Las tablas legacy no se tocan (ni se borran filas ni se altera su esquema) —
quedan como archivo histórico de solo lectura; ver docs/audit/unified_audit.md.

Los eventos migrados llevan `metadata.source_audit_system` (`core_auditlog_legacy` /
`dashboard_layout_legacy`) y `metadata.legacy_id` para trazabilidad hacia la fila de origen.
"""

from django.db import migrations

# `apps.get_model(...)` devuelve el modelo histórico (congelado en el estado de esta migración):
# solo tiene los campos de base de datos, no los `TextChoices`/métodos definidos en el código
# actual — por eso los valores de dominio/acción se escriben aquí como literales, no como
# `AuditEvent.Domain.X`.
_DOMINIO_POR_MODULO_LEGACY = {
    'authentication': 'AUTHENTICATION',
    'usuarios': 'USER_MANAGEMENT',
    'roles': 'ROLE_MANAGEMENT',
    'permisos': 'PERMISSION_MANAGEMENT',
    'configuracion': 'SYSTEM_CONFIGURATION',
}

# Excepción puntual dentro del módulo "usuarios": la asignación de permisos es, semánticamente,
# gestión de permisos (mismo criterio ya aplicado en `apps/users/services.py::assign_permissions`
# tras la unificación).
_ACCIONES_PERMISSION_MANAGEMENT = {'user.permissions_assigned'}

_ACCION_LEGACY_A_NUEVA = {
    'user.login_success': 'LOGIN_SUCCESS',
    'user.login_failed': 'LOGIN_FAILED',
    'user.created': 'USER_CREATED',
    'user.updated': 'USER_UPDATED',
    'user.enabled': 'USER_ENABLED',
    'user.disabled': 'USER_DISABLED',
    'user.blocked': 'USER_BLOCKED',
    'user.unblocked': 'USER_UNBLOCKED',
    'user.roles_assigned': 'USER_ROLES_ASSIGNED',
    'user.permissions_assigned': 'USER_PERMISSIONS_ASSIGNED',
    'role.created': 'ROLE_CREATED',
    'role.updated': 'ROLE_UPDATED',
    'role.deleted': 'ROLE_DELETED',
    'branding.updated': 'BRANDING_UPDATED',
    'branding.reset': 'BRANDING_RESET',
    'password.changed_self': 'PASSWORD_CHANGED_SELF',
    'access.denied': 'ACCESS_DENIED',
}

_RESULT_LEGACY_A_NUEVO = {
    'success': 'SUCCESS',
    'failure': 'FAILED',
}

# Mismo criterio que `apps.audit.services._SEVERIDAD_POR_RESULTADO` (los eventos legacy no
# tenían severidad propia; se deriva del resultado para no dejarlos todos en el default INFO).
_SEVERIDAD_POR_RESULTADO_NUEVO = {
    'SUCCESS': 'INFO',
    'FAILED': 'MEDIUM',
    'DENIED': 'MEDIUM',
    'WARNING': 'LOW',
}


def _accion_nueva(accion_legacy):
    return _ACCION_LEGACY_A_NUEVA.get(accion_legacy, accion_legacy.upper().replace('.', '_'))


def _dominio_nuevo(modulo_legacy, accion_legacy):
    if accion_legacy in _ACCIONES_PERMISSION_MANAGEMENT:
        return 'PERMISSION_MANAGEMENT'
    return _DOMINIO_POR_MODULO_LEGACY.get(modulo_legacy, 'SECURITY')


def migrar_historico(apps, schema_editor):
    AuditEvent = apps.get_model('audit', 'AuditEvent')
    AuditLog = apps.get_model('core', 'AuditLog')
    DashboardAuditLog = apps.get_model('cartera', 'DashboardAuditLog')
    User = apps.get_model('users', 'User')

    for legacy in AuditLog.objects.all().order_by('id'):
        actor_username = ''
        if legacy.actor_id:
            usuario = User.objects.filter(pk=legacy.actor_id).first()
            actor_username = usuario.username if usuario else ''

        resultado = _RESULT_LEGACY_A_NUEVO.get(legacy.result, 'SUCCESS')
        nuevo = AuditEvent.objects.create(
            domain=_dominio_nuevo(legacy.module, legacy.action),
            action=_accion_nueva(legacy.action),
            result=resultado,
            severity=_SEVERIDAD_POR_RESULTADO_NUEVO.get(resultado, 'INFO'),
            actor_id=legacy.actor_id,
            actor_username=actor_username,
            entity_type=legacy.target_type or '',
            entity_id=legacy.target_id or '',
            ip_address=legacy.ip_address,
            user_agent=legacy.user_agent or '',
            previous_values=legacy.previous_values or {},
            new_values=legacy.new_values or {},
            metadata={'source_audit_system': 'core_auditlog_legacy', 'legacy_id': str(legacy.pk), 'legacy_module': legacy.module},
        )
        AuditEvent.objects.filter(pk=nuevo.pk).update(created_at=legacy.created_at)

    for legacy in DashboardAuditLog.objects.all().order_by('id'):
        dominio = 'DASHBOARD_CONFIGURATION' if legacy.change_type == 'DISENO_RESTABLECIDO' else 'DASHBOARD_LAYOUT'
        nuevo = AuditEvent.objects.create(
            domain=dominio,
            action=legacy.change_type,
            actor_username=legacy.changed_by or '',
            dashboard_id=legacy.dashboard_id or '',
            component_id=legacy.component_id or '',
            previous_values=legacy.previous_config or {},
            new_values=legacy.new_config or {},
            metadata={
                'source_audit_system': 'dashboard_layout_legacy', 'legacy_id': str(legacy.pk),
                'version': legacy.version, 'changed_by_label': legacy.changed_by or 'Anónimo',
            },
        )
        AuditEvent.objects.filter(pk=nuevo.pk).update(created_at=legacy.changed_at)


def revertir_migracion(apps, schema_editor):
    """Reversible sin tocar las tablas legacy: solo borra los `AuditEvent` que esta migración
    creó (identificables por `metadata.source_audit_system`)."""
    AuditEvent = apps.get_model('audit', 'AuditEvent')
    for evento in AuditEvent.objects.all():
        if (evento.metadata or {}).get('source_audit_system') in ('core_auditlog_legacy', 'dashboard_layout_legacy'):
            evento.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0001_initial'),
        ('core', '0002_initial'),
        ('cartera', '0003_alter_dashboardauditlog_change_type'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrar_historico, revertir_migracion),
    ]
