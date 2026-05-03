from django.urls import path

from .views_admin import auditlog_list, auditlog_detail

app_name = 'admin_audit'

urlpatterns = [
    path('', auditlog_list, name='auditlog_list'),
    path('<int:pk>/', auditlog_detail, name='auditlog_detail'),
]
