"""
可用插件配置
定义系统中所有可用的插件
"""

# 系统内置插件
BUILTIN_PLUGINS = {
    'qq_verification': {
        'name': 'QQ验证插件',
        'module': 'plugins.qq_verification.qq_verification_plugin',
        'class': 'QQVerificationPlugin',
        'description': '用于检测QQ号是否在指定群中的验证插件',
        'version': '1.0.0',
        'enabled': True
    }
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