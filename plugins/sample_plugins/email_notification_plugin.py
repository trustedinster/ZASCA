"""
邮件通知插件示例
展示如何创建一个邮件通知插件
"""

from plugins.core.base import PluginInterface
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailNotificationPlugin(PluginInterface):
    """
    邮件通知插件
    提供邮件发送功能
    """
    
    def __init__(self):
        super().__init__(
            plugin_id="email_notification_plugin",
            name="Email Notification Plugin",
            version="1.0.0",
            description="提供邮件通知功能的插件"
        )
        self.smtp_server = ""
        self.smtp_port = 587
        self.username = ""
        self.password = ""
        self.sender_email = ""
        self.is_configured = False
        
    def initialize(self) -> bool:
        print(f"初始化 {self.name}")
        # 在实际项目中，这些配置通常从settings或数据库获取
        try:
            # 这里只是示例，实际配置应从安全的地方获取
            import os
            self.smtp_server = os.getenv('SMTP_SERVER', 'localhost')
            self.smtp_port = int(os.getenv('SMTP_PORT', 587))
            self.username = os.getenv('SMTP_USERNAME', '')
            self.password = os.getenv('SMTP_PASSWORD', '')
            self.sender_email = os.getenv('SENDER_EMAIL', '')
            
            if self.smtp_server and self.username and self.password and self.sender_email:
                self.is_configured = True
                print(f"{self.name} 配置完成")
            else:
                print(f"{self.name} 缺少必要配置，将以模拟模式运行")
                
            return True
        except Exception as e:
            print(f"初始化 {self.name} 时出错: {str(e)}")
            return False
        
    def shutdown(self) -> bool:
        print(f"关闭 {self.name}")
        return True
        
    def send_email(self, to_emails, subject, body, html_body=None):
        """
        发送邮件
        :param to_emails: 收件人邮箱列表
        :param subject: 邮件主题
        :param body: 邮件正文（文本格式）
        :param html_body: 邮件正文（HTML格式，可选）
        :return: 发送结果
        """
        try:
            if isinstance(to_emails, str):
                to_emails = [to_emails]
                
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            # 添加文本正文
            msg.attach(MIMEText(body, 'plain'))
            
            # 如果提供了HTML正文，则也添加HTML版本
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
                
            if self.is_configured:
                # 实际发送邮件
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
                server.login(self.username, self.password)
                
                text = msg.as_string()
                server.sendmail(self.sender_email, to_emails, text)
                server.quit()
                
                print(f"邮件已发送给: {to_emails}")
                return {'success': True, 'message': f'邮件已发送给 {len(to_emails)} 个收件人'}
            else:
                # 模拟发送（仅用于演示）
                print(f"模拟发送邮件给: {to_emails}")
                print(f"主题: {subject}")
                print(f"内容: {body[:100]}...")  # 只打印前100个字符
                return {'success': True, 'message': '邮件已模拟发送（未配置SMTP）'}
                
        except Exception as e:
            error_msg = f"发送邮件失败: {str(e)}"
            print(error_msg)
            return {'success': False, 'error': error_msg}
            
    def send_notification(self, to_email, notification_type, data):
        """
        发送特定类型的系统通知
        :param to_email: 收件人邮箱
        :param notification_type: 通知类型
        :param data: 通知数据
        :return: 发送结果
        """
        subjects = {
            'welcome': '欢迎加入我们的平台',
            'password_reset': '密码重置请求',
            'account_update': '账户信息更新',
            'system_alert': '系统警报'
        }
        
        bodies = {
            'welcome': f"您好，\n\n欢迎加入我们的平台！您的用户名是 {data.get('username', '用户')}。",
            'password_reset': f"您好，\n\n您请求重置密码，请使用以下链接完成操作：{data.get('reset_link', '#')}",
            'account_update': f"您好，\n\n您的账户信息已更新。更改了: {data.get('changed_fields', '未知')}",
            'system_alert': f"系统警报：{data.get('alert_message', '未知警报')}"
        }
        
        subject = subjects.get(notification_type, '系统通知')
        body = bodies.get(notification_type, '您有一条新的系统通知。')
        
        return self.send_email(to_email, subject, body)


# 高级邮件插件，具有模板功能
class AdvancedEmailPlugin(PluginInterface):
    """
    高级邮件插件
    提供模板化邮件发送功能
    """
    
    def __init__(self):
        super().__init__(
            plugin_id="advanced_email_plugin",
            name="Advanced Email Plugin",
            version="1.0.0",
            description="提供高级邮件功能（模板、队列等）的插件"
        )
        self.templates = {}
        self.email_queue = []
        
    def initialize(self) -> bool:
        print(f"初始化 {self.name}")
        # 预设一些常用模板
        self.templates = {
            'welcome': {
                'subject': '欢迎 {{ username }} 加入 {{ site_name }}',
                'body': '您好 {{ username }}，\n\n欢迎加入 {{ site_name }}！我们很高兴您成为我们社区的一员。'
            },
            'notification': {
                'subject': '{{ site_name }} - {{ title }}',
                'body': '您好 {{ username }}，\n\n{{ content }}'
            }
        }
        return True
        
    def shutdown(self) -> bool:
        print(f"关闭 {self.name}")
        # 在关闭时尝试发送队列中的邮件
        self.process_queue()
        return True
        
    def register_template(self, name, subject, body):
        """注册新的邮件模板"""
        self.templates[name] = {
            'subject': subject,
            'body': body
        }
        
    def render_template(self, template_name, context):
        """渲染邮件模板"""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
            
        template = self.templates[template_name]
        subject = template['subject']
        body = template['body']
        
        # 简单的模板渲染
        for key, value in context.items():
            placeholder = '{{ ' + key + ' }}'
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
            
        return subject, body
        
    def queue_email(self, to_emails, template_name, context):
        """将邮件添加到发送队列"""
        try:
            subject, body = self.render_template(template_name, context)
            email_data = {
                'to_emails': to_emails,
                'subject': subject,
                'body': body,
                'timestamp': __import__('time').time()
            }
            self.email_queue.append(email_data)
            return {'success': True, 'queued': True, 'queue_size': len(self.email_queue)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def process_queue(self):
        """处理邮件队列"""
        processed = 0
        for email_data in self.email_queue[:]:  # 创建副本以避免在迭代时修改
            # 这里应该实际发送邮件，为简单起见，我们只打印
            print(f"发送邮件: {email_data['to_emails']} - {email_data['subject']}")
            self.email_queue.remove(email_data)
            processed += 1
        return {'processed': processed, 'remaining': len(self.email_queue)}
        
    def send_templated_email(self, to_emails, template_name, context):
        """发送模板化邮件"""
        subject, body = self.render_template(template_name, context)
        
        # 这里应该是实际的邮件发送逻辑
        print(f"发送模板邮件: {to_emails}, 主题: {subject}")
        return {'success': True, 'subject': subject}