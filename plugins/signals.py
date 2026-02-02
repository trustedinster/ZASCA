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
    
    # 检查是否已处理过，避免无限循环
    if getattr(instance, '_plugin_processed', False):
        return
    
    # 通过插件管理器获取所有可用的验证插件并执行验证
    plugin_manager = get_plugin_manager()
    all_plugins = plugin_manager.get_all_plugins()
    
    validation_performed = False
    validation_results = []
    
    for plugin_id, plugin in all_plugins.items():
        if hasattr(plugin, 'validate_for_account_opening'):
            try:
                logger.info(f"[Post Save Signal] 使用插件 {plugin.name} 验证开户申请")
                is_valid, reason = plugin.validate_for_account_opening(
                    account_request=instance
                )
                
                validation_performed = True
                validation_results.append((plugin.name, is_valid, reason))
                
                if not is_valid:
                    from django.contrib.auth import get_user_model
                    from django.utils import timezone
                    User = get_user_model()
                    
                    # 验证失败，自动拒绝申请
                    instance.status = 'rejected'
                    instance.approval_notes = f'{plugin.name}验证失败：{reason}'
                    instance.approved_by = User.objects.filter(is_superuser=True).first()
                    instance.approval_date = timezone.now()
                    
                    # 标记已处理，避免无限循环
                    instance._plugin_processed = True
                    instance.save(update_fields=['status', 'approval_notes', 'approved_by', 'approval_date'])
                    
                    logger.warning(f"[Post Save Signal] 申请 {instance.id} {plugin.name}验证失败，已拒绝：{reason}")
                    return  # 一旦有任何验证失败就拒绝申请
            except Exception as e:
                logger.error(f"[Post Save Signal] 插件 {plugin.name} 验证过程中出错: {str(e)}")
    
    if validation_performed:
        logger.info(f"[Post Save Signal] 验证完成，结果: {validation_results}")
    else:
        logger.info(f"[Post Save Signal] 没有找到可执行验证的插件")


@receiver(post_save, sender=CloudComputerUser)
def handle_cloud_computer_user_update(sender, instance, **kwargs):
    """
    处理云电脑用户更新的信号处理器
    通过插件管理器调用相关插件
    """
    logger.info(f"[Post Save Signal] 云电脑用户更新: {instance.username}, 状态: {instance.status}")
    
    # 通过插件管理器获取所有可用的验证插件并执行验证
    plugin_manager = get_plugin_manager()
    all_plugins = plugin_manager.get_all_plugins()
    
    for plugin_id, plugin in all_plugins.items():
        if hasattr(plugin, 'validate_cloud_user'):
            try:
                logger.info(f"[Post Save Signal] 使用插件 {plugin.name} 验证云电脑用户")
                is_valid, reason = plugin.validate_cloud_user(
                    cloud_user=instance
                )
                
                if not is_valid:
                    # 验证失败，根据插件策略处理用户
                    if hasattr(plugin, 'should_disable_user_on_failure') and plugin.should_disable_user_on_failure():
                        if instance.status != 'disabled':
                            instance.status = 'disabled'
                            instance.save(update_fields=['status'])
                            logger.warning(f"[Post Save Signal] {plugin.name}验证失败，禁用用户: {instance.username} - {reason}")
                    else:
                        logger.info(f"[Post Save Signal] {plugin.name}验证失败，但不执行禁用操作: {instance.username} - {reason}")
            except Exception as e:
                logger.error(f"[Post Save Signal] 插件 {plugin.name} 验证云用户时出错: {str(e)}")