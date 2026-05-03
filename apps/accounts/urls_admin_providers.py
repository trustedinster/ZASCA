from django.urls import path

from .views_superadmin import (
    superadmin_host_list,
    superadmin_host_provider_assign,
    superadmin_hostgroup_list,
    superadmin_hostgroup_provider_assign,
)

app_name = 'admin_providers'

urlpatterns = [
    path(
        'hosts/',
        superadmin_host_list,
        name='provider_host_list',
    ),
    path(
        'hosts/<int:pk>/providers/',
        superadmin_host_provider_assign,
        name='provider_host_assign',
    ),
    path(
        'host-groups/',
        superadmin_hostgroup_list,
        name='provider_hostgroup_list',
    ),
    path(
        'host-groups/<int:pk>/providers/',
        superadmin_hostgroup_provider_assign,
        name='provider_hostgroup_assign',
    ),
]
