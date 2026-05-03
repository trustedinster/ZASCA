import abc
import logging
from typing import Any, Dict, List, Optional, Type

from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)


class PluginInterface(abc.ABC):
    def __init__(self, plugin_id: str, name: str, version: str, description: str = ""):
        self.plugin_id = plugin_id
        self.name = name
        self.version = version
        self.description = description
        self.enabled = True

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            'id': self.plugin_id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'enabled': self.enabled
        }

    @abc.abstractmethod
    def initialize(self) -> bool:
        pass

    @abc.abstractmethod
    def shutdown(self) -> bool:
        pass


class ServiceProvider(abc.ABC):
    """
    服务提供者接口
    插件可实现此接口以向系统注册可发现的服务
    """

    @abc.abstractmethod
    def get_service_name(self) -> str:
        pass

    @abc.abstractmethod
    def get_service_interface(self) -> Type:
        pass

    def get_service(self) -> Any:
        return self


class ServiceRegistry:
    """
    服务注册表
    管理插件提供的服务实例，支持按服务名称和接口类型查找
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._interfaces: Dict[Type, List[str]] = {}

    def register(self, provider: ServiceProvider) -> None:
        name = provider.get_service_name()
        interface = provider.get_service_interface()
        service = provider.get_service()

        self._services[name] = service

        if interface not in self._interfaces:
            self._interfaces[interface] = []
        if name not in self._interfaces[interface]:
            self._interfaces[interface].append(name)

        logger.info(f"Service registered: {name} (interface: {interface.__name__})")

    def unregister(self, service_name: str) -> None:
        if service_name in self._services:
            del self._services[service_name]
            for interface, names in self._interfaces.items():
                if service_name in names:
                    names.remove(service_name)
            logger.info(f"Service unregistered: {service_name}")

    def get(self, service_name: str) -> Optional[Any]:
        return self._services.get(service_name)

    def get_by_interface(self, interface: Type) -> List[Any]:
        names = self._interfaces.get(interface, [])
        return [self._services[n] for n in names if n in self._services]

    def list_services(self) -> Dict[str, Any]:
        return dict(self._services)


class HookInterface(abc.ABC):
    @abc.abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        pass


class EventHook(HookInterface):
    def __init__(self, name: str):
        self.name = name
        self.handlers: List[callable] = []

    def register(self, handler: callable):
        if handler not in self.handlers:
            self.handlers.append(handler)

    def unregister(self, handler: callable):
        if handler in self.handlers:
            self.handlers.remove(handler)

    def execute(self, *args, **kwargs) -> List[Any]:
        results = []
        for handler in self.handlers:
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Error executing handler "
                    f"{handler.__name__}: {str(e)}"
                )
                results.append(None)
        return results


class UIExtension:
    """
    UI 扩展点描述对象

    插件通过此对象声明要在某个页面位置注入的
    HTML 片段、模板路径或表单字段。
    """

    FORM_FIELD = 'form_field'
    SECTION = 'section'
    NAV_ITEM = 'nav_item'
    TEMPLATE = 'template'
    HTML = 'html'

    def __init__(
        self,
        extension_type: str,
        slot: str,
        label: str = '',
        html: str = '',
        template_name: str = '',
        field_name: str = '',
        field_config: Optional[Dict[str, Any]] = None,
        order: int = 0,
        context_callback=None,
    ):
        self.extension_type = extension_type
        self.slot = slot
        self.label = label
        self.html = html
        self.template_name = template_name
        self.field_name = field_name
        self.field_config = field_config or {}
        self.order = order
        self.context_callback = context_callback

    def render(self, request=None) -> str:
        if self.html:
            return mark_safe(self.html)

        if self.template_name:
            render_ctx = {}
            if self.context_callback:
                extra = self.context_callback()
                if extra:
                    render_ctx.update(extra)
            from django.template.loader import (
                render_to_string,
            )
            return mark_safe(
                render_to_string(
                    self.template_name, render_ctx,
                    request=request,
                )
            )

        return ''


class UIExtensionProvider(abc.ABC):
    """
    UI 扩展提供者接口

    插件实现此接口以向前端页面注入扩展内容。
    扩展点（slot）由核心系统在各页面模板中预定义，
    插件只需声明自己要注入到哪个 slot 即可。
    """

    @abc.abstractmethod
    def get_ui_extensions(self) -> List[UIExtension]:
        pass


class URLProvider(abc.ABC):
    """
    URL 提供者接口

    插件实现此接口以向系统注册 URL 路由。
    系统在启动时收集所有插件的 URL 模式，
    并动态 include 到对应命名空间下。
    """

    ADMIN = 'admin'
    PROVIDER = 'provider'
    PUBLIC = 'public'

    @abc.abstractmethod
    def get_url_patterns(self) -> List[dict]:
        """
        返回 URL 模式列表。

        每个元素为 dict:
        {
            'prefix': 'qq/',           # URL 前缀
            'module': 'plugins.qq_verification.urls_admin',
            'namespace': 'admin_plugins',
            'section': URLProvider.ADMIN,
        }
        """
        pass
