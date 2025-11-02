# hierarchy/urls.py
from django.urls import path
from . import views

app_name = 'curritree'

urlpatterns = [
    path('', views.index, name='curriculum_list'),
    path('node/create/', views.create_node, name='curriculum_create'),
    path('node/create/child-of/<int:parent_pk>/', views.create_child_node, name='create_child_node'),
    path('node/<int:pk>/', views.detail, name='curriculum_detail'),
    path('node/<int:pk>/edit/', views.edit_node, name='curriculum_edit'),
    path('api/tree/', views.api_tree, name='api_tree'),
    path('api/tree/<int:root_id>/', views.api_tree, name='api_tree_root'),
    path('node/<int:pk>/delete/', views.delete_node, name='curriculum_delete'),
]
