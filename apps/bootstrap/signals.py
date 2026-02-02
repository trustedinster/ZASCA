"""
主机引导应用的信号处理器
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import BootstrapToken


# 可以在这里添加具体的信号处理器
# 例如：在引导令牌即将过期时发送通知