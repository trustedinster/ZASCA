import socket
import struct
import logging
import time
import threading
import uuid
import os
from typing import Optional, Dict, Any, List

from django.conf import settings

logger = logging.getLogger('zasca')


class GatewayError(Exception):
    pass


def is_gateway_enabled() -> bool:
    return getattr(settings, 'GATEWAY_ENABLED', False)


def get_gateway_socket_path() -> str:
    return getattr(
        settings, 'GATEWAY_CONTROL_SOCKET',
        '/run/zasca/control.sock'
    )


class GatewayClient:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, socket_path: Optional[str] = None):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.enabled = is_gateway_enabled()
        self.socket_path = socket_path or get_gateway_socket_path()
        self._conn = None
        self._conn_lock = threading.Lock()
        self._reconnect_delay = 1
        self._max_reconnect_delay = 60
        self._available = None

    def _is_available(self) -> bool:
        if not self.enabled:
            return False
        if self._available is False:
            return False
        try:
            if os.path.exists(self.socket_path):
                return True
            self._available = False
            return False
        except Exception:
            self._available = False
            return False

    def _connect(self) -> socket.socket:
        try:
            import msgpack
        except ImportError:
            self._available = False
            raise GatewayError('msgpack not installed')
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect(self.socket_path)
        self._reconnect_delay = 1
        self._available = True
        return sock

    def _get_conn(self) -> socket.socket:
        with self._conn_lock:
            if self._conn is not None:
                try:
                    self._conn.getpeername()
                    return self._conn
                except Exception:
                    self._conn = None

            try:
                self._conn = self._connect()
                return self._conn
            except Exception as e:
                logger.debug(f'Gateway socket connect failed: {e}')
                self._available = False
                raise GatewayError(f'Cannot connect to Gateway: {e}')

    def _reconnect(self):
        with self._conn_lock:
            if self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    def _send_command(self, cmd_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._is_available():
            raise GatewayError('Gateway not available')

        try:
            import msgpack
        except ImportError:
            raise GatewayError('msgpack not installed')

        req_id = str(uuid.uuid4())
        command = {
            'type': cmd_type,
            'req_id': req_id,
            'payload': payload,
        }

        data = msgpack.packb(command, use_bin_type=True)
        header = struct.pack('>I', len(data))

        try:
            conn = self._get_conn()
            conn.sendall(header + data)

            resp_header = self._recv_exact(conn, 4)
            resp_len = struct.unpack('>I', resp_header)[0]
            resp_data = self._recv_exact(conn, resp_len)
            response = msgpack.unpackb(resp_data, raw=False)

            if response.get('req_id') != req_id:
                raise GatewayError('Response req_id mismatch')

            return response

        except (GatewayError, socket.error, OSError) as e:
            logger.debug(f'Gateway command {cmd_type} failed: {e}')
            self._reconnect()
            raise GatewayError(f'Command {cmd_type} failed: {e}')

    def _recv_exact(self, conn: socket.socket, n: int) -> bytes:
        buf = b''
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                raise GatewayError('Connection closed')
            buf += chunk
        return buf

    def domain_bind(self, domain: str, token: str) -> bool:
        if not self._is_available():
            logger.debug('Gateway not available, skipping domain_bind')
            return False
        try:
            resp = self._send_command('domain_bind', {
                'domain': domain,
                'token': token,
            })
            return resp.get('success', False)
        except GatewayError:
            return False

    def domain_unbind(self, domain: str) -> bool:
        if not self._is_available():
            logger.debug('Gateway not available, skipping domain_unbind')
            return False
        try:
            resp = self._send_command('domain_unbind', {
                'domain': domain,
            })
            return resp.get('success', False)
        except GatewayError:
            return False

    def tunnel_kick(self, token: str) -> bool:
        if not self._is_available():
            logger.debug('Gateway not available, skipping tunnel_kick')
            return False
        try:
            resp = self._send_command('tunnel_kick', {
                'token': token,
            })
            return resp.get('success', False)
        except GatewayError:
            return False

    def tunnel_stats(self, token: Optional[str] = None) -> Optional[Any]:
        if not self._is_available():
            return None
        try:
            payload = {}
            if token:
                payload['token'] = token
            resp = self._send_command('tunnel_stats', payload)
            if resp.get('success'):
                return resp.get('data')
            return None
        except GatewayError:
            return None

    def remote_exec(self, token: str, script: bytes,
                    encrypted_key: Optional[bytes] = None,
                    signature: Optional[bytes] = None,
                    pub_key_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not self._is_available():
            logger.debug('Gateway not available, cannot remote_exec')
            return None
        try:
            payload = {
                'token': token,
                'script': script,
            }
            if encrypted_key:
                payload['encrypted_key'] = encrypted_key
            if signature:
                payload['signature'] = signature
            if pub_key_id:
                payload['pub_key_id'] = pub_key_id

            resp = self._send_command('remote_exec', payload)
            return resp
        except GatewayError:
            return None


class GatewayEventListener:
    def __init__(self, socket_path: Optional[str] = None):
        self.enabled = is_gateway_enabled()
        self.socket_path = socket_path or get_gateway_socket_path()
        self._running = False
        self._handlers = {}

    def register_handler(self, event_type: str, handler):
        self._handlers[event_type] = handler

    def start(self):
        if not self.enabled:
            logger.info(
                'Gateway not enabled, event listener not starting. '
                'Set GATEWAY_ENABLED=True to enable.'
            )
            return

        try:
            import msgpack
        except ImportError:
            logger.warning(
                'msgpack not installed, Gateway event listener disabled. '
                'Install with: pip install msgpack'
            )
            return

        self._running = True
        while self._running:
            if not os.path.exists(self.socket_path):
                logger.debug(
                    f'Gateway socket {self.socket_path} not found, '
                    f'retrying in 30s...'
                )
                time.sleep(30)
                continue

            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(30)
                sock.connect(self.socket_path)
                logger.info('Gateway event listener connected')

                while self._running:
                    try:
                        header = self._recv_exact(sock, 4)
                        length = struct.unpack('>I', header)[0]
                        data = self._recv_exact(sock, length)
                        event = msgpack.unpackb(data, raw=False)

                        event_type = event.get('type', '')
                        payload = event.get('payload', {})

                        handler = self._handlers.get(event_type)
                        if handler:
                            handler(event_type, payload)
                        else:
                            logger.debug(f'Unhandled event type: {event_type}')

                    except socket.timeout:
                        continue
                    except Exception as e:
                        logger.error(f'Event listener read error: {e}')
                        break

            except Exception as e:
                logger.debug(f'Event listener connect error: {e}')

            if self._running:
                time.sleep(5)

    def stop(self):
        self._running = False

    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        buf = b''
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError('Connection closed')
            buf += chunk
        return buf
