from django.contrib.auth.models import Group
from rest_framework import serializers

from .models import User


class UserAdminListSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'status',
            'is_superuser', 'must_change_password', 'last_login', 'created_at', 'roles',
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
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password', 'must_change_password')

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
