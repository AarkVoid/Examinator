from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Question, QuestionPaper, PaperQuestion, MCQOption, MatchPair, FillBlankAnswer,ShortAnswer, TrueFalseAnswer
from .forms import (
    QuestionForm, MCQOptionFormSet, FillBlankAnswerFormSet, ShortAnswerForm,
    MatchPairFormSet, TrueFalseAnswerForm, QuestionPaperForm,
    QuestionSearchForm
)
from curritree.models import TreeNode
from django.db import transaction
import json
from django.db.models import Count,Q
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum 
from django.contrib.auth.decorators import permission_required
import csv, io, traceback
from .utils import validate_paper_limits_and_license
from datetime import date
from saas.models import LicenseGrant, UsageLimit
from django.core.files.storage import default_storage
from django.utils import timezone
import csv, io, traceback, os
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger 
# Assuming OrganizationProfile is imported from saas.models based on Question model definition
from saas.models import OrganizationProfile
from django.core.exceptions import ValidationError


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

def filter_questions_by_license(organization):
    """
    Return queryset of questions matching the licensed curriculum nodes 
    for the given organization, plus questions owned by the organization, 
    and published questions.
    """
    if not organization:
        return Question.objects.none()

    # Get all license grants for this organization
    grants = organization.license_grants.all()

    # Collect all allowed curriculum node IDs
    allowed_nodes = set()
    for grant in grants:
        # NOTE: get_all_licensed_nodes should return all descendants of the licensed nodes
        # We must assume the MPTT model and the license manager handle this correctly.
        for node in grant.get_all_licensed_nodes():
            allowed_nodes.add(node.id)

    # Filter questions linked to these nodes
    return Question.objects.filter(
        Q(curriculum_board_id__in=allowed_nodes)
        | Q(curriculum_class_id__in=allowed_nodes)
        | Q(curriculum_subject_id__in=allowed_nodes)
        | Q(curriculum_chapter_id__in=allowed_nodes)
    ).distinct()

# --- Main View Function (Updated) ---

@login_required
@permission_required('quiz.view_question',login_url='profile_update')
def question_list(request):
    
    # New Parameters for tabs and organization filter. Default tab is 'public'.
    tab_type = request.GET.get("tab", "public") 
    org_filter_id = request.GET.get("organization_id")
    
    filter_type = request.GET.get("filter", "all")
    search_query = request.GET.get("q", "")
    selected_node_id = request.GET.get("input_node")

    # --- Initial Context and User Role ---
    organization = getattr(request.user.profile, "organization_profile", None)
    is_staff_or_superuser = request.user.is_superuser or request.user.is_staff
    
    # --- Base QuerySet Determination (CRITICAL ACCESS LOGIC) ---
    
    if is_staff_or_superuser:
        if tab_type == "organization":
            # Case 1: Staff/Superuser viewing ALL ORGANIZATION questions (Auditing View)
            # Content: Organization is NOT NULL
            queryset = Question.objects.filter(organization__isnull=False)
            
            # Apply organization filter if selected (MANDATORY for Staff filter functionality)
            if org_filter_id:
                queryset = queryset.filter(organization_id=org_filter_id)
        else: # tab_type == "public" (or default)
            # Case 2: Staff/Superuser viewing STAFF/PUBLIC questions
            # Content: Organization IS NULL
            queryset = Question.objects.filter(organization__isnull=True)
            
    elif organization:
        if tab_type == "organization":
            # Case 3: Organization User viewing MY ORGANIZATION/LICENSED questions
            # Content: Restricted by license/ownership
            queryset = Question.objects.filter(organization=organization)
        else: # tab_type == "public" (or default)
            # Case 4: Organization User viewing PUBLIC questions
            # Content: Organization IS NULL
            queryset = filter_questions_by_license(organization)
            # Additional filter for organization IS NULL
            queryset = queryset.filter(is_published=True).exclude(organization=organization)
            
            
    else:
        # Default for users with no organization affiliation (safety default: public only)
        queryset = Question.objects.filter(organization__isnull=True)

    # --- Question Type Counts (MUST be based on the base 'queryset') ---
    
    # IMPORTANT: We gather the IDs of the base queryset BEFORE applying further filters 
    # so that the sidebar counts reflect the total bank the user has access to in this tab.
    base_queryset_ids = queryset.values_list('id', flat=True)
    
    counts = (
        Question.objects.filter(id__in=base_queryset_ids)
        .values("question_type")
        .annotate(total=Count("id"))
    )

    result = {key: 0 for key, _ in Question.QUESTION_TYPES}
    for entry in counts:
        result[entry["question_type"]] = entry["total"]

    json_type_count = json.dumps(result, indent=2)

    # --- Apply Filters (applied to the base 'queryset' to narrow the view) ---
    if filter_type != "all":
        queryset = queryset.filter(question_type=filter_type)

    if search_query:
        # Searching question text or answer text
        # Assuming question_answer is a related field/lookup that works, keeping the user's logic
        queryset = queryset.filter(Q(question_text__icontains=search_query) | Q(question_answer__icontains=search_query))

    if selected_node_id:
        try:
            # Note: Since the base_queryset is already distinct, we can apply filters directly
            queryset = queryset.filter(
                Q(curriculum_board__id=selected_node_id)
                | Q(curriculum_class__id=selected_node_id)
                | Q(curriculum_subject__id=selected_node_id)
                | Q(curriculum_chapter__id=selected_node_id)
            )
        except Exception:
            # Silently fail on invalid node ID and continue with the current queryset
            pass

    # Ensure the queryset is distinct before pagination (if needed after filtering)
    final_queryset = queryset.distinct()

    # --- Pagination Logic ---
    paginator = Paginator(final_queryset, settings.QUESTIONS_PER_PAGE)
    page_number = request.GET.get('page')
    
    try:
        questions = paginator.page(page_number)
    except PageNotAnInteger:
        questions = paginator.page(1)
    except EmptyPage:
        questions = paginator.page(paginator.num_pages)

    # --- Root Question Counts (MUST be based on the base 'queryset') ---
    root_question_counts = {}
    # Assuming MPTT model where parent__isnull=True correctly finds root nodes
    root_nodes = TreeNode.objects.filter(parent__isnull=True).order_by('name')

    for root in root_nodes:
        # Count only questions in the base set that link to this root's descendants
        # We use id__in base_queryset_ids to restrict the count to what the user can see in this tab
        count = Question.objects.filter(id__in=base_queryset_ids).filter(
            Q(curriculum_board__in=root.get_descendants(include_self=True))
            | Q(curriculum_class__in=root.get_descendants(include_self=True))
            | Q(curriculum_subject__in=root.get_descendants(include_self=True))
            | Q(curriculum_chapter__in=root.get_descendants(include_self=True))
        ).count()
        root_question_counts[str(root.name)] = count

    json_root_count = json.dumps(root_question_counts, indent=2)

    # Fetch all organizations for the filter dropdown (only for staff/superuser)
    all_organizations = []
    if is_staff_or_superuser:
        all_organizations = OrganizationProfile.objects.all().order_by('name')
        
    # --- Render ---
    return render(request, "quiz/question_list.html", {
        "questions": questions,
        "filter_type": filter_type,
        "search_query": search_query,
        "question_types": Question.QUESTION_TYPES,
        "root_nodes": root_nodes,
        "selected_node_id": selected_node_id,
        "json_type_count": json.loads(json_type_count),
        "json_root_count": json.loads(json_root_count),
        
        # New context for filtering and tabs
        "tab_type": tab_type,
        "is_staff_or_superuser": is_staff_or_superuser,
        "all_organizations": all_organizations,
        "org_filter_id": org_filter_id,
    })



def get_child_nodes(request, node_id):
    # 1. Determine the base queryset of children
    try:
        if node_id == 'null':
            # Case 1: Root nodes (top-level nodes with no parent)
            children_queryset = TreeNode.objects.filter(parent__isnull=True)
        else:
            # Case 2: Standard children (find parent and get its children)
            parent_node = TreeNode.objects.get(pk=node_id)
            children_queryset = parent_node.children.all()
        
        # 2. Apply access filtering if the user is NOT a superuser
        if not request.user.is_superuser:
            # Ensure the user is logged in and has a profile
            if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
                 # For security, return an empty list or unauthorized error if access is required
                return JsonResponse({"error": "Authentication required"}, status=403)

            # Get the PKs of all nodes accessible via the user's M2M field
            accessible_node_pks = request.user.profile.academic_stream.values_list('pk', flat=True)
            
            # Filter the children queryset to only include those whose PK 
            # is in the list of accessible nodes.
            children_queryset = children_queryset.filter(pk__in=accessible_node_pks)

        # 3. Serialize and return the filtered children
        children = children_queryset.values("id", "name", "node_type").order_by('name')
        
        return JsonResponse({"children": list(children)}, status=200)

    except TreeNode.DoesNotExist:
        # Catches if the requested parent_node (by node_id) doesn't exist
        return JsonResponse({"error": "Node not found"}, status=404)
    except Exception as e:
        # Catch unexpected errors (e.g., database connection issues)
        print(f"An unexpected error occurred in get_child_nodes: {e}")
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)
    




# --- Main CRUD View ---
@login_required
@permission_required('quiz.add_question',login_url='profile_update')
def question_create(request, pk=None):
    """
    Handles question creation/update by deriving Board and Subject from Chapter.
    """
    question = None
    posted_data = {} 
    if pk:
        # For edit mode, fetch the existing question
        question = get_object_or_404(Question, pk=pk)
        title = "Edit Question"
    else:
        title = "Add New Question"

    if request.method == 'POST':
        posted_data = request.POST
        
        # Get the child_and_types JSON data
        child_and_types_json = request.POST.get('child_and_types')
        child_and_types = {}
        
        if child_and_types_json:
            try:
                child_and_types = json.loads(child_and_types_json)
                print("Received child_and_types:", child_and_types)
            except json.JSONDecodeError as e:
                print("Error parsing child_and_types JSON:", e)
        
        # Get the final node ID
        chapter_id = child_and_types.get('chapter')
        class_id = child_and_types.get('class')
        board_id = child_and_types.get('board')
        subject_id = child_and_types.get('subject')
        
        # Get other form data
        question_text = request.POST.get('question_text')
        q_type = request.POST.get('question_type')
        difficulty = request.POST.get('difficulty')
        marks = request.POST.get('marks')

        # --- NEW: Retrieve the uploaded file from request.FILES ---
        question_image = request.FILES.get('question_image')
        # ------------------------------------------------------------
        
        # Basic validation
        if not all([chapter_id, question_text, q_type, difficulty, marks]):
            error_message = "Please fill in all required fields."
            
            context = {
                'title': title,
                'error': error_message,
                'board_nodes': board_nodes,
                'QUESTION_TYPES': QUESTION_TYPES,
                'DIFFICULTY_LEVELS': DIFFICULTY_LEVELS,
                'posted': request.POST, 
                'question': question,
                'child_and_types': child_and_types,  # Pass back to template
            }
            return render(request, 'quiz/question_form.html', context)
        
            
        # Re-render on hierarchy error
        if not (board_id and subject_id):
            error_message = error_message if 'error_message' in locals() else "Could not determine complete Board/Subject hierarchy for the selected Chapter."
            board_nodes = TreeNode.objects.filter(node_type__in=['board', 'competitive']).order_by('name').values('id', 'name')
            context = {
                'title': title,
                'error': error_message,
                'board_nodes': board_nodes,
                'QUESTION_TYPES': QUESTION_TYPES,
                'DIFFICULTY_LEVELS': DIFFICULTY_LEVELS,
                'posted': request.POST,
                'question': question,
                'posted': posted_data,
            }
            return render(request, 'quiz/question_form.html', context)
        
        # --- 3. Database Save Logic ---
        try:
            if question:
                q = question
            else:
                q = Question()

                q.created_by = request.user
            
            # Assign derived IDs
            q.curriculum_board_id = board_id 
            q.curriculum_class_id = class_id
            q.curriculum_subject_id = subject_id
            q.curriculum_chapter_id = chapter_id
            
            # Assign other field
            q.question_text = question_text
            q.question_type = q_type
            q.difficulty = difficulty
            if request.user.is_superuser:
                q.is_published = True
            else:
                q.organization = request.user.profile.organization_profile
            
            q.marks = float(marks) if marks else 0

            # --- NEW: Assign the uploaded image file ---
            if question_image:
                q.question_image = question_image
            # ------------------------------------------

            q.save()
            
            # Option/Answer Handling goes here
            # Handle different question types
            if q.question_type == 'mcq':
                return redirect('quiz:question_mcq_options', q.id)
            elif q.question_type == 'fill_blank':
                return redirect('quiz:question_fill_blank', q.id)
            elif q.question_type == 'short_answer':
                return redirect('quiz:question_short_answer', q.id)
            elif q.question_type == 'match':
                return redirect('quiz:question_match_pairs', q.id)
            elif q.question_type == 'true_false':
                return redirect('quiz:question_true_false', q.id)
            
            messages.success(request, 'Question created successfully!')
            return redirect('quiz:question_list')
            
        
        except Exception as e:
            error_message = f"An error occurred while saving: {e}"
            board_nodes = TreeNode.objects.filter(node_type__in=['board', 'competitive']).order_by('name').values('id', 'name')
            context = {
                'title': title,
                'error': error_message,
                'board_nodes': board_nodes,
                'QUESTION_TYPES': QUESTION_TYPES,
                'DIFFICULTY_LEVELS': DIFFICULTY_LEVELS,
                'posted': request.POST,
                'question': question,
                'posted': posted_data,
            }
            return render(request, 'quiz/question_form.html', context)


    # --- Initial GET Request Logic ---
    board_nodes = TreeNode.objects.filter(node_type__in=['board', 'competitive']).order_by('name').values('id', 'name')
    context = {
        'title': title,
        'board_nodes': board_nodes,
        'QUESTION_TYPES': QUESTION_TYPES, # New types passed here
        'DIFFICULTY_LEVELS': DIFFICULTY_LEVELS,
        'question': question, 
    }
    return render(request, 'quiz/question_form.html', context)



@login_required
def question_mcq_options(request, question_id):
    question = get_object_or_404(Question, id=question_id, question_type='mcq')
    
    if request.method == 'POST':
        formset = MCQOptionFormSet(request.POST, instance=question)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'MCQ options saved successfully!')
            return redirect('quiz:question_list')
    else:
        formset = MCQOptionFormSet(instance=question)
    
    return render(request, 'quiz/question_mcq_options.html', {
        'question': question,
        'formset': formset
    })

@login_required
def question_fill_blank(request, question_id):
    question = get_object_or_404(Question, id=question_id, question_type='fill_blank')
    
    if request.method == 'POST':
        formset = FillBlankAnswerFormSet(request.POST, instance=question)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Fill in the blank answers saved successfully!')
            return redirect('quiz:question_list')
    else:
        formset = FillBlankAnswerFormSet(instance=question)
    
    return render(request, 'quiz/question_fill_blank.html', {
        'question': question,
        'formset': formset
    })

@login_required
def question_short_answer(request, question_id):
    question = get_object_or_404(Question, id=question_id, question_type='short_answer')
    
    try:
        short_answer = question.short_answer
    except:
        short_answer = None
    
    if request.method == 'POST':
        form = ShortAnswerForm(request.POST, instance=short_answer)
        if form.is_valid():
            short_answer = form.save(commit=False)
            short_answer.question = question
            short_answer.save()
            messages.success(request, 'Short answer details saved successfully!')
            return redirect('quiz:question_list')
    else:
        form = ShortAnswerForm(instance=short_answer)
    
    return render(request, 'quiz/question_short_answer.html', {
        'question': question,
        'form': form
    })

@login_required
def question_match_pairs(request, question_id):
    question = get_object_or_404(Question, id=question_id, question_type='match')
    
    if request.method == 'POST':
        formset = MatchPairFormSet(request.POST, instance=question)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Match pairs saved successfully!')
            return redirect('quiz:question_list')
    else:
        formset = MatchPairFormSet(instance=question)
    
    return render(request, 'quiz/question_match_pairs.html', {
        'question': question,
        'formset': formset
    })

@login_required
def question_true_false(request, question_id):
    question = get_object_or_404(Question, id=question_id, question_type='true_false')
    
    try:
        true_false = question.true_false_answer
    except:
        true_false = None
    
    if request.method == 'POST':
        form = TrueFalseAnswerForm(request.POST, instance=true_false)
        if form.is_valid():
            true_false = form.save(commit=False)
            true_false.question = question
            true_false.save()
            messages.success(request, 'True/False answer saved successfully!')
            return redirect('quiz:question_list')
    else:
        form = TrueFalseAnswerForm(instance=true_false)
    
    return render(request, 'quiz/question_true_false.html', {
        'question': question,
        'form': form
    })


@login_required
@permission_required('quiz.change_question',login_url='profile_update')
def question_detail_and_edit(request, question_id):
    # Security: Ensure user only accesses their own questions
    UserInf = request.user
    if UserInf.is_superuser:
        question = get_object_or_404(Question, id=question_id)
    else:
        question = get_object_or_404(Question, id=question_id,organization=request.user.profile.organization_profile)

    # --- Determine which form type to use (Based on question.question_type) ---
    answer_form_class_map = {
        'mcq': MCQOptionFormSet,
        'fill_blank': FillBlankAnswerFormSet,
        'match': MatchPairFormSet,
        'short_answer': ShortAnswerForm,
        'true_false': TrueFalseAnswerForm,
    }

    AnswerFormOrSet = answer_form_class_map.get(question.question_type)
    
    # Initialize variables for safe handling
    answer_instance = question # Default instance for FormSets
    answer_form_context = None
    needs_type_selection = False

    if AnswerFormOrSet is None:
        # If the type is missing or invalid, we cannot load the answer form
        needs_type_selection = True
    else:
        # For one-to-one forms, we ensure the related object exists
        if question.question_type in ['short_answer']:
            answer_instance, _ = ShortAnswer.objects.get_or_create(question=question)
        elif question.question_type in ['true_false']:
            answer_instance, _ = TrueFalseAnswer.objects.get_or_create(question=question)

    # --- POST Handling ---
    if request.method == 'POST':
        # Identify which form was submitted (core question details or answer details)
        action = request.POST.get('form_action')
        
        if action == 'core_details':
            form = QuestionForm(request.POST, instance=question,user=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Core question details updated successfully.')
                return redirect('quiz:question_edit', question_id=question.id)
            else:
                # Initialize answer form for context if core details fail validation (safely)
                if AnswerFormOrSet:
                    answer_form_context = AnswerFormOrSet(instance=answer_instance)
                messages.error(request, 'Error updating core details. Please correct the fields.')
        
        elif action == 'answer_details':
            # GUARD: Prevent saving answers if the question type is undefined
            if needs_type_selection:
                messages.error(request, 'Cannot save answers: The question type must be set in the core details first.')
                form = QuestionForm(instance=question,user=request.user)
            else:
                # Handle FormSet (MCQ, Fill, Match) or single Form (Short, T/F)
                answer_form_context = AnswerFormOrSet(request.POST, instance=answer_instance)
                
                if answer_form_context.is_valid():
                    answer_form_context.save()
                    messages.success(request, f'{question.get_question_type_display()} answers/options updated successfully.')
                    return redirect('quiz:question_edit', question_id=question.id)
                else:
                    # Initialize core form for context if answer details fail validation
                    form = QuestionForm(instance=question,user=request.user)
                    messages.error(request, f'Error updating {question.get_question_type_display()} answers. Please correct the errors.')
        
        else:
            # Fallback/Unrecognized POST
            messages.error(request, 'Unrecognized form submission.')
            form = QuestionForm(instance=question,user=request.user)
            if AnswerFormOrSet:
                answer_form_context = AnswerFormOrSet(instance=answer_instance)

    # --- GET Handling (or POST failure initialization) ---
    else:
        form = QuestionForm(instance=question,user=request.user)
        if AnswerFormOrSet:
            answer_form_context = AnswerFormOrSet(instance=answer_instance)

    context = {
        'question': question,
        'form': form,
        'answer_form_context': answer_form_context,
        # Safely check if it's a FormSet, defaulting to False if context is None
        'is_formset': hasattr(answer_form_context, 'management_form') if answer_form_context else False,
        'needs_type_selection': needs_type_selection, # New flag for template logic
    }
    return render(request, 'quiz/question_detail_edit.html', context)

@login_required
@permission_required('quiz.delete_question',login_url='profile_update')
def question_delete(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'Question deleted successfully!')
        return redirect('quiz:question_list')
    
    return render(request, 'quiz/question_confirm_delete.html', {'question': question})

@login_required
@permission_required('quiz.view_questionpaper',login_url='profile_update')
def paper_list(request):
    """
    Displays a paginated list of published or draft papers, filtered by organization, 
    and calculates remaining paper and draft limits.
    """
    # Initialize limit variables and selected organization ID
    remaining_papers = 0
    total_max_papers = 0
    remaining_draft_papers = 0
    selected_org_id = request.GET.get('org', '') # Get the organization filter ID

    # Base Queryset
    papers_qs = QuestionPaper.objects.select_related('curriculum_subject', 'created_by', 'organization').order_by('-created')
    
    # Initialize querysets for pagination
    draft_papers_qs = papers_qs.filter(is_published=False)
    published_papers_qs = papers_qs.filter(is_published=True)
    
    # ----------------------------------------------------
    # Superuser Filter Logic
    # ----------------------------------------------------
    if request.user.is_superuser:
        # Fetch all organizations for the filter dropdown
        all_organizations = OrganizationProfile.objects.all().order_by('name')
        
        # Apply organization filter if an ID is provided
        if selected_org_id and selected_org_id.isdigit():
            draft_papers_qs = draft_papers_qs.filter(organization_id=selected_org_id)
            published_papers_qs = published_papers_qs.filter(organization_id=selected_org_id)
            
            # Since a filter is applied, we calculate counts based on the filter
            draft_papers_count = draft_papers_qs.count()
            published_papers_count = published_papers_qs.count()
        else:
            # No filter selected, get counts of all papers
            draft_papers_count = draft_papers_qs.count()
            published_papers_count = published_papers_qs.count()

    # ----------------------------------------------------
    # Organization User Logic
    # ----------------------------------------------------
    else:
        organization = request.user.profile.organization_profile
        all_organizations = [] # Not needed for non-staff users
        
        if organization:
            # 1. Filter Querysets and get Counts for the specific organization
            draft_papers_qs = draft_papers_qs.filter(organization=organization)
            published_papers_qs = published_papers_qs.filter(organization=organization)
            draft_papers_count = draft_papers_qs.count()
            published_papers_count = published_papers_qs.count()
            
            # 2. License/Limit Calculations
            today = date.today()
            license_grants = organization.license_grants.filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
            
            try:
                # Assuming UsageLimit is fetched as a single related object
                usage_limit = UsageLimit.objects.get(organization_profile=organization)
            except UsageLimit.DoesNotExist:
                usage_limit = None 

            # Calculate Remaining Question Papers (Published Limit)
            total_max_papers = license_grants.aggregate(total=Sum('max_question_papers'))['total'] or 0
            remaining_papers = total_max_papers - published_papers_count

            # Calculate Remaining Draft Papers Limit
            if usage_limit:
                max_drafts = usage_limit.max_question_papers_drafts
                remaining_draft_papers = max_drafts - draft_papers_count
            else:
                # If no usage limit object, assume 0 remaining based on business logic for limits
                remaining_draft_papers = 0
        else:
            # No organization: set querysets to empty and counts to 0
            draft_papers_qs = QuestionPaper.objects.none()
            published_papers_qs = QuestionPaper.objects.none()
            draft_papers_count = 0
            published_papers_count = 0


    # Determine which set of papers (QUERYSET) to display based on the 'tab' query parameter
    tab = request.GET.get('tab', 'published') # Default to 'published'
    
    if tab == 'drafts':
        papers_to_display = draft_papers_qs
    else:
        papers_to_display = published_papers_qs


    # Pagination logic
    paginator = Paginator(papers_to_display, 10)
    page = request.GET.get('page')
    papers_paged = paginator.get_page(page)
    
    context = {
        'papers': papers_paged, 
        'current_tab': tab,
        
        # Superuser Context
        'all_organizations': all_organizations,
        'selected_org_id': selected_org_id, 
        
        # User Context (Limit & Counts)
        'remaining_papers': remaining_papers,
        'total_max_papers': total_max_papers,
        'remaining_draft_papers': remaining_draft_papers,
        'draft_count': draft_papers_count,
        'published_count': published_papers_count,
        'organization': request.user.profile.organization_profile # Pass organization for utility checks
    }
    
    return render(request, 'quiz/paper_list.html', context)

@login_required
@permission_required('quiz.publish_questionpaper',login_url='profile_update')
def publish_paper(request, paper_id):
    """
    Changes a paper's status from Draft to Published, enforcing usage limits 
    and consuming a slot on the specific LicenseGrant.
    """
    paper = get_object_or_404(QuestionPaper, id=paper_id)
    organization = request.user.profile.organization_profile

    # Security check: Only allow the creator (or superuser) to publish
    if paper.created_by != request.user and not request.user.is_superuser:
        messages.error(request, "You do not have permission to publish this paper.")
        return redirect('quiz:paper_list')

    if paper.is_published:
        messages.info(request, "This paper is already published.")
        return redirect('quiz:paper_list')

    try:
        with transaction.atomic():
            # 🛑 ENFORCEMENT & SELECTION: Check published limit BEFORE publishing.
            # This function returns the specific LicenseGrant to consume.
            license_grant_to_consume = validate_paper_limits_and_license(
                organization=organization,
                curriculum_subject=paper.curriculum_subject,
                is_published=True, 
                existing_paper_id=paper.id 
            )

            # If validation passes, update the paper status
            paper.is_published = True
            paper.save()
            
            # 🛑 CONSUME THE LICENSE SLOT by incrementing the counter on the selected grant
            license_grant_to_consume.question_papers_created += 1
            license_grant_to_consume.save()
            
            messages.success(request, f"'{paper.title}' has been successfully published, consuming one license slot!")
            
    except ValidationError as e:
        messages.error(request, f"Could not publish paper: {e}")
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {e}")

    # Redirect back to the drafts tab
    return redirect('quiz:paper_list')



@login_required
@permission_required('quiz.add_questionpaper', login_url='profile_update')
def add_question_paper(request):
    # Get organization from request
    organization = None
    
    if request.user.profile.organization_profile:
        organization = request.user.profile.organization_profile
    print('OrganiZation : ',organization)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get basic form data
                title = request.POST.get('title')
                curriculum_subject_id = request.POST.get('curriculum_subject')
                pattern = request.POST.get('pattern', 'standard')
                total_marks = request.POST.get('total_marks', 0)
                duration_minutes = request.POST.get('duration_minutes', 60)
                instructions = request.POST.get('instructions', '')
                selected_chapters = request.POST.getlist('selectedItemsList')
                
                # Validate required fields
                if not title or not curriculum_subject_id:
                    messages.error(request, "Title and Subject are required fields.")
                    print("Missing required fields")
                    return redirect('quiz:add_question_paper')
                
                # Get the subject node
                curriculum_subject = get_object_or_404(TreeNode, id=curriculum_subject_id, node_type='subject')


                validate_paper_limits_and_license(
                    organization=organization,
                    curriculum_subject=curriculum_subject,
                    is_published=False, # We are checking against the DRAFT limit
                    existing_paper_id=None # This is a new paper, so no ID to exclude
                )
                
                # Create the question paper
                question_paper = QuestionPaper(
                    title=title,
                    organization=organization,
                    curriculum_subject=curriculum_subject,
                    pattern=pattern,
                    total_marks=total_marks or 0,
                    duration_minutes=duration_minutes or 60,
                    instructions=instructions,
                    created_by=request.user
                )
                question_paper.save()
                
                # Add selected chapters/units
                print("Selected Chapters:", selected_chapters)
                if selected_chapters:
                    chapter_nodes = TreeNode.objects.filter(id__in=selected_chapters)
                    question_paper.curriculum_chapters.set(chapter_nodes)
                
                print("Question paper created:", question_paper)
                messages.success(request, f"Question paper '{title}' created successfully!")
                return redirect('quiz:paper_detail', paper_id=question_paper.id)
                
        except Exception as e:
            messages.error(request, f"Error creating question paper: {str(e)}")
            print("Error:", str(e))
            return redirect('quiz:add_question_paper')
    
    # GET request - prepare the form data
    # Get root nodes (boards and classes) for the cascading hierarchy
    root_nodes = TreeNode.objects.filter(
        node_type__in=['board', 'competitive']
    ).order_by('node_type', 'name')
    
    # Get pattern choices
    pattern_choices = QuestionPaper.PAPER_PATTERNS
    
    context = {
        'root_nodes': root_nodes,
        'pattern_choices': pattern_choices,
        'organization': organization,
    }
    
    return render(request, 'quiz/add_question_paper.html', context)

@login_required
def get_curriculum_tree(request, subject_id):
    """AJAX endpoint to get curriculum tree for a subject (for chapter selection)"""
    try:
        subject = get_object_or_404(TreeNode, id=subject_id, node_type='subject')
        
        def build_tree(node):
            """Recursively build tree structure for chapters/units"""
            children_data = []
            for child in node.children.all().order_by('order', 'name'):
                child_data = {
                    'id': child.id,
                    'name': child.name,
                    'node_type': child.node_type,
                    'children': build_tree(child) if child.children.exists() else []
                }
                children_data.append(child_data)
            return children_data
        
        tree_data = {
            'id': subject.id,
            'name': subject.name,
            'node_type': subject.node_type,
            'children': build_tree(subject)
        }
        
        return JsonResponse({'success': True, 'tree': tree_data})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
def get_selected_nodes_info(request):
    """AJAX endpoint to get info about selected nodes for display"""
    if request.method == 'POST':
        try:
            node_ids = request.POST.getlist('node_ids[]')
            nodes = TreeNode.objects.filter(id__in=node_ids)
            
            node_data = []
            for node in nodes:
                node_data.append({
                    'id': node.id,
                    'name': node.name,
                    'node_type': node.node_type,
                    'path': node.get_path_display()
                })
            
            return JsonResponse({'success': True, 'nodes': node_data})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@permission_required('quiz.view_questionpaper', login_url='profile_update')
def paper_detail(request, paper_id):
    paper = get_object_or_404(QuestionPaper, id=paper_id)

    # 1. Handle POST request to synchronize paper's total_marks field
    if request.method == 'POST':
        # Check for a specific action to update the marks
        if 'action' in request.POST and request.POST['action'] == 'update_total_marks':
            
            # Basic permission check
            if paper.created_by != request.user and not request.user.is_staff:
                messages.error(request, 'You do not have permission to edit this paper.')
                return redirect('quiz:paper_detail', paper.id)

            # Calculate the current total marks directly from the questions
            current_total_marks_sum = paper.paper_questions.aggregate(
                total_marks=Sum('question__marks')
            )['total_marks'] or 0

            try:
                with transaction.atomic():
                    # Update the paper's official total_marks field
                    paper.total_marks = current_total_marks_sum
                    paper.save(update_fields=['total_marks'])
                    messages.success(request, f"Paper total marks successfully updated to {current_total_marks_sum}.")
            except Exception as e:
                messages.error(request, f"An error occurred while updating marks: {e}")
            
            return redirect('quiz:paper_detail', paper.id)


    total_current_marks = paper.paper_questions.aggregate(
        total_marks=Sum('question__marks')
    )['total_marks'] or 0

    # Board Detail: Assuming the curriculum_subject model has a 'board' relationship/field
    # Adjust this line if your model path is different (e.g., just paper.board)
    board_detail = paper.curriculum_subject.get_ancestors()

    for anstor in board_detail:
        if anstor.node_type == 'class':
            Class_name = anstor
            break
    
    # 3. Questions Query and Sorting (as provided in your original request)
    questions_queryset = paper.paper_questions.select_related(
        'question',
        'question__curriculum_subject',
        'question__curriculum_chapter'
    ) 

    if paper.pattern == 'difficulty_wise':
        difficulty_order = {'easy': 1, 'medium': 2, 'hard': 3}
        paper_questions = sorted(
            questions_queryset, 
            key=lambda pq: difficulty_order.get(pq.question.difficulty, 99)
        )
    
    elif paper.pattern == 'section_wise':
        paper_questions = questions_queryset.order_by(
            'question__curriculum_subject__name', 
            'question__curriculum_chapter__name'
        )
        
    elif paper.pattern == 'custom':
        paper_questions = questions_queryset.order_by('order')

    elif paper.pattern == 'standard':
        paper_questions = questions_queryset.order_by('question__question_type')
    
    else: # Fallback for any other undefined patterns
        paper_questions = questions_queryset.order_by('order', 'question__created')
    
    # 4. Prepare context
    context = {
        'paper': paper,
        'paper_questions': paper_questions,
        'total_current_marks': total_current_marks, # NEW
        'board_detail': board_detail,             # NEW
        'Class_name': Class_name,
    }
    
    return render(request, 'quiz/paper_detail.html', context)


@login_required
@permission_required('quiz.add_paperquestion', login_url='profile_update')
def paper_add_questions(request, paper_id):
    paper = get_object_or_404(QuestionPaper, id=paper_id)
    
    # Check if user can edit this paper (owner or admin)
    # ---------------------------------------------------------
    if paper.created_by != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to edit this paper.')
        return redirect('quiz:paper_detail', paper.id)
    
    # Get available questions that belong to this paper's subject
    existing_question_ids = paper.paper_questions.values_list('question_id', flat=True)
    
    # 🛑 Initial Query: Start with questions NOT already in the paper 🛑
    if request.user.is_staff or request.user.is_superuser:
        questions = Question.objects.all()
    else:
        org = getattr(request.user.profile, "organization_profile", None)
        questions = Question.objects.filter(
            Q(is_published=True) |
            Q(organization=org)
        )


    if paper.curriculum_chapters.exists():
        questions = questions.filter(
            curriculum_chapter__in=paper.curriculum_chapters.all()
        )


    
    
    # Apply filters
    search_form = QuestionSearchForm(request.GET)
    if search_form.is_valid():
        cleaned_data = search_form.cleaned_data

        # 🛑 NEW FILTER: Apply Board Filter
        if cleaned_data['board']:
            questions = questions.filter(curriculum_board=cleaned_data['board'])
            
        # Filter by Subject (which is likely a child of the selected Board)
        if cleaned_data['curriculum_subject']:
            questions = questions.filter(curriculum_subject=cleaned_data['curriculum_subject'])

        # Filter by Chapter (which is likely a child of the selected Subject)
        if cleaned_data['curriculum_chapter']:
            questions = questions.filter(curriculum_chapter=cleaned_data['curriculum_chapter'])
            
        if cleaned_data['question_type']:
            questions = questions.filter(question_type=cleaned_data['question_type'])
            
        if cleaned_data['difficulty']:
            questions = questions.filter(difficulty=cleaned_data['difficulty'])
            
        if cleaned_data['search']:
            questions = questions.filter(question_text__icontains=cleaned_data['search'])

    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_questions')
        section = request.POST.get('section', '')
        
        if selected_ids:
            last_order = paper.paper_questions.count()
            selected_questions = Question.objects.filter(id__in=selected_ids)
            
            for i, question in enumerate(selected_questions):
                PaperQuestion.objects.create(
                    paper=paper,
                    question=question,
                    order=last_order + i + 1,
                    marks=question.marks,
                    section=section
                )
            
            # The calculation method is correct
            paper.total_marks = paper.calculate_total_marks()
            paper.save()
            
            messages.success(request, f'{len(selected_ids)} questions added to the paper!')
            return redirect('quiz:paper_detail', paper.id)
        else:
            messages.error(request, 'Please select at least one question.')
    
    return render(request, 'quiz/paper_add_questions.html', {
        'paper': paper,
        'questions': questions,
        'search_form': search_form
    })

# --- Remaining Views (paper_remove_question, paper_edit, paper_delete) ---
# These views primarily rely on paper_id and question_id and do not directly 
# reference the subject/chapter fields, so they are correct as is.

@login_required
@permission_required('quiz.delete_paperquestion', login_url='profile_update')
def paper_remove_question(request, paper_id, question_id):
    paper = get_object_or_404(QuestionPaper, id=paper_id)
    paper_question = get_object_or_404(PaperQuestion, paper=paper, question_id=question_id)
    
    # Check if user can edit this paper (owner or admin)
    if paper.created_by != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to edit this paper.')
        return redirect('quiz:paper_detail', paper.id)
    
    if request.method == 'POST':
        paper_question.delete()
        
        # Reorder remaining questions
        remaining_questions = paper.paper_questions.order_by('order')
        for i, pq in enumerate(remaining_questions, 1):
            pq.order = i
            pq.save()
        
        # Update total marks
        paper.total_marks = paper.calculate_total_marks()
        paper.save()
        
        messages.success(request, 'Question removed from paper!')
        return redirect('quiz:paper_detail', paper.id)
    
    return render(request, 'quiz/paper_remove_question.html', {
        'paper': paper,
        'paper_question': paper_question
    })

@login_required
@permission_required('quiz.change_questionpaper', login_url='profile_update')
def edit_question_paper(request, paper_id):
    # In a real environment, remove the dummy code above and ensure real imports are used.
    
    question_paper = get_object_or_404(QuestionPaper, pk=paper_id)
    
    # Get organization from request
    organization = getattr(request.user.profile, 'organization_profile', None)
    
    # Optional Security Check: Ensure the user/org has rights to edit
    if (organization and question_paper.organization != organization) or (question_paper.is_published == True and not request.user.is_superuser):
        messages.error(request, "You do not have permission to edit this question paper.")
        return redirect('quiz:paper_list')
    
        
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # --- Update Basic Form Data ---
                question_paper.title = request.POST.get('title')
                new_subject_id = request.POST.get('curriculum_subject')
                question_paper.pattern = request.POST.get('pattern', 'standard')
                
                # Safely update numeric fields, falling back to 0/60 if input is empty or invalid
                question_paper.total_marks = int(request.POST.get('total_marks') or 0)
                question_paper.duration_minutes = int(request.POST.get('duration_minutes') or 60)
                
                question_paper.instructions = request.POST.get('instructions', '')
                
                # --- FIX APPLIED HERE ---
                # The JS creates hidden inputs named 'curriculum_chapters', not 'selectedItemsList'
                selected_chapters = request.POST.getlist('selectedItemsList')

                print("selected_chapters :", selected_chapters)
                
                # --- Validation ---
                if not question_paper.title or not new_subject_id:
                    messages.error(request, "Title and Subject are required fields.")
                    # Ensure redirect path is correct for your environment
                    return redirect('quiz:edit_question_paper', paper_id=paper_id)
                
                # --- Update Subject Node if Changed ---
                # Check if the selected subject ID is different from the existing one
                if not question_paper.curriculum_subject or str(question_paper.curriculum_subject.id) != new_subject_id:
                    # In a real environment, replace TreeNode.objects with your actual ORM call
                    curriculum_subject = get_object_or_404(TreeNode, id=new_subject_id, node_type='subject')
                    question_paper.curriculum_subject = curriculum_subject
                
                question_paper.save() # Save main changes
                
                # --- Update Chapters/Units ---
                if selected_chapters:
                    # In a real environment, replace TreeNode.objects with your actual ORM call
                    chapter_nodes = TreeNode.objects.filter(id__in=selected_chapters)
                    question_paper.curriculum_chapters.set(chapter_nodes)
                else:
                    question_paper.curriculum_chapters.clear() # Clear if none selected
                
                messages.success(request, f"Question paper '{question_paper.title}' updated successfully!")
                # Ensure redirect path is correct for your environment
                return redirect('quiz:paper_list') 
                
        except Exception as e:
            messages.error(request, f"Error updating question paper: {str(e)}")
            # Ensure redirect path is correct for your environment
            return redirect('quiz:edit_question_paper', paper_id=paper_id)
    
    # --- GET request - Prepare data for form pre-filling ---
    # In a real environment, replace TreeNode.objects with your actual ORM call
    root_nodes = TreeNode.objects.filter(
        node_type__in=['board', 'competitive']
    ).order_by('node_type', 'name')
    
    pattern_choices = QuestionPaper.PAPER_PATTERNS
    
    # 1. Get the list of selected chapters (ID, Name, Type) for JS initialization
    initial_chapters_list = list(
        question_paper.curriculum_chapters.all().values('id', 'name', 'node_type')
    )
    
    # 2. Get the full curriculum path (e.g., Board > Class > Subject)
    initial_subject_id = question_paper.curriculum_subject.id if question_paper.curriculum_subject else None
    
    context = {
        'question_paper': question_paper, # The object being edited
        'root_nodes': root_nodes,
        'pattern_choices': pattern_choices,
        'organization': organization,
        
        # Data for JS initialization
        'initial_subject_id': initial_subject_id,
        'initial_chapters_json': json.dumps(initial_chapters_list), # Chapters as a JSON string
    }
    
    return render(request, 'quiz/edit_question_paper.html', context)

@login_required
@permission_required('quiz.delete_questionpaper', login_url='profile_update')
def paper_delete(request, paper_id):
    paper = get_object_or_404(QuestionPaper, id=paper_id)

    if not request.user.is_superuser and paper.is_published == True:
        messages.error(request, 'Question paper cannot be deleted deleted')
        return redirect('quiz:paper_list')
    
    if request.method == 'POST':
        paper.delete()
        messages.success(request, 'Question paper deleted successfully!')
        return redirect('quiz:paper_list')
    
    return render(request, 'quiz/paper_confirm_delete.html', {'paper': paper})

@login_required
@permission_required('quiz.print_questionpaper', login_url='profile_update')
def paper_print(request, paper_id):
    paper = get_object_or_404(QuestionPaper, id=paper_id)
    
    questions_queryset = paper.paper_questions.select_related('question') 
    
    if paper.pattern == 'difficulty_wise':
        # To sort by a custom text order (Easy, Medium, Hard),
        # we need to sort the results in Python memory.
        difficulty_order = {'easy': 1, 'medium': 2, 'hard': 3}
        paper_questions = sorted(
            questions_queryset, 
            key=lambda pq: difficulty_order.get(pq.question.difficulty, 99)
        )
    
    elif paper.pattern == 'section_wise':
        # Sort by subject name and then by chapter name
        paper_questions = questions_queryset.order_by('question__subject__name', 'question__chapter__name')
        
    elif paper.pattern == 'custom':
        paper_questions = questions_queryset.order_by('order')

    elif paper.pattern == 'standard':
        # Sort by question type as requested.
        paper_questions = questions_queryset.order_by('question__question_type')
    
    else: # Fallback for any other undefined patterns
        paper_questions = questions_queryset.order_by('order', 'question__created')
    
    # Print options from GET parameters
    print(' answers : ',request.GET.get('answers'))
    show_answers = request.GET.get('answers', 'false') == 'true'
    show_marks = request.GET.get('marks', 'true') == 'true'
    show_instructions = request.GET.get('instructions', 'true') == 'true'
    group_by_type = request.GET.get('types', 'false') == 'true'

    print('show_answers :',show_answers, 'show_marks',show_marks,'show_instructions',show_instructions,'group_by_type',group_by_type)
    
    
    # Group questions by section or type if requested
    if group_by_type:
        sections = {}
        type_mapping = {
            'fill_blank': 'Fill in the Blanks',
            'true_false': 'True/False Questions',
            'match': 'Match the Following',
            'mcq': 'Multiple Choice Questions',
            'short_answer': 'Short Answer Questions',
            
        }
        question_counter = 1
        for pq in paper_questions:
            section_name = type_mapping.get(pq.question.question_type, 'Other')
            # pq.display_number = question_counter
            if section_name not in sections:
                pq.display_number = 1
                sections[section_name] = [pq]
            else:
                question_counter = sections[section_name][-1].display_number
                pq.display_number = question_counter + 1
                sections[section_name].append(pq)
        # Remove empty sections
        sections = {k: v for k, v in sections.items() if v}
    else:
        question_counter = 1
        for pq in paper_questions:
            pq.display_number = question_counter
            question_counter += 1
        sections = {'All Questions': list(paper_questions)}
    
    return render(request, 'quiz/paper_print.html', {
        'paper': paper,
        'sections': sections,
        'show_answers': show_answers,
        'show_marks': show_marks,
        'show_instructions': show_instructions,
        'group_by_type': group_by_type
    })

# AJAX Views

def get_chapters(request):
    subject_id = request.GET.get('subject_id')
    
    # Initialize an empty queryset
    chapters = [] 
    
    if subject_id:
        try:
            # 🛑 UPDATE: Query the TreeNode model
            # 🛑 Filter by parent_id (the selected subject) and enforce node_type='chapter'
            chapters_queryset = TreeNode.objects.filter(
                parent_id=subject_id, 
            ).order_by('order', 'name')
            
            # Convert queryset to a list of dicts for JSON serialization
            chapters = list(chapters_queryset.values('id', 'name'))
            
        except ValueError:
            # Handle cases where subject_id is not a valid integer
            pass
            
    return JsonResponse({'chapters': chapters})


@login_required
def get_subjects(request):
    """Returns subjects (TreeNode, node_type='subject') for a given board_id."""
    board_id = request.GET.get('board_id')
    subjects = []
    
    if board_id:
        try:
            subjects_queryset = TreeNode.objects.filter(
                parent_id=board_id, 
                node_type__in=['class']
            ).order_by('order', 'name')
            
            subjects = list(subjects_queryset.values('id', 'name'))
            
        except Exception as e:
            print("Invalid board_id:", board_id, "Error:", e)
            pass # board_id was invalid
    print("Returning subjects:", subjects)
    return JsonResponse({'subjects': subjects})




# ---------- Helper: resolve curriculum nodes ----------
def get_or_create_curriculum_nodes(board_name, class_name, subject_name, chapter_name=None, section_name=None):
    """Auto-create or fetch the full curriculum path."""
    board, _ = TreeNode.objects.get_or_create(name=board_name, node_type='board', parent=None)
    class_node, _ = TreeNode.objects.get_or_create(name=class_name, node_type='class', parent=board)
    subject, _ = TreeNode.objects.get_or_create(name=subject_name, node_type='subject', parent=class_node)

    chapter = None
    if chapter_name:
        chapter, _ = TreeNode.objects.get_or_create(name=chapter_name, node_type='chapter', parent=subject)

    section = None
    if section_name:
        parent = chapter or subject
        section, _ = TreeNode.objects.get_or_create(name=section_name, node_type='section', parent=parent)

    return board, class_node, subject, chapter, section


@login_required
@permission_required('quiz.upload_question_csv',login_url='profile_update')
def bulk_upload_questions(request):
    """
    Upload mixed question types via CSV.
    Expected CSV headers:
    question_type,question_text,options,correct_answer,pairs,board,class_name,subject,chapter,section,difficulty,marks,explanation,max_words,is_case_sensitive

    Notes:
    - MCQ → options separated by ';' | correct_answer is one or more exact matches.
    - Match → pairs like Left:Right;Left:Right;...
    - FillBlank → correct_answer text
    - TrueFalse → correct_answer True/False
    - ShortAnswer → correct_answer (sample answer)
    """
    if request.method == 'POST':
        csv_file = request.FILES.get('file')
        if not csv_file:
            messages.error(request, "Please attach a CSV file.")
            return redirect('bulk_upload_questions')

        # ✅ Save a copy of uploaded file for audit
        try:
            timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
            username = request.user.username.replace(" ", "_")
            upload_dir = os.path.join(settings.MEDIA_ROOT, "question_uploads")
            os.makedirs(upload_dir, exist_ok=True)

            file_path = os.path.join(upload_dir, f"{username}_{timestamp}.csv")
            with default_storage.open(file_path, 'wb+') as dest:
                for chunk in csv_file.chunks():
                    dest.write(chunk)

            # Optionally store record in DB (we'll add a model below)
            from .models import QuestionUploadLog
            QuestionUploadLog.objects.create(
                user=request.user,
                file_name=os.path.basename(file_path),
                file_path=os.path.relpath(file_path, settings.MEDIA_ROOT),
                uploaded_at=timezone.now(),
            )

        except Exception as e:
            messages.warning(request, f"File could not be saved: {e}")

        try:
            data = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(data))
        except Exception as e:
            messages.error(request, f"Error reading CSV: {e}")
            return redirect('bulk_upload_questions')

        total, successes = 0, 0
        failures = []

        for rownum, row in enumerate(reader, start=1):
            total += 1
            try:
                with transaction.atomic():
                    # Normalize fields
                    board_name = row.get('board', '').strip()
                    class_name = row.get('class_name', '').strip()
                    subject_name = row.get('subject', '').strip()
                    chapter_name = row.get('chapter', '').strip()
                    section_name = row.get('section', '').strip()

                    qtype = row.get('question_type', '').strip().lower()
                    q_text = row.get('question_text', '').strip()
                    difficulty = row.get('difficulty', 'medium').strip()

                    try:
                        marks = int(row.get('marks', 1))
                    except ValueError:
                        marks = 1

                    board, class_node, subject, chapter, section = get_or_create_curriculum_nodes(
                        board_name, class_name, subject_name, chapter_name, section_name
                    )

                    question = Question.objects.create(
                        question_type=qtype,
                        curriculum_board=board,
                        curriculum_subject=subject,
                        curriculum_chapter=section or chapter,
                        question_text=q_text,
                        difficulty=difficulty,
                        marks=marks,
                        created_by=request.user,
                    )

                    # Handle each type
                    if qtype == 'mcq':
                        options_raw = row.get('options', '') or ''
                        correct_raw = row.get('correct_answer', '') or ''
                        opts = [o.strip() for o in options_raw.split(';') if o.strip()]
                        correct_list = [c.strip().lower() for c in correct_raw.split(';') if c.strip()]
                        for i, opt in enumerate(opts, start=1):
                            is_correct = opt.strip().lower() in correct_list
                            MCQOption.objects.create(question=question, option_text=opt, is_correct=is_correct, order=i)

                    elif qtype == 'match':
                        pairs_raw = row.get('pairs', '') or ''
                        pairs = [p.strip() for p in pairs_raw.split(';') if p.strip()]
                        for i, pair in enumerate(pairs, start=1):
                            if ':' in pair:
                                left, right = pair.split(':', 1)
                                MatchPair.objects.create(question=question, left_item=left.strip(), right_item=right.strip(), order=i)

                    elif qtype in ['fill_blank', 'fill', 'fillblank']:
                        correct = (row.get('correct_answer') or '').strip()
                        is_case = str(row.get('is_case_sensitive', 'False')).lower() in ['true', '1', 'yes']
                        if correct:
                            FillBlankAnswer.objects.create(question=question, correct_answer=correct, is_case_sensitive=is_case)

                    elif qtype in ['true_false', 'tf']:
                        val = (row.get('correct_answer') or '').strip().lower()
                        if val not in ['true', 'false']:
                            raise ValueError("True/False question must have correct_answer 'True' or 'False'")
                        correct_bool = (val == 'true')
                        explanation = (row.get('explanation') or '').strip()
                        TrueFalseAnswer.objects.create(question=question, correct_answer=correct_bool, explanation=explanation)

                    elif qtype in ['short_answer', 'short']:
                        sample = (row.get('correct_answer') or row.get('sample_answer') or '').strip()
                        max_words = int(row.get('max_words') or 50)
                        ShortAnswer.objects.create(question=question, sample_answer=sample, max_words=max_words)

                    else:
                        question.delete()
                        raise ValueError(f"Unsupported question_type '{qtype}'")

                    successes += 1

            except Exception as e:
                tb = traceback.format_exc()
                failures.append({'row': rownum, 'error': str(e), 'trace': tb})

        messages.success(request, f"Processed {total} rows. Added: {successes}. Failed: {len(failures)}.")
        for f in failures[:5]:
            messages.error(request, f"Row {f['row']}: {f['error']}")

        return redirect('quiz:bulk_upload_questions')

    boards = TreeNode.objects.filter(node_type='board').order_by('name')
    return render(request, 'quiz/bulk_upload_questions.html', {'boards': boards})



@login_required
@permission_required('quiz.add_paperquestion', login_url='profile_update')
def paper_add_random_questions(request, paper_id):
    """
    Add random questions to paper based on pattern, marks, and chapters.
    
    Key Changes:
    - Stops automatically saving the calculated total marks to paper.total_marks.
    - Issues a warning if the calculated total marks change, requiring manual confirmation.
    """
    
    paper = get_object_or_404(QuestionPaper, id=paper_id)
    
    # Check if user can edit this paper
    if paper.created_by != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to edit this paper.')
        return redirect('quiz:paper_detail', paper.id)
    
    # Get existing question IDs to avoid duplicates
    existing_question_ids = paper.paper_questions.values_list('question_id', flat=True)
    
    # Calculate current marks before any additions
    current_marks_pre_add = paper.calculate_total_marks()
    
    if request.method == 'POST':
        try:
            # --- POST LOGIC FOR TARGET MARKS DEFAULT (Kept for consistency) ---
            target_marks_default = paper.total_marks if paper.total_marks is not None else 100
            
            if hasattr(paper, 'max_marks') and paper.max_marks is not None:
                # Calculate the remaining marks needed
                remaining_marks = paper.max_marks - current_marks_pre_add
                # Use the remaining needed marks, or 20 as a minimum addition
                target_marks_default = max(remaining_marks, 20) 
            
            # Get criteria from form
            target_marks = int(request.POST.get('target_marks', target_marks_default))
            distribution_type = request.POST.get('distribution_type', 'balanced')
            chapter_distribution = request.POST.get('chapter_distribution', 'proportional')
            # --- END POST LOGIC FOR TARGET MARKS DEFAULT ---

            # Get and filter available questions (Queries remain the same)
            available_questions = Question.objects.exclude(id__in=existing_question_ids)
            available_questions = available_questions.filter(
                curriculum_subject=paper.curriculum_subject
            )
            if paper.curriculum_chapters.exists():
                available_questions = available_questions.filter(
                    curriculum_chapter__in=paper.curriculum_chapters.all()
                )
            
            # Select questions
            selected_questions = select_questions_by_pattern_and_chapters(
                available_questions, paper.pattern, paper.curriculum_chapters.all(), 
                target_marks, distribution_type, chapter_distribution
            )
            
            if not selected_questions:
                messages.warning(request, 'No questions found matching the criteria.')
                return redirect('quiz:paper_add_random_questions', paper.id)
            
            # Add questions to paper within a transaction
            last_order = paper.paper_questions.count()
            total_added_marks = 0
            
            with transaction.atomic():
                for i, question_data in enumerate(selected_questions):
                    question = question_data['question']
                    PaperQuestion.objects.create(
                        paper=paper,
                        question=question,
                        order=last_order + i + 1,
                        marks=question.marks,
                        section=question_data.get('section', '')
                    )
                    total_added_marks += question.marks
            
            # Calculate the new total marks of the content (after additions)
            current_marks_post_add = paper.calculate_total_marks()
            
            # --- CONFIRMATION LOGIC ---
            
            # 1. Successful Addition Message
            messages.success(request, 
                f'Added {len(selected_questions)} questions totaling {total_added_marks} marks!'
            )

            # 2. Check if the calculated marks now differ from the intended/cached marks (paper.total_marks)
            if current_marks_post_add != paper.total_marks:
                messages.warning(request, 
                    f"⚠️ **Marks Discrepancy Alert!** The paper content now totals **{current_marks_post_add}** marks. "
                    f"The paper's intended max marks (`paper.total_marks`) is still set at **{paper.total_marks}**. "
                    f"The paper's intended max marks have **NOT** been automatically updated. Please review and manually change them if needed."
                )

            # 3. DO NOT UPDATE paper.total_marks or call paper.save() here.
            
            return redirect('quiz:paper_detail', paper.id)
            
        except Exception as e:
            messages.error(request, f'Error adding random questions: {str(e)}')
            return redirect('quiz:paper_add_random_questions', paper.id)
    
    # --- GET REQUEST LOGIC ---
    
    # Use the pre-calculated marks for display and comparison
    current_marks = current_marks_pre_add 

    # --- Start Issue 1 & 2 Logic (Display side) ---
    target_marks_default = paper.total_marks if paper.total_marks is not None else 100

    if hasattr(paper, 'max_marks') and paper.max_marks is not None:
        max_marks = paper.max_marks
        
        # Issue 2: Check for marks discrepancy
        if current_marks != max_marks:
            # Calculate how many marks are left to reach the intended total
            remaining_marks = max_marks - current_marks
            
            # Alert the user about the current state on the GET request
            messages.warning(request, 
                f"Paper Marks Alert: The current total marks of the content are {current_marks}, "
                f"but the intended max marks are {max_marks}. "
                f"You need {'+' if remaining_marks > 0 else ''}{remaining_marks} marks "
                f"to meet the intended target."
            )
            
            # Issue 1: Set default to the remaining marks, or 20 if it's already over/meets target
            target_marks_default = max(remaining_marks, 20) if max_marks > current_marks else 20
        else:
            # If marks match, suggest a small addition just in case (Issue 1 refinement)
            target_marks_default = 20
    else:
        messages.info(request, "The paper's intended max marks are not set, defaulting 'Target Marks' to 100.")
    # --- End Issue 1 & 2 Logic ---

    # Get available question count
    available_question_count = Question.objects.exclude(
        id__in=existing_question_ids
    ).filter(
        curriculum_subject=paper.curriculum_subject
    )
    if paper.curriculum_chapters.exists():
        available_question_count = available_question_count.filter(
            curriculum_chapter__in=paper.curriculum_chapters.all()
        )
    available_question_count = available_question_count.count()
    
    context = {
        'paper': paper,
        'current_marks': current_marks,
        'available_question_count': available_question_count,
        'pattern_choices': QuestionPaper.PAPER_PATTERNS,
        'target_marks_default': target_marks_default, # Pass to template for form's initial value
    }
    
    return render(request, 'quiz/paper_add_random_questions.html', context)


def select_questions_by_pattern_and_chapters(questions_queryset, pattern, selected_chapters, 
                                           target_marks, distribution_type, chapter_distribution):
    """
    Select random questions considering pattern, marks, and chapter distribution
    """
    questions = list(questions_queryset)
    if not questions:
        return []
    
    selected_questions = []
    
    if pattern == 'difficulty_wise':
        selected_questions = select_by_difficulty_and_chapters(
            questions, selected_chapters, target_marks, distribution_type, chapter_distribution
        )
    
    elif pattern == 'section_wise':
        selected_questions = select_by_sections_with_chapters(
            questions, selected_chapters, target_marks, distribution_type, chapter_distribution
        )
    
    elif pattern == 'standard':
        selected_questions = select_by_question_type_and_chapters(
            questions, selected_chapters, target_marks, distribution_type, chapter_distribution
        )
    
    else:  # custom or fallback
        selected_questions = select_random_balanced_with_chapters(
            questions, selected_chapters, target_marks, chapter_distribution
        )
    
    return selected_questions


def select_by_difficulty_and_chapters(questions, selected_chapters, target_marks, 
                                    distribution_type, chapter_distribution):
    """Select questions with balanced difficulty distribution across chapters"""
    # Group questions by chapter first, then by difficulty
    chapter_groups = group_questions_by_chapter(questions, selected_chapters)
    
    selected = []
    current_marks = 0
    
    # Determine marks distribution per chapter
    chapter_marks = distribute_marks_to_chapters(
        chapter_groups, target_marks, chapter_distribution
    )
    
    # Distribution ratios for difficulties
    if distribution_type == 'balanced':
        difficulty_ratios = {'easy': 0.4, 'medium': 0.4, 'hard': 0.2}
    elif distribution_type == 'exam_focused':
        difficulty_ratios = {'easy': 0.3, 'medium': 0.5, 'hard': 0.2}
    else:  # progressive
        difficulty_ratios = {'easy': 0.5, 'medium': 0.3, 'hard': 0.2}
    
    # Select questions from each chapter
    for chapter_id, chapter_data in chapter_groups.items():
        chapter_marks_target = chapter_marks.get(chapter_id, 0)
        if chapter_marks_target == 0:
            continue
            
        # Distribute marks across difficulties for this chapter
        difficulty_marks = {
            'easy': int(chapter_marks_target * difficulty_ratios['easy']),
            'medium': int(chapter_marks_target * difficulty_ratios['medium']),
            'hard': int(chapter_marks_target * difficulty_ratios['hard'])
        }
        
        # Select from each difficulty level in this chapter
        for difficulty in ['easy', 'medium', 'hard']:
            difficulty_questions = [q for q in chapter_data['questions'] if q.difficulty == difficulty]
            selected_from_difficulty = select_questions_up_to_marks(
                difficulty_questions, difficulty_marks[difficulty]
            )
            
            for question in selected_from_difficulty:
                if current_marks + question.marks <= target_marks:
                    selected.append({
                        'question': question,
                        'section': f"{chapter_data['chapter'].name} - {difficulty.capitalize()}"
                    })
                    current_marks += question.marks
    
    return selected


def select_by_sections_with_chapters(questions, selected_chapters, target_marks, 
                                   distribution_type, chapter_distribution):
    """Select questions grouped by chapters with intelligent distribution"""
    chapter_groups = group_questions_by_chapter(questions, selected_chapters)
    
    selected = []
    current_marks = 0
    
    # Distribute marks among chapters
    chapter_marks = distribute_marks_to_chapters(
        chapter_groups, target_marks, chapter_distribution
    )
    
    # Select questions from each chapter
    for chapter_id, chapter_data in chapter_groups.items():
        chapter_marks_target = chapter_marks.get(chapter_id, 0)
        if chapter_marks_target == 0:
            continue
            
        chapter_questions = chapter_data['questions']
        selected_from_chapter = select_questions_up_to_marks(
            chapter_questions, chapter_marks_target
        )
        
        for question in selected_from_chapter:
            if current_marks + question.marks <= target_marks:
                selected.append({
                    'question': question,
                    'section': chapter_data['chapter'].name
                })
                current_marks += question.marks
    
    return selected


def select_by_question_type_and_chapters(questions, selected_chapters, target_marks, 
                                       distribution_type, chapter_distribution):
    """Select questions with balanced type distribution across chapters"""
    chapter_groups = group_questions_by_chapter(questions, selected_chapters)
    
    selected = []
    current_marks = 0
    
    # Distribute marks among chapters
    chapter_marks = distribute_marks_to_chapters(
        chapter_groups, target_marks, chapter_distribution
    )
    
    # Question type distribution
    type_ratios = {
        'mcq': 0.4,
        'fill_blank': 0.2,
        'short_answer': 0.2,
        'true_false': 0.1,
        'match': 0.1
    }
    
    # Select from each chapter
    for chapter_id, chapter_data in chapter_groups.items():
        chapter_marks_target = chapter_marks.get(chapter_id, 0)
        if chapter_marks_target == 0:
            continue
            
        # Distribute chapter marks across question types
        for q_type, ratio in type_ratios.items():
            type_marks_target = int(chapter_marks_target * ratio)
            type_questions = [q for q in chapter_data['questions'] if q.question_type == q_type]
            
            selected_from_type = select_questions_up_to_marks(type_questions, type_marks_target)
            
            for question in selected_from_type:
                if current_marks + question.marks <= target_marks:
                    selected.append({
                        'question': question,
                        'section': f"{chapter_data['chapter'].name} - {question.get_question_type_display()}"
                    })
                    current_marks += question.marks
    
    return selected


def group_questions_by_chapter(questions, selected_chapters):
    """Group questions by their chapters"""
    chapter_groups = {}
    
    # If specific chapters are selected, only use those
    chapters_to_use = selected_chapters if selected_chapters else set()
    
    for question in questions:
        chapter = question.curriculum_chapter
        if chapter and (not selected_chapters or chapter in selected_chapters):
            if chapter.id not in chapter_groups:
                chapter_groups[chapter.id] = {
                    'chapter': chapter,
                    'questions': [],
                    'total_marks_available': 0
                }
            chapter_groups[chapter.id]['questions'].append(question)
            chapter_groups[chapter.id]['total_marks_available'] += question.marks
    
    return chapter_groups


def distribute_marks_to_chapters(chapter_groups, total_marks, distribution_type):
    """Distribute total marks among chapters based on distribution type"""
    if not chapter_groups:
        return {}
    
    chapter_marks = {}
    
    if distribution_type == 'equal':
        # Equal marks per chapter
        marks_per_chapter = total_marks // len(chapter_groups)
        for chapter_id in chapter_groups:
            chapter_marks[chapter_id] = marks_per_chapter
    
    elif distribution_type == 'proportional':
        # Proportional to available questions in each chapter
        total_available_marks = sum(
            data['total_marks_available'] for data in chapter_groups.values()
        )
        
        if total_available_marks > 0:
            for chapter_id, data in chapter_groups.items():
                proportion = data['total_marks_available'] / total_available_marks
                chapter_marks[chapter_id] = int(total_marks * proportion)
        else:
            # Fallback to equal distribution
            marks_per_chapter = total_marks // len(chapter_groups)
            for chapter_id in chapter_groups:
                chapter_marks[chapter_id] = marks_per_chapter
    
    else:  # weighted
        # Weight by chapter importance (you can customize this)
        for chapter_id, data in chapter_groups.items():
            # Simple weighting: more questions = higher weight
            weight = min(len(data['questions']) / 10, 1.0)  # Cap at 1.0
            chapter_marks[chapter_id] = int(total_marks * weight / len(chapter_groups))
    
    # Ensure we don't exceed total marks
    allocated_marks = sum(chapter_marks.values())
    if allocated_marks > total_marks:
        # Reduce proportionally
        ratio = total_marks / allocated_marks
        for chapter_id in chapter_marks:
            chapter_marks[chapter_id] = int(chapter_marks[chapter_id] * ratio)
    
    return chapter_marks


def select_random_balanced_with_chapters(questions, selected_chapters, target_marks, chapter_distribution):
    """Fallback random selection with chapter consideration"""
    chapter_groups = group_questions_by_chapter(questions, selected_chapters)
    
    selected = []
    current_marks = 0
    
    # Distribute marks among chapters
    chapter_marks = distribute_marks_to_chapters(
        chapter_groups, target_marks, chapter_distribution
    )
    
    # Select from each chapter
    for chapter_id, chapter_data in chapter_groups.items():
        chapter_marks_target = chapter_marks.get(chapter_id, 0)
        if chapter_marks_target == 0:
            continue
            
        chapter_questions = chapter_data['questions']
        selected_from_chapter = select_questions_up_to_marks(
            chapter_questions, chapter_marks_target
        )
        
        for question in selected_from_chapter:
            if current_marks + question.marks <= target_marks:
                selected.append({
                    'question': question,
                    'section': chapter_data['chapter'].name
                })
                current_marks += question.marks
    
    return selected


def select_questions_up_to_marks(question_list, target_marks):
    """Select random questions up to target marks from a list"""
    if not question_list:
        return []
    
    import random
    random.shuffle(question_list)
    
    selected = []
    current_marks = 0
    
    for question in question_list:
        if current_marks + question.marks <= target_marks:
            selected.append(question)
            current_marks += question.marks
    
    return selected



@login_required
@permission_required('quiz.change_paperquestion', login_url='profile_update')
def paper_swap_question_select(request, paper_id, old_question_id):
    """
    Shows a list of potential replacement questions for a specific question 
    in a paper. Candidates must match the marks, type, subject, and chapter 
    of the question being replaced, and must not already be in the paper.
    """
    
    paper = get_object_or_404(QuestionPaper, id=paper_id)
    
    # 1. Get the Question being swapped out
    try:
        old_pq = PaperQuestion.objects.select_related('question').get(
            paper=paper, question_id=old_question_id
        )
        old_question = old_pq.question
    except PaperQuestion.DoesNotExist:
        messages.error(request, 'The question you tried to swap is not in this paper.')
        return redirect('quiz:paper_detail', paper.id)

    # 2. Check permissions
    if paper.created_by != request.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to edit this paper.')
        return redirect('quiz:paper_detail', paper.id)

    # 3. Define the criteria for the replacement question
    target_marks = old_question.marks
    target_type = old_question.question_type
    target_chapter = old_question.curriculum_chapter # Can be None

    # 4. Get existing question IDs to exclude duplicates
    existing_question_ids = list(paper.paper_questions.values_list('question_id', flat=True))
    
    # 5. Build the query for candidate replacement questions
    
    # Base filter: Exclude existing questions, match subject, marks, and type
    candidates_queryset = Question.objects.exclude(id__in=existing_question_ids).filter(
        curriculum_subject=paper.curriculum_subject,
        marks=target_marks,
        question_type=target_type
    )

    # Chapter Filter: If the old question belongs to a specific chapter, limit candidates to that chapter.
    if target_chapter:
        candidates_queryset = candidates_queryset.filter(curriculum_chapter=target_chapter)
        chapter_criteria_text = f"Chapter: {target_chapter.name}"
    else:
        # If the old question had no chapter, we look for other chapterless questions or questions from any chapter in the subject
        # For simplicity, we keep it broad if no chapter was set on the original question.
        chapter_criteria_text = "Chapter: Any (or None)"


    # Fetch the candidates and limit the list for display purposes (e.g., 50)
    candidate_questions = candidates_queryset.order_by('?')[:50]
    
    # 6. Prepare context
    criteria = {
        'Marks': target_marks,
        'Type': old_question.get_question_type_display(),
        'Subject': paper.curriculum_subject.name,
        'Chapter': chapter_criteria_text,
    }

    context = {
        'paper': paper,
        'old_pq': old_pq,
        'old_question': old_question,
        'criteria': criteria,
        'candidate_questions': candidate_questions,
        'candidate_count': candidates_queryset.count(), # Total available before display limit
    }
    
    return render(request, 'quiz/paper_swap_question_select.html', context)

# --- PLACEHOLDER FOR NEXT STEP ---

@login_required
@permission_required('quiz.change_paperquestion', login_url='profile_update')
def paper_swap_question_confirm(request, paper_id, old_question_id, new_question_id):
    """
    View to execute the actual swap of old_question_id with new_question_id.
    This would involve getting the PaperQuestion instance for the old question,
    updating its question FK to point to the new question, and saving it, 
    all within a transaction.
    """
    messages.info(request, "Swap confirmation logic needs to be implemented here!")
    return redirect('quiz:paper_detail', paper_id)