# ZASCA 数据库 Schema 设计文档

## 1. 数据库概览

ZASCA 使用 PostgreSQL 作为主数据库，采用关系型数据模型设计，支持完整的 RBAC 权限体系和审计追踪功能。

### 1.1 数据库版本要求
- PostgreSQL 12+ （推荐 14+）
- 支持 JSONB 字段类型
- 支持数组类型
- 支持全文搜索

### 1.2 字符集与排序
- 字符集：UTF-8
- 排序规则：en_US.UTF-8 或 zh_CN.UTF-8

## 2. 核心数据表结构

### 2.1 用户认证相关表

#### accounts_customuser 表（用户表）
```sql
CREATE TABLE accounts_customuser (
    id SERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) UNIQUE NOT NULL,
    first_name VARCHAR(150) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    email VARCHAR(254) NOT NULL,
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined TIMESTAMP WITH TIME ZONE NOT NULL,
    phone VARCHAR(20),
    department VARCHAR(100),
    position VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_accounts_customuser_username ON accounts_customuser(username);
CREATE INDEX idx_accounts_customuser_email ON accounts_customuser(email);
CREATE INDEX idx_accounts_customuser_is_active ON accounts_customuser(is_active);
```

#### accounts_userprofile 表（用户档案扩展）
```sql
CREATE TABLE accounts_userprofile (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES accounts_customuser(id) ON DELETE CASCADE,
    avatar TEXT,
    bio TEXT,
    preferred_language VARCHAR(10) DEFAULT 'zh-hans',
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
    notification_settings JSONB DEFAULT '{}',
    last_password_change TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 2.2 主机管理相关表

#### hosts_host 表（主机信息）
```sql
CREATE TABLE hosts_host (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    ip_address INET NOT NULL,
    description TEXT,
    os_version VARCHAR(100),
    cpu_info VARCHAR(255),
    memory_gb INTEGER,
    disk_space_gb INTEGER,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'maintenance', 'disabled')),
    is_online BOOLEAN DEFAULT FALSE,
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    winrm_port INTEGER DEFAULT 5985,
    winrm_https BOOLEAN DEFAULT FALSE,
    winrm_username VARCHAR(100),
    winrm_password_encrypted TEXT,
    certificate_fingerprint VARCHAR(255),
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_by_id INTEGER REFERENCES accounts_customuser(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_hosts_host_hostname ON hosts_host(hostname);
CREATE INDEX idx_hosts_host_ip_address ON hosts_host(ip_address);
CREATE INDEX idx_hosts_host_status ON hosts_host(status);
CREATE INDEX idx_hosts_host_is_online ON hosts_host(is_online);
CREATE INDEX idx_hosts_host_tags ON hosts_host USING GIN(tags);
```

#### hosts_hostgroup 表（主机组）
```sql
CREATE TABLE hosts_hostgroup (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES hosts_hostgroup(id),
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_by_id INTEGER REFERENCES accounts_customuser(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 主机与主机组关联表
CREATE TABLE hosts_host_groups (
    id SERIAL PRIMARY KEY,
    host_id INTEGER REFERENCES hosts_host(id) ON DELETE CASCADE,
    hostgroup_id INTEGER REFERENCES hosts_hostgroup(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    assigned_by_id INTEGER REFERENCES accounts_customuser(id),
    UNIQUE(host_id, hostgroup_id)
);
```

### 2.3 权限管理相关表

#### hosts_hostpermission 表（主机权限）
```sql
CREATE TABLE hosts_hostpermission (
    id SERIAL PRIMARY KEY,
    host_id INTEGER REFERENCES hosts_host(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES accounts_customuser(id) ON DELETE CASCADE,
    permission_level VARCHAR(20) NOT NULL CHECK (permission_level IN ('read', 'operate', 'admin')),
    granted_by_id INTEGER REFERENCES accounts_customuser(id),
    granted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    UNIQUE(host_id, user_id)
);

-- 索引
CREATE INDEX idx_hosts_hostpermission_host_id ON hosts_hostpermission(host_id);
CREATE INDEX idx_hosts_hostpermission_user_id ON hosts_hostpermission(user_id);
CREATE INDEX idx_hosts_hostpermission_is_active ON hosts_hostpermission(is_active);
```

### 2.4 运维工单相关表

#### operations_accountopeningrequest 表（开户申请）
```sql
CREATE TABLE operations_accountopeningrequest (
    id SERIAL PRIMARY KEY,
    request_number VARCHAR(50) UNIQUE NOT NULL,
    applicant_id INTEGER REFERENCES accounts_customuser(id),
    host_id INTEGER REFERENCES hosts_host(id),
    username VARCHAR(100) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(254),
    phone VARCHAR(20),
    department VARCHAR(100),
    position VARCHAR(100),
    reason TEXT NOT NULL,
    duration_days INTEGER,
    access_level VARCHAR(20) DEFAULT 'standard' CHECK (access_level IN ('standard', 'elevated', 'administrator')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'completed', 'cancelled')),
    approver_id INTEGER REFERENCES accounts_customuser(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    approval_notes TEXT,
    completed_at TIMESTAMP WITH TIME ZONE,
    completion_notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_operations_aor_request_number ON operations_accountopeningrequest(request_number);
CREATE INDEX idx_operations_aor_applicant_id ON operations_accountopeningrequest(applicant_id);
CREATE INDEX idx_operations_aor_host_id ON operations_accountopeningrequest(host_id);
CREATE INDEX idx_operations_aor_status ON operations_accountopeningrequest(status);
CREATE INDEX idx_operations_aor_created_at ON operations_accountopeningrequest(created_at);
```

#### operations_systemtask 表（系统任务）
```sql
CREATE TABLE operations_systemtask (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    host_id INTEGER REFERENCES hosts_host(id),
    task_type VARCHAR(50) NOT NULL CHECK (task_type IN ('script_execution', 'file_transfer', 'service_control', 'user_management', 'system_info')),
    command TEXT,
    parameters JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    priority INTEGER DEFAULT 1 CHECK (priority BETWEEN 1 AND 10),
    created_by_id INTEGER REFERENCES accounts_customuser(id),
    assigned_to_id INTEGER REFERENCES accounts_customuser(id),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    result TEXT,
    error_message TEXT,
    execution_time_ms INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_operations_systemtask_task_id ON operations_systemtask(task_id);
CREATE INDEX idx_operations_systemtask_host_id ON operations_systemtask(host_id);
CREATE INDEX idx_operations_systemtask_status ON operations_systemtask(status);
CREATE INDEX idx_operations_systemtask_created_by_id ON operations_systemtask(created_by_id);
```

### 2.5 审计日志相关表

#### audit_auditlog 表（审计日志）
```sql
CREATE TABLE audit_auditlog (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    user_id INTEGER REFERENCES accounts_customuser(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id INTEGER,
    resource_name VARCHAR(255),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    severity VARCHAR(20) DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    category VARCHAR(50) DEFAULT 'general'
);

-- 索引
CREATE INDEX idx_audit_auditlog_timestamp ON audit_auditlog(timestamp);
CREATE INDEX idx_audit_auditlog_user_id ON audit_auditlog(user_id);
CREATE INDEX idx_audit_auditlog_action ON audit_auditlog(action);
CREATE INDEX idx_audit_auditlog_resource_type ON audit_auditlog(resource_type);
CREATE INDEX idx_audit_auditlog_severity ON audit_auditlog(severity);
```

### 2.6 证书管理相关表

#### certificates_certificateauthority 表（证书颁发机构）
```sql
CREATE TABLE certificates_certificateauthority (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    certificate_data TEXT NOT NULL,
    public_key TEXT NOT NULL,
    fingerprint VARCHAR(255) UNIQUE NOT NULL,
    issuer VARCHAR(255),
    subject VARCHAR(255),
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revocation_reason TEXT,
    metadata JSONB DEFAULT '{}',
    created_by_id INTEGER REFERENCES accounts_customuser(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_certificates_ca_fingerprint ON certificates_certificateauthority(fingerprint);
CREATE INDEX idx_certificates_ca_expires_at ON certificates_certificateauthority(expires_at);
CREATE INDEX idx_certificates_ca_is_active ON certificates_certificateauthority(is_active);
```

### 2.7 系统配置相关表

#### dashboard_systemconfig 表（系统配置）
```sql
CREATE TABLE dashboard_systemconfig (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    value_type VARCHAR(20) DEFAULT 'string' CHECK (value_type IN ('string', 'integer', 'float', 'boolean', 'json')),
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',
    is_sensitive BOOLEAN DEFAULT FALSE,
    editable BOOLEAN DEFAULT TRUE,
    last_modified_by_id INTEGER REFERENCES accounts_customuser(id),
    last_modified_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_dashboard_systemconfig_key ON dashboard_systemconfig(key);
CREATE INDEX idx_dashboard_systemconfig_category ON dashboard_systemconfig(category);
```

## 3. 视图设计

### 3.1 常用业务视图

#### 用户主机权限视图
```sql
CREATE VIEW v_user_host_permissions AS
SELECT 
    u.id as user_id,
    u.username,
    h.id as host_id,
    h.hostname,
    hp.permission_level,
    hp.is_active,
    hp.expires_at
FROM accounts_customuser u
JOIN hosts_hostpermission hp ON u.id = hp.user_id
JOIN hosts_host h ON hp.host_id = h.id
WHERE hp.is_active = TRUE 
AND (hp.expires_at IS NULL OR hp.expires_at > NOW());
```

#### 工单统计视图
```sql
CREATE VIEW v_ticket_statistics AS
SELECT 
    DATE(created_at) as date,
    status,
    COUNT(*) as count
FROM operations_accountopeningrequest
GROUP BY DATE(created_at), status
ORDER BY date DESC;
```

## 4. 存储过程和函数

### 4.1 权限检查函数
```sql
CREATE OR REPLACE FUNCTION check_host_permission(
    p_user_id INTEGER,
    p_host_id INTEGER,
    p_required_level VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    user_level VARCHAR;
    level_order INTEGER[];
BEGIN
    level_order := ARRAY['read', 'operate', 'admin'];
    
    SELECT hp.permission_level INTO user_level
    FROM hosts_hostpermission hp
    WHERE hp.user_id = p_user_id 
    AND hp.host_id = p_host_id 
    AND hp.is_active = TRUE
    AND (hp.expires_at IS NULL OR hp.expires_at > NOW());
    
    IF user_level IS NULL THEN
        RETURN FALSE;
    END IF;
    
    RETURN array_position(level_order, user_level) >= array_position(level_order, p_required_level);
END;
$$ LANGUAGE plpgsql;
```

## 5. 触发器

### 5.1 自动更新时间戳
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有主要表创建触发器
CREATE TRIGGER update_accounts_customuser_updated_at 
    BEFORE UPDATE ON accounts_customuser 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_hosts_host_updated_at 
    BEFORE UPDATE ON hosts_host 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## 6. 索引优化建议

### 6.1 性能关键索引
```sql
-- 复合索引优化常用查询
CREATE INDEX idx_operations_product_is_available ON operations_product(is_available);
CREATE INDEX idx_operations_aor_status_created ON operations_accountopeningrequest(status, created_at);
CREATE INDEX idx_audit_log_timestamp_severity ON audit_auditlog(timestamp, severity);

-- 全文搜索索引
CREATE INDEX idx_operations_product_search ON operations_product 
USING gin(to_tsvector('chinese_zh', name || ' ' || description));

-- JSONB 字段索引
CREATE INDEX idx_operations_product_metadata ON operations_product USING gin(metadata);
CREATE INDEX idx_operations_aor_metadata ON operations_accountopeningrequest USING gin(metadata);
```

## 7. 数据备份策略

### 7.1 备份频率
- **完整备份**：每日凌晨 2:00
- **增量备份**：每 4 小时
- **事务日志**：实时归档

### 7.2 保留策略
- 完整备份保留 30 天
- 增量备份保留 7 天
- 事务日志保留 3 天

### 7.3 恢复点目标 (RPO)
- 最大数据丢失：4 小时
- 恢复时间目标 (RTO)：2 小时

## 8. 数据库监控指标

### 8.1 关键性能指标
- 连接数使用率
- 查询响应时间
- 锁等待情况
- 磁盘 I/O 性能
- 缓冲区命中率

### 8.2 容量规划
- 当前数据量：~10GB
- 年增长率预估：30%
- 三年后预计容量：~22GB

---
*文档版本：V1.0*  
*最后更新：2026年2月3日*