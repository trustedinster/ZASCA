"""
测试主机连接的管理命令
"""
from django.core.management.base import BaseCommand
from apps.hosts.models import Host
from utils.winrm_client import WinrmClient
import logging

logger = logging.getLogger("zasca")


class Command(BaseCommand):
    help = '测试主机连接状态'

    def add_arguments(self, parser):
        parser.add_argument('--host-id', type=int, help='特定主机ID进行测试')
        parser.add_argument('--all', action='store_true', help='测试所有主机')

    def handle(self, *args, **options):
        if options['host_id']:
            # 测试特定主机
            try:
                host = Host.objects.get(id=options['host_id'])
                self.test_single_host(host)
            except Host.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'找不到ID为 {options["host_id"]} 的主机')
                )
        elif options['all']:
            # 测试所有主机
            hosts = Host.objects.all()
            for host in hosts:
                self.test_single_host(host)
        else:
            self.stdout.write(
                self.style.WARNING('请提供 --host-id 或 --all 参数')
            )

    def test_single_host(self, host):
        """测试单个主机的连接"""
        try:
            # 创建WinRM客户端测试连接
            client = WinrmClient(
                hostname=host.hostname,
                username=host.username,
                password=host.password,
                port=host.port,
                use_ssl=host.use_ssl
            )
            
            # 尝试执行一个简单命令来测试连接
            result = client.execute_command('whoami')
            
            # 根据执行结果更新主机状态
            if result.success:
                host.status = 'online'
                status_msg = '在线'
                style = self.style.SUCCESS
            else:
                host.status = 'error'
                status_msg = '错误'
                style = self.style.WARNING
                
            host.save(update_fields=['status', 'updated_at'])
            
            self.stdout.write(
                style(f'主机 {host.name} ({host.hostname}) 测试成功 - 状态: {status_msg}')
            )
            
        except Exception as e:
            # 连接失败，设置状态为离线
            host.status = 'offline'
            host.save(update_fields=['status', 'updated_at'])
            
            self.stdout.write(
                self.style.ERROR(f'主机 {host.name} ({host.hostname}) 连接失败 - 状态: 离线')
            )
            logger.error(f"主机连接测试失败 {host.hostname}: {str(e)}")