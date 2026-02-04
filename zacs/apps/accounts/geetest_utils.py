"""
极验（Geetest）集成工具（仅 v4）
提供二次校验(verify)的封装和前端初始化信息
"""
import json
import logging
import time
import requests
from django.conf import settings
import hmac
import hashlib
from apps.dashboard.models import SystemConfig

logger = logging.getLogger('zasca')

# v4 validate endpoint base
GEETEST_V4_API_SERVER = 'https://gcaptcha4.geetest.com'

# 超时配置（秒）
REQUEST_TIMEOUT = 10


def _get_runtime_keys():
    """Return (captcha_id, captcha_key) by preferring SystemConfig when enabled for geetest, otherwise settings."""
    captcha_id = getattr(settings, 'GEETEST_ID', None)
    captcha_key = getattr(settings, 'GEETEST_KEY', None)

    try:
        config = SystemConfig.get_config()
        if config and config.captcha_provider == 'geetest':
            if config.captcha_id:
                captcha_id = config.captcha_id
            if config.captcha_key:
                captcha_key = config.captcha_key
    except Exception:
        # if models not ready or DB unavailable, ignore and fall back to settings
        pass

    return captcha_id, captcha_key


def get_geetest_init(request):
    """Return minimal init info for frontend v4 usage.

    Returns: dict with keys:
      - captcha_id: id for initGeetest4
      - enabled: whether SystemConfig enables geetest or settings present
    """
    captcha_id, captcha_key = _get_runtime_keys()

    enabled = bool(captcha_id and captcha_key)

    # cache server status in session (simple)
    request.session['geetest_server_status'] = enabled
    request.session['geetest_server_status_ts'] = int(time.time())

    return {
        'captcha_id': captcha_id,
        'enabled': enabled,
        'success': 1 if enabled else 0,
    }


def verify_geetest_v4(lot_number, captcha_output, pass_token, gen_time, captcha_id=None):
    """使用 Geetest v4 的二次校验接口进行服务器端验证。

    参考接口：POST https://gcaptcha4.geetest.com/validate?captcha_id=xxxxx
    请求体（application/x-www-form-urlencoded）：
      lot_number, captcha_output, pass_token, gen_time, sign_token

    sign_token = HMAC_SHA256(key=captcha_key, message=lot_number)

    返回 (bool, message_or_response_dict)
    """
    # 获取运行时的 id/key（优先使用 SystemConfig）
    runtime_id, runtime_key = _get_runtime_keys()
    captcha_id = captcha_id or runtime_id
    captcha_key = runtime_key

    # 基本参数检查
    if not all([lot_number, captcha_output, pass_token, gen_time, captcha_id, captcha_key]):
        return False, '参数不完整或未配置极验ID/Key'

    try:
        # sign token: HMAC-SHA256(lot_number, captcha_key)
        # 注意：hmac.new(key, message, digestmod) — key和message都应为bytes
        sign_token = hmac.new(captcha_key.encode('utf-8'), lot_number.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()

        data = {
            'lot_number': lot_number,
            'captcha_output': captcha_output,
            'pass_token': pass_token,
            'gen_time': gen_time,
            'sign_token': sign_token,
        }

        url = f'{GEETEST_V4_API_SERVER}/validate'
        # 添加captcha_id作为查询参数
        params = {'captcha_id': captcha_id}
        
        # 使用 application/x-www-form-urlencoded 提交
        r = requests.post(url, data=data, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()

        # 解析 JSON 响应
        try:
            resp = r.json()
        except ValueError:
            # 非 JSON 返回
            logger.error('Geetest v4 validate returned non-JSON response: %s', r.text)
            return False, {'status': 'error', 'msg': '非JSON响应', 'raw': r.text}

        # 成功时 resp['result'] == 'success' (注意：文档中提到的是result而不是status)
        result = resp.get('result')
        reason = resp.get('reason', '')

        if result == 'success':
            return True, resp
        else:
            error_msg = f'验证码校验失败: {reason}' if reason else f'验证码校验失败: {resp}'
            logger.warning(f'Geetest v4 validation failed: {error_msg}')
            return False, resp

    except requests.Timeout:
        logger.error('Geetest v4 validate request timed out')
        return False, {'status': 'error', 'reason': '请求超时'}
    except requests.RequestException as e:
        logger.exception('请求 Geetest v4 校验接口失败: %s', e)
        return False, {'status': 'error', 'reason': '请求 geetest API 失败'}
    except Exception as e:
        logger.exception('Geetest v4 verify unexpected error: %s', e)
        return False, {'status': 'error', 'reason': '验证异常'}


def verify_turnstile(response_token, remoteip=None):
    """Verify Cloudflare Turnstile token server-side.

    POST https://challenges.cloudflare.com/turnstile/v0/siteverify
    params: secret, response, remoteip (optional)

    Returns (bool, resp_dict)
    """
    secret = getattr(settings, 'TURNSTILE_SECRET_KEY', None)
    try:
        cfg = SystemConfig.get_config()
        if cfg and cfg.captcha_provider == 'turnstile' and cfg.captcha_key:
            secret = cfg.captcha_key
    except Exception:
        pass

    if not secret or not response_token:
        return False, {'success': False, 'error': 'missing secret or response'}

    try:
        url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        data = {
            'secret': secret,
            'response': response_token,
        }
        if remoteip:
            data['remoteip'] = remoteip

        r = requests.post(url, data=data, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        resp = r.json()
        # resp['success'] is True/False
        return bool(resp.get('success')), resp
    except requests.RequestException as e:
        logger.exception('Turnstile verify request failed: %s', e)
        return False, {'success': False, 'error': 'request failed'}
    except Exception as e:
        logger.exception('Turnstile verify unexpected error: %s', e)
        return False, {'success': False, 'error': 'unexpected error'}