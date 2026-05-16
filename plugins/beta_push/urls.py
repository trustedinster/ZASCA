from django.urls import path

from . import views

app_name = 'beta_push'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('push/', views.start_push, name='start_push'),
    path('status/', views.push_status, name='push_status'),
]
