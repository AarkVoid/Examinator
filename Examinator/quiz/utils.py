from django.core.exceptions import ValidationError
from django.db.models import Q,Sum
# Assuming QuestionPaper, UsageLimit, and OrganizationProfile are available here
from .models import QuestionPaper
from saas.models import UsageLimit ,OrganizationProfile
from datetime import date
from typing import Union
from saas.models import LicenseGrant



def validate_paper_limits_and_license(organization: 'OrganizationProfile', curriculum_subject, is_published: bool, existing_paper_id=None) -> Union['LicenseGrant', bool]:
    """
    Validates constraints: License coverage, Draft limit, and Published limit.

    If is_published=False (Draft check), returns True or raises ValidationError.
    If is_published=True (Published check), returns the LicenseGrant object to consume 
    or raises ValidationError.
    """
    today = date.today()

    # --- 1 & 2: DRAFT LIMIT CHECK (Unchanged) ---
    if not is_published:
        try:
            usage_limit = organization.usage_limit
            max_drafts = usage_limit.max_question_papers_drafts
        except UsageLimit.DoesNotExist:
            raise ValidationError("Configuration Error: Usage limits are not configured for this organization.")

        qs = QuestionPaper.objects.filter(organization=organization)
        if existing_paper_id:
            qs = qs.exclude(pk=existing_paper_id)
            
        draft_count = qs.filter(is_published=False).count()
        
        if draft_count >= max_drafts:
            raise ValidationError(
                f"Limit Exceeded: You have reached the maximum allowed limit of {max_drafts} draft papers. Please publish or delete an existing draft."
            )
        
        return True 

    # --- 3: PUBLISHED LIMIT CHECK (Requires finding an available LicenseGrant) ---
    
    candidate_grants = []
    
    # Filter for active licenses
    active_grants = organization.license_grants.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today)
    )

    if not active_grants.exists():
        raise ValidationError("License Error: The organization has no active licenses.")

    # Iterate through active grants to check for subject coverage and capacity
    for grant in active_grants:
        # Check coverage: Build set of all nodes covered by this single grant
        licensed_nodes = {node.pk for node in grant.get_all_licensed_nodes()}
        
        if curriculum_subject.pk in licensed_nodes:
            # Check capacity: Does this specific license still have slots?
            if grant.question_papers_created < grant.max_question_papers:
                candidate_grants.append(grant)

    if not candidate_grants:
        # If no candidates are found, calculate the total published capacity for a useful error message
        total_limit_result = active_grants.aggregate(total_limit=Sum('max_question_papers'))
        total_limit = total_limit_result.get('total_limit') or 0
        
        total_used_result = active_grants.aggregate(total_used=Sum('question_papers_created'))
        total_used = total_used_result.get('total_used') or 0
        
        raise ValidationError(
            f"Limit Exceeded: All active license grants covering this subject are currently full. Your organization has used {total_used} of its total capacity of {total_limit}."
        )
    
    # 🛑 NEW LOGIC: Sort candidate grants to prioritize the one expiring soonest.
    # The key sorts by:
    # 1. Whether valid_until is None (False=0=first, True=1=last)
    # 2. The valid_until date itself (ascending)
    candidate_grants.sort(key=lambda grant: (grant.valid_until is None, grant.valid_until))

    # Return the first grant after sorting (the one expiring soonest)
    return candidate_grants[0]
