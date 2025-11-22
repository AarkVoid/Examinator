from django.db import models
from django.contrib.auth import get_user_model
from curritree.models import TreeNode
from accounts.models import TimeStampedModel,User
import json


User = get_user_model()

class Question(TimeStampedModel):
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
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.get_question_type_display()}: {self.question_text[:50]}..."

class MCQOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='mcq_options')
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['order']

class FillBlankAnswer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='fill_blank_answers')
    correct_answer = models.CharField(max_length=200)
    is_case_sensitive = models.BooleanField(default=False)

class ShortAnswer(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='short_answer')
    sample_answer = models.TextField()
    max_words = models.PositiveIntegerField(default=50)

class MatchPair(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='match_pairs')
    left_item = models.CharField(max_length=200)
    right_item = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['order']

class TrueFalseAnswer(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='true_false_answer')
    correct_answer = models.BooleanField()
    explanation = models.TextField(blank=True)

class QuestionPaper(TimeStampedModel):
    
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
    
    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        return self.title
    
    def calculate_total_marks(self):
        return sum(pq.marks for pq in self.paper_questions.all())

class PaperQuestion(models.Model):
    paper = models.ForeignKey(QuestionPaper, on_delete=models.CASCADE, related_name='paper_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    marks = models.PositiveIntegerField()
    section = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['paper', 'question']

class QuestionPaperAttempt(models.Model):
    paper = models.ForeignKey(QuestionPaper, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    answers = models.JSONField(default=dict)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    class Meta:
        unique_together = ['paper', 'student']


class QuestionUploadLog(TimeStampedModel):
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    total_questions = models.PositiveIntegerField(default=0)
    file_path = models.CharField(max_length=500)
    success_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    error_details = models.JSONField(blank=True, null=True)  # Use JSONField for structured data
    
    def __str__(self):
        return f"Upload by {self.uploaded_by.username} on {self.created.strftime('%Y-%m-%d %H:%M:%S')}"