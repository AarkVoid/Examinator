# education/models.py
from django.db import models
from django.conf import settings


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Board(TimeStampedModel):
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='unique_board'
            )
        ]

    def __str__(self):
        return self.name

class StudentClass(TimeStampedModel):
    name = models.CharField(max_length=50)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='classes')

    def __str__(self):
        return f"{self.name} ({self.board.name})"
    
# ================
# NEW: Division Model
# ================
class Division(TimeStampedModel):
    name = models.CharField(max_length=50, help_text="e.g., 'A', 'B', 'Alpha'")
    student_class = models.ForeignKey(
        StudentClass,
        on_delete=models.CASCADE,
        related_name='divisions',
        help_text="The class this division belongs to (e.g., Class 10)"
    )

    def __str__(self):
        return f"{self.student_class.name} - {self.name} ({self.student_class.board.name})"

    class Meta:
        # Ensure division name is unique within a specific student class
        unique_together = ('name', 'student_class')
        verbose_name = "Division"
        verbose_name_plural = "Divisions"
        ordering = ['student_class__name', 'name'] #

class Subject(TimeStampedModel):
    name = models.CharField(max_length=100)
    student_class = models.ForeignKey(StudentClass, on_delete=models.CASCADE, related_name='subjects')

    def __str__(self):
        return f"{self.name} - {self.student_class.name}"

class Chapter(TimeStampedModel):
    name = models.CharField(max_length=100)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='chapters')

    def __str__(self):
        return f"{self.name} ({self.subject.name})"
    

class Lesson(TimeStampedModel):
    """
    Model to store details about a specific lesson or lecture within a chapter.
    """
    title = models.CharField(max_length=200, help_text="Title of the lesson")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='lessons')
    content = models.TextField(blank=True, help_text="Main content or text for the lesson (e.g., lecture notes, explanation)")
    video_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Optional URL to a video lecture (e.g., YouTube, Vimeo)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes or supplementary information for the lesson"
    )
    # --- IMPORTANT: ADD THESE TWO FIELDS ---
    is_published = models.BooleanField(default=False, help_text="Designates if the lesson is visible to students.")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_lessons',
        help_text="The user (teacher/admin) who created this lesson."
    )
    # ---------------------------------------

    def __str__(self):
        return f"{self.title} ({self.chapter.name})"

    class Meta:
        # Ensure lesson title is unique within a chapter
        unique_together = ('title', 'chapter')
        # Order lessons by chapter title, then lesson title
        ordering = ['chapter__name', 'title']
        verbose_name = "Lesson"
        verbose_name_plural = "Lessons"
