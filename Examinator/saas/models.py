from django.db import models
from django.conf import settings
from django.db.models import UniqueConstraint, Q
from django.contrib.auth.models import Permission
from accounts.models import TimeStampedModel


# IMPORTANT: Ensure your curriculum app is named 'education'

class OrganizationProfile(models.Model):
    """
    The Tenant Model: Represents the paying organization (School, Coaching, Group).
    This acts as the main anchor for all licensing and user limits.
    """
    name = models.CharField(max_length=255, unique=True, verbose_name="Organization Name", help_text="The full name of the purchasing entity (e.g., 'Acme Academy').")
    billing_email = models.EmailField(unique=True, verbose_name="Primary Contact Email")
    is_active = models.BooleanField(default=True, verbose_name="Subscription Active", help_text="Designates if the organization's subscription is currently active.")
    
    # Top-level curriculum scope (for display/setup purposes)
    supported_curriculum = models.ManyToManyField(
        'curritree.TreeNode',
        blank=True,
        limit_choices_to={'node_type__in': ['board', 'competitive']},
        related_name='client_supported_curriculums',
        verbose_name="Supported Boards/Exams",
        help_text="The top-level curriculum (Boards/Exams) this organization operates under."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    address = models.TextField(blank=True, verbose_name="Organization Address")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="Contact Phone Number")

    class Meta:
        verbose_name = "Organization Profile (Tenant)"
        verbose_name_plural = "Organization Profiles (Tenants)"

    def __str__(self):
        return self.name

class LicenseGrant(models.Model):
    """
    Defines access to a specific curriculum node and its children (the license boundary).
    This is the core model for content gating.
    """
    organization_profile = models.ForeignKey(
        OrganizationProfile, 
        on_delete=models.CASCADE, 
        related_name='license_grants',
        verbose_name="Client Organization",
        help_text="The organization that holds this curriculum license."
    )

    curriculum_node = models.ManyToManyField(
        'curritree.TreeNode',
        blank=True,
        verbose_name="Licensed Curriculum Node",
        limit_choices_to={'node_type__in': ['class', 'subject', 'board', 'competitive']},
        help_text="The highest curriculum node (Class/Subject/Unit) to which access is granted (and all its children)."
    )

    permissions = models.ManyToManyField(
        Permission,
        through='LicensePermission', 
        blank=True,
        verbose_name="Assigned Permissions",
        help_text="The specific Django permissions granted by this license."
    )

    max_question_papers = models.PositiveIntegerField(
        default=50, 
        verbose_name="Maximum Question Papers",
        help_text="Maximum number of question papers this organization can generate."
    )

    question_papers_created = models.PositiveIntegerField(
        default=0, 
        verbose_name="No Of Question Papers created",
        help_text="number of question papers this organization has generate."
    )
    
    purchased_on = models.DateField(auto_now_add=True)
    valid_until = models.DateField(null=True, blank=True, verbose_name="License Expiry Date", help_text="Optional date when the license will automatically expire.")

    class Meta:
        # unique_together = ('organization_profile', 'curriculum_node')
        verbose_name = "Curriculum License Grant"
        verbose_name_plural = "Curriculum License Grants"

    def __str__(self):
        return f"License Grant for {self.organization_profile.name}"
    
    def get_all_licensed_nodes(self):
        """
        Returns a queryset of all curriculum nodes covered by this license,
        including all descendants of the licensed nodes.
        """
        from curritree.models import TreeNode  # Avoid circular import

        all_nodes = set()
        for node in self.curriculum_node.all():
            descendants = node.get_descendants(include_self=True)
            all_nodes.update(descendants)

        # Return as a queryset (not just a set)
        return TreeNode.objects.filter(id__in=[n.id for n in all_nodes])

class UsageLimit(models.Model):
    """
    Tracks the current active user limit for the OrganizationProfile's subscription.
    """
    organization_profile = models.OneToOneField(
        OrganizationProfile, 
        on_delete=models.CASCADE, 
        related_name='usage_limit'
    )
    max_users = models.PositiveIntegerField(
        default=1, 
        verbose_name="Maximum Allowed Users",
        help_text="Maximum number of active users allowed under this subscription plan."
    )
    
    max_question_papers_drafts = models.PositiveIntegerField(
        default=10, 
        verbose_name="Maximum Question Papers Drafts",
        help_text="Maximum number of question papers drafts this organization can generate."
    )

    class Meta:
        verbose_name = "Subscription Usage Limit"
        verbose_name_plural = "Subscription Usage Limits"

    def __str__(self):
        return f"{self.organization_profile.name} - Max Users: {self.max_users}"



class LicensePermission(models.Model):
    license = models.ForeignKey('LicenseGrant', on_delete=models.CASCADE, related_name='LicensePermission')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('license', 'permission')



