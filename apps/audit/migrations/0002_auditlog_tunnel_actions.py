from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(
                choices=[
                    ('create_user', '创建用户'),
                    ('delete_user', '删除用户'),
                    ('reset_password', '重置密码'),
                    ('connect_host', '连接主机'),
                    ('modify_host', '修改主机'),
                    ('view_password', '查看密码'),
                    ('approve_request', '审批请求'),
                    ('reject_request', '拒绝请求'),
                    ('bootstrap_host', '初始化主机'),
                    ('issue_cert', '签发证书'),
                    ('revoke_cert', '吊销证书'),
                    ('create_host', '创建主机'),
                    ('delete_host', '删除主机'),
                    ('update_host', '更新主机'),
                    ('process_opening_request', '处理开户请求'),
                    ('batch_process_requests', '批量处理请求'),
                    ('login', '用户登录'),
                    ('logout', '用户登出'),
                    ('view_audit_log', '查看审计日志'),
                    ('admin_action', '管理员操作'),
                    ('tunnel_online', '隧道上线'),
                    ('tunnel_offline', '隧道离线'),
                    ('tunnel_heartbeat_timeout', '隧道心跳超时'),
                    ('rdp_connect', 'RDP连接'),
                    ('rdp_disconnect', 'RDP断开'),
                    ('remote_exec', '远程执行命令'),
                    ('remote_exec_result', '远程执行结果'),
                    ('domain_bind', '域名绑定'),
                    ('domain_unbind', '域名解绑'),
                ],
                max_length=50, verbose_name='操作类型'
            ),
        ),
    ]
