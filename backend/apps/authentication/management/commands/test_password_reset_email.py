"""Comando QA (Módulo D, sección 9.2 del prompt): envía UNA recuperación de contraseña real a un
usuario existente, para validar manualmente que el flujo de correo funciona de punta a punta.

Reutiliza `PasswordResetService.solicitar(...)` — el mismo código que usa el endpoint público
`POST /api/auth/password-reset/request` — para que la prueba valide exactamente el camino de
producción (mismo servicio, misma plantilla, mismo registro de auditoría). El correo de prueba
nunca está hardcodeado en esa lógica: llega aquí únicamente como argumento `--email`.

No debe ejecutarse dentro de la suite automatizada — es una acción manual, deliberada, que solo
tiene sentido con `EMAIL_BACKEND` apuntando a un servidor real."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.authentication.services import PasswordResetService

User = get_user_model()


class Command(BaseCommand):
    help = 'Envía una recuperación de contraseña real a un usuario, como prueba QA manual.'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='Correo del usuario destinatario.')
        parser.add_argument(
            '--yes', action='store_true',
            help='Omite la confirmación interactiva (uso en automatización controlada, no en CI).',
        )

    def handle(self, *args, **options):
        email = options['email'].strip()
        confirmado = options['yes']

        usuario = User.objects.filter(email__iexact=email).first()
        if usuario is None:
            raise CommandError(f'No existe ningún usuario con el correo "{email}".')
        if not usuario.is_active:
            raise CommandError(f'El usuario "{usuario.username}" no está activo.')

        backend = settings.EMAIL_BACKEND
        es_backend_real = 'console' not in backend and 'locmem' not in backend
        self.stdout.write(f'Backend de correo configurado: {backend}')
        if not es_backend_real:
            self.stdout.write(self.style.WARNING(
                'Este backend no envía correo real (consola/memoria). Configura EMAIL_HOST y '
                'EMAIL_HOST_USER/EMAIL_HOST_PASSWORD en .env para una prueba real.',
            ))

        self.stdout.write(f'Destinatario: {usuario.email}  (usuario: {usuario.username})')
        self.stdout.write(f'FRONTEND_URL: {settings.FRONTEND_URL}')
        self.stdout.write(f'Expiración del token: {settings.PASSWORD_RESET_TOKEN_LIFETIME_MINUTES} minutos')

        if not confirmado:
            respuesta = input('¿Enviar el correo de recuperación ahora? Escribe "si" para continuar: ')
            if respuesta.strip().lower() not in ('si', 'sí', 'yes', 'y'):
                self.stdout.write(self.style.WARNING('Cancelado por el usuario. No se envió ningún correo.'))
                return

        momento_envio = timezone.now()
        PasswordResetService.solicitar(email=usuario.email)

        # `solicitar(...)` nunca lanza (falla silenciosa hacia el usuario final de la API, por
        # diseño anti-enumeración) — para saber si el envío realmente funcionó en esta prueba
        # manual, se consulta el evento de auditoría que la propia llamada acaba de registrar.
        evento = AuditEvent.objects.filter(
            domain=AuditEvent.Domain.AUTHENTICATION,
            action__in=['PASSWORD_RESET_EMAIL_SENT', 'PASSWORD_RESET_EMAIL_FAILED'],
            actor_id=usuario.id, created_at__gte=momento_envio,
        ).order_by('-created_at').first()

        if evento is None:
            raise CommandError('No se encontró el evento de auditoría del envío — revisa los logs del servidor.')

        if evento.action == 'PASSWORD_RESET_EMAIL_SENT':
            self.stdout.write(self.style.SUCCESS(f'Correo enviado correctamente. Evento de auditoría: {evento.id}'))
            return

        raise CommandError(f'El envío falló (revisa los logs). Evento de auditoría: {evento.id}')
