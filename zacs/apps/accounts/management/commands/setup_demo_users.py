"""
DEMO模式用户初始化命令
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
import os


class Command(BaseCommand):
    help = '初始化DEMO模式下的用户和权限'

    def handle(self, *args, **options):
        if os.environ.get('ZASCA_DEMO', '').lower() != '1':
            self.stdout.write(
                self.style.WARNING('非DEMO模式，跳过用户初始化')
            )
            return

        User = get_user_model()

        # 创建User用户
        user, created = User.objects.get_or_create(
            username='User',
            defaults={
                'email': 'user@example.com',
                'first_name': 'Demo',
                'last_name': 'User',
                'is_active': True,
            }
        )
        if created:
            user.set_password('demo_user_password')
            user.save()
            self.stdout.write(
                self.style.SUCCESS('成功创建User用户')
            )
        else:
            self.stdout.write(
                self.style.WARNING('User用户已存在')
            )

        # 创建Admin用户
        admin, created = User.objects.get_or_create(
            username='Admin',
            defaults={
                'email': 'admin@example.com',
                'first_name': 'Demo',
                'last_name': 'Admin',
                'is_staff': True,
                'is_active': True,
            }
        )
        if created:
            admin.set_password('demo_admin_password')
            # 分配特定权限
            self.assign_demo_permissions(admin)
            admin.save()
            self.stdout.write(
                self.style.SUCCESS('成功创建Admin用户并分配权限')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Admin用户已存在')
            )

    def assign_demo_permissions(self, user):
        """
        为DEMO模式下的Admin用户分配特定权限
        """
        permissions = [
            # View登录日志
            ('accounts', 'loginlog', 'view'),
            # View日志记录 (UserActivity)
            ('dashboard', 'useractivity', 'view'),
            # View开户申请
            ('operations', 'accountopeningrequest', 'view'),
            # Change开户申请
            ('operations', 'accountopeningrequest', 'change'),
            # View云电脑用户
            ('operations', 'cloudcomputeruser', 'view'),
            # Change云电脑用户
            ('operations', 'cloudcomputeruser', 'change'),
            # View产品
            ('operations', 'product', 'view'),
        ]

        for app_label, model, perm_action in permissions:
            try:
                content_type = ContentType.objects.get(app_label=app_label, model=model)
                permission_codename = f'{perm_action}_{model}'
                permission = Permission.objects.get(content_type=content_type, codename=permission_codename)
                user.user_permissions.add(permission)
            except ContentType.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"ContentType not found: {app_label}.{model}")
                )
            except Permission.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Permission not found: {app_label}.{model}.{perm_action}")
                )