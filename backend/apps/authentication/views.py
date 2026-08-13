from django.http import Http404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.core.audit import request_meta
from apps.permissions.permissions import require_permission
from cartera.exceptions import CarteraError

from .models import EmailTemplate
from .serializers import (
    AvatarUploadSerializer, ChangeOwnPasswordSerializer, EmailTemplateSerializer, EmailTemplateUpdateSerializer,
    LoginSerializer, MeSerializer, PasswordResetConfirmSerializer, PasswordResetRequestSerializer,
    PasswordResetValidateSerializer, RefreshSerializer, UpdateMyProfileSerializer,
)
from .services import AuthenticationService, PasswordResetService


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip, user_agent = request_meta(request)
        tokens, usuario = AuthenticationService.login(
            identifier=serializer.validated_data['identifier'],
            password=serializer.validated_data['password'],
            ip_address=ip, user_agent=user_agent,
        )
        return Response(tokens, status=200)


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = AuthenticationService.refresh_tokens(refresh_token_str=serializer.validated_data['refresh'])
        return Response(tokens, status=200)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthenticationService.logout(refresh_token_str=serializer.validated_data['refresh'])
        return Response(status=204)


class LogoutAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        AuthenticationService.logout_all(user=request.user)
        return Response(status=204)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        serializer = UpdateMyProfileSerializer(data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        usuario = request.user
        anterior = {campo: getattr(usuario, campo) for campo in serializer.validated_data}
        for campo, valor in serializer.validated_data.items():
            setattr(usuario, campo, valor)
        usuario.save(update_fields=list(serializer.validated_data.keys()) or None)
        log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_PROFILE_UPDATED', actor=usuario,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
            previous_values=anterior, new_values=serializer.validated_data, request=request,
        )
        return Response(MeSerializer(usuario, context={'request': request}).data)


class MyAvatarView(APIView):
    """`POST /api/auth/me/avatar` — reemplaza el avatar del usuario autenticado (multipart). Borra
    el archivo anterior del disco tras guardar el nuevo, para no acumular huérfanos."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = request.user
        avatar_anterior = usuario.avatar if usuario.avatar else None
        usuario.avatar = serializer.validated_data['avatar']
        usuario.save(update_fields=['avatar'])
        if avatar_anterior:
            avatar_anterior.delete(save=False)
        log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_AVATAR_UPDATED', actor=usuario,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username, request=request,
        )
        return Response(MeSerializer(usuario, context={'request': request}).data)


class ChangeOwnPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangeOwnPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = request.user

        if not usuario.check_password(serializer.validated_data['old_password']):
            raise CarteraError('La contraseña actual no es correcta.', codigo='CONTRASENA_ACTUAL_INCORRECTA')

        usuario.set_password(serializer.validated_data['new_password'])
        usuario.must_change_password = False
        usuario.save(update_fields=['password', 'must_change_password'])
        log_event(
            domain=AuditEvent.Domain.AUTHENTICATION, action='PASSWORD_CHANGED_SELF',
            actor=usuario, entity_type='user', entity_id=usuario.id, request=request,
        )
        return Response(status=204)


class PasswordResetRequestView(APIView):
    """`POST /api/auth/password-reset/request` — respuesta siempre genérica (nunca revela si el
    correo existe). Limitado por `ScopedRateThrottle` (sección 7.6, prevención de abuso)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip, user_agent = request_meta(request)
        mensaje = PasswordResetService.solicitar(
            email=serializer.validated_data['email'], request=request, ip_address=ip, user_agent=user_agent,
        )
        return Response({'message': mensaje}, status=200)


class PasswordResetValidateView(APIView):
    """`POST /api/auth/password-reset/validate` — permite a la pantalla de restablecimiento
    verificar el token antes de mostrar el formulario, sin consumirlo."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip, user_agent = request_meta(request)
        PasswordResetService.validar(
            raw_token=serializer.validated_data['token'], request=request, ip_address=ip, user_agent=user_agent,
        )
        return Response({'valid': True}, status=200)


class EmailTemplateAdminView(APIView):
    """`GET`/`PATCH /api/auth/admin/email-templates/<key>` — asunto + HTML de una plantilla de
    correo transaccional (hoy solo `password_reset`, ver `EmailTemplate`). El `GET` siembra la
    fila por defecto si todavía no existe (`get_or_seed`, mismo patrón que
    `SiteTheme.get_solo()`)."""

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [require_permission('configuracion.editar')()]
        return [require_permission('configuracion.ver')()]

    def _obtener_o_404(self, key):
        if key not in dict(EmailTemplate.KEY_CHOICES):
            raise Http404
        return EmailTemplate.get_or_seed(key)

    def get(self, request, key):
        plantilla = self._obtener_o_404(key)
        return Response(EmailTemplateSerializer(plantilla).data)

    def patch(self, request, key):
        plantilla = self._obtener_o_404(key)
        anterior = {'subject': plantilla.subject, 'html_body': plantilla.html_body}
        serializer = EmailTemplateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for campo, valor in serializer.validated_data.items():
            setattr(plantilla, campo, valor)
        plantilla.updated_by = request.user
        plantilla.save(update_fields=list(serializer.validated_data.keys()) + ['updated_by', 'updated_at'])
        log_event(
            domain=AuditEvent.Domain.SYSTEM_CONFIGURATION, action='EMAIL_TEMPLATE_UPDATED', actor=request.user,
            entity_type='email_template', entity_id=plantilla.pk, entity_name=plantilla.key, request=request,
            previous_values=anterior, new_values=serializer.validated_data,
        )
        return Response(EmailTemplateSerializer(plantilla).data)


class EmailTemplateResetView(APIView):
    """`POST /api/auth/admin/email-templates/<key>/reset` — vuelve la plantilla al HTML/asunto
    por defecto (`EmailTemplate.restablecer`)."""

    permission_classes = [require_permission('configuracion.editar')]

    def post(self, request, key):
        if key not in dict(EmailTemplate.KEY_CHOICES):
            raise Http404
        plantilla = EmailTemplate.get_or_seed(key)
        plantilla.restablecer()
        log_event(
            domain=AuditEvent.Domain.SYSTEM_CONFIGURATION, action='EMAIL_TEMPLATE_RESET', actor=request.user,
            entity_type='email_template', entity_id=plantilla.pk, entity_name=plantilla.key, request=request,
        )
        return Response(EmailTemplateSerializer(plantilla).data)


class PasswordResetConfirmView(APIView):
    """`POST /api/auth/password-reset/confirm` — cambia la contraseña, invalida el token y revoca
    las sesiones existentes del usuario."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip, user_agent = request_meta(request)
        PasswordResetService.confirmar(
            raw_token=serializer.validated_data['token'], new_password=serializer.validated_data['new_password'],
            request=request, ip_address=ip, user_agent=user_agent,
        )
        return Response({'message': 'Tu contraseña fue actualizada correctamente.'}, status=200)
