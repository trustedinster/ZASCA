# 远程服务器迁移修复说明

## 问题描述
远程服务器在执行 `python manage.py migrate` 时遇到错误：
```
django.db.utils.OperationalError: no such column: ""requested_password""
```

## 问题原因
数据库中的 [AccountOpeningRequest](file:///Users/Supercmd/Desktop/Python/ZASCA/apps/operations/models.py#L44-L126) 表没有 `requested_password` 字段，但新生成的迁移试图删除该字段。

## 解决方案

在远程服务器上按顺序执行以下命令：

```bash
# 1. 首先标记有问题的迁移为已应用（但不实际执行）
python manage.py migrate operations 0003 --fake

# 2. 然后继续执行后续迁移
python manage.py migrate
```

或者，如果您已经执行了上面的命令并仍然遇到问题，您可能需要：

```bash
# 1. 拉取最新的代码更改
git pull origin master

# 2. 标记有问题的迁移为已应用
python manage.py migrate operations 0003_remove_accountopeningrequest_requested_password_and_more --fake

# 3. 然后继续执行后续迁移
python manage.py migrate
```

## 说明
- 我们添加了一个手动修复迁移 [0003_manual_fix.py](file:///Users/Supercmd/Desktop/Python/ZASCA/apps/operations/migrations/0003_manual_fix.py)，它不执行任何数据库操作
- 通过使用 `--fake` 参数，我们告诉 Django 这个迁移已经应用，但实际上没有执行任何操作
- 这样可以解决数据库状态与迁移历史之间的不匹配问题