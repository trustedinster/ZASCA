"""
审计日志应用的信号处理器
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import AuditLog, SensitiveOperation, SecurityEvent, SessionActivity


# 可以在这里添加具体的信号处理器
# 例如：在创建审计日志时触发某些操作