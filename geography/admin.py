from django.contrib import admin
from .models import CustomUser, GoverningBody
from django.utils.safestring import mark_safe

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'membership_id', 'is_active', 'profile_pic_thumbnail')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email')
    readonly_fields = ('profile_pic_preview',)

    def profile_pic_preview(self, obj):
        if obj.profile_picture:
            return mark_safe(f'<img src="{obj.profile_picture.url}" style="max-height: 50px;">')
        return "No profile picture"
    profile_pic_preview.short_description = "Profile Picture"

    def profile_pic_thumbnail(self, obj):
        if obj.profile_picture:
            return mark_safe(f'<img src="{obj.profile_picture.url}" style="max-height: 50px; max-width: 50px; border-radius: 50%;"/>')
        return "No Image"
    profile_pic_thumbnail.short_description = "Profile Picture"



@admin.register(GoverningBody)
class GoverningBodyAdmin(admin.ModelAdmin):
    list_display = ('name', 'acronym', 'headquarters')
    list_filter = ('headquarters',)
    search_fields = ('name', 'acronym')
    readonly_fields = ('logo_display',)

    def logo_display(self, obj):
        if obj.logo:
            return mark_safe(f'<img src="{obj.logo.url}" style="max-height: 50px;">')
        return "No logo uploaded"  # Single return per condition

    logo_display.short_description = "Current Logo"