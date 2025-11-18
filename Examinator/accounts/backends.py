from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class MultiFieldLoginBackend(BaseBackend):
    """
    Custom authentication backend that allows users to log in using 
    username, email, or phone number.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        The 'username' argument here is the credential the user provides in the login form,
        which could be a username, email, or phone number.
        """
        
        # 1. Look up the user by matching the credential against username, email, or phone_number
        try:
            # We use Q objects to combine multiple OR conditions
            user = User.objects.get(
                Q(username__iexact=username) |  # Case-insensitive username match
                Q(email__iexact=username) |     # Case-insensitive email match
                Q(phone_number=username)        # Exact phone number match
            )
        except User.DoesNotExist:
            # No user found matching any of the fields
            return None

        # 2. Check the password
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        # Password did not match
        return None

    def get_user(self, user_id):
        """
        Required method for the backend to retrieve a user instance using the primary key (id).
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def user_can_authenticate(self, user):
        """
        Override this to check if the user is active/allowed to log in. 
        Matches Django's default behavior, checking for user.is_active.
        """
        return user.is_active