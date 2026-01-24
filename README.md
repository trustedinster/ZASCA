# ZASCA (Zero Agent Share Computer Administrator)

## 简介

ZASCA（Zero Agent Share Computer Administrator）是一个不需要在共享计算机上额外安装软件的多机管理工具。它采用基于Winrm的连接方式，可以实现对多台云电脑的统一管理和开户服务。

## 特性

- 🚀 **零代理部署**：采用Winrm连接方式，无需在主机端额外安装软件
- 🔒 **安全可靠**：借助微软成熟的Winrm方案，不怕被恶意用户关闭
- 🌐 **多机管理**：支持一控多架构，可同时管理多台云电脑
- 💻 **跨平台支持**：Web端可在能运行Python 3.10以上的任意Linux、Windows版本上使用
- 🔌 **灵活部署**：主机端只需端口映射，不强制要求公网IPv4

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

## 使用指南

### 配置云电脑端

1. 在Windows主机上启用Winrm服务
```powershell
winrm quickconfig -q
winrm set winrm/config/client '@{TrustedHosts="*"}'
```

2. 配置防火墙规则，允许Winrm端口（默认5985/5986）

3. 在Web端添加主机信息

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
│   ├── operations/     # 操作记录应用
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

MIT License

## 联系方式

- 项目主页: https://github.com/trustedinster/ZASCA
- 问题反馈: https://github.com/trustedinster/ZASCA/issues
