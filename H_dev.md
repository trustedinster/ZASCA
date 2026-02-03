# H端开发者联合调试配合指南

本文档说明H端开发者在与C端进行联合调试时需要配合的事项和具体操作。

## 1. 调试前准备工作

### 1.1 确认技术契约实现
H端开发者需要确保以下技术契约已正确实现：

- [ ] **数据载荷解析**：正确解析C端提供的Base64编码JSON
- [ ] **密钥派生算法**：使用`token + "|" + host_id + "|" + expires_at`拼接字符串
- [ ] **HMAC-SHA256计算**：使用盐值`MY_SECRET_2024`
- [ ] **TOTP算法参数**：SHA1、30秒时间步长、6位数字

### 1.2 初始化逻辑实现
确保已实现H端初始化逻辑：

- [ ] 获取用户输入的Base64字符串
- [ ] Base64解码得到JSON
- [ ] 解析JSON提取：`c_side_url`, `token`, `host_id`, `expires_at`
- [ ] 将这些信息持久化存储到本地配置

## 2. API接口调用配合

### 2.1 TOTP生成与展示
**实现要求**：
- [ ] **计算K_TOTP**：严格按照契约计算Base32字符串
- [ ] **生成Code**：使用标准TOTP库，设置`digits=6`, `interval=30`
- [ ] **用户交互**：在控制台打印或UI显示："请访问C端管理后台，输入主机ID [host_id] 和验证码 [totp_code] 进行激活"

### 2.2 Token交换接口调用
**接口**：`POST /api/exchange_token` 或 `/bootstrap/exchange-token/`

H端需实现以下逻辑：
```javascript
// 构造HTTP POST请求
const response = await fetch(`${c_side_url}/api/exchange_token`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

**配合要点**：
- [ ] 使用Bearer模式传递AccessToken
- [ ] 正确处理响应：成功时获取`session_token`，失败时给出相应提示
- [ ] 处理特定错误"Wait To Active"：提示用户尚未在C端完成TOTP验证

### 2.3 业务请求处理
- [ ] 每次请求Header携带`Authorization: Bearer {session_token}`
- [ ] 实现IP变化检测：网络环境变化时提示用户需要重新绑定

### 2.4 会话吊销接口调用
**接口**：`DELETE /api/session` 或 `/bootstrap/session/`

H端程序正常退出时：
- [ ] 构造HTTP DELETE请求
- [ ] Header携带`Authorization: Bearer {session_token}`
- [ ] 发送请求后本地清除`session_token`

## 3. 联合调试流程

### 3.1 初始配置阶段
1. 用户输入C端提供的Base64配置字符串
2. H端解析并提取配置信息
3. 计算TOTP密钥并生成当前验证码
4. 在控制台显示主机ID和TOTP码，提示用户在C端输入

### 3.2 TOTP验证阶段
1. 用户在C端管理界面输入主机ID和H端显示的TOTP码
2. C端验证TOTP码并更新状态
3. H端调用Token交换接口获取session_token

### 3.3 问题排查配合

如果调试过程中出现问题，请按以下方式配合：

**网络问题排查**：
- [ ] 确认C端API接口URL可访问
- [ ] 检查网络代理设置
- [ ] 验证HTTPS证书处理（如需要忽略证书验证）

**认证问题排查**：
- [ ] 双方确认密钥派生算法完全一致（盐值、拼接顺序、哈希算法）
- [ ] 确认TOTP参数完全一致（时间步长、位数、算法）
- [ ] 检查Base64解码是否正确

**时间同步问题**：
- [ ] 确认H端系统时间准确（TOTP对时间敏感）
- [ ] 验证TOTP码生成时间窗口设置

## 4. 异常处理建议

### 4.1 网络超时处理
- [ ] 换取Token时设置重试机制（如3次，间隔5秒）
- [ ] 实现合理的超时设置（建议30秒）

### 4.2 Base64格式错误处理
- [ ] 程序启动时校验，若解码失败直接报错退出
- [ ] 提供清晰的错误提示信息

### 4.3 状态检查
- [ ] 定期检查session_token有效性
- [ ] 实现失效后的重新认证流程

## 5. 调试工具支持

为了便于调试，H端应提供以下支持：
- [ ] 详细的请求/响应日志记录
- [ ] 网络请求的详细信息输出（URL、Headers、Body）
- [ ] TOTP码生成过程的日志
- [ ] 状态变化的跟踪记录

## 6. 调试沟通方式

在调试过程中，如遇到问题请提供以下信息以便快速定位：
- [ ] 完整的请求/响应日志
- [ ] 相关的时间戳
- [ ] 使用的具体token、host_id等标识信息
- [ ] 当前H端的系统时间
- [ ] 预期行为与实际行为的差异
- [ ] TOTP码的生成时间点

## 7. 测试用例配合

请准备以下测试用例配合调试：

1. **正常流程测试**：完整走通配置解析、TOTP生成、Token交换流程
2. **错误码测试**：验证不同错误状态码的处理
3. **网络重试测试**：验证重试机制的有效性
4. **时间偏移测试**：验证时间偏移对TOTP验证的影响
5. **IP变更测试**：验证网络IP变化后的处理逻辑