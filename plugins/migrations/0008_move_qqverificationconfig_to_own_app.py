from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('plugins', '0007_add_use_default_bot_and_group_ids'),
        ('qq_verification', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='QQVerificationConfig',
                ),
            ],
            database_operations=[],
        ),
    ]
