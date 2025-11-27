from django.contrib.auth.backends import ModelBackend

class OrganizationBackend(ModelBackend):

    def get_group_permissions(self, user_obj, obj=None):
        if not user_obj.is_authenticated:
            return set()

        perms = set()

        # If user has org groups
        org_groups = getattr(user_obj, "organization_groups", None)
        if org_groups:
            for group in org_groups.all():
                for perm in group.permissions.all():
                    perms.add(f"{perm.content_type.app_label}.{perm.codename}")

        return perms

    def get_all_permissions(self, user_obj, obj=None):
        perms = super().get_all_permissions(user_obj, obj)
        perms |= self.get_group_permissions(user_obj, obj)
        return perms

    def has_perm(self, user_obj, perm, obj=None):
        return perm in self.get_all_permissions(user_obj, obj)
