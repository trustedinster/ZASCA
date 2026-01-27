README.md
# ZASCA (Zero Agent Share Computer Administrator)

## 简介

ZASCA（Zero Agent Share Computer Administrator）是一个不需要在共享计算机上额外安装软件的多机管理工具。它采用基于Winrm的连接方式，可以实现对多台云电脑的统一管理和开户服务。

## 特性

- 🚀 **零代理部署**：采用Winrm连接方式，无需在主机端额外安装软件
- 🔒 **安全可靠**：借助微软成熟的Winrm方案，不怕被恶意用户关闭
- 🌐 **多机管理**：支持一控多架构，可同时管理多台云电脑
- 💻 **跨平台支持**：Web端可在能运行Python 3.10以上的任意Linux、Windows版本上使用
- 🔌 **灵活部署**：主机端只需端口映射，不强制要求公网IPv4
- 👥 **用户开户系统**：支持用户自助申请和管理员审核流程
- 🎯 **演示模式**：内置DEMO模式，方便快速体验系统功能

## 系统架构

### Web端
- 提供网站供用户注册开户
- 基于Django框架实现
- 支持Python 3.10+
- 可部署在Linux或Windows系统上
- 使用Winrm连接到云电脑端

### 云电脑端（主机端）
- 支持Windows Server 2016+
- 支持Windows 10+
- 需配置Winrm服务
- 需要端口映射到公网或内网可访问

## 技术栈

- **后端框架**: Django 4.2+
- **数据库**: PostgreSQL/MySQL
- **远程连接**: pywinrm
- **前端**: Bootstrap 5 + jQuery
- **异步任务**: Celery + Redis

## 快速开始

### 环境要求

- Python 3.10+
- PostgreSQL 12+ 或 MySQL 8.0+
- Redis 6.0+

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/ZASCA.git
cd ZASCA
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，配置数据库、Redis等连接信息
```

5. 数据库迁移
```bash
python manage.py makemigrations
python manage.py migrate
```

6. 创建超级用户
```bash
python manage.py createsuperuser
```

7. 启动服务
```bash
python manage.py runserver
```

## DEMO模式

### 启用DEMO模式

ZASCA提供便捷的DEMO模式，方便快速体验系统功能，无需配置数据库和外部服务。

```bash
# 设置环境变量启用DEMO模式
export ZASCA_DEMO=1

# 或者在一行命令中运行
ZASCA_DEMO=1 python manage.py runserver
```

### DEMO模式特性

- 🔐 **数据库**: 使用 DEMO.sqlite3 (数据不会持久保存)
- 👤 **预设用户**:
  - 用户名: User, 密码: demo_user_password
  - 用户名: Admin, 密码: demo_admin_password
  - 用户名: SuperAdmin, 密码: DemoSuperAdmin123!
- 🛠️ **主机状态**: 所有主机始终显示为在线状态
- 📧 **邮件功能**: 邮件发送功能被模拟（不会实际发送邮件）
- 🚀 **WinRM指令**: 不会实际执行（仅模拟）
- 🔐 **密码策略**: 忽略密码复杂度要求
- 📋 **权限设定**: 
  - Admin用户具有工作人员权限但不是超级用户
  - 拥有特定权限：View登录日志、View日志记录、View开户申请、Change开户申请、View云电脑用户、Change云电脑用户、View产品

### DEMO登录界面

在DEMO模式下，登录页面将显示用户选择下拉框：
- 选择"User (demo)"或"Admin (demo)"将自动填入对应账号和密码
- 用户名和密码输入框将被禁用（只读状态）
- 如需使用其他账户，可选择"-- 选择DEMO用户 (留空则手动输入) --"后手动输入账号信息

## 使用指南

### 配置云电脑端

1. 在Windows主机上启用Winrm服务
```powershell
winrm quickconfig -q
winrm set winrm/config/client '@{TrustedHosts="*"}'
```

2. 配置防火墙规则，允许Winrm端口（默认5985/5986）

3. 在Web端添加主机信息

### 用户开户系统

#### 系统概述
ZASCA 用户开户系统是一个为云电脑用户创建账户并在目标主机上创建相应用户的功能。系统利用WinRM协议连接到云电脑主机，在目标机器上创建用户账户，实现了零代理的多机管理。

#### 核心模型
- **AccountOpeningRequest (开户申请模型)**: 记录用户提交的开户申请信息
  - 申请人信息 (applicant, contact_email, contact_phone)
  - 开户信息 (username, user_fullname, user_email, user_description)
  - 目标主机 (target_host)
  - 审核信息 (status, approved_by, approval_date, approval_notes)
  - 结果信息 (cloud_user_id, cloud_user_password, result_message)

- **CloudComputerUser (云电脑用户模型)**: 记录在各个云电脑主机上创建的用户信息
  - 用户信息 (username, fullname, email, description)
  - 主机信息 (host, status, is_admin, groups)
  - 创建信息 (created_from_request)

#### 系统流程
1. **申请阶段**: 用户提交开户申请
2. **审核阶段**: 管理员审核申请
3. **处理阶段**: 系统连接目标主机并创建用户
4. **完成阶段**: 记录结果并更新状态

#### 用户端功能
- **提交开户申请**: 普通用户可以提交开户申请
- **查看申请状态**: 查看自己提交的申请状态

#### 管理员功能
- **审核申请**: 批准或拒绝开户申请
- **执行开户**: 在云电脑上创建用户账户
- **用户管理**: 管理已创建的云电脑用户
- **批量操作**: 支持批量审核和用户状态管理

#### 使用流程
1. **普通用户使用流程**
   - 访问 "提交开户申请" 页面
   - 填写申请信息 (用户名、姓名、邮箱等)
   - 选择目标主机
   - 提交申请并等待审核
   - 查看申请状态

2. **管理员使用流程**
   - 查看待处理的开户申请
   - 审核申请信息
   - 批准或拒绝申请
   - 对于已批准的申请，执行开户操作
   - 监控开户结果

#### URL 路径
- `/operations/account-openings/` - 开户申请列表
- `/operations/account-openings/create/` - 创建开户申请
- `/operations/account-openings/<id>/approve/` - 批准申请
- `/operations/account-openings/<id>/reject/` - 拒绝申请
- `/operations/account-openings/<id>/process/` - 处理开户
- `/operations/cloud-users/` - 云电脑用户列表

### 用户开户流程

1. 管理员在Web端创建开户请求
2. 系统通过Winrm连接到目标主机
3. 在主机上创建用户账户
4. 配置用户权限和资源限制
5. 返回开户结果

## 项目结构

```
ZASCA/
├── apps/
│   ├── accounts/       # 用户管理应用
│   ├── hosts/          # 主机管理应用
│   ├── operations/     # 操作记录应用（含开户系统）
│   └── dashboard/      # 仪表盘应用
├── config/             # 配置文件
├── static/             # 静态文件
├── templates/          # 模板文件
├── utils/              # 工具函数
├── manage.py
├── requirements.txt
└── README.md
```

## 安全说明

1. 使用HTTPS加密传输
2. Winrm连接使用SSL加密
3. 实施严格的访问控制
4. 定期审计操作日志
5. 使用强密码策略

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

GNU GENERAL PUBLIC LICENSE Version 2

本软件根据GPL 2.0许可证发布。您可以自由使用、修改和分发本软件，
但必须保留原始版权声明和许可证声明。

## 联系方式

- 项目主页: https://github.com/trustedinster/ZASCA
- 问题反馈: https://github.com/trustedinster/ZASCA/issues