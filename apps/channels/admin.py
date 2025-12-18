from django.contrib import admin
from .models import Channel


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ['title', 'username', 'channel_type', 'order', 'is_active']
    list_filter = ['channel_type', 'is_active']
    search_fields = ['title', 'username']
    ordering = ['order', 'title']

    fieldsets = (
        ('Asosiy', {
            'fields': ('title', 'username', 'channel_id', 'invite_link')
        }),
        ('Sozlamalar', {
            'fields': ('channel_type', 'order', 'is_active')
        }),
    )
