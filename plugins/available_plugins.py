"""
可用插件配置
定义系统中所有可用的插件
"""
import toml
import os
from django.conf import settings


# 加载 TOML 配置文件
toml_file_path = os.path.join(settings.BASE_DIR, 'plugins', 'plugins.toml')
if os.path.exists(toml_file_path):
    with open(toml_file_path, 'r', encoding='utf-8') as f:
        toml_data = toml.load(f)
else:
    # 如果 TOML 文件不存在，使用默认配置
    toml_data = {
        'builtin': {},
        'third_party': {}
    }


# 系统内置插件
BUILTIN_PLUGINS = toml_data.get('builtin', {})

# 第三方插件（如果有的话）
THIRD_PARTY_PLUGINS = toml_data.get('third_party', {})

# 合并所有插件
ALL_AVAILABLE_PLUGINS = {**BUILTIN_PLUGINS, **THIRD_PARTY_PLUGINS}