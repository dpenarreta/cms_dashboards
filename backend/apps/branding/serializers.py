from rest_framework import serializers

from .catalog import border_radius_css, font_css
from .models import SiteTheme


class SiteThemeSerializer(serializers.ModelSerializer):
    font_primary_css = serializers.SerializerMethodField()
    font_secondary_css = serializers.SerializerMethodField()
    border_radius_css = serializers.SerializerMethodField()

    class Meta:
        model = SiteTheme
        fields = (
            'site_name', 'short_name', 'logo_url', 'favicon_url',
            'color_primary', 'color_secondary', 'color_background', 'color_headings',
            'color_text', 'color_links', 'color_buttons', 'color_menu',
            'color_success', 'color_danger', 'color_warning', 'color_info', 'color_button_text',
            'font_primary', 'font_secondary', 'font_size_base', 'border_radius',
            'font_primary_css', 'font_secondary_css', 'border_radius_css',
        )

    def get_font_primary_css(self, obj):
        return font_css(obj.font_primary)

    def get_font_secondary_css(self, obj):
        return font_css(obj.font_secondary)

    def get_border_radius_css(self, obj):
        return border_radius_css(obj.border_radius)


class SiteThemeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteTheme
        fields = (
            'site_name', 'short_name', 'logo_url', 'favicon_url',
            'color_primary', 'color_secondary', 'color_background', 'color_headings',
            'color_text', 'color_links', 'color_buttons', 'color_menu',
            'color_success', 'color_danger', 'color_warning', 'color_info', 'color_button_text',
            'font_primary', 'font_secondary', 'font_size_base', 'border_radius',
        )
        extra_kwargs = {campo: {'required': False} for campo in fields}
