"""
ZASCA操作记录应用
"""
default_app_config = 'apps.operations.apps.OperationsConfig'

# 导入模型中的信号，以便可以从apps.operations直接导入
try:
    # 防止在Django应用初始化期间导入模型导致的AppRegistryNotReady错误
    from django.apps import apps
    if apps.ready:
        from .models import account_opening_request_pre_submit, account_opening_request_post_submit
except:
    # 如果应用尚未准备好，不导出信号
    pass