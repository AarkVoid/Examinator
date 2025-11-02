import logging
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

# --- NOTE: Replace these placeholder imports with your actual models ---
# Assuming these models are accessible in your project:
# from your_app.models import LicenseGrant, OrganizationProfile, Profile, TreeNode
# from django.contrib.auth.models import User, Permission
# -----------------------------------------------------------------------

# --- Placeholder definitions for running the command independently ---
# You MUST replace these with your actual model imports.
from saas.models import LicenseGrant
from saas.models import OrganizationProfile
from accounts.models import User, Profile
from curritree.models import TreeNode
from django.contrib.auth.models import Permission
# -----------------------------------------------------------------------

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Synchronizes user permissions and streams for organizations whose licenses have recently expired.'

    def handle(self, *args, **options):
        today = date.today()
        self.stdout.write(f"Starting license synchronization check for {today}...")

        # 1. Identify all organizations that have at least one license that expired before today.
        # We look for organizations whose *active* license count might have just changed.
        affected_orgs = OrganizationProfile.objects.filter(
            license_grants__valid_until__lt=today,
            license_grants__valid_until__isnull=False # Ensure we only check for licenses with explicit expiration dates
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
                    
                    for profile in user_profiles:
                        # Use .set() to efficiently synchronize the M2M field
                        profile.academic_stream.set(all_active_nodes_pk)

                    self.stdout.write(f"  -> Synced {len(all_active_nodes_pk)} stream nodes for {user_profiles.count()} users (All Users).")

                    # 3. Sync Organization Supported Boards/Curriculum
                    root_board_pks = TreeNode.objects.filter(
                        pk__in=all_active_nodes_pk,
                        node_type__in=["board", "competitive"],
                        parent__isnull=True  # This guarantees it's a top-level node
                    ).values_list('pk', flat=True)
                    
                    org.supported_curriculum.set(root_board_pks)
                    org.save()


                    # --- B. PERMISSION SYNC (Global Revocation) ---

                    # 1. Get aggregate permissions from the calculated active licenses
                    all_perms = Permission.objects.filter(
                        licensepermission__license__in=active_licenses_qs
                    ).distinct()
                    
                    # 2. Find target users
                    # 🛑 FIX: Target ALL users for global permission revocation on expiry.
                    users_to_update = User.objects.filter(
                        profile__organization_profile=org
                    )

                    # 3. Use the bulk approach for efficient update
                    UserPermissionM2M = User._meta.get_field('user_permissions').remote_field.through
                    
                    # The clearing/setting process below ensures that only permissions 
                    # from ACTIVE licenses remain on ANY user.
                    for user in users_to_update:
                        # Clear old permissions (Crucial for revocation)
                        UserPermissionM2M.objects.filter(user=user).delete() 

                        # Bulk create new permissions (if the user is an admin, they will get them back 
                        # if they are in the all_perms set, if not, they remain cleared).
                        if all_perms and user.role == 'admin': # Only re-add permissions to admins
                            new_user_perms = [
                                UserPermissionM2M(user=user, permission=perm)
                                for perm in all_perms
                            ]
                            UserPermissionM2M.objects.bulk_create(new_user_perms, ignore_conflicts=True)
                            
                    self.stdout.write(f"  -> Synced {all_perms.count()} permissions for {users_to_update.count()} users.")
                    total_synced_orgs += 1
                    
            except Exception as e:
                logger.error(f"Error processing organization {org.id}: {e}")
                self.stdout.write(self.style.ERROR(f"FATAL ERROR for Org {org.id}. Check logs."))


        self.stdout.write(self.style.SUCCESS(f"Finished. Successfully synchronized data for {total_synced_orgs} organizations."))
