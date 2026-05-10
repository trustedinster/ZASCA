import os
import logging
import secrets
import requests
import time
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.decorators import login_required, permission_required
from django.core.cache import cache
from utils.helpers import get_client_ip

logger = logging.getLogger(__name__)

TUNNEL_RELEASES_URL = os.environ.get(
    'TUNNEL_RELEASES_URL',
    'https://api.github.com/repos/2c2a/tunnel/releases/latest'
)
TUNNEL_DOWNLOAD_DIR = os.path.join(settings.MEDIA_ROOT, 'tunnel_clients')


def _tunnel_rate_limit(key_prefix, rate='10/m'):
    limit, period = rate.lower().split('/')
    limit = int(limit)
    period_map = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    period_seconds = period_map.get(period, 60)

    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            ip = get_client_ip(request)
            window = int(time.time() // period_seconds)
            cache_key = f'rl:{key_prefix}:{ip}:{window}'
            current = cache.get(cache_key, 0)
            if current >= limit:
                return JsonResponse(
                    {'success': False, 'error': 'Too many requests'},
                    status=429,
                )
            cache.set(cache_key, current + 1, timeout=period_seconds + 1)
            return view_func(request, *args, **kwargs)
        wrapper.__name__ = view_func.__name__
        return wrapper
    return decorator


@csrf_exempt
@require_http_methods(["GET"])
@_tunnel_rate_limit('tunnel_download', '5/m')
def download_tunnel_client(request):
    """
    下载tunnel客户端
    支持从GitHub Release下载或从本地存储下载
    """
    try:
        arch = request.GET.get('arch', 'amd64')
        if arch not in ['amd64', 'arm64']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid architecture. Use amd64 or arm64'
            }, status=400)

        filename = f'2c2a-tunnel-windows-{arch}.exe'
        local_path = os.path.join(TUNNEL_DOWNLOAD_DIR, filename)

        if os.path.exists(local_path):
            return FileResponse(
                open(local_path, 'rb'),
                as_attachment=True,
                filename=filename
            )

        try:
            response = requests.get(TUNNEL_RELEASES_URL, timeout=10)
            response.raise_for_status()
            release_data = response.json()

            download_url = None
            for asset in release_data.get('assets', []):
                if asset['name'] == filename:
                    download_url = asset['browser_download_url']
                    break

            if not download_url:
                return JsonResponse({
                    'success': False,
                    'error': f'Tunnel client not found for architecture: {arch}'
                }, status=404)

            download_response = requests.get(download_url, stream=True, timeout=60)
            download_response.raise_for_status()

            os.makedirs(TUNNEL_DOWNLOAD_DIR, exist_ok=True)

            with open(local_path, 'wb') as f:
                for chunk in download_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return FileResponse(
                open(local_path, 'rb'),
                as_attachment=True,
                filename=filename
            )

        except requests.RequestException as e:
            logger.error(f"Failed to download tunnel client: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to download tunnel client from GitHub'
            }, status=503)

    except Exception as e:
        logger.error(f"Error in download_tunnel_client: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@_tunnel_rate_limit('tunnel_config', '10/m')
def get_tunnel_config(request):
    """
    获取tunnel配置
    需要验证session_token，返回tunnel_token和gateway地址
    """
    try:
        import json
        from apps.bootstrap.models import ActiveSession
        from apps.hosts.models import Host

        data = json.loads(request.body.decode('utf-8'))
        session_token = data.get('session_token')

        if not session_token:
            return JsonResponse({
                'success': False,
                'error': 'session_token is required'
            }, status=400)

        try:
            active_session = ActiveSession.objects.get(
                session_token=session_token,
                expires_at__gt=timezone.now()
            )
        except ActiveSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid or expired session token'
            }, status=401)

        client_ip = get_client_ip(request)
        if active_session.bound_ip != client_ip:
            return JsonResponse({
                'success': False,
                'error': 'IP address mismatch'
            }, status=403)

        host = active_session.host

        if not host.tunnel_token:
            host.tunnel_token = secrets.token_urlsafe(32)
            host.connection_type = 'tunnel'
            host.tunnel_status = 'offline'
            host.save(update_fields=[
                'tunnel_token', 'connection_type', 'tunnel_status'
            ])

        gateway_url = os.environ.get(
            'TUNNEL_GATEWAY_URL',
            'wss://gateway.2c2a.com:9000'
        )

        return JsonResponse({
            'success': True,
            'data': {
                'tunnel_token': host.tunnel_token,
                'gateway_url': gateway_url,
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in get_tunnel_config: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to get tunnel config'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@_tunnel_rate_limit('tunnel_install', '5/m')
def install_tunnel_service(request):
    """
    一键安装tunnel服务
    接收session_token，自动下载、配置并安装tunnel服务
    """
    try:
        import json
        import subprocess
        import tempfile
        from apps.bootstrap.models import ActiveSession

        data = json.loads(request.body.decode('utf-8'))
        session_token = data.get('session_token')
        arch = data.get('arch', 'amd64')

        if not session_token:
            return JsonResponse({
                'success': False,
                'error': 'session_token is required'
            }, status=400)

        try:
            active_session = ActiveSession.objects.get(
                session_token=session_token,
                expires_at__gt=timezone.now()
            )
        except ActiveSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid or expired session token'
            }, status=401)

        config_response = get_tunnel_config(request)
        if config_response.status_code != 200:
            return config_response

        config_data = json.loads(config_response.content)
        tunnel_token = config_data['data']['tunnel_token']
        gateway_url = config_data['data']['gateway_url']

        return JsonResponse({
            'success': True,
            'data': {
                'message': 'Tunnel service installation initiated',
                'tunnel_token': tunnel_token,
                'gateway_url': gateway_url,
                'install_command': f'2c2a-tunnel.exe install -token {tunnel_token} -server {gateway_url}'
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in install_tunnel_service: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to install tunnel service'
        }, status=500)
