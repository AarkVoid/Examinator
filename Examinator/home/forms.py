from django import forms
from .models import Comment, ContactMessage, Message
from django.contrib.auth import get_user_model

User = get_user_model()

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['subject', 'message', 'is_public']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary'}),
            'message': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary', 'rows': 5}),
            'is_public': forms.CheckboxInput(attrs={'class': 'rounded'})
        }

class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary'}),
            'subject': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary'}),
            'message': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary', 'rows': 5})
        }

class MessageForm(forms.ModelForm):
    recipient = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary'})
    )
    
    class Meta:
        model = Message
        fields = ['recipient', 'subject', 'content']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary'}),
            'content': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary', 'rows': 6})
        }


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['message', 'is_public']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary',
                'rows': 3
            }),
            'is_public': forms.CheckboxInput(attrs={'class': 'rounded'})
        }


class ContactReplyForm(forms.Form):
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(
            attrs={
                'class': 'w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary',
                'placeholder': 'Subject'
            }
        )
    )
    message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary',
                'rows': 6,
                'placeholder': 'Write your reply here...'
            }
        )
    )