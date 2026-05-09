"""
DEMO模式启动脚本
"""
import os
from django.conf import settings
from django.core.management.color import color_style


def show_demo_startup_message():
    """
    显示DEMO模式启动提示信息
    """
    if os.environ.get('2C2A_DEMO', '').lower() != '1':
        return

    style = color_style()

    demo_message = """
********************************************************************************
*                           2C2A DEMO MODE ACTIVATED                          *
********************************************************************************
*                                                                              *
*  当前系统运行在DEMO模式下，具有以下特性：                                      *
*                                                                              *
*  🔐 数据库: 使用 DEMO.sqlite3 (数据不会持久保存)                               *
*  👤 预设用户:                                                               *
*     - 用户名: User, 密码: demo_user_password                                 *
*     - 用户名: Admin, 密码: demo_admin_password                              *
*     - 用户名: SuperAdmin, 密码: DemoSuperAdmin123! (如果有创建)              *
*  🛠️ 所有主机始终显示为在线状态                                                *
*  📧 邮件发送功能被模拟（不会实际发送邮件）                                     *
*  🚀 WinRM指令不会实际执行（仅模拟）                                          *
*  🔐 忽略密码复杂度要求                                                      *
*                                                                              *
*  💡 提示: 在DEMO模式下，您可以自由测试所有功能而不影响实际系统                    *
********************************************************************************
"""

    print(style.HTTP_INFO(demo_message))