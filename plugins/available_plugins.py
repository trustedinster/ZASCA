"""
可用插件配置
定义系统中所有可用的插件
"""

# 系统内置插件
BUILTIN_PLUGINS = {
    'qq_verification': {
        'name': 'QQ Verification Plugin',
        'module': 'plugins.qq_verification.qq_verification',
        'class': 'QQVerificationPlugin',
        'description': 'QQ验证插件，提供QQ登录和验证功能',
        'version': '1.0.0',
        'enabled': True
    },
    # 包含一些示例插件供参考
    'example_plugin': {
        'name': 'Example Plugin',
        'module': 'plugins.sample_plugins.example_plugin',
        'class': 'ExamplePlugin',
        'description': '示例插件，展示插件开发的基本结构',
        'version': '1.0.0',
        'enabled': True
    },
    'email_notification_plugin': {
        'name': 'Email Notification Plugin',
        'module': 'plugins.sample_plugins.email_notification_plugin',
        'class': 'EmailNotificationPlugin',
        'description': '提供邮件通知功能的插件',
        'version': '1.0.0',
        'enabled': True
    },
    'demo_auth_plugin': {
        'name': 'Demo Authentication Plugin',
        'module': 'plugins.sample_plugins.demo_auth_plugin',
        'class': 'DemoAuthPlugin',
        'description': '演示认证功能的插件',
        'version': '1.0.0',
        'enabled': True
    },

}

# 第三方插件（如果有的话）
THIRD_PARTY_PLUGINS = {
    # 示例格式
    # 'third_party_plugin': {
    #     'name': '第三方插件名称',
    #     'module': 'plugins.third_party.plugin_module',
    #     'class': 'ThirdPartyPluginClass',
    #     'description': '插件描述',
    #     'version': '1.0.0',
    #     'enabled': True
    # }
}

# 合并所有插件
ALL_AVAILABLE_PLUGINS = {**BUILTIN_PLUGINS, **THIRD_PARTY_PLUGINS}