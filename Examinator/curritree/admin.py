# hierarchy/admin.py
from django.contrib import admin
from .models import TreeNode

@admin.register(TreeNode)
class NodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'node_type', 'parent', 'order', 'created')
    list_filter = ('node_type',)
    search_fields = ('name',)
    ordering = ('parent__id', 'order', 'name')
    raw_id_fields = ('parent',)
    readonly_fields = ('created', 'modified')
    fieldsets = (
        (None, {
            'fields': ('name', 'node_type', 'parent', 'order')
        }),
        ('Timestamps', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',),
        }),
    )