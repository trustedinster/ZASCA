from django.urls import path

from . import views_admin_groups as views

app_name = 'admin_groups'

urlpatterns = [
    path('', views.group_list, name='group_list'),
    path('create/', views.group_create, name='group_create'),
    path('<int:pk>/edit/', views.group_update, name='group_edit'),
    path('<int:pk>/delete/', views.group_delete, name='group_delete'),
]
