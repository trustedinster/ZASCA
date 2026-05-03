from django.db import migrations


def migrate_qq_bot_config_to_plugin(apps, schema_editor):
    SystemConfig = apps.get_model('dashboard', 'SystemConfig')
    PluginRecord = apps.get_model('plugins', 'PluginRecord')
    PluginConfiguration = apps.get_model(
        'plugins', 'PluginConfiguration'
    )

    try:
        config = SystemConfig.objects.first()
        if not config:
            return
    except Exception:
        return

    record, _ = PluginRecord.objects.get_or_create(
        plugin_id='qq_verification',
        defaults={
            'name': 'QQ Verification Plugin',
            'version': '1.0.0',
            'description': 'QQ验证插件',
            'is_active': True,
        },
    )

    for field_name in (
        'qq_bot_host', 'qq_bot_port', 'qq_bot_token'
    ):
        value = getattr(config, field_name, None) or ''
        PluginConfiguration.objects.update_or_create(
            plugin=record,
            key=field_name,
            defaults={'value': value},
        )


def reverse_migrate(apps, schema_editor):
    SystemConfig = apps.get_model('dashboard', 'SystemConfig')
    PluginRecord = apps.get_model('plugins', 'PluginRecord')
    PluginConfiguration = apps.get_model(
        'plugins', 'PluginConfiguration'
    )

    try:
        record = PluginRecord.objects.get(
            plugin_id='qq_verification'
        )
    except PluginRecord.DoesNotExist:
        return

    config = SystemConfig.objects.first()
    if not config:
        return

    for field_name in (
        'qq_bot_host', 'qq_bot_port', 'qq_bot_token'
    ):
        try:
            pc = PluginConfiguration.objects.get(
                plugin=record, key=field_name
            )
            setattr(config, field_name, pc.value)
        except PluginConfiguration.DoesNotExist:
            pass

    config.save()


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0009_remove_qq_bot_fields'),
        ('plugins', '0007_add_use_default_bot_and_group_ids'),
    ]

    operations = [
        migrations.RunPython(
            migrate_qq_bot_config_to_plugin,
            reverse_migrate,
        ),
    ]
