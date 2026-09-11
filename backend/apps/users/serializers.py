from django.contrib.auth.models import Group
from rest_framework import serializers

from apps.core.password import campo_password, validar_fortaleza

from .models import User


class UserAdminListSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    # No es un campo del modelo — lo anota `UserAdminViewSet.get_queryset` (subquery sobre
    # `apps.authentication.models.Session`) porque `last_login` nunca se completa en este
    # proyecto (login 100% JWT propio, nunca pasa por `django.contrib.auth.login()`). Se declara
    # explícito (no lo infiere `ModelSerializer`, no es un campo real de `User`) y de solo lectura.
    ultima_conexion = serializers.DateTimeField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'status',
            'is_superuser', 'must_change_password', 'last_login', 'created_at', 'roles',
            'ultima_conexion',
        )

    def get_roles(self, obj):
        return list(obj.groups.values_list('name', flat=True))


class UserAdminDetailSerializer(UserAdminListSerializer):
    permissions = serializers.SerializerMethodField()
    direct_permissions = serializers.SerializerMethodField()

    class Meta(UserAdminListSerializer.Meta):
        fields = UserAdminListSerializer.Meta.fields + ('permissions', 'direct_permissions')

    def get_permissions(self, obj):
        from apps.permissions.authorization import get_user_permission_codenames
        return sorted(get_user_permission_codenames(obj))

    def get_direct_permissions(self, obj):
        return sorted(p.codename for p in obj.user_permissions.all())


class UserAdminCreateSerializer(serializers.ModelSerializer):
    password = campo_password(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password', 'must_change_password')

    def validate(self, data):
        # El usuario todavía no existe, así que se arma una instancia sin guardar solo para que
        # `UserAttributeSimilarityValidator` pueda comparar la contraseña contra el username, el
        # nombre y el correo que vienen en el mismo formulario (es justo el caso que ese validador
        # cubre: "juan.perez" con contraseña "juanperez2026"). Los otros tres validadores ya
        # corrieron a nivel de campo.
        password = data.get('password')
        if password:
            validar_fortaleza(password, User(
                username=data.get('username', ''), email=data.get('email', ''),
                first_name=data.get('first_name', ''), last_name=data.get('last_name', ''),
            ))
        return data

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('Ya existe un usuario con ese nombre de usuario.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Ya existe un usuario con ese correo.')
        return value


class UserAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')


class RoleAssignmentSerializer(serializers.Serializer):
    role_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Group.objects.all())


class PermissionAssignmentSerializer(serializers.Serializer):
    codenames = serializers.ListField(child=serializers.CharField(), allow_empty=True)


class SuperuserAssignmentSerializer(serializers.Serializer):
    is_superuser = serializers.BooleanField()
