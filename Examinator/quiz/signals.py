from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import F
# Assuming OrgQuestion, Question, PaperQuestion, and PaperOrgQuestion are in models.py
# If they are in a different app, adjust the import path.
from .models import OrgQuestion, Question, PaperQuestion, PaperOrgQuestion 

# --- PaperQuestion Signals (for Public Questions) ---

