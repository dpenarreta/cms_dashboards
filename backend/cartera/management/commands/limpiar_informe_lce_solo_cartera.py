"""Script de un solo uso, de seguimiento a `poblar_informe_lce_junio2026`: el usuario pidió dejar
SOLO la sección de Cartera (sección 6 del informe original) en el dashboard "Administracion", sin
las otras 4 pestañas que se habían creado. Borra las pestañas "Rentabilidad", "Balance General",
"Caja, Deuda y Situación de Caja" y "Capital de Trabajo y Cartera", y reemplaza el contenido de la
raíz ("Administracion") por `poblar_cartera` (solo Cartera, sin Capital de Trabajo)."""

from django.core.management.base import BaseCommand

from cartera.services import dashboards as dashboards_service
from .poblar_informe_lce_junio2026 import DASHBOARD_RAIZ, ConstructorDashboard, poblar_cartera

PESTANAS_A_BORRAR = ['Rentabilidad', 'Balance General', 'Caja, Deuda y Situación de Caja', 'Capital de Trabajo y Cartera']


class Command(BaseCommand):
    help = 'Deja "Administracion" solo con el contenido de Cartera (sección 6), borra las otras 4 pestañas creadas por poblar_informe_lce_junio2026.'

    def handle(self, *args, **options):
        raiz = dashboards_service._obtener_dashboard_o_error(DASHBOARD_RAIZ)
        for nombre in PESTANAS_A_BORRAR:
            pestana = raiz.pestanas.filter(name=nombre).first()
            if not pestana:
                self.stdout.write(f'Pestaña "{nombre}" no existe, se omite.')
                continue
            dashboards_service.eliminar_dashboard(pestana.dashboard_id, confirmacion_nombre=nombre)
            self.stdout.write(self.style.SUCCESS(f'Pestaña "{nombre}" eliminada.'))

        poblar_cartera(ConstructorDashboard(DASHBOARD_RAIZ))
        self.stdout.write(self.style.SUCCESS(f'"{DASHBOARD_RAIZ}" reemplazado: ahora solo tiene el contenido de Cartera.'))
