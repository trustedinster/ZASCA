"""
插件系统基础类定义
"""

import abc
from typing import Any, Dict, List, Optional


class PluginInterface(abc.ABC):
    """
    插件接口定义
    所有插件必须继承此接口
    """
    
    def __init__(self, plugin_id: str, name: str, version: str, description: str = ""):
        self.plugin_id = plugin_id
        self.name = name
        self.version = version
        self.description = description
        self.enabled = True
        
    @property
    def metadata(self) -> Dict[str, Any]:
        """获取插件元数据"""
        return {
            'id': self.plugin_id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'enabled': self.enabled
        }
    
    @abc.abstractmethod
    def initialize(self) -> bool:
        """
        初始化插件
        :return: 初始化是否成功
        """
        pass
    
    @abc.abstractmethod
    def shutdown(self) -> bool:
        """
        关闭插件
        :return: 关闭是否成功
        """
        pass


class HookInterface(abc.ABC):
    """
    钩子接口定义
    插件可以通过钩子在特定时机执行代码
    """
    
    @abc.abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        执行钩子函数
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return: 执行结果
        """
        pass


class EventHook(HookInterface):
    """
    事件钩子实现
    """
    
    def __init__(self, name: str):
        self.name = name
        self.handlers: List[callable] = []
        
    def register(self, handler: callable):
        """注册处理器"""
        if handler not in self.handlers:
            self.handlers.append(handler)
            
    def unregister(self, handler: callable):
        """注销处理器"""
        if handler in self.handlers:
            self.handlers.remove(handler)
            
    def execute(self, *args, **kwargs) -> List[Any]:
        """
        执行所有注册的处理器
        :return: 所有处理器的返回值列表
        """
        results = []
        for handler in self.handlers:
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Error executing handler {handler.__name__}: {str(e)}")
                results.append(None)
        return results