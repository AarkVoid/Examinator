from django.urls import path
from . import views

urlpatterns = [
    path('', views.education_dashboard, name='education_dashboard'),
    path('board/add/', views.board_create, name='add_board'),
    path('class/add/', views.class_create, name='add_class'),
    path('subject/add/', views.subject_create, name='add_subject'),
    path('division/add/', views.division_create, name='add_division'),
    path('chapter/add/', views.chapter_create, name='add_chapter'),
    
    path('get-boards/', views.get_board, name='get_boards'),
    path('get-classes/', views.get_classes, name='get_classes'),
    path('get-subjects/', views.get_subject, name='get_subject'),
    path('get-chapters/', views.get_chapter, name='get_chapter'),
    path('get-divisions/', views.get_divisions, name='get_divisions'), 

    path('delete-board/<int:pk>/', views.board_delete, name='board_delete'),
    path('delete-class/<int:pk>/', views.class_delete, name='class_delete'),
    path('delete-subject/<int:pk>/', views.subject_delete, name='subject_delete'),
    path('delete-chapter/<int:pk>/', views.chapter_delete, name='chapter_delete'),
    path('board/edit/<int:pk>/', views.board_edit, name='board_edit'),
    path('class/edit/<int:pk>/', views.class_edit, name='class_edit'),
    path('division/<int:pk>/edit/', views.division_edit, name='division_edit'),
    path('subject/edit/<int:pk>/', views.subject_edit, name='subject_edit'),
    path('chapter/edit/<int:pk>/', views.chapter_edit, name='chapter_edit'),

    ######### lessons #########
    path('lessons/', views.lesson_list_create_view, name='lesson_list'),
    path('lessons/<int:lesson_id>/', views.lesson_detail_view, name='lesson_detail'),
    path('lessons/edit/<int:lesson_id>/', views.lesson_edit_view, name='lesson_edit'), 
    path('lessons/delete/<int:lesson_id>/', views.lesson_delete_view, name='lesson_delete'),
    path('division/<int:pk>/delete/', views.division_delete, name='division_delete'),
]