"""
用户管理信号处理器
"""
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_log(sender, instance, created, **kwargs):
    """
    用户创建/更新时记录操作日志

    Args:
        sender: 发送信号的模型类
        instance: 用户实例
        created: 是否是新创建的用户
        **kwargs: 其他参数
    """
    pass


@receiver(m2m_changed, sender=User.groups.through)
def sync_staff_on_group_change(sender, instance, action, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        instance.sync_staff_status()
