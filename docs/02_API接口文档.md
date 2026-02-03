# ZASCA API 接口文档

## 1. API 设计规范

### 1.1 设计原则
- **RESTful 风格**：遵循 REST 架构约束
- **版本化管理**：API 版本通过 URL 路径管理 (`/api/v1/`)
- **状态码规范**：使用标准 HTTP 状态码
- **JSON 格式**：请求和响应均使用 JSON 格式
- **安全性**：所有 API 都需要认证授权

### 1.2 响应格式标准

#### 成功响应
```json
{
    "success": true,
    "data": {},
    "message": "操作成功",
    "timestamp": "2026-02-03T10:30:00Z"
}
```

#### 错误响应
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "参数验证失败",
        "details": {
            "field": "username",
            "reason": "用户名不能为空"
        }
    },
    "timestamp": "2026-02-03T10:30:00Z"
}
```

## 2. 认证与授权

### 2.1 认证方式
使用 Django Session 认证，通过 Cookie 传递 sessionid

### 2.2 权限控制
- 基于 Django 内置权限系统
- 对象级别的权限检查
- 主机维度的数据隔离

## 3. 主机管理 API

### 3.1 获取主机列表
```
GET /api/v1/hosts/
```

**参数：**
- `page` (integer, optional): 页码，默认 1
- `page_size` (integer, optional): 每页数量，默认 20
- `status` (string, optional): 主机状态 (active/maintenance/disabled)
- `search` (string, optional): 搜索关键词
- `group_id` (integer, optional): 主机组ID

**响应示例：**
```json
{
    "success": true,
    "data": {
        "count": 45,
        "next": "/api/v1/hosts/?page=2",
        "previous": null,
        "results": [
            {
                "id": 1,
                "hostname": "WIN-SERVER-001",
                "ip_address": "192.168.1.100",
                "description": "主数据库服务器",
                "os_version": "Windows Server 2019",
                "status": "active",
                "is_online": true,
                "last_heartbeat": "2026-02-03T10:15:30Z",
                "tags": ["database", "production"],
                "created_at": "2026-01-15T09:30:00Z"
            }
        ]
    },
    "timestamp": "2026-02-03T10:30:00Z"
}
```

### 3.2 获取主机详情
```
GET /api/v1/hosts/{id}/
```

**响应示例：**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "hostname": "WIN-SERVER-001",
        "ip_address": "192.168.1.100",
        "description": "主数据库服务器",
        "os_version": "Windows Server 2019",
        "cpu_info": "Intel Xeon E5-2680 v4 @ 2.40GHz",
        "memory_gb": 32,
        "disk_space_gb": 1024,
        "status": "active",
        "is_online": true,
        "last_heartbeat": "2026-02-03T10:15:30Z",
        "winrm_port": 5985,
        "winrm_https": false,
        "certificate_fingerprint": "SHA256:ABCDEF...",
        "tags": ["database", "production"],
        "metadata": {
            "location": "北京机房A区",
            "owner": "IT部门"
        },
        "groups": [
            {
                "id": 1,
                "name": "生产环境服务器",
                "description": "生产环境的所有服务器"
            }
        ],
        "permissions": {
            "can_read": true,
            "can_operate": true,
            "can_admin": false
        },
        "created_by": {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com"
        },
        "created_at": "2026-01-15T09:30:00Z",
        "updated_at": "2026-02-03T10:15:30Z"
    },
    "timestamp": "2026-02-03T10:30:00Z"
}
```

### 3.3 创建主机
```
POST /api/v1/hosts/
```

**请求体：**
```json
{
    "hostname": "NEW-WIN-SERVER",
    "ip_address": "192.168.1.101",
    "description": "新的应用服务器",
    "winrm_username": "administrator",
    "winrm_password": "SecurePassword123!",
    "winrm_port": 5985,
    "winrm_https": false,
    "tags": ["application", "test"],
    "group_ids": [2, 3]
}
```

### 3.4 更新主机
```
PUT /api/v1/hosts/{id}/
PATCH /api/v1/hosts/{id}/
```

### 3.5 删除主机
```
DELETE /api/v1/hosts/{id}/
```

### 3.6 测试主机连接
```
POST /api/v1/hosts/{id}/test-connection/
```

**响应示例：**
```json
{
    "success": true,
    "data": {
        "connected": true,
        "response_time_ms": 150,
        "message": "连接成功",
        "server_info": {
            "os_version": "Microsoft Windows NT 10.0.17763.0",
            "computer_name": "WIN-SERVER-001"
        }
    },
    "timestamp": "2026-02-03T10:30:00Z"
}
```

## 4. 工单管理 API

### 4.1 获取工单列表
```
GET /api/v1/tickets/
```

**参数：**
- `page` (integer, optional)
- `page_size` (integer, optional)
- `status` (string, optional): pending/approved/rejected/completed/cancelled
- `host_id` (integer, optional)
- `applicant_id` (integer, optional)

**响应示例：**
```json
{
    "success": true,
    "data": {
        "count": 23,
        "next": "/api/v1/tickets/?page=2",
        "previous": null,
        "results": [
            {
                "id": 1001,
                "request_number": "TKT-20260203-001",
                "title": "申请数据库服务器访问权限",
                "applicant": {
                    "id": 5,
                    "username": "zhangsan",
                    "email": "zhangsan@company.com"
                },
                "host": {
                    "id": 1,
                    "hostname": "DB-SERVER-01",
                    "ip_address": "192.168.1.100"
                },
                "status": "approved",
                "priority": "high",
                "created_at": "2026-02-03T09:15:00Z",
                "updated_at": "2026-02-03T10:20:00Z"
            }
        ]
    },
    "timestamp": "2026-02-03T10:30:00Z"
}
```

### 4.2 创建开户申请
```
POST /api/v1/tickets/account-opening/
```

**请求体：**
```json
{
    "host_id": 1,
    "username": "newuser",
    "full_name": "新用户",
    "email": "newuser@company.com",
    "phone": "13800138000",
    "department": "技术部",
    "position": "开发工程师",
    "reason": "项目开发需要访问数据库服务器",
    "duration_days": 90,
    "access_level": "standard"
}
```

### 4.3 审批工单
```
POST /api/v1/tickets/{id}/approve/
```

**请求体：**
```json
{
    "approval_notes": "经核实，申请合理，同意开通",
    "send_notification": true
}
```

### 4.4 拒绝工单
```
POST /api/v1/tickets/{id}/reject/
```

**请求体：**
```json
{
    "rejection_reason": "申请理由不够充分，请补充详细信息"
}
```

## 5. 系统任务 API

### 5.1 获取任务列表
```
GET /api/v1/tasks/
```

### 5.2 创建系统任务
```
POST /api/v1/tasks/
```

**请求体示例（脚本执行）：**
```json
{
    "name": "获取系统信息",
    "host_id": 1,
    "task_type": "script_execution",
    "command": "Get-ComputerInfo",
    "priority": 5
}
```

**请求体示例（用户管理）：**
```json
{
    "name": "创建本地用户",
    "host_id": 1,
    "task_type": "user_management",
    "parameters": {
        "action": "create",
        "username": "newuser",
        "password": "TempPass123!",
        "fullname": "新用户",
        "description": "临时开发账户"
    },
    "priority": 3
}
```

### 5.3 获取任务详情
```
GET /api/v1/tasks/{id}/
```

### 5.4 取消任务
```
POST /api/v1/tasks/{id}/cancel/
```

## 6. 用户管理 API

### 6.1 获取当前用户信息
```
GET /api/v1/users/me/
```

**响应示例：**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "first_name": "系统",
        "last_name": "管理员",
        "is_superuser": true,
        "is_staff": true,
        "date_joined": "2026-01-01T00:00:00Z",
        "last_login": "2026-02-03T10:15:00Z",
        "permissions": {
            "hosts": ["view", "add", "change", "delete"],
            "tickets": ["view", "add", "change", "delete"],
            "tasks": ["view", "add", "change", "delete"]
        },
        "accessible_hosts": 45
    },
    "timestamp": "2026-02-03T10:30:00Z"
}
```

### 6.2 修改密码
```
POST /api/v1/users/change-password/
```

**请求体：**
```json
{
    "old_password": "current_password",
    "new_password": "new_secure_password",
    "confirm_password": "new_secure_password"
}
```

## 7. 统计数据 API

### 7.1 获取仪表盘统计数据
```
GET /api/v1/dashboard/stats/
```

**响应示例：**
```json
{
    "success": true,
    "data": {
        "hosts": {
            "total": 45,
            "online": 42,
            "offline": 3,
            "by_status": {
                "active": 40,
                "maintenance": 3,
                "disabled": 2
            }
        },
        "tickets": {
            "total": 128,
            "pending": 15,
            "approved": 89,
            "rejected": 12,
            "completed": 12
        },
        "tasks": {
            "total": 256,
            "pending": 8,
            "running": 3,
            "completed": 235,
            "failed": 10
        },
        "recent_activity": [
            {
                "timestamp": "2026-02-03T10:25:00Z",
                "user": "admin",
                "action": "创建主机",
                "resource": "WIN-SERVER-005"
            }
        ]
    },
    "timestamp": "2026-02-03T10:30:00Z"
}
```

### 7.2 获取主机状态统计
```
GET /api/v1/dashboard/host-stats/
```

## 8. 审计日志 API

### 8.1 获取审计日志
```
GET /api/v1/audit/logs/
```

**参数：**
- `page` (integer, optional)
- `page_size` (integer, optional)
- `user_id` (integer, optional)
- `action` (string, optional)
- `resource_type` (string, optional)
- `severity` (string, optional)
- `start_date` (string, optional): ISO 8601 格式
- `end_date` (string, optional): ISO 8601 格式

## 9. 错误码定义

### 9.1 通用错误码
| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| SUCCESS | 200 | 操作成功 |
| CREATED | 201 | 创建成功 |
| BAD_REQUEST | 400 | 请求参数错误 |
| UNAUTHORIZED | 401 | 未认证 |
| FORBIDDEN | 403 | 权限不足 |
| NOT_FOUND | 404 | 资源不存在 |
| METHOD_NOT_ALLOWED | 405 | 方法不允许 |
| CONFLICT | 409 | 资源冲突 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

### 9.2 业务错误码
| 错误码 | 说明 |
|--------|------|
| HOST_CONNECTION_FAILED | 主机连接失败 |
| PERMISSION_DENIED | 权限被拒绝 |
| INVALID_CREDENTIALS | 凭证无效 |
| TASK_EXECUTION_FAILED | 任务执行失败 |
| RESOURCE_LOCKED | 资源被锁定 |

## 10. API 调用示例

### 10.1 Python 客户端示例
```python
import requests
import json

class ZASCAClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.login(username, password)
    
    def login(self, username, password):
        """登录获取会话"""
        response = self.session.post(
            f"{self.base_url}/accounts/login/",
            data={
                'username': username,
                'password': password
            }
        )
        response.raise_for_status()
    
    def get_hosts(self, **params):
        """获取主机列表"""
        response = self.session.get(
            f"{self.base_url}/api/v1/hosts/",
            params=params
        )
        response.raise_for_status()
        return response.json()['data']
    
    def create_ticket(self, host_id, **ticket_data):
        """创建工单"""
        data = {
            'host_id': host_id,
            **ticket_data
        }
        response = self.session.post(
            f"{self.base_url}/api/v1/tickets/account-opening/",
            json=data
        )
        response.raise_for_status()
        return response.json()['data']

# 使用示例
client = ZASCAClient('http://localhost:8000', 'admin', 'password')
hosts = client.get_hosts(status='active')
print(f"活跃主机数量: {len(hosts['results'])}")
```

### 10.2 cURL 示例
```bash
# 登录
curl -X POST http://localhost:8000/accounts/login/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=password" \
  -c cookies.txt

# 获取主机列表
curl -X GET http://localhost:8000/api/v1/hosts/ \
  -b cookies.txt \
  -H "Accept: application/json"

# 创建开户申请
curl -X POST http://localhost:8000/api/v1/tickets/account-opening/ \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{
    "host_id": 1,
    "username": "newuser",
    "full_name": "新用户",
    "email": "newuser@company.com",
    "reason": "项目开发需要",
    "access_level": "standard"
  }'
```

---
*文档版本：V1.0*  
*最后更新：2026年2月3日*