# Django 迁移修复指南

## 问题描述
远程服务器遇到以下错误：
```
django.db.migrations.exceptions.NodeNotFoundError: Migration plugins.0006_delete_qqverifyconfig_alter_pluginrecord_options_and_more dependencies reference nonexistent parent node ('plugins', '0005_auto_20260130_1041')
```

## 问题原因
远程服务器上存在本地 Git 仓库中没有的迁移文件，这些迁移已经被应用到数据库中，但依赖关系无法在当前的 Git 仓库中找到。

## 解决方案

### 步骤 1: 检查远程服务器上的迁移文件
在远程服务器上运行：
```bash
ls -la plugins/migrations/
```

### 步骤 2: 手动编辑问题迁移文件
找到 `plugins/migrations/0006_delete_qqverifyconfig_alter_pluginrecord_options_and_more.py` 文件，并修改其依赖部分：

将：
```python
dependencies = [
    ('plugins', '0005_auto_20260130_1041'),  # 修改这一行
]
```

改为：
```python
dependencies = [
    ('plugins', '0003_auto_20260129_1808'),  # 指向已存在的迁移
]
```

### 步骤 3: 如果仍有问题，检查所有迁移文件
检查远程服务器上是否存在以下文件：
- `0004_auto_20260130_1034.py`
- `0005_auto_20260130_1041.py`

如果有，也需要确保它们的依赖关系正确。

### 步骤 4: 运行迁移
修复依赖后，运行：
```bash
python manage.py migrate
```

## 替代方案（如果上述方法不起作用）

如果修改依赖仍然有问题，可以在远程服务器上执行以下操作：

1. 检查 Django migrations 表中的记录：
```bash
python manage.py showmigrations
```

2. 如果发现未记录的已应用迁移，可以使用 --fake 标志来标记它们：
```bash
python manage.py migrate --fake plugins 0006_delete_qqverifyconfig_alter_pluginrecord_options_and_more
```

## 预防措施
为了避免将来出现此类问题：
1. 确保所有迁移文件都提交到 Git 仓库
2. 在生产环境部署前，先在测试环境中验证迁移
3. 遵循"先提交迁移文件，再应用迁移"的工作流程