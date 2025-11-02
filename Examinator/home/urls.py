from django.urls import path
from . import views

urlpatterns = [
    path('',views.home, name='home'),
    path('organisationHome',views.organization_home,name= 'OrgHome'),
    path('Test/', views.TakeTest, name='TakeTest'),
    path('get-quizzes-json/', views.get_quizzes_json_view, name='get_quizzes_json'),
    #### comments ########
    path('add_comment/', views.add_comment, name='add_comment'),
    path('comments/', views.view_comments, name='view_comments'),
    path('comments/reply/<int:comment_id>/', views.reply_comment, name='reply_comment'),
    path('comments/delete/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    ######### contact us #########
    path('contact/', views.contact_us, name='contact_us'),
    path('contact-messages/', views.view_contact_messages, name='view_contact_messages'),
    path('contact-messages/<int:message_id>/', views.view_contact_message_detail, name='view_contact_message_detail'),
    path('contact-messages/<int:message_id>/reply/', views.reply_to_contact_message, name='reply_to_contact_message'),
    
    # Message URLs
    path('send-message/', views.send_message, name='send_message'),
    path('messages/', views.message_list, name='message_list'),
    path('message/<int:message_id>/', views.message_detail, name='message_detail'),
] 