from django.db.models.signals import post_save,m2m_changed
from django.dispatch import receiver
from .models import User, Profile,OrganizationGroup

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

def sync_user_permissions(profile):
    """
    Re-sync user permissions based on assigned organization groups.
    """
    user = profile.user
    user.user_permissions.clear()

    for group in profile.organization_groups.all():
        perms = group.permissions.all()
        user.user_permissions.set(perms)

    user.save()
    print(" permission : ",user.user_permissions.all())


# When user.organization_groups changes
@receiver(m2m_changed, sender=Profile.organization_groups.through)
def on_org_group_change(sender, instance, action, **kwargs):
    """
    Fires whenever organization_groups M2M relation changes.
    """
    if action in ("post_add", "post_remove", "post_clear"):
        sync_user_permissions(instance)


# When permissions inside an OrganizationGroup change
@receiver(m2m_changed, sender=OrganizationGroup.permissions.through)
def on_org_group_permissions_change(sender, instance, action, pk_set, **kwargs):
    """
    When permissions are added/removed from an OrganizationGroup,
    update all affected users.
    """
    if action in ("post_add", "post_remove", "post_clear"):
        affected_profiles = instance.members.all()  # Profile objects

        for profile in affected_profiles:
            sync_user_permissions(profile)