from django.test import TestCase, Client
from unittest.mock import patch
from django.urls import reverse

from apps.accounts import geetest_utils


class GeetestUtilsTests(TestCase):
    def test_verify_missing_params(self):
        ok, msg = geetest_utils.verify_geetest_v4('', '', '', '')
        self.assertFalse(ok)
        self.assertIn('参数不完整', msg)

    @patch('apps.accounts.geetest_utils._get_runtime_keys', return_value=('captcha-id','private-key'))
    @patch('apps.accounts.geetest_utils.requests.post')
    def test_verify_success(self, mock_post, mock_keys):
        class R:
            def raise_for_status(self):
                return None
            def json(self):
                return {'status': 'success', 'result': 'success'}
        mock_post.return_value = R()
        ok, msg = geetest_utils.verify_geetest_v4('lot', 'out', 'pass', '123')
        self.assertTrue(ok)

    @patch('apps.accounts.geetest_utils._get_runtime_keys', return_value=('captcha-id','private-key'))
    @patch('apps.accounts.geetest_utils.requests.post')
    def test_verify_fail(self, mock_post, mock_keys):
        class R:
            def raise_for_status(self):
                return None
            def json(self):
                return {'status': 'success', 'result': 'fail', 'reason': 'pass_token expire'}
        mock_post.return_value = R()
        ok, resp = geetest_utils.verify_geetest_v4('lot', 'out', 'pass', '123')
        self.assertFalse(ok)
        self.assertIn('result', resp)


class GeetestEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('apps.accounts.geetest_utils._get_runtime_keys')
    def test_register_endpoint(self, mock_keys):
        mock_keys.return_value = ('captcha-id-123', 'private-key')
        resp = self.client.get(reverse('accounts:geetest_register'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('captcha_id', data)
        self.assertIn('enabled', data)
