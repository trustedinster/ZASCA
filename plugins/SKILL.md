# SKILL.md - ZASCA 插件设计 AI 指南

> **文档版本**: 1.0  
> **适用范围**: ZASCA 项目 AI Agent 插件开发  
> **目标读者**: AI Agent（自动化插件生成）  
> **关联规范**: [AGENTS.md](/home/supercmd/python/zascateam/ZASCA/AGENTS.md)（AI 绝对开发规范）  

## 文档说明

本文件定义了 AI 为 ZASCA 项目设计、实现和验证插件时必须遵循的完整流程与规范。AI 在接到任何插件开发任务时，必须严格按照本文档规定的步骤执行，不得跳过或省略任何环节。

### 核心原则

- **流程强制**: 必须按顺序执行「需求分析 → 接口选型 → 目录规划 → 代码实现 → 注册配置 → 迁移验证 → 归属声明检查」
- **解耦优先**: 严禁直接导入核心模型，必须使用 `apps.get_model()` 或延迟导入
- **样式隔离**: 前后台 UI 严禁混用样式公式，必须严格区分 `slate/cyan`（后台）与 `md:`（前台）
- **归属声明**: 所有 UI 元素必须包含可见的插件来源标识（LICENSE Section 3(d) 强制要求）

---

## 1. 总体流程

接到插件开发任务后，AI 必须按以下顺序执行：

```
需求分析 → 接口选型 → 目录规划 → 代码实现 → 注册配置 → 迁移验证 → 归属声明检查
```

每一步完成后再进入下一步，不得跳过。

***

## 2. 需求分析

在编写任何代码之前，AI 必须先明确以下问题并记录结论：

| 问题                 | 选项           | 影响                             |
| ------------------ | ------------ | ------------------------------ |
| 插件的核心功能是什么？        | 自由描述         | 决定插件类名、plugin\_id              |
| 是否需要向系统注册可发现的服务？   | 是 / 否        | 是否实现 `ServiceProvider`         |
| 是否需要向前端页面注入 UI 内容？ | 是 / 否        | 是否实现 `UIExtensionProvider`     |
| 是否需要注册独立的 URL 路由？  | 是 / 否        | 是否实现 `URLProvider`             |
| 是否需要自有数据模型？        | 是 / 否        | 是否需要独立 Django App + migrations |
| 是否需要响应系统事件？        | 是 / 否        | 使用 EventHook 或 Django signals  |
| UI 内容属于前台还是后台？     | 前台 / 后台 / 都有 | 决定样式公式和 URL section            |

***

## 3. 接口选型

根据需求分析结果，从以下四个核心接口中选择需要实现的：

```
PluginInterface          ← 必须实现（生命周期管理）
  ├── ServiceProvider    ← 可选（注册可发现服务）
  ├── UIExtensionProvider ← 可选（注入页面 UI 内容）
  └── URLProvider         ← 可选（动态注册 URL 路由）
```

### 接口对照表

| 接口                    | 必须实现的方法                                         | 适用场景                           |
| --------------------- | ----------------------------------------------- | ------------------------------ |
| `PluginInterface`     | `initialize()`, `shutdown()`                    | 所有插件必须实现                       |
| `ServiceProvider`     | `get_service_name()`, `get_service_interface()` | 提供可被其他模块发现和消费的服务（如 IP 查询、短信发送） |
| `UIExtensionProvider` | `get_ui_extensions()`                           | 在核心页面注入导航链接、配置面板、表单字段等         |
| `URLProvider`         | `get_url_patterns()`                            | 拥有独立的页面、视图、管理后台                |

### 典型组合

| 插件类型   | 接口组合                                                  | 示例                 |
| ------ | ----------------------------------------------------- | ------------------ |
| 纯后台服务  | `PluginInterface + ServiceProvider`                   | Gateway 插件、IP 查询插件 |
| 纯事件监听  | `PluginInterface`                                     | 审计日志插件、邮件通知插件      |
| UI 注入型 | `PluginInterface + UIExtensionProvider`               | 系统监控面板插件           |
| 完整功能型  | `PluginInterface + UIExtensionProvider + URLProvider` | 公告管理插件             |

***

## 4. 目录规划

### 4.1 简单插件（无独立模型/路由）

```
plugins/<plugin_name>/
├── __init__.py
└── plugin.py            ← 插件主类
```

### 4.2 完整功能插件（有独立模型/路由/模板）

```
plugins/<plugin_name>/
├── __init__.py
├── apps.py              ← Django AppConfig（必须）
├── plugin.py            ← 插件主类
├── models.py            ← 自有数据模型
├── views_admin.py       ← 管理视图（后台）
├── views_provider.py    ← 提供商视图（如需要）
├── forms_admin.py       ← 管理表单
├── urls_admin.py        ← 管理路由
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py
└── templates/<plugin_name>/
    ├── list.html
    ├── form.html
    └── _config_section.html
```

### 4.3 命名规范

| 项目         | 规范                                       | 示例                                            |
| ---------- | ---------------------------------------- | --------------------------------------------- |
| 目录名        | 小写下划线                                    | `qq_verification`, `system_monitor`           |
| plugin\_id | 小写下划线，与目录名一致                             | `"qq_verification"`, `"system_monitor"`       |
| 类名         | PascalCase + Plugin 后缀                   | `QQVerificationPlugin`, `SystemMonitorPlugin` |
| 模块路径       | `plugins.<目录名>` 或 `plugins.<目录名>.plugin` | `plugins.gateway`                             |

***

## 5. 代码实现

### 5.1 插件主类模板

```python
import logging
from typing import List

from plugins.core.base import (
    PluginInterface,
    ServiceProvider,        # 按需导入
    UIExtension,            # 按需导入
    UIExtensionProvider,    # 按需导入
    URLProvider,            # 按需导入
)

logger = logging.getLogger(__name__)


class MyPlugin(PluginInterface, UIExtensionProvider, URLProvider):
    def __init__(self):
        super().__init__(
            plugin_id="my_plugin",
            name="My Plugin",
            version="1.0.0",
            description="插件描述",
        )

    def initialize(self) -> bool:
        logger.info(f"初始化 {self.name}")
        return True

    def shutdown(self) -> bool:
        logger.info(f"关闭 {self.name}")
        return True
```

### 5.2 ServiceProvider 实现

```python
class MyServiceInterface:
    """定义服务的抽象接口，消费方依赖此类型"""
    def my_method(self) -> dict:
        raise NotImplementedError


class MyPlugin(PluginInterface, ServiceProvider):
    def get_service_name(self) -> str:
        return "my_service"

    def get_service_interface(self) -> Type:
        return MyServiceInterface

    def get_service(self) -> Any:
        return self

    def my_method(self) -> dict:
        return {"result": "ok"}
```

消费方使用：

```python
from plugins.core.plugin_manager import get_plugin_manager

pm = get_plugin_manager()
service = pm.service_registry.get("my_service")
# 或按接口类型查找（推荐）
services = pm.service_registry.get_by_interface(MyServiceInterface)
```

### 5.3 UIExtensionProvider 实现

```python
def get_ui_extensions(self) -> List[UIExtension]:
    try:
        from django.urls import reverse
        url = reverse("admin:admin_plugins:my_view")
    except Exception:
        url = "#"

    return [
        UIExtension(
            extension_type=UIExtension.NAV_ITEM,
            slot="admin_sidebar_plugins",
            html=(
                f'<a href="{url}" '
                f'class="flex items-center gap-3 px-4 '
                f'py-2.5 rounded-md text-sm font-medium '
                f'transition text-white/70 '
                f'hover:bg-white/5 hover:text-white">'
                f'<span class="material-symbols-rounded '
                f'text-lg shrink-0 text-cyan-400">'
                f'icon_name</span>'
                f'<span>功能名称</span>'
                f'<span class="ml-auto text-[10px] '
                f'px-1.5 py-0.5 rounded '
                f'bg-cyan-500/10 text-cyan-400 '
                f'border border-cyan-500/20 '
                f'font-medium">Plugin</span></a>'
            ),
            order=20,
        ),
    ]
```

#### 预定义 UI 扩展点（Slot）

| Slot 名称                        | 位置              | 用途       |
| ------------------------------ | --------------- | -------- |
| `admin_sidebar_plugins`        | 后台侧边栏"插件与路由"分组  | 添加导航链接   |
| `host_form_after_auth`         | 主机编辑页 - 认证信息之后  | 添加主机配置字段 |
| `host_form_after_providers`    | 主机编辑页 - 提供商分配之后 | 添加主机扩展配置 |
| `system_config_after_sections` | 系统设置页 - 所有区块之后  | 添加插件配置区块 |

#### 模板标签用法

```html
{% load plugin_extensions %}

{% plugin_extensions "slot_name" %}
{% plugin_nav_items %}
{% plugin_has_extensions "slot" as has_ext %}
```

### 5.4 URLProvider 实现

```python
def get_url_patterns(self) -> List[dict]:
    return [
        {
            "prefix": "my_plugin/",
            "module": "plugins.my_plugin.urls_admin",
            "namespace": "admin_plugins",
            "section": URLProvider.ADMIN,
        },
    ]
```

section 取值：`URLProvider.ADMIN` / `URLProvider.PROVIDER` / `URLProvider.PUBLIC`

### 5.5 EventHook 使用

```python
def initialize(self) -> bool:
    from plugins.core.plugin_manager import get_plugin_manager
    pm = get_plugin_manager()
    pm.register_hook("event_name", self._handler)
    return True

def shutdown(self) -> bool:
    from plugins.core.plugin_manager import get_plugin_manager
    pm = get_plugin_manager()
    pm.get_hook("event_name").unregister(self._handler)
    return True

def _handler(self, **kwargs):
    pass
```

> 如果需要响应 Django ORM 信号（如 `post_save`），直接使用 Django signals 框架，无需经过 PluginManager。参考 `plugins/signals.py`。

### 5.6 独立 Django App 配置

当插件拥有自有模型时，必须创建 `apps.py` 并注册到 `INSTALLED_APPS`：

```python
# plugins/my_plugin/apps.py
from django.apps import AppConfig

class MyPluginAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plugins.my_plugin"
    label = "my_plugin"
    verbose_name = "我的插件"
```

在 `config/settings.py` 的 `INSTALLED_APPS` 中添加 `"plugins.my_plugin"`。

模型中必须设置 `app_label`：

```python
class MyModel(models.Model):
    class Meta:
        app_label = "my_plugin"
```

***

## 6. 注册配置

### 6.1 plugins.toml 注册

在 `plugins/plugins.toml` 中添加：

```toml
[builtin.my_plugin]
name = "My Plugin"
module = "plugins.my_plugin"
class = "MyPlugin"
description = "插件描述"
version = "1.0.0"
enabled = true
```

- `module`：插件主类所在的 Python 模块路径
- `class`：插件主类的类名
- `enabled`：设为 `false` 可跳过加载

### 6.2 INSTALLED\_APPS 注册

仅当插件拥有独立 Django App（有 `apps.py`）时需要：

```python
# config/settings.py
INSTALLED_APPS = [
    # ...
    "plugins.my_plugin",
]
```

### 6.3 数据库迁移

仅当插件拥有自有模型时需要：

```bash
uv run python manage.py makemigrations my_plugin
uv run python manage.py migrate
```

***

## 7. 解耦规范

### ✅ 允许

| 操作            | 方式                                        |
| ------------- | ----------------------------------------- |
| 访问核心模型        | `apps.get_model("operations", "Product")` |
| 读取插件配置        | `PluginConfiguration` + `PluginRecord`    |
| 注入 UI 内容      | `UIExtensionProvider` + 预定义 slot          |
| 注册 URL 路由     | `URLProvider` + `dynamic_urls`            |
| 注册服务          | `ServiceProvider` + `ServiceRegistry`     |
| 响应事件          | `EventHook` / Django signals              |
| 注册 Django App | `apps.py` + `INSTALLED_APPS`              |

### ❌ 禁止

| 操作                                           | 原因              |
| -------------------------------------------- | --------------- |
| `from apps.operations.models import Product` | 直接 import 紧耦合   |
| 修改核心模板文件                                     | 应使用 UI 扩展点      |
| 修改核心 URL 配置                                  | 应使用 URLProvider |
| 为核心模型创建迁移                                    | 只能操作自有模型        |
| monkey-patch 核心代码                            | 违反 LICENSE 附加条款 |

### 延迟导入模式

对于无法通过 `apps.get_model()` 获取的工具函数，使用延迟导入：

```python
# ❌ 直接导入
from apps.accounts.provider_decorators import admin_required

# ✅ 延迟导入
def _get_admin_required():
    from apps.accounts.provider_decorators import admin_required
    return admin_required

@_get_admin_required()
def my_view(request):
    ...
```

### 访问核心模型

```python
# ✅ 通过 apps.get_model
from django.apps import apps
Product = apps.get_model("operations", "Product")

# ✅ 通过 PluginConfiguration 读取配置
from django.apps import apps
PluginRecord = apps.get_model("plugins", "PluginRecord")
PluginConfiguration = apps.get_model("plugins", "PluginConfiguration")
```

***

## 8. 样式规范

插件 UI 必须遵循 ZASCA 项目的双轨样式隔离规范。

### 8.1 后台（提供商/管理端）

设计语言：科技监控风 + 毛玻璃

| 元素       | 样式公式                                                                                                                                                                                                                |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 科技风毛玻璃卡片 | `bg-slate-950/70 backdrop-blur-xl border border-slate-700/50 rounded-md shadow-none`                                                                                                                                |
| 发光输入框    | `w-full bg-slate-900/50 backdrop-blur-sm border border-slate-700/50 rounded px-3 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/50 focus:border-cyan-500 transition` |
| 科技风主按钮   | `bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded-md font-medium shadow-[0_0_15px_-3px_rgba(34,211,238,0.3)] transition`                                                                                  |
| 科技风毛玻璃弹窗 | `bg-slate-950/80 backdrop-blur-2xl border border-cyan-500/20 rounded-lg shadow-2xl`                                                                                                                                 |
| 图标颜色     | `text-cyan-400` 或 `text-slate-400`                                                                                                                                                                                  |
| 圆角       | `rounded-md` (6px) 或 `rounded-lg` (8px)                                                                                                                                                                             |

### 8.2 前台（用户端）

设计语言：Material Design 3 + 毛玻璃（使用 `md:` 命名空间）

| 元素      | 样式公式                                                                                                                                                                                  |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 毛玻璃卡片   | `bg-md-surface-container/70 backdrop-blur-xl border border-white/10 rounded-md-lg shadow-2xl`                                                                                         |
| MD3 输入框 | `w-full bg-md-surface/50 border border-md-outline/50 rounded-md px-4 py-3 text-md-on-surface placeholder-md-outline focus:outline-none focus:ring-2 focus:ring-md-primary transition` |
| 圆角      | 按钮/输入框 `rounded-md` (12px)，卡片 `rounded-md-lg` (16px)，弹窗/FAB `rounded-md-xl` (28px)                                                                                                    |

### 8.3 通用规范

- 严禁编写原生 `<style>` 或内联样式，必须使用 Tailwind 原子类
- 严禁使用 Bootstrap
- 严禁引用任何 CDN 资源
- 图标统一使用 `<span class="material-symbols-rounded">icon_name</span>`
- 前后台样式严禁混用

***

## 9. 可视化归属声明（LICENSE 强制要求）

> ⚠️ 这是 LICENSE Section 3(d) 的强制要求，违反此条款将导致插件失去 AGPLv3 豁免资格。

### 适用范围

| UI 元素类型       | 是否需要归属 | 归属方式           |
| ------------- | ------ | -------------- |
| 侧边栏导航链接       | ✅      | 附带 "Plugin" 徽章 |
| 注入的面板/卡片/小组件  | ✅      | 标题标签或页脚注释      |
| 模态框/弹窗/浮层     | ✅      | 标题栏或页脚标注插件名称   |
| 通知/Toast/警告横幅 | ✅      | 消息文本中标识来源      |
| 插件提供的完整页面     | ✅      | 页脚或标题徽章声明      |
| 纯后台服务（无 UI）   | ❌      | 仅需源码声明         |
| 纯事件监听（无 UI）   | ❌      | 仅需源码声明         |

### 归属徽章样式（后台）

```python
f'<span class="ml-auto text-[10px] '
f'px-1.5 py-0.5 rounded '
f'bg-cyan-500/10 text-cyan-400 '
f'border border-cyan-500/20 '
f'font-medium">Plugin</span>'
```

### context\_callback 归属字段

使用 `TEMPLATE` 类型扩展时，`context_callback` 必须返回：

```python
def _get_data(self):
    data = {"key": "value"}
    data["plugin_name"] = self.name
    data["plugin_attribution"] = f"Provided by {self.name} (ZASCA Plugin)"
    return data
```

### ❌ 不合规做法

- 仅在 HTML 注释中标注
- 隐藏在 tooltip 中
- 极小/极浅的文字
- 需要展开才能看到

***

## 10. 验证清单

插件开发完成后，AI 必须逐项检查：

### 代码结构

- [ ] 插件目录位于 `plugins/` 下
- [ ] `__init__.py` 存在
- [ ] 插件主类继承 `PluginInterface`
- [ ] `initialize()` 和 `shutdown()` 已实现
- [ ] `plugin_id` 与目录名一致
- [ ] 类名使用 PascalCase + Plugin 后缀

### 注册配置

- [ ] `plugins/plugins.toml` 中已注册
- [ ] `module` 路径正确指向插件主类所在模块
- [ ] `class` 名称与实际类名一致
- [ ] 如有独立 Django App，已添加到 `INSTALLED_APPS`
- [ ] 如有模型，已执行 `makemigrations` 和 `migrate`

### 解耦合规

- [ ] 无直接 import 核心模型（使用 `apps.get_model()`）
- [ ] 无修改核心模板文件（使用 UI 扩展点）
- [ ] 无修改核心 URL 配置（使用 URLProvider）
- [ ] 无为核心模型创建迁移
- [ ] 无 monkey-patch 核心代码
- [ ] 工具函数使用延迟导入

### 样式合规

- [ ] 后台 UI 使用 `slate/cyan` 色系，无 `md:` 命名空间
- [ ] 前台 UI 使用 `md:` 命名空间
- [ ] 无原生 `<style>` 或内联样式
- [ ] 无 Bootstrap 组件
- [ ] 无 CDN 引用
- [ ] 图标使用 `material-symbols-rounded`

### 归属声明

- [ ] 所有 `NAV_ITEM` 附带可见 "Plugin" 徽章
- [ ] 所有 `SECTION` / `HTML` / `TEMPLATE` 包含归属标签
- [ ] 所有模态框/弹窗标注插件名称
- [ ] 所有通知/Toast 标识插件来源
- [ ] 所有 `URLProvider` 页面包含页脚归属声明
- [ ] `context_callback` 返回 `plugin_name` 和 `plugin_attribution`
- [ ] 归属标识在正常使用条件下视觉可辨

### 运行验证

```bash
uv run python manage.py check
```

***

## 11. 参考文件索引

| 文件                                                    | 用途                                                                                                                 |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `plugins/core/base.py`                                | 所有接口定义：PluginInterface, ServiceProvider, UIExtensionProvider, URLProvider, EventHook, UIExtension, ServiceRegistry |
| `plugins/core/plugin_manager.py`                      | 插件管理器：加载、卸载、钩子、UI 扩展收集、URL 模式收集                                                                                    |
| `plugins/available_plugins.py`                        | 从 plugins.toml 加载插件配置                                                                                              |
| `plugins/models.py`                                   | PluginRecord, PluginConfiguration 数据模型                                                                             |
| `plugins/signals.py`                                  | Django 信号处理器示例                                                                                                     |
| `plugins/apps.py`                                     | Django AppConfig，启动时自动加载所有插件                                                                                       |
| `plugins/dynamic_urls.py`                             | 动态 URL 路由收集                                                                                                        |
| `plugins/templatetags/plugin_extensions.py`           | 模板标签：plugin\_extensions, plugin\_nav\_items, plugin\_has\_extensions                                               |
| `plugins/sample_plugins/demo_auth_plugin.py`          | ServiceProvider 示例                                                                                                 |
| `plugins/sample_plugins/email_notification_plugin.py` | EventHook 示例                                                                                                       |
| `plugins/sample_plugins/ui_extension_plugin.py`       | UIExtensionProvider 示例                                                                                             |
| `plugins/sample_plugins/full_featured_plugin.py`      | 完整功能插件示例（URLProvider + 独立 App）                                                                                     |
| `plugins/gateway/`                                    | 生产级插件参考（ServiceProvider + 独立接口定义）                                                                                  |
| `plugins/sample_plugins/PLUGIN_DEV_GUIDE.md`          | 人类开发者指南                                                                                                            |

