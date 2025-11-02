from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from .forms import BoardForm,StudentClassForm,SubjectForm,ChapterForm,LessonForm,DivisionForm
from .models import StudentClass, Board, Chapter, Subject, Lesson, Division
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Prefetch
from django.http import JsonResponse


# Views
@permission_required({'education.view_board','education.view_studentclass','education.view_subject','education.view_division'},raise_exception=True)
def education_dashboard(request):
    country_id = request.GET.get('country')
    state_id = request.GET.get('state')

    boards_queryset = Board.objects.all()

    if country_id:
        boards_queryset = boards_queryset.filter(location__country_id=country_id)
    if state_id:
        boards_queryset = boards_queryset.filter(location_id=state_id)

    boards = boards_queryset.prefetch_related(
        Prefetch('classes', queryset=StudentClass.objects.order_by('name')),
        Prefetch('classes__subjects', queryset=Subject.objects.order_by('name')),
        Prefetch('classes__subjects__chapters', queryset=Chapter.objects.order_by('name'))
    ).order_by('name')

    # For filter dropdowns


    return render(request, 'dashboard.html', {
        'boards': boards,
        'selected_country': country_id,
        'selected_state': state_id,
        'request':request,
    })

@permission_required({'education.add_board'},raise_exception=True)
def board_create(request):
    state_id = request.GET.get('state_id')
    form = BoardForm(request.POST or None)

    if state_id and not request.POST:
        form.fields['location'].initial = state_id
    
    if form.is_valid():
        form.save()
        messages.success(request, "Board added successfully.")
        return redirect('education_dashboard')  # Redirect to the dashboard after success
    
    return render(request, 'form.html', {'form': form, 'title': 'Add Board'})

@login_required
@permission_required({'education.add_studentclass'},raise_exception=True)
def class_create(request):
    board_id = request.GET.get('board_id')
    form = StudentClassForm(request.POST or None)
    
    if board_id and not request.POST:
        form.fields['board'].initial = board_id

    if form.is_valid():
        form.save()
        messages.success(request, "Class added.")
        return redirect('education_dashboard')
    
    return render(request, 'form.html', {'form': form, 'title': 'Add Class'})


@login_required
@permission_required({'education.add_division'},raise_exception=True)
def division_create(request):
    student_class_id = request.GET.get('student_class_id')
    form = DivisionForm(request.POST or None)

    if student_class_id and not request.POST:
        form.fields['student_class'].initial = student_class_id
    
    if form.is_valid():
        form.save()
        messages.success(request, "Division added successfully.")
        return redirect('education_dashboard')
    
    return render(request, 'form.html', {'form': form, 'title': 'Add Division'})


@login_required
@permission_required({'education.add_subject'},raise_exception=True)
def subject_create(request):
    class_id = request.GET.get('class_id')
    form = SubjectForm(request.POST or None)

    if class_id and not request.POST:
        form.fields['student_class'].initial = class_id

    if form.is_valid():
        form.save()
        messages.success(request, "Subject added.")
        return redirect('education_dashboard')

    return render(request, 'form.html', {'form': form, 'title': 'Add Subject'})

@login_required
@permission_required({'education.add_chapter'},raise_exception=True)
def chapter_create(request):
    subject_id = request.GET.get('subject_id')
    form = ChapterForm(request.POST or None)

    if subject_id and not request.POST:
        form.fields['subject'].initial = subject_id

    if form.is_valid():
        form.save()
        messages.success(request, "Chapter added.")
        return redirect('education_dashboard')

    return render(request, 'form.html', {'form': form, 'title': 'Add Chapter'})


def get_board(request):
    state_id = request.GET.get('state_id')
    
    if not state_id:
        return JsonResponse({'boards': []})  # Return empty list if no board selected

    try:
        boards = Board.objects.filter(location_id=state_id).values('id', 'name')
        return JsonResponse({'boards': list(boards)})
    except ValueError:
        return JsonResponse({'boards': []})

def get_classes(request):
    board_id = request.GET.get('board_id')
    
    if not board_id:
        return JsonResponse({'classes': []})  # Return empty list if no board selected

    try:
        classes = StudentClass.objects.filter(board_id=board_id).values('id', 'name')
        return JsonResponse({'classes': list(classes)})
    except ValueError:
        return JsonResponse({'classes': []})
    

def get_subject(request):
    class_id = request.GET.get('class_id')
    
    if not class_id:
        return JsonResponse({'subjects': []})  # Return empty list if no board selected

    try:
        subjects = Subject.objects.filter(student_class_id=class_id).values('id', 'name')
        return JsonResponse({'subjects': list(subjects)})
    except ValueError:
        return JsonResponse({'subjects': []})
    
def get_divisions(request):
    class_id = request.GET.get('class_id')
    if not class_id:
        return JsonResponse({'divisions': []})

    try:
        divisions = Division.objects.filter(student_class_id=class_id).values('id', 'name')
        return JsonResponse({'divisions': list(divisions)})
    except ValueError:
        return JsonResponse({'divisions': []})
    
def get_chapter(request):
    subject_id = request.GET.get('subject_id')
    
    if not subject_id:
        return JsonResponse({'chapters': []})  # Return empty list if no board selected

    try:
        chapters = Chapter.objects.filter(subject_id=subject_id).values('id', 'name')
        return JsonResponse({'chapters': list(chapters)})
    except ValueError:
        return JsonResponse({'chapters': []})


# Edit Board
@login_required
@permission_required({'education.change_board'},raise_exception=True)
def board_edit(request, pk):
    board = get_object_or_404(Board, pk=pk)
    form = BoardForm(request.POST or None, instance=board)  # Passing instance for editing
    
    if form.is_valid():
        form.save()
        messages.success(request, "Board updated successfully.")
        return redirect('education_dashboard')  # Redirect to the dashboard after saving
    
    return render(request, 'Edit_form.html', {'form': form, 'title': 'Edit Board'})

# Edit Student Class
@login_required
@permission_required({'education.change_studentclass'},raise_exception=True)
def class_edit(request, pk):
    student_class = get_object_or_404(StudentClass, pk=pk)
    form = StudentClassForm(request.POST or None, instance=student_class)  # Passing instance for editing
    
    if form.is_valid():
        form.save()
        messages.success(request, "Class updated successfully.")
        return redirect('education_dashboard')
    
    return render(request, 'Edit_form.html', {'form': form, 'title': 'Edit Class'})

# Edit Subject
@login_required
@permission_required({'education.change_subject'},raise_exception=True)
def subject_edit(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    form = SubjectForm(request.POST or None, instance=subject)  # Passing instance for editing
    
    if form.is_valid():
        form.save()
        messages.success(request, "Subject updated successfully.")
        return redirect('education_dashboard')
    
    return render(request, 'Edit_form.html', {'form': form, 'title': 'Edit Subject'})

@login_required
@permission_required({'education.delete_division'},raise_exception=True)
def division_edit(request, pk):
    division = get_object_or_404(Division, pk=pk)
    form = DivisionForm(request.POST or None, instance=division)

    if form.is_valid():
        form.save()
        messages.success(request, "Division updated successfully.")
        return redirect('education_dashboard')
    
    return render(request, 'education/Edit_form.html', {'form': form, 'title': 'Edit Division'})


# Edit Chapter
@login_required
@permission_required({'education.change_chapter'},raise_exception=True)
def chapter_edit(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk)
    form = ChapterForm(request.POST or None, instance=chapter)  # Passing instance for editing
    
    if form.is_valid():
        form.save()
        messages.success(request, "Chapter updated successfully.")
        return redirect('education_dashboard')
    
    return render(request, 'Edit_form.html', {'form': form, 'title': 'Edit Chapter'})



@login_required
@permission_required({'education.view_lesson'},raise_exception=True)
def lesson_list_create_view(request):
    user = request.user
    form = None
    can_add_lesson = False

    # Determine if the user can add lessons
    print(" user : ",user.role)
    if user.role in ['teacher', 'admin']:
        can_add_lesson = True
        if request.method == 'POST':
            form = LessonForm(request.POST)
            if form.is_valid():
                lesson = form.save(commit=False)
                lesson.created_by = user
                lesson.save()
                return redirect('lesson_list')
        else:
            form = LessonForm()

    # Base queryset for lessons
    lessons_queryset = Lesson.objects.all().select_related('chapter', 'created_by')

    # Filter lessons based on user role
    if user.role == 'student':
        # Students only see published lessons within published chapters
        # You'll need to define what makes a chapter "published" if not already.
        # For now, let's assume if a chapter exists, its lessons can be viewed if lesson is published.
        lessons_queryset = lessons_queryset.filter(is_published=True)
        # Further filter by student's board/class from profile
        if hasattr(user, 'profile') and user.profile:
            profile = user.profile
            if profile.board:
                lessons_queryset = lessons_queryset.filter(chapter__subject__student_class__board=profile.board)
            if profile.class_field:
                lessons_queryset = lessons_queryset.filter(chapter__subject__student_class=profile.class_field)

    elif user.role == 'teacher':
        # Teachers see their own lessons (published or not) and all published lessons
        lessons_queryset = (lessons_queryset.filter(is_published=True) | lessons_queryset.filter(created_by=user)).distinct()

    elif user.role == 'admin':
        # Admins see all lessons (no additional filtering needed)
        pass # lessons_queryset is already all()
    else:
        lessons_queryset = Lesson.objects.none() # No lessons for unknown roles

    # Pagination
    paginator = Paginator(lessons_queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    print("user.role :",user.role)
    context = {
        'page_obj': page_obj,
        'form': form,
        'can_add_lesson': can_add_lesson,
        'user_role': user.role,
    }
    return render(request, 'education/lesson_list.html', context)


@login_required
@permission_required({'education.view_lesson'},raise_exception=True)
def lesson_detail_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    # Basic permission check for viewing (e.g., unpublished lessons are restricted)
    if not lesson.is_published and request.user != lesson.created_by and request.user.role != 'admin':
        # If lesson is not published, and user is not the creator or an admin, deny access
        return redirect('lesson_list') # Or render an unauthorized page

    context = {
        'lesson': lesson
    }
    return render(request, 'education/lesson_detail.html', context)

# lesson_edit_view and lesson_delete_view remain largely the same,
# but ensure to use the new form and context variables.
@login_required
@permission_required({'education.change_lesson'},raise_exception=True)
def lesson_edit_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    user = request.user

    # Only creator or admin can edit
    if not (user.role == 'admin' or (user.role == 'teacher' and lesson.created_by == user)):
        return redirect('lesson_list')

    if request.method == 'POST':
        form = LessonForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            return redirect('lesson_detail', lesson_id=lesson.id)
    else:
        form = LessonForm(instance=lesson)

    context = {
        'form': form,
        'lesson': lesson,
        'user_role': user.role,
    }
    return render(request, 'education/lesson_edit.html', context)


@login_required
@permission_required({'education.delete_lesson'},raise_exception=True)
def lesson_delete_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    user = request.user

    # Only creator or admin can delete
    if not (user.role == 'admin' or (user.role == 'teacher' and lesson.created_by == user)):
        return redirect('lesson_list')

    if request.method == 'POST':
        lesson.delete()
        return redirect('lesson_list')

    context = {
        'lesson': lesson,
        'user_role': user.role,
    }
    return render(request, 'education/lesson_confirm_delete.html', context)

@login_required
@permission_required({'education.delete_board'},raise_exception=True)
def board_delete(request, pk):
    board = get_object_or_404(Board, pk=pk)
    if request.method == 'POST':
        board.delete()
        messages.success(request, f"Board '{board.name}' deleted successfully.")
        return redirect('education_dashboard')
    return render(request, 'confirm_delete.html', {'obj': board, 'type': 'Board'})

@login_required
@permission_required({'education.delete_studentclass'},raise_exception=True)
def class_delete(request, pk):
    student_class = get_object_or_404(StudentClass, pk=pk)
    if request.method == 'POST':
        student_class.delete()
        messages.success(request, f"Class '{student_class.name}' deleted successfully.")
        return redirect('education_dashboard')
    return render(request, 'confirm_delete.html', {'obj': student_class, 'type': 'Class'})

@login_required
@permission_required({'education.delete_subject'},raise_exception=True)
def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        subject.delete()
        messages.success(request, f"Subject '{subject.name}' deleted successfully.")
        return redirect('education_dashboard')
    return render(request, 'confirm_delete.html', {'obj': subject, 'type': 'Subject'})

# NEW: Division Delete View
@login_required
@permission_required({'education.delete_division'},raise_exception=True)
def division_delete(request, pk):
    division = get_object_or_404(Division, pk=pk)
    if request.method == 'POST':
        division.delete()
        messages.success(request, f"Division '{division.name}' deleted successfully.")
        return redirect('education_dashboard')
    return render(request, 'education/confirm_delete.html', {'obj': division, 'type': 'Division'})

@login_required
@permission_required({'education.delete_chapter'},raise_exception=True)
def chapter_delete(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk)
    if request.method == 'POST':
        chapter.delete()
        messages.success(request, f"Chapter '{chapter.name}' deleted successfully.")
        return redirect('education_dashboard')
    return render(request, 'confirm_delete.html', {'obj': chapter, 'type': 'Chapter'})
