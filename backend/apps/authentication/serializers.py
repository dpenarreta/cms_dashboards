from rest_framework import serializers


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


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(trim_whitespace=False, min_length=8)
    confirm_password = serializers.CharField(trim_whitespace=False)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Las contraseñas no coinciden.'})
        return data
