# ZASCA 用户开户系统说明文档

## 1. 系统概述

ZASCA 用户开户系统是一个为云电脑用户创建账户并在目标主机上创建相应用户的功能。系统利用WinRM协议连接到云电脑主机，在目标机器上创建用户账户，实现了零代理的多机管理。

## 2. 系统架构

### 2.1 核心模型

#### AccountOpeningRequest (开户申请模型)
- **功能**: 记录用户提交的开户申请信息
- **主要字段**:
  - 申请人信息 (applicant, contact_email, contact_phone)
  - 开户信息 (username, user_fullname, user_email, user_description)
  - 目标主机 (target_host)
  - 审核信息 (status, approved_by, approval_date, approval_notes)
  - 结果信息 (cloud_user_id, cloud_user_password, result_message)

#### CloudComputerUser (云电脑用户模型)
- **功能**: 记录在各个云电脑主机上创建的用户信息
- **主要字段**:
  - 用户信息 (username, fullname, email, description)
  - 主机信息 (host, status, is_admin, groups)
  - 创建信息 (created_from_request)

### 2.2 系统流程

1. **申请阶段**: 用户提交开户申请
2. **审核阶段**: 管理员审核申请
3. **处理阶段**: 系统连接目标主机并创建用户
4. **完成阶段**: 记录结果并更新状态

## 3. 功能特性

### 3.1 用户端功能
- **提交开户申请**: 普通用户可以提交开户申请
- **查看申请状态**: 查看自己提交的申请状态

### 3.2 管理员功能
- **审核申请**: 批准或拒绝开户申请
- **执行开户**: 在云电脑上创建用户账户
- **用户管理**: 管理已创建的云电脑用户
- **批量操作**: 支持批量审核和用户状态管理

### 3.3 统计功能
- **实时统计**: 显示开户申请和用户数量
- **仪表盘集成**: 在主仪表盘显示关键指标

## 4. 技术实现

### 4.1 WinRM 连接
- 使用 `utils.winrm_client.WinrmClient` 连接云电脑
- 通过 PowerShell 命令在远程主机上创建用户
- 自动生成安全密码

### 4.2 安全措施
- 权限控制: 区分普通用户和管理员权限
- 操作日志: 记录所有开户相关操作
- 密码安全: 使用强密码生成算法

## 5. 使用指南

### 5.1 普通用户使用流程
1. 访问 "提交开户申请" 页面
2. 填写申请信息 (用户名、姓名、邮箱等)
3. 选择目标主机
4. 提交申请并等待审核
5. 查看申请状态

### 5.2 管理员使用流程
1. 查看待处理的开户申请
2. 审核申请信息
3. 批准或拒绝申请
4. 对于已批准的申请，执行开户操作
5. 监控开户结果

### 5.3 URL 路径
- `/operations/account-openings/` - 开户申请列表
- `/operations/account-openings/create/` - 创建开户申请
- `/operations/account-openings/<id>/approve/` - 批准申请
- `/operations/account-openings/<id>/reject/` - 拒绝申请
- `/operations/account-openings/<id>/process/` - 处理开户
- `/operations/cloud-users/` - 云电脑用户列表

## 6. 管理后台

在 Django 管理后台中提供了以下功能：
- AccountOpeningRequest: 开户申请管理
- CloudComputerUser: 云电脑用户管理
- OperationLog: 操作日志管理
- SystemTask: 系统任务管理

## 7. 错误处理

系统包含完善的错误处理机制：
- 网络连接错误
- 主机认证失败
- 用户创建失败
- 权限不足处理

## 8. 扩展性

系统设计具有良好的扩展性：
- 支持多种云电脑主机类型
- 可扩展不同类型的用户权限
- 模块化设计便于功能扩展

## 9. 注意事项

1. 确保目标主机已启用 WinRM 服务
2. 管理员需要有在目标主机上创建用户的权限
3. 定期检查和清理过期的开户申请
4. 监控系统操作日志以确保安全性

## 10. 维护建议

1. 定期备份开户申请和用户数据
2. 监控系统性能和响应时间
3. 更新 WinRM 连接配置以适应网络变化
4. 定期审查用户权限和安全策略