"""
插件系统信号处理器
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.operations.models import AccountOpeningRequest, CloudComputerUser
from .core.plugin_manager import get_plugin_manager
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AccountOpeningRequest)
def handle_account_opening_request(sender, instance, created, **kwargs):
    """
    处理开户申请的信号处理器
    通过插件管理器调用相关插件
    """
    logger.info(f"[Post Save Signal] 处理开户申请: {instance.id}, 创建: {created}, 状态: {instance.status}")
    
    # 通过插件管理器获取QQ验证插件并执行验证
    plugin_manager = get_plugin_manager()
    qq_plugin = plugin_manager.get_plugin("qq_verification_plugin")
    
    if qq_plugin and hasattr(qq_plugin, 'validate'):
        if instance.target_product and instance.status == 'pending':
            logger.info(f"[Post Save Signal] 开始验证产品ID {instance.target_product.id} 的QQ验证")
            # 检查是否通过QQ验证
            is_valid = qq_plugin.validate(
                product_id=instance.target_product.id,
                applicant_email=instance.contact_email
            )
            
            if not is_valid:
                from django.contrib.auth import get_user_model
                from django.utils import timezone
                User = get_user_model()
                
                # 验证失败，自动拒绝申请
                instance.status = 'rejected'
                instance.approval_notes = 'QQ验证失败：您的QQ号未在指定群中'
                instance.approved_by = User.objects.filter(is_superuser=True).first()
                instance.approval_date = timezone.now()
                
                # 标记已处理，避免无限循环
                instance._qq_verification_processed = True
                instance.save()
                
                logger.warning(f"[Post Save Signal] 申请 {instance.id} QQ验证失败，已拒绝")
            else:
                logger.info(f"[Post Save Signal] 申请 {instance.id} QQ验证通过")
    else:
        logger.info(f"[Post Save Signal] 未找到QQ验证插件或插件没有validate方法")


@receiver(post_save, sender=CloudComputerUser)
def handle_cloud_computer_user_update(sender, instance, **kwargs):
    """
    处理云电脑用户更新的信号处理器
    通过插件管理器调用相关插件
    """
    logger.info(f"[Post Save Signal] 云电脑用户更新: {instance.username}, 状态: {instance.status}")
    
    # 通过插件管理器获取QQ验证插件并执行验证
    plugin_manager = get_plugin_manager()
    qq_plugin = plugin_manager.get_plugin("qq_verification_plugin")
    
    if qq_plugin and hasattr(qq_plugin, 'validate') and instance.status == 'active':
        try:
            from .models import QQVerificationConfig
            
            # 获取与用户关联的产品的QQ验证配置
            config = QQVerificationConfig.objects.get(product=instance.product)
            
            if config.is_old_six_mode_enabled:
                logger.info(f"[Post Save Signal] 老六模式验证用户: {instance.username}")
                # 检查用户是否通过QQ验证
                is_valid = qq_plugin.validate(
                    product_id=instance.product.id,
                    cloud_user=instance
                )
                
                if not is_valid and instance.status != 'disabled':
                    # 验证失败，且用户尚未被禁用
                    # 在老六模式下，验证失败会禁用账户
                    instance.status = 'disabled'
                    instance.save()
                    logger.warning(f"[Post Save Signal] 老六模式验证失败，禁用用户: {instance.username}")
                    
        except QQVerificationConfig.DoesNotExist:
            # 如果没有配置，则跳过验证
            logger.info(f"[Post Save Signal] 用户 {instance.username} 关联的产品没有QQ验证配置")
            pass