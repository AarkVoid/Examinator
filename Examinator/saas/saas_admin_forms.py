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

TAILWIND_INPUT_ATTRS = {
    'class': (
        'w-full px-4 py-2.5 border rounded-lg transition-all duration-150 '
        'bg-gray-50 border-gray-300 text-gray-900 '
        'dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 '
        'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 '
        'dark:focus:ring-blue-400 dark:focus:border-blue-400'
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
    Form to create a new client user (admin role) and gather their core details.
    Uses first_name and last_name from the User model.
    """
    # User fields - Username (NEWLY EXPOSED FIELD)
    username = forms.CharField(
        max_length=150, 
        required=True, 
        label="Username", 
        widget=forms.TextInput(attrs=TAILWIND_INPUT_CLASSES)
    )

    # User fields - Name (Now explicitly part of the User model via inheritance)
    first_name = forms.CharField(
        max_length=150, # Max length of first_name in AbstractUser
        required=True, 
        label="First Name", 
        widget=forms.TextInput(attrs=TAILWIND_INPUT_CLASSES)
    )
    last_name = forms.CharField(
        max_length=150, # Max length of last_name in AbstractUser
        required=True, 
        label="Last Name", 
        widget=forms.TextInput(attrs=TAILWIND_INPUT_CLASSES)
    )
    
    # User fields - Optional Phone Number
    phone_number = forms.CharField(
        max_length=20, 
        required=False, 
        label="Phone Number (Optional)", 
        widget=forms.TextInput(attrs=TAILWIND_INPUT_CLASSES)
    )
    
    # User fields - password
    password = forms.CharField(
        widget=forms.PasswordInput(attrs=TAILWIND_INPUT_CLASSES),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs=TAILWIND_INPUT_CLASSES),
        label="Confirm Password"
    )
    
    # Hidden field for role
    role = forms.CharField(
        required=False,
        initial='admin', 
        widget=forms.HiddenInput()
    )

    class Meta:
        model = User
        # UPDATED: Added 'username' to fields
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number'] 
        widgets = {
            'email': forms.EmailInput(attrs=TAILWIND_INPUT_CLASSES),
        }
    
    # NEW CLEAN METHOD: Ensures username is unique
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not password:
            raise forms.ValidationError("Password is required.")
        try:
            # Pass the instance (self.instance is often None during creation)
            validate_password(password, self.instance) 
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        # 1. Password Match Check
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
            
        # 2. Removed automatic username derivation as it is now an explicit field
        
        return cleaned_data
        
    @transaction.atomic
    def save(self, commit=True):
        """
        Custom save method to create the User with name fields and the associated Profile instance.
        """
        # 1. Create the User instance
        user = super().save(commit=False)
        
        # Username is automatically set by super().save() because it's in Meta.fields
        user.set_password(self.cleaned_data['password'])
        
        # Set inherited name and new phone number fields
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone_number = self.cleaned_data.get('phone_number')
        
        # Set the custom role field
        if hasattr(user, 'role') and self.cleaned_data.get('role'):
            user.role = self.cleaned_data['role']
            
        if commit:
            user.save()
            
            # 2. Ensure the Profile object exists
            try:
                # Retrieve profile if a signal automatically creates it
                profile = user.profile 
            except:
                # Explicitly create the Profile if not done by a signal
                profile = Profile.objects.create(user=user) 
            
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
    A standalone form to select content boundaries and define usage limits
    for a new LicenseGrant object.
    """
    # Maps to LicenseGrant.curriculum_node (M2M field)
    curriculum_nodes = forms.ModelMultipleChoiceField(
        # Filter choices to Class, Subject, or Unit level nodes
        # NOTE: Using 'curritree.TreeNode' needs to be imported or correctly referenced
        # I'll use a placeholder queryset for demonstration.
        queryset=TreeNode.objects.filter(node_type__in=['class', 'subject', 'unit']).order_by('node_type', 'name'),
        label="Select Curriculum Nodes for Access",
        # UPDATED USAGE: Merge the base attributes with the height class
        widget=forms.SelectMultiple(attrs={**TAILWIND_INPUT_CLASSES, 'class': TAILWIND_INPUT_CLASSES['class'] + ' h-48'}),
        help_text="Select all specific content boundaries to license (e.g., 'Class 10 Science', 'JEE Maths')."
    )

    # Maps to LicenseGrant.max_question_papers
    max_question_papers = forms.IntegerField(
        required=False,
        initial=50, # Matches the model default
        min_value=1,
        # UPDATED USAGE: Use the ATTRS dictionary directly
        widget=forms.NumberInput(attrs=TAILWIND_INPUT_CLASSES),
        label="Max Question Papers (Limit)",
        help_text="The maximum number of question papers this organization can generate."
    )

    # Maps to LicenseGrant.valid_until
    valid_until = forms.DateField(
        required=False,
        # UPDATED USAGE: Merge the ATTRS dictionary with the type attribute
        widget=forms.DateInput(attrs={**TAILWIND_INPUT_CLASSES, 'type': 'date'}),
        label="License Expiry Date (Optional)"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Ensure the M2M queryset filtering is robust
        try:
            from curritree.models import TreeNode
            self.fields['curriculum_nodes'].queryset = TreeNode.objects.filter(
                node_type__in=['class', 'subject', 'board', 'competitive'] # Updated to match model limit_choices_to
            ).order_by('node_type', 'name')
        except Exception:
            # Fallback if TreeNode is not defined
            self.fields['curriculum_nodes'].queryset = None


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
            'supported_curriculum': forms.SelectMultiple(attrs={
                **TAILWIND_INPUT_CLASSES, 
                'disabled': 'disabled'
            }),
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
    




