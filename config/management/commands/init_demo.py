"""
初始化DEMO环境的管理命令
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import DEFAULT_DB_ALIAS
import os


class Command(BaseCommand):
    help = '初始化DEMO环境，包括数据库和用户'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新初始化DEMO环境（删除现有DEMO数据库）',
        )

    def handle(self, *args, **options):
        # 检查是否在DEMO模式下运行
        if os.environ.get('ZASCA_DEMO', '').lower() != '1':
            self.stdout.write(
                self.style.ERROR('请设置 ZASCA_DEMO=1 环境变量以运行DEMO模式')
            )
            return

        import shutil
        from pathlib import Path
        from django.conf import settings
        
        demo_db_path = settings.BASE_DIR / 'DEMO.sqlite3'
        
        if demo_db_path.exists() and not options['force']:
            self.stdout.write(
                self.style.WARNING(f'DEMO数据库已存在: {demo_db_path}')
                + '\n使用 --force 参数强制重新初始化'
            )
            return

        # 删除现有的DEMO数据库
        if demo_db_path.exists():
            demo_db_path.unlink()
            self.stdout.write(
                self.style.SUCCESS('已删除现有DEMO数据库')
            )

        # 运行迁移
        self.stdout.write('正在运行数据库迁移...')
        call_command('migrate', verbosity=1, interactive=False, database=DEFAULT_DB_ALIAS)

        # 创建DEMO用户
        self.stdout.write('正在创建DEMO用户...')
        call_command('setup_demo_users', verbosity=1)

        # 创建一些示例数据
        self.create_demo_data()

        self.stdout.write(
            self.style.SUCCESS('DEMO环境初始化完成！')
        )
        self.stdout.write('用户名: User, 密码: demo_user_password')
        self.stdout.write('管理员: Admin, 密码: demo_admin_password')

    def create_demo_data(self):
        """创建DEMO环境的示例数据"""
        from apps.accounts.models import LoginLog
        from apps.operations.models import Product, AccountOpeningRequest
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        import random
        
        User = get_user_model()
        
        # 获取DEMO用户
        try:
            user = User.objects.get(username='User')
            admin = User.objects.get(username='Admin')
        except User.DoesNotExist:
            return  # 如果用户不存在，则跳过示例数据创建

        # 创建一些示例登录日志
        for i in range(5):
            LoginLog.objects.get_or_create(
                user=user,
                ip_address=f'192.168.1.{random.randint(1, 100)}',
                user_agent='Mozilla/5.0 (DEMO Mode)',
                login_type='web',
                status='success',
                created_at=timezone.now()
            )

        # 创建示例产品
        from apps.hosts.models import Host
        # 创建一个示例主机
        demo_host, created = Host.objects.get_or_create(
            name='DEMO主机',
            hostname='demo.example.com',
            username='demo',
            host_type='server',
            defaults={
                'port': 5985,
                'description': 'DEMO模式下的示例主机',
                'status': 'online',  # 在DEMO模式下总是在线
            }
        )
        demo_host.password = 'demo_password'
        demo_host.save()

        # 创建示例产品
        demo_product, created = Product.objects.get_or_create(
            name='DEMO产品',
            display_name='DEMO云电脑',
            description='DEMO模式下的示例产品',
            display_description='DEMO云电脑产品',
            host=demo_host,
            defaults={
                'rdp_port': 3389,
                'display_hostname': 'demo.example.com',
                'is_available': True,
            }
        )

        # 创建示例开户申请
        for i in range(3):
            AccountOpeningRequest.objects.get_or_create(
                applicant=admin,
                contact_email=f'user{i}@demo.com',
                username=f'demo_user_{i}',
                user_fullname=f'DEMO User {i}',
                user_email=f'user{i}@demo.com',
                target_product=demo_product,
                defaults={
                    'status': random.choice(['pending', 'approved', 'completed']),
                    'user_description': f'DEMO用户 {i} 的描述',
                }
            )