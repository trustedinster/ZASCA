from django.urls import path

from . import views_admin_reglinks as views

app_name = 'admin_reglinks'

urlpatterns = [
    path('', views.reglink_list, name='reglink_list'),
    path('create/', views.reglink_create, name='reglink_create'),
    path('<int:pk>/delete/', views.reglink_delete, name='reglink_delete'),
]
