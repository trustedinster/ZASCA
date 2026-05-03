from django.urls import path
from . import api

app_name = 'provider_api'

urlpatterns = [
    path('hosts/<int:pk>/deploy/', api.HostDeployAPI.as_view(), name='host_deploy'),
    path('account-requests/<int:pk>/action/', api.AccountRequestActionAPI.as_view(), name='accountrequest_action'),
    path('cloud-users/<int:pk>/action/', api.CloudUserActionAPI.as_view(), name='clouduser_action'),
    path(
        'invitation-tokens/<int:pk>/action/',
        api.InvitationTokenActionAPI.as_view(),
        name='invitationtoken_action',
    ),
    path(
        'products/<int:pk>/share-link/',
        api.ProductShareLinkAPI.as_view(),
        name='product_share_link',
    ),
]
