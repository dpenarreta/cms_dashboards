from django.core.management.base import BaseCommand

from cartera.services import fuente_bd_scheduler


class Command(BaseCommand):
    help = (
        'Actualización automática de "Conectar vista de base de datos": reconecta y reaplica el '
        'último mapeo confirmado para cada dashboard con una actualización PENDIENTE según su '
        'frecuencia (semanal/mensual). Sin programador de tareas propio de la app — se espera que '
        'un programador externo al sistema operativo (Windows Task Scheduler / cron) invoque este '
        'comando una vez al día. Si un día previsto no corrió, la siguiente ejecución lo recupera: '
        'no hay que esperar al próximo período ni lanzar nada a mano.'
    )

    def handle(self, *args, **options):
        resultados = fuente_bd_scheduler.actualizar_todos()
        if not resultados:
            self.stdout.write('Ningún dashboard tenía una actualización automática pendiente.')
            return

        for resultado in resultados:
            linea = f'{resultado["dashboard_id"]}: {resultado["mensaje"]}'
            if resultado['ok']:
                self.stdout.write(self.style.SUCCESS(linea))
            else:
                self.stdout.write(self.style.WARNING(linea))
