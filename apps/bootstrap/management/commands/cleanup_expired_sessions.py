from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.bootstrap.models import ActiveSession
from datetime import timedelta


class Command(BaseCommand):
    help = '清理过期的活动会话'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要删除的会话，不实际删除',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # 查找过期的会话
        expired_sessions = ActiveSession.objects.filter(expires_at__lt=timezone.now())
        
        if expired_sessions.exists():
            self.stdout.write(
                self.style.SUCCESS(
                    f'找到 {expired_sessions.count()} 个过期的会话'
                )
            )
            
            if dry_run:
                for session in expired_sessions:
                    self.stdout.write(
                        f"- Session: {session.session_token[:12]}..., "
                        f"Host: {session.host.name}, "
                        f"Expired: {session.expires_at}"
                    )
            else:
                deleted_count = expired_sessions.delete()[0]
                self.stdout.write(
                    self.style.SUCCESS(
                        f'成功删除 {deleted_count} 个过期的会话'
                    )
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('没有找到过期的会话')
            )