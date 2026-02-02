"""
插件系统示例插件
展示如何创建和使用插件
"""

from plugins.core.base import PluginInterface


class ExamplePlugin(PluginInterface):
    """
    示例插件
    演示插件的基本功能和结构
    """
    
    def __init__(self):
        super().__init__(
            plugin_id="example_plugin",
            name="Example Plugin",
            version="1.0.0",
            description="这是一个示例插件，用于演示插件系统的功能"
        )
        self.initialized = False
        
    def initialize(self) -> bool:
        """
        初始化插件
        :return: 初始化是否成功
        """
        print(f"Initializing {self.name} v{self.version}")
        # 在这里添加插件初始化逻辑
        self.initialized = True
        return True
        
    def shutdown(self) -> bool:
        """
        关闭插件
        :return: 关闭是否成功
        """
        print(f"Shutting down {self.name}")
        # 在这里添加插件清理逻辑
        self.initialized = False
        return True


# 另一个示例插件 - 日志插件
class LoggingPlugin(PluginInterface):
    """
    日志插件
    演示插件可以提供日志记录功能
    """
    
    def __init__(self):
        super().__init__(
            plugin_id="logging_plugin",
            name="Logging Plugin",
            version="1.0.0",
            description="提供日志记录功能的插件"
        )
        self.log_file = None
        
    def initialize(self) -> bool:
        print(f"Initializing {self.name}")
        # 初始化日志文件
        self.log_file = open("plugin_logs.txt", "a")
        return True
        
    def shutdown(self) -> bool:
        print(f"Shutting down {self.name}")
        if self.log_file:
            self.log_file.close()
        return True
        
    def log_message(self, message: str):
        """记录消息到日志文件"""
        if self.log_file:
            self.log_file.write(f"[{self.name}] {message}\n")
            self.log_file.flush()


# 另一个示例插件 - 认证插件
class AuthPlugin(PluginInterface):
    """
    认证插件
    演示插件可以提供认证功能
    """
    
    def __init__(self):
        super().__init__(
            plugin_id="auth_plugin",
            name="Authentication Plugin",
            version="1.0.0",
            description="提供用户认证功能的插件"
        )
        self.users = {}
        
    def initialize(self) -> bool:
        print(f"Initializing {self.name}")
        # 初始化认证系统
        self.users = {
            "admin": "admin123",
            "user": "user123"
        }
        return True
        
    def shutdown(self) -> bool:
        print(f"Shutting down {self.name}")
        # 清理认证数据
        self.users.clear()
        return True
        
    def authenticate(self, username: str, password: str) -> bool:
        """验证用户凭据"""
        return self.users.get(username) == password