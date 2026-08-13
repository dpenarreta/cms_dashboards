"""Creación de dashboards por área. Cada dashboard es un contenedor (nombre/área/descripción) que
aloja el mismo pipeline de carga y cálculo de KPIs de cartera — ya no existe un único dashboard
especial con lógica propia: cualquier dashboard creado aquí puede eliminarse igual que cualquier
otro."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils.text import slugify

from apps.audit.models import AuditEvent
from apps.audit.services import log_event

from ..exceptions import CarteraError
from ..models import CargaArchivo, Dashboard, DashboardLayout
from . import plantilla

User = get_user_model()

LONGITUD_MAXIMA_NOMBRE = 150
LONGITUD_MAXIMA_AREA = 100
LONGITUD_MAXIMA_DESCRIPCION = 300
LONGITUD_MAXIMA_CONTEXTO = 3000
# Máximo de pestañas por dashboard (la raíz cuenta como la primera) — sección "pestañas dentro de
# un mismo dashboard".
LIMITE_PESTANAS = 5


def _obtener_dashboard_o_error(dashboard_id):
    try:
        return Dashboard.objects.get(dashboard_id=dashboard_id)
    except Dashboard.DoesNotExist:
        raise CarteraError('El dashboard indicado no existe.', codigo='DASHBOARD_NO_ENCONTRADO')


def _generar_dashboard_id_unico(nombre):
    base = slugify(nombre)[:90] or 'dashboard'
    candidato = base
    sufijo = 2
    # `plantilla.DASHBOARD_ID_PLANTILLA_BASE` está reservado (la plantilla base personalizable de
    # "Configuración") — nunca corresponde a un `Dashboard` real, así que el chequeo de colisión
    # de arriba no lo vería como ocupado por sí solo.
    while Dashboard.objects.filter(dashboard_id=candidato).exists() or candidato == plantilla.DASHBOARD_ID_PLANTILLA_BASE:
        candidato = f'{base}-{sufijo}'
        sufijo += 1
    return candidato


def crear_dashboard(*, nombre, area='', descripcion='', contexto='', creado_por=None, request=None, parent=None, orden=1):
    nombre = (nombre or '').strip()
    if not nombre:
        raise CarteraError('El nombre del dashboard es obligatorio.', codigo='NOMBRE_REQUERIDO')
    if len(nombre) > LONGITUD_MAXIMA_NOMBRE:
        raise CarteraError(f'El nombre no puede superar los {LONGITUD_MAXIMA_NOMBRE} caracteres.', codigo='NOMBRE_DEMASIADO_LARGO')

    area = (area or '').strip()[:LONGITUD_MAXIMA_AREA]
    descripcion = (descripcion or '').strip()[:LONGITUD_MAXIMA_DESCRIPCION]
    contexto = (contexto or '').strip()[:LONGITUD_MAXIMA_CONTEXTO]

    dashboard_id = _generar_dashboard_id_unico(nombre)
    dashboard = Dashboard.objects.create(
        dashboard_id=dashboard_id, name=nombre, area=area, description=descripcion, contexto=contexto,
        created_by=creado_por, owner=creado_por, parent=parent, orden=orden,
    )
    # Todo dashboard nuevo (sea de nivel superior o una pestaña de otro) nace con las 13
    # posiciones fijas de la plantilla (4 KPI, 6 gráficos, 3 tablas) con datos ficticios — nunca
    # vacío. Al cargar un archivo real, esas mismas 13 posiciones se sobreescriben con datos
    # calculados de sus columnas (`plantilla.aplicar_mapeo`). La disposición/tipo de gráfico/
    # color/título de partida son los personalizados en "Configuración → Plantilla base", si los
    # hay (`sembrar_plantilla_desde_base`), o si no los de fábrica (patrón Z).
    plantilla.sembrar_plantilla_desde_base(dashboard_id)

    log_event(
        domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_CREATED',
        actor=creado_por, entity_type='dashboard', entity_id=dashboard.dashboard_id, entity_name=nombre,
        dashboard_id=dashboard.dashboard_id, new_values={'name': nombre, 'area': area},
        metadata={'parent_dashboard_id': parent.dashboard_id} if parent else {},
        request=request,
    )
    return dashboard


def crear_pestana(dashboard_id, *, nombre, actor=None, request=None):
    """Agrega una pestaña nueva (un `Dashboard` más, completamente independiente) a la familia
    del dashboard indicado — "+" en la barra de pestañas funciona igual sin importar en qué
    pestaña esté parado el usuario, siempre se cuelga de la raíz de la familia."""
    dashboard = _obtener_dashboard_o_error(dashboard_id)
    raiz = dashboard.parent or dashboard

    total_actual = 1 + raiz.pestanas.count()
    if total_actual >= LIMITE_PESTANAS:
        raise CarteraError(
            f'Un dashboard no puede tener más de {LIMITE_PESTANAS} pestañas.', codigo='MAXIMO_PESTANAS_ALCANZADO',
        )

    return crear_dashboard(
        nombre=nombre, area=raiz.area, creado_por=actor, request=request,
        parent=raiz, orden=total_actual + 1,
    )


def listar_pestanas(dashboard_id):
    """Todas las pestañas de la familia del dashboard indicado, la raíz primero — se puede llamar
    desde cualquier pestaña de la familia, no solo desde la raíz. Un dashboard sin pestañas
    adicionales todavía devuelve una lista de un elemento (él mismo): "si no hay ninguna, aparece
    la primera"."""
    dashboard = _obtener_dashboard_o_error(dashboard_id)
    raiz = dashboard.parent or dashboard
    familia = [raiz, *raiz.pestanas.order_by('orden')]
    # Se incluye `area` (no solo `dashboard_id`/`name`/`orden`) para que renombrar una pestaña
    # (`DashboardTabsBar` → `PATCH /api/dashboards/<id>/`) pueda reenviar su área actual sin
    # borrarla — `actualizar_dashboard` sobreescribe el área con lo que reciba.
    return [{'dashboard_id': d.dashboard_id, 'name': d.name, 'orden': d.orden, 'area': d.area} for d in familia]


def actualizar_dashboard(dashboard_id, *, nombre, area='', contexto='', actor=None, request=None):
    dashboard = _obtener_dashboard_o_error(dashboard_id)

    nombre = (nombre or '').strip()
    if not nombre:
        raise CarteraError('El nombre del dashboard es obligatorio.', codigo='NOMBRE_REQUERIDO')
    if len(nombre) > LONGITUD_MAXIMA_NOMBRE:
        raise CarteraError(f'El nombre no puede superar los {LONGITUD_MAXIMA_NOMBRE} caracteres.', codigo='NOMBRE_DEMASIADO_LARGO')

    area = (area or '').strip()[:LONGITUD_MAXIMA_AREA]
    contexto = (contexto or '').strip()[:LONGITUD_MAXIMA_CONTEXTO]

    valores_anteriores = {'name': dashboard.name, 'area': dashboard.area}
    dashboard.name = nombre
    dashboard.area = area
    dashboard.contexto = contexto
    dashboard.save(update_fields=['name', 'area', 'contexto'])

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
        # Si `dashboard` es una raíz con pestañas, `dashboard.delete()` va a borrar esas filas
        # `Dashboard` hijas también (on_delete=CASCADE), pero no sabe de `CargaArchivo`/
        # `DashboardLayout` (solo se relacionan por el string `dashboard_id`, no por FK) — hay que
        # limpiarlas a mano por cada pestaña, igual que ya se hace para la raíz misma, para no
        # dejar datos huérfanos.
        ids_a_limpiar = [dashboard.dashboard_id, *dashboard.pestanas.values_list('dashboard_id', flat=True)]
        CargaArchivo.objects.filter(dashboard_id__in=ids_a_limpiar).delete()
        DashboardLayout.objects.filter(dashboard_id__in=ids_a_limpiar).delete()
        dashboard.delete()


def obtener_acceso(dashboard_id):
    """Estado actual del control de acceso de un dashboard (control de acceso por dashboard):
    quién es su dueño y qué roles están en cada uno de los 2 grupos (`roles_editores` puede ver Y
    editar, `roles_lectores` solo puede ver). Un dashboard sin ningún rol asignado en ninguno de
    los 2 grupos no tiene ACL activa — se sigue autorizando por el permiso global de siempre (ver
    `cartera/permisos.py::tiene_acceso_dashboard`)."""
    dashboard = _obtener_dashboard_o_error(dashboard_id)
    return {
        'dashboard_id': dashboard.dashboard_id,
        'owner': {'id': dashboard.owner_id, 'username': dashboard.owner.username} if dashboard.owner_id else None,
        'roles_editores': [{'id': g.id, 'name': g.name} for g in dashboard.roles_editores.order_by('name')],
        'roles_lectores': [{'id': g.id, 'name': g.name} for g in dashboard.roles_lectores.order_by('name')],
    }


def actualizar_acceso(dashboard_id, *, roles_editores_ids, roles_lectores_ids, actor=None, request=None):
    """Reemplaza los 2 grupos de roles de un dashboard — reservado al dueño o al superusuario
    (`permisos.puede_administrar_acceso`, verificado por el llamador). Un rol no puede estar en
    los 2 grupos a la vez: `roles_editores` ya incluye la capacidad de ver, así que repetirlo en
    `roles_lectores` es ambiguo, no un caso a resolver en silencio."""
    dashboard = _obtener_dashboard_o_error(dashboard_id)

    try:
        editores_ids = {int(i) for i in (roles_editores_ids or [])}
        lectores_ids = {int(i) for i in (roles_lectores_ids or [])}
    except (TypeError, ValueError):
        raise CarteraError('Los roles indicados no son válidos.', codigo='ROL_INVALIDO')
    solapados = editores_ids & lectores_ids
    if solapados:
        raise CarteraError(
            'Un rol no puede estar en los dos grupos a la vez.', codigo='ROL_DUPLICADO',
        )

    editores = list(Group.objects.filter(pk__in=editores_ids))
    lectores = list(Group.objects.filter(pk__in=lectores_ids))
    if len(editores) != len(editores_ids) or len(lectores) != len(lectores_ids):
        raise CarteraError('Alguno de los roles indicados no existe.', codigo='ROL_NO_ENCONTRADO')

    valores_anteriores = {
        'roles_editores': sorted(dashboard.roles_editores.values_list('id', flat=True)),
        'roles_lectores': sorted(dashboard.roles_lectores.values_list('id', flat=True)),
    }
    dashboard.roles_editores.set(editores)
    dashboard.roles_lectores.set(lectores)

    log_event(
        domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_ACCESO_ACTUALIZADO',
        actor=actor, entity_type='dashboard', entity_id=dashboard.dashboard_id, entity_name=dashboard.name,
        dashboard_id=dashboard.dashboard_id, previous_values=valores_anteriores,
        new_values={'roles_editores': sorted(editores_ids), 'roles_lectores': sorted(lectores_ids)},
        request=request,
    )
    return obtener_acceso(dashboard_id)


def reasignar_dueno(dashboard_id, *, nuevo_dueno_id, actor=None, request=None):
    """Reasigna el dueño de un dashboard — reservado al superusuario (verificado por el llamador,
    `DashboardDuenoView`, gateado con `IsSuperuser`). `nuevo_dueno_id=None` desasigna el dueño."""
    dashboard = _obtener_dashboard_o_error(dashboard_id)

    nuevo_dueno = None
    if nuevo_dueno_id:
        try:
            nuevo_dueno = User.objects.get(pk=nuevo_dueno_id)
        except User.DoesNotExist:
            raise CarteraError('El usuario indicado no existe.', codigo='USUARIO_NO_ENCONTRADO')

    dueno_anterior_id = dashboard.owner_id
    dashboard.owner = nuevo_dueno
    dashboard.save(update_fields=['owner'])

    log_event(
        domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_DUENO_REASIGNADO',
        actor=actor, entity_type='dashboard', entity_id=dashboard.dashboard_id, entity_name=dashboard.name,
        dashboard_id=dashboard.dashboard_id, previous_values={'owner_id': dueno_anterior_id},
        new_values={'owner_id': nuevo_dueno.id if nuevo_dueno else None},
        request=request,
    )
    return obtener_acceso(dashboard_id)
