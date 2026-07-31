from rest_framework import serializers

from apps.permissions.authorization import user_has_permission

from .models import AuditEvent


class AuditEventListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = (
            'id', 'created_at', 'domain', 'action', 'result', 'severity',
            'actor_username', 'entity_type', 'entity_id', 'entity_name',
            'dashboard_id', 'component_id', 'ip_address', 'message',
        )


class AuditEventDetailSerializer(AuditEventListSerializer):
    class Meta(AuditEventListSerializer.Meta):
        fields = AuditEventListSerializer.Meta.fields + (
            'previous_values', 'new_values', 'metadata', 'user_agent', 'request_id', 'session_id',
        )

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        usuario = self.context.get('request').user if self.context.get('request') else None
        if not user_has_permission(usuario, 'auditoria.ver_detalle'):
            for campo in ('previous_values', 'new_values', 'metadata'):
                datos.pop(campo, None)
        return datos
