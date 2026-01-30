# ZASCA项目模型文档索引

## 文档概览

本文档集合详细介绍了ZASCA项目中的Django模型设计、实现和最佳实践。

## 文档目录

### 1. [Django模型编写指南](./django_models_guide.md)
- 模型基础概念和字段类型
- 模型定义和字段选项
- 模型关系和查询优化
- 实际项目示例和最佳实践

### 2. [模型关系与查询优化指南](./model_relationships_and_optimization.md)
- Django模型关系详解 (ForeignKey, OneToOneField, ManyToManyField)
- 查询优化技术 (select_related, prefetch_related)
- 数据库索引策略
- 高级查询技巧和性能监控

### 3. [模型安全与验证指南](./model_security_and_validation.md)
- 敏感数据保护和密码加密
- 输入验证层次结构
- 安全控制和数据脱敏
- 验证错误处理和安全审计

### 4. [插件系统模型设计指南](./plugin_system_models_guide.md)
- 插件系统模型结构 (PluginRecord, PluginConfiguration)
- 状态同步机制和避免循环调用
- 插件接口设计和管理界面集成
- 示例插件实现

## 模型概览

### Accounts应用模型
- **User**: 自定义用户模型，扩展Django默认用户
- **UserProfile**: 用户资料模型
- **LoginLog**: 登录日志模型

### Dashboard应用模型
- **SystemStats**: 系统统计模型
- **DashboardWidget**: 仪表盘组件模型
- **UserActivity**: 用户活动模型
- **SystemConfig**: 系统配置模型

### Hosts应用模型
- **Host**: 主机模型，包含连接信息和加密密码
- **HostGroup**: 主机组模型，用于分组管理

### Operations应用模型
- **PublicHostInfo**: 公开主机信息模型
- **SystemTask**: 系统任务模型
- **Product**: 产品模型
- **AccountOpeningRequest**: 开户申请模型
- **CloudComputerUser**: 云电脑用户模型

### Plugins应用模型
- **PluginRecord**: 插件记录模型
- **PluginConfiguration**: 插件配置模型

## 设计原则

1. **安全性**: 所有敏感数据均加密存储
2. **可扩展性**: 支持插件系统和模块化设计
3. **性能优化**: 合理的索引和查询优化
4. **数据完整性**: 完整的验证和约束机制
5. **用户体验**: 支持复杂的业务逻辑和交互

## 代码规范

- 所有模型都遵循Django编码规范
- 使用国际化支持 (verbose_name, help_text)
- 实现适当的索引以优化查询性能
- 遵循单一职责原则，保持模型简洁
- 使用适当的数据库约束保证数据完整性

## 维护指南

- 修改模型前请备份数据库
- 仔细测试数据库迁移脚本
- 遵循向后兼容原则
- 文档化所有重要的模型变更

## 贡献指南

- 为新模型添加适当的单元测试
- 确保所有字段都有适当的验证
- 提供清晰的help_text和verbose_name
- 遵循项目现有的代码风格和命名约定