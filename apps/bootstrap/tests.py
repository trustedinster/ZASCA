from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.hosts.models import Host
from .models import InitialToken, ActiveSession
from django.contrib.auth import get_user_model
import pyotp
import uuid


User = get_user_model()


class BootstrapTokenTestCase(TestCase):
    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # 创建测试主机
        self.host = Host.objects.create(
            name='Test Host',
            hostname='test-host.local',
            username='testuser',
            password='encrypted_password',
            port=5985,
            rdp_port=3389,
            host_type='windows',
            created_by=self.user
        )

    def test_initial_token_creation(self):
        """测试初始令牌创建"""
        expires_at = timezone.now() + timedelta(hours=24)
        
        token = InitialToken.objects.create(
            token='test-token-123',
            host=self.host,
            expires_at=expires_at,
            status='ISSUED'
        )
        
        self.assertEqual(token.token, 'test-token-123')
        self.assertEqual(token.host, self.host)
        self.assertEqual(token.status, 'ISSUED')
        self.assertFalse(token.expires_at < timezone.now())

    def test_totp_secret_generation(self):
        """测试TOTP密钥生成"""
        expires_at = timezone.now() + timedelta(hours=24)
        
        token = InitialToken.objects.create(
            token='test-token-totp',
            host=self.host,
            expires_at=expires_at,
            status='ISSUED'
        )
        
        totp_secret = token.generate_totp_secret()
        
        # 验证生成的密钥是有效的Base32编码
        self.assertIsNotNone(totp_secret)
        self.assertTrue(len(totp_secret) > 0)
        
        # 尝试使用生成的密钥创建TOTP对象
        totp = pyotp.TOTP(totp_secret)
        current_code = totp.now()
        
        # 验证生成的验证码是6位数字
        self.assertEqual(len(current_code), 6)
        self.assertTrue(current_code.isdigit())

    def test_active_session_creation(self):
        """测试活动会话创建"""
        session_token = str(uuid.uuid4())
        bound_ip = '192.168.1.100'
        expires_at = timezone.now() + timedelta(days=1)
        
        session = ActiveSession.objects.create(
            session_token=session_token,
            host=self.host,
            bound_ip=bound_ip,
            expires_at=expires_at
        )
        
        self.assertEqual(session.session_token, session_token)
        self.assertEqual(session.host, self.host)
        self.assertEqual(session.bound_ip, bound_ip)
        self.assertEqual(session.expires_at, expires_at)

    def test_token_status_transitions(self):
        """测试令牌状态转换"""
        expires_at = timezone.now() + timedelta(hours=24)
        
        token = InitialToken.objects.create(
            token='test-status-token',
            host=self.host,
            expires_at=expires_at,
            status='ISSUED'
        )
        
        # 初始状态
        self.assertEqual(token.status, 'ISSUED')
        
        # 验证后状态
        token.status = 'TOTP_VERIFIED'
        token.save()
        self.assertEqual(token.status, 'TOTP_VERIFIED')
        
        # 消耗后状态
        token.status = 'CONSUMED'
        token.save()
        self.assertEqual(token.status, 'CONSUMED')

    def test_token_expiry_check(self):
        """测试令牌过期检查"""
        # 未过期令牌
        future_time = timezone.now() + timedelta(hours=1)
        token = InitialToken.objects.create(
            token='future-token',
            host=self.host,
            expires_at=future_time,
            status='ISSUED'
        )
        
        self.assertGreater(token.expires_at, timezone.now())
        
        # 已过期令牌
        past_time = timezone.now() - timedelta(hours=1)
        expired_token = InitialToken.objects.create(
            token='past-token',
            host=self.host,
            expires_at=past_time,
            status='ISSUED'
        )
        
        self.assertLess(expired_token.expires_at, timezone.now())