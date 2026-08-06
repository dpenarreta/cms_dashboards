"""Catálogo de dashboards disponibles (sección 13 de la integración con skelleton_base).

Antes era una lista fija en código con un único dashboard ("cartera"). Ahora los dashboards viven
en el modelo `Dashboard` (tabla editable en runtime: un administrador con `dashboard.crear` puede
agregar dashboards nuevos por área — ver `services/dashboards.py`), pero el criterio de
autorización no cambia: todos los dashboards, el de cartera y los nuevos por igual, se protegen
con el mismo permiso `dashboard.view` (no existe todavía un permiso por-dashboard-individual; ver
alcance acotado explícitamente por el usuario). La API nunca devuelve un dashboard que el usuario
autenticado no tenga permiso de ver, para que el frontend no tenga que hardcodear esa lista.
"""

from . import permisos
from .models import Dashboard


def dashboards_autorizados(request):
    # Las pestañas de un dashboard (`Dashboard.parent`) no son dashboards sueltos — se navega a
    # ellas desde la barra de pestañas del dashboard raíz, no deben aparecer acá como una entrada
    # aparte. Cada dashboard se filtra individualmente por `tiene_acceso_dashboard` (control de
    # acceso por roles editores/lectores + dueño) en vez de un único chequeo global: un dashboard
    # sin ACL propia se ve igual que siempre (basta `dashboard.view`), uno con ACL configurada solo
    # lo ven su dueño/el superusuario/quien tenga uno de los roles asignados — aunque no tenga el
    # permiso global. `puede_administrar_acceso` le indica al frontend si mostrar el botón para
    # configurar esa ACL.
    return [
        {
            'dashboard_id': d.dashboard_id, 'name': d.name, 'area': d.area,
            'puede_administrar_acceso': permisos.puede_administrar_acceso(request, d.dashboard_id),
        }
        for d in Dashboard.objects.filter(parent__isnull=True)
        if permisos.tiene_acceso_dashboard(request, d.dashboard_id, permiso_global=permisos.DASHBOARD_VIEW)
    ]
