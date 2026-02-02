from django.core.management.base import BaseCommand
from apps.hosts.models import Host
from apps.operations.models import PublicHostInfo


class Command(BaseCommand):
    help = '为现有主机创建公开主机信息'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制为所有主机创建公开信息，即使已存在',
        )

    def handle(self, *args, **options):
        force = options['force']
        hosts = Host.objects.all()
        created_count = 0
        skipped_count = 0

        for host in hosts:
            # 检查是否已存在对应的 PublicHostInfo
            if not force and PublicHostInfo.objects.filter(internal_host=host).exists():
                self.stdout.write(
                    self.style.WARNING(f'Skipping {host.name} - PublicHostInfo already exists')
                )
                skipped_count += 1
                continue

            # 创建 PublicHostInfo
            public_info, created = PublicHostInfo.objects.get_or_create(
                internal_host=host,
                defaults={
                    'display_name': host.name,
                    'display_description': host.description,
                    'display_hostname': host.hostname,
                    'display_rdp_port': host.rdp_port,
                    'is_available': True,
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created PublicHostInfo for {host.name}')
                )
            else:
                # 如果记录已存在但在强制模式下，更新它
                if force:
                    public_info.display_name = host.name
                    public_info.display_description = host.description
                    public_info.display_hostname = host.hostname
                    public_info.display_rdp_port = host.rdp_port
                    public_info.is_available = True
                    public_info.save()
                    self.stdout.write(
                        self.style.WARNING(f'Updated PublicHostInfo for {host.name}')
                    )

        self.stdout.write(
            self.style.NOTICE(
                f'Completed! Created: {created_count}, Skipped: {skipped_count}'
            )
        )