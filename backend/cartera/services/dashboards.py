"""Creación de dashboards por área. Cada dashboard es un contenedor (nombre/área/descripción) que
aloja el mismo pipeline de carga y cálculo de KPIs de cartera — ya no existe un único dashboard
especial con lógica propia: cualquier dashboard creado aquí puede eliminarse igual que cualquier
otro."""

from django.db import transaction
from django.utils.text import slugify

from apps.audit.models import AuditEvent
from apps.audit.services import log_event

from ..exceptions import CarteraError
from ..models import CargaArchivo, Dashboard, DashboardLayout

LONGITUD_MAXIMA_NOMBRE = 150
LONGITUD_MAXIMA_AREA = 100
LONGITUD_MAXIMA_DESCRIPCION = 300


def _obtener_dashboard_o_error(dashboard_id):
    try:
        return Dashboard.objects.get(dashboard_id=dashboard_id)
    except Dashboard.DoesNotExist:
        raise CarteraError('El dashboard indicado no existe.', codigo='DASHBOARD_NO_ENCONTRADO')


def _generar_dashboard_id_unico(nombre):
    base = slugify(nombre)[:90] or 'dashboard'
    candidato = base
    sufijo = 2
    while Dashboard.objects.filter(dashboard_id=candidato).exists():
        candidato = f'{base}-{sufijo}'
        sufijo += 1
    return candidato


def crear_dashboard(*, nombre, area='', descripcion='', creado_por=None, request=None):
    nombre = (nombre or '').strip()
    if not nombre:
        raise CarteraError('El nombre del dashboard es obligatorio.', codigo='NOMBRE_REQUERIDO')
    if len(nombre) > LONGITUD_MAXIMA_NOMBRE:
        raise CarteraError(f'El nombre no puede superar los {LONGITUD_MAXIMA_NOMBRE} caracteres.', codigo='NOMBRE_DEMASIADO_LARGO')

    area = (area or '').strip()[:LONGITUD_MAXIMA_AREA]
    descripcion = (descripcion or '').strip()[:LONGITUD_MAXIMA_DESCRIPCION]

    dashboard_id = _generar_dashboard_id_unico(nombre)
    dashboard = Dashboard.objects.create(
        dashboard_id=dashboard_id, name=nombre, area=area, description=descripcion, created_by=creado_por,
    )

    log_event(
        domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_CREATED',
        actor=creado_por, entity_type='dashboard', entity_id=dashboard.dashboard_id, entity_name=nombre,
        dashboard_id=dashboard.dashboard_id, new_values={'name': nombre, 'area': area},
        request=request,
    )
    return dashboard


def actualizar_dashboard(dashboard_id, *, nombre, area='', actor=None, request=None):
    dashboard = _obtener_dashboard_o_error(dashboard_id)

    nombre = (nombre or '').strip()
    if not nombre:
        raise CarteraError('El nombre del dashboard es obligatorio.', codigo='NOMBRE_REQUERIDO')
    if len(nombre) > LONGITUD_MAXIMA_NOMBRE:
        raise CarteraError(f'El nombre no puede superar los {LONGITUD_MAXIMA_NOMBRE} caracteres.', codigo='NOMBRE_DEMASIADO_LARGO')

    area = (area or '').strip()[:LONGITUD_MAXIMA_AREA]

    valores_anteriores = {'name': dashboard.name, 'area': dashboard.area}
    dashboard.name = nombre
    dashboard.area = area
    dashboard.save(update_fields=['name', 'area'])

    log_event(
        domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_UPDATED',
        actor=actor, entity_type='dashboard', entity_id=dashboard.dashboard_id, entity_name=nombre,
        dashboard_id=dashboard.dashboard_id,
        previous_values=valores_anteriores, new_values={'name': nombre, 'area': area},
        request=request,
    )
    return dashboard


def eliminar_dashboard(dashboard_id, *, confirmacion_nombre, actor=None, request=None):
    dashboard = _obtener_dashboard_o_error(dashboard_id)

    if (confirmacion_nombre or '').strip() != dashboard.name:
        raise CarteraError(
            'El nombre ingresado no coincide con el nombre del dashboard.', codigo='CONFIRMACION_INVALIDA',
        )

    nombre, area = dashboard.name, dashboard.area

    log_event(
        domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_DELETED',
        actor=actor, entity_type='dashboard', entity_id=dashboard.dashboard_id, entity_name=nombre,
        dashboard_id=dashboard.dashboard_id, previous_values={'name': nombre, 'area': area},
        request=request,
    )

    with transaction.atomic():
        CargaArchivo.objects.filter(dashboard_id=dashboard.dashboard_id).delete()
        DashboardLayout.objects.filter(dashboard_id=dashboard.dashboard_id).delete()
        dashboard.delete()
