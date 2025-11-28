from django import forms
from django.forms import inlineformset_factory
from .models import Question, MCQOption, FillBlankAnswer, ShortAnswer, MatchPair, TrueFalseAnswer, QuestionPaper,FillBlankAnswerOrg,\
    ShortAnswerOrg,MatchPairOrg,TrueFalseAnswerOrg,OrgQuestion,MCQOptionOrg

from curritree.models import TreeNode 
import json

TAILWIND_INPUT_CLASSES = {
    'class': (
        'w-full px-4 py-2.5 border rounded-lg transition-all duration-150 '
        'bg-gray-50 border-gray-300 text-gray-900 '
        'dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 '
        'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 '
        'dark:focus:ring-blue-400 dark:focus:border-blue-400'
    )
}

# Checkbox styling
TAILWIND_CHECKBOX_CLASSES = {
    'class': (
        'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded '
        'focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 '
        'focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
    )
}

# Fallback/General Widget Attrs (using the verbose input classes is usually better)
# WIDGET_ATTRS = {
#     'class': 'w-full border border-gray-300 p-3 rounded-xl mt-1 focus:ring-blue-500 focus:border-blue-500 transition duration-150 dark:bg-gray-800 dark:border-gray-700 dark:text-white',
# }
# We will use TAILWIND_INPUT_CLASSES for consistency in the final output.
# ---------------------------------------------------------------------

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'question_type', 'curriculum_board', 'curriculum_class', # Added Class
            'curriculum_subject', 'curriculum_chapter', 'question_text', 
            'question_image',
            'difficulty', 'marks', 'is_published'
        ] 
        widgets = {
            'question_type': forms.Select(attrs=TAILWIND_INPUT_CLASSES),
            'curriculum_board': forms.Select(attrs=TAILWIND_INPUT_CLASSES),
            'curriculum_class': forms.Select(attrs=TAILWIND_INPUT_CLASSES), # Added Class widget
            'curriculum_subject': forms.Select(attrs=TAILWIND_INPUT_CLASSES),
            'curriculum_chapter': forms.Select(attrs=TAILWIND_INPUT_CLASSES),
            'question_text': forms.Textarea(attrs={**TAILWIND_INPUT_CLASSES, 'rows': 4}),
            'question_image': forms.FileInput(attrs=TAILWIND_INPUT_CLASSES),
            'difficulty': forms.Select(attrs=TAILWIND_INPUT_CLASSES),
            'marks': forms.NumberInput(attrs={**TAILWIND_INPUT_CLASSES, 'min': 1}),
            'is_published': forms.CheckboxInput(attrs=TAILWIND_CHECKBOX_CLASSES),
        }
    
    def __init__(self, *args, **kwargs):

        self.current_user = kwargs.pop('user', None)


        super().__init__(*args, **kwargs)

        if self.current_user and not (self.current_user.is_staff or self.current_user.is_superuser):
            self.fields.pop('is_published', None)

        
        # 1. Initialize Board Field (Always populated)
        self.fields['curriculum_board'].queryset = TreeNode.objects.filter(
            node_type__in=['board', 'competitive']
        ).order_by('name')



        # 2. Initialize Class, Subject, and Chapter fields to empty
        self.fields['curriculum_class'].queryset = TreeNode.objects.none()
        self.fields['curriculum_subject'].queryset = TreeNode.objects.none()
        self.fields['curriculum_chapter'].queryset = TreeNode.objects.none()
        
        # ====================================================================
        # START: Read-Only Logic (Includes curriculum_class)
        # ====================================================================

        if self.instance.pk:
            # Disable fields that define the fixed question structure
            fields_to_disable = [
                'question_type', 
                'curriculum_board', 
                'curriculum_class', # Added
                'curriculum_subject', 
                'curriculum_chapter'
            ]
            
            # for field_name in fields_to_disable:
            #     field = self.fields[field_name]
            #     field.widget.attrs['disabled'] = True
            #     field.required = False
            #     field.widget.attrs['class'] += ' opacity-70 bg-gray-100 dark:bg-gray-800/50 cursor-not-allowed'


        # ====================================================================
        # START: CASCADING LOGIC (Board -> Class -> Subject -> Chapter)
        # ====================================================================
        
        # A. Populate Class Field (Filter by Board)
        current_board = None
        board_id = self.data.get('curriculum_board') if 'curriculum_board' in self.data else (self.instance.curriculum_board.pk if self.instance.pk and self.instance.curriculum_board else None)
        
        if board_id:
            try:
                current_board = TreeNode.objects.get(pk=int(board_id))
                self.fields['curriculum_class'].queryset = TreeNode.objects.filter(
                    parent=current_board,
                    node_type='class'
                ).order_by('order', 'name')
            except (ValueError, TreeNode.DoesNotExist):
                pass
        
        # B. Populate Subject Field (Filter by Class)
        current_class = None
        class_id = self.data.get('curriculum_class') if 'curriculum_class' in self.data else (self.instance.curriculum_class.pk if self.instance.pk and self.instance.curriculum_class else None)
        
        if class_id:
            try:
                current_class = TreeNode.objects.get(pk=int(class_id))
                self.fields['curriculum_subject'].queryset = TreeNode.objects.filter(
                    parent=current_class,
                    node_type='subject'
                ).order_by('order', 'name')
            except (ValueError, TreeNode.DoesNotExist):
                pass

        # C. Populate Chapter Field (Filter by Subject)
        current_subject = None
        subject_id = self.data.get('curriculum_subject') if 'curriculum_subject' in self.data else (self.instance.curriculum_subject.pk if self.instance.pk and self.instance.curriculum_subject else None)
        
        if subject_id:
            try:
                current_subject = TreeNode.objects.get(pk=int(subject_id))
                self.fields['curriculum_chapter'].queryset = TreeNode.objects.filter(
                    parent=current_subject,
                    node_type='chapter'
                ).order_by('order', 'name')
            except (ValueError, TreeNode.DoesNotExist):
                pass


class OrgQuestionForm(forms.ModelForm):
    class Meta:
        model = OrgQuestion
        fields = [
            'question_type', 'curriculum_board', 'curriculum_class', # Added Class
            'curriculum_subject', 'curriculum_chapter', 'question_text', 
            'question_image',
            'difficulty', 'marks', 'is_published'
        ] 
        widgets = {
            'question_type': forms.Select(attrs=TAILWIND_INPUT_CLASSES),
            'curriculum_board': forms.Select(attrs=TAILWIND_INPUT_CLASSES),
            'curriculum_class': forms.Select(attrs=TAILWIND_INPUT_CLASSES), # Added Class widget
            'curriculum_subject': forms.Select(attrs=TAILWIND_INPUT_CLASSES),
            'curriculum_chapter': forms.Select(attrs=TAILWIND_INPUT_CLASSES),
            'question_text': forms.Textarea(attrs={**TAILWIND_INPUT_CLASSES, 'rows': 4}),
            'question_image': forms.FileInput(attrs=TAILWIND_INPUT_CLASSES),
            'difficulty': forms.Select(attrs=TAILWIND_INPUT_CLASSES),
            'marks': forms.NumberInput(attrs={**TAILWIND_INPUT_CLASSES, 'min': 1}),
            'is_published': forms.CheckboxInput(attrs=TAILWIND_CHECKBOX_CLASSES),
        }
    
    def __init__(self, *args, **kwargs):

        self.current_user = kwargs.pop('user', None)


        super().__init__(*args, **kwargs)

        if self.current_user and not (self.current_user.is_staff or self.current_user.is_superuser):
            self.fields.pop('is_published', None)

        
        # 1. Initialize Board Field (Always populated)
        self.fields['curriculum_board'].queryset = TreeNode.objects.filter(
            node_type__in=['board', 'competitive']
        ).order_by('name')



        # 2. Initialize Class, Subject, and Chapter fields to empty
        self.fields['curriculum_class'].queryset = TreeNode.objects.none()
        self.fields['curriculum_subject'].queryset = TreeNode.objects.none()
        self.fields['curriculum_chapter'].queryset = TreeNode.objects.none()
        
        # ====================================================================
        # START: Read-Only Logic (Includes curriculum_class)
        # ====================================================================

        if self.instance.pk:
            # Disable fields that define the fixed question structure
            fields_to_disable = [
                'question_type', 
                'curriculum_board', 
                'curriculum_class', # Added
                'curriculum_subject', 
                'curriculum_chapter'
            ]
            
            # for field_name in fields_to_disable:
            #     field = self.fields[field_name]
            #     field.widget.attrs['disabled'] = True
            #     field.required = False
            #     field.widget.attrs['class'] += ' opacity-70 bg-gray-100 dark:bg-gray-800/50 cursor-not-allowed'


        # ====================================================================
        # START: CASCADING LOGIC (Board -> Class -> Subject -> Chapter)
        # ====================================================================
        
        # A. Populate Class Field (Filter by Board)
        current_board = None
        board_id = self.data.get('curriculum_board') if 'curriculum_board' in self.data else (self.instance.curriculum_board.pk if self.instance.pk and self.instance.curriculum_board else None)
        
        if board_id:
            try:
                current_board = TreeNode.objects.get(pk=int(board_id))
                self.fields['curriculum_class'].queryset = TreeNode.objects.filter(
                    parent=current_board,
                    node_type='class'
                ).order_by('order', 'name')
            except (ValueError, TreeNode.DoesNotExist):
                pass
        
        # B. Populate Subject Field (Filter by Class)
        current_class = None
        class_id = self.data.get('curriculum_class') if 'curriculum_class' in self.data else (self.instance.curriculum_class.pk if self.instance.pk and self.instance.curriculum_class else None)
        
        if class_id:
            try:
                current_class = TreeNode.objects.get(pk=int(class_id))
                self.fields['curriculum_subject'].queryset = TreeNode.objects.filter(
                    parent=current_class,
                    node_type='subject'
                ).order_by('order', 'name')
            except (ValueError, TreeNode.DoesNotExist):
                pass

        # C. Populate Chapter Field (Filter by Subject)
        current_subject = None
        subject_id = self.data.get('curriculum_subject') if 'curriculum_subject' in self.data else (self.instance.curriculum_subject.pk if self.instance.pk and self.instance.curriculum_subject else None)
        
        if subject_id:
            try:
                current_subject = TreeNode.objects.get(pk=int(subject_id))
                self.fields['curriculum_chapter'].queryset = TreeNode.objects.filter(
                    parent=current_subject,
                    node_type='chapter'
                ).order_by('order', 'name')
            except (ValueError, TreeNode.DoesNotExist):
                pass
     


class MCQOptionForm(forms.ModelForm):
    class Meta:
        model = MCQOption
        fields = ['option_text', 'is_correct', 'order']
        widgets = {
            'option_text': forms.TextInput(attrs=TAILWIND_INPUT_CLASSES),
            'is_correct': forms.CheckboxInput(attrs=TAILWIND_CHECKBOX_CLASSES),
            'order': forms.NumberInput(attrs={**TAILWIND_INPUT_CLASSES, 'min': 1}),
        }

MCQOptionFormSet = inlineformset_factory(
    Question, MCQOption, form=MCQOptionForm, extra=4, can_delete=True
)

class MCQOptionOrgForm(forms.ModelForm):
    class Meta:
        model = MCQOptionOrg
        fields = ['option_text', 'is_correct', 'order']
        widgets = {
            'option_text': forms.TextInput(attrs=TAILWIND_INPUT_CLASSES),
            'is_correct': forms.CheckboxInput(attrs=TAILWIND_CHECKBOX_CLASSES),
            'order': forms.NumberInput(attrs={**TAILWIND_INPUT_CLASSES, 'min': 1}),
        }

MCQOptionOrgFormSet = inlineformset_factory(
    OrgQuestion, MCQOptionOrg, form=MCQOptionForm, extra=4, can_delete=True
)


class FillBlankAnswerForm(forms.ModelForm):
    class Meta:
        model = FillBlankAnswer
        fields = ['correct_answer', 'is_case_sensitive']
        widgets = {
            'correct_answer': forms.TextInput(attrs=TAILWIND_INPUT_CLASSES),
            'is_case_sensitive': forms.CheckboxInput(attrs=TAILWIND_CHECKBOX_CLASSES),
        }

FillBlankAnswerFormSet = inlineformset_factory(
    Question, FillBlankAnswer, form=FillBlankAnswerForm, extra=1, can_delete=True
)

class FillBlankAnswerOrgForm(forms.ModelForm):
    """Form for the Org (Draft) FillBlankAnswerOrg model."""
    class Meta:
        model = FillBlankAnswerOrg
        fields = ['correct_answer', 'is_case_sensitive']
        widgets = {
            'correct_answer': forms.TextInput(attrs=TAILWIND_INPUT_CLASSES),
            'is_case_sensitive': forms.CheckboxInput(attrs=TAILWIND_CHECKBOX_CLASSES),
        }

FillBlankAnswerOrgFormSet = inlineformset_factory(
    OrgQuestion, FillBlankAnswerOrg, form=FillBlankAnswerOrgForm, extra=1, can_delete=True
)


class ShortAnswerForm(forms.ModelForm):
    class Meta:
        model = ShortAnswer
        fields = ['sample_answer', 'max_words']
        widgets = {
            'sample_answer': forms.Textarea(attrs={**TAILWIND_INPUT_CLASSES, 'rows': 3}),
            'max_words': forms.NumberInput(attrs={**TAILWIND_INPUT_CLASSES, 'min': 1}),
        }
class ShortAnswerOrgForm(forms.ModelForm):
    class Meta:
        model = ShortAnswerOrg
        fields = ['sample_answer', 'max_words']
        widgets = {
            'sample_answer': forms.Textarea(attrs={**TAILWIND_INPUT_CLASSES, 'rows': 3}),
            'max_words': forms.NumberInput(attrs={**TAILWIND_INPUT_CLASSES, 'min': 1}),
        }

class MatchPairForm(forms.ModelForm):
    class Meta:
        model = MatchPair
        fields = ['left_item', 'right_item', 'order']
        widgets = {
            'left_item': forms.TextInput(attrs=TAILWIND_INPUT_CLASSES),
            'right_item': forms.TextInput(attrs=TAILWIND_INPUT_CLASSES),
            'order': forms.NumberInput(attrs={**TAILWIND_INPUT_CLASSES, 'min': 1}),
        }

MatchPairFormSet = inlineformset_factory(
    Question, MatchPair, form=MatchPairForm, extra=3, can_delete=True
)

class MatchPairOrgForm(forms.ModelForm):
    class Meta:
        model = MatchPairOrg
        fields = ['left_item', 'right_item', 'order']
        widgets = {
            'left_item': forms.TextInput(attrs=TAILWIND_INPUT_CLASSES),
            'right_item': forms.TextInput(attrs=TAILWIND_INPUT_CLASSES),
            'order': forms.NumberInput(attrs={**TAILWIND_INPUT_CLASSES, 'min': 1}),
        }
MatchPairOrgFormSet = inlineformset_factory(
    OrgQuestion, MatchPairOrg, form=MatchPairOrgForm, extra=3, can_delete=True
)

class TrueFalseAnswerForm(forms.ModelForm):
    class Meta:
        model = TrueFalseAnswer
        fields = ['correct_answer', 'explanation']
        widgets = {
            'correct_answer': forms.Select(choices=[(True, 'True'), (False, 'False')], attrs=TAILWIND_INPUT_CLASSES),
            'explanation': forms.Textarea(attrs={**TAILWIND_INPUT_CLASSES, 'rows': 2}),
        }

class TrueFalseAnswerOrgForm(forms.ModelForm):
    class Meta:
        model = TrueFalseAnswerOrg
        fields = ['correct_answer', 'explanation']
        widgets = {
            'correct_answer': forms.Select(choices=[(True, 'True'), (False, 'False')], attrs=TAILWIND_INPUT_CLASSES),
            'explanation': forms.Textarea(attrs={**TAILWIND_INPUT_CLASSES, 'rows': 2}),
        }


class QuestionPaperForm(forms.ModelForm):
    # This hidden field captures the JSON string of all selected Unit/Chapter/Section IDs (the M2M data)
    # from the JavaScript interface, allowing the form to handle multiple selections for curriculum_chapters.
    m2m_selection_data = forms.CharField(required=False, widget=forms.HiddenInput())
    
    class Meta:
        model = QuestionPaper
        # Note: 'curriculum_chapters' is explicitly excluded from 'fields' here because it's handled 
        # manually in the save() method using 'm2m_selection_data'.
        fields = ['title', 'curriculum_subject', 'pattern', 'duration_minutes', 'instructions', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            # 'curriculum_subject' is the root select.
            'curriculum_subject': forms.Select(attrs={'class': 'form-select'}),
            'pattern': forms.Select(attrs={'class': 'form-select'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Enforce the Model's Constraint: Filter root subject choices to only show 'subject' nodes.
        self.fields['curriculum_subject'].queryset = TreeNode.objects.filter(parent__isnull=True ).order_by('name')
        
        # Add ID for the root select for JavaScript cascade handling.
        self.fields['curriculum_subject'].widget.attrs.update({'id': 'root-node-paper'})
        
        # If editing an existing paper, populate the hidden M2M data so JavaScript can pre-check the boxes.
        if self.instance.pk:
            selected_ids = list(self.instance.curriculum_chapters.values_list('id', flat=True))
            # Serialize the list of IDs into a JSON string for the hidden input.
            self.initial['m2m_selection_data'] = json.dumps(selected_ids)


    def save(self, commit=True):
        # 1. Save the primary instance fields (including the curriculum_subject FK)
        instance = super().save(commit=False)
        
        if commit:
            # We must save the instance first before setting ManyToMany fields
            instance.save()
            
            # 2. Handle the multi-select M2M nodes (curriculum_chapters)
            m2m_data = self.cleaned_data.get('m2m_selection_data')
            
            if m2m_data:
                try:
                    # Deserialize the JSON string back into a Python list of IDs.
                    selected_ids = json.loads(m2m_data)
                    
                    # Fetch and set the selected nodes to the ManyToMany field.
                    # This replaces any existing chapters with the newly selected ones.
                    valid_nodes = TreeNode.objects.filter(id__in=selected_ids)
                    instance.curriculum_chapters.set(valid_nodes)
                except json.JSONDecodeError:
                    # Log error if the JS data is corrupt
                    print("ERROR: Could not decode JSON data for M2M selection.")
                    pass
            # If no data is selected, calling .set([]) clears the M2M relationship.
            elif self.instance.pk:
                instance.curriculum_chapters.clear()

        return instance


class QuestionSearchForm(forms.Form):
    
    # Define the base styling classes for reuse
    SELECT_WIDGET_CLASSES = (
        'form-select w-full p-2 border border-gray-300 dark:border-gray-600 '
        'rounded-lg focus:ring-blue-500 focus:border-blue-500 '
        'bg-white dark:bg-gray-800 text-gray-900 dark:text-white '
        'transition-all duration-200 shadow-sm'
    )
    INPUT_WIDGET_CLASSES = (
        'form-control w-full p-2 border border-gray-300 dark:border-gray-600 '
        'rounded-lg focus:ring-blue-500 focus:border-blue-500 '
        'bg-white dark:bg-gray-800 text-gray-900 dark:text-white '
        'transition-all duration-200 shadow-sm'
    )

    board = forms.ModelChoiceField(
        queryset=TreeNode.objects.filter(node_type__in=['board', 'competitive']).order_by('name'),
        required=False,
        label="Board",
        empty_label="All Boards",
        # Use the base CSS class for initial definition
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_board'})
    )

    curriculum_subject = forms.ModelChoiceField(
        queryset=TreeNode.objects.none(), 
        required=False,
        label="Subject",
        empty_label="All Subjects",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_curriculum_subject'})
    )
    
    curriculum_chapter = forms.ModelChoiceField(
        queryset=TreeNode.objects.none(), 
        required=False,
        label="Chapter",
        empty_label="All Chapters",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_curriculum_chapter'})
    )
    
    question_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Question.QUESTION_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    difficulty = forms.ChoiceField(
        choices=[('', 'All Difficulties')] + Question.DIFFICULTY_LEVELS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search question text...'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get the submitted data from the GET request
        data = self.data

        # 1. Populate Subject based on submitted Board filter (Cascading Logic)
        board_id = data.get('board')
        if board_id:
            try:
                self.fields['curriculum_subject'].queryset = TreeNode.objects.filter(
                    parent_id=board_id,
                    node_type__in=['subject', 'class'] 
                ).order_by('name')
            except ValueError:
                pass

        # 2. Populate Chapter based on submitted Subject filter (Cascading Logic)
        subject_id = data.get('curriculum_subject')
        if subject_id:
            try:
                self.fields['curriculum_chapter'].queryset = TreeNode.objects.filter(
                    parent_id=subject_id,
                    node_type='chapter'
                ).order_by('order', 'name')
            except ValueError:
                pass
        
        # ====================================================================
        # START: APPLYING THE THEME CSS
        # ====================================================================
        
        for name, field in self.fields.items():
            # Apply the appropriate full set of classes to each widget
            if isinstance(field.widget, forms.Select):
                # Ensure the 'form-select' is included, then add Tailwind styling
                field.widget.attrs.update({'class': self.SELECT_WIDGET_CLASSES})
            
            elif isinstance(field.widget, forms.TextInput):
                # Ensure the 'form-control' is included, then add Tailwind styling
                field.widget.attrs.update({'class': self.INPUT_WIDGET_CLASSES})