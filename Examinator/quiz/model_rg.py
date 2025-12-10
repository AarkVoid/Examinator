from django.db import models
from django.contrib.auth import get_user_model
from curritree.models import TreeNode
from accounts.models import TimeStampedModel,User
import json
import uuid

User = get_user_model()

QUESTION_TYPES_LIST = [
        ('mcq', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('fill_blank', 'Fill in the Blank'),
        ('match', 'Match the Following (Simple)'),
        ('short_answer', 'Short Answer (SAQ)'),
        ('essay', 'Long Answer/Essay (LAQ)'),
        ('assertion_reason', 'Assertion-Reason'),
        ('integer_type', 'Numerical/Integer'),
        ('ordering', 'Sequencing/Ordering'),
        ('matrix_match', 'Matrix Match'),
    ]

DIFFICULTY_LEVELS_LIST = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]


class Passage(TimeStampedModel):
    """
    Stores the main text or stimulus for a set of Passage Based Questions.
    This model is used for long textual passages, case studies, or complex diagrams 
    that drive multiple subsequent questions.
    """
    passage_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    title = models.CharField(max_length=200, help_text="A short title or identifier for the passage/stimulus.")
    
    # The main textual content of the passage (e.g., a case study or historical text)
    passage_text = models.TextField()
    
    # Optional image or diagram associated with the passage itself
    passage_image = models.ImageField(
        upload_to='passages/images/', 
        null=True, 
        blank=True,
        # UPDATED: Explicitly mentions diagram/image as the main stimulus
        help_text="The main diagram, graph, or image that serves as the stimulus for linked questions."
    )
    
    # Linking the passage to the curriculum
    curriculum_board = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='board_passages',
        limit_choices_to={'node_type': 'board'},
        default=None, null=True, blank=True
    )

    curriculum_class = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='class_passages',
        limit_choices_to={'node_type': 'class'},
        default=None, null=True, blank=True
    )
    
    curriculum_subject = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='subject_passages',
        limit_choices_to={'node_type': 'subject'},
        default=None, null=True, blank=True
    )
    
    organization = models.ForeignKey(
        'saas.OrganizationProfile', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Organization that owns this private passage."
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False, help_text="If true, available to all users/organizations.")
    
    class Meta:
        verbose_name = 'Reading Passage/Stimulus (Text or Diagram)'
        verbose_name_plural = 'Reading Passages/Stimuli (Text or Diagram)'
    
    def __str__(self):
        return f"{self.title} ({self.passage_text[:50]}...)"

class OrgQuestion(TimeStampedModel):
    question_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    QUESTION_TYPES = QUESTION_TYPES_LIST
    
    DIFFICULTY_LEVELS = DIFFICULTY_LEVELS_LIST
    
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
    
    class Meta:
        ordering = ['-created']
        verbose_name = 'Client Question '
        verbose_name_plural = 'Client Question '
    
    def __str__(self):
        return f"{self.question_type()}: {self.question_text[:50]}..."
    

class Question(TimeStampedModel):
    question_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    QUESTION_TYPES = QUESTION_TYPES_LIST
    
    DIFFICULTY_LEVELS = DIFFICULTY_LEVELS_LIST
    
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

    question_subtype = models.ForeignKey(
        'QuestionSubTypes', 
        on_delete=models.SET_NULL, 
        related_name='public_questions_with_subtype', 
        null=True, 
        blank=True,
        help_text="Custom subtype (e.g., 'Case Study Based', 'Diagram Q') for this question."
    )


    question_text = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS, default='medium')
    marks = models.PositiveIntegerField(default=1)
    organization = models.ForeignKey('saas.OrganizationProfile', on_delete=models.CASCADE, null=True, blank=True)
    is_published = models.BooleanField(default=False)
    orignal_qid = models.ForeignKey(OrgQuestion, on_delete=models.CASCADE, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_Textual =  models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created']
        verbose_name = 'Public Question '
        verbose_name_plural = 'Public Question '
    
    def __str__(self):
        return f"{self.question_type()}: {self.question_text[:50]}..."
    

class QuestionSubTypes(TimeStampedModel):
    """
    Allows organizations to define custom, curriculum-specific question sub-types 
    (e.g., 'Assertion/Reason', 'Diagram-based MCQ') that relate to a base question type.
    Includes a list of marks that questions of this subtype are typically assigned.
    """
    curriculum_board = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='subtype_boards',
        limit_choices_to={'node_type': 'board'},
        default=None, null=True, blank=True,
        help_text="Board scope for this custom subtype (optional)."
    )

    curriculum_class = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='subtype_classes',
        limit_choices_to={'node_type': 'class'},
        default=None, null=True, blank=True,
        help_text="Class scope for this custom subtype (optional)."
    )
    
    curriculum_subject = models.ForeignKey(
        TreeNode, 
        on_delete=models.CASCADE, 
        related_name='subtype_subjects',
        limit_choices_to={'node_type': 'subject'},
        default=None, null=True, blank=True,
        help_text="Subject scope for this custom subtype (optional)."
    )

    subtype_name = models.CharField(
        max_length=500,
        help_text="The custom name (e.g., 'Case Study MCQ', 'Image Identification')."
    )
    
    # NEW FIELD ADDED: allowed_marks
    allowed_marks = models.CharField(
        max_length=1000,
        default='1, 2, 3, 4, 5',
        help_text="Comma-separated list of valid marks (e.g., '1, 2.5, 5') for questions of this subtype. This enables filtering question subtypes when a user specifies the required mark for a question."
    )
    
    # Base question types defined in OrgQuestion
    BASE_QUESTION_TYPES = QUESTION_TYPES_LIST

    base_question_type = models.CharField(
        max_length=20, 
        choices=BASE_QUESTION_TYPES, 
        default='mcq', 
        help_text="The core question format this subtype uses (e.g., MCQ, Short Answer)."
    )

    organization = models.ForeignKey(
        'saas.OrganizationProfile', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    class Meta:
        verbose_name = 'Custom Question Subtype'
        verbose_name_plural = 'Custom Question Subtypes'
        unique_together = ('curriculum_board', 'curriculum_class', 'curriculum_subject', 'subtype_name', 'base_question_type')
    
    def __str__(self):
        scope = []
        if self.curriculum_board:
            scope.append(self.curriculum_board.name)
        if self.curriculum_class:
            scope.append(self.curriculum_class.name)
        if self.curriculum_subject:
            scope.append(self.curriculum_subject.name)
            
        scope_str = " / ".join(scope)
        marks_display = f"Marks: {self.allowed_marks}" if self.allowed_marks else "Marks: N/A"
        
        return f"[{self.base_question_type.upper()}] {self.subtype_name} ({marks_display}) ({scope_str if scope_str else 'Global'})"

    def get_allowed_marks(self):
        """
        Parses the comma-separated string into a list of numbers (float for flexibility).
        This is what your application logic would use for filtering.
        """
        if not self.allowed_marks:
            return []
        
        try:
            # Strip whitespace and convert each part to a float
            return [float(m.strip()) for m in self.allowed_marks.split(',')]
        except ValueError:
            # Handle cases where the input string is not clean (e.g., contains text)
            print(f"Warning: Failed to parse marks list for {self.subtype_name}. Raw data: {self.allowed_marks}")
            return []
        
        
class PassageQuestionLink(models.Model):
    """
    Links an individual question (OrgQuestion or Question) to its governing passage/stimulus.
    A single passage/diagram can be linked to multiple questions.
    """
    passage = models.ForeignKey(Passage, on_delete=models.CASCADE, related_name='linked_questions')
    
    # Allows linking to either OrgQuestion (Client's private question) or Question (Public question)
    org_question = models.ForeignKey(
        OrgQuestion, 
        on_delete=models.CASCADE, 
        related_name='passage_link', 
        null=True, 
        blank=True,
        help_text="Link to a private (Org) question."
    )
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE, 
        related_name='passage_link', 
        null=True, 
        blank=True,
        help_text="Link to a public question."
    )
    
    order = models.PositiveIntegerField(default=1, help_text="The order in which the question appears after the passage.")
    
    class Meta:
        ordering = ['passage', 'order']
        verbose_name = 'Passage Question Link'
        verbose_name_plural = 'Passage Question Links'
        constraints = [
            models.CheckConstraint(
                check=models.Q(org_question__isnull=False, question__isnull=True) | models.Q(org_question__isnull=True, question__isnull=False),
                name='must_have_one_question_type'
            )
        ]

    def __str__(self):
        q_id = self.org_question.id if self.org_question else self.question.id
        q_type = "Org" if self.org_question else "Public"
        return f"Passage '{self.passage.title}' -> Q{q_id} ({q_type})"



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


class IntegerAnswerOrg(models.Model):
    question = models.OneToOneField(OrgQuestion, on_delete=models.CASCADE, related_name='integer_answer_org')
    correct_value = models.DecimalField(max_digits=10, decimal_places=4)
    tolerance = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        default=0,
        help_text="Maximum allowed error margin for the student's answer."
    )
    class Meta:
        verbose_name = 'Client Integer/Numerical Answer'
        verbose_name_plural = 'Client Integer/Numerical Answers'

class OrderingAnswerOrg(models.Model):
    question = models.ForeignKey(OrgQuestion, on_delete=models.CASCADE, related_name='ordering_answers_org')
    item_text = models.CharField(max_length=500, help_text="Text for the item to be sequenced.")
    correct_order_index = models.PositiveIntegerField(
        help_text="The correct sequential position (e.g., 1, 2, 3...)."
    )
    class Meta:
        ordering = ['correct_order_index']
        verbose_name = 'Client Ordering Item'
        verbose_name_plural = 'Client Ordering Items'

class AssertionReasonAnswerOrg(models.Model):
    question = models.OneToOneField(OrgQuestion, on_delete=models.CASCADE, related_name='assertion_reason_answer_org')
    assertion_text = models.TextField()
    reason_text = models.TextField()
    
    CORRECT_OPTIONS = [
        ('A', 'Both Assertion and Reason are true and Reason is the correct explanation of Assertion.'),
        ('B', 'Both Assertion and Reason are true but Reason is NOT the correct explanation of Assertion.'),
        ('C', 'Assertion is true but Reason is false.'),
        ('D', 'Assertion is false but Reason is true.'),
    ]
    correct_option = models.CharField(max_length=1, choices=CORRECT_OPTIONS)

    class Meta:
        verbose_name = 'Client Assertion-Reason Answer'
        verbose_name_plural = 'Client Assertion-Reason Answers'




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

class IntegerAnswer(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='integer_answer')
    correct_value = models.DecimalField(max_digits=10, decimal_places=4)
    tolerance = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        default=0,
        help_text="Maximum allowed error margin for the student's answer."
    )
    class Meta:
        verbose_name = 'Integer/Numerical Answer'
        verbose_name_plural = 'Integer/Numerical Answers'

class OrderingAnswer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='ordering_answers')
    item_text = models.CharField(max_length=500, help_text="Text for the item to be sequenced.")
    correct_order_index = models.PositiveIntegerField(
        help_text="The correct sequential position (e.g., 1, 2, 3...)."
    )
    class Meta:
        ordering = ['correct_order_index']
        verbose_name = 'Ordering Item'
        verbose_plural = 'Ordering Items'

class AssertionReasonAnswer(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='assertion_reason_answer')
    assertion_text = models.TextField()
    reason_text = models.TextField()
    
    CORRECT_OPTIONS = [
        ('A', 'Both Assertion and Reason are true and Reason is the correct explanation of Assertion.'),
        ('B', 'Both Assertion and Reason are true but Reason is NOT the correct explanation of Assertion.'),
        ('C', 'Assertion is true but Reason is false.'),
        ('D', 'Assertion is false but Reason is true.'),
    ]
    correct_option = models.CharField(max_length=1, choices=CORRECT_OPTIONS)

    class Meta:
        verbose_name = 'Assertion-Reason Answer'
        verbose_name_plural = 'Assertion-Reason Answers'




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


