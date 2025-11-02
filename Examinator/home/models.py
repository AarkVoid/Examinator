from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.models import TimeStampedModel

User = get_user_model()

class Comment(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_public = models.BooleanField(default=True)
    parent_comment = models.ForeignKey('self',null=True,blank=True,related_name='replies',on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.subject} by {self.user.username}"

class ContactMessage(TimeStampedModel):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    has_been_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.subject} from {self.name}"

class Message(TimeStampedModel):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', null=True, blank=True)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    subject = models.CharField(max_length=200)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.subject} from {self.sender.username} to {self.recipient.username}"