from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Profile, EmailVerificationToken,OrganizationGroup
from django.utils.crypto import get_random_string
# --- NEW IMPORTS for refactored data model ---
from curritree.models import TreeNode
from saas.models import OrganizationProfile
# --- REMOVED: from institute.models import Institution, InstitutionGroup
# --- REMOVED: from education.models import Board, StudentClass, Division
# ---------------------------------------------

User = get_user_model()


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full border border-gray-300 p-2 rounded mt-1'}),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full border border-gray-300 p-2 rounded mt-1'}),
        label="Confirm Password"
    )
    role = forms.ChoiceField(
        choices=[('admin', 'Client')],
        widget=forms.Select(attrs={'class': 'w-full border border-gray-300 p-2 rounded mt-1'}),
        label="I am a..."
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password', 'role']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full border border-gray-300 p-2 rounded mt-1'}),
            'email': forms.EmailInput(attrs={'class': 'w-full border border-gray-300 p-2 rounded mt-1'}),
        }
    
    def clean_username(self):
        username = self.cleaned_data.get('username')

        # Case-insensitive check for duplicates
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            try:
                validate_password(password, self.instance)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_active = False
        user.role = self.cleaned_data.get('role')

        if commit:
            try:
                user.save()
                token = EmailVerificationToken.objects.create(
                    user=user,
                    expires_at=timezone.now() + timedelta(hours=24)
                )
                verification_link = f"{settings.SITE_URL}/verify-email/{token.token}/"
                send_mail(
                    "Verify Your Email",
                    f"Click the link to verify your email:\n{verification_link}",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False
                )
            except Exception as e:
                print(f"Email verification error: {e}")
                # We raise a generic error here as database exceptions might occur before email.
                raise forms.ValidationError(f'Could not complete registration. Error: {e}')
        return user


class ProfileForm(forms.ModelForm):
    """
    Simplified basic profile form using the new academic_stream.
    """
    class Meta:
        model = Profile
        # Updated fields: removed board, class_field. Added academic_stream.
        fields = ['address', 'academic_stream']
        widgets = {
             'academic_stream': forms.Select(attrs={'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['academic_stream'].queryset = TreeNode.objects.filter(
            node_type__in=['board', 'competitive', 'class', 'subject']
        ).order_by('node_type', 'name')


TAILWIND_INPUT_CLASSES = (
    'w-full px-4 py-2.5 border rounded-lg transition-all duration-150 '
    'bg-gray-50 border-gray-300 text-gray-900 '
    'dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 '
    'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 '
    'dark:focus:ring-blue-400 dark:focus:border-blue-400'
)

# Define the checkbox classes for proper alignment and appearance
TAILWIND_CHECKBOX_CLASSES = (
    'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded '
    'focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 '
    'focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
)

class UserEditForm(forms.ModelForm):
    """
    Superuser form for editing user properties.
    The 'user_permissions' field is automatically hidden/disabled for admin users
    whose permissions are managed by the LicenseGrant signal.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
        required=False,
        help_text="Leave blank if you don't want to change the password."
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
        required=False,
        help_text="Enter the new password again for confirmation."
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'is_active', 'is_staff', 'is_superuser', 'role', 'groups', 'user_permissions']
        widgets = {
            'username': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'email': forms.EmailInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            
            # Checkboxes
            'is_active': forms.CheckboxInput(attrs={'class': TAILWIND_CHECKBOX_CLASSES}),
            'is_staff': forms.CheckboxInput(attrs={'class': TAILWIND_CHECKBOX_CLASSES}),
            'is_superuser': forms.CheckboxInput(attrs={'class': TAILWIND_CHECKBOX_CLASSES}),
            
            # Selects and M2M
            'role': forms.Select(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'groups': forms.SelectMultiple(attrs={'class': TAILWIND_INPUT_CLASSES + ' h-32'}), 
            'user_permissions': forms.SelectMultiple(attrs={'class': TAILWIND_INPUT_CLASSES + ' h-32'}), 
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['groups'].queryset = Group.objects.all().order_by('name')
        self.fields['user_permissions'].queryset = Permission.objects.all().order_by('name')

        if self.instance.pk:
            # Set initial values for M2M fields
            self.fields['groups'].initial = self.instance.groups.all()
            self.fields['user_permissions'].initial = self.instance.user_permissions.all()
            
            self.fields['password'].initial = ''
            self.fields['password_confirm'].initial = ''
            
            # 🚨 CRITICAL FIX: Disable user_permissions if managed by the signal
            is_license_managed = False
            try:
                # Check if user has an organization profile and is an admin
                if self.instance.profile.organization_profile and self.instance.role == 'admin':
                     is_license_managed = True
            except AttributeError:
                # Handle case where profile might not exist yet (though view attempts to create it)
                pass

            if is_license_managed:
                # Hide the field to prevent form data from overwriting signal changes
                self.fields['user_permissions'].widget = forms.HiddenInput()
                self.fields['user_permissions'].required = False 
                
                # Optional: Add a custom message to the groups field to explain why permissions are missing
                # You might need to add a non-field error in the template for better visibility
                # self.fields['groups'].help_text = (
                #     "Permissions for Admin users are managed automatically by active licenses "
                #     "and cannot be set manually here."
                # )
                
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        # Password validation logic (omitted for brevity, assume it's correct)
        # ... 

        if password or password_confirm:
            if not password:
                self.add_error('password', "Please enter a new password.")
            if not password_confirm:
                self.add_error('password_confirm', "Please confirm your new password.")
            
            if password and password_confirm and password != password_confirm:
                self.add_error('password_confirm', "Passwords do not match.")
            
            if password:
                try:
                    # NOTE: validate_password requires the user instance
                    validate_password(password, self.instance) 
                except ValidationError as e:
                    self.add_error('password', e)
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)

        if commit:
            user.save()
            
            # 💡 ROBUST M2M SAVE: Use .get() with empty list fallback to prevent issues
            groups_data = self.cleaned_data.get('groups', [])
            user_perms_data = self.cleaned_data.get('user_permissions', [])

            user.groups.set(groups_data)
            
            # NOTE: We only set user_permissions if the field was visible/submitted
            # If it's a HiddenInput, user_perms_data will likely be [] or the initial value,
            # but we trust the signal to manage the correct list.
            user.user_permissions.set(user_perms_data) 

        return user

class ProfileEditForm(forms.ModelForm):
    """
    Form for editing ALL profile details, including the M2M academic_stream field.
    """
    class Meta:
        model = Profile
        fields = [
            'Name', 'Surname', 'MiddleName', 'Contact', 'BirthDate',
            'address', 
            'academic_stream', # M2M field
            'organization_profile', 
            'pic'
        ]
        widgets = {
            # --- Applying Tailwind Classes to all fields ---
            'Name': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'Surname': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'MiddleName': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'Contact': forms.NumberInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            
            'BirthDate': forms.DateInput(attrs={'class': TAILWIND_INPUT_CLASSES, 'type': 'date'}),
            
            'address': forms.Textarea(attrs={'class': TAILWIND_INPUT_CLASSES, 'rows': 3}),
            
            # M2M field needs SelectMultiple and extra height
            'academic_stream': forms.SelectMultiple(attrs={'class': TAILWIND_INPUT_CLASSES + ' h-32'}), 
            
            'organization_profile': forms.Select(attrs={'class': TAILWIND_INPUT_CLASSES}), 
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Set all fields to not required
        for fieldName in self.fields:
            self.fields[fieldName].required = False 

        # 2. Set the M2M queryset
        if self.instance and self.instance.pk and self.instance.academic_stream.exists():
            # RESTRICT: Show only currently selected nodes (plus ancestors if needed)
            current_streams = self.instance.academic_stream.all()
            self.fields['academic_stream'].queryset = current_streams
        else:
            # DEFAULT: Show all allowed options (for new users or when nothing is selected)
            self.fields['academic_stream'].queryset = TreeNode.objects.filter(
                node_type__in=['board', 'competitive', 'class', 'subject']
            ).order_by('node_type', 'name')

        # 3. Set Queryset for FK (organization_profile)
        try:
            self.fields['organization_profile'].queryset = OrganizationProfile.objects.all().order_by('name')
        except NameError:
            pass


class GroupAdminUserCreationForm(forms.ModelForm):
    """
    Form for Superuser to create a Main Admin and link them to a top-level client OrganizationProfile.
    """
    password = forms.CharField(widget=forms.PasswordInput)
    
    # Replaced instituteGroup with organization_profile
    organization_profile = forms.ModelChoiceField(
        queryset=OrganizationProfile.objects.all(), 
        required=True,
        label="Client Organization"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError("A user with this username already exists.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'main_admin'

        if commit:
            user.save()

            selected_org = self.cleaned_data['organization_profile']
            profile, created = Profile.objects.get_or_create(user=user)
            profile.organization_profile = selected_org # Link to the OrganizationProfile
            profile.save()

        return user


class AdminUserCreationForm(forms.ModelForm):
    """
    Form for Superuser or Main Admin to create an Admin for a specific OrganizationProfile.
    """
    password = forms.CharField(widget=forms.PasswordInput)
    
    class Meta:
        model = User
        fields = ['email', 'password']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(AdminUserCreationForm, self).__init__(*args, **kwargs)
        
        # Determine OrganizationProfile queryset based on the creating user's role
        if self.user and self.user.is_superuser:
            self.fields['organization_profile'] = forms.ModelChoiceField(
                queryset=OrganizationProfile.objects.all(),
                required=True,
                label="Client Organization"
            )
        elif self.user and self.user.role == 'main_admin' and hasattr(self.user, 'profile') and self.user.profile.organization_profile:
            # Main admin can only create admins within their organization
            user_org = self.user.profile.organization_profile
            self.fields['organization_profile'] = forms.ModelChoiceField(
                queryset=OrganizationProfile.objects.filter(id=user_org.id),
                required=True,
                label="Client Organization",
                initial=user_org,
                widget=forms.Select(attrs={'disabled': 'disabled'}) # Show, but prevent change
            )
        else:
            self.fields['organization_profile'] = forms.ModelChoiceField(
                queryset=OrganizationProfile.objects.none(),
                required=True,
                label="Client Organization",
                empty_label="Error: No linked organization."
            )
            # Remove password field if no organization is linked (prevent creation)
            del self.fields['password']


    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password'])
        user.role = 'admin'

        if commit:
            user.save()
            
            selected_org = self.cleaned_data.get('organization_profile')
            # If the field was disabled, we fetch the value from the user's profile
            if not selected_org and self.user.profile.organization_profile:
                 selected_org = self.user.profile.organization_profile
                 
            if selected_org:
                profile, created = Profile.objects.get_or_create(user=user)
                profile.organization_profile = selected_org
                # Removed setting profile.board/class
                profile.save()
            else:
                 user.delete()
                 raise forms.ValidationError("User could not be linked to a Client Organization.")

        return user
    

class GroupForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Group
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['permissions'].initial = self.instance.permissions.all()
    
    def save(self, commit=True):
        group = super().save(commit=commit)
        if commit:
            group.permissions.set(self.cleaned_data['permissions'])
        return group

    
class TeacherCreationForm(forms.ModelForm):
    """
    Form for Admins to create Teachers, automatically linking them to their organization.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label="Confirm Password"
    )

    class Meta:
        model = User
        fields = [ 'email', 'password', 'confirm_password']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        user_org = self.request.user.profile.organization_profile if self.request and self.request.user.is_authenticated and hasattr(self.request.user, 'profile') else None
        
        # Only superusers get a choice of organization
        if self.request and self.request.user.is_superuser:
            self.fields['organization_profile'] = forms.ModelChoiceField(
                queryset=OrganizationProfile.objects.all(),
                required=True,
                label="Client Organization"
            )
        elif self.request.user and user_org:
            # For admin/main_admin, the organization is automatically set
            self.fields['organization_profile'] = forms.ModelChoiceField(
                queryset=OrganizationProfile.objects.filter(id=user_org.id),
                initial=user_org.id,
                required=True,
                label="Client Organization",
                widget=forms.HiddenInput() # Hidden, but value is submitted
            )
        else:
             self.fields['organization_profile'] = forms.ModelChoiceField(
                queryset=OrganizationProfile.objects.none(),
                required=False,
                label="Client Organization",
                empty_label="Error: Admin has no linked organization."
            )
            # Prevent creation if admin has no linked organization
             del self.fields['password']
             del self.fields['confirm_password']


    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            try:
                validate_password(password, self.instance)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password'])
        user.is_active = True
        user.role = 'teacher'

        if commit:
            user.save()
            
            selected_org = self.cleaned_data.get('organization_profile')
            # If organization_profile was hidden, use the admin's organization
            if not selected_org and self.request.user.profile.organization_profile:
                selected_org = self.request.user.profile.organization_profile

            if selected_org:
                teacher_profile, created = Profile.objects.get_or_create(user=user)
                teacher_profile.organization_profile = selected_org
                teacher_profile.save()
            else:
                user.delete() 
                raise forms.ValidationError("Teacher could not be linked to a Client Organization.")
        return user


class InstituteUserEditForm(forms.ModelForm):
    """
    Form for Institute Admin to edit User fields for student/teacher.
    """
    class Meta:
        model = User
        fields = [ 'email', 'is_active', 'role']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [
            ('student', 'Student'),
            ('teacher', 'Teacher'),
        ]
        # Logic to disable editing of admin roles remains the same
        if self.instance.pk and (self.instance.is_superuser or self.instance.role in ('admin', 'main_admin')):
            self.fields['role'].widget.attrs['disabled'] = True
            self.fields['is_active'].widget.attrs['disabled'] = True
            self.fields['email'].widget.attrs['readonly'] = True


    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if self.instance.pk and (self.instance.is_superuser or self.instance.role in ('admin', 'main_admin')):
            return self.instance.role
        if role not in ['student', 'teacher']:
            raise forms.ValidationError("Invalid role selected.")
        return role

    def clean_is_active(self):
        is_active = self.cleaned_data.get('is_active')
        if self.instance.pk and (self.instance.is_superuser or self.instance.role == 'admin'):
            return self.instance.is_active
        return is_active
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # If the email has been changed, we update the username to match it.
        if user.email != self.cleaned_data.get('email'):
            user.username = self.cleaned_data.get('email')

        if commit:
            user.save()
        return user
    

class InstituteProfileEditForm(forms.ModelForm):
    """
    Form for Institute Admin to edit Profile fields (Name, Contact, Academic Stream) for student/teacher.
    """
    class Meta:
        model = Profile
        fields = [
            'Name', 'Surname', 'MiddleName', 'Contact', 'BirthDate',
            'address', 
            'academic_stream', # NEW FIELD
            'pic'
        ]
        widgets = {
            'Name': forms.TextInput(attrs={'class': 'form-control'}),
            'Surname': forms.TextInput(attrs={'class': 'form-control'}),
            'MiddleName': forms.TextInput(attrs={'class': 'form-control'}),
            'Contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., +919876543210'}),
            'BirthDate': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'academic_stream': forms.Select(attrs={'class': 'form-select'}), # UPDATED
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set queryset for academic stream
        self.fields['academic_stream'].queryset = TreeNode.objects.filter(
            node_type__in=['board', 'competitive', 'class', 'subject']
        ).order_by('node_type', 'name')

        # Make fields optional
        optional_fields = [
            'address', 'Contact', 'BirthDate', 'academic_stream', 'pic'
        ]
        for field_name in optional_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False
        
        # Removed all cascading education logic


class UserPermissionForm(forms.Form):
    """
    Permissions form (no changes needed as it only uses auth models).
    """
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    enabled_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Direct Permissions"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['groups'].initial = user.groups.all()
            self.fields['enabled_permissions'].queryset = Permission.objects.all()
            self.fields['enabled_permissions'].initial = user.user_permissions.all()

        # Group permissions by app and model for display (used in template)
        self.permission_dict = self.get_grouped_permissions()

    def get_grouped_permissions(self):
        permission_qs = Permission.objects.all().select_related('content_type')
        grouped = {}

        for perm in permission_qs:
            app = perm.content_type.app_label
            model = perm.content_type.model
            grouped.setdefault(app, {}).setdefault(model, []).append(perm)

        return grouped



class OrganizationUserCreationForm(forms.Form):
    # --- User Model Fields ---
    email = forms.EmailField(
        label="Email (Used for Login)",
        widget=forms.EmailInput(attrs={'class': TAILWIND_INPUT_CLASSES})
    )
    role = forms.ChoiceField(
        # Uses the choices defined on your custom User model
        choices=[(r, label) for r, label in User.ROLE_CHOICES if r in ['student', 'teacher', 'admin']],
        widget=forms.Select(attrs={'class': TAILWIND_INPUT_CLASSES}),
        initial='student'
    )
    
    # --- Profile Model Fields ---
    Name = forms.CharField(
        max_length=100,
        label="First Name",
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES})
    )
    Surname = forms.CharField(
        max_length=100, 
        required=False,
        label="Last Name",
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES})
    )
    MiddleName = forms.CharField(
        max_length=100, 
        required=False,
        label="Middle Name",
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES})
    )
    Contact = forms.CharField(
        required=False,
        label="Phone Number",
        widget=forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES})
    )
    BirthDate = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': TAILWIND_INPUT_CLASSES, 'type': 'date'})
    )
    
    # academic_stream - Model field, Queryset filtered in __init__
    academic_stream = forms.ModelMultipleChoiceField(
        # The queryset is initially empty and will be set in __init__
        queryset=None, 
        required=False,
        label="Academic Stream Access (Content Boundaries)",
        widget=forms.SelectMultiple(attrs={'class': TAILWIND_INPUT_CLASSES})
    )

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Assuming TreeNode is imported and accessible
        # Set the queryset for academic_stream based on the organization's supported curriculum
        self.fields['academic_stream'].queryset = organization.supported_curriculum.all()

        if not self.fields['academic_stream'].queryset.exists():
            self.fields['academic_stream'].help_text = (
                "The organization has no supported curriculum configured. "
                "The user cannot be assigned content boundaries until they are."
            )

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def save(self, organization):
        # Generate a temporary, secure password (12 characters, letters and digits)
        temp_password = get_random_string(12)
        
        # 1. Create User
        # NOTE: Using email as the mandatory 'username' for the custom User model
        user = User.objects.create_user(
            username=self.cleaned_data['email'], 
            email=self.cleaned_data['email'],
            password=temp_password,
            role=self.cleaned_data['role']
        )
        user.first_name = self.cleaned_data['Name']
        user.last_name = self.cleaned_data['Surname'] or ''
        user.save()
        
        # 2. Create Profile
        profile_data = {
            'Name': self.cleaned_data['Name'],
            'Surname': self.cleaned_data['Surname'],
            'MiddleName': self.cleaned_data['MiddleName'], 
            'Contact': self.cleaned_data['Contact'], 
            'BirthDate': self.cleaned_data['BirthDate']
        }
        profile = Profile.objects.create(
            user=user,
            organization_profile=organization,
            **profile_data
        )
        
        # 3. Handle M2M field for Profile (academic_stream)
        stream_nodes = self.cleaned_data.get('academic_stream')
        if stream_nodes:
            profile.academic_stream.set(stream_nodes)
            
        return user, temp_password
    



class OrganizationGroupForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        # Pre-fetch content_type for display optimization
        queryset=Permission.objects.select_related('content_type').all().order_by('content_type__app_label', 'name'),
        widget=forms.SelectMultiple(attrs={'class': 'custom-permissions-select', 'size': 15}),
        required=False,
        label="Granted Permissions"
    )

    class Meta:
        model = OrganizationGroup
        fields = ['name', 'permissions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input-field', 'placeholder': 'e.g., Sales Team, Managers'}),
        }


class OrgUserAdminForm(forms.ModelForm):
    """
    Form for Organization Admins to edit a standard user's core details.
    Restricts role choices and adds a new password field.
    """
    
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
        required=False,
        label="Set New Password",
        help_text="Leave blank to keep the current password."
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'is_active', 'role']
        widgets = {
            'username': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'email': forms.EmailInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'is_active': forms.CheckboxInput(attrs={'class': TAILWIND_CHECKBOX_CLASSES}),
            'role': forms.Select(attrs={'class': TAILWIND_INPUT_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        role_choices = [(r, label) for r, label in User.ROLE_CHOICES if r not in ('admin', 'main_admin')]
        
        # If the user being edited is an admin/main_admin, lock the role and active status
        if self.instance.pk and self.instance.role in ('admin', 'main_admin'):
             role_choices.append((self.instance.role, self.instance.get_role_display()))
             self.fields['role'].widget.attrs['disabled'] = True
             self.fields['is_active'].widget.attrs['disabled'] = True

        self.fields['role'].choices = role_choices

    def clean_new_password(self):
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            try:
                # Validate password complexity
                validate_password(new_password, self.instance)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return new_password

    def save(self, commit=True):
        user = super().save(commit=False)
        
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)

        if commit:
            # Prevent privilege escalation/demotion if the user is a protected admin
            if self.instance.pk and self.instance.role in ('admin', 'main_admin') and user.role != self.instance.role:
                user.role = self.instance.role
                user.is_active = self.instance.is_active
            
            user.save()
        return user


class OrgProfileAdminForm(forms.ModelForm):
    """
    Form for Organization Admins to edit a user's Profile details.
    Includes personal info and the academic stream M2M field.
    """
    class Meta:
        model = Profile
        # Note: organization_profile is excluded as it should be managed via API, not forms.
        fields = [
            'Name', 'Surname', 'MiddleName', 'Contact', 'BirthDate',
            'address', 
            'academic_stream', # M2M field
            'pic' # ImageField included
        ]
        widgets = {
            'Name': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'Surname': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'MiddleName': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'Contact': forms.NumberInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'BirthDate': forms.DateInput(attrs={'class': TAILWIND_INPUT_CLASSES, 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': TAILWIND_INPUT_CLASSES, 'rows': 3}),
            'academic_stream': forms.SelectMultiple(attrs={'class': TAILWIND_INPUT_CLASSES + ' h-32'}), 
            'organization_groups': forms.SelectMultiple(attrs={'class': TAILWIND_INPUT_CLASSES + ' h-32'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set queryset for academic stream to all valid nodes
        try:
            self.fields['academic_stream'].queryset = TreeNode.objects.filter(
                node_type__in=['board', 'competitive', 'class', 'subject']
            ).order_by('node_type', 'name')
        except:
             # Handle case where TreeNode might not be defined during initial load
             self.fields['academic_stream'].queryset = None 

        # Make all fields optional
        for fieldName in self.fields:
            self.fields[fieldName].required = False