from django.contrib import admin

# Register your models here.
from .models import Board, StudentClass, Subject, Chapter,Lesson

admin.site.register(Board)
admin.site.register(StudentClass)
admin.site.register(Subject)


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    # Display the chapter name and its direct subject link
    list_display = ('name', 'subject', 'created', 'modified')
    # Filter by the subject directly
    list_filter = ('subject',)
    search_fields = ('name', 'subject__name')# Useful if you have many boards/classes

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    # Display main lesson details and its direct chapter link
    list_display = (
        'title',
        'chapter',
        'is_published',
        'created_by',
        'created',
        'modified'
    )
    # Filter directly by published status, creator, and the chapter itself.
    # You can also filter by chapter's subject for slightly more granularity.
    list_filter = (
        'is_published',
        'created_by__role', # Filter by the role of the user who created it
        'chapter',          # Filter by specific chapter
        'chapter__subject', # Filter by subject that the chapter belongs to
    )
    search_fields = ('title', 'content', 'notes', 'chapter__name', 'created_by__username')
    raw_id_fields = ('chapter', 'created_by',)
    actions = ['make_published', 'make_draft']
    fieldsets = (
        (None, {
            'fields': ('title', 'chapter', 'is_published')
        }),
        ('Content', {
            'fields': ('content', 'video_url', 'notes'),
            'description': 'Main lesson materials.'
        }),
        ('Metadata', {
            'fields': ('created_by',),
            'classes': ('collapse',),
        })
    )
    readonly_fields = ('created_by',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def make_published(self, request, queryset):
        queryset.update(is_published=True)
    make_published.short_description = "Mark selected lessons as published"

    def make_draft(self, request, queryset):
        queryset.update(is_published=False)
    make_draft.short_description = "Mark selected lessons as draft"