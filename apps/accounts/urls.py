"""
用户管理URL配置
"""
from django.urls import path
from django.views.decorators.cache import never_cache
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', never_cache(views.LoginView.as_view()), name='login'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('logout/', views.logout_view, name='logout'),
    # Geetest endpoints
    path('geetest/register/', views.geetest_register, name='geetest_register'),
    path('geetest/validate/', views.geetest_validate, name='geetest_validate'),
    path('email/send-code/', views.send_register_email_code, name='send_register_email_code'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot_password'),
    path('email/send-forgot-password-code/', views.send_forgot_password_email_code, name='send_forgot_password_email_code'),
    # Local Captcha endpoints
    path('captcha/generate/', views.local_captcha_generate, name='local_captcha_generate'),
    path('captcha/image/<str:captcha_id>/', views.local_captcha_image, name='local_captcha_image'),
    path('captcha/verify/', views.local_captcha_verify, name='local_captcha_verify'),
    path('api/profile/avatar/', views.upload_avatar, name='upload_avatar'),
    # API endpoints
    path('api/password/change/', views.password_change_api, name='password_change_api'),
]