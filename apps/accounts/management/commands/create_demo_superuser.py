"""
创建DEMO超级管理员用户命令
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os


class Command(BaseCommand):
    help = '在DEMO模式下创建超级管理员用户'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='SuperAdmin',
            help='超级管理员用户名 (默认: SuperAdmin)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='superadmin@example.com',
            help='超级管理员邮箱 (默认: superadmin@example.com)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='DemoSuperAdmin123!',
            help='超级管理员密码 (默认: DemoSuperAdmin123!)'
        )

    def handle(self, *args, **options):
        if os.environ.get('ZASCA_DEMO', '').lower() != '1':
            self.stdout.write(
                self.style.ERROR('请设置 ZASCA_DEMO=1 环境变量以在DEMO模式下运行此命令')
            )
            return

        User = get_user_model()
        
        username = options['username']
        email = options['email']
        password = options['password']

        # 检查用户是否已存在
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'用户 {username} 已存在，跳过创建')
            )
            return

        # 创建超级用户
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            first_name='Demo',
            last_name='SuperAdmin'
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'成功创建超级管理员用户: {username}\n'
                f'用户名: {username}\n'
                f'邮箱: {email}\n'
                f'密码: {password}'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                '注意：在DEMO模式下，此用户拥有完整的超级用户权限'
            )
        )