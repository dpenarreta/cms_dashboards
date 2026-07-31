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
    if not permisos.tiene_permiso(request, permisos.DASHBOARD_VIEW):
        return []
    return [
        {'dashboard_id': d.dashboard_id, 'name': d.name, 'area': d.area}
        for d in Dashboard.objects.all()
    ]
