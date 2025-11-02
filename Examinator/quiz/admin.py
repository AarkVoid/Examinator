from django.contrib import admin
from .models import Question, QuestionPaper,PaperQuestion, MCQOption, FillBlankAnswer, MatchPair, ShortAnswer, TrueFalseAnswer
from curritree.models import TreeNode 

# --- Inline Definitions ---

class MCQOptionInline(admin.TabularInline):
    model = MCQOption
    extra = 1

class FillBlankAnswerInline(admin.StackedInline):
    model = FillBlankAnswer
    max_num = 1 # Only one answer per Fill-in-the-Blank question

class MatchPairInline(admin.TabularInline):
    model = MatchPair
    extra = 1
    
class ShortAnswerInline(admin.StackedInline):
    model = ShortAnswer
    max_num = 1
    
class TrueFalseAnswerInline(admin.StackedInline):
    model = TrueFalseAnswer
    max_num = 1

class PaperQuestionInline(admin.TabularInline):
    model = PaperQuestion
    extra = 1
    # Display the related Question text directly
    autocomplete_fields = ['question'] 
    fields = ('question', 'order', 'marks', 'section')
    

# --- Admin Classes ---

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    # 🛑 UPDATE: Use 'curriculum_subject' instead of 'subject'
    # Use 'get_subject_name' for cleaner display if you want the name, otherwise 'curriculum_subject'
    list_display = [
        'question_text', 
        'question_type', 
        'curriculum_board',
        'curriculum_subject', # Using the FK field directly
        'curriculum_chapter', # Using the FK field directly'
        'difficulty', 
        'marks', 
        'created_by'
    ]
    
    # 🛑 UPDATE: Use 'curriculum_subject' in filters
    list_filter = ['question_type', 'difficulty', 'curriculum_subject', 'created']
    search_fields = ['question_text']
    
    # 🛑 Autocomplete fields for TreeNode lookups
    autocomplete_fields = ['curriculum_subject', 'curriculum_chapter']
    
    # Group fields for better editing experience
    fieldsets = (
        (None, {'fields': ('question_text', 'question_type', 'difficulty', 'marks','organization')}),
        ('Curriculum Links', {'fields': ('curriculum_subject', 'curriculum_chapter','curriculum_board')}),
        ('Metadata', {'fields': ('created_by',)}),
    )
    
    def get_inlines(self, request, obj=None):
        if obj is None:
            return [] # Inlines are not available until the question is saved
            
        if obj.question_type == 'mcq':
            return [MCQOptionInline]
        elif obj.question_type == 'fill_blank':
            return [FillBlankAnswerInline]
        elif obj.question_type == 'short_answer':
            return [ShortAnswerInline]
        elif obj.question_type == 'match':
            return [MatchPairInline]
        elif obj.question_type == 'true_false':
            return [TrueFalseAnswerInline]
        return []


@admin.register(QuestionPaper)
class QuestionPaperAdmin(admin.ModelAdmin):
    # 🛑 UPDATE: Use 'curriculum_subject' instead of 'subject'
    list_display = [
        'title', 
        'curriculum_subject', # Using the FK field directly
        'total_marks', 
        'duration_minutes', 
        'is_published', 
        'created_by'
    ]
    
    # 🛑 UPDATE: Use 'curriculum_subject' in filters
    list_filter = ['curriculum_subject', 'pattern', 'is_published', 'created']
    search_fields = ['title']
    
    # 🛑 Autocomplete fields for TreeNode lookups
    autocomplete_fields = ['curriculum_subject']
    
    inlines = [PaperQuestionInline]