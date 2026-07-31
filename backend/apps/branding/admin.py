from django.contrib import admin

from .models import SiteTheme


@admin.register(SiteTheme)
class SiteThemeAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'color_primary', 'updated_at')

    def has_add_permission(self, request):
        return not SiteTheme.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
