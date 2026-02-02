import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def markdown_filter(value):
    """
    将 Markdown 文本转换为 HTML
    """
    if not value:
        return value
    
    md = markdown.Markdown(extensions=[
        'extra',
        'codehilite',
        'tables',
        'toc',
    ])
    html = md.convert(value)
    return mark_safe(html)


@register.simple_tag
def markdown_render(text):
    """
    渲染 Markdown 文本的简单标签
    """
    if not text:
        return ""
    
    md = markdown.Markdown(extensions=[
        'extra',
        'codehilite',
        'tables',
        'toc',
    ])
    html = md.convert(text)
    return mark_safe(html)