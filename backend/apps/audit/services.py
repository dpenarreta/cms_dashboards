"""Único punto de escritura de auditoría (Módulo A). Ninguna vista o servicio debe crear un
`AuditEvent` directamente ni escribir en las tablas legacy (`apps.core.AuditLog`,
`cartera.DashboardAuditLog`) — todas pasan por `log_event`.
"""

import logging

from apps.core.audit import mask_sensitive_fields
from apps.core.audit import request_meta as _request_meta

from .models import AuditEvent

logger = logging.getLogger(__name__)

_SEVERIDAD_POR_RESULTADO = {
    AuditEvent.Result.SUCCESS: AuditEvent.Severity.INFO,
    AuditEvent.Result.WARNING: AuditEvent.Severity.LOW,
    AuditEvent.Result.FAILED: AuditEvent.Severity.MEDIUM,
    AuditEvent.Result.DENIED: AuditEvent.Severity.MEDIUM,
}


def log_event(
    *, domain, action, result=AuditEvent.Result.SUCCESS, severity=None,
    actor=None, entity_type='', entity_id='', entity_name='',
    dashboard_id='', component_id='',
    request=None, request_id='', session_id='', ip_address=None, user_agent='',
    previous_values=None, new_values=None, metadata=None, message='',
):
    """Registra un evento de auditoría. Nunca lanza: una falla al auditar no debe interrumpir la
    operación de negocio que la originó (se registra en el logger de Python y se continúa)."""
    try:
        if request is not None and not ip_address and not user_agent:
            ip_address, user_agent = _request_meta(request)

        usuario = actor if (actor and getattr(actor, 'is_authenticated', False)) else None

        return AuditEvent.objects.create(
            domain=domain,
            action=action,
            result=result,
            severity=severity or _SEVERIDAD_POR_RESULTADO.get(result, AuditEvent.Severity.INFO),
            actor=usuario,
            actor_username=getattr(usuario, 'username', '') or '',
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else '',
            entity_name=entity_name,
            dashboard_id=dashboard_id or '',
            component_id=component_id or '',
            request_id=request_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=(user_agent or '')[:255],
            previous_values=mask_sensitive_fields(previous_values or {}),
            new_values=mask_sensitive_fields(new_values or {}),
            metadata=metadata or {},
            message=message,
        )
    except Exception:
        logger.exception('No se pudo registrar el evento de auditoría (domain=%s, action=%s)', domain, action)
        return None
