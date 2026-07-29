import time

from django.conf import settings
from django.core.management.base import BaseCommand

HORAS_POR_DEFECTO = 24


class Command(BaseCommand):
    help = 'Elimina archivos temporales de carga (sección 17) más antiguos que N horas (por defecto 24).'

    def add_arguments(self, parser):
        parser.add_argument('--horas', type=float, default=HORAS_POR_DEFECTO)

    def handle(self, *args, **options):
        limite = time.time() - options['horas'] * 3600
        carpeta = settings.CARTERA_TEMP_UPLOADS_DIR
        eliminados = 0
        for archivo in carpeta.glob('*'):
            if archivo.is_file() and archivo.stat().st_mtime < limite:
                archivo.unlink()
                eliminados += 1
        self.stdout.write(self.style.SUCCESS(f'{eliminados} archivo(s) temporal(es) eliminado(s).'))
