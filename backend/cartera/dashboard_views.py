from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditEvent
from apps.permissions.permissions import IsSuperuser, require_permission

from . import dashboard_registry, permisos
from .exceptions import CarteraError
from .services import dashboard_interpretation
from .services import dashboard_layout as dl
from .services import dashboards as dashboards_service


def _permisos_respuesta(request):
    return permisos.permisos_del_usuario(request)


class DashboardLayoutView(APIView):
    def get(self, request, dashboard_id):
        if not permisos.tiene_acceso_dashboard(request, dashboard_id, permiso_global=permisos.DASHBOARD_VIEW):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para ver este dashboard.'}, status=403)

        layout = dl.obtener_o_crear_layout(dashboard_id)
        return Response({**dl.serializar_layout(layout), 'permisos': _permisos_respuesta(request)})

    def put(self, request, dashboard_id):
        if not permisos.tiene_acceso_dashboard(request, dashboard_id, permiso_global=permisos.DASHBOARD_LAYOUT_EDIT, requiere_edicion=True):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para editar el layout.'}, status=403)

        version_recibida = request.data.get('version')
        if version_recibida is None:
            raise CarteraError('Se requiere la versión del layout que se está editando.', codigo='VERSION_REQUERIDA')

        layout_actual = dl.obtener_o_crear_layout(dashboard_id)
        if int(version_recibida) != layout_actual.version:
            return Response({
                'error': 'CONFLICTO_DE_VERSION',
                'mensaje': 'Existe una versión más reciente de este dashboard. Recargue antes de guardar.',
                **dl.serializar_layout(layout_actual),
            }, status=409)

        componentes = dl.validar_componentes(dashboard_id, request.data.get('components') or [])
        changed_by = (request.data.get('changed_by') or 'Anónimo')[:150]
        layout = dl.aplicar_layout(dashboard_id, componentes, changed_by, actor=request.user, request=request)

        return Response(dl.serializar_layout(layout))


class DashboardComponentePresentacionalView(APIView):
    """`POST /api/dashboards/<dashboard_id>/componentes-presentacionales` — agrega un componente
    de solo presentación (título o separador, panel lateral de componentes del editor de
    dashboard, sección "Zona Personal") sin necesitar ningún archivo cargado — a diferencia de
    `AgregarGraficaView` (`cartera/views.py`), que sí lo requiere para calcular datos."""

    def post(self, request, dashboard_id):
        if not permisos.tiene_acceso_dashboard(request, dashboard_id, permiso_global=permisos.DASHBOARD_LAYOUT_EDIT, requiere_edicion=True):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para editar el layout.'}, status=403)

        tipo = request.data.get('tipo')
        ancho_columnas = request.data.get('ancho_columnas') or None
        zona = request.data.get('zona') or None
        layout = dl.agregar_componente_presentacional(
            dashboard_id, tipo, ancho_columnas=ancho_columnas, zona=zona, actor=request.user, request=request,
        )
        return Response(dl.serializar_layout(layout), status=201)


class DashboardLayoutResetView(APIView):
    def post(self, request, dashboard_id):
        if not permisos.tiene_acceso_dashboard(request, dashboard_id, permiso_global=permisos.DASHBOARD_CONFIGURATION_RESET, requiere_edicion=True):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para restablecer el diseño.'}, status=403)

        changed_by = (request.data.get('changed_by') or 'Anónimo')[:150]
        layout = dl.restablecer_layout(dashboard_id, changed_by, actor=request.user, request=request)
        return Response(dl.serializar_layout(layout))


class DashboardsAuthorizedView(APIView):
    """`GET /api/dashboards/authorized` — solo los dashboards que el usuario autenticado puede
    ver (nunca hardcodeado en el frontend, sección 13 de la integración con skelleton_base)."""

    def get(self, request):
        return Response(dashboard_registry.dashboards_autorizados(request))


class DashboardCreateView(APIView):
    """`POST /api/dashboards/` — crea un dashboard nuevo por área (solo el contenedor: nombre,
    área y un `dashboard_id` único generado a partir del nombre; sin procesamiento de datos
    propio, alcance acotado explícitamente por el usuario)."""

    permission_classes = [require_permission(permisos.DASHBOARD_CREAR)]

    def post(self, request):
        dashboard = dashboards_service.crear_dashboard(
            nombre=request.data.get('name'),
            area=request.data.get('area', ''),
            descripcion=request.data.get('description', ''),
            contexto=request.data.get('contexto', ''),
            creado_por=request.user,
            request=request,
        )
        return Response({
            'dashboard_id': dashboard.dashboard_id, 'name': dashboard.name, 'area': dashboard.area,
            'description': dashboard.description, 'contexto': dashboard.contexto,
        }, status=201)


class DashboardDetailView(APIView):
    """`PATCH`/`DELETE /api/dashboards/<dashboard_id>/` — edición (nombre/área) y eliminación de
    un dashboard por área."""

    def patch(self, request, dashboard_id):
        if not permisos.tiene_permiso(request, permisos.DASHBOARD_EDITAR):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para editar dashboards.'}, status=403)

        dashboard = dashboards_service.actualizar_dashboard(
            dashboard_id, nombre=request.data.get('name'), area=request.data.get('area', ''),
            contexto=request.data.get('contexto', ''), actor=request.user, request=request,
        )
        return Response({
            'dashboard_id': dashboard.dashboard_id, 'name': dashboard.name, 'area': dashboard.area,
            'contexto': dashboard.contexto,
        })

    def delete(self, request, dashboard_id):
        if not permisos.tiene_permiso(request, permisos.DASHBOARD_ELIMINAR):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para eliminar dashboards.'}, status=403)

        dashboards_service.eliminar_dashboard(
            dashboard_id, confirmacion_nombre=request.data.get('confirmation_name', ''),
            actor=request.user, request=request,
        )
        return Response(status=204)


class DashboardTabsView(APIView):
    """`GET`/`POST /api/dashboards/<dashboard_id>/pestanas` — las pestañas del dashboard indicado
    (siempre incluye al menos la raíz misma, aunque no tenga ninguna pestaña adicional) y la
    creación de una pestaña nueva. Cada pestaña es un `Dashboard` independiente (su propia
    plantilla de 13 posiciones, su propio archivo) — ver `services/dashboards.py::crear_pestana`/
    `listar_pestanas`."""

    def get(self, request, dashboard_id):
        if not permisos.tiene_acceso_dashboard(request, dashboard_id, permiso_global=permisos.DASHBOARD_VIEW):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para ver este dashboard.'}, status=403)
        # La familia completa puede incluir pestañas con su propia ACL más restrictiva que la de
        # esta — no tendría sentido que la barra de pestañas enlace a una a la que el usuario no
        # tiene acceso.
        familia = dashboards_service.listar_pestanas(dashboard_id)
        visibles = [
            p for p in familia
            if permisos.tiene_acceso_dashboard(request, p['dashboard_id'], permiso_global=permisos.DASHBOARD_VIEW)
        ]
        return Response(visibles)

    def post(self, request, dashboard_id):
        if not permisos.tiene_acceso_dashboard(request, dashboard_id, permiso_global=permisos.DASHBOARD_CREAR, requiere_edicion=True):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para crear dashboards.'}, status=403)
        dashboard = dashboards_service.crear_pestana(
            dashboard_id, nombre=request.data.get('name'), actor=request.user, request=request,
        )
        return Response({'dashboard_id': dashboard.dashboard_id, 'name': dashboard.name, 'orden': dashboard.orden}, status=201)


class DashboardAccesoView(APIView):
    """`GET`/`PUT /api/dashboards/<dashboard_id>/acceso` — control de acceso por dashboard: los 2
    grupos de roles (`roles_editores` puede ver y editar, `roles_lectores` solo puede ver) y quién
    es el dueño actual. Editar esta configuración está reservado al dueño o al superusuario
    (`permisos.puede_administrar_acceso`) — a propósito no cae a ningún permiso global del
    catálogo, ni siquiera `dashboard.editar`."""

    def get(self, request, dashboard_id):
        if not permisos.tiene_acceso_dashboard(request, dashboard_id, permiso_global=permisos.DASHBOARD_VIEW):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para ver este dashboard.'}, status=403)
        return Response(dashboards_service.obtener_acceso(dashboard_id))

    def put(self, request, dashboard_id):
        if not permisos.puede_administrar_acceso(request, dashboard_id):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'Solo el dueño o un superusuario pueden editar el acceso de este dashboard.'}, status=403)
        return Response(dashboards_service.actualizar_acceso(
            dashboard_id, roles_editores_ids=request.data.get('roles_editores') or [],
            roles_lectores_ids=request.data.get('roles_lectores') or [],
            actor=request.user, request=request,
        ))


class DashboardDuenoView(APIView):
    """`PATCH /api/dashboards/<dashboard_id>/dueno` — reasigna el dueño de un dashboard. Reservado
    al superusuario, ni siquiera el dueño actual puede reasignarse a otra persona (mismo criterio
    que conceder superusuario, ver `apps/permissions/permissions.py::IsSuperuser`)."""

    permission_classes = [IsSuperuser]

    def patch(self, request, dashboard_id):
        dashboards_service.reasignar_dueno(
            dashboard_id, nuevo_dueno_id=request.data.get('owner_id'), actor=request.user, request=request,
        )
        return Response(dashboards_service.obtener_acceso(dashboard_id))


class DashboardInterpretacionView(APIView):
    """`POST /api/dashboards/<dashboard_id>/interpretacion` — interpretación completa del
    dashboard generada por IA (Gemini) a partir de los datos ya calculados de sus componentes
    visibles. Operación de solo lectura (no muta el layout): exige primero poder ver el dashboard
    (`tiene_acceso_dashboard`, respeta ACL por-dashboard) y además el permiso global dedicado
    `dashboard.interpretar` — separado de `DASHBOARD_VIEW` a propósito, para poder otorgar/quitar
    el uso de IA sin tocar quién puede ver el dashboard (control de costo del LLM). Ver
    `services/dashboard_interpretation.py`."""

    def post(self, request, dashboard_id):
        if not permisos.tiene_acceso_dashboard(request, dashboard_id, permiso_global=permisos.DASHBOARD_VIEW):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para ver este dashboard.'}, status=403)
        if not permisos.tiene_permiso(request, permisos.DASHBOARD_INTERPRETAR):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para generar interpretaciones con IA.'}, status=403)

        texto = dashboard_interpretation.generar_interpretacion(dashboard_id)
        return Response({'interpretacion': texto})


class DashboardHallazgosIAView(APIView):
    """`POST /api/dashboards/<dashboard_id>/hallazgos-ia` — hallazgo clave por componente
    (KPI/gráfico/tabla) generado por IA en un único llamado batch a Gemini (no uno por
    componente). Mismo patrón en dos pasos que `DashboardInterpretacionView`: acceso al dashboard
    primero, y además el permiso dedicado `dashboard.hallazgos_ia` (distinto de
    `dashboard.interpretar` — esta llamada se dispara automáticamente al abrir/guardar el
    dashboard, no por una acción explícita, así que conviene poder controlarla aparte). Ver
    `services/dashboard_interpretation.py::generar_hallazgos_ia`."""

    def post(self, request, dashboard_id):
        if not permisos.tiene_acceso_dashboard(request, dashboard_id, permiso_global=permisos.DASHBOARD_VIEW):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para ver este dashboard.'}, status=403)
        if not permisos.tiene_permiso(request, permisos.DASHBOARD_HALLAZGOS_IA):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para generar hallazgos con IA.'}, status=403)

        hallazgos = dashboard_interpretation.generar_hallazgos_ia(dashboard_id)
        return Response({'hallazgos': hallazgos})


class DashboardVersionsView(APIView):
    def get(self, request, dashboard_id):
        if not permisos.tiene_acceso_dashboard(request, dashboard_id, permiso_global=permisos.DASHBOARD_VIEW):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para ver este dashboard.'}, status=403)

        entradas = AuditEvent.objects.filter(
            domain__in=[AuditEvent.Domain.DASHBOARD_LAYOUT, AuditEvent.Domain.DASHBOARD_CONFIGURATION],
            dashboard_id=dashboard_id,
        )[:50]
        return Response([
            {
                'component_id': e.component_id,
                'change_type': e.action,
                'changed_by': e.metadata.get('changed_by_label') or e.actor_username or 'Anónimo',
                'changed_at': e.created_at.isoformat(),
                'version': e.metadata.get('version'),
            }
            for e in entradas
        ])
