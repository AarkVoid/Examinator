from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile, EmailVerificationToken,OrganizationGroup

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False

class CustomUserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]

    # Add 'role' to the list display on the /admin/accounts/user/ page
    list_display = BaseUserAdmin.list_display + ('role',)

    # Add 'role' to the filters on the right sidebar
    list_filter = BaseUserAdmin.list_filter + ('role',)

    # Add 'role' to the fields you can edit (e.g., create a new fieldset for it)
    fieldsets = BaseUserAdmin.fieldsets + (
        (('Custom Fields'), {'fields': ('role',)}),
    )

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

admin.site.register(User, CustomUserAdmin)
admin.site.register(Profile)

admin.site.register(EmailVerificationToken)

admin.site.register(OrganizationGroup)