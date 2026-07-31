from django.db.models import Q
from django.utils.dateparse import parse_date, parse_datetime


def _fecha_desde(valor):
    if not valor:
        return None
    return parse_datetime(valor) or parse_date(valor)


def filter_audit_events(queryset, params):
    date_from = _fecha_desde(params.get('date_from'))
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)

    date_to = _fecha_desde(params.get('date_to'))
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)

    for campo in ('domain', 'result', 'severity', 'dashboard_id', 'component_id', 'entity_type', 'ip_address'):
        valor = params.get(campo)
        if valor:
            queryset = queryset.filter(**{campo: valor})

    accion = params.get('action')
    if accion:
        queryset = queryset.filter(action__icontains=accion)

    entidad = params.get('entity_id')
    if entidad:
        queryset = queryset.filter(entity_id=entidad)

    actor = params.get('actor')
    if actor:
        queryset = queryset.filter(Q(actor_id=actor) | Q(actor_username__icontains=actor))

    q = params.get('q')
    if q:
        queryset = queryset.filter(
            Q(action__icontains=q) | Q(message__icontains=q) | Q(entity_name__icontains=q) | Q(actor_username__icontains=q)
        )

    return queryset
