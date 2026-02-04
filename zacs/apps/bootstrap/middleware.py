import hashlib
import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages

logger = logging.getLogger('zasca')


def get_client_ip(request):
    """获取真实客户端IP"""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def make_fingerprint(request):
    """生成会话指纹: IP + UA哈希"""
    ip = get_client_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '')
    raw = f"{ip}|{ua}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class SessionValidationMiddleware(MiddlewareMixin):
    """会话安全中间件 - 指纹绑定 + 防劫持"""

    BYPASS_PATHS = ['/admin/login/', '/accounts/login/', '/static/', '/media/']

    def process_request(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None

        # 跳过静态资源和登录页
        path = request.path
        if any(path.startswith(p) for p in self.BYPASS_PATHS):
            return None

        session = request.session
        current_fp = make_fingerprint(request)
        stored_fp = session.get('_fp')

        if stored_fp is None:
            # 首次访问，记录指纹
            session['_fp'] = current_fp
            session['_fp_ip'] = get_client_ip(request)
            self._record_session(request, current_fp)
        elif stored_fp != current_fp:
            # 指纹不匹配，可能会话被劫持
            self._log_hijack_attempt(request, stored_fp, current_fp)
            logout(request)
            messages.error(request, '检测到会话异常，请重新登录')
            return redirect('/accounts/login/')

        return None

    def _record_session(self, request, fingerprint):
        """记录会话到数据库"""
        try:
            from apps.audit.models import SessionActivity
            session_key = request.session.session_key
            if not session_key:
                return
            SessionActivity.objects.update_or_create(
                session_key=session_key,
                defaults={
                    'user': request.user,
                    'ip_address': get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                    'is_active': True
                }
            )
        except Exception as e:
            logger.warning(f"记录会话失败: {e}")

    def _log_hijack_attempt(self, request, old_fp, new_fp):
        """记录劫持尝试"""
        try:
            from apps.audit.models import SecurityEvent
            SecurityEvent.objects.create(
                event_type='suspicious_activity',
                severity='high',
                user=request.user,
                ip_address=get_client_ip(request),
                description=f"会话指纹变更，疑似劫持。原:{old_fp[:8]}.. 新:{new_fp[:8]}.."
            )
            logger.warning(f"会话劫持检测: user={request.user.username} old={old_fp[:8]} new={new_fp[:8]}")
        except Exception as e:
            logger.error(f"记录安全事件失败: {e}")


class SessionPersistenceMiddleware(MiddlewareMixin):
    """会话持久化中间件 - 延长活跃用户会话"""

    EXTEND_THRESHOLD = 300  # 5分钟内有活动则延长

    def process_request(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None

        session = request.session
        if session.get_expiry_age() < self.EXTEND_THRESHOLD:
            # 即将过期，延长会话
            session.set_expiry(session.get_expiry_age() + 1800)  # +30分钟
        return None
