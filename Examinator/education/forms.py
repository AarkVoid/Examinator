from django import forms
from .models import Board, StudentClass, Subject, Chapter, Lesson,Division

class BoardForm(forms.ModelForm):
    class Meta:
        model = Board
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter board name'}),
            'location': forms.Select(attrs={'class': 'form-select'})
        }

class StudentClassForm(forms.ModelForm):
    class Meta:
        model = StudentClass
        fields = ['name', 'board']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter class name'}),
            'board': forms.Select(attrs={'class': 'form-select'})
        }

# NEW: DivisionForm
class DivisionForm(forms.ModelForm):
    class Meta:
        model = Division
        fields = ['name', 'student_class']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter division name (e.g., A, B)'}),
            'student_class': forms.Select(attrs={'class': 'form-select'})
        }

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'student_class']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter subject name'}),
            'student_class': forms.Select(attrs={'class': 'form-select'})
        }

class ChapterForm(forms.ModelForm):
    class Meta:
        model = Chapter
        fields = ['name', 'subject']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Enter chapter name'}),
            'subject': forms.Select(attrs={'class': 'form-select'})
        }



class LessonForm(forms.ModelForm):
    board = forms.ModelChoiceField(
        queryset=Board.objects.all(),
        required=False,
        label='Board',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_board'})
    )
    student_class = forms.ModelChoiceField(
        queryset=StudentClass.objects.none(),
        required=False,
        label='Class',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_student_class'})
    )
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        required=False,
        label='Subject',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_subject'})
    )

    class Meta:
        model = Lesson
        fields = ['board', 'student_class', 'subject', 'chapter', 'title', 'content', 'video_url', 'notes', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Lesson Title'}),
            'chapter': forms.Select(attrs={'class': 'form-select', 'id': 'id_chapter'}),
            'content': forms.Textarea(attrs={'class': 'form-input', 'rows': 8, 'placeholder': 'Main lecture content...'}),
            'video_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'Optional: YouTube or Vimeo URL'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Additional notes...'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['chapter'].queryset = Chapter.objects.none()

        if 'subject' in self.data:
            try:
                subject_id = int(self.data.get('subject'))
                self.fields['chapter'].queryset = Chapter.objects.filter(subject_id=subject_id).order_by('name')
            except (ValueError, TypeError):
                pass  # Invalid input; fallback to empty queryset
        elif self.instance.pk and self.instance.chapter:
            self.fields['chapter'].queryset = Chapter.objects.filter(subject=self.instance.chapter.subject)

        # Optional: Filter student_class and subject if instance exists
        if 'board' in self.data:
            try:
                board_id = int(self.data.get('board'))
                self.fields['student_class'].queryset = StudentClass.objects.filter(board_id=board_id)
            except:
                pass
        if 'student_class' in self.data:
            try:
                class_id = int(self.data.get('student_class'))
                self.fields['subject'].queryset = Subject.objects.filter(student_class_id=class_id)
            except:
                pass
        