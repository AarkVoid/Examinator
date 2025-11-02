from django.contrib import admin

from .models import OrganizationProfile, LicenseGrant, UsageLimit, LicensePermission

@admin.register(OrganizationProfile)
class OrganizationProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'billing_email', 'created_at', 'is_active')
    search_fields = ('name', 'billing_email')
    ordering = ('name',)
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('name', 'billing_email', 'address', 'phone_number', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

@admin.register(LicenseGrant)
class LicenseGrantAdmin(admin.ModelAdmin):
    list_display = (
        'organization_name',
        'get_curriculum_nodes',
        'purchased_on',
        'valid_until',
        'is_active',
    )
    list_filter = (
        'purchased_on',
        'valid_until',
    )
    search_fields = (
        'organization_profile__name',
        'curriculum_node__name',
    )
    filter_horizontal = ('curriculum_node',)  # better UI for ManyToManyField

    fieldsets = (
        ("Organization Info", {
            'fields': ('organization_profile',)
        }),
        ("Curriculum Access", {
            'fields': ('curriculum_node',)
        }),
        ("License Validity", {
            'fields': ('purchased_on', 'max_question_papers','valid_until'),
            'description': "Set expiry date if the license should auto-expire."
        }),
    )

    readonly_fields = ('purchased_on',)

    def organization_name(self, obj):
        return obj.organization_profile.name
    organization_name.short_description = "Organization"

    def get_curriculum_nodes(self, obj):
        """Show comma-separated list of licensed nodes."""
        nodes = obj.curriculum_node.all().values_list('name', flat=True)
        return ", ".join(nodes) if nodes else "—"
    get_curriculum_nodes.short_description = "Licensed Nodes"

    def is_active(self, obj):
        """Show whether license is currently active."""
        from datetime import date
        if obj.valid_until:
            return obj.valid_until >= date.today()
        return True
    is_active.boolean = True
    is_active.short_description = "Active?"



    
@admin.register(UsageLimit)
class UsageLimitAdmin(admin.ModelAdmin):
    list_display = ('organization_profile', 'max_users','max_question_papers_drafts')
    search_fields = ('organization_profile__name',)
    ordering = ('organization_profile__name',)
    raw_id_fields = ('organization_profile',)
    fieldsets = (
        (None, {
            'fields': ('organization_profile', 'max_users', 'max_question_papers_drafts')
        }),
    )       
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('organization_profile')    
    verbose_name_plural = "Subscription Usage Limits"


@admin.register(LicensePermission)
class LicensePermissionAdmin(admin.ModelAdmin):
    list_display = ('license', 'permission')
    search_fields = ('license__organization_profile__name', 'permission__codename')
    list_filter = ('permission__content_type',)
    raw_id_fields = ('license', 'permission')
    ordering = ('license__organization_profile__name', 'permission__codename')
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('license__organization_profile', 'permission')
    