"""
ZASCA URL Configuration
"""
from django.contrib.staticfiles.views import serve
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from config import views

urlpatterns = [
    path('admin/', include('apps.accounts.urls_admin')),
    path('provider/', include('apps.accounts.urls_provider')),
    path('api/', include('rest_framework.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('operations/', include('apps.operations.urls')),
    path('certificates/', include('apps.certificates.urls')),
    path('bootstrap/', include('apps.bootstrap.urls')),
    path('audit/', include('apps.audit.urls')),
    path('tunnel/', include('apps.tunnel.urls')),
    path('tickets/', include('apps.tickets.urls')),
    path('', include('apps.dashboard.urls')),
    path('404/', TemplateView.as_view(template_name='errors/404.html'), name='404'),
    path('favicon.ico', views.favicon_view),
    path('favicon.svg', views.favicon_svg_view),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = 'config.views.custom_404'
handler500 = 'config.views.custom_500'
