import logging
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

# --- NOTE: Replace these placeholder imports with your actual models ---
# Assuming these models are accessible in your project:
# from your_app.models import LicenseGrant, OrganizationProfile, Profile, TreeNode
# from django.contrib.auth.models import User, Permission, Group
# -----------------------------------------------------------------------

# --- Placeholder definitions for running the command independently ---
from saas.models import LicenseGrant
from saas.models import OrganizationProfile
from accounts.models import User, Profile
from curritree.models import TreeNode
from django.contrib.auth.models import Permission, Group  # Added Group import
# -----------------------------------------------------------------------

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Synchronizes user permissions and streams for organizations whose licenses have recently expired.'

    def handle(self, *args, **options):
        today = date.today()
        self.stdout.write(f"Starting license synchronization check for {today}...")

        # 1. Identify all organizations that have at least one license that expired before today.
        affected_orgs = OrganizationProfile.objects.filter(
            license_grants__valid_until__lt=today,
            license_grants__valid_until__isnull=False
        ).distinct()

        if not affected_orgs.exists():
            self.stdout.write(self.style.SUCCESS("No organizations found with recently expired licenses. Exiting."))
            return

        total_synced_orgs = 0
        
        for org in affected_orgs:
            try:
                with transaction.atomic():
                    self.stdout.write(f"Processing organization: {org.name} (ID: {org.id})")
                    
                    # Get the queryset of ALL licenses that are still ACTIVE (including non-expiring ones)
                    active_licenses_qs = org.license_grants.filter(
                        Q(valid_until__isnull=True) | Q(valid_until__gte=today)
                    )
                    
                    # --- A. ACADEMIC STREAM & CURRICULUM SYNC (Global Revocation) ---

                    
                    # 1. Recalculate all licensed nodes based ONLY on currently active licenses
                    all_licensed_nodes_qs = TreeNode.objects.filter(
                        licensegrant__in=active_licenses_qs
                    ).distinct()
                    
                    final_stream_pks = set()
                    # Recalculate stream to include ancestors and descendants of the remaining active nodes
                    for node in all_licensed_nodes_qs:
                        final_stream_pks.add(node.pk)

                        # We use .get_ancestors and .get_descendants from the MPTT model
                        ancestors = node.get_ancestors(include_self=False)
                        for ancestor in ancestors:
                            final_stream_pks.add(ancestor.pk)

                        descendants = node.get_descendants(include_self=False)
                        for descendant in descendants:
                            final_stream_pks.add(descendant.pk)

                    all_active_nodes_pk = list(final_stream_pks)
                    
                    # 2. Sync User Profile Streams (M2M field)
                    # 🛑 CRITICAL: Target ALL users for stream recalculation to ensure revocation for everyone.
                    user_profiles = Profile.objects.filter(organization_profile=org) 

                    is_license_active = active_licenses_qs.exists()
                    for profile in user_profiles:
                        profile.is_license_active = is_license_active
                        profile.academic_stream.set(all_active_nodes_pk) # Use .set() to efficiently synchronize the M2M field
                        profile.save()

                    self.stdout.write(f"  -> Synced {len(all_active_nodes_pk)} stream nodes for {user_profiles.count()} users (All Users).")

                    
                    # 3. Sync Organization Supported Boards/Curriculum
                    board_pks = TreeNode.objects.filter(
                        pk__in=all_active_nodes_pk,
                        node_type__in=["board", "competitive","class","subject","unit","chapter","section"],
                        parent__isnull=True  # This guarantees it's a top-level node
                    ).values_list('pk', flat=True)
                    
                    org.supported_curriculum.set(all_active_nodes_pk)
              
                    org.save()

                    
                    # --- CONDITIONAL STOP ADDED HERE ---
                    if not is_license_active:
                        self.stdout.write(self.style.WARNING(f"  -> Organization {org.name} has NO active licenses remaining. Stopping further sync for this organization (Curriculum/Permissions)."))
                        total_synced_orgs += 1
                        continue # Skip the rest of the loop for this organization
                    # ----------------------------------


                    # --- B. PERMISSION SYNC (Global Revocation) ---

                    # 1. Get aggregate permissions from the calculated active licenses
                    all_perms_qs = Permission.objects.filter(
                        licensepermission__license__in=active_licenses_qs
                    ).distinct()
                    # Get the PKs for efficient set comparison
                    licensed_perms_pks = set(all_perms_qs.values_list('pk', flat=True))
                    
                    # 2. Sync Organization Custom Groups 
                    # This logic ensures unlicensed permissions are revoked from groups.
                    try:
                        organization_groups = org.custom_groups.all() 
                        total_groups_synced = 0

                        for group in organization_groups:
                            current_group_perms_pks = set(group.permissions.values_list('pk', flat=True))

                            # Permissions to KEEP are the intersection of currently held and currently licensed
                            perms_to_keep_pks = current_group_perms_pks.intersection(licensed_perms_pks)
                            
                            # We set the group permissions to the set of permissions that should remain.
                            group.permissions.set(list(perms_to_keep_pks))
                            total_groups_synced += 1

                        self.stdout.write(f"  -> Synced {total_groups_synced} custom groups, revoking unlicensed permissions.")
                    except AttributeError:
                        self.stdout.write(self.style.WARNING("  -> WARNING: Skipping Group Sync. 'custom_groups' field not found on OrganizationProfile."))


                    # 3. Find target users and sync permissions
                    users_to_update = User.objects.filter(
                        profile__organization_profile=org
                    )

                    # 4. Use the bulk approach for efficient update of direct user permissions (FIXED LOGIC)
                    UserPermissionM2M = User._meta.get_field('user_permissions').remote_field.through
                    
                    for user in users_to_update:
                        
                        # 4.1. Get the primary keys of the permissions currently held directly by the user.
                        current_user_direct_perms_pks = set(
                            user.user_permissions.all().values_list('pk', flat=True)
                        )

                        # 4.2. Identify permissions that are no longer licensed (and thus must be revoked).
                        # These are permissions the user holds (A) that are NOT in the active licensed set (B).
                        perms_to_revoke_pks = current_user_direct_perms_pks.difference(licensed_perms_pks)
                        
                        # 4.3. REVOCATION: Remove only the permissions identified for revocation.
                        if perms_to_revoke_pks:
                            # Delete M2M entries where the permission PK is in the revocation set for this user.
                            UserPermissionM2M.objects.filter(
                                user=user, 
                                permission__pk__in=perms_to_revoke_pks
                            ).delete()
                            self.stdout.write(f"    -> Revoked {len(perms_to_revoke_pks)} unlicensed direct perms for {user.username}.")
                        
                        # 4.4. RE-GRANT/SYNC (Admin Specific: Full Sync)
                        if user.role == 'admin':
                            # Get the licensed permissions that the admin *does not* currently hold directly
                            # This prevents revoking existing licenses that they might have for other reasons,
                            # and only ensures they have the *full* set granted by licenses.
                            perms_to_add_pks = licensed_perms_pks.difference(current_user_direct_perms_pks)

                            if perms_to_add_pks:
                                # Bulk create M2M entries for the missing licensed permissions
                                perms_to_add = all_perms_qs.filter(pk__in=perms_to_add_pks)
                                new_user_perms = [
                                    UserPermissionM2M(user=user, permission=perm)
                                    for perm in perms_to_add
                                ]
                                UserPermissionM2M.objects.bulk_create(new_user_perms, ignore_conflicts=True)
                                self.stdout.write(f"    -> Added {len(new_user_perms)} licensed direct perms for Admin {user.username}.")


                        # 4.5. 🛑 CRITICAL FIX: Invalidate the user's permission cache
                        if hasattr(user, '_perm_cache'):
                            del user._perm_cache
                        if hasattr(user, '_user_perm_cache'):
                            del user._user_perm_cache
                        if hasattr(user, '_group_perm_cache'):
                            del user._group_perm_cache
                            
                    self.stdout.write(f"  -> Processed direct permissions for {users_to_update.count()} users.")
                    total_synced_orgs += 1
                    
            except Exception as e:
                logger.error(f"Error processing organization {org.id}: {e}")
                self.stdout.write(self.style.ERROR(f"FATAL ERROR for Org {org.id}. Check logs."))


        self.stdout.write(self.style.SUCCESS(f"Finished. Successfully synchronized data for {total_synced_orgs} organizations."))