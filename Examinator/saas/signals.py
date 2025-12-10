# from django.db.models.signals import m2m_changed, post_save, post_delete
# from django.dispatch import receiver
# from .models import LicenseGrant,LicensePermission
# from django.contrib.auth.models import Permission
# from accounts.models import Profile
# from datetime import date
# from django.db.models import Q
# from accounts.models import User
# from django.db import transaction 
# from curritree.models import TreeNode

# @receiver(m2m_changed, sender=LicenseGrant.curriculum_node.through)
# def update_org_and_user_streams(sender, instance, action, pk_set, **kwargs):
#     """
#     Sync organization supported boards and user profile streams and permissions
#     whenever curriculum nodes are added/removed from a LicenseGrant.
    
#     CRITICAL: This uses a full recalculation based *only* on non-expired licenses 
#     to prevent expired content from being re-granted.
#     """
#     # Only proceed for actions that change the linked nodes
#     if action not in ["post_add", "post_remove", "post_clear","post_delete"]:
#         return

#     # Check if the license grant has an organization attached
#     try:
#         org = instance.organization_profile
#     except AttributeError:
#         # If the instance is somehow detached or corrupt, exit cleanly
#         return
        
#     if not org:
#         return

#     with transaction.atomic():
#         today = date.today()
        
#         # 1. FIND ALL ACTIVE LICENSES FOR THIS ORGANIZATION
#         # This is the CRITICAL security check: only use licenses that haven't expired.
#         active_licenses_qs = org.license_grants.filter(
#             Q(valid_until__isnull=True) | Q(valid_until__gte=today)
#         )
        
#         # --- 2. GLOBAL RECALCULATION OF ALL ACTIVE LICENSED NODES ---
#         all_licensed_nodes_qs = TreeNode.objects.filter(
#             # Filter nodes only based on the active licenses
#             licensegrant__in=active_licenses_qs
#         ).distinct()

#         final_stream_pks = set()
#         for node in all_licensed_nodes_qs:
#             final_stream_pks.add(node.pk)

#             # Efficiently retrieve and add all ancestors and descendants to the stream
#             ancestors = node.get_ancestors(include_self=False)
#             final_stream_pks.update([n.pk for n in ancestors])

#             descendants = node.get_descendants(include_self=False)
#             final_stream_pks.update([d.pk for d in descendants])

#         all_active_nodes_pk = list(final_stream_pks)
        
        
#         # --- 3. DETERMINE TARGET USERS (Applying Selective/Global Policy) ---
#         profile_filter = {'organization_profile': org}
        
#         if action == "post_add":
#             # Policy: If adding a license, ONLY update admin profiles.
#             profile_filter['user__role'] = 'admin'
        
#         elif action in ["post_remove", "post_clear"]:
#             # Policy: If removing/clearing nodes, update ALL users to enforce revocation.
#             pass # profile_filter remains global

#         user_profiles = Profile.objects.filter(**profile_filter).select_related('user')
        
#         # Apply the calculated stream to the target users
#         for profile in user_profiles:
#             profile.academic_stream.set(all_active_nodes_pk)
            
            
#         # --- 4. SYNC MANAGEMENT PERMISSIONS (Added for completeness) ---

#         # Calculate the aggregate permission set from all active licenses
#         all_perms = Permission.objects.filter(
#             licensepermission__license__in=active_licenses_qs
#         ).distinct()
        
#         # We target the actual User model instances
#         users_to_update_perms = User.objects.filter(profile__in=user_profiles)
#         UserPermissionM2M = User._meta.get_field('user_permissions').remote_field.through

#         for user in users_to_update_perms:
#             # Always clear old permissions for security/revocation
#             UserPermissionM2M.objects.filter(user=user).delete() 

#             # Only re-add permissions if the user is an admin AND we have active permissions
#             if all_perms and user.role == 'admin':
#                 new_user_perms = [
#                     UserPermissionM2M(user=user, permission=perm)
#                     for perm in all_perms
#                 ]
#                 UserPermissionM2M.objects.bulk_create(new_user_perms, ignore_conflicts=True)
                
#         # --- 5. Sync Organization Supported Boards ---
#         root_board_pks = TreeNode.objects.filter(
#             pk__in=all_active_nodes_pk,
#             node_type__in=["board", "competitive"],
#             parent__isnull=True
#         ).values_list('pk', flat=True)
        
#         org.supported_curriculum.set(root_board_pks)
#         org.save()

# @receiver([post_save, post_delete], sender=LicenseGrant)
# @receiver([post_save, post_delete], sender=LicensePermission)
# def sync_org_permissions(sender, instance, **kwargs):
#     """
#     Sync organization permissions based on active licenses and permissions.

#     This function now implements conditional user targeting:
#     - Post Save (Implied Addition/Change): Only updates 'admin' users.
#     - Post Delete (Implied Revocation): Updates ALL users.
#     """
#     is_deletion = kwargs.get('signal') == post_delete
    
#     # 1. Determine the OrganizationProfile
#     if sender == LicenseGrant:
#         org = instance.organization_profile
#     elif sender == LicensePermission:
#         # For post_delete of LicensePermission, the foreign key might be unavailable.
#         try:
#             org = instance.license.organization_profile
#         except AttributeError:
#             # This happens if the license was deleted first, or during cascade.
#             return
#     else:
#         return

#     if not org:
#         return

#     today = date.today()

#     # 2. Get active (non-expired) licenses for the organization
#     active_licenses = org.license_grants.filter(
#         Q(valid_until__isnull=True) | Q(valid_until__gte=today)
#     )

#     # 3. Get all UNIQUE Permission objects linked to the active licenses
#     all_perms = Permission.objects.filter(
#         licensepermission__license__in=active_licenses
#     ).distinct()


#     # 4. Fetch target organization users based on action
#     user_filter = {'profile__organization_profile': org}
    
#     # CRITICAL: Apply conditional filtering
#     if is_deletion:
#         # Revocation: Update ALL users in the organization
#         pass 
#     else:
#         # Addition/Change: Only update 'admin' users
#         user_filter['role'] = 'admin'

#     users_to_update = User.objects.filter(**user_filter)
    
#     # CRITICAL FIX: Get the correct intermediary model for the User-Permission relationship
#     UserPermissionM2M = User._meta.get_field('user_permissions').remote_field.through

#     print(f"Syncing permissions for {users_to_update.count()} users in org '{org.name}' with {all_perms.count()} permissions. Deletion={is_deletion}")
    
#     # 5. Assign permissions manually using a transaction for safety and efficiency
#     with transaction.atomic():
#         for user in users_to_update:
#             # Clear all existing direct permissions for the targeted user set
#             # This is safe because we clear ALL, and then set the currently calculated ALL.
#             UserPermissionM2M.objects.filter(user=user).delete() 

#             # Prepare and Create new UserPermission M2M instances
#             if all_perms:
#                 new_user_perms = [
#                     UserPermissionM2M(user=user, permission=perm)
#                     for perm in all_perms
#                 ]
                
#                 # Bulk create the new links
#                 UserPermissionM2M.objects.bulk_create(new_user_perms, ignore_conflicts=True)

#     print("Permission sync complete.")

from django.db.models.signals import m2m_changed, post_save, post_delete
from django.dispatch import receiver
from django.db.models import Q
from django.db import transaction 

# Import all necessary models
from .models import LicenseGrant, LicensePermission
from django.contrib.auth.models import Permission
from accounts.models import Profile, User, OrganizationGroup
from curritree.models import TreeNode
from datetime import date
import logging

logger = logging.getLogger(__name__)

# Helper function to find the UserPermission M2M table
UserPermissionM2M = User._meta.get_field('user_permissions').remote_field.through

def _sync_organization_permissions(org, is_deletion=False):
    """
    Recalculates and syncs management permissions for an organization's users. 
    It enforces permission revocation on OrganizationGroups only when explicitly 
    requested via the `sync_groups=True` flag (which is reserved for LicenseGrant deletion).

    :param org: The OrganizationProfile instance.
    :param is_deletion: True if this sync is triggered by a revocation (Post Delete). Used for user targeting.
    :param sync_groups: True if group revocation logic should run (only for LicenseGrant deletion).
    """
    today = date.today()
    
    # 1. Find active licenses
    active_licenses_qs = org.license_grants.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today)
    )

    # 2. Get all UNIQUE Permission objects linked to the active licenses
    all_perms = Permission.objects.filter(
        licensepermission__license__in=active_licenses_qs
    ).distinct()

    # print(f"S Active Licensed Permissions: {all_perms.count()} perms.")

    # --- USER SYNC POLICY ---
    # 3. Determine target users based on policy: 
    #    Deletion/Revocation targets all users; otherwise (on save), only 'admin' users.
    user_filter = {'profile__organization_profile': org}
    if not is_deletion:
        user_filter['role'] = 'admin'

    users_to_update = User.objects.filter(**user_filter)
    
    with transaction.atomic():
        # --- A. Sync Direct User Permissions ---
        # This runs on every save/delete, ensuring admin user permissions are always correct.
        for user in users_to_update:
            # Clear all existing direct permissions for the targeted user
            UserPermissionM2M.objects.filter(user=user).delete() 

            # Prepare and Create new UserPermission M2M instances if permissions exist
            if all_perms and user.role == 'admin': # Only admins get management perms
                new_user_perms = [
                    UserPermissionM2M(user=user, permission=perm)
                    for perm in all_perms
                ]
                UserPermissionM2M.objects.bulk_create(new_user_perms, ignore_conflicts=True)
        
        # --- B. Sync Organization Group Permissions (REVOCATION ONLY) ---
        # This section ensures permissions are removed (revoked) from groups.
        if all_perms:
            # Fetch all custom groups belonging to this organization
            org_groups = org.custom_groups.all() 
            
            print(f"Syncing permissions for {org_groups.count()} organization groups in org '{org.name}'.")
            for group in org_groups:
                # Store the current permissions before clearing
                current_group_perms = set(group.permissions.all())
                # print(f"Current perms for group '{group.name}': {current_group_perms}, all_perms: {all_perms}")
                
                # Permissions that are currently licensed
                licensed_perms = set(all_perms)
                
                # Find permissions that are currently in the group but are NO LONGER LICENSED (must be revoked)
                revoked_perms = current_group_perms.difference(licensed_perms)
                
                # Calculate the set of permissions to KEEP (current_group_perms minus revoked_perms)
                perms_to_keep = current_group_perms.difference(revoked_perms)
                
                # We update the group permissions to the set of permissions that should remain.
                group.permissions.set(perms_to_keep)
                
                # Cleaned up print statement for better debugging:
                revoked_pks = [p.pk for p in revoked_perms]
                # print(f"Revoked {len(revoked_perms)} permissions (PKs: {revoked_pks}) from group '{group.name}' in org '{org.name}'.")
                
    logger.debug(f"Permission sync complete for org '{org.name}'. {users_to_update.count()} users updated.")


@receiver(m2m_changed, sender=LicenseGrant.curriculum_node.through)
def update_org_and_user_streams(sender, instance, action, pk_set, **kwargs):
    """
    Sync organization supported boards and user profile streams whenever curriculum nodes 
    are added/removed from a LicenseGrant.
    """
    # Only proceed for relevant actions
    if action not in ["post_add", "post_remove", "post_clear"]:
        return

    org = instance.organization_profile
    if not org:
        return
        
    # Determine if this action should trigger the "revocation" logic for user targeting
    is_revocation_action = action in ["post_remove", "post_clear"]
    # print(f"LicenseGrant M2M change detected. Action: {action}. Revocation Action: {is_revocation_action}")

    with transaction.atomic():
        today = date.today()
        
        # 1. FIND ALL ACTIVE LICENSES FOR THIS ORGANIZATION
        active_licenses_qs = org.license_grants.filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=today)
        )

        is_license_active = True if active_licenses_qs else False
        
        # --- 2. GLOBAL RECALCULATION OF ALL ACTIVE LICENSED NODES ---
        all_licensed_nodes_qs = TreeNode.objects.filter(
            licensegrant__in=active_licenses_qs
        ).distinct()

        final_stream_pks = set()
        for node in all_licensed_nodes_qs:
            final_stream_pks.add(node.pk)

            # Efficiently retrieve and add all ancestors and descendants to the stream
            # ancestors = node.get_ancestors(include_self=False)
            # final_stream_pks.update([n.pk for n in ancestors])

            # descendants = node.get_descendants(include_self=False)
            # final_stream_pks.update([d.pk for d in descendants])

        all_active_nodes_pk = list(final_stream_pks)
        
        
        # --- 3. DETERMINE TARGET USERS (Applying Selective/Global Policy) ---
        profile_filter = {'organization_profile': org}
        
        # Policy: If adding, only update admin profiles. If removing/clearing, update ALL users.
        if not is_revocation_action:
            profile_filter['user__role'] = 'admin'
        
        user_profiles = Profile.objects.filter(**profile_filter).select_related('user')
        
        # Apply the calculated stream to the target users
        for profile in user_profiles:
            profile.academic_stream.set(all_active_nodes_pk)
            profile.is_license_active = is_license_active
            profile.save()

            
            
            
        # --- 4. SYNC MANAGEMENT PERMISSIONS (Use the helper function) ---
        # The stream M2M change should not trigger group sync as it's not a full license revocation
        _sync_organization_permissions(org, is_deletion=is_revocation_action)
                
        # --- 5. Sync Organization Supported Boards ---
        root_board_pks = TreeNode.objects.filter(
            pk__in=all_active_nodes_pk,
            node_type__in=["board", "competitive"],
            parent__isnull=True
        ).values_list('pk', flat=True)
        
        org.supported_curriculum.set(root_board_pks)
        org.save()


# NEW SEPARATE SIGNAL HANDLERS
@receiver([post_save, post_delete], sender=LicenseGrant)
def sync_on_license_grant_change(sender, instance, **kwargs):
    """
    Handles changes (save/delete) to the main LicenseGrant.
    - Triggers full user permission sync.
    - Triggers group revocation (sync_groups=True) ONLY on deletion.
    - Triggers full stream/board sync ONLY on deletion.
    """
    is_deletion = kwargs.get('signal') == post_delete
    
    # 1. Determine the OrganizationProfile
    org = instance.organization_profile
    if not org:
        return

    # Determine if we should perform group revocation (Part B of sync).
    # Group revocation is expensive and is primarily required when the LicenseGrant itself is deleted.
    # True only when LicenseGrant is deleted

    # Recalculate all active licensed permissions for debugging context (optional for clarity)
    today = date.today()
    active_licenses_qs = org.license_grants.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today)
    )
    all_perms = Permission.objects.filter(
        licensepermission__license__in=active_licenses_qs
    ).distinct()



    # print(f"License change detected on {sender.__name__}. is_deletion={is_deletion}. Active Licensed Permissions: {all_perms.count()} perms,signals {kwargs.get('signal')}")
    
    # Call the synchronized permission logic
    with transaction.atomic():
        # is_deletion controls the user targeting (All users vs. Admins only)
        _sync_organization_permissions(org, is_deletion=is_deletion)
        
        # If the license is DELETED, we must also manually trigger the full stream sync
        if is_deletion:
             # This is a simplification: we'll call the M2M logic with "post_clear" context
             # to ensure full stream recalculation and user targeting.
             update_org_and_user_streams(
                 LicenseGrant.curriculum_node.through, 
                 instance, 
                 "post_clear", 
                 pk_set=set(), 
                 **kwargs
             )

    logger.debug(f"LicenseGrant sync completed for organization {org.name}.")

@receiver([post_save, post_delete], sender=LicensePermission)
def sync_on_license_permission_change(sender, instance, **kwargs):
    """
    Handles changes (save/delete) to the LicensePermission M2M table.
    - Triggers user permission sync only.
    - Group revocation (sync_groups=False) is explicitly suppressed as this is often part of an edit.
    """
    is_deletion = kwargs.get('signal') == post_delete
    
    # 1. Determine the OrganizationProfile
    # For post_delete of LicensePermission, the foreign key might be unavailable.
    try:
        org = instance.license.organization_profile
    except AttributeError:
        return # License was likely deleted in cascade
    
    if not org:
        return
    
    # Group revocation is explicitly suppressed for LicensePermission changes (sync_groups=False)
   

    # Recalculate all active licensed permissions for debugging context (optional for clarity)
    today = date.today()
    active_licenses_qs = org.license_grants.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today)
    )
    all_perms = Permission.objects.filter(
        licensepermission__license__in=active_licenses_qs
    ).distinct()
    
    # Removed the aggressive print() statement to reduce log noise during M2M operations.
    logger.debug(f"License change detected on {sender.__name__}. is_deletion={is_deletion}. Active Licensed Permissions: {all_perms.count()} perms. ")
    
    # Call the synchronized permission logic
    with transaction.atomic():
        # is_deletion controls the user targeting (All users vs. Admins only)
        _sync_organization_permissions(org, is_deletion=is_deletion)

    logger.debug(f"LicensePermission sync completed for organization {org.name}.")