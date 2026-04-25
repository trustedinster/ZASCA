from django.urls import path
from . import views

app_name = 'tunnel'

urlpatterns = [
    path('download/', views.download_tunnel_client, name='download'),
    path('config/', views.get_tunnel_config, name='config'),
    path('install/', views.install_tunnel_service, name='install'),
]
