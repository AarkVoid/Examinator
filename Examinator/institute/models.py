from django.db import models
from django.conf import settings
from django.db.models.signals import pre_save, post_delete,post_save
from django.dispatch import receiver




class InstitutionGroup(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    board = models.ManyToManyField(
        'education.Board',
        blank=True,
        null=True,
    )


    def __str__(self):
        return self.name
    

class Institution(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    board = models.ForeignKey('education.Board', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    group = models.ForeignKey(InstitutionGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='institutionGroup')

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('institute:institution_detail', kwargs={'pk': self.pk})



@receiver(pre_save, sender=Institution)
def handle_institution_update(sender, instance, **kwargs):
    """Handle case where institution's group or board changes."""
    if not instance.pk:  # New object, skip (post_save handles it)
        return

    try:
        old_instance = Institution.objects.get(pk=instance.pk)
    except Institution.DoesNotExist:
        return

    # If group or board changed
    if old_instance.group != instance.group or old_instance.board != instance.board:
        # Remove old board from old group if not used anymore
        if old_instance.group and old_instance.board:
            still_used = Institution.objects.filter(
                group=old_instance.group,
                board=old_instance.board
            ).exclude(pk=old_instance.pk).exists()

            if not still_used:
                old_instance.group.board.remove(old_instance.board)


@receiver(post_save, sender=Institution)
def sync_institution_board_on_save(sender, instance, created, **kwargs):
    """Ensure institution's board is reflected in its group (create or update)."""
    if instance.group and instance.board:
        instance.group.board.add(instance.board)


@receiver(post_delete, sender=Institution)
def sync_institution_board_on_delete(sender, instance, **kwargs):
    """Remove board from group if no other institution in same group uses it."""
    if instance.group and instance.board:
        still_used = Institution.objects.filter(
            group=instance.group,
            board=instance.board
        ).exists()

        if not still_used:
            instance.group.board.remove(instance.board)




class InstitutionPasskey(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    passkey = models.CharField(max_length=100)
    valid_until = models.DateField()

    def __str__(self):
        return f"{self.institution.name} - Passkey"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('institute:passkey_detail', kwargs={'pk': self.pk})



class InstituteApplication(models.Model):
    """
    Model to store pending applications from users to join an institution.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    # --- CHANGE THIS LINE ---
    # From OneToOneField to ForeignKey
    # Use related_name='institute_applications' (plural) for consistency
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='institute_applications')

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    passkey_attempt = models.CharField(max_length=100, blank=True, null=True, help_text="Passkey entered by the user (if any)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    # Fields to track approval/rejection
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, help_text="Notes from the admin reviewing the application.")

    class Meta:
        verbose_name = "Institute Application"
        verbose_name_plural = "Institute Applications"
        # --- REMOVE OR MODIFY THIS LINE ---
        # unique_together = ('user', 'institution',)
        # If you keep unique_together=('user', 'institution',), it means a user can apply to a specific institution ONLY ONCE, EVER.
        # If you want a user to be able to apply to the same institution again after being rejected/approved, REMOVE this line.
        # If you want to enforce one application per user per institution (regardless of status), keep it.
        # Based on your view logic, you likely want to REMOVE this, as the UniqueConstraint below handles pending.
        
        constraints = [
            # This constraint correctly ensures a user can only have ONE pending application at any given time.
            models.UniqueConstraint(fields=['user'], condition=models.Q(status='pending'), name='unique_pending_application_per_user')
        ]

    def __str__(self):
        return f"Application by {self.user.username} for {self.institution.name} ({self.status})"
