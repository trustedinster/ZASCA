from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    # 审计日志API
    path('logs/', views.get_audit_logs, name='get_audit_logs'),
    path('sensitive-ops/', views.get_sensitive_operations, name='get_sensitive_operations'),
    path('security-events/', views.get_security_events, name='get_security_events'),
    path('mark-event-resolved/', views.mark_security_event_resolved, name='mark_security_event_resolved'),
    path('session-activity/', views.get_user_session_activity, name='get_user_session_activity'),
    path('stats/', views.AuditManagementView.as_view(), name='audit_stats'),
    path('export/', views.export_audit_logs, name='export_audit_logs'),
]