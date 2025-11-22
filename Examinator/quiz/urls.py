from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    # Question URLs
    path('questions/', views.question_list, name='question_list'),
    path('questions/create/', views.question_create, name='question_create'),
    path('questions/<int:question_id>/edit/', views.question_detail_and_edit, name='question_edit'),
    path('questions/<int:question_id>/delete/', views.question_delete, name='question_delete'),
    
    # Question type specific URLs
    path('questions/<int:question_id>/mcq-options/', views.question_mcq_options, name='question_mcq_options'),
    path('questions/<int:question_id>/fill-blank/', views.question_fill_blank, name='question_fill_blank'),
    path('questions/<int:question_id>/short-answer/', views.question_short_answer, name='question_short_answer'),
    path('questions/<int:question_id>/match-pairs/', views.question_match_pairs, name='question_match_pairs'),
    path('questions/<int:question_id>/true-false/', views.question_true_false, name='question_true_false'),
    
    # Question Paper URLs
    path('papers/', views.paper_list, name='paper_list'),
    path('publis/<int:paper_id>',views.publish_paper,name='publish_paper'),
    path('papers/create/', views.add_question_paper, name='add_question_paper'),
    path('papers/<int:paper_id>/', views.paper_detail, name='paper_detail'),
    path('papers/<int:paper_id>/edit/', views.edit_question_paper, name='edit_question_paper'),
    path('papers/<int:paper_id>/delete/', views.paper_delete, name='paper_delete'),
    path('papers/<int:paper_id>/add-questions/', views.paper_add_questions, name='paper_add_questions'),
    path('papers/<int:paper_id>/remove-question/<int:question_id>/', views.paper_remove_question, name='paper_remove_question'),
    path('paper/<int:paper_id>/swap/<int:old_question_id>/select/', views.paper_execute_random_swap_api, name='paper_swap_question_select'),
    path('papers/<int:paper_id>/print/', views.paper_print, name='paper_print'),
    
    # AJAX URLs
    path('ajax/get-chapters/', views.get_chapters, name='get_chapters'),
    path('ajax/get-subjects/', views.get_subjects, name='get_subjects'),

    path("nodes/<int:node_id>/children/", views.get_child_nodes, name="get_child_nodes"),
    path("nodes/<int:subject_id>/curriculam",views.get_curriculum_tree, name="get_curriculum_tree"),

    # ... other paths
    path('bulk-upload/', views.bulk_upload_questions, name='bulk_upload_questions'),
]