from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'action', 'host', 'user',
        'ip_address', 'timestamp',
    ]
    list_filter = ['action', 'timestamp']
    search_fields = [
        'action', 'user__username',
        'host__name', 'ip_address',
    ]
    readonly_fields = [
        'action', 'host', 'user',
        'ip_address', 'details',
        'timestamp',
    ]

    fieldsets = (
        ('操作信息', {
            'fields': ('action', 'user', 'ip_address')
        }),
        ('关联信息', {
            'fields': ('host',)
        }),
        ('详细信息', {
            'fields': ('details',),
            'classes': ('collapse',),
        }),
        ('时间信息', {
            'fields': ('timestamp',),
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
