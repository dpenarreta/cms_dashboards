from rest_framework.response import Response
from rest_framework.views import APIView

from .catalog import PERMISSION_CATALOG
from .permissions import require_permission


class PermissionCatalogView(APIView):
    """Catálogo de permisos agrupado por módulo. Solo lectura — la fuente de verdad es código
    (`catalog.py`), no una tabla editable en runtime."""

    permission_classes = [require_permission('permisos.ver')]

    def get(self, request):
        agrupado = {}
        for permiso in PERMISSION_CATALOG:
            agrupado.setdefault(permiso['module'], []).append({
                'codename': permiso['codename'], 'name': permiso['name'],
            })
        return Response({'modules': agrupado})
