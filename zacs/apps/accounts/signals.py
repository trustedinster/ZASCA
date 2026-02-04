"""
用户管理信号处理器
"""
from django.db.models.signals import post_save
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
    # 移除日志记录功能，因为已经删除了 OperationLog 模型
    pass
