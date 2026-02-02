"""
演示认证插件
展示如何在实际项目中使用插件系统
"""

from plugins.core.base import PluginInterface


class DemoAuthPlugin(PluginInterface):
    """
    演示认证插件
    提供简单的用户认证功能
    """
    
    def __init__(self):
        super().__init__(
            plugin_id="demo_auth_plugin",
            name="Demo Authentication Plugin",
            version="1.0.0",
            description="演示如何在Django项目中集成认证插件"
        )
        self.users = {}
        self.active_sessions = {}
        
    def initialize(self) -> bool:
        print(f"初始化 {self.name}")
        # 初始化用户数据（在实际项目中，这可能来自数据库）
        self.users = {
            "admin": "secret123",
            "user": "password123",
            "guest": "guest123"
        }
        return True
        
    def shutdown(self) -> bool:
        print(f"关闭 {self.name}")
        # 清理会话数据
        self.active_sessions.clear()
        return True
        
    def authenticate(self, username: str, password: str) -> dict:
        """
        认证用户
        :param username: 用户名
        :param password: 密码
        :return: 包含认证结果的字典
        """
        if username in self.users and self.users[username] == password:
            # 创建会话
            session_id = f"session_{username}_{hash(password)}"
            self.active_sessions[session_id] = {
                'username': username,
                'authenticated_at': __import__('datetime').datetime.now().isoformat()
            }
            return {
                'success': True,
                'session_id': session_id,
                'user': {'username': username}
            }
        else:
            return {
                'success': False,
                'error': 'Invalid credentials'
            }
            
    def validate_session(self, session_id: str) -> bool:
        """
        验证会话
        :param session_id: 会话ID
        :return: 会话是否有效
        """
        return session_id in self.active_sessions
        
    def logout(self, session_id: str) -> bool:
        """
        注销用户
        :param session_id: 会话ID
        :return: 注销是否成功
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False


# 另一个演示插件：日志记录插件
class DemoLoggingPlugin(PluginInterface):
    """
    演示日志记录插件
    提供灵活的日志记录功能
    """
    
    def __init__(self):
        super().__init__(
            plugin_id="demo_logging_plugin",
            name="Demo Logging Plugin",
            version="1.0.0",
            description="演示如何在项目中集成日志记录插件"
        )
        self.logs = []
        self.log_level = 'INFO'
        self.max_log_size = 1000  # 最大日志条目数
        
    def initialize(self) -> bool:
        print(f"初始化 {self.name}")
        return True
        
    def shutdown(self) -> bool:
        print(f"关闭 {self.name}")
        return True
        
    def log(self, level: str, message: str, **context):
        """
        记录日志
        :param level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        :param message: 日志消息
        :param context: 上下文信息
        """
        import datetime
        
        if self._should_log(level):
            log_entry = {
                'timestamp': datetime.datetime.now().isoformat(),
                'level': level.upper(),
                'message': message,
                'context': context
            }
            
            self.logs.append(log_entry)
            
            # 控制日志大小
            if len(self.logs) > self.max_log_size:
                self.logs.pop(0)
                
            # 输出到控制台
            print(f"[{log_entry['level']}] {log_entry['message']}")
            
    def _should_log(self, level: str) -> bool:
        """根据日志级别判断是否应该记录"""
        levels = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3}
        current_level = levels.get(self.log_level.upper(), 1)
        message_level = levels.get(level.upper(), 1)
        return message_level >= current_level
        
    def get_logs(self, level_filter: str = None, limit: int = None):
        """
        获取日志条目
        :param level_filter: 过滤日志级别
        :param limit: 限制返回条目数
        :return: 日志条目列表
        """
        filtered_logs = self.logs
        
        if level_filter:
            filtered_logs = [log for log in filtered_logs 
                           if log['level'] == level_filter.upper()]
                           
        if limit:
            filtered_logs = filtered_logs[-limit:]
            
        return filtered_logs
        
    def set_log_level(self, level: str):
        """设置日志级别"""
        self.log_level = level.upper()