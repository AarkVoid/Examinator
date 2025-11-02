from django import forms
from saas.models import OrganizationProfile, LicenseGrant, UsageLimit,LicensePermission
from django.contrib.auth import get_user_model
from curritree.models import TreeNode
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from accounts.models import User,Profile
from django.core.mail import send_mail
from django.db import transaction
from accounts.models import Profile
from django.contrib.auth.models import Permission
from django.db.models import Q

# --- Define the shared Tailwind input classes ---
TAILWIND_INPUT_CLASSES = {
    'class': (
        'w-full px-4 py-2.5 border rounded-lg transition-all duration-150 '
        'bg-gray-50 border-gray-300 text-gray-900 '
        'dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 '
        'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 '
        'dark:focus:ring-blue-400 dark:focus:border-blue-400'
    )
}

TAILWIND_CHECKBOX_CLASSES = {
    'class': (
        'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded '
        'focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 '
        'focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
    )
}


WIDGET_ATTRS = {
    'class': 'w-full border border-gray-300 p-3 rounded-xl mt-1 focus:ring-blue-500 focus:border-blue-500 transition duration-150 dark:bg-gray-800 dark:border-gray-700 dark:text-white',
}
User = get_user_model()


# --- 1. New Client User Form (Creates User + Gathers Profile Data) ---
def get_username_from_email(email):
    # Takes the part before @ (e.g., 'john.doe@example.com' -> 'john.doe')
    return email.split('@')[0]

class NewClientUserForm(forms.ModelForm):
    """
    Form to create a new client user (admin role) and gather their profile details.
    The 'username' field is derived from the 'email'.
    """
    # Profile fields (Name, Surname)
    Name = forms.CharField(
        max_length=100, 
        required=True, 
        label="First Name", 
        widget=forms.TextInput(attrs=TAILWIND_INPUT_CLASSES)
    )
    Surname = forms.CharField(
        max_length=100, 
        required=True, 
        label="Last Name", 
        widget=forms.TextInput(attrs=TAILWIND_INPUT_CLASSES)
    )
    
    # User fields (password)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs=TAILWIND_INPUT_CLASSES),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs=TAILWIND_INPUT_CLASSES),
        label="Confirm Password"
    )
    
    # Hidden field for role (assumes 'role' is a field on your custom User model)
    role = forms.CharField(
        required=False,
        initial='admin', 
        widget=forms.HiddenInput()
    )

    class Meta:
        model = User
        fields = ['email'] # Only include fields that belong to the User model
        widgets = {
            'email': forms.EmailInput(attrs=TAILWIND_INPUT_CLASSES),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Manually set field order for better user experience
        # self.fields.keyOrder = ['email', 'Name', 'Surname', 'password', 'confirm_password', 'role']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Ensure email is unique (case-insensitive check is often safer)
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not password:
            # Note: This check is redundant if the field is required=True, 
            # but is good for explicitness.
            raise forms.ValidationError("Password is required.")
        try:
            # Pass the instance (self.instance is often None during creation)
            validate_password(password) 
        except ValidationError as e:
            # Re-raise with a clear message for the user
            raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        email = cleaned_data.get("email")

        # 1. Password Match Check
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
            
        # 2. Set username (MANDATORY for Django User model, even if unused)
        if email:
            # Set the cleaned_data for save() to use
            cleaned_data['username'] = get_username_from_email(email)
            
        # 3. Ensure Profile fields are present (if CharField, this is redundant 
        # due to required=True, but serves as a final safety check for logic)
        if not cleaned_data.get('Name'):
            self.add_error('Name', "First Name is required.")
        if not cleaned_data.get('Surname'):
            self.add_error('Surname', "Last Name is required.")

        return cleaned_data
        
    @transaction.atomic
    def save(self, commit=True):
        """
        Custom save method to create the User and the associated Profile instance.
        """
        # 1. Create the User instance
        user = super().save(commit=False)
        
        # Set mandatory fields before saving
        user.username = self.cleaned_data['username']
        user.set_password(self.cleaned_data['password'])
        
        # Set the custom role field
        if hasattr(user, 'role') and self.cleaned_data.get('role'):
            user.role = self.cleaned_data['role']
            
        if commit:
            user.save()
            
            # 2. Create or Update the Profile object
            # Assuming 'Profile' model is imported and linked via a reverse accessor named 'profile'
            try:
                # If a signal automatically creates the profile, this retrieves it
                profile = user.profile 
            except:
                # If no signal is set up, explicitly create the Profile
                # NOTE: You must import your Profile model here if not done already
                profile = Profile.objects.create(user=user) 

            # Update profile fields
            profile.Name = self.cleaned_data['Name']
            profile.Surname = self.cleaned_data['Surname']
            
            profile.save()

        return user

class OrganizationAssignmentForm(forms.Form):
    """
    Form to either select an existing organization OR create a new one.
    """
    existing_organization = forms.ModelChoiceField(
        queryset=OrganizationProfile.objects.all(),
        required=False,
        empty_label="--- Select an existing Organization to assign ---",
        label="Existing Organization",
        widget=forms.Select(attrs=WIDGET_ATTRS)
    )

    # Fields for creating a NEW organization
    new_org_name = forms.CharField(
        max_length=255,
        required=False,
        label="New Organization Name",
        help_text="Provide a name if creating a new organization.",
        widget=forms.TextInput(attrs=WIDGET_ATTRS)
    )
    new_billing_email = forms.EmailField(
        required=False,
        label="New Organization Contact Email",
        help_text="Provide an email if creating a new organization.",
        widget=forms.EmailInput(attrs=WIDGET_ATTRS)
    )

    def clean(self):
        cleaned_data = super().clean()
        existing_org = cleaned_data.get('existing_organization')
        new_name = cleaned_data.get('new_org_name')
        new_email = cleaned_data.get('new_billing_email')

        # Scenario 1: Both existing and new fields are provided (Error)
        if existing_org and (new_name or new_email):
            raise forms.ValidationError(
                "You cannot select an existing organization and create a new one simultaneously. Please choose one option."
            )

        # Scenario 2: Creating a new organization
        elif new_name or new_email:
            # Check if both new fields are provided
            if not (new_name and new_email):
                raise forms.ValidationError(
                    "To create a new organization, both the Name and the Contact Email are required."
                )

            # Check for uniqueness of the new organization name
            if OrganizationProfile.objects.filter(name__iexact=new_name).exists():
                raise forms.ValidationError(
                    f"An organization named '{new_name}' already exists."
                )
            
            # Check for uniqueness of the new billing email
            if OrganizationProfile.objects.filter(billing_email=new_email).exists():
                 raise forms.ValidationError(
                    f"The billing email '{new_email}' is already associated with an organization."
                )

        # Scenario 3: Neither existing nor new fields are provided (Error)
        elif not existing_org:
            raise forms.ValidationError(
                "You must either select an existing organization or provide details to create a new one."
            )

        return cleaned_data


# --- 2. Organization Assignment Form (Select or Create) ---
class OrganizationAssignmentForm(forms.Form):
    """
    Form to allow the Superuser to either select an existing organization OR 
    create a new one to link the new admin user to.
    """
    existing_organization = forms.ModelChoiceField(
        queryset=OrganizationProfile.objects.all().order_by('name'),
        required=False,
        label="Link to Existing Organization",
        help_text="Select an existing client, OR fill the fields below to create a new one.",
        widget=forms.Select(attrs=WIDGET_ATTRS)
    )
    
    # Fields for creating a NEW organization
    new_org_name = forms.CharField(
        max_length=255, 
        required=False, 
        label="New Organization Name",
        widget=forms.TextInput(attrs=WIDGET_ATTRS)
    )
    new_billing_email = forms.EmailField(
        required=False, 
        label="New Organization Billing Email",
        widget=forms.EmailInput(attrs=WIDGET_ATTRS)
    )

    def clean(self):
        cleaned_data = super().clean()
        existing_org = cleaned_data.get('existing_organization')
        new_name = cleaned_data.get('new_org_name')
        new_email = cleaned_data.get('new_billing_email')

        # Scenario 1: Both existing and new fields are filled (Invalid)
        if existing_org and (new_name or new_email):
            raise forms.ValidationError("You must either select an existing organization OR create a new one, not both.")
        
        # Scenario 2: Neither existing nor new fields are filled (Invalid)
        if not existing_org and not (new_name and new_email):
            raise forms.ValidationError("You must either select an existing organization or provide a name and email to create a new one.")

        # Scenario 3: Creating a new organization, check for uniqueness
        if new_name:
            if OrganizationProfile.objects.filter(name__iexact=new_name).exists():
                self.add_error('new_org_name', "An organization with this name already exists.")
        
        if new_email:
            if OrganizationProfile.objects.filter(billing_email=new_email).exists():
                self.add_error('new_billing_email', "This billing email is already registered to an organization.")

        return cleaned_data



# --- 1. Organization Profile Form ---
class OrganizationProfileForm(forms.ModelForm):
    class Meta:
        model = OrganizationProfile
        fields = ['name', 'billing_email', 'is_active', 'supported_curriculum']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Tailwind classes to all fields
        for name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full border border-gray-300 p-3 rounded-xl mt-1 focus:ring-blue-500 focus:border-blue-500 transition duration-150 dark:bg-gray-800 dark:border-gray-700 dark:text-white',
            })
        # Special styling for M2M fields
        if 'supported_curriculum' in self.fields:
            self.fields['supported_curriculum'].widget.attrs.update({'size': '5'})


# --- 2. Usage Limit Form ---
class UsageLimitForm(forms.ModelForm):
    class Meta:
        model = UsageLimit
        fields = ['max_users', 'max_question_papers_drafts']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Tailwind classes
        self.fields['max_users'].widget.attrs.update({
            'class': 'w-full border border-gray-300 p-3 rounded-xl mt-1 focus:ring-blue-500 focus:border-blue-500 transition duration-150 dark:bg-gray-800 dark:border-gray-700 dark:text-white',
        })
        self.fields['max_question_papers_drafts'].widget.attrs.update({
            'class': 'w-full border border-gray-300 p-3 rounded-xl mt-1 focus:ring-blue-500 focus:border-blue-500 transition duration-150 dark:bg-gray-800 dark:border-gray-700 dark:text-white',
        })

# --- 3. License Grant Form (for multiple grants) ---
class MultipleLicenseGrantForm(forms.Form):
    """
    A standalone form to select multiple curriculum nodes to license at once.
    """
    curriculum_nodes = forms.ModelMultipleChoiceField(
        # Filter choices to Class, Subject, or Unit level nodes
        queryset=TreeNode.objects.filter(node_type__in=['class', 'subject', 'unit']).order_by('node_type', 'name'),
        label="Select Curriculum Nodes (Class/Subject/Unit) for Access",
        widget=forms.SelectMultiple(attrs={'size': '10'}),
        help_text="Select all specific content boundaries to license (e.g., 'Class 10 Science', 'JEE Maths')."
    )
    valid_until = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="License Expiry Date (Optional)"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Tailwind classes
        for name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full border border-gray-300 p-3 rounded-xl mt-1 focus:ring-blue-500 focus:border-blue-500 transition duration-150 dark:bg-gray-800 dark:border-gray-700 dark:text-white',
            })
        self.fields['curriculum_nodes'].widget.attrs['class'] += ' h-48' 


# --- 4. User Assignment Form (to link a client admin to the Organization) ---
class UserAssignmentForm(forms.Form):
    """
    Form to select the User (who is usually the Client Admin) to link to the OrganizationProfile.
    """
    client_admin_user = forms.ModelChoiceField(
        # Filter users who are not currently linked to an organization
        queryset=User.objects.filter(profile__organization_profile__isnull=True).order_by('email'),
        label="Select Client Administrator to Assign",
        help_text="Choose the user who registered and will manage this organization."
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Tailwind classes
        self.fields['client_admin_user'].widget.attrs.update({
            'class': 'w-full border border-gray-300 p-3 rounded-xl mt-1 focus:ring-blue-500 focus:border-blue-500 transition duration-150 dark:bg-gray-800 dark:border-gray-700 dark:text-white',
        })



class OrganizationCreateForm(forms.ModelForm):
    class Meta:
        model = OrganizationProfile
        # Fields matching the provided OrganizationProfile model
        fields = [
            'name', 'billing_email', 'supported_curriculum', 'is_active'
        ]
        widgets = {
            # Apply the comprehensive input class to all text/email fields
            'name': forms.TextInput(attrs=TAILWIND_INPUT_CLASSES),
            'billing_email': forms.EmailInput(attrs=TAILWIND_INPUT_CLASSES),
            
            # Apply input class and set height for the multi-select field
            'supported_curriculum': forms.SelectMultiple(attrs={
                **TAILWIND_INPUT_CLASSES, 
                'multiple': True, 
                'size': 6  # Gives the box a good default height
            }),
            
            # Apply the specific checkbox class
            'is_active': forms.CheckboxInput(attrs=TAILWIND_CHECKBOX_CLASSES),
        }


class OrganizationEditForm(forms.ModelForm):
    class Meta:
        model = OrganizationProfile
        fields = [
            'name', 'billing_email', 'is_active','phone_number','address', 'supported_curriculum'
        ]
        widgets = {
            'name': forms.TextInput(attrs=TAILWIND_INPUT_CLASSES),
            'billing_email': forms.EmailInput(attrs=TAILWIND_INPUT_CLASSES),
            'supported_curriculum': forms.SelectMultiple(attrs=TAILWIND_INPUT_CLASSES),
            'is_active': forms.CheckboxInput(attrs=TAILWIND_CHECKBOX_CLASSES),
            'address': forms.Textarea(attrs={**TAILWIND_INPUT_CLASSES, 'rows': 6,'cols': 12}),
            'phone_number': forms.TextInput(attrs=TAILWIND_INPUT_CLASSES),
        }

# --- Form for Adding a New License (Requires a separate model) ---

class LicenseGrantForm(forms.ModelForm):
    # Define the field here, but set the final filtered queryset in __init__
    permissions = forms.ModelMultipleChoiceField(
        # Initial queryset can be generic, but we override it below
        queryset=Permission.objects.none(), 
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'w-full rounded custom-permissions-select border-gray-300',
            'size': 10,
        }),
        label="Granted Permissions"
    )

    class Meta:
        model = LicenseGrant
        fields = ['curriculum_node', 'valid_until', 'permissions']
        widgets = {
            'curriculum_node': forms.SelectMultiple(attrs={
                'class': 'w-full rounded border-gray-300',
                'id': 'id_license_curriculum_nodes', 
                'size': 10,
            }),
            'valid_until': forms.DateInput(attrs={
                'type': 'date',
                'class': 'rounded border-gray-300'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1. Filter curriculum_node (Existing Logic)
        self.fields['curriculum_node'].queryset = TreeNode.objects.filter(
            parent__isnull=True
        ).order_by('name')

        # 2. Filter Permissions (Existing Logic)
        APP_LABELS = ['accounts', 'quiz'] 
        ACTION_CODENAMES = ['add_', 'change_', 'delete_', 'view_']

        app_filter = Q(content_type__app_label__in=APP_LABELS)
        
        action_filter = Q()
        for action in ACTION_CODENAMES:
            action_filter |= Q(codename__startswith=action)

        self.fields['permissions'].queryset = Permission.objects.filter(
            app_filter & action_filter
        ).select_related('content_type').order_by(
            'content_type__app_label', 'codename'
        )

    # 🎯 NEW: Dedicated method to save the permissions M2M records 
    def save_permissions(self, license_instance):
        """Saves the M2M permissions data to the LicensePermission intermediary model."""
        
        # Ensure the instance has been saved before proceeding
        if not license_instance.pk:
            raise ValueError("LicenseGrant instance must be saved before saving permissions.")

        # 1. Clear existing LicensePermission records for this license
        LicensePermission.objects.filter(license=license_instance).delete() 
        
        # 2. Create new LicensePermission records based on the form's cleaned data
        for perm in self.cleaned_data.get('permissions', []):
            LicensePermission.objects.create(license=license_instance, permission=perm)

    # Revert save() to the standard implementation for simplicity and reliability
    # The view must now call save_permissions(instance) manually after saving the instance.
    def save(self, commit=True):
        """
        The overridden save method for ModelForm.
        We ensure it returns the instance without touching M2M data, 
        which will be handled by the new save_permissions method.
        """
        return super().save(commit)
    




