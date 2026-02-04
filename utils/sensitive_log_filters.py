"""
日志脱敏过滤器
用于清理日志中的敏感信息
"""
import re
import logging


class SensitiveDataFilter(logging.Filter):
    """过滤日志中的敏感数据"""

    # 敏感字段正则表达式
    SENSITIVE_PATTERNS = [
        (r'(password)\s*=\s*[\'"]?([^\s\'"]+)', r'\1=***'),
        (r'(pwd)\s*=\s*[\'"]?([^\s\'"]+)', r'\1=***'),
        (r'(secret_key)\s*=\s*[\'"]?([^\s\'"]+)', r'\1=***'),
        (r'(token)\s*=\s*[\'"]?([^\s\'"]+)', r'\1=***'),
        (r'(api_key)\s*=\s*[\'"]?([^\s\'"]+)', r'\1=***'),
        (r'(access_token)\s*=\s*[\'"]?([^\s\'"]+)', r'\1=***'),
        (r'(session_key)\s*=\s*[\'"]?([^\s\'"]+)', r'\1=***'),
    ]

    # IP 地址脱敏模式（保留前三段）
    IP_PATTERN = r'(\b(?:[0-9]{1,3}\.){3})[0-9]{1,3}\b'
    IP_REPLACEMENT = r'\1xxx'

    def filter(self, record):
        """过滤日志记录中的敏感数据"""
        if hasattr(record, 'msg'):
            record.msg = self._sanitize_message(str(record.msg))

        if hasattr(record, 'args') and record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self._sanitize_message(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)

        return True

    def _sanitize_message(self, message: str) -> str:
        """清理消息中的敏感信息"""
        # 清理密码等敏感字段
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)

        # 清理 IP 地址
        message = re.sub(self.IP_PATTERN, self.IP_REPLACEMENT, message)

        return message


class AuditFilter(logging.Filter):
    """审计日志过滤器，确保重要操作都被记录"""

    AUDIT_ACTIONS = [
        'create_user', 'delete_user', 'reset_password', 'approve_request',
        'reject_request', 'modify_host', 'delete_host', 'login', 'logout',
        'view_password', 'process_opening_request'
    ]

    def filter(self, record):
        """确保审计相关的日志被记录"""
        # 检查是否是审计操作
        if hasattr(record, 'action') and record.action in self.AUDIT_ACTIONS:
            record.levelno = logging.INFO
            record.levelname = logging.getLevelName(logging.INFO)

        return True