from django.urls import path

from .views_admin import (
    themeconfig_edit,
    themeconfig_clear_cache,
    pagecontent_list,
    pagecontent_create,
    pagecontent_edit,
    pagecontent_delete,
    widgetlayout_list,
    widgetlayout_create,
    widgetlayout_edit,
    widgetlayout_delete,
)

app_name = 'admin_themes'

urlpatterns = [
    path('config/', themeconfig_edit, name='themeconfig_edit'),
    path(
        'config/clear-cache/',
        themeconfig_clear_cache,
        name='themeconfig_clear_cache',
    ),
    path('pages/', pagecontent_list, name='pagecontent_list'),
    path('pages/create/', pagecontent_create, name='pagecontent_create'),
    path(
        'pages/<int:pk>/edit/',
        pagecontent_edit,
        name='pagecontent_edit',
    ),
    path(
        'pages/<int:pk>/delete/',
        pagecontent_delete,
        name='pagecontent_delete',
    ),
    path('layouts/', widgetlayout_list, name='widgetlayout_list'),
    path(
        'layouts/create/',
        widgetlayout_create,
        name='widgetlayout_create',
    ),
    path(
        'layouts/<int:pk>/edit/',
        widgetlayout_edit,
        name='widgetlayout_edit',
    ),
    path(
        'layouts/<int:pk>/delete/',
        widgetlayout_delete,
        name='widgetlayout_delete',
    ),
]
