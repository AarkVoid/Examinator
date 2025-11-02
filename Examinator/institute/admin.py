from django.contrib import admin
from .models import Institution, InstitutionPasskey,InstituteApplication,InstitutionGroup

admin.site.register(Institution)
admin.site.register(InstitutionPasskey)
admin.site.register(InstituteApplication)
admin.site.register(InstitutionGroup)