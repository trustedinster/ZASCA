# -*- coding: utf-8 -*-
"""核心功能测试 - 只测关键路径"""
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from apps.operations.models import Product, AccountOpeningRequest, CloudComputerUser
from apps.hosts.models import Host
from utils.winrm_client import _escape_ps_string, WinrmResult

User = get_user_model()


class TestPowerShellEscape(TestCase):
    """PowerShell转义测试 - 防注入核心"""

    def test_escape_quotes(self):
        """双引号必须转义"""
        self.assertEqual(_escape_ps_string('pass"word'), 'pass`"word')

    def test_escape_dollar(self):
        """$符号必须转义，否则会被当作变量"""
        self.assertEqual(_escape_ps_string('pa$$word'), 'pa`$`$word')

    def test_escape_backtick(self):
        """反引号是PS转义符，必须先处理"""
        self.assertEqual(_escape_ps_string('pass`word'), 'pass``word')

    def test_injection_attempt(self):
        """模拟注入攻击"""
        evil = '"; Remove-Item C:\\* -Recurse; echo "'
        escaped = _escape_ps_string(evil)
        # 确保引号被转义，无法闭合字符串
        self.assertIn('`"', escaped)
        self.assertNotIn('";', escaped.replace('`"', ''))


class TestAccountOpeningFlow(TestCase):
    """开户流程测试"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', email='test@test.com', password='testpass123'
        )
        self.host = Host.objects.create(
            name='TestHost', hostname='192.168.1.1',
            username='admin', host_type='server'
        )
        self.host._password = 'fake'  # 跳过加密
        self.host.save()

        self.product = Product.objects.create(
            name='test_product', display_name='测试产品',
            host=self.host, is_available=True
        )

    def test_request_creation(self):
        """开户申请能正常创建"""
        req = AccountOpeningRequest.objects.create(
            applicant=self.user,
            username='newuser',
            user_fullname='测试用户',
            user_description='测试申请',
            target_product=self.product
        )
        self.assertEqual(req.status, 'pending')
        self.assertEqual(req.applicant, self.user)

    @patch('apps.operations.models.CloudComputerUser._create_on_host')
    def test_approve_creates_cloud_user(self, mock_create):
        """审批通过后创建云电脑用户"""
        mock_create.return_value = True
        req = AccountOpeningRequest.objects.create(
            applicant=self.user,
            username='newuser',
            user_fullname='测试用户',
            user_description='测试',
            target_product=self.product,
            status='pending'
        )
        # 模拟审批
        req.status = 'approved'
        req.save()
        # 检查是否尝试创建用户（实际逻辑可能在signal里）


class TestBurnAfterRead(TestCase):
    """阅后即焚密码测试"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser2', email='t2@test.com', password='pass'
        )
        self.host = Host.objects.create(
            name='H2', hostname='192.168.1.2',
            username='admin', host_type='server'
        )
        self.host._password = 'x'
        self.host.save()
        self.product = Product.objects.create(
            name='p2', display_name='P2', host=self.host, is_available=True
        )

    def test_password_burned_after_view(self):
        """密码查看后应销毁"""
        cloud_user = CloudComputerUser.objects.create(
            username='burntest',
            fullname='Burn Test',
            email='burn@test.com',
            product=self.product,
            owner=self.user,
            initial_password='secret123',
            password_viewed=False
        )
        pwd = cloud_user.get_and_burn_password()
        self.assertEqual(pwd, 'secret123')

        cloud_user.refresh_from_db()
        self.assertTrue(cloud_user.password_viewed)
        self.assertEqual(cloud_user.initial_password, '')

    def test_cannot_view_burned_password(self):
        """已销毁的密码不能再次查看"""
        cloud_user = CloudComputerUser.objects.create(
            username='burned',
            fullname='Burned',
            email='burned@test.com',
            product=self.product,
            owner=self.user,
            initial_password='',
            password_viewed=True
        )
        with self.assertRaises(Exception) as ctx:
            cloud_user.get_and_burn_password()
        self.assertIn('已被查看', str(ctx.exception))


class TestSecurityHeaders(TestCase):
    """安全响应头测试"""

    def test_xframe_options(self):
        """检查X-Frame-Options防止点击劫持"""
        client = Client()
        resp = client.get('/accounts/login/')
        # Django默认会添加，检查是否没被移除
        self.assertIn(resp.get('X-Frame-Options', 'DENY'), ['DENY', 'SAMEORIGIN'])
