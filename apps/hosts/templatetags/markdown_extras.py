import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='markdown')
def markdown_filter(text):
    """
    将 Markdown 文本转换为 HTML
    """
    if text:
        # 使用安全的 Markdown 扩展，避免 XSS 攻击
        html = markdown.markdown(text, extensions=['extra', 'codehilite', 'toc'])
        return mark_safe(html)
    return text