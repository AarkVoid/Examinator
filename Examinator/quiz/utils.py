from django.core.exceptions import ValidationError
from django.db.models import F,Max,Q
# Assuming QuestionPaper, UsageLimit, and OrganizationProfile are available here
from .models import QuestionPaper
from saas.models import UsageLimit ,OrganizationProfile
from datetime import date



def validate_paper_limits_and_license(organization: 'OrganizationProfile', curriculum_subject, is_published: bool, existing_paper_id=None):
    """
    Validates constraints: License coverage, Draft limit, and Published limit.
    """
    
    # 1. License Check: Ensure the subject is covered by the organization's licenses
    # We check against the pre-calculated OrganizationProfile.supported_curriculum.
    licensed_nodes_pks = organization.license_grants.all().values_list('curriculum_node__pk', flat=True).distinct()

    if curriculum_subject.pk not in licensed_nodes_pks:
        raise ValidationError(
            "License Error: The selected subject is not covered by any active license grant for your organization."
        )

    # 2. Limit Check - UsageLimit (Drafts)
    try:
        usage_limit = organization.usage_limit
        max_drafts = usage_limit.max_question_papers_drafts
    except UsageLimit.DoesNotExist:
        raise ValidationError("Configuration Error: Usage limits are not configured for this organization.")

    # 3. Limit Check - LicenseGrant (Published Papers)
    today = date.today()
    
    # Find the largest max_question_papers value across all active licenses
    max_published_papers_result = organization.license_grants.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today)
    ).aggregate(max_limit=Max('max_question_papers'))

    # Use the max_limit found, defaulting to 0 if no active licenses exist
    max_published_papers = max_published_papers_result.get('max_limit') or 0

    if max_published_papers == 0:
        raise ValidationError("License Error: The organization has no active licenses allowing paper creation.")

    # Base queryset for counting existing papers
    qs = QuestionPaper.objects.filter(organization=organization)
    
    # Exclude the current paper if we are editing it (or publishing it)
    if existing_paper_id:
        qs = qs.exclude(pk=existing_paper_id)

    if not is_published:
        # 3a. If checking for a DRAFT (when adding a new paper or saving an existing draft)
        draft_count = qs.filter(is_published=False).count()
        
        # Check against UsageLimit model's max_question_papers_drafts
        if draft_count >= max_drafts:
            raise ValidationError(
                f"Limit Exceeded: You have reached the maximum allowed limit of {max_drafts} draft papers. Please publish or delete an existing draft."
            )
    else:
        # 3b. If checking for PUBLISHED (when publishing a draft or saving a new published paper)
        published_count = qs.filter(is_published=True).count()
        
        # Check against the MAX limit from all active LicenseGrant models
        if published_count >= max_published_papers:
            raise ValidationError(
                f"Limit Exceeded: You have reached the maximum allowed limit of {max_published_papers} published papers. Please unpublish an existing paper first."
            )
    
    return True
