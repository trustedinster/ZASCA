# C端主机自动化初始化与安全认证系统

## 系统概述

本系统实现了符合共享技术契约的C端主机自动化初始化与安全认证功能，支持基于TOTP的双重验证机制，确保H端和C端之间的安全对接。

## 核心功能

### 1. 数据库设计

系统包含两个核心数据表：

#### InitialToken（初始令牌表）
| 字段名 | 类型 | 说明 |
|--------|------|------|
| token | String (PK) | AccessToken |
| host | ForeignKey | 关联的主机 |
| expires_at | Datetime | AccessToken过期时间 |
| status | Enum | `ISSUED`(已签发), `TOTP_VERIFIED`(已验证), `CONSUMED`(已消耗) |
| created_at | Datetime | 创建时间 |

#### ActiveSession（活动会话表）
| 字段名 | 类型 | 说明 |
|---------|------|------|
| session_token | String (PK) | 颁发给H端的临时凭证 |
| host | ForeignKey | 关联的主机 |
| bound_ip | String | **关键**：绑定的请求源IP |
| expires_at | Datetime | 24小时后的过期时间 |
| created_at | Datetime | 创建时间 |

### 2. API接口

#### A. TOTP验证接口
- **URL**: `POST /bootstrap/verify-totp/`
- **Request Body**:
```json
{
  "host_id": "Unique-Host-ID",
  "totp_code": "123456"
}
```

#### B. Token交换接口
- **URL**: `POST /bootstrap/exchange-token/`
- **Headers**: `Authorization: Bearer {AccessToken}`
- **Response**:
```json
{
  "success": true,
  "session_token": "new-session-uuid",
  "expires_in": 86400
}
```

#### C. 会话吊销接口
- **URL**: `DELETE /bootstrap/session/`
- **Headers**: `Authorization: Bearer {session_token}`

### 3. 安全机制

#### 密钥派生算法
严格按照共享技术契约实现：
1. 拼接字符串：`input_string = token + "|" + host_id + "|" + expires_at`
2. 哈希计算：`raw_hash = HMAC-SHA256(key="SHARED_STATIC_SALT", message=input_string)`
3. 截取与编码：取`raw_hash`的前20个字节，进行**Base32**编码

#### TOTP算法参数
- **算法**: HMAC-SHA1
- **时间步长**: 30秒
- **位数**: 6位数字
- **初始时间**: Unix Epoch (T0 = 0)

## 管理界面

系统集成到Django Admin中，提供以下功能：
- 初始令牌管理
- 活动会话监控
- 一键生成令牌
- 状态监控

## 自动化任务

- 定期清理过期的活动会话
- 定期清理过期的初始令牌

## 配置要求

在`settings.py`中配置共享盐值：
```python
BOOTSTRAP_SHARED_SALT = os.environ.get('BOOTSTRAP_SHARED_SALT', 'MY_SECRET_2024')
```

## 使用流程

1. 管理员在Django Admin中生成初始令牌
2. 系统生成包含C端URL、令牌、主机ID等信息的Base64配置字符串
3. H端使用配置字符串进行初始化
4. 用户在C端输入H端显示的TOTP码进行验证
5. H端使用Access Token换取Session Token
6. 双方通过Session Token进行后续安全通信