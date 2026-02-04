# 插件系统

插件系统为ZASCA提供可扩展的功能模块支持，采用松耦合设计，支持动态加载和管理插件。

## 架构设计

插件系统采用分层架构，将核心接口与具体实现分离：

- **core/**: 核心组件目录，包含接口定义和插件管理器
- **各插件目录**: 每个插件都有独立的目录，包含其所有相关文件

## 核心概念

### PluginInterface

所有插件必须继承 `PluginInterface` 抽象基类，并实现以下方法：

- `initialize()`: 初始化插件
- `shutdown()`: 关闭插件

### 插件管理器

`PluginManager` 负责插件的加载、初始化、运行和卸载。

## 开发新插件

### 1. 创建插件目录

为新插件创建独立的目录：

```bash
mkdir plugins/new_plugin_name
```

### 2. 实现插件类

创建插件实现文件，继承 `PluginInterface`：

```python
from plugins.core.base import PluginInterface

class NewPlugin(PluginInterface):
    def __init__(self):
        super().__init__(
            plugin_id="new_plugin",
            name="新插件",
            version="1.0.0",
            description="新插件描述"
        )
    
    def initialize(self) -> bool:
        # 初始化插件
        return True
    
    def shutdown(self) -> bool:
        # 关闭插件
        return True
```

### 3. 注册插件

在 [available_plugins.py](file:///Users/Supercmd/Desktop/Python/ZASCA/plugins/available_plugins.py) 文件中注册插件：

```python
BUILTIN_PLUGINS = {
    'new_plugin': {
        'name': '新插件',
        'module': 'plugins.new_plugin.new_plugin',
        'class': 'NewPlugin',
        'description': '新插件描述',
        'version': '1.0.0',
        'enabled': True
    }
}
```

## 现有插件

### QQ验证插件

位于 `plugins/qq_verification/` 目录，提供QQ群验证功能：

- 检测QQ号是否在指定群中
- 支持"只有加入了某个群才允许使用机器"模式
- 支持"老六模式"（对已有云电脑用户进行验证）

## 目录结构

参见 [STRUCTURE.md](file:///Users/Supercmd/Desktop/Python/ZASCA/plugins/STRUCTURE.md) 文件了解详细的目录结构说明。

## 运行时管理

插件系统通过 `PluginManager` 实现插件的动态管理，支持：

- 插件热加载
- 插件状态监控
- 事件钩子机制