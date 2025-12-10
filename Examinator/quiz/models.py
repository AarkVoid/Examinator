from django.db import models
from django.contrib.auth import get_user_model
from curritree.models import TreeNode
from accounts.models import TimeStampedModel,User
import json
import uuid

User = get_user_model()

class OrgQuestion(TimeStampedModel):
    question_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    QUESTION_TYPES = [
        ('mcq', 'Multiple Choice'),
        ('fill_blank', 'Fill in the Blank'),
        ('short_answer', 'Short Answer'),
        ('match', 'Match the Following'),
        ('true_false', 'True/False'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)

    question_image = models.ImageField(
        upload_to='questions/images/', 
        null=True, 
        blank=True,
        help_text="Optional image to accompany the question text."
    )
    
    curriculum_board = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='board_Org_questions',
        limit_choices_to={'node_type': 'board'},
        default=None, null=True, blank=True
    )

    curriculum_class = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='class_Org_questions',
        limit_choices_to={'node_type': 'class'},
        default=None, null=True, blank=True
    )
    
    curriculum_subject = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='Org_questions',
        limit_choices_to={'node_type': 'subject'}, # Hint for admin/forms
        default=None, null=True, blank=True
    )
    curriculum_chapter = models.ForeignKey(
        TreeNode, 
        on_delete=models.SET_NULL, 
        blank=True,
        related_name='chapter_Org_questions',
        limit_choices_to={'node_type': 'chapter'}, # Hint for admin/forms
        default=None, null=True,
    )
    question_text = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS, default='medium')
    marks = models.PositiveIntegerField(default=1)
    organization = models.ForeignKey('saas.OrganizationProfile', on_delete=models.CASCADE, null=True, blank=True)
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    paere_count = models.BigIntegerField(default=0,blank=True,null=True)
    
    class Meta:
        ordering = ['-created']
        verbose_name = 'Client Question '
        verbose_name_plural = 'Client Question '
    
    def __str__(self):
        return f"{self.get_question_type_display()}: {self.question_text[:50]}..."
    

class Question(TimeStampedModel):
    question_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    QUESTION_TYPES = [
        ('mcq', 'Multiple Choice'),
        ('fill_blank', 'Fill in the Blank'),
        ('short_answer', 'Short Answer'),
        ('match', 'Match the Following'),
        ('true_false', 'True/False'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)

    question_image = models.ImageField(
        upload_to='questions/images/', 
        null=True, 
        blank=True,
        help_text="Optional image to accompany the question text."
    )
    
    curriculum_board = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='board_questions',
        limit_choices_to={'node_type': 'board'},
        default=None, null=True, blank=True
    )

    curriculum_class = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='class_questions',
        limit_choices_to={'node_type': 'class'},
        default=None, null=True, blank=True
    )
    
    curriculum_subject = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='questions',
        limit_choices_to={'node_type': 'subject'}, # Hint for admin/forms
        default=None, null=True, blank=True
    )
    curriculum_chapter = models.ForeignKey(
        TreeNode, 
        on_delete=models.SET_NULL, 
        blank=True,
        related_name='chapter_questions',
        limit_choices_to={'node_type': 'chapter'}, # Hint for admin/forms
        default=None, null=True,
    )
    question_text = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS, default='medium')
    marks = models.PositiveIntegerField(default=1)
    organization = models.ForeignKey('saas.OrganizationProfile', on_delete=models.CASCADE, null=True, blank=True)
    is_published = models.BooleanField(default=False)
    orignal_qid = models.ForeignKey(OrgQuestion, on_delete=models.CASCADE, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    paere_count = models.BigIntegerField(default=0,blank=True,null=True)
    is_Textual =  models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created']
        verbose_name = 'Public Question '
        verbose_name_plural = 'Public Question '
    
    def __str__(self):
        return f"{self.get_question_type_display()}: {self.question_text[:50]}..."
    




class MCQOptionOrg(models.Model): # Renamed: MCQOptionOrg
    question = models.ForeignKey(OrgQuestion, on_delete=models.CASCADE, related_name='mcq_options_org') 
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Client MCQ Question Option'
        verbose_name_plural = 'Client MCQ Question Options'

class FillBlankAnswerOrg(models.Model): # Renamed: FillBlankAnswerOrg
    question = models.ForeignKey(OrgQuestion, on_delete=models.CASCADE, related_name='fill_blank_answers_org')
    correct_answer = models.CharField(max_length=200)
    is_case_sensitive = models.BooleanField(default=False)
    class Meta:
        verbose_name = 'Client FIB Question Option'
        verbose_name_plural = 'Client FIB Question Options'

class ShortAnswerOrg(models.Model): # Renamed: ShortAnswerOrg
    question = models.OneToOneField(OrgQuestion, on_delete=models.CASCADE, related_name='short_answer_org')
    sample_answer = models.TextField()
    max_words = models.PositiveIntegerField(default=50)
    class Meta:
        verbose_name = 'Client Short Answer Question Option'
        verbose_name_plural = 'Client Short Answer Question Options'

class MatchPairOrg(models.Model): # Renamed: MatchPairOrg
    question = models.ForeignKey(OrgQuestion, on_delete=models.CASCADE, related_name='match_pairs_org')
    left_item = models.CharField(max_length=200)
    right_item = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Client Match Question Option'
        verbose_name_plural = 'Client Match Question Options'

class TrueFalseAnswerOrg(models.Model): # Renamed: TrueFalseAnswerOrg
    question = models.OneToOneField(OrgQuestion, on_delete=models.CASCADE, related_name='true_false_answer_org')
    correct_answer = models.BooleanField()
    explanation = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Client True or False Question Option'
        verbose_name_plural = 'Client True or False Question Options'



class MCQOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='mcq_options')
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'MCQ Question Option'
        verbose_name_plural = 'MCQ Question Options'

class FillBlankAnswer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='fill_blank_answers')
    correct_answer = models.CharField(max_length=200)
    is_case_sensitive = models.BooleanField(default=False)
    class Meta:
        verbose_name = 'FIB Question Option'
        verbose_name_plural = 'FIB Question Options'

class ShortAnswer(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='short_answer')
    sample_answer = models.TextField()
    max_words = models.PositiveIntegerField(default=50)
    class Meta:
        verbose_name = ' Short Answer Question Option'
        verbose_name_plural = ' Short Answer Question Options'

class MatchPair(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='match_pairs')
    left_item = models.CharField(max_length=200)
    right_item = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Match Question Option'
        verbose_name_plural = 'Match Question Options'

class TrueFalseAnswer(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='true_false_answer')
    correct_answer = models.BooleanField()
    explanation = models.TextField(blank=True)

    class Meta:
        verbose_name = 'True or False Question Option'
        verbose_name_plural = 'True or False Question Options'


class QuestionPaper(TimeStampedModel):

    paper_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    
    PAPER_PATTERNS = [
        ('standard', 'Standard Pattern'),
        ('section_wise', 'Section-wise Pattern'),
        ('difficulty_wise', 'Difficulty-wise Pattern'),
        ('custom', 'Custom Pattern'),
    ]
    
    title = models.CharField(max_length=200)
    
    # Point 1: Organization Field for filtering access
    organization = models.ForeignKey('saas.OrganizationProfile', on_delete=models.CASCADE, related_name='papers', null=True, blank=True)
    
    # Point 3: curriculum_subject is the root (must be a 'subject' node)
    curriculum_subject = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='root_papers',
        # Only allow 'subject' nodes to be selected as the primary FK
        limit_choices_to={'node_type': 'subject'} 
    )
    
    # Point 4: Multi-select Chapters/Units/Sections
    # This M2M field will store the IDs of all selected Chapter/Unit/Section nodes.
    curriculum_chapters = models.ManyToManyField(
        TreeNode, 
        related_name='paper_chapters',
        blank=True,
        help_text="The specific units, chapters, or sections covered by this paper (multiple selection enabled)."
    )
    
    pattern = models.CharField(max_length=20, choices=PAPER_PATTERNS, default='standard')
    total_marks = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=60)
    instructions = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)
    marks_distribution = models.JSONField(default={},blank=True,null=True)
    
    class Meta:
        ordering = ['-created']
        verbose_name = 'Question Paper'
        verbose_name_plural = 'Question Paper'
    
    def __str__(self):
        return self.title
    
    def calculate_total_marks(self):
        return sum(pq.marks for pq in self.paper_questions.all()) + sum(pq.marks for pq in self.paper_orgquestions.all())

class PaperQuestion(models.Model):
    paper = models.ForeignKey(QuestionPaper, on_delete=models.CASCADE, related_name='paper_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    marks = models.PositiveIntegerField()
    section = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['paper', 'question']
        verbose_name = 'Question In Paper'
        verbose_name_plural = 'Question In Paper'


class PaperOrgQuestion(models.Model):
    paper = models.ForeignKey(QuestionPaper, on_delete=models.CASCADE, related_name='paper_orgquestions')
    question = models.ForeignKey(OrgQuestion, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    marks = models.PositiveIntegerField()
    section = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['paper', 'question']
        verbose_name = 'Client Question In Paper'
        verbose_name_plural = 'Client Question In Paper'

class QuestionPaperAttempt(models.Model):
    paper = models.ForeignKey(QuestionPaper, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    answers = models.JSONField(default=dict)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    class Meta:
        unique_together = ['paper', 'student']
        verbose_name = 'Attempts on Question Paper'
        verbose_name_plural = 'Attempts on Question Paper'


class QuestionUploadLog(TimeStampedModel):
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    total_questions = models.PositiveIntegerField(default=0)
    file_path = models.CharField(max_length=500)
    success_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    error_details = models.JSONField(blank=True, null=True)  # Use JSONField for structured data
    
    def __str__(self):
        return f"Upload by {self.uploaded_by.username} on {self.created.strftime('%Y-%m-%d %H:%M:%S')}"
    
    class Meta:
        verbose_name = 'Bulk Upload Of Question'
        verbose_name_plural = 'Bulk Upload Of Question'