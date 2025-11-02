from django.contrib import admin

# Register your models here.
from .models import Comment,ContactMessage

admin.site.register(Comment)
admin.site.register(ContactMessage)