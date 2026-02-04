# 多主题系统设计文档

> 创建日期: 2026-02-03
> 状态: 已实现

## 概述

为 ZASCA 系统实现多主题支持，包含 Material Design 3 和 Neumorphism（新拟态）两种主题风格，支持后台管理配置和移动端响应式适配。

## 功能特性

- **双主题支持**: Material Design 3 / Neumorphism
- **后台可配置**: 管理员可在后台切换主题、自定义颜色和品牌资源
- **页面内容管理**: 可编辑的登录欢迎语、公告、页脚等内容
- **仪表盘布局**: 可配置的组件显示顺序和响应式设置
- **移动端适配**: 前端和后台管理界面均支持移动端

## 技术方案

### 设计原则

1. **最小侵入**: 使用 CSS 变量覆盖 Bootstrap 5，不修改现有组件结构
2. **性能优先**: 使用 Django 缓存避免重复数据库查询
3. **灵活扩展**: JSONField 存储配置，便于未来扩展

### 数据模型

| 模型 | 用途 | 关键字段 |
|------|------|----------|
| `ThemeConfig` | 主题配置单例 | `active_theme`, `branding`(JSON), `custom_colors`(JSON) |
| `PageContent` | 可编辑内容 | `position`, `content`, `is_enabled` |
| `WidgetLayout` | 仪表盘布局 | `widget_type`, `display_order`, `responsive`(JSON) |

### CSS 架构

```
frontend/static/css/themes/
├── _variables.css       # 基础 CSS 变量
├── _responsive.css      # 移动端响应式
├── material-design-3.css # MD3 主题
└── neumorphism.css      # 新拟态主题
```

### 模板集成

```html
<html data-theme="material-design-3">
  <head>
    {% theme_head %}  <!-- 自动加载主题相关样式 -->
  </head>
</html>
```

---

## 部署步骤

### 1. 生成数据库迁移

```bash
python manage.py makemigrations themes
```

预期输出：
```
Migrations for 'themes':
  apps/themes/migrations/0001_initial.py
    - Create model ThemeConfig
    - Create model PageContent
    - Create model WidgetLayout
```

### 2. 应用数据库迁移

```bash
python manage.py migrate themes
```

预期输出：
```
Operations to perform:
  Apply all migrations: themes
Running migrations:
  Applying themes.0001_initial... OK
```

### 3. 收集静态文件

```bash
python manage.py collectstatic --noinput
```

这将复制以下文件到 `staticfiles/` 目录：
- `css/themes/*.css`
- `admin/css/responsive.css`
- `admin/js/responsive.js`

### 4. 初始化默认配置（可选）

在 Django shell 中创建默认主题配置：

```bash
python manage.py shell
```

```python
from apps.themes.models import ThemeConfig, PageContent

# 创建主题配置
config = ThemeConfig.objects.create(
    active_theme='material-design-3',
    enable_mobile_optimization=True
)

# 创建默认页面内容
PageContent.objects.create(
    position='login_welcome',
    title='欢迎使用',
    content='ZASCA 云电脑管理系统',
    is_enabled=True
)

PageContent.objects.create(
    position='footer_copyright',
    content='© 2026 ZASCA. All rights reserved.',
    is_enabled=True
)
```

### 5. 验证安装

1. 启动开发服务器：
   ```bash
   python manage.py runserver
   ```

2. 访问后台管理：`http://localhost:8000/admin/`

3. 检查以下内容：
   - 左侧菜单出现「主题管理」分组
   - 包含「主题配置」「页面内容」「组件布局」三个管理项
   - 移动端访问时侧边栏变为抽屉式

---

## 文件清单

### Python 模块

| 文件路径 | 说明 |
|----------|------|
| `apps/themes/__init__.py` | 应用入口 |
| `apps/themes/apps.py` | 应用配置 |
| `apps/themes/models.py` | 数据模型 |
| `apps/themes/admin.py` | 后台管理 |
| `apps/themes/context_processors.py` | 模板上下文处理器 |
| `apps/themes/templatetags/__init__.py` | 模板标签包 |
| `apps/themes/templatetags/theme_tags.py` | 模板标签 |

### 静态资源

| 文件路径 | 说明 |
|----------|------|
| `frontend/static/css/themes/_variables.css` | CSS 变量基础层 |
| `frontend/static/css/themes/_responsive.css` | 前端移动端响应式 |
| `frontend/static/css/themes/material-design-3.css` | MD3 主题样式 |
| `frontend/static/css/themes/neumorphism.css` | 新拟态主题样式 |
| `frontend/static/admin/css/responsive.css` | Admin 移动端样式 |
| `frontend/static/admin/js/responsive.js` | Admin 移动端交互 |

### 模板文件

| 文件路径 | 说明 |
|----------|------|
| `frontend/templates/themes/base_themed.html` | 主题基础模板 |
| `frontend/templates/themes/partials/theme_head.html` | 主题 head 片段 |
| `frontend/templates/admin/base_site.html` | Admin 模板覆盖 |

### 配置变更

| 文件 | 变更内容 |
|------|----------|
| `config/settings.py` | 添加 `apps.themes` 到 `INSTALLED_APPS` |
| `config/settings.py` | 添加主题上下文处理器到 `TEMPLATES.OPTIONS.context_processors` |

---

## 使用指南

### 在模板中使用主题

```html
{% extends "themes/base_themed.html" %}

{% block content %}
  <div class="card">
    <div class="card-body">
      内容将自动应用当前主题样式
    </div>
  </div>
{% endblock %}
```

### 获取页面内容

```html
{% load theme_tags %}

{# 方式1: 直接输出 #}
{% get_content 'login_welcome' '默认欢迎语' %}

{# 方式2: 赋值后使用 #}
{% get_content_obj 'dashboard_notice' as notice %}
{% if notice %}
  <h3>{{ notice.title }}</h3>
  {{ notice.content|safe }}
{% endif %}
```

### 获取品牌资源

```html
{% load theme_tags %}

<img src="{% branding 'logo' '/static/img/default-logo.png' %}">
```

### 获取主题颜色

```html
{% load theme_tags %}

<div style="background-color: {% theme_color 'primary' '#6750A4' %}">
  使用主题主色调
</div>
```

---

## 故障排除

### 问题: 主题样式未生效

1. 检查是否已运行 `collectstatic`
2. 确认模板使用了 `data-theme` 属性
3. 清除浏览器缓存

### 问题: 后台管理未显示主题配置

1. 确认 `apps.themes` 已添加到 `INSTALLED_APPS`
2. 确认已运行 `migrate themes`
3. 检查 `apps/themes/admin.py` 是否正确注册

### 问题: 移动端样式未生效

1. 确认 `base_site.html` 模板已正确覆盖
2. 检查 `responsive.css` 和 `responsive.js` 文件是否存在
3. 确认 viewport meta 标签已添加

### 问题: 缓存未更新

在 Django Admin 中点击「清除缓存」按钮，或执行：

```python
from apps.themes.models import ThemeConfig
ThemeConfig.invalidate_cache()
```

---

## 扩展开发

### 添加新主题

1. 创建 `frontend/static/css/themes/new-theme.css`
2. 在 `ThemeConfig.THEME_CHOICES` 中添加选项
3. 运行 `collectstatic`

### 添加新页面内容位置

1. 在 `PageContent.POSITION_CHOICES` 中添加选项
2. 在模板中使用 `{% get_content 'new_position' %}`

### 自定义 CSS 变量

在后台「主题配置」的「自定义颜色」字段中输入 JSON：

```json
{
  "primary": "#FF5722",
  "secondary": "#607D8B",
  "accent": "#FFC107"
}
```

这将生成对应的 CSS 变量覆盖默认值。
