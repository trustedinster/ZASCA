# 插件系统目录结构

## 概述
插件系统采用分层架构设计，将核心接口与具体实现分离，确保系统的可扩展性和可维护性。

## 目录结构

```
plugins/                           # 插件系统根目录
├── core/                         # 核心组件目录
│   ├── __init__.py               # 核心模块初始化
│   ├── base.py                   # 插件接口定义
│   └── plugin_manager.py         # 插件管理器
├── qq_verification/              # QQ验证插件
│   ├── __init__.py               # 插件初始化
│   ├── qq_checker.py             # QQ验证核心功能
│   └── qq_verification_plugin.py # QQ验证插件实现
├── sample_plugins/               # 示例插件目录
│   ├── __init__.py               # 示例插件初始化
│   └── ...                       # 各种示例插件
├── __init__.py                   # 插件系统初始化
├── apps.py                       # Django应用配置
├── models.py                     # 插件相关的Django模型
├── admin.py                      # Django管理界面配置
├── signals.py                    # Django信号处理器
├── available_plugins.py          # 可用插件配置
├── README.md                     # 插件系统说明
└── migrations/                   # 数据库迁移文件
```

## 核心组件 (core/)

- **base.py**: 定义了[PluginInterface](file:///Users/Supercmd/Desktop/Python/ZASCA/plugins/core/base.py#L8-L48)抽象基类和其他核心接口
- **plugin_manager.py**: 实现插件的加载、管理、运行和卸载功能
- **__init__.py**: 核心模块初始化

## 具体插件目录

每个插件都有自己的目录，包含该插件的所有相关文件：

- **qq_verification/**: QQ验证插件
  - [qq_checker.py](file:///Users/Supercmd/Desktop/Python/ZASCA/plugins/qq_verification/qq_checker.py): 实现QQ群验证的核心功能
  - [qq_verification_plugin.py](file:///Users/Supercmd/Desktop/Python/ZASCA/plugins/qq_verification/qq_verification_plugin.py): 实现[PluginInterface](file:///Users/Supercmd/Desktop/Python/ZASCA/plugins/core/base.py#L8-L48)的具体插件类
  - **__init__.py**: 插件初始化

## 配置文件

- **available_plugins.py**: 定义系统中所有可用的插件及其配置信息
- **models.py**: 插件相关的数据库模型
- **signals.py**: Django信号处理器，用于集成插件功能

## 设计优势

1. **清晰分离**: 核心接口与具体实现完全分离
2. **易于扩展**: 添加新插件只需创建新目录和实现接口
3. **易于维护**: 每个插件的功能封装在自己的目录中
4. **降低耦合**: 插件之间相互独立，减少依赖关系