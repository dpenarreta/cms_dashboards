from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor', 'action', 'module', 'result')
    list_filter = ('module', 'result')
    search_fields = ('action', 'target_type', 'target_id')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
