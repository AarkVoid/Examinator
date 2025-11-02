# institute/forms.py
from django import forms
from .models import Institution, InstitutionPasskey,InstituteApplication

from education.models import Board

class InstitutionForm(forms.ModelForm):
    """
    Form for creating and updating Institution instances with cascading dropdowns
    for Country, State, and Board.
    """


    class Meta:
        model = Institution
        # IMPORTANT: Only include fields that are directly on the Institution model for saving.
        # 'country' and 'state' are excluded here.
        fields = ['name', 'code', 'address', 'board'] 
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-700 border-slate-600 border rounded-xl text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition'}),
            'code': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-700 border-slate-600 border rounded-xl text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition'}),
            'address': forms.Textarea(attrs={'class': 'w-full px-4 py-2 bg-slate-700 border-slate-600 border rounded-xl text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition', 'rows': 4}),
            'board': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-slate-700 border-slate-600 border rounded-xl text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 transition',
                'id': 'id_board' # ID for JavaScript to target
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set board queryset to all boards
        self.fields['board'].queryset = Board.objects.all().order_by('name')
        self.fields['board'].empty_label = "Select a Board"



class InstitutionPasskeyForm(forms.ModelForm):
    class Meta:
        model = InstitutionPasskey
        fields = ['institution', 'passkey', 'valid_until']
        widgets = {
            'institution': forms.Select(attrs={'class': 'form-select'}),
            'passkey': forms.TextInput(attrs={'class': 'form-input'}),
            'valid_until': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }


class InstituteApplicationForm(forms.ModelForm):
    """
    Form for users to apply to an institution.
    Note: 'user' field is excluded as it will be set automatically.
    """
    class Meta:
        model = InstituteApplication
        fields = ['institution', 'passkey_attempt'] # Exclude 'user'
        widgets = {
            'institution': forms.Select(attrs={'class': 'form-select'}),
            'passkey_attempt': forms.TextInput(attrs={'class': 'form-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Pop the 'user_institute' from kwargs if it was passed
        user_institute = kwargs.pop('user_institute', None) 
        super().__init__(*args, **kwargs)

        # Order institutions alphabetically for better UX
        self.fields['institution'].queryset = Institution.objects.all().order_by('name')

        # If a user's institute is provided, set it as the initial selection
        if user_institute:
            self.fields['institution'].initial = user_institute.id 

