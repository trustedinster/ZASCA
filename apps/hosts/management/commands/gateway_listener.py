import logging
import signal
import sys

from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger('zasca')


class Command(BaseCommand):
    help = 'Listen for Gateway events via Unix Domain Socket'

    def add_arguments(self, parser):
        parser.add_argument(
            '--socket',
            type=str,
            default=None,
            help='Unix Domain Socket path (default: from settings)',
        )

    def handle(self, *args, **options):
        from utils.gateway_client import is_gateway_enabled

        if not is_gateway_enabled():
            self.stdout.write(
                self.style.WARNING(
                    'Gateway is not enabled. '
                    'Set GATEWAY_ENABLED=True in environment to enable. '
                    'Exiting.'
                )
            )
            return

        from utils.gateway_client import GatewayEventListener

        socket_path = options.get('socket') or getattr(
            settings, 'GATEWAY_CONTROL_SOCKET',
            '/run/zasca/control.sock'
        )

        self.stdout.write(
            f'Starting Gateway event listener on {socket_path}'
        )

        listener = GatewayEventListener(socket_path)

        listener.register_handler(
            'tunnel_online', self._handle_tunnel_online
        )
        listener.register_handler(
            'tunnel_offline', self._handle_tunnel_offline
        )
        listener.register_handler(
            'rdp_connect', self._handle_rdp_connect
        )
        listener.register_handler(
            'rdp_disconnect', self._handle_rdp_disconnect
        )
        listener.register_handler(
            'remote_exec_result', self._handle_remote_exec_result
        )

        def signal_handler(signum, frame):
            self.stdout.write('Shutting down listener...')
            listener.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            listener.start()
        except KeyboardInterrupt:
            listener.stop()

    def _handle_tunnel_online(self, event_type, payload):
        from django.utils import timezone
        from apps.hosts.models import Host
        from apps.audit.models import AuditLog

        token = payload.get('token', '')
        client_ip = payload.get('client_ip', '')
        client_ver = payload.get('client_ver', '')
        public_key = payload.get('public_key', b'')

        try:
            host = Host.objects.get(tunnel_token=token)
            now = timezone.now()
            host.tunnel_status = 'online'
            host.tunnel_connected_at = now
            host.tunnel_last_seen_at = now
            host.tunnel_client_ip = client_ip
            host.tunnel_client_version = client_ver
            if public_key:
                host.tunnel_public_key = public_key
            host.save(update_fields=[
                'tunnel_status', 'tunnel_connected_at',
                'tunnel_last_seen_at', 'tunnel_client_ip',
                'tunnel_client_version', 'tunnel_public_key',
            ])

            AuditLog.objects.create(
                host=host,
                action='tunnel_online',
                details={
                    'token': token,
                    'client_ip': client_ip,
                    'client_ver': client_ver,
                }
            )

            logger.info(
                f'Tunnel online: host={host.name}, '
                f'token={token}, ip={client_ip}'
            )

        except Host.DoesNotExist:
            logger.warning(
                f'Tunnel online event for unknown token: {token}'
            )

    def _handle_tunnel_offline(self, event_type, payload):
        from apps.hosts.models import Host
        from apps.audit.models import AuditLog

        token = payload.get('token', '')

        try:
            host = Host.objects.get(tunnel_token=token)
            host.tunnel_status = 'offline'
            host.save(update_fields=['tunnel_status'])

            AuditLog.objects.create(
                host=host,
                action='tunnel_offline',
                details={'token': token}
            )

            logger.info(
                f'Tunnel offline: host={host.name}, token={token}'
            )

        except Host.DoesNotExist:
            logger.warning(
                f'Tunnel offline event for unknown token: {token}'
            )

    def _handle_rdp_connect(self, event_type, payload):
        from apps.audit.models import AuditLog

        token = payload.get('token', '')
        domain = payload.get('domain', '')
        client_ip = payload.get('client_ip', '')

        try:
            from apps.hosts.models import Host
            host = Host.objects.get(tunnel_token=token)

            AuditLog.objects.create(
                host=host,
                action='rdp_connect',
                ip_address=client_ip,
                details={
                    'domain': domain,
                    'token': token,
                }
            )

            logger.info(
                f'RDP connect: host={host.name}, '
                f'domain={domain}, ip={client_ip}'
            )

        except Host.DoesNotExist:
            logger.warning(
                f'RDP connect event for unknown token: {token}'
            )

    def _handle_rdp_disconnect(self, event_type, payload):
        from apps.audit.models import AuditLog

        token = payload.get('token', '')
        domain = payload.get('domain', '')
        duration = payload.get('duration', 0)
        bytes_in = payload.get('bytes_in', 0)
        bytes_out = payload.get('bytes_out', 0)

        try:
            from apps.hosts.models import Host
            host = Host.objects.get(tunnel_token=token)

            AuditLog.objects.create(
                host=host,
                action='rdp_disconnect',
                details={
                    'domain': domain,
                    'duration': duration,
                    'bytes_in': bytes_in,
                    'bytes_out': bytes_out,
                }
            )

            logger.info(
                f'RDP disconnect: host={host.name}, domain={domain}'
            )

        except Host.DoesNotExist:
            logger.warning(
                f'RDP disconnect event for unknown token: {token}'
            )

    def _handle_remote_exec_result(self, event_type, payload):
        from apps.audit.models import AuditLog

        token = payload.get('token', '')
        req_id = payload.get('req_id', '')
        exit_code = payload.get('exit_code', -1)

        try:
            from apps.hosts.models import Host
            host = Host.objects.get(tunnel_token=token)

            AuditLog.objects.create(
                host=host,
                action='remote_exec_result',
                details={
                    'req_id': req_id,
                    'exit_code': exit_code,
                }
            )

            logger.info(
                f'Remote exec result: host={host.name}, '
                f'req_id={req_id}, exit_code={exit_code}'
            )

        except Host.DoesNotExist:
            logger.warning(
                f'Remote exec result event for unknown token: {token}'
            )
