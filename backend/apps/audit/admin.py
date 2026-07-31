from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'domain', 'action', 'result', 'severity', 'actor_username')
    list_filter = ('domain', 'result', 'severity')
    search_fields = ('action', 'entity_type', 'entity_id', 'actor_username', 'message')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
