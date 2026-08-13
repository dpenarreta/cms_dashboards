from django.contrib.auth import get_user_model
from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    is_superuser = serializers.BooleanField()
    must_change_password = serializers.BooleanField()
    area = serializers.CharField()
    avatar_url = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url

    def get_roles(self, obj):
        return list(obj.groups.values_list('name', flat=True))

    def get_permissions(self, obj):
        from apps.permissions.authorization import get_user_permission_codenames
        return sorted(get_user_permission_codenames(obj))


class UpdateMyProfileSerializer(serializers.Serializer):
    area = serializers.CharField(max_length=100, allow_blank=True, required=False)
    # `max_length=150` calza con el default de Django en `first_name`/`last_name`
    # (`AbstractUser`, sin sobreescribir — ver `apps/users/migrations/0001_initial.py`).
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    # Mismo validador que ya trae el campo en el modelo (`AbstractUser.username`, sin
    # sobreescribir en `apps.users.models.User`): letras/dígitos/`@`/`.`/`+`/`-`/`_` solamente.
    # No `allow_blank` — a diferencia de área/nombre/apellido, un username vacío nunca es válido.
    username = serializers.CharField(max_length=150, validators=[UnicodeUsernameValidator()], required=False)

    def validate_username(self, value):
        # Este serializer no está atado a una instancia (`UpdateMyProfileSerializer(data=...)`,
        # sin `instance=`) — la vista pasa `context={'request': request}` para poder excluir al
        # propio usuario de la comprobación de unicidad. Mismo criterio case-insensitive y mismo
        # mensaje que `UserAdminCreateSerializer.validate_username` (`apps/users/serializers.py`).
        usuario_actual = self.context['request'].user
        if User.objects.filter(username__iexact=value).exclude(pk=usuario_actual.pk).exists():
            raise serializers.ValidationError('Ya existe un usuario con ese nombre de usuario.')
        return value


# 2 MB — un avatar no necesita el límite de 25 MB pensado para el Excel de cartera
# (`settings.UPLOAD_MAX_SIZE_BYTES`).
AVATAR_MAX_SIZE_BYTES = 2 * 1024 * 1024


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField()

    def validate_avatar(self, value):
        if value.size > AVATAR_MAX_SIZE_BYTES:
            raise serializers.ValidationError('La imagen no puede superar 2 MB.')
        return value


class ChangeOwnPasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False, min_length=8)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetValidateSerializer(serializers.Serializer):
    token = serializers.CharField()


class EmailTemplateSerializer(serializers.Serializer):
    key = serializers.CharField()
    subject = serializers.CharField()
    html_body = serializers.CharField()
    updated_at = serializers.DateTimeField()
    variables = serializers.SerializerMethodField()

    def get_variables(self, obj):
        from .email_template_defaults import TEMPLATE_VARIABLES
        return TEMPLATE_VARIABLES.get(obj.key, [])


class EmailTemplateUpdateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    # Sin tope estricto de la plantilla de correo original (era ~1 KB) — pero sí un límite
    # generoso para no aceptar payloads absurdos desde el editor de texto enriquecido.
    html_body = serializers.CharField(max_length=100_000)


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(trim_whitespace=False, min_length=8)
    confirm_password = serializers.CharField(trim_whitespace=False)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Las contraseñas no coinciden.'})
        return data
