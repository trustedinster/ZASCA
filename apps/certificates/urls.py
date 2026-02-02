from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    # 证书签发API
    path('issue-server-cert/', views.issue_server_certificate, name='issue_server_certificate'),
    path('issue-client-cert/', views.issue_client_certificate, name='issue_client_certificate'),
    path('validate-request/', views.validate_certificate_request, name='validate_certificate_request'),
    path('get-ca-cert/', views.get_ca_certificate, name='get_ca_certificate'),
    
    # 证书管理API
    path('manage/', views.CertificateManagementView.as_view(), name='certificate_management'),
    path('renew/', views.renew_certificate, name='renew_certificate'),
]