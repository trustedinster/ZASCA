"""
证书管理应用的信号处理器
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import CertificateAuthority, ServerCertificate, ClientCertificate


# 可以在这里添加具体的信号处理器
# 例如：在证书即将过期时发送通知