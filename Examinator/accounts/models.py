from django.db import models
from django.contrib.auth.models import AbstractUser , Group, Permission
from django.conf import settings
from django.utils import timezone
import uuid
from datetime import date
from django.db.models.signals import post_save,pre_delete
from django.dispatch import receiver

# ================
# Reusable Timestamp Base
# ================
class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True,null=True,blank=True)
    modified = models.DateTimeField(auto_now=True,null=True,blank=True)

    class Meta:
        abstract = True


class EmailVerificationToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.user.email} - {self.token}"

    def is_valid(self):
        return self.expires_at > timezone.now()

# ================
# Custom User Model
# ================
class User(AbstractUser, TimeStampedModel):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Staff'),
        ('admin', 'Admin'),
    ]
    # email = models.EmailField(unique=True)
    # USERNAME_FIELD = "email"    # ✅ this tells Django to use email as login
    # REQUIRED_FIELDS = ['username']  # 👈 This is the crucial fix

    email = models.EmailField(unique=True)
    
    # --- NEW FIELD FOR FLEXIBLE LOGIN ---
    phone_number = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True, 
        null=True,
        help_text="Optional. Used for alternate login or two-factor authentication."
    )
    # ------------------------------------

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ['email'] 

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    is_active = models.BooleanField(default=True)

    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )


    def __str__(self):
        return f"{self.username} ({self.role})"
    

# ================
# Profile Model
# ================
class Profile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='profile',
        # Adding a database index to the ForeignKey for faster join/lookup performance
        db_index=True 
    )
    address = models.TextField(blank=True)
    # Name = models.CharField(max_length=100,null=True, blank=True)
    # Surname = models.CharField(max_length=100,null=True, blank=True)
    MiddleName = models.CharField(max_length=100, null=True, blank=True)
    Contact = models.BigIntegerField(blank=True, null=True)
    BirthDate = models.DateField(default=date.today, blank=True, null=True)
    
    # CONTENT/CURRICULUM CONTEXT (from curritree app)
    # CONSOLIDATED: Use one field to specify the user's highest access level (Stream)
    academic_stream = models.ManyToManyField(
        'curritree.TreeNode', 
        blank=True, # blank=True is necessary for M2M fields to be optional
        verbose_name="Academic Stream/Content Boundary",
        # Allow linking to Board, Class, Subject, etc., depending on the enrollment level
        limit_choices_to={'node_type__in': ['board', 'competitive', 'class', 'subject']} 
    )
    # SAAS CLIENT RELATIONSHIP (from saas app)
    # This directly links the user to the paying entity/tenant.
    organization_profile = models.ForeignKey(
        'saas.OrganizationProfile', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Client Organization"
    )

    organization_groups = models.ManyToManyField(
        'accounts.OrganizationGroup',
        blank=True,
        related_name='members',
        verbose_name="Organization Groups"
    )
    
    pic = models.ImageField(upload_to='profileImg', null=True, blank=True)

    impersonation_pin = models.CharField(
        max_length=128, 
        blank=True, 
        null=True,
        default=12345,
        # NOTE: For production, this field MUST store a secure hash, not the plaintext PIN.
        help_text="A security PIN required for staff/admin users (non-superusers) to impersonate this user. Use a hashing function before saving in production."
    )


    def __str__(self):
        # ✅ FIX: Use .all() to get the queryset and .join() to format the names.
        stream_names = ", ".join([s.name for s in self.academic_stream.all()])
        return f"{self.user.username} Profile | Stream(s): {stream_names or 'Unassigned'}"
    
    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"


class OrganizationGroup(TimeStampedModel):
    """
    Represents a custom group defined within a specific organization.
    This model ties groups and their permissions directly to a tenant, 
    ensuring isolation and preventing naming conflicts between clients.
    """
    organization = models.ForeignKey(
        'saas.OrganizationProfile', 
        on_delete=models.CASCADE, 
        related_name='custom_groups', 
        verbose_name="Organization"
    )
    
    # The name of the group
    name = models.CharField(max_length=150)
    
    # Permissions assigned to this group
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='organization_groups',
        verbose_name="Permissions"
    )

    class Meta:
        # CRUCIAL: Ensures a group name is only unique within the scope of its organization.
        # This allows multiple organizations to have a group named "Managers" without conflict.
        unique_together = (('organization', 'name'),)
        verbose_name = "Organization Group"
        verbose_name_plural = "Organization Groups"
    
    def __str__(self):
        # We try to use the name attribute of the organization object.
        org_name = self.organization.name if hasattr(self.organization, 'name') else 'Organization ID: ' + str(self.organization_id)
        return f"{self.name} ({org_name})"
    


