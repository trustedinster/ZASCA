from django.conf import settings

class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not settings.DEBUG:
            csp_parts = [
                "default-src 'self'",

                # JS：极验 + 你的静态站
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                "https://static.2c2a.cc.cd "
                "https://static.geetest.com https://static.geevisit.com "
                "https://gcaptcha4.geetest.com https://gcaptcha4.geevisit.com",

                # CSS：极验 + 你的静态站（关键：之前这里没加极验域名，所以 CSS 被拦）
                "style-src 'self' 'unsafe-inline' "
                "https://static.2c2a.cc.cd "
                "https://static.geetest.com https://static.geevisit.com",

                # 图片：极验 + 你的静态站
                "img-src 'self' data: blob: "
                "https://static.2c2a.cc.cd "
                "https://static.geetest.com https://static.geevisit.com",

                # 字体：极验 + 你的静态站（极验也用到了字体）
                "font-src 'self' "
                "https://static.2c2a.cc.cd "
                "https://static.geetest.com https://static.geevisit.com",

                # AJAX / WebSocket：极验接口
                "connect-src 'self' wss: ws: "
                "https://gcaptcha4.geetest.com https://gcaptcha4.geevisit.com",

                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ]
            response['Content-Security-Policy'] = '; '.join(csp_parts)

            response['Permissions-Policy'] = (
                'geolocation=(), microphone=(), camera=(), '
                'payment=(), usb=(), magnetometer=(), gyroscope=(), '
                'accelerometer=()'
            )

        return response
