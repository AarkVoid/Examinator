from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import Profile
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required,permission_required
from django.contrib import messages
from .models import Comment,ContactMessage,Message
from .forms import CommentForm, ContactMessageForm, MessageForm,ReplyForm, ContactReplyForm
from taggit.models import Tag
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from accounts.models import User
from saas.models import OrganizationProfile,LicenseGrant
from quiz.models import Question,QuestionPaper,QuestionPaperAttempt
from curritree.models import TreeNode
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from saas.models import LicenseGrant, UsageLimit
from django.db.models import Sum
from datetime import date
from saas.utils import get_licensed_node_ids
from accounts.views import staff_required,superuser_required
# Create your views here. 

@login_required
@staff_required
def home(request):
    # Define time thresholds
    print("Home View Accessed by:", request.user.username)
    one_week_ago = timezone.now() - timedelta(days=7)
    one_month_from_now = timezone.now() + timedelta(days=30)

    # --- Database Statistics Fetching ---
    
    # Core Quiz Stats (Assuming Question, QuestionPaper, QuestionPaperAttempt are imported)
    total_questions = Question.objects.count()
    total_papers = QuestionPaper.objects.count()
    recent_papers = QuestionPaper.objects.select_related('created_by').order_by('-created')[:4]
    total_boards = TreeNode.objects.filter(node_type='board').count()
    total_competitive_exams = TreeNode.objects.filter(node_type='competitive').count()
    total_subjects = TreeNode.objects.filter(node_type='subject').count()
    total_class = TreeNode.objects.filter(node_type='class').count()
    total_chapters = TreeNode.objects.filter(node_type='chapter').count()
    # User Stats (Assuming User is imported via get_user_model())
    total_users = User.objects.count()
    
    # Organization/Licensing Stats (Assuming OrganizationProfile, LicenseGrant are imported)
    total_organizations = OrganizationProfile.objects.count()
    
    # Licenses expiring within the next month
    expiring_licenses_count = LicenseGrant.objects.filter(
        valid_until__gt=timezone.now(), 
        valid_until__lte=one_month_from_now
    ).count()
    
    # Licenses that have already expired
    expired_licenses_count = LicenseGrant.objects.filter(
        valid_until__lt=timezone.now()
    ).count()
    
    # Recently added items (assuming User has 'date_joined' and OrganizationProfile has 'created_at')
    recently_added_users = User.objects.filter(
        date_joined__gte=one_week_ago
    ).order_by('-date_joined')[:5]
    
    recently_added_orgs = OrganizationProfile.objects.filter(
        created_at__gte=one_week_ago
    ).order_by('-created_at')[:3]
    
    # Users by Role (Group aggregation)
    # This query counts users per group. Note: Django's User model has a 'groups' M2M field.
    # The keys in the final dict will be the Group names.
    user_role_counts = User.objects.exclude(groups__isnull=True).values_list(
        'groups__name'
    ).annotate(count=Count('pk')).order_by('-count')
    
    # Transforming the queryset result into the required dictionary format: {RoleName: Count}
    user_roles_data = {item[0]: item[1] for item in user_role_counts}
    
    # If using the mock environment, use the mock output directly
    # user_roles_data = {item['group__name']: item['count'] for item in User.objects.values_list('groups__name', flat=True).annotate(count=Count('pk'))} 
    
    # --- Final Context ---
    context = {
        'total_questions': total_questions,
        'total_papers': total_papers,
        'recent_papers': recent_papers,
        
        'total_users': total_users,
        'recently_added_users': recently_added_users,
        'user_roles_data': user_roles_data,
        
        'total_organizations': total_organizations,
        'expiring_licenses_count': expiring_licenses_count,
        'expired_licenses_count': expired_licenses_count,
        'recently_added_orgs': recently_added_orgs,


        'total_boards': total_boards,
        'total_competitive_exams': total_competitive_exams,
        'total_subjects': total_subjects,
        'total_class': total_class,
        'total_chapters': total_chapters,
        
        'request': request
    }
    
    return render(request, 'home.html', context)







@login_required
def organization_home(request):
    """
    Dedicated dashboard for Organization Admins and Superusers to easily navigate
    to all management areas of the application, now with a License & Usage tab.
    """
    
    organization = getattr(request.user.profile, 'organization_profile', None)
    is_org_admin = organization is not None

    # Check for authorization: Must be Superuser OR Organization Admin
    if not request.user.is_superuser and not is_org_admin:
        return HttpResponseForbidden("You do not have permission to access the Administration Hub.")

    # --- Data Fetching ---
    org_metrics = {}
    license_grants = LicenseGrant.objects.none()
    usage_limit = None
    remaining_papers = 0
    total_max_papers = 0
    current_papers_count = 0
    
    # New draft paper metrics
    current_draft_papers_count = 0
    remaining_draft_papers = 0
    
    # Curriculum usage data
    curriculum_usage = []
    subject_usage = []

    if organization:
        # 1. Fetch standard organization metrics
        current_papers = QuestionPaper.objects.filter(organization=organization)
        current_papers_count = current_papers.count()
        latest_papers = current_papers.order_by('-created')[:5]
        # Fetch current draft paper count
        current_draft_papers = QuestionPaper.objects.filter(organization=organization, is_published=False)
        current_draft_papers_count = current_draft_papers.count()

        current_questions = Question.objects.filter(organization=organization)
        current_questions_count = current_questions.count()
        latest_questions = current_questions.order_by('-created')[:5]

        org_metrics = {
            'total_org_users': User.objects.filter(profile__organization_profile=organization).count(),
            'total_org_questions': current_questions_count,
            'current_papers_count': current_papers_count,
            'current_draft_papers_count': current_draft_papers_count, # Added for metric card
        }
        
        # 2. Fetch License & Usage Data
        today = date.today()
    
        license_grants = organization.license_grants.filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
        try:
            usage_limit = UsageLimit.objects.get(organization_profile=organization)
        except UsageLimit.DoesNotExist:
            usage_limit = None # Handle case where usage limit might not be set

        # 3. Calculate Remaining Question Papers (Total)
        total_max_papers = license_grants.filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=today)
        ).aggregate(total=Sum('max_question_papers'))['total'] or 0
        remaining_papers = total_max_papers - current_papers_count
        
        # 4. Calculate Remaining Draft Papers
        if usage_limit:
            max_drafts = usage_limit.max_question_papers_drafts
            remaining_draft_papers = max_drafts - current_draft_papers_count
        else:
            max_drafts = 0
            remaining_draft_papers = 0

        # 5. Calculate Curriculum Usage in Papers AND Questions
        # Get all papers and questions for this organization
        all_papers = QuestionPaper.objects.filter(organization=organization)
        all_questions = Question.objects.filter(organization=organization)
        
        # Subject Usage Analysis
        subject_usage_data = {}
        for paper in all_papers:
            subject = paper.curriculum_subject
            if subject:
                subject_id = subject.id
                if subject_id not in subject_usage_data:
                    subject_usage_data[subject_id] = {
                        'subject': subject,
                        'paper_count': 0,
                        'published_count': 0,
                        'draft_count': 0,
                        'question_count': 0  # Initialize question count
                    }
                subject_usage_data[subject_id]['paper_count'] += 1
                if paper.is_published:
                    subject_usage_data[subject_id]['published_count'] += 1
                else:
                    subject_usage_data[subject_id]['draft_count'] += 1
        
        # Count questions per subject
        for question in all_questions:
            # Assuming Question model has curriculum_nodes or similar field
            # Adjust this based on your actual Question model structure
            if hasattr(question, 'curriculum_nodes') and question.curriculum_nodes.exists():
                for node in question.curriculum_nodes.all():
                    # Find the subject (root) of this node
                    subject_node = node
                    while subject_node.parent is not None:
                        subject_node = subject_node.parent
                    
                    # If this subject is in our usage data, count the question
                    for subject_data in subject_usage_data.values():
                        if subject_data['subject'].id == subject_node.id:
                            subject_data['question_count'] += 1
                            break
        
        subject_usage = list(subject_usage_data.values())
        
        # Chapter Usage Analysis
        chapter_usage_data = {}
        for paper in all_papers:
            # Count chapters used in this paper
            chapters = paper.curriculum_chapters.all()
            for chapter in chapters:
                chapter_id = chapter.id
                if chapter_id not in chapter_usage_data:
                    chapter_usage_data[chapter_id] = {
                        'chapter': chapter,
                        'paper_count': 0,
                        'published_count': 0,
                        'draft_count': 0,
                        'question_count': 0,  # Initialize question count
                        'subject': chapter.parent.name if chapter.parent else "No Subject"
                    }
                chapter_usage_data[chapter_id]['paper_count'] += 1
                if paper.is_published:
                    chapter_usage_data[chapter_id]['published_count'] += 1
                else:
                    chapter_usage_data[chapter_id]['draft_count'] += 1
        
        # Count questions per chapter
        for question in all_questions:
            # Assuming Question model has curriculum_nodes or similar field
            # Adjust this based on your actual Question model structure
            if hasattr(question, 'curriculum_nodes') and question.curriculum_nodes.exists():
                for node in question.curriculum_nodes.all():
                    chapter_id = node.id
                    if chapter_id in chapter_usage_data:
                        chapter_usage_data[chapter_id]['question_count'] += 1
        
        curriculum_usage = list(chapter_usage_data.values())
        
        # Sort by paper count (descending)
        subject_usage.sort(key=lambda x: x['paper_count'], reverse=True)
        curriculum_usage.sort(key=lambda x: x['paper_count'], reverse=True)

        # 6. Total question count for the organization
        total_question_count = all_questions.count()

    # 7. Context Construction
    context = {
        'organization': organization,
        'is_superuser': request.user.is_superuser,
        'org_pk': organization.pk if organization else None,

        'latest_questions': latest_questions,
        'latest_papers': latest_papers,
        
        # Data for Admin Hub Tab
        'org_metrics': org_metrics, 
        
        # Data for License & Usage Tab
        'license_grants': license_grants,
        'usage_limit': usage_limit,
        'remaining_papers': remaining_papers,
        'total_max_papers': total_max_papers,
        'current_papers_count': current_papers_count,
        
        # New Draft Metrics
        'current_draft_papers_count': current_draft_papers_count,
        'remaining_draft_papers': remaining_draft_papers,
        
        # Curriculum Usage Data
        'subject_usage': subject_usage,
        'curriculum_usage': curriculum_usage,
        'total_question_count': total_question_count,

        # Get current tab from URL query, default to 'hub'
        'current_tab': request.GET.get('tab', 'hub') 
    }
    
    # Render the updated hub page
    return render(request, 'organization_home.html', context)



@login_required
@permission_required('Games.view_game', raise_exception=True)
def TakeTest(request):
    user = request.user
    is_student = user.role == 'student'
    quizzes = None # Will only be populated directly for students
    organized_data = {}
    if is_student:
        try:
            student_profile = user.profile
            required_fields = [
                student_profile.class_field,
                student_profile.board,
                student_profile.institute,
            ]

            if any(field is None for field in required_fields) :
                messages.error(request, ' kindly update the all the profile fields') 
                print("student_profile.class_field :",student_profile.class_field)

                return redirect('profile_update') 
            # Filter quizzes based on the student's assigned class and board
            subjects_with_quizzes = Subject.objects.filter(
                # CORRECTED: Use student_class, not class_field
                Q(student_class=student_profile.class_field)
            ).prefetch_related(
                'quizset_set',          # Prefetch the quiz sets
                'quizset_set__tags',    # Prefetch tags related to QuizSet
                'quizset_set__institution', # Prefetch the institution related to QuizSet
                'quizset_set__user'     # Prefetch the user related to QuizSet
            ).distinct().order_by(
                'student_class__board__name', 'student_class__name', 'name'
            )
            
            for subject in subjects_with_quizzes:
                class_name = str(subject.student_class.name) # Get the string representation of the class

                # --- DEBUGGING / CORRECT ACCESS ---
                print(f"\n--- Subject: {subject.name} (ID: {subject.id}) ---")
                
                # CORRECT WAY TO SEE RELATED QUIZZES FOR THIS SUBJECT:
                # Iterate over the manager or convert it to a list
                all_quizzes_for_this_subject = subject.quizset_set.all()
                print(f"All quizzes directly linked to '{subject.name}': {all_quizzes_for_this_subject.count()}")
                for quiz in all_quizzes_for_this_subject:
                    print(f"  - Quiz: {quiz.test_name} (ID: {quiz.id}), Institution: {quiz.institution.name}")
                
                # --- Original Logic Continuation ---
                if class_name not in organized_data:
                    organized_data[class_name] = []

                # CORRECTED: Use student_profile.institution
                relevant_quizzes = subject.quizset_set.filter(
                    institution=student_profile.institute
                ).select_related('user', 'institution').order_by('test_name')

                print(f"Relevant quizzes for student's institution ({student_profile.institute.name}): {relevant_quizzes.count()}")
                for quiz in relevant_quizzes:
                    print(f"  - Filtered Quiz: {quiz.test_name}, User: {quiz.user.username}")


                # NEW/CORRECTED: Apply tag filtering if tag_ids are provided
                tag_ids_filter = request.GET.getlist('tag_ids')
                filtered_quizzes_after_tags = relevant_quizzes # Start with already institution-filtered quizzes
                if tag_ids_filter:
                    for tag_id in tag_ids_filter:
                        filtered_quizzes_after_tags = filtered_quizzes_after_tags.filter(tags__id=tag_id)
                    filtered_quizzes_after_tags = filtered_quizzes_after_tags.distinct()

                print(f"Quizzes after tag filter ({tag_ids_filter}): {filtered_quizzes_after_tags.count()}")
                for quiz in filtered_quizzes_after_tags:
                    print(f"  - Final Quiz: {quiz.test_name}, Tags: {[t.name for t in quiz.tags.all()]}")


                # CORRECTED: Build the dictionary structure as discussed for JS compatibility
                quizzes_data_for_subject = []
                for quiz in filtered_quizzes_after_tags: # Use the final filtered_quizzes
                    quizzes_data_for_subject.append({
                        'id': quiz.id,
                        'test_name': quiz.test_name,
                        'description': quiz.description,
                        'subject': quiz.subject.name, # Assuming quiz.subject is the subject object
                        'user': quiz.user.username,
                        'institution': quiz.institution.name,
                        'tags': [tag.name for tag in quiz.tags.all()]
                    })
                
                # NEW/CORRECTED: Collect all unique tags available for THIS subject's quizzes
                # These should be tags from the *relevant_quizzes_base* (before tag filtering is applied)
                # so the student sees all tags that exist for quizzes they CAN access.
                all_tags_for_subject_quizzes = Tag.objects.filter(
                    quizset__subject=subject,
                    quizset__institution=student_profile.institute # Only tags from quizzes student can access
                ).distinct().values('id', 'name').order_by('name')


                organized_data[class_name].append({
                    'subject': subject.name,      # Pass subject name
                    'id': subject.id,             # Pass subject ID for JS filtering
                    'quizzes': quizzes_data_for_subject,
                    'available_tags': list(all_tags_for_subject_quizzes),
                })
            
            for class_name in organized_data:
                organized_data[class_name].sort(key=lambda x: x['subject'])
        except Profile.DoesNotExist:
            subjects_with_quizzes = Subject.objects.none() # No quizzes if no profile
        
        context = {'organized_data': organized_data, 'is_student': is_student, 'request':request, }

    if (user.role == 'teacher' or user.role == 'admin') and not user.is_superuser:
        admin_profile = user.profile
        required_fields = [
            admin_profile.board,
            admin_profile.institute,
        ]

        if any(field is None for field in required_fields) and request.user.profile.institute.name != 'Global':
            messages.error(request, 'Kindly update all the profile fields') 
            return redirect('profile_update') 
        
        boards = Board.objects.all()
        if user.profile.board:
            class_s = StudentClass.objects.filter(board=user.profile.board.id)
        else:
            class_s = StudentClass.objects.none()
        context = {'boards': boards, 'classes': class_s, 'request': request}

    if user.is_superuser or user.role == 'main_admin':
        context = {'request': request}

    return render(request, 'TakeTest.html', context)

# --- NEW AJAX View to fetch quizzes ---
def get_quizzes_json_view(request):
    class_id = request.GET.get('class_id')
    subject_id_filter = request.GET.get('subject_id')
    tag_ids_filter = request.GET.getlist('tag_ids') # List of tag IDs (strings)

    organized_data = {}
    user = request.user

    try:
        # Start with all subjects related to the requested class
        subjects_query = Subject.objects.filter(student_class_id=class_id).order_by('name')

        if subject_id_filter:
            subjects_query = subjects_query.filter(id=subject_id_filter)

        
        subjects_with_data = subjects_query.prefetch_related(
            'quizset_set__tags', # Prefetch tags directly on QuizSet
            'quizset_set__institution', # Prefetch institution for filtering
            'quizset_set__user', # Prefetch user for display
        ).distinct()


        for subject in subjects_with_data:
            class_name = str(subject.student_class.name)
            if class_name not in organized_data:
                organized_data[class_name] = []

            # Determine relevant quizzes based on user role and apply tag filtering
            quizzes_for_subject = subject.quizset_set.all()

            if user.is_superuser :
                pass
            elif user.role == 'teacher' or user.role == 'admin':
                quizzes_for_subject = quizzes_for_subject.filter(institution=user.profile.institute)
                 # Superusers see all quizzes for the subject
            elif user.role == 'main_admin':
                quizzes_for_subject = quizzes_for_subject.filter(institution__group=user.profile.institute_group)
                print("quizzes_for_subject : ",quizzes_for_subject)
            else:
                quizzes_for_subject = quizzes_for_subject.none() # Or filter for public quizzes if applicable

            # Apply tag filtering directly on QuizSet's tags
            if tag_ids_filter:
                for tag_id in tag_ids_filter:
                    quizzes_for_subject = quizzes_for_subject.filter(tags__id=tag_id)
                quizzes_for_subject = quizzes_for_subject.distinct() # In case a quiz has multiple tags matching filters

            # Order and collect quiz data
            quizzes_data = []
            for quiz in quizzes_for_subject.order_by('test_name'):
                quizzes_data.append({
                    'id': quiz.id,
                    'test_name': quiz.test_name,
                    'description': quiz.description,
                    'subject': quiz.subject.name,
                    'user': quiz.user.username,
                    'institution': quiz.institution.name if quiz.institution else 'N/A',
                    'tags': [tag.name for tag in quiz.tags.all()] # Get tags directly from QuizSet
                })

            # --- Collect all unique tags available for this subject's quizzes ---
            # This should get tags from ALL quizzes associated with this subject,
            # regardless of the current `tag_ids_filter` applied to `quizzes_for_subject`.
            all_tags_for_subject_quizzes = Tag.objects.filter(
                quizset__subject=subject # Link tags to quizzes through the subject
            ).distinct().values('id', 'name').order_by('name')

            available_tags_list = list(all_tags_for_subject_quizzes)

            # Append subject data to organized_data
            organized_data[class_name].append({
                'subject': subject.name,
                'id': subject.id,
                'quizzes': quizzes_data,
                'available_tags': available_tags_list, # Include available tags for this subject
            })

        # Sort by subject name within each class
        for class_name in organized_data:
            organized_data[class_name].sort(key=lambda x: x['subject'])

    except Exception as e:
        print(f"Error in get_quizzes_json_view: {e}")
        return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({
        'organized_data': organized_data,
        'userRole': user.role,
        'isSuperuser': user.is_superuser
    })



@login_required
def add_comment(request):
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.save()
            messages.success(request, 'Your comment has been submitted successfully!')
            return redirect('view_comments')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CommentForm()

    context = {
        'form': form,
        'page_title': 'Add Your Comment or Feedback'
    }
    return render(request, 'add_comment.html', context)

# NEW: View to display comments and their replies
def view_comments(request):
    if request.user.is_authenticated:
        # User sees public comments OR their own comments (public or private)
        top_level_comments = Comment.objects.filter(parent_comment__isnull=True).filter(
            Q(is_public=True) | Q(user=request.user)
        ).select_related('user').prefetch_related('replies__user').order_by('-created')
    else:
        # Anonymous users only see public comments
        top_level_comments = Comment.objects.filter(parent_comment__isnull=True, is_public=True)\
                                            .select_related('user').prefetch_related('replies__user')\
                                            .order_by('-created')


    # Prepare comments with reply forms for the template
    comments_with_forms = []
    for comment in top_level_comments:
        comments_with_forms.append({
            'comment': comment,
            'reply_form': ReplyForm() # A new form instance for each comment
        })

    context = {
        'comments_with_forms': comments_with_forms,
        'page_title': 'Community Comments & Feedback'
    }
    return render(request, 'view_comments.html', context) # IMPORTANT: Use 'your_app_name/' prefix

# NEW: View to handle reply submission
@login_required
def reply_comment(request, comment_id):
    parent_comment = get_object_or_404(Comment, id=comment_id)

    if request.method == 'POST':
        form = ReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.user = request.user
            reply.parent_comment = parent_comment
            reply.is_public = parent_comment.is_public

            reply.subject = f"Re: {parent_comment.subject[:20]}" if parent_comment.subject else "Reply" # Auto-set subject
            reply.save()
            messages.success(request, 'Your reply has been posted successfully!')
            return redirect('view_comments') # Redirect back to the comments page
        else:
            messages.error(request, 'Please correct the errors in your reply.')
            return redirect('view_comments')
    else:
        return redirect('view_comments')



def delete_comment(request, comment_id):
    """
    Deletes a comment if the request user is the author.
    """
    if request.method == 'POST' and request.user.is_authenticated:
        comment = get_object_or_404(Comment, pk=comment_id)
        if request.user == comment.user:
            comment.delete()
            messages.success(request, 'Your comment has been deleted successfully.')
        else:
            messages.error(request, 'You are not authorized to delete this comment.')
    else:
        messages.error(request, 'Invalid request or you are not logged in.')

    # Redirect back to the comments page
    return redirect('view_comments')




# --- NEW VIEW: Contact Us Page ---
def contact_us(request):
    if request.method == 'POST':
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            contact = form.save()  # Save to DB

            # Extract cleaned data
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            # Compose full message
            full_message = f"""
                Subject: {subject}

                Message:
                {message}
                """
            # Send mail
            send_mail(
                subject=f'New Contact Message: {subject}',
                message=full_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_RECEIVER_EMAIL,email,],  # Add this in your settings
                fail_silently=False,
            )

            messages.success(request, 'Mail sent successfully!')
            return redirect('home')
        else:
            context = {
                'form': form,
                'page_title': 'Contact Us'
            }
            return render(request, 'contact_us.html', context)
    else:
        form = ContactMessageForm()

    context = {
        'form': form,
        'page_title': 'Contact Us'
    }
    return render(request, 'contact_us.html', context)


@login_required
def view_contact_messages(request):
    search_query = request.GET.get('q', '')
    messages_queryset = ContactMessage.objects.all().order_by('-created')

    if search_query:
        messages_queryset = messages_queryset.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(message__icontains=search_query)
        )

    context = {
        'contact_messages': messages_queryset,
        'search_query': search_query,
        'page_title': 'Received Contact Messages'
    }
    return render(request, 'view_contact_messages.html', context)

# NEW: View to see the details of a single message
@login_required
def view_contact_message_detail(request, message_id):
    # Fetch the message or return a 404 error
    message = get_object_or_404(ContactMessage, pk=message_id)
    
    # Mark the message as read
    if not message.has_been_read:
        message.has_been_read = True
        message.save()

    context = {
        'message': message,
        'page_title': f'Message from {message.name}'
    }
    return render(request, 'view_contact_message_detail.html', context)

@login_required
def reply_to_contact_message(request, message_id):
    # Fetch the original message
    original_message = get_object_or_404(ContactMessage, pk=message_id)

    if request.method == 'POST':
        form = ContactReplyForm(request.POST)
        if form.is_valid():
            reply_subject = form.cleaned_data['subject']
            reply_body = form.cleaned_data['message']

            # Send the email
            send_mail(
                subject=reply_subject,
                message=reply_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[original_message.email],
                fail_silently=False,
            )
            # You can optionally add a success message here
            # messages.success(request, 'Your reply has been sent successfully!')
            return redirect('view_contact_message_detail', message_id=message_id)
    else:
        # Pre-populate the subject with a "Re:" prefix
        initial_data = {'subject': f'Re: {original_message.subject}'}
        form = ContactReplyForm(initial=initial_data)

    context = {
        'original_message': original_message,
        'form': form,
        'page_title': f'Reply to {original_message.name}'
    }
    return render(request, 'reply_to_contact_message.html', context)

@login_required
def send_message(request):
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.save()
            messages.success(request, 'Message sent successfully!')
            return redirect('message_list')
    else:
        form = MessageForm()
    return render(request, 'home/send_message.html', {'form': form})

@login_required
def message_list(request):
    sent_messages = Message.objects.filter(sender=request.user)[:5]
    received_messages = Message.objects.filter(recipient=request.user)[:5]
    
    return render(request, 'home/message_list.html', {
        'sent_messages': sent_messages,
        'received_messages': received_messages
    })

@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    
    if message.sender != request.user and message.recipient != request.user:
        messages.error(request, 'Access denied.')
        return redirect('message_list')
    
    if message.recipient == request.user and not message.is_read:
        message.is_read = True
        message.save()
    
    return render(request, 'home/message_detail.html', {'message': message})




@login_required
@staff_required
def reports_dashboard(request):

    # -----------------------------
    # GLOBAL STATS (your existing)
    # -----------------------------
    total_orgs = OrganizationProfile.objects.count()
    active_orgs = OrganizationProfile.objects.filter(is_active=True).count()
    inactive_orgs = total_orgs - active_orgs

    total_licenses = LicenseGrant.objects.count()
    expired_licenses = LicenseGrant.objects.filter(valid_until__lt=date.today()).count()

    total_users = User.objects.count()
    total_papers = QuestionPaper.objects.count()
    published_papers = QuestionPaper.objects.filter(is_published=True).count()
    draft_papers = total_papers - published_papers


    organizations = OrganizationProfile.objects.prefetch_related(
        'custom_groups__permissions'
    )

    # -----------------------------
    # PER-ORGANISATION STATISTICS
    # -----------------------------
    orgs = OrganizationProfile.objects.all()
    org_data = []
    today = date.today()

    for org in orgs:

        users = User.objects.filter(profile__organization_profile=org)
        licenses_with_status = []
        # Fetch licenses
        licenses = org.license_grants.all().prefetch_related("permissions")
        
        for license in licenses:
            # Calculate expiry status
            license.is_expired = license.valid_until < today
            licenses_with_status.append(license)

        org_data.append({
            "org": org,

            # USERS
            "total_users": users.count(),
            "active_users": users.filter(is_active=True).count(),
            "inactive_users": users.filter(is_active=False).count(),
            "students": users.filter(role="student").count(),
            "teachers": users.filter(role="teacher").count(),
            "admins": users.filter(role="admin").count(),

            # LICENSES
            "total_licenses": org.license_grants.count(),
            "active_licenses": org.license_grants.filter(valid_until__gte=date.today()).count(),
            "expired_licenses": org.license_grants.filter(valid_until__lt=date.today()).count(),

            # NEW: license objects (with permissions)
            "licenses": licenses_with_status,

            # ORG GROUPS
            "Orgnsation_groups": org.custom_groups.all().prefetch_related('permissions'),

            # CONTENT CREATED BY ORG
            "total_questions": Question.objects.filter(organization=org).count(),
            "total_papers": QuestionPaper.objects.filter(organization=org).count(),
        })

    # -----------------------------
    # GLOBAL CURRICULUM COUNTS
    # -----------------------------
    total_boards = TreeNode.objects.filter(node_type="board").count()
    total_classes = TreeNode.objects.filter(node_type="class").count()
    total_subjects = TreeNode.objects.filter(node_type="subject").count()
    total_chapters = TreeNode.objects.filter(node_type="chapter").count()


    hierarchy = {}

    # Get all classes
    board = TreeNode.objects.filter(node_type="board")

    for b in board:
        classes = b.children.filter(node_type="class")

        hierarchy[b] = {}  # Board level
        
        for c in classes:
            subjects = c.children.filter(node_type="subject")
            hierarchy[b][c] = {}  # Class level

            for s in subjects:
                chapters = s.children.filter(node_type="chapter")

                hierarchy[b][c][s] = {}  # Subject level

                for ch in chapters:
                    # Count questions directly under chapter
                    q_count = ch.chapter_questions.count()  # Reverse FK: TreeNode → Question
                    # print(q_count,ch.questions)
                    hierarchy[b][c][s][ch] = q_count

    # -----------------------------
    # RETURN
    # -----------------------------
    context = {
        # Global stats
        "total_orgs": total_orgs,
        "active_orgs": active_orgs,
        "inactive_orgs": inactive_orgs,
        "total_licenses": total_licenses,
        "expired_licenses": expired_licenses,
        "total_users": total_users,
        "total_papers": total_papers,
        "published_papers": published_papers,
        "draft_papers": draft_papers,
        "active_licenses": total_licenses - expired_licenses,
        "hierarchy": hierarchy,

        # global curriculum stats
        "stats": {
            "Boards": total_boards,
            "Classes": total_classes,
            "Subjects": total_subjects,
            "Chapters": total_chapters,
        }.items(),

        # NEW PER-ORG DATA
        "org_data": org_data,
       
    }

    return render(request, "reports.html", context)