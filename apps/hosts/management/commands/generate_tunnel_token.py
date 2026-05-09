import secrets
from django.core.management.base import BaseCommand
from apps.hosts.models import Host


class Command(BaseCommand):
    help = '为隧道模式主机生成隧道Token'

    def add_arguments(self, parser):
        parser.add_argument(
            'host_id',
            type=int,
            help='主机ID',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            default=False,
            help='强制重新生成Token（即使已存在）',
        )

    def handle(self, *args, **options):
        host_id = options['host_id']
        force = options['force']

        try:
            host = Host.objects.get(id=host_id)
        except Host.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f'主机ID {host_id} 不存在')
            )
            return

        if host.tunnel_token and not force:
            self.stderr.write(
                self.style.WARNING(
                    f'主机 {host.name} 已有Token: {host.tunnel_token}\n'
                    f'使用 --force 强制重新生成'
                )
            )
            return

        token = secrets.token_urlsafe(32)
        host.tunnel_token = token
        host.connection_type = 'tunnel'
        host.tunnel_status = 'offline'
        host.save(update_fields=[
            'tunnel_token', 'connection_type', 'tunnel_status',
        ])

        self.stdout.write(
            self.style.SUCCESS(
                f'主机 {host.name} 的隧道Token已生成:\n'
                f'  Token: {token}\n'
                f'  连接类型已设置为: tunnel\n'
                f'\n'
                f'请将此Token配置到边缘端 2c2a-tunnel:\n'
                f'  2c2a-tunnel.exe install -token {token} -server wss://<gateway>:9000'
            )
        )
