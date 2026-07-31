"""Utilidades genéricas reutilizadas por el servicio de auditoría unificado
(`apps.audit.services.log_event`, Módulo A del trabajo futuro post-integración).

`record_audit_event` (que escribía directamente en `apps.core.AuditLog`) se retiró: desde la
unificación de auditoría, `apps.audit.services.log_event` es el único punto de escritura para
todos los dominios (seguridad, usuarios, roles, permisos, layout de dashboards, etc.). El modelo
`AuditLog` se conserva sin cambios (no se borra su tabla ni sus datos históricos — ver
docs/integracion/decisions.md y future_work_completion_report.md), pero ya no recibe filas
nuevas.
"""

_CLAVES_SENSIBLES = ('password', 'contrasena', 'contraseña', 'token', 'secret', 'refresh', 'access', 'key', 'authorization', 'credential')


def mask_sensitive_fields(valores):
    """Enmascara cualquier clave cuyo nombre contenga un fragmento sensible, sin alterar el resto."""
    if not isinstance(valores, dict):
        return valores
    return {
        clave: ('***' if any(fragmento in clave.lower() for fragmento in _CLAVES_SENSIBLES) else valor)
        for clave, valor in valores.items()
    }


def request_meta(request):
    """IP y user-agent, tolerante a proxies simples (X-Forwarded-For)."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')
    return ip, request.META.get('HTTP_USER_AGENT', '')
