"""
主机模型定义
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password


class Host(models.Model):
    """
    主机模型
    """
    HOST_TYPE_CHOICES = [
        ('server', '服务器'),
        ('workstation', '工作站'),
        ('laptop', '笔记本'),
        ('desktop', '台式机'),
    ]
    
    STATUS_CHOICES = [
        ('online', '在线'),
        ('offline', '离线'),
        ('error', '错误'),
    ]

    name = models.CharField(max_length=100, verbose_name='主机名称')
    hostname = models.CharField(max_length=255, verbose_name='主机地址')
    port = models.IntegerField(default=5985, verbose_name='WinRM端口')
    rdp_port = models.IntegerField(default=3389, verbose_name='RDP端口')
    use_ssl = models.BooleanField(default=False, verbose_name='使用SSL')
    username = models.CharField(max_length=100, verbose_name='用户名')
    _password = models.CharField(max_length=255, verbose_name='密码', db_column='password')  # 加密存储
    host_type = models.CharField(max_length=20, choices=HOST_TYPE_CHOICES, verbose_name='主机类型')
    os_version = models.CharField(max_length=100, blank=True, verbose_name='操作系统版本')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline', verbose_name='状态')
    description = models.TextField(blank=True, verbose_name='描述')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '主机'
        verbose_name_plural = '主机'
        db_table = 'hosts_host'  # 与数据库中的实际表名一致

    def __str__(self):
        return self.name

    @property
    def password(self):
        """
        获取解密后的密码
        注意：此属性不应在模板或日志中直接使用
        """
        from django.core.signing import Signer
        signer = Signer()
        try:
            return signer.unsign(self._password)
        except:
            # 如果解密失败，说明可能是未加密的旧数据
            return self._password

    @password.setter
    def password(self, raw_password):
        """
        设置并加密密码
        """
        from django.core.signing import Signer
        signer = Signer()
        self._password = signer.sign(raw_password)

    def save(self, *args, **kwargs):
        """
        重写save方法，在保存主机时自动测试连接状态
        """
        # 先调用父类的save方法保存数据
        super().save(*args, **kwargs)
        
        # 测试主机连接状态
        self.test_connection()
    
    def test_connection(self):
        """
        测试主机连接状态
        """
        from utils.winrm_client import WinrmClient
        try:
            # 创建WinRM客户端测试连接
            client = WinrmClient(
                hostname=self.hostname,
                username=self.username,
                password=self.password,  # 使用属性访问解密后的密码
                port=self.port,
                use_ssl=self.use_ssl
            )
            
            # 尝试执行一个简单命令来测试连接
            result = client.execute_command('whoami')
            
            # 根据执行结果更新主机状态
            if result.success:
                self.status = 'online'
            else:
                self.status = 'error'
                
        except Exception as e:
            # 连接失败，设置状态为离线
            self.status = 'offline'
            import logging
            logger = logging.getLogger("zasca")
            logger.error(f"主机连接测试失败 {self.hostname}: {str(e)}")
        
        # 保存更新后的状态
        super().save(update_fields=['status', 'updated_at'])


class HostGroup(models.Model):
    """
    主机组模型
    """
    name = models.CharField(max_length=100, verbose_name='组名称')
    description = models.TextField(blank=True, verbose_name='描述')
    hosts = models.ManyToManyField(Host, blank=True, verbose_name='主机')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '主机组'
        verbose_name_plural = '主机组'
        db_table = 'hosts_hostgroup'
    
    def __str__(self):
        return self.name