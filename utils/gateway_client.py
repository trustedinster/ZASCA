import logging
from typing import Any, Dict, Optional

logger = logging.getLogger('zasca')


class GatewayError(Exception):
    pass


def _get_gateway_service():
    from plugins.core.plugin_manager import get_plugin_manager
    from plugins.gateway.interfaces import GatewayServiceInterface

    pm = get_plugin_manager()
    service = pm.get_service('gateway')
    if service is not None and isinstance(
        service, GatewayServiceInterface
    ):
        return service
    return None


def is_gateway_enabled() -> bool:
    service = _get_gateway_service()
    if service is not None:
        return service.is_enabled()
    from django.conf import settings
    return getattr(settings, 'GATEWAY_ENABLED', False)


def get_gateway_socket_path() -> str:
    from django.conf import settings
    return getattr(
        settings, 'GATEWAY_CONTROL_SOCKET',
        '/run/zasca/control.sock'
    )


class GatewayClient:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, socket_path: Optional[str] = None):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

    def _get_service(self):
        return _get_gateway_service()

    @property
    def enabled(self) -> bool:
        service = self._get_service()
        if service:
            return service.is_enabled()
        return False

    def _is_available(self) -> bool:
        service = self._get_service()
        if service:
            return service.is_available()
        return False

    def domain_bind(self, domain: str, token: str) -> bool:
        service = self._get_service()
        if service:
            return service.domain_bind(domain, token)
        return False

    def domain_unbind(self, domain: str) -> bool:
        service = self._get_service()
        if service:
            return service.domain_unbind(domain)
        return False

    def tunnel_kick(self, token: str) -> bool:
        service = self._get_service()
        if service:
            return service.tunnel_kick(token)
        return False

    def tunnel_stats(
        self, token: Optional[str] = None
    ) -> Optional[Any]:
        service = self._get_service()
        if service:
            return service.tunnel_stats(token)
        return None

    def remote_exec(
        self,
        token: str,
        script: bytes,
        encrypted_key: Optional[bytes] = None,
        signature: Optional[bytes] = None,
        pub_key_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        service = self._get_service()
        if service:
            return service.remote_exec(
                token, script, encrypted_key,
                signature, pub_key_id
            )
        return None


class GatewayEventListener:
    def __init__(self, socket_path: Optional[str] = None):
        self._socket_path = socket_path
        self._running = False
        self._handlers = {}

    def register_handler(self, event_type: str, handler):
        self._handlers[event_type] = handler

    def start(self):
        from plugins.core.plugin_manager import get_plugin_manager
        pm = get_plugin_manager()
        plugin = pm.get_plugin('gateway')
        if plugin and hasattr(plugin, 'get_event_listener'):
            listener = plugin.get_event_listener(self._socket_path)
            for event_type, handler in self._handlers.items():
                listener.register_handler(event_type, handler)
            listener.start()
        else:
            logger.warning(
                'Gateway plugin not available, '
                'event listener not starting'
            )

    def stop(self):
        self._running = False
