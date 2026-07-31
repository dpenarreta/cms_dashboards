from django.contrib.auth.models import Group, Permission
from rest_framework import serializers

from apps.permissions.catalog import PERMISSION_CATALOG

_CODENAMES_VALIDOS = {p['codename'] for p in PERMISSION_CATALOG}


class RoleSerializer(serializers.ModelSerializer):
    permission_codenames = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ('id', 'name', 'permission_codenames')

    def get_permission_codenames(self, obj):
        return sorted(
            obj.permissions.filter(content_type__app_label='permissions').values_list('codename', flat=True)
        )


class RoleWriteSerializer(serializers.ModelSerializer):
    permission_codenames = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    class Meta:
        model = Group
        fields = ('name', 'permission_codenames')

    def validate_name(self, value):
        queryset = Group.objects.filter(name__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Ya existe un rol con ese nombre.')
        return value

    def validate_permission_codenames(self, value):
        invalidos = set(value) - _CODENAMES_VALIDOS
        if invalidos:
            raise serializers.ValidationError(f'Permisos no reconocidos: {", ".join(sorted(invalidos))}.')
        return value

    def create(self, validated_data):
        codenames = validated_data.pop('permission_codenames', [])
        grupo = Group.objects.create(name=validated_data['name'])
        self._asignar_permisos(grupo, codenames)
        return grupo

    def update(self, instance, validated_data):
        if 'name' in validated_data:
            instance.name = validated_data['name']
            instance.save(update_fields=['name'])
        if 'permission_codenames' in validated_data:
            self._asignar_permisos(instance, validated_data['permission_codenames'])
        return instance

    @staticmethod
    def _asignar_permisos(grupo, codenames):
        permisos = Permission.objects.filter(codename__in=codenames, content_type__app_label='permissions')
        grupo.permissions.set(permisos)
